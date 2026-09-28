"""Tests for tools/sync_audit_issues.py."""
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


def row(fid, severity="Major", target="openamr-platform-sw ros2/src/bringup/launch/real.launch.py", **kw):
    base = dict.fromkeys(FIELDS, "")
    base.update(id=fid, severity=severity, area="imu", file_to_change=target,
                fix="Ask the named lead to decide", owner="A Person", value_a="internal quote")
    base.update(kw)
    return base


class Plan(unittest.TestCase):
    def run_plan(self, rows, existing=()):
        return sai.plan(rows, list(existing), MAINTAINERS, "audits", "2026-10-05-alignment-audit@abc1234")

    def test_opens_blocker_and_major_only(self):
        to_open, _ = self.run_plan([row("ELE-001", "Blocker"), row("SW-002", "Minor"), row("GEO-003", "Question")])
        self.assertEqual([i["title"] for i in to_open], ["[audit] ELE-001: imu"])
        self.assertEqual(to_open[0]["repository"], "openamr-platform-sw")
        self.assertEqual(to_open[0]["labels"], ["audit-finding", "blocker"])

    def test_owner_from_maintainers_map_not_from_csv(self):
        to_open, _ = self.run_plan([row("SW-001"), row("DOC-001", target="openamrobot-docs docs/a.md")])
        self.assertIn("Owner: @panthera-momagdii (software-lead)", to_open[0]["body"])
        self.assertIn("Owner: docs-owner, no handle recorded", to_open[1]["body"])
        self.assertNotIn("A Person", to_open[0]["body"] + to_open[1]["body"])

    def test_public_issue_is_an_extract(self):
        to_open, _ = self.run_plan([row("SW-001")])
        body = to_open[0]["body"]
        self.assertNotIn("internal quote", body)
        self.assertNotIn("Ask the named lead", body)
        self.assertIn("`ros2/src/bringup/launch/real.launch.py`", body)

    def test_plan_document_findings_go_to_private_fallback_with_full_text(self):
        to_open, _ = self.run_plan([row("TEAM-004", target="P-01 Status document")])
        self.assertEqual(to_open[0]["repository"], "audits")
        self.assertIn("internal quote", to_open[0]["body"])

    def test_existing_issue_is_not_duplicated(self):
        existing = [{"repository": "openamr-platform-sw", "number": 5, "title": "[audit] ELE-001: imu", "state": "open"}]
        to_open, to_close = self.run_plan([row("ELE-001", "Blocker")], existing)
        self.assertEqual((to_open, to_close), ([], []))

    def test_resolved_or_absent_findings_close_open_issues(self):
        existing = [
            {"repository": "openamr-platform-sw", "number": 5, "title": "[audit] ELE-001: imu", "state": "open"},
            {"repository": "openamrobot-docs", "number": 9, "title": "[audit] DOC-021: docs", "state": "open"},
            {"repository": "openamrobot-docs", "number": 3, "title": "[audit] DOC-002: docs", "state": "closed"},
            {"repository": "openamrobot-docs", "number": 4, "title": "Unrelated", "state": "open"},
        ]
        _, to_close = self.run_plan([row("ELE-001", status="resolved")], existing)
        self.assertEqual(sorted((i["repository"], i["number"]) for i in to_close),
                         [("openamr-platform-sw", 5), ("openamrobot-docs", 9)])


class Api(unittest.TestCase):
    def test_apply_creates_comments_and_closes(self):
        calls = []
        sai.apply("org", [{"repository": "r", "title": "t", "body": "b", "labels": ["audit-finding"]}],
                  [{"repository": "r", "number": 2}], "tok", "abc",
                  call=lambda m, u, t, d=None: calls.append((m, u)))
        self.assertEqual(calls, [
            ("POST", "https://api.github.com/repos/org/r/issues"),
            ("POST", "https://api.github.com/repos/org/r/issues/2/comments"),
            ("PATCH", "https://api.github.com/repos/org/r/issues/2"),
        ])

    def test_fetch_existing_parses_search(self):
        item = {"repository_url": "https://api.github.com/repos/org/r", "number": 1,
                "title": "[audit] SW-001: x", "state": "open"}
        got = sai.fetch_existing("org", "tok", call=lambda m, u, t, d=None: {"items": [item]})
        self.assertEqual(got, [{"repository": "r", "number": 1, "title": "[audit] SW-001: x", "state": "open"}])


class CommandLine(unittest.TestCase):
    def test_dry_run_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "ISSUES.csv")
            with open(path, "w", newline="", encoding="utf-8") as stream:
                w = csv.DictWriter(stream, fieldnames=FIELDS)
                w.writeheader()
                w.writerows([row("ELE-001", "Blocker"), row("SW-002", "Minor")])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = sai.main(["--issues", str(path), "--maintainers", str(ROOT / "maintainers.yaml"),
                                 "--fallback-repository", "audits", "--report", "x@1"])
            self.assertEqual(code, 0)
            self.assertIn("plan: 1 to open, 0 to close", out.getvalue())


if __name__ == "__main__":
    unittest.main()
