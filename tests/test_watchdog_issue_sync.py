import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import watchdog_issue_sync as wis  # noqa: E402


MAINTAINERS = yaml.safe_load((ROOT / "maintainers.yaml").read_text(encoding="utf-8"))


def report(found=True):
    return {
        "repository": "openamrobot-docs",
        "commit": "a" * 40,
        "results": {
            "decisions": [{"group": "COMPUTE", "file": "README.md", "line": 4,
                           "found": "Raspberry Pi 5", "decision": "Jetson is current.",
                           "why": "Current 2.0 compute must be named.", "fix": "Label legacy or use Jetson.", "links": []}] if found else [],
            "public-extract": [], "shared-rules": [], "workflow-policy": [],
        },
        "freshness": ["COMPUTE review_by 2026-10-01 is past due"] if found else [],
    }


class PurePlan(unittest.TestCase):
    def test_fingerprint_is_stable_when_line_moves(self):
        a = wis.grouped_items([report()], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS)[0]
        changed = copy.deepcopy(report())
        changed["results"]["decisions"][0]["line"] = 99
        b = wis.grouped_items([changed], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS)[0]
        self.assertEqual(a["marker"], b["marker"])

    def test_plan_deduplicates_due_warning_and_opens_dashboard_candidates(self):
        data = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08", mode="groups")
        self.assertEqual(len(data["open"]), 2)
        self.assertTrue(any(i["kind"] == "finding" for i in data["open"]))
        self.assertTrue(any(i["kind"] == "review" for i in data["open"]))
        self.assertIsNone(data["dashboard"])

    def test_existing_issue_is_not_duplicated_and_changed_evidence_comments(self):
        first = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08", mode="groups")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 7, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "open", "comments": [], "url": "https://github.com/openAMRobot/.github/issues/7"}]
        second = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-08", mode="groups")
        self.assertFalse(any(i["kind"] == "finding" for i in second["open"]))
        changed = copy.deepcopy(report())
        changed["results"]["decisions"][0]["found"] = "old Pi"
        third = wis.plan([changed], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-08", mode="groups")
        self.assertTrue(any("still detected" in u["body"] for u in third["updates"]))

    def test_missing_finding_is_never_closed(self):
        first = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08", mode="groups")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 8, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "open", "comments": [], "url": "https://github.com/openAMRobot/.github/issues/8"}]
        second = wis.plan([report(False)], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-15", mode="groups")
        self.assertTrue(any(wis.NO_LONGER_MARKER in u["body"] for u in second["updates"]))
        self.assertFalse(any(u["issue"].get("number") == 8 and "PATCH" in u for u in second["updates"]))

    def test_reappearing_closed_finding_is_reopened(self):
        first = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08", mode="groups")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 9, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "closed", "comments": [], "url": "https://github.com/openAMRobot/.github/issues/9"}]
        second = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-15", mode="groups")
        reopen = [u for u in second["updates"] if u["issue"].get("number") == 9]
        self.assertEqual(len(reopen), 1)
        self.assertTrue(reopen[0]["reopen"])

    def test_public_issue_body_redacts_untrusted_values(self):
        item = wis.grouped_items([report()], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS)[0]
        item["findings"][0]["found"] = "https://drive.google.com/x user@example.com sk-ant-123456789"
        body = wis.body_for(item, "run", "2026-10-08")
        self.assertNotIn("drive.google.com", body)
        self.assertNotIn("user@example.com", body)
        self.assertNotIn("sk-ant-", body)

    def test_dashboard_observation_is_stable_marker(self):
        data = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08", mode="groups")
        body = wis.dashboard_body([report()], [], data, "run", "2026-10-08", [])
        self.assertIsNotNone(wis.OBSERVATION_RE.search(body))
        self.assertIn("Shared rules", body)


class Api(unittest.TestCase):
    def test_apply_reopens_and_comments_without_closing(self):
        calls = []

        def fake(method, url, token, data=None):
            calls.append((method, url, data))
            if method == "POST" and url.endswith("/issues"):
                return {"html_url": "https://github.com/openAMRobot/.github/issues/10"}
            return {}

        plan = {"open": [], "updates": [{"issue": {"number": 9, "title": "finding", "url": "u"},
                                          "body": "reappeared", "reopen": True}],
                "active": [], "dashboard": None, "mode": "groups"}
        wis.apply("openAMRobot/.github", plan, [], [], "token", "run", "2026-10-15", call=fake)
        methods = [method for method, _, _ in calls]
        self.assertIn("PATCH", methods)
        self.assertIn("POST", methods)
        self.assertNotIn("DELETE", methods)
        self.assertTrue(any("/issues/9/comments" in url for _, url, _ in calls))


def blocked():
    return [{"repository": "openamrobot-comm", "reason": "clone failed"}]


class IssueMode(unittest.TestCase):
    DECISIONS = {"COMPUTE": {"owner": "platform-lead"}}

    def test_unset_or_empty_switch_means_dashboard(self):
        self.assertEqual(wis.resolve_mode(None), "dashboard")
        self.assertEqual(wis.resolve_mode(""), "dashboard")
        self.assertEqual(wis.resolve_mode("  Groups "), "groups")
        with self.assertRaisesRegex(ValueError, "WATCHDOG_ISSUE_MODE"):
            wis.resolve_mode("everything")

    def test_dashboard_mode_plans_no_group_issue_writes(self):
        first = wis.plan([report()], [], self.DECISIONS, MAINTAINERS, [], "run", "2026-10-08", mode="groups")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 7, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "closed", "comments": [], "url": "u7"}]
        data = wis.plan([report()], blocked(), self.DECISIONS, MAINTAINERS, existing, "run", "2026-10-08")
        self.assertEqual(data["mode"], "dashboard")
        self.assertEqual((data["open"], data["updates"]), ([], []))
        self.assertEqual(len(data["active"]), 3)  # finding group, decision review, blocked repository

    def test_dashboard_lists_every_active_group_and_blocked_repositories(self):
        for mode in ("dashboard", "groups"):
            with self.subTest(mode=mode):
                data = wis.plan([report()], blocked(), self.DECISIONS, MAINTAINERS, [], "run", "2026-10-08", mode=mode)
                body = wis.dashboard_body([report()], blocked(), data, "run", "2026-10-08", [])
                self.assertIn(f"Issue mode: `{mode}`", body)
                self.assertIn("| Repository | Check | Group | Findings | Owner | Files |", body)
                self.assertIn("| openamrobot-docs | decisions | COMPUTE | 1 | platform-lead (BotshareAI) | "
                              "[README.md:4](https://github.com/openAMRobot/openamrobot-docs/blob/" + "a" * 40 + "/README.md#L4) |", body)
                self.assertIn("| decisions.yaml | decision-review | COMPUTE | 1 |", body)
                self.assertIn("| openamrobot-comm | scan | **BLOCKED** | - | ci-owner", body)
                self.assertIn("| openamrobot-comm | unavailable | - | - | - | **BLOCKED** |", body)

    def test_file_links_are_capped_per_group(self):
        many = copy.deepcopy(report())
        many["results"]["decisions"] = [dict(report()["results"]["decisions"][0], line=n) for n in range(1, 9)]
        data = wis.plan([many], [], self.DECISIONS, MAINTAINERS, [], "run", "2026-10-08")
        body = wis.dashboard_body([many], [], data, "run", "2026-10-08", [])
        self.assertIn("| 8 |", body)
        self.assertIn("#L5), and 3 more |", body)
        self.assertNotIn("#L6)", body)

    def run_apply(self, mode, dashboard=None):
        calls = []

        def fake(method, url, token, data=None):
            calls.append((method, url, data))
            return {"html_url": "https://github.com/openAMRobot/.github/issues/1"} if url.endswith("/issues") else {}

        data = wis.plan([report()], blocked(), self.DECISIONS, MAINTAINERS, [dashboard] if dashboard else [], "run",
                        "2026-10-08", mode=mode)
        wis.apply("openAMRobot/.github", data, [report()], blocked(), "token", "run", "2026-10-08", call=fake)
        return [(m, u.split("/repos/openAMRobot/.github/", 1)[1], d) for m, u, d in calls]

    def test_dashboard_mode_creates_only_the_dashboard(self):
        calls = self.run_apply("dashboard")
        issue_posts = [d for m, u, d in calls if m == "POST" and u == "issues"]
        self.assertEqual([d["title"] for d in issue_posts], ["[watchdog] Organization dashboard"])
        self.assertFalse([c for c in calls if "/comments" in c[1]])
        self.assertEqual({d["name"] for m, u, d in calls if u == "labels"}, {"watchdog-report"})

    def test_dashboard_mode_updates_the_dashboard_in_place_once(self):
        old = {"number": 5, "title": "[watchdog] Organization dashboard", "state": "open", "comments": [],
               "body": wis.DASHBOARD_MARKER + "\n<!-- watchdog:observation:0000 -->\nold", "url": "u5"}
        calls = self.run_apply("dashboard", old)
        writes = [(m, u) for m, u, d in calls if m in ("PATCH", "POST") and u != "labels"]
        self.assertEqual(writes, [("PATCH", "issues/5")])
        body = next(d for m, u, d in calls if m == "PATCH")["body"]
        same = dict(old, body=body)
        self.assertEqual([(m, u) for m, u, d in self.run_apply("dashboard", same) if u != "labels"], [])

    def test_groups_mode_keeps_per_group_issues(self):
        calls = self.run_apply("groups")
        titles = [d["title"] for m, u, d in calls if m == "POST" and u == "issues"]
        self.assertIn("[watchdog] openamrobot-docs: decisions / COMPUTE", titles)
        self.assertIn("[watchdog] Decision review: COMPUTE", titles)
        self.assertIn("[watchdog] Scan blocked: openamrobot-comm", titles)
        self.assertIn("[watchdog] Organization dashboard", titles)

    def test_command_line_reads_the_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "r.json").write_text(json.dumps(report()), encoding="utf-8")
            args = ["--reports", tmp, "--maintainers", str(ROOT / "maintainers.yaml"),
                    "--decisions", str(ROOT / "decisions.yaml"), "--run-url", "run"]
            for value, expected in ((None, "mode dashboard"), ("", "mode dashboard"), ("groups", "mode groups")):
                env = {k: v for k, v in os.environ.items() if k != "WATCHDOG_ISSUE_MODE"}
                if value is not None:
                    env["WATCHDOG_ISSUE_MODE"] = value
                out = io.StringIO()
                with unittest.mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out):
                    self.assertEqual(wis.main(args), 0)
                self.assertIn(expected, out.getvalue())
            err = io.StringIO()
            with unittest.mock.patch.dict(os.environ, {"WATCHDOG_ISSUE_MODE": "all"}), contextlib.redirect_stderr(err):
                self.assertEqual(wis.main(args), 2)


if __name__ == "__main__":
    unittest.main()
