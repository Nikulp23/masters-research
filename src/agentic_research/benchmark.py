from __future__ import annotations

import csv
import json
import os
import warnings
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, date
from pathlib import Path
from typing import Any

from .config import load_config
from .graphs import compare_architectures, run_architecture
from .sample_tasks import SAMPLE_TASKS, get_task


PROMPT_VERSION = "faang-v1"
# Flag runs that spend more tokens than expected; helps catch regressions post-optimization.
_TOKEN_BUDGET_WARN = int(os.getenv("AGENTIC_TOKEN_BUDGET_WARN", "60000"))

# Ordered task lists by language — determines the number suffix in folder names.
_TASKS_BY_LANGUAGE: dict[str, list[str]] = {
    "python": [
        "requests-netrc-empty-default",
        "click-flag-value-optional",
        "werkzeug-safe-join-device-names",
        "flask-provide-automatic-options",
        "flask-teardown-all-callbacks",
    ],
    "go": [
        "gin-data-render-content-length",
        "gin-form-binding-empty-slice",
        "gin-literal-colon-route",
        "validator-panic-unique-nil-pointer",
        "testify-mock-assert-expectations-panic",
    ],
    "rust": [
        "clap-builder-quote-empty-default",
        "clap-parser-help-propagate-ignore-errors",
        "clap-parser-value-terminator-regression",
        "clap-complete-zsh-optional-value-args",
        "clap-builder-default-vals-newline",
    ],
    "js": [
        "react-router-create-routes-stub",
        "react-router-double-slash-colon-path",
        "react-router-optional-segment-slash",
        "react-router-percent-encoding",
        "react-router-client-loader-hydrate",
        "ngrx-eslint-prefix-selectors",
        "ngrx-component-illegal-invocation",
        "ngrx-eslint-factory-with-state",
        "ngrx-eslint-on-function-return-type",
        "ngrx-signals-prod-assert-injection",
    ],
}

# Reverse lookup: task_id -> "lang-N" folder label
_TASK_FOLDER_LABEL: dict[str, str] = {
    task_id: f"{lang}-{i + 1}"
    for lang, task_ids in _TASKS_BY_LANGUAGE.items()
    for i, task_id in enumerate(task_ids)
}

# Model training cutoff — bugs fixed on or before this date may be in training data.
MODEL_TRAINING_CUTOFF = date(2025, 8, 1)


def check_task_leakage(task: dict[str, Any]) -> None:
    """Warn if a task's fix_date is within the model's training window."""
    task_type = task.get("task_type", "synthetic")
    fix_date_str = task.get("fix_date")

    if task_type == "synthetic":
        warnings.warn(
            f"Task '{task['id']}' is synthetic — results reflect an artificial bug, "
            "not real-world engineering performance.",
            stacklevel=3,
        )
        return

    if not fix_date_str:
        warnings.warn(
            f"Task '{task['id']}' is marked 'real' but has no fix_date. "
            "Cannot verify the fix is post-training-cutoff.",
            stacklevel=3,
        )
        return

    fix_date = date.fromisoformat(fix_date_str)
    if fix_date <= MODEL_TRAINING_CUTOFF:
        warnings.warn(
            f"Task '{task['id']}' fix_date {fix_date_str} is on or before the model training "
            f"cutoff ({MODEL_TRAINING_CUTOFF}). The model may have seen this fix in training data. "
            "Consider replacing with a more recent bug.",
            stacklevel=3,
        )


