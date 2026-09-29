"""Tests for rollout/verify.sh: zero-test rule, skip rule, delegation."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "rollout" / "verify.sh"
PASSING = "import unittest\n\nclass T(unittest.TestCase):\n    def test_one(self):\n        self.assertTrue(True)\n"


def make_repo(files):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return tmp, root


def verify(root):
    proc = subprocess.run(["bash", str(VERIFY), str(root)], capture_output=True, text=True, timeout=120,
                          env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(root)})
    runs = sorted((root / ".verification").glob("run.*"))
    summary = json.loads((runs[-1] / "summary.json").read_text()) if runs else {}
    return proc.returncode, proc.stdout + proc.stderr, summary


class VerifyScript(unittest.TestCase):
    def check(self, files):
        tmp, root = make_repo(files)
        self.addCleanup(tmp.cleanup)
        return verify(root)

    def test_passing_suite_passes_with_counts(self):
        code, out, summary = self.check({"tests/test_a.py": PASSING})
        self.assertEqual(code, 0, out)
        self.assertEqual((summary["result"], summary["tests_total"]), ("PASS", 1))

    def test_zero_tests_fail(self):
        code, out, summary = self.check({"tests/test_a.py": "# no tests yet\n"})
        self.assertNotEqual(code, 0)
        self.assertIn("zero tests executed", out)
        self.assertEqual(summary["failed_stage"], "test")

    def test_failing_test_fails(self):
        body = PASSING.replace("self.assertTrue(True)", "self.fail('deliberate')")
        code, out, summary = self.check({"tests/test_a.py": body})
        self.assertNotEqual(code, 0)
        self.assertIn("test command exited with status", out)
        self.assertEqual(summary["failed_stage"], "test")

    def test_fully_skipped_suite_fails(self):
        body = PASSING.replace("    def test_one", "    @unittest.skip('flaky, see #12')\n    def test_one")
        code, out, _ = self.check({"tests/test_a.py": body})
        self.assertNotEqual(code, 0)
        self.assertIn("zero tests executed", out)

    def test_skip_without_issue_fails(self):
        body = PASSING + "\n    @unittest." + "skip('later')\n    def test_two(self):\n        pass\n"
        code, out, summary = self.check({"tests/test_a.py": body})
        self.assertNotEqual(code, 0)
        self.assertEqual(summary["failed_stage"], "test-markers")

    def test_skip_with_issue_is_allowed(self):
        body = PASSING + "\n    @unittest.skip('hardware only, see #12')\n    def test_two(self):\n        pass\n"
        code, out, summary = self.check({"tests/test_a.py": body})
        self.assertEqual(code, 0, out)
        self.assertEqual((summary["tests_total"], summary["tests_skipped"]), (2, 1))

    def test_nothing_detected_fails(self):
        code, out, _ = self.check({"notes.txt": "hello\n"})
        self.assertNotEqual(code, 0)
        self.assertIn("no buildable or testable project detected", out)

    def test_delegates_to_existing_tools_verify(self):
        code, out, _ = self.check({"tools/verify.sh": "echo repository-own-verify\nexit 0\n"})
        self.assertEqual(code, 0)
        self.assertIn("repository-own-verify", out)

    def test_delegation_writes_summary_with_delegated_status_and_counts(self):
        script = ("echo 'Ran 3 tests in 0.010s'\n"
                  "echo 'Evidence: /work/.verification/run.native'\n"
                  "exit 0\n")
        code, out, summary = self.check({"tools/verify.sh": script})
        self.assertEqual(code, 0, out)
        self.assertEqual(summary["mode"], "delegated")
        self.assertEqual((summary["result"], summary["exit_code"]), ("PASS", 0))
        self.assertEqual((summary["tests_total"], summary["tests_skipped"], summary["counts_parsed"]), (3, 0, True))
        self.assertEqual(summary["delegated_evidence"], "/work/.verification/run.native")
        self.assertIsInstance(summary["duration_seconds"], int)
        for key in ("schema_version", "head_sha", "base_sha", "harness_sha", "delegated_script"):
            self.assertIn(key, summary)

    def test_delegated_failure_is_recorded_and_propagated(self):
        code, out, summary = self.check({"tools/verify.sh": "echo 'Ran 2 tests in 0.1s'\necho boom\nexit 7\n"})
        self.assertEqual(code, 7, out)
        self.assertEqual((summary["result"], summary["exit_code"]), ("FAIL", 7))
        self.assertIn("FAIL: delegated tools/verify.sh (exit 7)", out)

    def test_delegation_without_recognisable_counts_says_so(self):
        _, _, summary = self.check({"tools/verify.sh": "echo done\nexit 0\n"})
        self.assertEqual((summary["tests_total"], summary["counts_parsed"]), (None, False))


if __name__ == "__main__":
    unittest.main()
