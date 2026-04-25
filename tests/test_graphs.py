"""Unit tests for the graph orchestration layer.

These tests use synthetic, in-memory tasks and a stub brain so they run
without the real benchmark fixtures or any LLM API calls.
"""

from __future__ import annotations

import os
import unittest

os.environ["AGENTIC_MODE"] = "deterministic"

from agentic_research.graphs import _single_cycle
from agentic_research.state import build_initial_state


class _ReviewFailingBrain:
    """Stub brain that succeeds at every phase except review, which raises."""

    def summarize_issue(self, state, role):
        return "summary"

    def diagnose_root_cause(self, state, role):
        return "root cause"

    def propose_patch(self, state, role, strategy=""):
        return "patch proposal"

    def validate(self, state, role):
        state["llm_calls_used"] = state.get("llm_calls_used", 0) + 1
        return True, "validation passed"

    def review(self, state, role):
        state["llm_calls_used"] = state.get("llm_calls_used", 0) + 1
        raise ValueError("bad json")


class GraphTests(unittest.TestCase):
    def test_single_cycle_handles_review_exception_without_crashing(self) -> None:
        proposal_task = {
            "id": "test-review-exception",
            "title": "Test review exception handling",
            "repository": "local/test",
            "description": "A minimal proposal-mode task for testing.",
            "difficulty": "easy",
            "constraints": ["Keep it simple."],
            "acceptance_keywords": ["patch proposal"],
            "validation_instructions": "Validation passes when the patch contains the keywords.",
        }
        state = build_initial_state(proposal_task, architecture="single", max_llm_calls=12)
        result = _single_cycle(state, _ReviewFailingBrain())

        self.assertEqual(result["final_status"], "in_progress")
        self.assertEqual(result["review_recommendation"], "revise")
        self.assertIn("could not complete review", result["review_notes"].lower())
        self.assertEqual(result["llm_calls_used"], 2)


if __name__ == "__main__":
    unittest.main()
