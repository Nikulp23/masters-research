import os
import tempfile
import unittest
from pathlib import Path

from agentic_research.sandbox import run_test_preflight


class SandboxPreflightTests(unittest.TestCase):
    def test_unittest_discover_preflight_passes_for_valid_test_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_issue_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
            )
            result = run_test_preflight(
                str(root),
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_demo.py", "-v"],
                expected_test_files=["tests/test_issue_demo.py"],
            )
            self.assertTrue(result["passed"])
            self.assertEqual(result["returncode"], 0)

    def test_unittest_module_preflight_fails_for_missing_module_target(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_issue_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
            )
            result = run_test_preflight(
                str(root),
                ["python3", "-m", "unittest", "tests.missing_issue_demo", "-v"],
                expected_test_files=["tests/test_issue_demo.py"],
            )
            self.assertFalse(result["passed"])
            self.assertEqual(result["returncode"], -2)
            self.assertIn("preflight failed", result["stderr"].lower())

    def test_preflight_fails_for_missing_editable_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_issue_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
            )
            result = run_test_preflight(
                str(root),
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_demo.py", "-v"],
                expected_test_files=["tests/test_issue_demo.py"],
                editable_files=["src/missing.py"],
            )
            self.assertFalse(result["passed"])
            self.assertEqual(result["returncode"], -3)
            self.assertIn("missing editable files", result["stderr"].lower())


if __name__ == "__main__":
    unittest.main()