@dataclass(frozen=True)
class BenchmarkRunRecord:
    run_id: str
    suite_id: str
    timestamp_utc: str
    task_id: str
    task_title: str
    task_type: str
    fix_date: str
    repository: str
    architecture: str
    workflow_label: str
    role_count: int
    engineer_worker_count: int
    repeat_index: int
    mode: str
    model: str
    prompt_version: str
    max_iterations: int
    max_revision_rounds: int
    max_llm_calls: int
    final_status: str
    validation_passed: bool
    review_recommendation: str
    latency_seconds: float
    iterations: int
    revision_count: int
    llm_calls_used: int
    tokens_used: int
    cached_tokens: int
    tokens_by_role: dict[str, int]
    token_budget_exceeded: bool
    test_returncode: int | None
    regression_passed: bool | None
    failure_category: str
    changed_files: list[str]
    validation_report: str
    review_notes: str
    issue_summary: str
    root_cause: str
    logs: list[dict[str, Any]]
    transcript: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    patch_summary: str
    current_patch: str
    test_stdout: str
    test_stderr: str
    selected_branch_id: str
    branch_results: list[dict[str, Any]]
    attempt_notes: str
    first_attempt_passed: bool


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": result["task_id"],
        "title": result["title"],
        "architecture": result["architecture"],
        "final_status": result["final_status"],
        "validation_passed": result["validation_passed"],
        "review_recommendation": result["review_recommendation"],
        "metrics": result["metrics"],
        "issue_summary": result["issue_summary"],
        "root_cause": result["root_cause"],
        "current_patch": result["current_patch"],
        "validation_report": result["validation_report"],
        "review_notes": result["review_notes"],
        "logs": result["logs"],
        "transcript": result.get("transcript", []),
        "messages": result.get("messages", []),
        "changed_files": result.get("changed_files", []),
        "patch_summary": result.get("patch_summary", ""),
        "current_patch": result.get("current_patch", ""),
        "test_stdout": result.get("test_stdout", ""),
        "test_stderr": result.get("test_stderr", ""),
        "engineer_worker_count": result.get("engineer_worker_count", 0),
        "selected_branch_id": result.get("selected_branch_id", ""),
        "branch_results": result.get("branch_results", []),
        "attempt_notes": result.get("attempt_notes", ""),
        "first_attempt_passed": result.get("first_attempt_passed", True),
    }


def classify_failure(result: dict[str, Any]) -> str:
    if result["final_status"] == "success":
        return "success"

    validation_report = (result.get("validation_report") or "").lower()
    review_notes = (result.get("review_notes") or "").lower()
    test_stderr = (result.get("test_stderr") or "").lower()
    current_patch = (result.get("current_patch") or "").lower()
    combined = " ".join([validation_report, review_notes, test_stderr])

    if "budget exhausted" in combined:
        return "llm_budget_exhausted"
    if "task preflight failed" in combined or result.get("test_returncode") == -3:
        return "task_preflight_failed"
    if "harness preflight failed" in combined or result.get("test_returncode") == -2:
        return "harness_preflight_failed"
    if "invalid json" in combined or "not valid json" in combined:
        return "invalid_patch_payload"
    if "edit target not found" in combined:
        return "patch_target_mismatch"
    if "patch application failed" in combined:
        return "patch_application_failed"
    if result.get("test_returncode") == -1:
        return "execution_failed_before_test"
    if result.get("test_returncode") not in {None, 0}:
        return "test_failed"
    if not current_patch.strip():
        return "no_patch_produced"
    return "unresolved_failure"


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _suite_id() -> str:
    return datetime.now(UTC).strftime("suite-%Y%m%dT%H%M%SZ")


