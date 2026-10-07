"""Tests for tools/watchdog_report.py, the shared Watchdog output format."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import watchdog_report as wr  # noqa: E402


def sample():
    return [
        wr.finding("Mismatch with approved decision", "A", "docs/x.md", 4, "old", "A is new.", "Why A.", "Use new.",
                   [("WATCHDOG.md", wr.DOCS)]),
        wr.finding("Mismatch with approved decision", "B", "README.md", 2, "b,c:d", "B is b.", "Why B.", "Use b."),
        wr.finding("Mismatch with approved decision", "A", "docs/y.md", 9, "old", "A is new.", "Why A.", "Use new."),
    ]


class Render(unittest.TestCase):
    def test_grouped_blocks_and_closing_summary(self):
        lines = wr.render(sample(), "Decisions of record", "fix it.")
        text = "\n".join(lines)
        self.assertLess(text.index("== A: 2 finding(s) =="), text.index("== B: 1 finding(s) =="))
        self.assertIn("Mismatch with approved decision: docs/x.md:4: A found 'old'\n"
                      "  Decision: A is new.\n  Why:      Why A.\n  Fix:      Use new.\n"
                      f"  More:     WATCHDOG.md: {wr.DOCS}", text)
        self.assertEqual(lines[-2], "Decisions of record summary: 3 finding(s) (A 2, B 1)")
        self.assertEqual(lines[-1], "Next step: fix it.")

    def test_clean_run_says_nothing_to_fix(self):
        self.assertEqual(wr.render([], "Public extract", "x"),
                         ["Public extract summary: 0 finding(s)", "Next step: nothing to fix."])

    def test_rule_word(self):
        self.assertIn("  Rule:     A is new.", wr.render(sample()[:1], "T", "n", decision_word="Rule"))


class GitHubOutput(unittest.TestCase):
    def test_annotation_level_and_escaping(self):
        warn = wr.annotations(sample())
        self.assertEqual(len(warn), 3)
        self.assertTrue(warn[0].startswith(
            "::warning file=docs/x.md,line=4,title=Mismatch with approved decision (A)::Found 'old'."))
        self.assertTrue(all(a.startswith("::error ") for a in wr.annotations(sample(), "error")))
        self.assertTrue(wr.annotations(sample(), "bogus")[0].startswith("::warning "))
        odd = wr.finding("L", "G", "a,b:c.md", 1, "x\ny", "d", "w", "f")
        line = wr.annotations([odd])[0]
        self.assertIn("file=a%2Cb%3Ac.md,", line)
        self.assertNotIn("\n", line)

    def test_markdown_summary_table_and_details(self):
        md = wr.markdown(sample(), "Decisions of record", "fix it.")
        self.assertIn("### Decisions of record: 3 finding(s)", md)
        self.assertIn("| A | 2 | Use new. |", md)
        self.assertIn("<details><summary>B: 1 finding(s)</summary>", md)
        self.assertIn("- `docs/y.md:9` found `old`", md)
        self.assertIn("No findings", wr.markdown([], "T", "n"))

    def test_emit_only_inside_github_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp, "s.md")
            self.assertEqual(wr.emit_github(sample(), "T", "n", {"GITHUB_STEP_SUMMARY": str(summary)}), [])
            self.assertFalse(summary.exists())
            env = {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": str(summary), "WATCHDOG_ANNOTATIONS": "0"}
            self.assertEqual(wr.emit_github(sample(), "T", "n", env), [])
            env.pop("WATCHDOG_ANNOTATIONS")
            env["WATCHDOG_ANNOTATION"] = "error"
            lines = wr.emit_github(sample(), "T", "n", env)
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].startswith("::error "))
            self.assertIn("| A | 2 |", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
