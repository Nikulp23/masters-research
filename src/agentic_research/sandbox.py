from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

UNITTEST_PREFLIGHT_SCRIPT = """
from __future__ import annotations

import json
import sys
import unittest


def main() -> int:
    args = sys.argv[1:]
    loader = unittest.TestLoader()
    suite = None

    if args and args[0] == "discover":
        start_dir = "."
        pattern = "test*.py"
        top_level_dir = None
        index = 1
        while index < len(args):
            arg = args[index]
            if arg in {"-s", "--start-directory"} and index + 1 < len(args):
                start_dir = args[index + 1]
                index += 2
                continue
            if arg in {"-p", "--pattern"} and index + 1 < len(args):
                pattern = args[index + 1]
                index += 2
                continue
            if arg in {"-t", "--top-level-directory"} and index + 1 < len(args):
                top_level_dir = args[index + 1]
                index += 2
                continue
            index += 1
        suite = loader.discover(start_dir=start_dir, pattern=pattern, top_level_dir=top_level_dir)
    else:
        names = [arg for arg in args if not arg.startswith("-")]
        suite = loader.loadTestsFromNames(names)

    errors = list(loader.errors)
    payload = {
        "passed": not errors and suite.countTestCases() > 0,
        "errors": errors,
        "test_count": suite.countTestCases(),
    }
    print(json.dumps(payload))
    return 0 if payload["passed"] else 1


raise SystemExit(main())
"""


def create_workspace(task: dict[str, Any]) -> str:
    fixture_dir = task.get("fixture_dir")
    source_repo_path = task.get("source_repo_path")
    if source_repo_path:
        source = Path(source_repo_path)
    elif fixture_dir:
        source = PROJECT_ROOT / fixture_dir
    else:
        raise ValueError("Task is missing fixture_dir or source_repo_path.")
    if not source.exists():
        raise FileNotFoundError(f"Fixture directory does not exist: {source}")
    workspace = Path(tempfile.mkdtemp(prefix=f"agentic-{task['id']}-"))
    shutil.copytree(source, workspace, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "node_modules"))

    base_commit = task.get("base_commit")
    if base_commit:
        # Copy the .git directory separately (needed for checkout), then reset to buggy commit.
        git_source = source / ".git"
        if not git_source.exists():
            raise FileNotFoundError(
                f"base_commit specified but {source} has no .git directory. "
                "Run `git fetch --unshallow` in the repo first."
            )
        shutil.copytree(git_source, workspace / ".git")
        result = subprocess.run(
            ["git", "checkout", base_commit, "--", "."],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to checkout base_commit {base_commit!r} in workspace:\n{result.stderr}"
            )

    for relative_path, content in task.get("injected_test_files", {}).items():
        target = workspace / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return str(workspace)


def clone_workspace(workspace_path: str, suffix: str) -> str:
    source = Path(workspace_path)
    if not source.exists():
        raise FileNotFoundError(f"Workspace does not exist: {source}")
    cloned = Path(tempfile.mkdtemp(prefix=f"{source.name}-{suffix}-"))
    shutil.copytree(source, cloned, dirs_exist_ok=True, ignore=shutil.ignore_patterns("node_modules"))
    # Re-point editable-install path references inside the cloned venv so that
    # package imports resolve from the clone's source tree, not the original.
    old_path = str(source)
    new_path = str(cloned)
    venv_dir = cloned / ".venv"
    if venv_dir.exists():
        for f in venv_dir.rglob("*"):
            if f.suffix in (".pth", ".egg-link") or f.name == "direct_url.json":
                try:
                    content = f.read_text(errors="replace")
                    if old_path in content:
                        f.write_text(content.replace(old_path, new_path))
                except (OSError, PermissionError):
                    pass
    _setup_js_dependencies(str(cloned))
    _setup_cargo_dependencies(str(cloned))
    return str(cloned)


def setup_virtualenv(workspace_path: str, test_command: list[str] | None = None) -> str:
    workspace = Path(workspace_path)
    venv_dir = workspace / ".venv"
    subprocess.run(["python3", "-m", "venv", str(venv_dir)], check=True, cwd=workspace_path, text=True, capture_output=True)
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.exists():
        raise FileNotFoundError(f"Virtualenv python not found: {python_bin}")
    installs_pytest_dependencies = False
    for metadata_file in ("pyproject.toml", "setup.py", "setup.cfg"):
        if (workspace / metadata_file).exists():
            install_command = [str(python_bin), "-m", "pip", "install", "-e", "."]
            if _uses_python_pytest(test_command or []) and _has_dependency_group(workspace, "tests"):
                install_command.extend(["--group", "tests"])
                installs_pytest_dependencies = True
            _run_setup_command(install_command, workspace_path)
            break
    if _uses_python_pytest(test_command or []) and not installs_pytest_dependencies:
        _run_setup_command([str(python_bin), "-m", "pip", "install", "pytest", "-q"], workspace_path)
    # Install JS/TS dependencies if this is a JavaScript/TypeScript project.
    _setup_js_dependencies(workspace_path)
    # Fetch Rust dependencies if this is a Cargo project.
    _setup_cargo_dependencies(workspace_path)
    return str(python_bin)