def _make_run_record(
    suite_id: str,
    task_id: str,
    architecture: str,
    repeat_index: int,
    result: dict[str, Any],
) -> BenchmarkRunRecord:
    config = load_config()
    task = get_task(task_id)
    metrics = result["metrics"]
    failure_category = classify_failure(result)
    timestamp = _timestamp()
    return BenchmarkRunRecord(
        run_id=f"{suite_id}-{task_id}-{architecture}-r{repeat_index + 1}",
        suite_id=suite_id,
        timestamp_utc=timestamp,
        task_id=task_id,
        task_title=task["title"],
        task_type=task.get("task_type", "synthetic"),
        fix_date=task.get("fix_date", ""),
        repository=task["repository"],
        architecture=architecture,
        workflow_label="single-agent baseline" if architecture == "single" else "multi-agent workflow",
        role_count=1 if architecture == "single" else 5,
        engineer_worker_count=int(result.get("engineer_worker_count", 0)),
        repeat_index=repeat_index,
        mode=config.mode,
        model=config.openai_model if config.mode == "openai" else "deterministic",
        prompt_version=PROMPT_VERSION,
        max_iterations=config.max_iterations,
        max_revision_rounds=config.max_revision_rounds,
        max_llm_calls=config.max_llm_calls,
        final_status=result["final_status"],
        validation_passed=result["validation_passed"],
        review_recommendation=result["review_recommendation"],
        latency_seconds=float(metrics["latency_seconds"]),
        iterations=int(metrics["iterations"]),
        revision_count=int(metrics["revision_count"]),
        llm_calls_used=int(metrics["llm_calls_used"]),
        tokens_used=int(metrics.get("tokens_used", 0)),
        cached_tokens=int(metrics.get("cached_tokens", 0)),
        tokens_by_role=dict(metrics.get("tokens_by_role") or {}),
        token_budget_exceeded=int(metrics.get("tokens_used", 0)) > _TOKEN_BUDGET_WARN,
        test_returncode=metrics.get("test_returncode"),
        regression_passed=metrics.get("regression_passed"),
        failure_category=failure_category,
        changed_files=result.get("changed_files", []),
        validation_report=result["validation_report"],
        review_notes=result["review_notes"],
        issue_summary=result["issue_summary"],
        root_cause=result["root_cause"],
        logs=result["logs"],
        transcript=result.get("transcript", []),
        messages=result.get("messages", []),
        patch_summary=result.get("patch_summary", ""),
        current_patch=result.get("current_patch", ""),
        test_stdout=result.get("test_stdout", ""),
        test_stderr=result.get("test_stderr", ""),
        selected_branch_id=result.get("selected_branch_id", ""),
        branch_results=result.get("branch_results", []),
        attempt_notes=result.get("attempt_notes", ""),
        first_attempt_passed=bool(result.get("first_attempt_passed", True)),
    )


def _task_arch_dir(task_id: str, architecture: str) -> Path:
    """Return and create benchmark_runs/<lang-N>/<architecture>/."""
    label = _TASK_FOLDER_LABEL.get(task_id, task_id)
    path = Path("benchmark_runs") / label / architecture
    path.mkdir(parents=True, exist_ok=True)
    (path / "raw").mkdir(exist_ok=True)
    return path


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2))


