"""Regression tests from the 1 Nov 2026 effectiveness audit (openAMRobot/audits,
2026-11-01-harness-effectiveness, probe P1): the selector chose openamrobot-manifest#12
although a person's open PR #19 ("fix(ci): ... (#12)") already works on it, because only
ai-generated PRs and ai/ branches counted as taken; and the build inputs had no list of open
PRs, so the agent could not fill the Integration Gate."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import harness_inputs  # noqa: E402
import harness_lib as hl  # noqa: E402
import harness_select as sel  # noqa: E402

POLICY = hl.load_policy(ROOT)


def issue(n):
    return {"number": n, "repository": "openamrobot-manifest", "state": "open", "title": f"issue {n}",
            "body": "", "labels": [{"name": "ai-ready"}, {"name": "tier:B"}], "created_at": f"2026-10-0{n}T00:00:00Z"}


def human_pr(title, body=""):
    return {"number": 19, "repository": "openamrobot-manifest", "state": "open", "labels": [],
            "title": title, "body": body, "head": {"ref": "ci/verify-tip"}}


class Overlap(unittest.TestCase):
    def pick(self, issues, pulls):
        return sel.select(POLICY, ROOT, issues, pulls, True, 2)

    def test_a_persons_pr_naming_the_issue_in_its_title_takes_it(self):
        result = self.pick([issue(2)], [human_pr("fix(ci): validate branch-tip pins (#2)")])
        self.assertFalse(result["run"], result)
        self.assertIn("open PR", result["skipped"][0]["reason"])

    def test_a_persons_pr_linking_the_issue_in_its_body_takes_it(self):
        self.assertFalse(self.pick([issue(2)], [human_pr("fix(ci)", "Refs #2")])["run"])

    def test_unrelated_pr_leaves_the_issue_free(self):
        self.assertTrue(self.pick([issue(2)], [human_pr("docs: other (#7)")])["run"])


class BuildInputs(unittest.TestCase):
    def test_build_inputs_include_open_pulls(self):
        class FakeGh:
            def get(self, path):
                return {"number": 2, "title": "t"}

            def paged(self, path, limit=1000):
                if "/pulls?" in path:
                    return [{"number": 19, "title": "fix(ci) (#2)", "head": {"ref": "x"}, "user": {"login": "u"},
                             "body": "Refs #2", "updated_at": "2026-11-01T00:00:00Z"}]
                return []
        with tempfile.TemporaryDirectory() as ws:
            harness_inputs.collect("build", {"repository": "openamrobot-manifest", "issue": 2}, Path(ws),
                                   "openAMRobot", FakeGh(), POLICY)
            pulls = json.loads((Path(ws) / ".harness-in" / "open-pulls.json").read_text())
        self.assertEqual(pulls[0]["number"], 19)


if __name__ == "__main__":
    unittest.main()