def _setup_js_dependencies(workspace_path: str) -> None:
    """Install npm/pnpm dependencies when package.json is present."""
    workspace = Path(workspace_path)
    if not (workspace / "package.json").exists():
        return
    if shutil.which("pnpm") and (workspace / "pnpm-lock.yaml").exists():
        cmd = ["pnpm", "install", "--frozen-lockfile"]
    else:
        cmd = ["npm", "install", "--legacy-peer-deps"]
    _run_setup_command(cmd, workspace_path)


def _uses_python_pytest(command: list[str]) -> bool:
    return len(command) >= 3 and command[0].startswith("python") and command[1:3] == ["-m", "pytest"]


def _has_dependency_group(workspace: Path, group_name: str) -> bool:
    pyproject = workspace / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        data = tomllib.loads(pyproject.read_text())
    except tomllib.TOMLDecodeError:
        return False
    groups = data.get("dependency-groups", {})
    return isinstance(groups, dict) and group_name in groups


def _setup_cargo_dependencies(workspace_path: str) -> None:
    """Fetch Cargo dependencies when Cargo.toml is present."""
    workspace = Path(workspace_path)
    if not (workspace / "Cargo.toml").exists():
        return
    _run_setup_command(["cargo", "fetch"], workspace_path)


def _run_setup_command(command: list[str], workspace_path: str) -> None:
    result = subprocess.run(command, cwd=workspace_path, capture_output=True, text=True)
    if result.returncode == 0:
        return
    details = "\n".join(
        part
        for part in (
            f"Setup command failed: {' '.join(command)}",
            f"cwd: {workspace_path}",
            f"returncode: {result.returncode}",
            "stdout:",
            result.stdout.strip(),
            "stderr:",
            result.stderr.strip(),
        )
        if part
    )
    raise RuntimeError(details)


def load_file_bundle(workspace_path: str, paths: list[str]) -> dict[str, str]:
    workspace = Path(workspace_path)
    bundle: dict[str, str] = {}
    for relative_path in paths:
        bundle[relative_path] = (workspace / relative_path).read_text()
    return bundle


def load_existing_file_bundle(workspace_path: str, paths: list[str]) -> dict[str, str]:
    workspace = Path(workspace_path)
    bundle: dict[str, str] = {}
    for relative_path in paths:
        target = workspace / relative_path
        if target.exists():
            bundle[relative_path] = target.read_text()
    return bundle


def apply_text_edits(
    workspace_path: str,
    edits: list[dict[str, str]],
    editable_files: list[str],
) -> list[str]:
    workspace = Path(workspace_path)
    editable = set(editable_files)
    changed: list[str] = []
    for edit in edits:
        relative_path = edit["path"]
        if relative_path not in editable:
            raise ValueError(f"Attempted to edit non-editable file: {relative_path}")
        find_text = edit.get("find", "")
        replace_text = edit.get("replace", "")
        target = workspace / relative_path
        original = target.read_text()
        if find_text not in original:
            raise ValueError(f"Edit target not found in {relative_path}")
        updated = original.replace(find_text, replace_text, 1)
        target.write_text(updated)
        if relative_path not in changed:
            changed.append(relative_path)
    return changed


def parse_patch_payload(payload: str) -> dict[str, Any]:
    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Patch payload does not contain JSON: {payload}")
    return json.loads(payload[start : end + 1])


def apply_file_updates(workspace_path: str, updates: dict[str, str], editable_files: list[str]) -> list[str]:
    workspace = Path(workspace_path)
    editable = set(editable_files)
    changed: list[str] = []
    for relative_path, content in updates.items():
        if relative_path not in editable:
            raise ValueError(f"Attempted to edit non-editable file: {relative_path}")
        target = workspace / relative_path
        target.write_text(content)
        changed.append(relative_path)
    return changed


