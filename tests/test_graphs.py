import os
import unittest

os.environ["AGENTIC_MODE"] = "deterministic"

from agentic_research.graphs import _single_cycle, compare_architectures, run_architecture
from agentic_research.sample_tasks import SAMPLE_TASKS
from agentic_research.state import build_initial_state


class GraphTests(unittest.TestCase):
    def test_single_architecture_completes(self) -> None:
        result = run_architecture("single", task_id="no-color")
        self.assertIn(result["final_status"], {"success", "failed"})
        self.assertGreaterEqual(result["metrics"]["iterations"], 1)
        self.assertTrue(result["transcript"])
        self.assertTrue(any(entry["phase"] == "propose_patch" for entry in result["transcript"]))
        self.assertTrue(any(entry["phase"] == "validate" and entry["kind"] == "deterministic" for entry in result["transcript"]))
        self.assertTrue(result["venv_python"].endswith("/.venv/bin/python"))

    def test_multi_architecture_completes(self) -> None:
        result = run_architecture("multi", task_id="rerun-teardown")
        self.assertIn(result["final_status"], {"success", "failed"})
        self.assertGreaterEqual(result["metrics"]["iterations"], 1)
        self.assertTrue(result["transcript"])
        self.assertTrue(result["messages"])
        self.assertTrue(any(entry["phase"] == "decision" for entry in result["transcript"]))
        self.assertTrue(any(entry["role"] == "Analyst" for entry in result["transcript"]))
        self.assertTrue(any(entry["kind"] == "message" for entry in result["transcript"]))
        self.assertTrue(any(message["kind"] == "question" for message in result["messages"]))
        self.assertTrue(any(message["kind"] == "answer" for message in result["messages"]))
        self.assertEqual(result["engineer_worker_count"], 2)
        self.assertEqual(len(result["branch_results"]), 2)
        self.assertTrue(result["selected_branch_id"])

    def test_multi_architecture_stops_when_stalled(self) -> None:
        result = run_architecture("multi", task_id="rich-alignment")
        if result["final_status"] == "failed":
            self.assertTrue(
                "can't figure this out" in result["latest_feedback"].lower()
                or result.get("no_progress_count", 0) >= 1
            )

    def test_compare_returns_both_architectures(self) -> None:
        comparison = compare_architectures("rich-alignment")
        self.assertEqual(set(comparison), {"single", "multi"})
        self.assertEqual(comparison["single"]["task_id"], "rich-alignment")
        self.assertEqual(comparison["multi"]["task_id"], "rich-alignment")

    def test_click_tasks_use_discovery_style_commands(self) -> None:
        for task_id in ["click-no-color-real", "click-negative-flag-real", "click-class-flag-default-real"]:
            command = SAMPLE_TASKS[task_id]["test_command"]
            self.assertEqual(command[:4], ["python3", "-m", "unittest", "discover"])

    def test_new_fixture_tasks_complete(self) -> None:
        for task_id in ["negative-flag-fixture", "plugin-loader-fixture"]:
            result = run_architecture("single", task_id=task_id)
            self.assertIn(result["final_status"], {"success", "failed"})
            self.assertNotEqual(result["test_returncode"], -3)

    def test_multi_engineer_branches_use_separate_workspaces(self) -> None:
        result = run_architecture("multi", task_id="no-color")
        branch_results = result["branch_results"]
        self.assertEqual(len(branch_results), 2)
        workspace_paths = {branch["workspace_path"] for branch in branch_results}
        self.assertEqual(len(workspace_paths), 2)
        self.assertNotIn(result["workspace_path"], workspace_paths)
        self.assertTrue(all(branch["transcript"] for branch in branch_results))
        self.assertTrue(all(branch["messages"] for branch in branch_results))
        self.assertTrue(
            all(
                any(entry.get("branch_id") == branch["branch_id"] for entry in branch["transcript"])
                for branch in branch_results
            )
        )
        self.assertTrue(
            all(
                any(message.get("branch_id") == branch["branch_id"] for message in branch["messages"])
                for branch in branch_results
            )
        )

    def test_task_preflight_fails_before_agent_execution_for_bad_click_paths(self) -> None:
        result = run_architecture("single", task_id="click-negative-flag-real")
        self.assertEqual(result["final_status"], "failed")
        self.assertEqual(result["metrics"]["iterations"], 0)
        self.assertEqual(result["test_returncode"], -3)
        self.assertIn("task preflight failed", result["validation_report"].lower())

    def test_single_cycle_handles_review_exception_without_crashing(self) -> None:
        class ReviewFailingBrain:
            def summarize_issue(self, state, role):
                return "summary"

            def diagnose_root_cause(self, state, role):
                return "root cause"

            def propose_patch(self, state, role):
                return "patch proposal"

            def validate(self, state, role):
                state["llm_calls_used"] = state.get("llm_calls_used", 0) + 1
                return True, "validation passed"

            def review(self, state, role):
                state["llm_calls_used"] = state.get("llm_calls_used", 0) + 1
                raise ValueError("bad json")

        state = build_initial_state(SAMPLE_TASKS["rich-alignment"], architecture="single", max_llm_calls=12)
        result = _single_cycle(state, ReviewFailingBrain())

        self.assertEqual(result["final_status"], "in_progress")
        self.assertEqual(result["review_recommendation"], "revise")
        self.assertIn("could not complete review", result["review_notes"].lower())
        self.assertEqual(result["llm_calls_used"], 2)


if __name__ == "__main__":
    unittest.main()
