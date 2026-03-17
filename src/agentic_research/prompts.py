from __future__ import annotations

from textwrap import dedent
from typing import Any


def _engineering_standards() -> str:
    return dedent(
        """
        Engineering standards:
        - Operate like a senior engineer on a high-quality product team.
        - Be precise, skeptical, and implementation-focused.
        - Do not hand-wave. Tie claims to the code, the task, or the test output.
        - Keep scope tight. Fix the issue without broad redesign unless the task requires it.
        - Prefer the smallest correct change that will make the real test pass.
        - If prior feedback indicates a failed approach, do not repeat it.
        """
    ).strip()


def _task_block(state: dict[str, Any]) -> str:
    constraints = "\n".join(f"- {item}" for item in state["constraints"])
    keywords = ", ".join(state["acceptance_keywords"])
    feedback = state.get("latest_feedback") or "None"
    return dedent(
        f"""
        Task ID: {state['task_id']}
        Title: {state['title']}
        Repository: {state['repository']}
        Difficulty: {state['difficulty']}
        Description: {state['description']}
        Constraints:
        {constraints}
        Acceptance keywords: {keywords}
        Validation instructions: {state['validation_instructions']}
        Latest feedback: {feedback}
        {_team_messages_block(state)}
        """
    ).strip()


def _repo_context_block(state: dict[str, Any]) -> str:
    if not state.get("repo_context"):
        return ""
    sections = []
    for path, content in state["repo_context"].items():
        sections.append(f"FILE: {path}\n```python\n{content}\n```")
    return "\n\n".join(sections)


def _message_scope_matches(state: dict[str, Any], message: dict[str, Any]) -> bool:
    message_branch = message.get("branch_id") or ""
    current_branch = state.get("branch_id") or ""
    if current_branch:
        return message_branch in {"", current_branch}
    return message_branch == ""


def _team_messages_block(state: dict[str, Any]) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "Relevant team messages: None"
    role = state.get("active_role", "")
    relevant: list[dict[str, Any]] = []
    for item in messages:
        if not _message_scope_matches(state, item):
            continue
        recipient = item.get("recipient", "")
        if recipient in {"", "all", role} or item.get("sender") == role:
            relevant.append(item)
    relevant = relevant[-8:]
    if not relevant:
        return "Relevant team messages: None"
    lines = []
    for item in relevant:
        branch = f" [{item['branch_id']}]" if item.get("branch_id") else ""
        status = f" ({item.get('status', 'sent')})" if item.get("kind") == "question" else ""
        lines.append(
            f"- {item.get('kind', 'message').upper()}{branch}: {item.get('sender', 'Unknown')} -> "
            f"{item.get('recipient', 'all')}: {item.get('content', '')}{status}"
        )
    return "Relevant team messages:\n" + "\n".join(lines)


def summarize_prompt(state: dict[str, Any], role: str) -> str:
    return dedent(
        f"""
        You are the {role} on a FAANG-style software engineering team.
        Your job is to brief the team on the issue before implementation starts.

        Requirements:
        - Produce a concise issue summary in 2-4 sentences.
        - State the actual broken behavior.
        - State the likely area of code involved.
        - Mention the most important constraint or risk.
        - Do not propose a solution yet.

        {_engineering_standards()}

        {_task_block(state)}
        """
    ).strip()


def coordinator_plan_prompt(state: dict[str, Any]) -> str:
    return dedent(
        f"""
        You are the Coordinator / Tech Lead on a strong product infrastructure team.
        Your responsibility is to break the task down clearly, avoid wasted work, and
        drive the team toward a correct, test-backed fix.

        Requirements:
        - Produce a short high-signal plan in at most 5 sentences.
        - Say what the engineer should verify in code first.
        - Say what the tester must prove before the patch can be accepted.
        - Say what the reviewer should watch for.
        - Keep the plan tightly scoped to the stated issue.

        {_engineering_standards()}

        {_task_block(state)}
        """
    ).strip()


def diagnose_prompt(state: dict[str, Any], role: str) -> str:
    return dedent(
        f"""
        You are the {role} on a FAANG-style engineering team.
        Your responsibility is root-cause analysis, not broad brainstorming.

        Requirements:
        - Explain the likely root cause in 2-4 sentences.
        - Be concrete about the code path or behavior involved.
        - Distinguish between symptom and root cause.
        - Keep the diagnosis bounded to the task.
        - Do not propose unrelated cleanup or redesign.

        {_engineering_standards()}

        {_task_block(state)}
        """
    ).strip()