def _write_summary_csv(path: Path, rows: list[BenchmarkRunRecord]) -> None:
    fieldnames = [
        "run_id",
        "suite_id",
        "timestamp_utc",
        "task_id",
        "task_title",
        "task_type",
        "fix_date",
        "repository",
        "architecture",
        "workflow_label",
        "role_count",
        "engineer_worker_count",
        "repeat_index",
        "mode",
        "model",
        "prompt_version",
        "max_iterations",
        "max_revision_rounds",
        "max_llm_calls",
        "final_status",
        "validation_passed",
        "review_recommendation",
        "latency_seconds",
        "iterations",
        "revision_count",
        "llm_calls_used",
        "tokens_used",
        "tokens_by_role",
        "test_returncode",
        "regression_passed",
        "failure_category",
        "changed_files",
        "attempt_notes",
        "first_attempt_passed",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = asdict(row)
            payload["changed_files"] = ";".join(row.changed_files)
            payload["tokens_by_role"] = json.dumps(row.tokens_by_role, sort_keys=True)
            writer.writerow({key: payload[key] for key in fieldnames})


def _aggregate(rows: list[BenchmarkRunRecord]) -> dict[str, Any]:
    by_task: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_bucket = by_task.setdefault(
            row.task_id,
            {
                "task_title": row.task_title,
                "repository": row.repository,
                "architectures": {},
            },
        )
        arch_bucket = task_bucket["architectures"].setdefault(
            row.architecture,
            {
                "runs": 0,
                "successes": 0,
                "avg_latency_seconds": 0.0,
                "avg_llm_calls_used": 0.0,
                "avg_tokens_used": 0.0,
                "avg_cached_tokens": 0.0,
                "token_budget_exceeded_count": 0,
                "failure_categories": {},
            },
        )
        arch_bucket["runs"] += 1
        arch_bucket["successes"] += int(row.final_status == "success")
        arch_bucket["avg_latency_seconds"] += row.latency_seconds
        arch_bucket["avg_llm_calls_used"] += row.llm_calls_used
        arch_bucket["avg_tokens_used"] += row.tokens_used
        arch_bucket["avg_cached_tokens"] += row.cached_tokens
        arch_bucket["token_budget_exceeded_count"] += int(row.token_budget_exceeded)
        arch_bucket["failure_categories"][row.failure_category] = (
            arch_bucket["failure_categories"].get(row.failure_category, 0) + 1
        )

    for task_bucket in by_task.values():
        for arch_bucket in task_bucket["architectures"].values():
            runs = arch_bucket["runs"]
            arch_bucket["success_rate"] = arch_bucket["successes"] / runs if runs else 0.0
            arch_bucket["avg_latency_seconds"] = round(arch_bucket["avg_latency_seconds"] / runs, 6)
            arch_bucket["avg_llm_calls_used"] = round(arch_bucket["avg_llm_calls_used"] / runs, 3)
            arch_bucket["avg_tokens_used"] = round(arch_bucket["avg_tokens_used"] / runs, 1)
            arch_bucket["avg_cached_tokens"] = round(arch_bucket["avg_cached_tokens"] / runs, 1)
            arch_bucket["cache_hit_rate"] = round(
                arch_bucket["avg_cached_tokens"] / arch_bucket["avg_tokens_used"], 3
            ) if arch_bucket["avg_tokens_used"] > 0 else 0.0

    overall = {
        "total_runs": len(rows),
        "tasks": len({row.task_id for row in rows}),
        "architectures": sorted({row.architecture for row in rows}),
        "role_counts": sorted({row.role_count for row in rows}),
    }
    return {"overall": overall, "by_task": by_task}


def run_benchmark_suite(
    task_ids: list[str],
    repeats: int = 1,
    architectures: list[str] | None = None,
) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    selected_architectures = architectures or ["single", "multi"]
    for architecture in selected_architectures:
        if architecture not in {"single", "multi"}:
            raise ValueError(f"Unsupported architecture for benchmark: {architecture}")
    for task_id in task_ids:
        if task_id not in SAMPLE_TASKS:
            raise KeyError(f"Unknown task '{task_id}'")

    suite_id = _suite_id()
    records: list[BenchmarkRunRecord] = []

    for task_id in task_ids:
        check_task_leakage(SAMPLE_TASKS[task_id])
        for repeat_index in range(repeats):
            for architecture in selected_architectures:
                raw_result = run_architecture(architecture, task_id=task_id)
                compact = compact_result(raw_result)
                record = _make_run_record(suite_id, task_id, architecture, repeat_index, compact)
                records.append(record)
                arch_dir = _task_arch_dir(task_id, architecture)
                _write_json(arch_dir / "raw" / f"{record.run_id}.json", asdict(record))

    # Write per-task-per-architecture summary.json
    from collections import defaultdict
    arch_records: dict[tuple[str, str], list[BenchmarkRunRecord]] = defaultdict(list)
    for rec in records:
        arch_records[(rec.task_id, rec.architecture)].append(rec)
    for (task_id, architecture), recs in arch_records.items():
        arch_dir = _task_arch_dir(task_id, architecture)
        _write_json(arch_dir / "summary.json", _aggregate(recs))

    summary = _aggregate(records)
    return {
        "suite_id": suite_id,
        "manifest": {
            "suite_id": suite_id,
            "created_at_utc": _timestamp(),
            "task_ids": task_ids,
            "repeats": repeats,
            "architectures": selected_architectures,
            "config": asdict(load_config()),
            "prompt_version": PROMPT_VERSION,
        },
        "summary": summary,
        "runs": [asdict(record) for record in records],
    }


def run_compare_once(task_id: str) -> dict[str, Any]:
    raw = compare_architectures(task_id)
    return {name: compact_result(result) for name, result in raw.items()}
