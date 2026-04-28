from __future__ import annotations

from typing import Any

from .prompts import (
    coordinator_plan_prompt,
    diagnose_prompt,
    patch_prompt,
    review_prompt,
    summarize_prompt,
    validation_prompt,
)
from .state import ReviewRecommendation
from .transcript import append_transcript_entry


class DeterministicResearchBrain:
    """Local deterministic simulator for the first runnable prototype."""

    # Returns a canned summary string without calling any LLM.
    def summarize_issue(self, state: dict[str, Any], role: str) -> str:
        constraints = "; ".join(state["constraints"])
        response = (
            f"{role} summary: {state['title']} in {state['repository']}. "
            f"Difficulty={state['difficulty']}. Constraints: {constraints}"
        )
        append_transcript_entry(
            state,
            role=role,
            phase="summarize_issue",
            kind="llm",
            prompt=summarize_prompt(state, role),
            response=response,
        )
        return response

    def coordinator_plan(self, state: dict[str, Any]) -> str:
        response = (
            "Coordinator plan: delegate issue analysis to the analyst, hand the root cause to the engineer, "
            "then require tester validation and reviewer acceptance before shipping."
        )
        append_transcript_entry(
            state,
            role="Coordinator",
            phase="plan",
            kind="llm",
            prompt=coordinator_plan_prompt(state),
            response=response,
        )
        return response

    def diagnose_root_cause(self, state: dict[str, Any], role: str) -> str:
        difficulty_note = {
            "easy": "The bug is likely local and behavior-driven.",
            "medium": "The bug likely crosses a small module boundary.",
            "hard": "The bug likely involves state handling and report semantics.",
        }[state["difficulty"]]
        response = f"{role} diagnosis: {difficulty_note}"
        append_transcript_entry(
            state,
            role=role,
            phase="diagnose_root_cause",
            kind="llm",
            prompt=diagnose_prompt(state, role),
            response=response,
        )
        return response

    def propose_patch(self, state: dict[str, Any], role: str, strategy: str = "") -> str:
        keywords = list(state["acceptance_keywords"])
        revision = state["revision_count"]
        difficulty = state["difficulty"]

        # Deliberately omit one keyword on the first attempt for harder tasks
        # so the revision loop gets exercised during testing.
        if role == "Single Agent":
            if difficulty in {"medium", "hard"} and revision == 0 and len(keywords) > 1:
                included = keywords[:-1]
            else:
                included = keywords
        else:
            if difficulty == "hard" and revision == 0 and len(keywords) > 2:
                included = keywords[:-1]
            else:
                included = keywords

        bullets = "\n".join(f"- address {item}" for item in included)
        feedback = state["latest_feedback"]
        feedback_line = f"\nFeedback addressed: {feedback}" if feedback else ""
        response = (
            f"{role} patch proposal for '{state['title']}':\n"
            f"{bullets}\n"
            "- update tests to capture the regression"
            f"{feedback_line}"
        )
        append_transcript_entry(
            state,
            role=role,
            phase="propose_patch",
            kind="llm",
            prompt=patch_prompt(state, role),
            response=response,
        )
        return response

    def validate(self, state: dict[str, Any], role: str) -> tuple[bool, str]:
        if state.get("execution_mode") == "sandbox":
            passed = state.get("test_returncode", 1) == 0
            if passed:
                report = (
                    f"{role} validation passed. Real test command exited with code 0 for "
                    f"{', '.join(state.get('changed_files', [])) or 'no changed files'}."
                )
                append_transcript_entry(
                    state,
                    role=role,
                    phase="validate",
                    kind="llm",
                    prompt=validation_prompt(state, role),
                    response=json_string({"passed": True, "report": report}),
                )
                return True, report
            report = (
                f"{role} validation failed. Real test command exited with code "
                f"{state.get('test_returncode')}.\nSTDOUT:\n{state.get('test_stdout', '')}\n"
                f"STDERR:\n{state.get('test_stderr', '')}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="validate",
                kind="llm",
                prompt=validation_prompt(state, role),
                response=json_string({"passed": False, "report": report}),
            )
            return False, report

        patch = state["current_patch"].lower()
        missing = [item for item in state["acceptance_keywords"] if item.lower() not in patch]
        if missing:
            report = (
                f"{role} validation failed. Missing acceptance keywords: {', '.join(missing)}. "
                f"Validation rule: {state['validation_instructions']}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="validate",
                kind="llm",
                prompt=validation_prompt(state, role),
                response=json_string({"passed": False, "report": report}),
            )
            return False, report

        report = (
            f"{role} validation passed. Patch covers {', '.join(state['acceptance_keywords'])} "
            "and includes an explicit regression-testing story."
        )
        append_transcript_entry(
            state,
            role=role,
            phase="validate",
            kind="llm",
            prompt=validation_prompt(state, role),
            response=json_string({"passed": True, "report": report}),
        )
        return True, report

    def review(self, state: dict[str, Any], role: str) -> tuple[ReviewRecommendation, str]:
        if state.get("execution_mode") == "sandbox":
            if not state["validation_passed"]:
                notes = f"{role} review: test execution is still failing."
                append_transcript_entry(
                    state,
                    role=role,
                    phase="review",
                    kind="llm",
                    prompt=review_prompt(state, role),
                    response=json_string({"recommendation": "revise", "notes": notes}),
                )
                return "revise", notes
            if not state.get("changed_files"):
                notes = f"{role} review: no files were changed."
                append_transcript_entry(
                    state,
                    role=role,
                    phase="review",
                    kind="llm",
                    prompt=review_prompt(state, role),
                    response=json_string({"recommendation": "revise", "notes": notes}),
                )
                return "revise", notes
            notes = (
                f"{role} review: patch updated {', '.join(state['changed_files'])} and the real test "
                "suite passed."
            )
            append_transcript_entry(
                state,
                role=role,
                phase="review",
                kind="llm",
                prompt=review_prompt(state, role),
                response=json_string({"recommendation": "accept", "notes": notes}),
            )
            return "accept", notes

        if not state["validation_passed"]:
            notes = f"{role} review: reject until validation passes."
            append_transcript_entry(
                state,
                role=role,
                phase="review",
                kind="llm",
                prompt=review_prompt(state, role),
                response=json_string({"recommendation": "revise", "notes": notes}),
            )
            return "revise", notes

        patch = state["current_patch"].lower()
        if "update tests" not in patch and "regression test" not in patch:
            notes = f"{role} review: patch still needs explicit regression-test coverage."
            append_transcript_entry(
                state,
                role=role,
                phase="review",
                kind="llm",
                prompt=review_prompt(state, role),
                response=json_string({"recommendation": "revise", "notes": notes}),
            )
            return "revise", notes

        notes = f"{role} review: patch is acceptable with bounded regression risk."
        append_transcript_entry(
            state,
            role=role,
            phase="review",
            kind="llm",
            prompt=review_prompt(state, role),
            response=json_string({"recommendation": "accept", "notes": notes}),
        )
        return "accept", notes

    def coordinator_decision(self, state: dict[str, Any], branch_results: list[dict[str, Any]]) -> tuple[str, str]:
        if not branch_results:
            return "", "No branches to evaluate."
        # Sort branches: prefer ones that both passed validation and got accepted by review.
        def _sort_key(b: dict[str, Any]) -> tuple[int, int, int, str]:
            return (
                0 if b.get("validation_passed") and b.get("review_recommendation") == "accept" else 1,
                0 if b.get("validation_passed") else 1,
                b.get("test_returncode", 0) if b.get("test_returncode") is not None else 0,
                b.get("branch_id", ""),
            )
        best = sorted(branch_results, key=_sort_key)[0]
        return best.get("branch_id", ""), "Selected by validation outcome and review recommendation."


def build_log_entry(role: str, state: dict[str, Any], message: str) -> dict[str, Any]:
    payload = {
        "role": role,
        "iteration": state["iteration_count"],
        "revision": state["revision_count"],
        "message": message,
    }
    if state.get("branch_id"):
        payload["branch_id"] = state["branch_id"]
    return payload


def json_string(value: str) -> str:
    import json

    return json.dumps(value)
