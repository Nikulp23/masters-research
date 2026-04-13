from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

# Two-tailed t critical values for 95% CI indexed by degrees of freedom (n-1).
_T_TABLE = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365}

_TASK_LABELS = {
    "no-color": "NO_COLOR support",
    "negative-flag-fixture": "Negative flag default",
    "plugin-loader-fixture": "Plugin loader filter",
    "tag-parser-fixture": "Tag parser whitespace",
}


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


def _ci_half_width(values: list[float]) -> float | None:
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = math.sqrt(variance)
    t = _T_TABLE.get(n - 1, 1.96)
    return t * std / math.sqrt(n)


def build_chart_data(benchmark_root: str | Path = "benchmark_runs") -> dict[str, Any]:
    root = Path(benchmark_root)
    if not root.exists():
        raise FileNotFoundError(f"Benchmark root not found: {root}")

    groups: dict[tuple[str, str], dict[str, list]] = defaultdict(
        lambda: {"latency": [], "llm_calls": [], "tokens": [], "success": []}
    )
    task_meta: dict[str, str] = {}

    for run in _load_runs(root):
        task_id = run.get("task_id", "unknown")
        arch = run.get("architecture", "unknown")
        task_meta.setdefault(task_id, run.get("task_title", task_id))
        key = (task_id, arch)
        groups[key]["latency"].append(float(run.get("latency_seconds", 0)))
        groups[key]["llm_calls"].append(float(run.get("llm_calls_used", 0)))
        groups[key]["tokens"].append(float(run.get("tokens_used", 0)))
        groups[key]["success"].append(1.0 if run.get("final_status") == "success" else 0.0)

    tasks = sorted(task_meta.keys())
    task_labels = [_TASK_LABELS.get(t, task_meta[t]) for t in tasks]

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    def _arch_means(metric: str, arch: str) -> list[float]:
        return [round(_mean(groups[(t, arch)][metric]), 4) for t in tasks]

    def _arch_ci(metric: str, arch: str) -> list[float | None]:
        return [
            (round(ci, 4) if (ci := _ci_half_width(groups[(t, arch)][metric])) is not None else None)
            for t in tasks
        ]

    def _arch_success(arch: str) -> list[float]:
        return [round(_mean(groups[(t, arch)]["success"]), 4) for t in tasks]

    all_single_lat = [v for t in tasks for v in groups[(t, "single")]["latency"]]
    all_multi_lat  = [v for t in tasks for v in groups[(t, "multi")]["latency"]]
    all_single_llm = [v for t in tasks for v in groups[(t, "single")]["llm_calls"]]
    all_multi_llm  = [v for t in tasks for v in groups[(t, "multi")]["llm_calls"]]

    sl_mean = round(_mean(all_single_lat), 4)
    ml_mean = round(_mean(all_multi_lat), 4)
    sl_ci   = _ci_half_width(all_single_lat)
    ml_ci   = _ci_half_width(all_multi_lat)
    sl_llm  = round(_mean(all_single_llm), 4)
    ml_llm  = round(_mean(all_multi_llm), 4)

    lat_overhead = round((ml_mean - sl_mean) / sl_mean * 100, 1) if sl_mean else 0
    llm_overhead = round((ml_llm - sl_llm) / sl_llm * 100, 1) if sl_llm else 0

    return {
        "tasks": tasks,
        "taskLabels": task_labels,
        "latency": {
            "single": {"means": _arch_means("latency", "single"), "ci": _arch_ci("latency", "single")},
            "multi":  {"means": _arch_means("latency", "multi"),  "ci": _arch_ci("latency", "multi")},
        },
        "llmCalls": {
            "single": {"means": _arch_means("llm_calls", "single")},
            "multi":  {"means": _arch_means("llm_calls", "multi")},
        },
        "tokens": {
            "single": {"means": _arch_means("tokens", "single")},
            "multi":  {"means": _arch_means("tokens", "multi")},
        },
        "successRate": {
            "single": _arch_success("single"),
            "multi":  _arch_success("multi"),
        },
        "aggregate": {
            "meanLatencySingle":  sl_mean,
            "meanLatencyMulti":   ml_mean,
            "ciLatencySingle":    round(sl_ci, 4) if sl_ci is not None else None,
            "ciLatencyMulti":     round(ml_ci, 4) if ml_ci is not None else None,
            "meanLlmSingle":      sl_llm,
            "meanLlmMulti":       ml_llm,
            "latencyOverheadPct": lat_overhead,
            "llmOverheadPct":     llm_overhead,
        },
    }


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
                "tokens_used": run.get("tokens_used", 0),
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
    chart_data = build_chart_data(benchmark_root)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    json_path = target / "conversations.json"
    js_path   = target / "conversations.js"
    json_text = json.dumps(data, indent=2)
    json_path.write_text(json_text)
    js_path.write_text(f"window.AGENTIC_CONVERSATIONS = {json_text};\n")

    chart_json_text = json.dumps(chart_data, indent=2)
    chart_json_path = target / "chart_data.json"
    chart_js_path   = target / "chart_data.js"
    chart_json_path.write_text(chart_json_text)
    chart_js_path.write_text(f"window.AGENTIC_CHART_DATA = {chart_json_text};\n")

    return {
        "issue_count": data["issue_count"],
        "json_path": str(json_path),
        "js_path": str(js_path),
        "chart_js_path": str(chart_js_path),
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
