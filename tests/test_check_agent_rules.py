"""Tests for tools/check_agent_rules.py (shared-block drift check)."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_agent_rules as car  # noqa: E402

CANONICAL = ROOT / "agent-rules" / "SHARED_RULES.md"


class Drift(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.shared = CANONICAL.read_text(encoding="utf-8")

    def repo(self, name, agents, claude="@AGENTS.md\n"):
        d = Path(self.tmp.name, name)
        d.mkdir()
        (d / "AGENTS.md").write_text(agents, encoding="utf-8")
        (d / "CLAUDE.md").write_text(claude, encoding="utf-8")
        return d

    def run_main(self, *args):
        err = io.StringIO()
        with contextlib.redirect_stdout(err), contextlib.redirect_stderr(err):
            try:
                code = car.main(["--canonical", str(CANONICAL), *map(str, args)])
            except SystemExit as exc:
                code = exc.code
        return code, err.getvalue()

    def test_identical_block_passes(self):
        self.repo("a", self.shared + "\n# Repository-specific rules: a\n")
        self.assertEqual(self.run_main("--root", self.tmp.name)[0], 0)

    def test_root_agents_md_passes(self):
        self.assertEqual(self.run_main("--file", ROOT / "AGENTS.md")[0], 0)

    def test_edited_block_fails(self):
        self.repo("a", self.shared.replace("zero tests fails", "zero tests is fine"))
        code, err = self.run_main("--root", self.tmp.name)
        self.assertEqual(code, 1)
        self.assertIn("shared block differs from canonical", err)
        self.assertIn("Shared agent rules out of date: ", err)
        self.assertIn("Fix:      Copy the block between the BEGIN and END markers", err)
        self.assertIn("Shared agent rules summary: 1 finding(s) (shared-rules 1)", err)

    def test_older_version_fails_with_version_message(self):
        old = self.shared.replace("SHARED RULES v2", "SHARED RULES v1")
        self.repo("a", old)
        self.assertIn("shared block is v1, canonical is v2", self.run_main("--root", self.tmp.name)[1])

    def test_line_limit_and_claude_import(self):
        self.repo("long", self.shared + "x\n" * 120)
        self.repo("claude", self.shared, claude="@AGENTS.md\nextra rules\n")
        err = self.run_main("--root", self.tmp.name)[1]
        self.assertIn("must be under 120 lines", err)
        self.assertIn("CLAUDE.md must import @AGENTS.md", err)

    def test_empty_selection_is_refused(self):
        self.assertEqual(self.run_main("--root", self.tmp.name)[0], 2)


if __name__ == "__main__":
    unittest.main()
