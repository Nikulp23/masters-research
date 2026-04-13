import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_research.sandbox import (
    _build_preflight_command,
    _setup_cargo_dependencies,
    _uses_python_pytest,
    _validate_test_command_inputs,
    run_test_preflight,
)


class SandboxPreflightTests(unittest.TestCase):
    def test_unittest_discover_preflight_passes_for_valid_test_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_issue_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
            )
            result = run_test_preflight(
                str(root),
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_demo.py", "-v"],
                expected_test_files=["tests/test_issue_demo.py"],
            )
            self.assertTrue(result["passed"])
            self.assertEqual(result["returncode"], 0)

    def test_unittest_module_preflight_fails_for_missing_module_target(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_issue_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
            )
            result = run_test_preflight(
                str(root),
                ["python3", "-m", "unittest", "tests.missing_issue_demo", "-v"],
                expected_test_files=["tests/test_issue_demo.py"],
            )
            self.assertFalse(result["passed"])
            self.assertEqual(result["returncode"], -2)
            self.assertIn("preflight failed", result["stderr"].lower())

    def test_preflight_fails_for_missing_editable_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_issue_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
            )
            result = run_test_preflight(
                str(root),
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_demo.py", "-v"],
                expected_test_files=["tests/test_issue_demo.py"],
                editable_files=["src/missing.py"],
            )
            self.assertFalse(result["passed"])
            self.assertEqual(result["returncode"], -3)
            self.assertIn("missing editable files", result["stderr"].lower())

    def test_cargo_preflight_compiles_tests_without_running_them(self) -> None:
        self.assertEqual(
            _build_preflight_command(["cargo", "test"]),
            ["cargo", "test", "--no-run"],
        )
        self.assertEqual(
            _build_preflight_command(
                [
                    "cargo",
                    "test",
                    "--test",
                    "real_test",
                    "-p",
                    "crate",
                    "--",
                    "--nocapture",
                ]
            ),
            ["cargo", "test", "--test", "real_test", "-p", "crate", "--no-run"],
        )

    def test_cargo_validation_requires_workspace_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            self.assertEqual(
                _validate_test_command_inputs(root, ["cargo", "test"]),
                "cargo test requires Cargo.toml in workspace root",
            )
            (root / "Cargo.toml").write_text(
                '[package]\nname = "demo"\nversion = "0.1.0"\n'
            )
            self.assertIsNone(_validate_test_command_inputs(root, ["cargo", "test"]))

    def test_setup_cargo_dependencies_fetches_when_manifest_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            with patch("agentic_research.sandbox._run_setup_command") as run_setup_command:
                _setup_cargo_dependencies(str(root))
                run_setup_command.assert_not_called()

            (root / "Cargo.toml").write_text(
                '[package]\nname = "demo"\nversion = "0.1.0"\n'
            )
            with patch("agentic_research.sandbox._run_setup_command") as run_setup_command:
                _setup_cargo_dependencies(str(root))
                run_setup_command.assert_called_once_with(["cargo", "fetch"], str(root))

    def test_pytest_install_detection_does_not_match_js_commands(self) -> None:
        self.assertTrue(
            _uses_python_pytest(["python", "-m", "pytest", "tests/test_demo.py"])
        )
        self.assertFalse(_uses_python_pytest(["sh", "node_modules/.bin/jest", "test.tsx"]))
        self.assertFalse(_uses_python_pytest(["node", "node_modules/.bin/jest", "test.ts"]))


if __name__ == "__main__":
    unittest.main()
