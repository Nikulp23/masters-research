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
        Engineering standards (non-negotiable):
        - Operate like a staff engineer at a top-tier infrastructure team. Production code, real users.
        - Every claim must be grounded in the actual code, the task spec, or the real test output. No speculation.
        - Smallest correct change that makes the real test pass. No drive-by refactors, no defensive rewrites of unrelated code.
        - Do not invent APIs, files, parameters, or behaviors that are not visible in the provided repo context.
        - Do not modify test files unless the task explicitly says to. Editable files are an allow-list, not a suggestion.
        - If prior feedback says an approach failed, do not repeat it. Read the failure, update your hypothesis, then act.
        - Prefer preserving existing semantics for cases unrelated to the bug. Backwards-compatibility is a default, not an afterthought.
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
        Brief the team on the issue before any implementation begins. This summary is the
        shared baseline the rest of the workflow will build on, so it must be precise.

        Requirements:
        - 2-4 sentences. No bullet lists, no headers.
        - Sentence 1: the observable broken behavior in concrete terms (what is wrong, what should happen).
        - Sentence 2: the most likely area of code (module / function / file) that owns this behavior.
        - Sentence 3 (optional): the most load-bearing constraint or risk (regression surface, edge case, API contract).
        - Do NOT propose a fix. Do NOT speculate about implementation. Diagnosis happens in the next phase.

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Latest feedback: {_format_feedback(state.get('latest_feedback') or 'None')}
        {_team_messages_block(state)}
        """
    ).strip()


def coordinator_plan_prompt(state: dict[str, Any]) -> str:
    return dedent(
        f"""
        You are the Coordinator / Tech Lead on a top-tier infrastructure team.
        Your job is to point the team at the right code and the right evidence so they don't
        waste a revision round on a wrong hypothesis.

        Requirements:
        - At most 5 sentences. Each sentence must carry signal; no filler.
        - Engineer: name the file or function the engineer should read first, and what to look for there.
        - Tester: state the exact behavior the test must demonstrate before the patch ships (what passes, what would still fail under a wrong fix).
        - Reviewer: name the most likely failure mode for this class of bug (e.g. inverted condition, off-by-one, missing edge case, scope creep).
        - Stay tightly scoped to the stated issue. Do not plan refactors, doc updates, or "while we're here" cleanup.

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
        You own root-cause analysis. The Engineer will write code based on what you produce here,
        so a wrong diagnosis costs the team a full revision round. Be precise.

        Requirements:
        - 2-4 sentences of prose explaining the root cause.
        - Be concrete: name the function, the conditional, the loop, or the call site that misbehaves.
        - Distinguish symptom (what the test observes) from cause (why the code produces that observation).
        - Cite the line or expression that is wrong, and explain what it should do instead in one phrase.
        - Do not propose a multi-file redesign. Do not flag unrelated smells.
        - If the task or repo context is insufficient to be certain, say "uncertain: <reason>" rather than guess.
        - End your response with EXACTLY two lines in this format, with real values, no placeholders:
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
            You own implementation. You will produce a real patch that will be applied to a real
            repository sandbox and validated against a real test command. There is no LLM judge.
            The test runs and either passes or fails. Optimism does not help you.

            Output JSON only. No prose, no markdown, no preamble. Exact shape:
            {{
              "summary": "one short sentence describing the change",
              "edits": [
                {{
                  "path": "relative/path.py",
                  "find": "exact existing text including whitespace",
                  "replace": "replacement text"
                }}
              ]
            }}

            Hard rules (violations cause patch application to fail):
            - Editable file allow-list: {editable}. Editing anything else aborts the run.
            - Use the "edits" shape ONLY. Do not return full file contents under any key.
            - "find" must match the file byte-for-byte, including indentation and trailing whitespace. No paraphrasing, no normalization.
            - Each "find" string is SHORT: only the lines that change plus 1-2 lines of context for uniqueness. Never paste a whole function or file.
            - For multiple disjoint changes, emit multiple entries in the "edits" array. Do not bundle them into one giant find/replace.

            Implementation discipline:
            - Smallest correct change. If a one-line fix works, do not write a five-line fix.
            - Match surrounding style (naming, indentation, idioms). The diff should look like the existing author wrote it.
            - No placeholder comments, no TODOs, no "fixed bug" comments. The git history records the change.
            - Do not modify tests, docs, configs, or unrelated code.
            - Do not invent APIs, modules, or parameters. If the repo context does not show it exists, do not call it.
            - If prior feedback names a failed approach, your patch must directly correct that specific mistake. Do not retry the same fix.

            Implementation strategy for this branch: {strategy or "minimal-surgical — smallest correct change that makes the test pass."}

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
            You are the last gate before this patch ships. Be skeptical. A green test is
            necessary but not sufficient — patches can pass the test by accident, by overfitting
            to the assertion, or by silently breaking adjacent behavior.

            Respond in JSON only:
            {{
              "recommendation": "accept" or "revise",
              "notes": "short technical review notes"
            }}

            Accept criteria (ALL must hold):
            1. Validation passed AND the test return code is 0.
            2. The patch addresses the stated root cause, not just the symptom that triggers the test.
            3. The diff is scoped to the editable file allow-list and stays minimal.
            4. The change does not silently alter behavior for cases unrelated to the bug.
            5. No invented APIs, no placeholder TODOs, no commented-out code, no debug prints.

            Revise if any of the following:
            - The test is failing or the patch did not apply cleanly.
            - The patch overfits the test (e.g. hardcoding a value the test asserts) instead of fixing the cause.
            - Edits stray outside the bug's actual surface area (drive-by refactors, unrelated cleanup).
            - The fix repeats logic the prior feedback already flagged as wrong.
            - The diff weakens an existing invariant or breaks an obvious adjacent case.

            Notes must be short, technical, and specific. Name the file, line, or behavior at issue.

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
        You are the Coordinator selecting which engineer branch to ship from a parallel fanout.
        You see only the post-execution metadata for each branch — the real test already ran.

        Selection priority (apply strictly in this order):
        1. validation_passed == true AND review_recommendation == "accept".
        2. Among (1), prefer the branch with the smallest, most targeted diff (fewer changed files, shorter patch summary).
        3. If no branch satisfies (1), prefer validation_passed == true regardless of review.
        4. If no branch passed validation, select the branch whose review notes describe the failure most precisely — that is the one most likely to recover on a revision.
        5. Break further ties by branch_id (lexicographic) for determinism.

        Respond in JSON only, no prose:
        {{
          "selected_branch_id": "engineer-N",
          "reasoning": "one sentence naming the rule that decided it"
        }}

        {_engineering_standards()}

        {_task_block(state, include_variable=False)}

        Branch results:
        {branches_block}
        """
    ).strip()