def patch_prompt(state: dict[str, Any], role: str) -> str:
    if state.get("execution_mode") == "sandbox":
        editable = ", ".join(state.get("editable_files", []))
        return dedent(
            f"""
            You are the {role} on a FAANG-style engineering team.
            You own implementation. You must produce an actual patch for a real repository sandbox.

            Output JSON only. Use one of these exact shapes:
            {{
              "summary": "short patch summary",
              "files": {{
                "relative/path.py": "full new file content"
              }}
            }}

            or

            {{
              "summary": "short patch summary",
              "edits": [
                {{
                  "path": "relative/path.py",
                  "find": "exact existing text",
                  "replace": "replacement text"
                }}
              ]
            }}

            Rules:
            - Only edit these files: {editable}
            - For very large files, prefer "edits" with exact find/replace blocks.
            - If you use "files", return full replacement content for each edited file.
            - Keep the patch minimal and bounded.
            - Use the latest feedback if present.
            - Make the real test command pass.
            - Do not describe a fix; implement it.
            - Do not invent APIs, files, or behavior outside the provided repo context.
            - If feedback says a previous patch was wrong, directly correct that mistake.
            - Prefer preserving existing semantics for unaffected cases.

            Implementation expectations:
            - Change only what is necessary for the task.
            - Match the style of the surrounding code.
            - Avoid placeholder comments or TODOs.
            - If an exact targeted edit is possible, prefer it over broad rewrites.

            {_engineering_standards()}

            {_task_block(state)}
            Current root cause: {state.get('root_cause', '')}
            Repository context:
            {_repo_context_block(state)}
            """
        ).strip()

    return dedent(
        f"""
        You are the {role} on a FAANG-style engineering team.
        Produce a patch proposal as a concise engineering note.

        Requirements:
        - Mention the key behavior being fixed.
        - Mention how tests should be updated.
        - If feedback exists, explicitly address it.
        - Keep the scope bounded.

        {_engineering_standards()}

        {_task_block(state)}
        Current root cause: {state.get('root_cause', '')}
        """
    ).strip()


def validation_prompt(state: dict[str, Any], role: str) -> str:
    if state.get("execution_mode") == "sandbox":
        return dedent(
            f"""
            You are the {role} on a FAANG-style QA / validation team.
            Your job is to judge the patch based on actual execution results, not optimism.

            Summarize the real test execution result in JSON.
            Respond in JSON with:
            {{
              "passed": true or false,
              "report": "short validation report grounded in the actual test output"
            }}

            Validation rules:
            - Base your answer on the actual test result and output.
            - If the test command failed, `passed` must be false.
            - If patch application failed or no meaningful change happened, say so clearly.
            - Mention the key failing behavior or the key passing evidence.
            - Do not speculate beyond the provided output.

            {_engineering_standards()}

            {_task_block(state)}
            Changed files: {', '.join(state.get('changed_files', [])) or 'None'}
            Test return code: {state.get('test_returncode')}
            Test stdout:
            {state.get('test_stdout', '')}

            Test stderr:
            {state.get('test_stderr', '')}
            """
        ).strip()

    return dedent(
        f"""
        You are the {role} on a FAANG-style QA / validation team.
        Evaluate whether the patch proposal satisfies the validation instructions.

        Respond in JSON with:
        {{
          "passed": true or false,
          "report": "short validation report"
        }}

        {_engineering_standards()}

        {_task_block(state)}
        Patch proposal:
        {state.get('current_patch', '')}
        """
    ).strip()


def review_prompt(state: dict[str, Any], role: str) -> str:
    if state.get("execution_mode") == "sandbox":
        return dedent(
            f"""
            You are the {role} on a FAANG-style code review team.
            Your job is to make a shipping recommendation after implementation and test execution.

            Review the real patch after actual test execution.
            Respond in JSON with:
            {{
              "recommendation": "accept" or "revise",
              "notes": "short review notes grounded in the patch summary and test result"
            }}

            Review rules:
            - Recommend `accept` only if the patch is test-backed and scoped correctly.
            - Recommend `revise` if the patch is wrong, incomplete, risky, or not grounded in the result.
            - Call out specific risk areas such as over-broad edits, repeated failed logic, or mismatch with the task.
            - Keep notes short, direct, and technical.

            {_engineering_standards()}

            {_task_block(state)}
            Patch summary: {state.get('patch_summary', '')}
            Changed files: {', '.join(state.get('changed_files', [])) or 'None'}
            Validation passed: {state.get('validation_passed')}
            Validation report: {state.get('validation_report', '')}
            Test return code: {state.get('test_returncode')}
            """
        ).strip()

    return dedent(
        f"""
        You are the {role} on a FAANG-style code review team.
        Review the patch proposal after validation.

        Respond in JSON with:
        {{
          "recommendation": "accept" or "revise",
          "notes": "short review notes"
        }}

        {_engineering_standards()}

        {_task_block(state)}
        Validation passed: {state.get('validation_passed')}
        Validation report: {state.get('validation_report', '')}
        Patch proposal:
        {state.get('current_patch', '')}
        """
    ).strip()
