"""Tests for tools/watchdog.py, the one-command Watchdog runner."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import watchdog  # noqa: E402

DRIVE = "https://drive.google.com/file/d/abc123/view"


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = watchdog.main([str(a) for a in args])
    return code, out.getvalue()


def setUpModule():
    # Tests never write to the real GitHub Actions log or job summary of the CI run.
    patcher = unittest.mock.patch.dict(os.environ)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    for key in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "WATCHDOG_ANNOTATION", "WATCHDOG_ANNOTATIONS"):
        os.environ.pop(key, None)


class Watchdog(unittest.TestCase):
    def make(self, tmp, agents=True):
        repo = Path(tmp, "openamr-platform-sw")
        (repo / "docs").mkdir(parents=True)
        (repo / "docs/a.md").write_text("Compute is a Raspberry Pi 5.\n", encoding="utf-8")
        (repo / "README.md").write_text(f"See {DRIVE}\n", encoding="utf-8")
        wf = repo / ".github/workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("jobs:\n  a:\n    steps:\n      - uses: actions/checkout@v4\n", encoding="utf-8")
        if agents:
            (repo / "AGENTS.md").write_text("no shared block\n", encoding="utf-8")
            (repo / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        return repo

    def test_all_checks_run_and_summary_groups_by_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make(tmp)
            code, out = run("--root", repo)
            self.assertEqual(code, 1)
            self.assertIn("OpenAMRobot Watchdog: openamr-platform-sw", out)
            self.assertIn("Mismatch with approved decision: docs/a.md:1: COMPUTE found 'Raspberry Pi 5'", out)
            self.assertIn("Should not be public: README.md:1: google-drive-link found", out)
            self.assertIn("Shared agent rules out of date: AGENTS.md:1:", out)
            self.assertIn("Workflow not pinned: .github/workflows/ci.yml:4:", out)
            self.assertIn("Total: 4 finding(s) (COMPUTE 1, google-drive-link 1, shared-rules 1, unpinned-action 1)", out)
            self.assertIn("WATCHDOG.md", out)

    def test_report_only_never_fails_on_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("--root", self.make(tmp), "--report-only")[0], 0)

    def test_clean_repository_and_missing_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp, "demo")
            repo.mkdir()
            (repo / "README.md").write_text("Reference compute is the Jetson.\n", encoding="utf-8")
            code, out = run("--root", repo)
            self.assertEqual(code, 0, out)
            self.assertIn("Not run: the repository has no AGENTS.md.", out)
            self.assertIn("Total: 0 finding(s)", out)
            self.assertIn("Next step: nothing to fix.", out)

    def test_this_repository_passes_its_own_agents_check(self):
        report = watchdog.run(ROOT, ".github")
        self.assertEqual(report["results"]["shared-rules"], [])

    def test_usage_and_configuration_errors_exit_two(self):
        self.assertEqual(run("--root", "/nonexistent/path")[0], 2)
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp, "harness")
            shutil.copytree(ROOT / "tools", harness / "tools")
            shutil.copytree(ROOT / "agent-rules", harness / "agent-rules")
            shutil.copy(ROOT / "maintainers.yaml", harness)
            shutil.copy(ROOT / "public-extract-allowlist.yaml", harness)
            (harness / "decisions.yaml").write_text("schema_version: 9\n", encoding="utf-8")
            code, out = run("--root", ROOT, "--harness", harness, "--report-only")
            self.assertEqual(code, 2)
            self.assertIn("INVALID configuration", out)

    def test_json_and_markdown_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make(tmp, agents=False)
            md, js = Path(tmp, "summary.md"), Path(tmp, "r.json")
            run("--root", repo, "--report-only", "--markdown", md, "--json", js, "--repository", "x")
            run("--root", repo, "--report-only", "--markdown", md, "--repository", "y")
            text = md.read_text(encoding="utf-8")
            self.assertIn("### x: 3 finding(s)", text)
            self.assertIn("### y: 3 finding(s)", text)
            self.assertIn("| Shared agent rules | not run (no AGENTS.md) |", text)
            self.assertIn("| COMPUTE | 1 |", text)
            data = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(data["repository"], "x")
            self.assertEqual(len(data["results"]["decisions"]), 1)

    def test_freshness_reports_past_review_dates(self):
        self.assertEqual(watchdog.freshness(ROOT / "decisions.yaml", date(2000, 1, 1)), [])
        overdue = watchdog.freshness(ROOT / "decisions.yaml", date(2100, 1, 1))
        self.assertTrue(overdue)
        self.assertTrue(all("past due" in w for w in overdue))
        with tempfile.TemporaryDirectory() as tmp:
            report = watchdog.run(Path(tmp), "x", today=date(2100, 1, 1))
            text = "\n".join(watchdog.render(report))
            self.assertIn("Review due: ", text)
            self.assertEqual(watchdog.total(report), 0)


class Guide(unittest.TestCase):
    """WATCHDOG.md stays in step with the register and the checks."""

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "WATCHDOG.md").read_text(encoding="utf-8")

    def test_accepted_words_table_matches_register(self):
        code, out = run("--accepted-words")
        self.assertEqual(code, 0)
        section = self.text.split("<!-- BEGIN ACCEPTED WORDS -->\n", 1)[1].split("<!-- END ACCEPTED WORDS -->", 1)[0]
        self.assertEqual(section, out, "regenerate with: python3 tools/watchdog.py --accepted-words")

    def test_every_decision_is_listed(self):
        for d in watchdog.cd.load_decisions(ROOT / "decisions.yaml"):
            self.assertIn(f"| {d['id']} | {d['status']} |", self.text)

    def test_link_anchors_used_by_findings_exist(self):
        for anchor in ("decisions-of-record", "public-extract", "shared-agent-rules", "workflow-policy",
                       "pr-evidence", "verify", "decision-freshness"):
            self.assertIn(f'<a id="{anchor}"></a>', self.text)

    def test_plain_words(self):
        self.assertEqual(watchdog.plain_words(r"supersed|\bnot\b|rev ?18\.[1-6]\b|3\.0"),
                         ["supersed (superseded, supersedes)", "not", "rev 18.1 to rev 18.6", "3.0"])
        self.assertEqual(watchdog.split_alternatives(r"a(?:b|c)|[|]|d"), ["a(?:b|c)", "[|]", "d"])

    def test_guide_is_excluded_only_at_the_repository_root(self):
        decisions = watchdog.cd.load_decisions(ROOT / "decisions.yaml")
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("WATCHDOG.md", "docs/WATCHDOG.md"):
                Path(tmp, name).parent.mkdir(parents=True, exist_ok=True)
                Path(tmp, name).write_text("Compute is a Raspberry Pi 5.\n", encoding="utf-8")
            found = watchdog.cd.scan(tmp, decisions, ".github")[0]
            self.assertEqual(sorted(f["file"] for f in found), ["docs/WATCHDOG.md"])

    def test_guide_is_linked(self):
        for name in ("README.md", "CONTRIBUTING.md"):
            self.assertIn("WATCHDOG.md", (ROOT / name).read_text(encoding="utf-8"), name)


if __name__ == "__main__":
    unittest.main()
