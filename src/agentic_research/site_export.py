from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _normalize_role(value: str) -> str:
    return value.replace("_", " ").title()


def _legacy_transcript(run: dict[str, Any]) -> list[dict[str, Any]]:
    architecture_role = "Single Agent" if run.get("architecture") == "single" else "Multi Agent"
    transcript: list[dict[str, Any]] = []

    issue_summary = run.get("issue_summary", "")
    if issue_summary:
        transcript.append(
            {
                "role": architecture_role,
                "phase": "summarize_issue",
                "kind": "summary",
                "iteration": 0,
                "revision": 0,
                "response": issue_summary,
            }
        )

    root_cause = run.get("root_cause", "")
    if root_cause:
        transcript.append(
            {
                "role": "Engineer" if run.get("architecture") == "multi" else architecture_role,
                "phase": "diagnose_root_cause",
                "kind": "summary",
                "iteration": 0,
                "revision": 0,
                "response": root_cause,
            }
        )

    current_patch = run.get("current_patch", "")
    patch_summary = run.get("patch_summary", "")
    if current_patch or patch_summary:
        transcript.append(
            {
                "role": "Engineer" if run.get("architecture") == "multi" else architecture_role,
                "phase": "propose_patch",
                "kind": "summary",
                "iteration": max(run.get("iterations", 1) - 1, 0),
                "revision": run.get("revision_count", 0),
                "response": patch_summary or "Patch proposal recorded.",
                "patch_payload": current_patch,
            }
        )

    for log in run.get("logs", []):
        transcript.append(
            {
                "role": _normalize_role(log.get("role", "agent")),
                "phase": "event",
                "kind": "event",
                "iteration": log.get("iteration", 0),
                "revision": log.get("revision", 0),
                "message": log.get("message", ""),
            }
        )

    validation_report = run.get("validation_report", "")
    if validation_report:
        transcript.append(
            {
                "role": "Tester / QA",
                "phase": "validate",
                "kind": "summary",
                "iteration": run.get("iterations", 0),
                "revision": run.get("revision_count", 0),
                "response": validation_report,
            }
        )

    review_notes = run.get("review_notes", "")
    if review_notes:
        transcript.append(
            {
                "role": "Reviewer",
                "phase": "review",
                "kind": "summary",
                "iteration": run.get("iterations", 0),
                "revision": run.get("revision_count", 0),
                "response": review_notes,
            }
        )

    test_stdout = run.get("test_stdout", "")
    test_stderr = run.get("test_stderr", "")
    if test_stdout or test_stderr:
        transcript.append(
            {
                "role": "Sandbox",
                "phase": "execute_patch",
                "kind": "execution",
                "iteration": run.get("iterations", 0),
                "revision": run.get("revision_count", 0),
                "message": "Recorded test execution output from the raw benchmark run.",
                "test_returncode": run.get("test_returncode"),
                "test_stdout": test_stdout,
                "test_stderr": test_stderr,
                "changed_files": run.get("changed_files", []),
            }
        )

    return transcript


def _load_runs(benchmark_root: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(benchmark_root.glob("*/raw/*.json")):
        payload = json.loads(path.read_text())
        payload.setdefault("run_id", path.stem)
        payload.setdefault("transcript", _legacy_transcript(payload))
        payload.setdefault("messages", [])
        payload.setdefault("patch_summary", "")
        payload.setdefault("current_patch", "")
        payload.setdefault("test_stdout", "")
        payload.setdefault("test_stderr", "")
        runs.append(payload)
    runs.sort(key=lambda item: item.get("timestamp_utc", ""), reverse=True)
    return runs


def build_site_data(benchmark_root: str | Path = "benchmark_runs") -> dict[str, Any]:
    root = Path(benchmark_root)
    if not root.exists():
        raise FileNotFoundError(f"Benchmark root does not exist: {root}")

    issues: dict[str, dict[str, Any]] = {}
    for run in _load_runs(root):
        issue = issues.setdefault(
            run["task_id"],
            {
                "task_id": run["task_id"],
                "title": run.get("task_title", run["task_id"]),
                "repository": run.get("repository", ""),
                "runs": {"single": [], "multi": []},
            },
        )
        issue["runs"].setdefault(run["architecture"], []).append(
            {
                "run_id": run.get("run_id", ""),
                "suite_id": run.get("suite_id", ""),
                "timestamp_utc": run.get("timestamp_utc", ""),
                "architecture": run.get("architecture", ""),
                "workflow_label": run.get("workflow_label", ""),
                "role_count": run.get("role_count"),
                "engineer_worker_count": run.get("engineer_worker_count", 0),
                "mode": run.get("mode", ""),
                "model": run.get("model", ""),
                "final_status": run.get("final_status", ""),
                "failure_category": run.get("failure_category", ""),
                "validation_passed": run.get("validation_passed", False),
                "review_recommendation": run.get("review_recommendation", ""),
                "latency_seconds": run.get("latency_seconds", 0),
                "iterations": run.get("iterations", 0),
                "revision_count": run.get("revision_count", 0),
                "llm_calls_used": run.get("llm_calls_used", 0),
                "changed_files": run.get("changed_files", []),
                "issue_summary": run.get("issue_summary", ""),
                "root_cause": run.get("root_cause", ""),
                "validation_report": run.get("validation_report", ""),
                "review_notes": run.get("review_notes", ""),
                "patch_summary": run.get("patch_summary", ""),
                "current_patch": run.get("current_patch", ""),
                "test_returncode": run.get("test_returncode"),
                "test_stdout": run.get("test_stdout", ""),
                "test_stderr": run.get("test_stderr", ""),
                "selected_branch_id": run.get("selected_branch_id", ""),
                "branch_results": run.get("branch_results", []),
                "logs": run.get("logs", []),
                "transcript": run.get("transcript", []),
                "messages": run.get("messages", []),
            }
        )

    ordered_issues = sorted(issues.values(), key=lambda item: item["title"].lower())
    return {
        "generated_from": str(root),
        "issue_count": len(ordered_issues),
        "issues": ordered_issues,
    }


def export_site_data(
    benchmark_root: str | Path = "benchmark_runs",
    output_dir: str | Path = "site-data",
) -> dict[str, Any]:
    data = build_site_data(benchmark_root)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "conversations.json"
    js_path = target / "conversations.js"
    json_text = json.dumps(data, indent=2)
    json_path.write_text(json_text)
    js_path.write_text(f"window.AGENTIC_CONVERSATIONS = {json_text};\n")
    return {
        "issue_count": data["issue_count"],
        "json_path": str(json_path),
        "js_path": str(js_path),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export benchmark conversation data for the website.")
    parser.add_argument(
        "--benchmark-root",
        default="benchmark_runs",
        help="Directory containing suite folders with raw benchmark JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default="site-data",
        help="Directory where the website conversation data files should be written.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = export_site_data(benchmark_root=args.benchmark_root, output_dir=args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
