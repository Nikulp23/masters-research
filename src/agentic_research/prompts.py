from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


def _format_feedback(feedback: str) -> str:
    """Render structured feedback (JSON dict) as a readable block, or return as-is."""
    if not feedback:
        return "None"
    try:
        data = json.loads(feedback)
        if isinstance(data, dict):
            lines = []
            if data.get("failed_approach"):
                lines.append(f"Previous patch: {data['failed_approach']}")
            if data.get("specific_error"):
                lines.append(f"Error: {data['specific_error']}")
            if data.get("validation_report"):
                lines.append(f"Validation: {data['validation_report']}")
            if data.get("avoid"):
                lines.append(f"Avoid: {data['avoid']}")
            if data.get("regression_failure"):
                lines.append(f"Regression: {data['regression_failure']}")
            return "\n".join(lines) if lines else feedback
    except (json.JSONDecodeError, TypeError):
        pass
    return feedback


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


def _task_block(state: dict[str, Any], include_variable: bool = True) -> str:
    """Stable task description block.

    When include_variable=False, omits feedback and team messages so the block
    can form a cacheable prefix. Variable data is then appended at the call site.
    """
    constraints = "\n".join(f"- {item}" for item in state["constraints"])
    keywords = ", ".join(state["acceptance_keywords"])
    base = dedent(
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
        """
    ).strip()
    if not include_variable:
        return base
    feedback = state.get("latest_feedback") or "None"
    return base + "\n" + dedent(
        f"""
        Latest feedback: {_format_feedback(feedback)}
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
    k = state.get("transcript_tail_k", 8)
    relevant = relevant[-k:]
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
    # Stable prefix: role + standards + stable task block
    # Variable suffix: feedback + messages
    return dedent(
        f"""
        You are the {role} on a software engineering team.
        Your job is to brief the team on the issue before implementation starts.

        Requirements:
        - Produce a concise issue summary in 2-4 sentences.
        - State the actual broken behavior.
        - State the likely area of code involved.
        - Mention the most important constraint or risk.
        - Do not propose a solution yet.

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Latest feedback: {_format_feedback(state.get('latest_feedback') or 'None')}
        {_team_messages_block(state)}
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

        {_task_block(state, include_variable=False)}

        Latest feedback: {_format_feedback(state.get('latest_feedback') or 'None')}
        {_team_messages_block(state)}
        """
    ).strip()


def diagnose_prompt(state: dict[str, Any], role: str) -> str:
    return dedent(
        f"""
        You are the {role} on an engineering team.
        Your responsibility is root-cause analysis, not broad brainstorming.

        Requirements:
        - Explain the likely root cause in 2-4 sentences.
        - Be concrete about the code path or behavior involved.
        - Distinguish between symptom and root cause.
        - Keep the diagnosis bounded to the task.
        - Do not propose unrelated cleanup or redesign.
        - End your response with exactly two lines in this format (fill in real values):
          Target-File: <relative/path/to/file>
          Target-Function: <function_or_method_name>

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Latest feedback: {_format_feedback(state.get('latest_feedback') or 'None')}
        {_team_messages_block(state)}
        """
    ).strip()


def patch_prompt(state: dict[str, Any], role: str, strategy: str = "") -> str:
    if state.get("execution_mode") == "sandbox":
        editable = ", ".join(state.get("editable_files", []))
        # Stable prefix: role + output format rules + standards + task spec + repo context
        # Variable suffix: root cause + feedback + messages (changes each iteration)
        return dedent(
            f"""
            You are the {role} on an engineering team.
            You own implementation. You must produce an actual patch for a real repository sandbox.

            Output JSON only. Use this exact shape:
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
            - You MUST use the "edits" shape. Do NOT return full file contents under any key.
            - Each "find" string must be SHORT — include only the lines that actually change plus 1-2 lines of surrounding context for uniqueness. Never include whole functions or whole files.
            - If multiple disjoint regions need changing, emit multiple entries in the "edits" array.
            - "find" must match the file byte-for-byte (including whitespace). Do not paraphrase.
            - Keep the total JSON response small enough to fit well under the token limit.
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
            - Keep "find" and "replace" strings as short as possible — include only the lines that change, not entire functions.
            Implementation strategy for this branch: {strategy or "minimal — prefer the smallest correct change that makes the test pass."}

            {_engineering_standards()}

            {_task_block(state, include_variable=False)}
            Repository context:
            {_repo_context_block(state)}

            Current root cause: {state.get('root_cause', '')}
            Latest feedback: {_format_feedback(state.get('latest_feedback') or 'None')}
            {_team_messages_block(state)}
            """
        ).strip()

    return dedent(
        f"""
        You are the {role} on an engineering team.
        Produce a patch proposal as a concise engineering note.

        Requirements:
        - Mention the key behavior being fixed.
        - Mention how tests should be updated.
        - If feedback exists, explicitly address it.
        - Keep the scope bounded.

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Current root cause: {state.get('root_cause', '')}
        Latest feedback: {_format_feedback(state.get('latest_feedback') or 'None')}
        {_team_messages_block(state)}
        """
    ).strip()


def validation_prompt(state: dict[str, Any], role: str) -> str:
    if state.get("execution_mode") == "sandbox":
        # Stable prefix: role + format + rules + standards + task spec
        # Variable suffix: test results (changes every execution)
        return dedent(
            f"""
            You are the {role} on a QA / validation team.
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

            {_task_block(state, include_variable=False)}

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
        You are the {role} on a QA / validation team.
        Evaluate whether the patch proposal satisfies the validation instructions.

        Respond in JSON with:
        {{
          "passed": true or false,
          "report": "short validation report"
        }}

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Patch proposal:
        {state.get('current_patch', '')}
        """
    ).strip()


def review_prompt(state: dict[str, Any], role: str) -> str:
    if state.get("execution_mode") == "sandbox":
        # Stable prefix: role + format + rules + standards + task spec
        # Variable suffix: patch results (changes every execution)
        return dedent(
            f"""
            You are the {role} on a code review team.
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

            {_task_block(state, include_variable=False)}

            Patch summary: {state.get('patch_summary', '')}
            Changed files: {', '.join(state.get('changed_files', [])) or 'None'}
            Validation passed: {state.get('validation_passed')}
            Validation report: {state.get('validation_report', '')}
            Test return code: {state.get('test_returncode')}
            Regression suite passed: {state.get('regression_passed')} (None means no regression command configured)
            Patch diff:
            {(state.get('patch_diff') or '')[:4000]}
            """
        ).strip()

    return dedent(
        f"""
        You are the {role} on a code review team.
        Review the patch proposal after validation.

        Respond in JSON with:
        {{
          "recommendation": "accept" or "revise",
          "notes": "short review notes"
        }}

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Validation passed: {state.get('validation_passed')}
        Validation report: {state.get('validation_report', '')}
        Patch proposal:
        {state.get('current_patch', '')}
        """
    ).strip()


def coordinator_decision_prompt(state: dict[str, Any], branch_results: list[dict[str, Any]]) -> str:
    # Stable prefix: role + rules + format + standards + task spec
    # Variable suffix: branch results (different each fanout)
    branches_block = ""
    for br in branch_results:
        branches_block += f"\n--- {br['branch_id']} ---\n"
        branches_block += f"Validation passed: {br.get('validation_passed', False)}\n"
        branches_block += f"Test return code: {br.get('test_returncode')}\n"
        branches_block += f"Review: {br.get('review_recommendation', 'revise')}\n"
        branches_block += f"Patch summary: {br.get('patch_summary', 'none')}\n"
        branches_block += f"Changed files: {', '.join(br.get('changed_files', [])) or 'none'}\n"
        branches_block += f"Review notes: {br.get('review_notes', 'none')}\n"
    return dedent(
        f"""
        You are the Coordinator selecting the best engineer branch to ship.

        Rules:
        - Prefer branches where validation passed and review recommends accept.
        - If multiple branches passed, prefer the one with the most targeted, minimal change.
        - If no branch passed, select the one most likely to succeed with a revision.

        Respond in JSON only:
        {{
          "selected_branch_id": "engineer-N",
          "reasoning": "one sentence explanation"
        }}

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Branch results:
        {branches_block}
        """
    ).strip()
