"""Tests for tools/sync_audit_issues.py. All rows are synthetic."""
import contextlib
import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sync_audit_issues as sai  # noqa: E402

MAINTAINERS = yaml.safe_load((ROOT / "maintainers.yaml").read_text(encoding="utf-8"))
FIELDS = ["id", "severity", "area", "source_a", "value_a", "source_b", "value_b",
          "decision_of_record", "fix", "file_to_change", "owner"]


def row(fid, severity="Major", target="openamr-platform-sw ros2/src/pkg/launch/a.launch.py", **kw):
    base = dict.fromkeys(FIELDS, "")
    base.update(id=fid, severity=severity, area="topic", file_to_change=target,
                fix="synthetic private fix text", owner="Synthetic Person", value_a="synthetic private quote")
    base.update(kw)
    return base


def issue(repo, number, fid, state="open"):
    return {"repository": repo, "number": number, "title": f"[audit] {fid}: topic", "state": state}


class Plan(unittest.TestCase):
    def run_plan(self, rows, existing=()):
        return sai.plan(rows, list(existing), MAINTAINERS, "audits", "2099-01-01-alignment-audit@abc1234")

    def test_opens_blocker_and_major_only(self):
        to_open, _ = self.run_plan([row("ELE-901", "Blocker"), row("SW-902", "Minor"), row("GEO-903", "Question")])
        self.assertEqual([i["title"] for i in to_open], ["[audit] ELE-901: topic"])
        self.assertEqual(to_open[0]["repository"], "openamr-platform-sw")
        self.assertEqual(to_open[0]["labels"], ["audit-finding", "blocker"])

    def test_owner_from_maintainers_map_not_from_csv(self):
        to_open, _ = self.run_plan([row("SW-901"), row("DOC-901", target="openamrobot-docs docs/a.md")])
        self.assertIn("Owner: @panthera-momagdii (software-lead)", to_open[0]["body"])
        self.assertIn("Owner: docs-owner, no handle recorded", to_open[1]["body"])
        self.assertNotIn("Synthetic Person", to_open[0]["body"] + to_open[1]["body"])

    def test_public_issue_is_an_extract(self):
        body = self.run_plan([row("SW-901")])[0][0]["body"]
        self.assertNotIn("synthetic private quote", body)
        self.assertNotIn("synthetic private fix", body)
        self.assertIn("`ros2/src/pkg/launch/a.launch.py`", body)

    def test_findings_without_public_target_go_to_private_fallback(self):
        to_open, _ = self.run_plan([row("TEAM-901", target="plan document only")])
        self.assertEqual(to_open[0]["repository"], "audits")
        self.assertIn("synthetic private quote", to_open[0]["body"])

    def test_existing_issue_is_not_duplicated(self):
        self.assertEqual(self.run_plan([row("ELE-901", "Blocker")], [issue("openamr-platform-sw", 5, "ELE-901")]), ([], []))

    def test_no_longer_detected_is_commented_never_closed(self):
        existing = [issue("openamr-platform-sw", 5, "ELE-901"), issue("openamrobot-docs", 9, "DOC-901"),
                    issue("openamrobot-docs", 3, "DOC-902", "closed"),
                    {"repository": "openamrobot-docs", "number": 4, "title": "Unrelated", "state": "open"}]
        _, notify = self.run_plan([row("ELE-901", status="resolved")], existing)
        self.assertEqual(sorted((i["repository"], i["number"]) for i in notify),
                         [("openamr-platform-sw", 5), ("openamrobot-docs", 9)])


class Api(unittest.TestCase):
    def test_apply_creates_and_comments_but_never_closes(self):
        calls = []

        def fake(method, url, token, data=None):
            calls.append((method, url))
            return [] if method == "GET" else {}

        sai.apply("org", [{"repository": "r", "title": "t", "body": "b", "labels": ["audit-finding"]}],
                  [{"repository": "r", "number": 2}], "tok", "run@abc", call=fake)
        self.assertEqual(calls, [
            ("POST", "https://api.github.com/repos/org/r/issues"),
            ("GET", "https://api.github.com/repos/org/r/issues/2/comments?per_page=100"),
            ("POST", "https://api.github.com/repos/org/r/issues/2/comments"),
        ])
        self.assertFalse(any(m == "PATCH" for m, _ in calls))

    def test_no_longer_detected_comment_is_posted_once(self):
        calls = []

        def fake(method, url, token, data=None):
            calls.append(method)
            return [{"body": sai.NOT_DETECTED + " earlier"}] if method == "GET" else {}

        sai.apply("org", [], [{"repository": "r", "number": 2}], "tok", "run", call=fake)
        self.assertEqual(calls, ["GET"])

    def test_fetch_existing_parses_search(self):
        item = {"repository_url": "https://api.github.com/repos/org/r", "number": 1,
                "title": "[audit] SW-901: x", "state": "open"}
        got = sai.fetch_existing("org", "tok", call=lambda m, u, t, d=None: {"items": [item]})
        self.assertEqual(got, [{"repository": "r", "number": 1, "title": "[audit] SW-901: x", "state": "open"}])


class CommandLine(unittest.TestCase):
    def test_dry_run_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "ISSUES.csv")
            with open(path, "w", newline="", encoding="utf-8") as stream:
                w = csv.DictWriter(stream, fieldnames=FIELDS)
                w.writeheader()
                w.writerows([row("ELE-901", "Blocker"), row("SW-902", "Minor")])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = sai.main(["--issues", str(path), "--maintainers", str(ROOT / "maintainers.yaml"),
                                 "--fallback-repository", "audits", "--report", "x@1"])
            self.assertEqual(code, 0)
            self.assertIn("plan: 1 to open, 0 to comment 'no longer detected', 0 closed", out.getvalue())


if __name__ == "__main__":
    unittest.main()
