from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from .brains import build_log_entry
from .config import load_config
from .providers import BrainProtocol, build_brain
from .sandbox import (
    apply_file_updates,
    apply_text_edits,
    clone_workspace,
    create_workspace,
    load_existing_file_bundle,
    parse_patch_payload,
    setup_virtualenv,
    run_test_preflight,
    run_test_command,
)
from .sample_tasks import TaskSpec, get_task
from .state import AgentState, build_initial_state
from .transcript import append_transcript_entry

MULTI_WORKFLOW_ROLE_COUNT = 5


def _build_multi_worker_brains(config: Any) -> dict[str, Any]:
    return {
        "coordinator": build_brain(config),
        "analyst": build_brain(config),
        "engineers": [build_brain(config) for _ in range(max(config.multi_engineer_workers, 1))],
        "tester": build_brain(config),
        "reviewer": build_brain(config),
    }


def _branch_sort_key(branch: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        0 if branch.get("validation_passed") and branch.get("review_recommendation") == "accept" else 1,
        0 if branch.get("validation_passed") else 1,
        branch.get("test_returncode", 0) if branch.get("test_returncode") is not None else 0,
        branch.get("branch_id", ""),
    )


def _select_branch_result(branch_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not branch_results:
        return {}
    return sorted(branch_results, key=_branch_sort_key)[0]


def _message_id(state: AgentState, sender: str, branch_id: str = "") -> str:
    scope = branch_id or "global"
    sender_slug = sender.lower().replace(" / ", "-").replace(" ", "-")
    return f"{scope}-{sender_slug}-{len(state.get('messages', [])) + 1}"


def _append_message(
    state: AgentState,
    *,
    sender: str,
    recipient: str,
    kind: str,
    content: str,
    branch_id: str = "",
    status: str = "sent",
    reply_to: str = "",
) -> dict[str, Any]:
    message = {
        "id": _message_id(state, sender, branch_id),
        "sender": sender,
        "recipient": recipient,
        "branch_id": branch_id,
        "kind": kind,
        "content": content,
        "status": status,
        "reply_to": reply_to,
        "created_at_iteration": state.get("iteration_count", 0),
        "created_at_revision": state.get("revision_count", 0),
    }
    messages = list(state.get("messages", []))
    messages.append(message)
    state["messages"] = messages
    append_transcript_entry(
        state,
        role=sender,
        phase="message_bus",
        kind="message",
        message=f"{sender} -> {recipient}: {content}",
        extra={
            "message_id": message["id"],
            "message_kind": kind,
            "message_status": status,
            "recipient": recipient,
            "branch_id": branch_id or None,
            "reply_to": reply_to,
        },
    )
    return message


def _mark_message_answered(state: AgentState, message_id: str) -> None:
    updated: list[dict[str, Any]] = []
    for item in state.get("messages", []):
        if item.get("id") == message_id:
            updated.append({**item, "status": "answered"})
        else:
            updated.append(item)
    state["messages"] = updated


def _merge_messages(*message_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for group in message_groups:
        for item in group:
            merged[item["id"]] = item
    return sorted(
        merged.values(),
        key=lambda item: (
            item.get("created_at_iteration", 0),
            item.get("created_at_revision", 0),
            item.get("id", ""),
        ),
    )


def _message_scope_matches(message: dict[str, Any], branch_id: str = "") -> bool:
    message_branch = message.get("branch_id") or ""
    if branch_id:
        return message_branch in {"", branch_id}
    return message_branch == ""


def _role_question_and_answer(state: AgentState, sender: str) -> None:
    branch_id = state.get("branch_id", "")
    if sender == "Engineer":
        question = _append_message(
            state,
            sender="Engineer",
            recipient="Analyst",
            kind="question",
            branch_id=branch_id,
            status="open",
            content="Confirm the implementation should stay tightly scoped to the targeted editable file and issue behavior.",
        )
        _append_message(
            state,
            sender="Analyst",
            recipient="Engineer",
            kind="answer",
            branch_id=branch_id,
            reply_to=question["id"],
            content="Yes. Keep the patch local to the targeted editable file and avoid unrelated behavior changes.",
        )
        _mark_message_answered(state, question["id"])
    elif sender == "Tester / QA":
        question = _append_message(
            state,
            sender="Tester / QA",
            recipient="Engineer",
            kind="question",
            branch_id=branch_id,
            status="open",
            content="What behavior was this patch intended to change so I can ground the validation summary correctly?",
        )
        _append_message(
            state,
            sender="Engineer",
            recipient="Tester / QA",
            kind="answer",
            branch_id=branch_id,
            reply_to=question["id"],
            content=(
                state.get("patch_summary")
                or "The patch is intended to make the targeted regression test pass without broadening scope."
            ),
        )
        _mark_message_answered(state, question["id"])
    elif sender == "Reviewer":
        question = _append_message(
            state,
            sender="Reviewer",
            recipient="Engineer",
            kind="question",
            branch_id=branch_id,
            status="open",
            content="Was the patch intentionally limited to the current changed files, or did you leave known follow-up work unaddressed?",
        )
        _append_message(
            state,
            sender="Engineer",
            recipient="Reviewer",
            kind="answer",
            branch_id=branch_id,
            reply_to=question["id"],
            content=(
                f"The patch was intentionally limited to {', '.join(state.get('changed_files', [])) or 'the targeted file set'} "
                "to match the task and keep the change reviewable."
            ),
        )
        _mark_message_answered(state, question["id"])


def _prepare_execution_state(task: TaskSpec, state: AgentState) -> AgentState:
    if task.get("execution_mode") != "sandbox":
        return state
    workspace_path = create_workspace(task)
    venv_python = setup_virtualenv(workspace_path)
    repo_paths = task.get("editable_files", []) + task.get("readonly_files", [])
    prompt_context = task.get("prompt_context")
    test_env = {**state.get("test_env", {}), "AGENTIC_VENV_PYTHON": venv_python}
    return {
        "workspace_path": workspace_path,
        "base_workspace_path": workspace_path,
        "venv_python": venv_python,
        "test_env": test_env,
        "repo_context": prompt_context or load_existing_file_bundle(workspace_path, repo_paths),
    }


def _run_harness_preflight(task: TaskSpec, state: AgentState) -> AgentState | None:
    if task.get("execution_mode") != "sandbox":
        return None
    preflight = run_test_preflight(
        state["workspace_path"],
        state["test_command"],
        state.get("test_env", {}),
        task.get("readonly_files", []),
        task.get("editable_files", []),
        task.get("readonly_files", []),
    )
    if preflight["passed"]:
        return None
    phase = "task_preflight" if preflight["returncode"] == -3 else "preflight"
    failure_label = "Task preflight" if preflight["returncode"] == -3 else "Harness preflight"
    failed_state: AgentState = {
        "validation_passed": False,
        "validation_report": f"{failure_label} failed before agent execution.",
        "review_recommendation": "revise",
        "review_notes": f"{failure_label.lower()} failure detected before any agent patch attempt.",
        "latest_feedback": f"{failure_label} failed. The agents were not asked to repair task setup or the test harness.",
        "final_status": "failed",
        "test_returncode": preflight["returncode"],
        "test_stdout": preflight["stdout"],
        "test_stderr": preflight["stderr"],
        "changed_files": [],
        "logs": state["logs"] + [
            build_log_entry(phase, state, f"{failure_label} failed before agent execution.")
        ],
        "transcript": state.get("transcript", []),
    }
    append_transcript_entry(
        failed_state,
        role="Task Preflight" if preflight["returncode"] == -3 else "Harness Preflight",
        phase=phase,
        kind="deterministic",
        message=f"The benchmark stopped before agent execution because {failure_label.lower()} failed.",
        extra={
            "test_returncode": preflight["returncode"],
            "test_stdout": preflight["stdout"],
            "test_stderr": preflight["stderr"],
            "command": state["test_command"],
        },
    )
    return failed_state


def _execute_real_patch(state: AgentState, patch_payload: str, role: str) -> AgentState:
    parsed = parse_patch_payload(patch_payload)
    summary = parsed.get("summary", "")
    files = parsed.get("files", {})
    edits = parsed.get("edits", [])
    if isinstance(files, dict) and files:
        changed_files = apply_file_updates(state["workspace_path"], files, state["editable_files"])
    elif isinstance(edits, list) and edits:
        changed_files = apply_text_edits(state["workspace_path"], edits, state["editable_files"])
    else:
        raise ValueError("Patch payload must include a non-empty 'files' or 'edits' object.")
    test_result = run_test_command(
        state["workspace_path"],
        state["test_command"],
        state.get("test_env", {}),
    )
    append_transcript_entry(
        state,
        role=role,
        phase="execute_patch",
        kind="execution",
        message="Applied the patch payload in the sandbox and ran the real test command.",
        extra={
            "patch_summary": summary,
            "patch_payload": patch_payload,
            "changed_files": changed_files,
            "test_returncode": test_result["returncode"],
            "test_stdout": test_result["stdout"],
            "test_stderr": test_result["stderr"],
        },
    )
    repo_paths = state["editable_files"] + state["readonly_files"]
    return {
        "current_patch": patch_payload,
        "patch_summary": summary,
        "changed_files": changed_files,
        "validation_passed": test_result["passed"],
        "test_returncode": test_result["returncode"],
        "test_stdout": test_result["stdout"],
        "test_stderr": test_result["stderr"],
        "repo_context": load_existing_file_bundle(state["workspace_path"], repo_paths),
        "transcript": state.get("transcript", []),
    }


def _execution_failure_update(state: AgentState, patch_payload: str, error: Exception, role: str) -> AgentState:
    append_transcript_entry(
        state,
        role=role,
        phase="execute_patch",
        kind="execution",
        message=f"Patch application or test execution failed: {error}",
        extra={
            "patch_payload": patch_payload,
            "changed_files": [],
            "test_returncode": -1,
            "test_stdout": "",
            "test_stderr": f"Patch application failed: {error}",
        },
    )
    return {
        "current_patch": patch_payload,
        "patch_summary": "",
        "changed_files": [],
        "validation_passed": False,
        "test_returncode": -1,
        "test_stdout": "",
        "test_stderr": f"Patch application failed: {error}",
        "transcript": state.get("transcript", []),
    }


def _deterministic_validate(state: AgentState, role: str) -> tuple[bool, str]:
    passed = state.get("test_returncode", -1) == 0
    if passed:
        report = (
            f"{role} validation passed deterministically from the real test result. "
            f"Return code 0 for {', '.join(state.get('changed_files', [])) or 'no changed files'}."
        )
    else:
        report = (
            f"{role} validation failed deterministically from the real test result. "
            f"Return code {state.get('test_returncode')}.\nSTDOUT:\n{state.get('test_stdout', '')}\n"
            f"STDERR:\n{state.get('test_stderr', '')}"
        )
    append_transcript_entry(
        state,
        role=role,
        phase="validate",
        kind="deterministic",
        message=report,
        extra={
            "test_returncode": state.get("test_returncode"),
            "test_stdout": state.get("test_stdout", ""),
            "test_stderr": state.get("test_stderr", ""),
            "changed_files": state.get("changed_files", []),
        },
    )
    return passed, report


def _deterministic_review(state: AgentState, role: str) -> tuple[Literal["accept", "revise"], str]:
    if not state.get("validation_passed"):
        notes = f"{role} review: revise because the real test execution is still failing."
        recommendation: Literal["accept", "revise"] = "revise"
    elif not state.get("changed_files"):
        notes = f"{role} review: revise because no code change was applied in the sandbox."
        recommendation = "revise"
    else:
        notes = (
            f"{role} review: accept because the patch stayed scoped to "
            f"{', '.join(state.get('changed_files', []))} and the real test passed."
        )
        recommendation = "accept"
    append_transcript_entry(
        state,
        role=role,
        phase="review",
        kind="deterministic",
        message=notes,
        extra={
            "recommendation": recommendation,
            "validation_passed": state.get("validation_passed"),
            "changed_files": state.get("changed_files", []),
        },
    )
    return recommendation, notes


def _progress_signature(state: AgentState) -> str:
    changed_files = ",".join(sorted(state.get("changed_files", [])))
    return "|".join(
        [
            changed_files,
            str(state.get("test_returncode")),
            str(state.get("validation_passed")),
            str(state.get("review_recommendation", "")),
            str(state.get("validation_report", "")),
        ]
    )


def _single_cycle(state: AgentState, brain: BrainProtocol) -> AgentState:
    next_iteration = state["iteration_count"] + 1
    working_state: AgentState = {**state, "iteration_count": next_iteration}
    try:
        working_state["active_role"] = "Single Agent"
        issue_summary = brain.summarize_issue(working_state, "Single Agent")
        working_state["issue_summary"] = issue_summary
        working_state["active_role"] = "Single Agent"
        root_cause = brain.diagnose_root_cause(working_state, "Single Agent")
        working_state["root_cause"] = root_cause
        working_state["active_role"] = "Single Agent"
        patch = brain.propose_patch(working_state, "Single Agent")
    except Exception as exc:
        failed_working: AgentState = {
            "iteration_count": next_iteration,
            "issue_summary": working_state.get("issue_summary", state.get("issue_summary", "")),
            "root_cause": working_state.get("root_cause", state.get("root_cause", "")),
            "current_patch": working_state.get("current_patch", state.get("current_patch", "")),
            "validation_passed": False,
            "validation_report": f"Single Agent execution failed before validation: {exc}",
            "review_recommendation": "revise",
            "review_notes": f"Single Agent could not continue: {exc}",
            "latest_feedback": str(exc),
            "final_status": "failed",
            "messages": working_state.get("messages", state.get("messages", [])),
            "transcript": working_state.get("transcript", state.get("transcript", [])),
            "logs": state["logs"] + [
                build_log_entry("single_agent", {**state, "iteration_count": next_iteration}, f"execution_error={exc}")
            ],
        }
        return failed_working

    working: AgentState = {
        "iteration_count": next_iteration,
        "issue_summary": issue_summary,
        "root_cause": root_cause,
        "llm_calls_used": working_state["llm_calls_used"],
        "messages": working_state.get("messages", state.get("messages", [])),
        "transcript": working_state.get("transcript", []),
    }
    if state.get("execution_mode") == "sandbox":
        try:
            execution_update = _execute_real_patch({**state, **working}, patch, "Single Agent")
        except Exception as exc:
            execution_update = _execution_failure_update({**state, **working}, patch, exc, "Single Agent")
        working.update(execution_update)
    else:
        working["current_patch"] = patch
    validation_state = {**state, **working}
    if state.get("execution_mode") == "sandbox":
        passed, validation_report = _deterministic_validate(validation_state, "Single Agent")
    else:
        try:
            passed, validation_report = brain.validate(validation_state, "Single Agent")
        except Exception as exc:
            passed = False
            validation_report = f"Single Agent could not complete validation: {exc}"
    working["validation_passed"] = passed
    working["validation_report"] = validation_report
    working["llm_calls_used"] = validation_state["llm_calls_used"]
    working["messages"] = validation_state.get("messages", working.get("messages", []))
    working["transcript"] = validation_state.get("transcript", working.get("transcript", []))
    review_state = {**state, **working}
    if state.get("execution_mode") == "sandbox":
        recommendation, review_notes = _deterministic_review(review_state, "Single Agent")
    else:
        try:
            recommendation, review_notes = brain.review(review_state, "Single Agent")
        except Exception as exc:
            recommendation, review_notes = "revise", f"Single Agent could not complete review: {exc}"
    working["review_recommendation"] = recommendation
    working["review_notes"] = review_notes
    working["llm_calls_used"] = review_state["llm_calls_used"]
    working["messages"] = review_state.get("messages", working.get("messages", []))
    working["transcript"] = review_state.get("transcript", working.get("transcript", []))

    success = passed and recommendation == "accept"
    budget_exceeded = state["max_llm_calls"] > 0 and working["llm_calls_used"] >= state["max_llm_calls"]
    exceeded = (
        next_iteration >= state["max_iterations"]
        or state["revision_count"] >= state["max_revision_rounds"]
        or budget_exceeded
    )

    if success:
        working["final_status"] = "success"
        working["latest_feedback"] = ""
    elif exceeded:
        working["final_status"] = "failed"
        working["latest_feedback"] = review_notes if not passed else validation_report
    else:
        working["final_status"] = "in_progress"
        working["revision_count"] = state["revision_count"] + 1
        working["latest_feedback"] = f"{validation_report} {review_notes}"

    log_message = (
        f"validation={'pass' if passed else 'fail'}; "
        f"review={recommendation}; status={working['final_status']}"
    )
    working["logs"] = state["logs"] + [build_log_entry("single_agent", {**state, **working}, log_message)]
    return working


def _coordinator(state: AgentState, brain: BrainProtocol) -> AgentState:
    working_state: AgentState = {**state}
    try:
        working_state["active_role"] = "Coordinator"
        coordinator_plan = brain.coordinator_plan(working_state)
        log_message = "Prepared plan and delegated to analyst."
    except Exception as exc:
        coordinator_plan = f"Coordinator failed to prepare plan: {exc}"
        log_message = f"coordination_error={exc}"
    _append_message(
        working_state,
        sender="Coordinator",
        recipient="all",
        kind="status",
        content=coordinator_plan,
    )
    update: AgentState = {
        "iteration_count": state["iteration_count"],
        "coordinator_plan": coordinator_plan,
        "llm_calls_used": working_state["llm_calls_used"],
        "messages": working_state.get("messages", state.get("messages", [])),
        "transcript": working_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [build_log_entry("coordinator", state, log_message)],
    }
    return update


def _analyst(state: AgentState, brain: BrainProtocol) -> AgentState:
    next_iteration = state["iteration_count"] + 1
    working_state: AgentState = {**state, "iteration_count": next_iteration}
    try:
        working_state["active_role"] = "Analyst"
        issue_summary = brain.summarize_issue(working_state, "Analyst")
        working_state["issue_summary"] = issue_summary
        working_state["active_role"] = "Analyst"
        diagnosis = brain.diagnose_root_cause(working_state, "Analyst")
        working_state["root_cause"] = diagnosis
    except Exception as exc:
        return {
            "iteration_count": next_iteration,
            "issue_summary": working_state.get("issue_summary", state.get("issue_summary", "")),
            "root_cause": state.get("root_cause", ""),
            "current_patch": state.get("current_patch", ""),
            "validation_passed": False,
            "validation_report": f"Analyst could not complete issue analysis: {exc}",
            "test_returncode": -1,
            "test_stdout": "",
            "test_stderr": f"Analyst failure: {exc}",
            "llm_calls_used": working_state["llm_calls_used"],
            "messages": working_state.get("messages", state.get("messages", [])),
            "transcript": working_state.get("transcript", state.get("transcript", [])),
            "logs": state["logs"] + [
                build_log_entry("analyst", {**state, "iteration_count": next_iteration}, f"analyst_error={exc}")
            ],
        }
    _append_message(
        working_state,
        sender="Analyst",
        recipient="all",
        kind="status",
        content=diagnosis,
    )
    return {
        "iteration_count": next_iteration,
        "issue_summary": issue_summary,
        "root_cause": diagnosis,
        "llm_calls_used": working_state["llm_calls_used"],
        "messages": working_state.get("messages", state.get("messages", [])),
        "transcript": working_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [
            build_log_entry("analyst", {**state, "iteration_count": next_iteration}, "Prepared issue summary and root-cause analysis.")
        ],
    }


def _engineer(state: AgentState, brain: BrainProtocol) -> AgentState:
    working_state: AgentState = {**state}
    _role_question_and_answer(working_state, "Engineer")
    try:
        working_state["active_role"] = "Engineer"
        patch = brain.propose_patch(working_state, "Engineer")
    except Exception as exc:
        return {
            "root_cause": state.get("root_cause", ""),
            "current_patch": state.get("current_patch", ""),
            "validation_passed": False,
            "validation_report": f"Engineer could not produce a patch: {exc}",
            "test_returncode": -1,
            "test_stdout": "",
            "test_stderr": f"Engineer failure: {exc}",
            "llm_calls_used": working_state["llm_calls_used"],
            "messages": working_state.get("messages", state.get("messages", [])),
            "transcript": working_state.get("transcript", state.get("transcript", [])),
            "logs": state["logs"] + [
                build_log_entry("engineer", state, f"engineer_error={exc}")
            ],
        }
    update: AgentState = {
        "llm_calls_used": working_state["llm_calls_used"],
        "messages": working_state.get("messages", state.get("messages", [])),
        "transcript": working_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [
            build_log_entry("engineer", state, "Prepared patch proposal from the analyst handoff.")
        ],
    }
    if state.get("execution_mode") == "sandbox":
        try:
            update.update(_execute_real_patch({**state, **update}, patch, "Engineer"))
        except Exception as exc:
            update.update(_execution_failure_update({**state, **update}, patch, exc, "Engineer"))
    else:
        update["current_patch"] = patch
    return update


def _tester(state: AgentState, brain: BrainProtocol) -> AgentState:
    working_state: AgentState = {**state}
    _role_question_and_answer(working_state, "Tester / QA")
    try:
        if state.get("execution_mode") == "sandbox":
            passed, report = _deterministic_validate(working_state, "Tester / QA")
        else:
            working_state["active_role"] = "Tester / QA"
            passed, report = brain.validate(working_state, "Tester / QA")
    except Exception as exc:
        passed = False
        report = f"Tester could not complete validation: {exc}"
    return {
        "validation_passed": passed,
        "validation_report": report,
        "llm_calls_used": working_state["llm_calls_used"],
        "messages": working_state.get("messages", state.get("messages", [])),
        "transcript": working_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [
            build_log_entry("tester", state, f"Validation {'passed' if passed else 'failed'}.")
        ],
    }


def _reviewer(state: AgentState, brain: BrainProtocol) -> AgentState:
    working_state: AgentState = {**state}
    _role_question_and_answer(working_state, "Reviewer")
    try:
        if state.get("execution_mode") == "sandbox":
            recommendation, notes = _deterministic_review(working_state, "Reviewer")
        else:
            working_state["active_role"] = "Reviewer"
            recommendation, notes = brain.review(working_state, "Reviewer")
    except Exception as exc:
        recommendation, notes = "revise", f"Reviewer could not complete review: {exc}"
    return {
        "review_recommendation": recommendation,
        "review_notes": notes,
        "llm_calls_used": working_state["llm_calls_used"],
        "messages": working_state.get("messages", state.get("messages", [])),
        "transcript": working_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [
            build_log_entry("reviewer", state, f"Review recommendation={recommendation}.")
        ],
    }


def _run_engineer_branch(
    state: AgentState,
    engineer_brain: BrainProtocol,
    tester_brain: BrainProtocol,
    reviewer_brain: BrainProtocol,
    branch_index: int,
) -> dict[str, Any]:
    branch_id = f"engineer-{branch_index + 1}"
    branch_state: AgentState = {
        **state,
        "branch_id": branch_id,
        "selected_branch_id": "",
        "branch_results": [],
        "logs": [],
        "transcript": [],
        "llm_calls_used": 0,
        "messages": list(state.get("messages", [])),
    }
    if state.get("execution_mode") == "sandbox":
        branch_workspace = clone_workspace(state["base_workspace_path"], branch_id)
        repo_paths = state["editable_files"] + state["readonly_files"]
        branch_state["workspace_path"] = branch_workspace
        branch_state["repo_context"] = load_existing_file_bundle(branch_workspace, repo_paths)
    engineer_update = _engineer(branch_state, engineer_brain)
    candidate_state: AgentState = {**branch_state, **engineer_update}
    tester_update = _tester(candidate_state, tester_brain)
    candidate_state.update(tester_update)
    reviewer_update = _reviewer(candidate_state, reviewer_brain)
    candidate_state.update(reviewer_update)
    candidate_state["branch_id"] = branch_id
    candidate_state["logs"] = candidate_state.get("logs", [])
    candidate_state["transcript"] = candidate_state.get("transcript", [])
    return {
        "branch_id": branch_id,
        "workspace_path": candidate_state.get("workspace_path", ""),
        "llm_calls_used": candidate_state.get("llm_calls_used", 0),
        "current_patch": candidate_state.get("current_patch", ""),
        "patch_summary": candidate_state.get("patch_summary", ""),
        "changed_files": candidate_state.get("changed_files", []),
        "validation_passed": candidate_state.get("validation_passed", False),
        "validation_report": candidate_state.get("validation_report", ""),
        "review_recommendation": candidate_state.get("review_recommendation", "revise"),
        "review_notes": candidate_state.get("review_notes", ""),
        "test_returncode": candidate_state.get("test_returncode"),
        "test_stdout": candidate_state.get("test_stdout", ""),
        "test_stderr": candidate_state.get("test_stderr", ""),
        "messages": candidate_state.get("messages", []),
        "logs": candidate_state.get("logs", []),
        "transcript": candidate_state.get("transcript", []),
    }


def _engineer_fanout(state: AgentState, worker_brains: dict[str, Any]) -> AgentState:
    engineer_brains = worker_brains["engineers"]
    with ThreadPoolExecutor(max_workers=len(engineer_brains)) as executor:
        futures = [
            executor.submit(
                _run_engineer_branch,
                state,
                engineer_brain,
                worker_brains["tester"],
                worker_brains["reviewer"],
                index,
            )
            for index, engineer_brain in enumerate(engineer_brains)
        ]
        branch_results = [future.result() for future in futures]

    branch_results.sort(key=lambda item: item["branch_id"])
    selected_branch = _select_branch_result(branch_results)
    llm_calls_used = state.get("llm_calls_used", 0) + sum(branch.get("llm_calls_used", 0) for branch in branch_results)
    merged_messages = _merge_messages(
        state.get("messages", []),
        *[branch.get("messages", []) for branch in branch_results],
    )
    fanout_state: AgentState = {**state}
    append_transcript_entry(
        fanout_state,
        role="Coordinator",
        phase="engineer_fanout",
        kind="event",
        message=f"Ran {len(branch_results)} engineer branches concurrently and selected {selected_branch.get('branch_id', 'no branch')}.",
        extra={
            "engineer_worker_count": len(branch_results),
            "selected_branch_id": selected_branch.get("branch_id", ""),
        },
    )
    _append_message(
        fanout_state,
        sender="Coordinator",
        recipient="all",
        kind="decision",
        content=f"Collected {len(branch_results)} branch results and selected {selected_branch.get('branch_id', 'no branch')}.",
    )
    return {
        "engineer_worker_count": len(branch_results),
        "branch_results": branch_results,
        "selected_branch_id": selected_branch.get("branch_id", ""),
        "current_patch": selected_branch.get("current_patch", ""),
        "patch_summary": selected_branch.get("patch_summary", ""),
        "changed_files": selected_branch.get("changed_files", []),
        "validation_passed": selected_branch.get("validation_passed", False),
        "validation_report": selected_branch.get("validation_report", "No engineer branch produced a usable result."),
        "review_recommendation": selected_branch.get("review_recommendation", "revise"),
        "review_notes": selected_branch.get("review_notes", "No engineer branch produced a reviewable result."),
        "test_returncode": selected_branch.get("test_returncode"),
        "test_stdout": selected_branch.get("test_stdout", ""),
        "test_stderr": selected_branch.get("test_stderr", ""),
        "llm_calls_used": llm_calls_used,
        "messages": _merge_messages(merged_messages, fanout_state.get("messages", [])),
        "transcript": fanout_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [build_log_entry("engineer_fanout", state, f"Ran {len(branch_results)} engineer branches concurrently.")],
    }


def _coordinator_decide(state: AgentState) -> AgentState:
    success = state["validation_passed"] and state["review_recommendation"] == "accept"
    budget_exceeded = state["max_llm_calls"] > 0 and state["llm_calls_used"] >= state["max_llm_calls"]
    signature = _progress_signature(state)
    repeated_no_progress = not success and state.get("last_progress_signature") == signature
    no_progress_count = state.get("no_progress_count", 0) + 1 if repeated_no_progress else 0
    stalled_out = no_progress_count >= 1
    exceeded = (
        state["iteration_count"] >= state["max_iterations"]
        or state["revision_count"] >= state["max_revision_rounds"]
        or budget_exceeded
        or stalled_out
    )

    if success:
        status: Literal["success", "failed", "in_progress"] = "success"
        revision_count = state["revision_count"]
        latest_feedback = ""
    elif exceeded:
        status = "failed"
        revision_count = state["revision_count"]
        if stalled_out:
            latest_feedback = "Coordinator can't figure this out after repeated no-progress revisions."
        else:
            latest_feedback = f"{state['validation_report']} {state['review_notes']}"
    else:
        status = "in_progress"
        revision_count = state["revision_count"] + 1
        latest_feedback = f"{state['validation_report']} {state['review_notes']}"

    decision_state: AgentState = {**state}
    append_transcript_entry(
        decision_state,
        role="Coordinator",
        phase="decision",
        kind="event",
        message=(
            "Decision made after review: failed because the workflow could not figure this out."
            if stalled_out
            else f"Decision made after review: {status}."
        ),
        extra={
            "validation_passed": state["validation_passed"],
            "review_recommendation": state["review_recommendation"],
            "no_progress_count": no_progress_count,
        },
    )
    _append_message(
        decision_state,
        sender="Coordinator",
        recipient="all",
        kind="decision",
        content=(
            "Stopping the run because repeated revisions produced no progress."
            if stalled_out
            else f"Coordinator decision: {status}."
        ),
    )
    return {
        "final_status": status,
        "revision_count": revision_count,
        "latest_feedback": latest_feedback,
        "last_progress_signature": signature,
        "no_progress_count": no_progress_count,
        "llm_calls_used": state["llm_calls_used"],
        "messages": decision_state.get("messages", state.get("messages", [])),
        "transcript": decision_state.get("transcript", state.get("transcript", [])),
        "logs": state["logs"] + [
            build_log_entry(
                "coordinator",
                state,
                "Decision made: failed_no_progress."
                if stalled_out
                else f"Decision made: {status}.",
            )
        ],
    }


def _single_route(state: AgentState) -> str:
    return END if state["final_status"] in {"success", "failed"} else "single_cycle"


def _multi_route(state: AgentState) -> str:
    return END if state["final_status"] in {"success", "failed"} else "coordinator"


def build_single_graph(brain: BrainProtocol):
    graph = StateGraph(AgentState)
    graph.add_node("single_cycle", lambda state: _single_cycle(state, brain))
    graph.add_edge(START, "single_cycle")
    graph.add_conditional_edges("single_cycle", _single_route)
    return graph.compile()


def build_multi_graph(worker_brains: dict[str, Any]):
    graph = StateGraph(AgentState)
    graph.add_node("coordinator", lambda state: _coordinator(state, worker_brains["coordinator"]))
    graph.add_node("analyst", lambda state: _analyst(state, worker_brains["analyst"]))
    graph.add_node("engineer_fanout", lambda state: _engineer_fanout(state, worker_brains))
    graph.add_node("coordinator_decide", _coordinator_decide)
    graph.add_edge(START, "coordinator")
    graph.add_edge("coordinator", "analyst")
    graph.add_edge("analyst", "engineer_fanout")
    graph.add_edge("engineer_fanout", "coordinator_decide")
    graph.add_conditional_edges("coordinator_decide", _multi_route)
    return graph.compile()


def run_architecture(
    architecture: Literal["single", "multi"],
    task: TaskSpec | None = None,
    task_id: str | None = None,
) -> AgentState:
    if task is None:
        if task_id is None:
            raise ValueError("Either task or task_id must be provided.")
        task = get_task(task_id)

    config = load_config()
    max_llm_calls = config.max_llm_calls if architecture == "single" else config.multi_max_llm_calls
    initial_state = build_initial_state(
        task,
        architecture,
        max_iterations=config.max_iterations,
        max_revision_rounds=config.max_revision_rounds,
        max_llm_calls=max_llm_calls,
    )
    initial_state.update(_prepare_execution_state(task, initial_state))
    preflight_failure = _run_harness_preflight(task, initial_state)
    if preflight_failure is not None:
        final_state = {**initial_state, **preflight_failure}
        final_state["metrics"] = {
            "latency_seconds": 0.0,
            "iterations": final_state["iteration_count"],
            "revision_count": final_state["revision_count"],
            "success": False,
            "llm_calls_used": final_state["llm_calls_used"],
            "max_llm_calls": final_state["max_llm_calls"],
            "test_returncode": final_state.get("test_returncode"),
            "simulated_cost_units": 0,
        }
        return final_state
    if architecture == "single":
        graph = build_single_graph(build_brain(config))
    else:
        initial_state["engineer_worker_count"] = max(config.multi_engineer_workers, 1)
        graph = build_multi_graph(_build_multi_worker_brains(config))

    started = perf_counter()
    final_state = graph.invoke(initial_state)
    elapsed = perf_counter() - started
    final_state["metrics"] = {
        "latency_seconds": round(elapsed, 6),
        "iterations": final_state["iteration_count"],
        "revision_count": final_state["revision_count"],
        "success": final_state["final_status"] == "success",
        "llm_calls_used": final_state["llm_calls_used"],
        "max_llm_calls": final_state["max_llm_calls"],
        "test_returncode": final_state.get("test_returncode"),
        "simulated_cost_units": final_state["iteration_count"] * (1 if architecture == "single" else 2),
    }
    return final_state


def compare_architectures(task_id: str) -> dict[str, AgentState]:
    task = get_task(task_id)
    return {
        "single": run_architecture("single", task=task),
        "multi": run_architecture("multi", task=task),
    }
