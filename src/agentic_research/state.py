from __future__ import annotations

from typing import Any, Literal, TypedDict


# Possible final outcomes for a run
Status = Literal["in_progress", "success", "failed"]
# What the reviewer returns after inspecting the patch
ReviewRecommendation = Literal["accept", "revise"]


# All the fields passed between graph nodes throughout a run.
# total=False means every field is optional so nodes can return partial updates.
class AgentState(TypedDict, total=False):
    task_id: str
    title: str
    repository: str
    description: str
    difficulty: str
    constraints: list[str]
    acceptance_keywords: list[str]
    validation_instructions: str
    execution_mode: str
    fixture_dir: str
    editable_files: list[str]
    readonly_files: list[str]
    test_command: list[str]
    regression_test_command: list[str]
    test_env: dict[str, str]
    workspace_path: str
    base_workspace_path: str
    venv_python: str
    repo_context: dict[str, str]
    architecture: Literal["single", "multi"]
    issue_summary: str
    root_cause: str
    current_patch: str
    patch_summary: str
    patch_diff: str
    changed_files: list[str]
    validation_passed: bool
    validation_report: str
    test_stdout: str
    test_stderr: str
    test_returncode: int
    regression_passed: bool
    regression_returncode: int
    review_recommendation: ReviewRecommendation
    review_notes: str
    coordinator_plan: str
    messages: list[dict[str, Any]]
    branch_id: str
    selected_branch_id: str
    engineer_worker_count: int
    branch_results: list[dict[str, Any]]
    latest_feedback: str
    last_progress_signature: str
    no_progress_count: int
    iteration_count: int
    max_iterations: int
    revision_count: int
    max_revision_rounds: int
    llm_calls_used: int
    tokens_used: int
    input_tokens_used: int
    output_tokens_used: int
    cached_tokens: int
    tokens_by_role: dict[str, int]
    max_llm_calls: int
    transcript_tail_k: int
    final_status: Status
    logs: list[dict[str, Any]]
    transcript: list[dict[str, Any]]
    metrics: dict[str, Any]


# Build the starting state dict from a task spec before the graph runs.
def build_initial_state(
    task: dict[str, Any],
    architecture: Literal["single", "multi"],
    max_iterations: int = 50,
    max_revision_rounds: int = 30,
    max_llm_calls: int = 0,
    transcript_tail_k: int = 6,
) -> AgentState:
    return {
        "task_id": task["id"],
        "title": task["title"],
        "repository": task["repository"],
        "description": task["description"],
        "difficulty": task["difficulty"],
        "constraints": task["constraints"],
        "acceptance_keywords": task["acceptance_keywords"],
        "validation_instructions": task["validation_instructions"],
        "execution_mode": task.get("execution_mode", "proposal"),
        "fixture_dir": task.get("fixture_dir", ""),
        "editable_files": task.get("editable_files", []),
        "readonly_files": task.get("readonly_files", []),
        "test_command": task.get("test_command", []),
        "regression_test_command": task.get("regression_test_command", []),
        "test_env": task.get("test_env", {}),
        "workspace_path": "",
        "base_workspace_path": "",
        "venv_python": "",
        "repo_context": {},
        "architecture": architecture,
        "issue_summary": "",
        "root_cause": "",
        "current_patch": "",
        "patch_summary": "",
        "patch_diff": "",
        "changed_files": [],
        "validation_passed": False,
        "validation_report": "",
        "test_stdout": "",
        "test_stderr": "",
        "test_returncode": 0,
        "regression_passed": None,
        "regression_returncode": None,
        "review_recommendation": "revise",
        "review_notes": "",
        "coordinator_plan": "",
        "messages": [],
        "branch_id": "",
        "selected_branch_id": "",
        "engineer_worker_count": 0,
        "branch_results": [],
        "latest_feedback": "",
        "last_progress_signature": "",
        "no_progress_count": 0,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "revision_count": 0,
        "max_revision_rounds": max_revision_rounds,
        "llm_calls_used": 0,
        "tokens_used": 0,
        "input_tokens_used": 0,
        "output_tokens_used": 0,
        "cached_tokens": 0,
        "tokens_by_role": {},
        "max_llm_calls": max_llm_calls,
        "transcript_tail_k": transcript_tail_k,
        "final_status": "in_progress",
        "logs": [],
        "transcript": [],
        "metrics": {},
    }
