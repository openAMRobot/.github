"""Tests for tools/check_workflow_policy.py."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_workflow_policy as policy  # noqa: E402


class WorkflowPolicy(unittest.TestCase):
    def write(self, root, path, text):
        target = Path(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def test_full_sha_and_local_workflow_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, ".github/workflows/ok.yml", """
name: ok
jobs:
  build:
    uses: ./.github/workflows/reusable.yml
  test:
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
""")
            self.assertEqual(policy.findings(tmp), [])

    def test_tag_branch_and_placeholder_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, ".github/workflows/bad.yml", """
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-artifact@main
      - uses: owner/action
      - run: echo <HARNESS_SHA>
""")
            errors = policy.findings(tmp)
            self.assertEqual(len(errors), 4)
            self.assertTrue(any("full commit SHA" in e for e in errors))
            self.assertTrue(any("no immutable" in e for e in errors))
            self.assertTrue(any("<HARNESS_SHA>" in e for e in errors))

    def test_command_line_explains_each_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, ".github/workflows/bad.yml", "jobs:\n  b:\n    steps:\n      - uses: actions/checkout@v4\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = policy.main(["--root", tmp])
            text = out.getvalue()
            self.assertEqual(code, 1)
            self.assertIn("Workflow not pinned: .github/workflows/bad.yml:4: unpinned-action found", text)
            self.assertIn("\n  Rule:     ", text)
            self.assertIn("\n  Fix:      ", text)
            self.assertIn("Workflow policy summary: 1 finding(s) (unpinned-action 1)", text)
            self.assertIn("result: 1 workflow policy finding(s)", text)

    def test_rollout_examples_are_outside_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "rollout/workflows/example.yml",
                       "uses: actions/checkout@<HARNESS_SHA>\n")
            self.assertEqual(policy.findings(tmp), [])


if __name__ == "__main__":
    unittest.main()