def run_test_command(workspace_path: str, command: list[str], env_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    command = _rewrite_python_command(command, env_overrides)
    env = _build_env(workspace_path, env_overrides)
    result = subprocess.run(
        command,
        cwd=workspace_path,
        text=True,
        capture_output=True,
        env=env,
    )
    return {
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command": command,
    }


def _build_env(workspace_path: str, env_overrides: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in (env_overrides or {}).items():
        env[key] = value if os.path.isabs(value) else str(Path(workspace_path) / value)
    return env


def run_test_preflight(
    workspace_path: str,
    command: list[str],
    env_overrides: dict[str, str] | None = None,
    expected_test_files: list[str] | None = None,
    editable_files: list[str] | None = None,
    readonly_files: list[str] | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_path)
    missing_editable = [
        relative_path
        for relative_path in (editable_files or [])
        if not (workspace / relative_path).exists()
    ]
    if missing_editable:
        return {
            "passed": False,
            "returncode": -3,
            "stdout": "",
            "stderr": f"Task preflight failed: missing editable files: {', '.join(missing_editable)}",
            "command": command,
            "reason": "missing_editable_files",
        }

    missing_readonly = [
        relative_path
        for relative_path in (readonly_files or [])
        if not (workspace / relative_path).exists()
    ]
    if missing_readonly:
        return {
            "passed": False,
            "returncode": -3,
            "stdout": "",
            "stderr": f"Task preflight failed: missing readonly files: {', '.join(missing_readonly)}",
            "command": command,
            "reason": "missing_readonly_files",
        }

    missing_expected_tests = [
        relative_path
        for relative_path in (expected_test_files or [])
        if not (workspace / relative_path).exists()
    ]
    if missing_expected_tests:
        return {
            "passed": False,
            "returncode": -3,
            "stdout": "",
            "stderr": f"Task preflight failed: missing injected test files: {', '.join(missing_expected_tests)}",
            "command": command,
            "reason": "missing_test_files",
        }

    command = _rewrite_python_command(command, env_overrides)
    env = _build_env(workspace_path, env_overrides)
    command_validation_error = _validate_test_command_inputs(workspace, command)
    if command_validation_error:
        return {
            "passed": False,
            "returncode": -3,
            "stdout": "",
            "stderr": f"Task preflight failed: {command_validation_error}",
            "command": command,
            "reason": "invalid_test_command",
        }
    preflight_command = _build_preflight_command(command)
    if preflight_command is None:
        return {
            "passed": True,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "command": command,
            "reason": "unsupported_preflight_skipped",
        }

    result = subprocess.run(
        preflight_command,
        cwd=workspace_path,
        text=True,
        capture_output=True,
        env=env,
    )
    parsed = _parse_preflight_output(result.stdout)
    # For pytest --collect-only the output is human-readable (not JSON), so
    # parsed will be empty. A zero returncode from collect-only means tests
    # were discovered successfully, which is all preflight needs to confirm.
    preflight_passed = result.returncode == 0 and (parsed.get("passed", False) or not parsed)
    if preflight_passed:
        return {
            "passed": True,
            "returncode": 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
            "reason": "preflight_passed",
            "test_count": parsed.get("test_count", 0),
        }
    errors = parsed.get("errors", [])
    error_text = "\n".join(errors) if errors else (result.stderr or result.stdout)
    return {
        "passed": False,
        "returncode": -2,
        "stdout": result.stdout,
        "stderr": f"Preflight failed before agent execution.\n{error_text}".strip(),
        "command": command,
        "reason": "harness_preflight_failed",
        "test_count": parsed.get("test_count", 0),
    }


def _build_preflight_command(command: list[str]) -> list[str] | None:
    if len(command) >= 3 and command[1:3] == ["-m", "unittest"]:
        return [command[0], "-c", UNITTEST_PREFLIGHT_SCRIPT, *command[3:]]
    if len(command) >= 3 and command[1:3] == ["-m", "pytest"]:
        targets = [arg for arg in command[3:] if not arg.startswith("-")]
        return [command[0], "-m", "pytest", *targets, "--collect-only", "-q"]
    if len(command) >= 2 and command[:2] == ["cargo", "test"]:
        cargo_args = command[2:]
        if "--" in cargo_args:
            cargo_args = cargo_args[:cargo_args.index("--")]
        if "--no-run" not in cargo_args:
            cargo_args = [*cargo_args, "--no-run"]
        return ["cargo", "test", *cargo_args]
    return None


def _parse_preflight_output(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text.splitlines()[-1])
    except json.JSONDecodeError:
        return {}


def _validate_test_command_inputs(workspace: Path, command: list[str]) -> str | None:
    if len(command) >= 4 and command[1:4] == ["-m", "unittest", "discover"]:
        start_dir = "."
        top_level_dir = None
        index = 4
        while index < len(command):
            arg = command[index]
            if arg in {"-s", "--start-directory"} and index + 1 < len(command):
                start_dir = command[index + 1]
                index += 2
                continue
            if arg in {"-t", "--top-level-directory"} and index + 1 < len(command):
                top_level_dir = command[index + 1]
                index += 2
                continue
            index += 1
        if not (workspace / start_dir).exists():
            return f"unittest discover start directory does not exist: {start_dir}"
        if top_level_dir and not (workspace / top_level_dir).exists():
            return f"unittest discover top-level directory does not exist: {top_level_dir}"
        return None

    if len(command) >= 3 and command[1:3] == ["-m", "pytest"]:
        for arg in command[3:]:
            if arg.startswith("-"):
                continue
            if ("/" in arg or arg.endswith(".py")) and not (workspace / arg).exists():
                return f"pytest target does not exist: {arg}"
        return None

    if len(command) >= 2 and command[:2] == ["cargo", "test"]:
        if not (workspace / "Cargo.toml").exists():
            return "cargo test requires Cargo.toml in workspace root"
        return None

    return None


def _rewrite_python_command(command: list[str], env_overrides: dict[str, str] | None = None) -> list[str]:
    python_bin = (env_overrides or {}).get("AGENTIC_VENV_PYTHON")
    if python_bin and command and command[0].startswith("python"):
        return [python_bin, *command[1:]]
    return command
