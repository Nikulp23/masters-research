import os
import tempfile
import unittest
from pathlib import Path

os.environ["AGENTIC_MODE"] = "deterministic"

from agentic_research.benchmark import classify_failure, run_benchmark_suite
from agentic_research.site_export import export_site_data


class BenchmarkTests(unittest.TestCase):
    def test_classify_failure_categories(self) -> None:
        self.assertEqual(
            classify_failure(
                {
                    "final_status": "failed",
                    "validation_report": "Tester could not complete validation: LLM call budget exhausted.",
                    "review_notes": "",
                    "test_stderr": "",
                    "current_patch": "{}",
                    "test_returncode": 1,
                }
            ),
            "llm_budget_exhausted",
        )
        self.assertEqual(
            classify_failure(
                {
                    "final_status": "failed",
                    "validation_report": "Task preflight failed before agent execution.",
                    "review_notes": "",
                    "test_stderr": "",
                    "current_patch": "",
                    "test_returncode": -3,
                }
            ),
            "task_preflight_failed",
        )
        self.assertEqual(
            classify_failure(
                {
                    "final_status": "failed",
                    "validation_report": "Harness preflight failed before agent execution.",
                    "review_notes": "",
                    "test_stderr": "ModuleNotFoundError",
                    "current_patch": "",
                    "test_returncode": -2,
                }
            ),
            "harness_preflight_failed",
        )
        self.assertEqual(
            classify_failure(
                {
                    "final_status": "failed",
                    "validation_report": "Patch application failed because payload was not valid JSON.",
                    "review_notes": "",
                    "test_stderr": "",
                    "current_patch": "",
                    "test_returncode": -1,
                }
            ),
            "invalid_patch_payload",
        )

    def test_benchmark_suite_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            suite_dir = os.path.join(tempdir, "suite-test")
            result = run_benchmark_suite(
                task_ids=["no-color"],
                repeats=1,
                architectures=["single", "multi"],
                output_dir=suite_dir,
            )
            self.assertEqual(result["summary"]["overall"]["total_runs"], 2)
            self.assertTrue(os.path.exists(os.path.join(suite_dir, "manifest.json")))
            self.assertTrue(os.path.exists(os.path.join(suite_dir, "summary.json")))
            self.assertTrue(os.path.exists(os.path.join(suite_dir, "summary.csv")))
            self.assertTrue(os.path.isdir(os.path.join(suite_dir, "raw")))
            self.assertEqual(result["runs"][0]["workflow_label"], "single-agent baseline")
            self.assertEqual(result["runs"][1]["workflow_label"], "multi-agent workflow")
            self.assertEqual(result["runs"][0]["role_count"], 1)
            self.assertEqual(result["runs"][1]["role_count"], 5)
            self.assertEqual(result["runs"][1]["engineer_worker_count"], 2)
            self.assertEqual(len(result["runs"][1]["branch_results"]), 2)

            export_result = export_site_data(
                benchmark_root=tempdir,
                output_dir=os.path.join(tempdir, "site-data"),
            )
            self.assertEqual(export_result["issue_count"], 1)
            exported = Path(tempdir, "site-data", "conversations.json").read_text()
            self.assertIn("no-color", exported)
            self.assertIn("transcript", exported)
            self.assertIn("workflow_label", exported)
            self.assertIn("branch_results", exported)
            self.assertIn("messages", exported)


if __name__ == "__main__":
    unittest.main()
