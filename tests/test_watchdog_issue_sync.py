import copy
import sys
import unittest
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
        data = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08")
        self.assertEqual(len(data["open"]), 2)
        self.assertTrue(any(i["kind"] == "finding" for i in data["open"]))
        self.assertTrue(any(i["kind"] == "review" for i in data["open"]))
        self.assertIsNone(data["dashboard"])

    def test_existing_issue_is_not_duplicated_and_changed_evidence_comments(self):
        first = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 7, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "open", "comments": [], "url": "https://github.com/openAMRobot/.github/issues/7"}]
        second = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-08")
        self.assertFalse(any(i["kind"] == "finding" for i in second["open"]))
        changed = copy.deepcopy(report())
        changed["results"]["decisions"][0]["found"] = "old Pi"
        third = wis.plan([changed], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-08")
        self.assertTrue(any("still detected" in u["body"] for u in third["updates"]))

    def test_missing_finding_is_never_closed(self):
        first = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 8, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "open", "comments": [], "url": "https://github.com/openAMRobot/.github/issues/8"}]
        second = wis.plan([report(False)], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-15")
        self.assertTrue(any(wis.NO_LONGER_MARKER in u["body"] for u in second["updates"]))
        self.assertFalse(any(u["issue"].get("number") == 8 and "PATCH" in u for u in second["updates"]))

    def test_reappearing_closed_finding_is_reopened(self):
        first = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08")
        finding = next(i for i in first["open"] if i["kind"] == "finding")
        existing = [{"number": 9, "title": finding["payload"]["title"], "body": finding["payload"]["body"],
                     "state": "closed", "comments": [], "url": "https://github.com/openAMRobot/.github/issues/9"}]
        second = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, existing, "run", "2026-10-15")
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
        data = wis.plan([report()], [], {"COMPUTE": {"owner": "platform-lead"}}, MAINTAINERS, [], "run", "2026-10-08")
        body = wis.dashboard_body([report()], [], data, "run", "2026-10-08", [])
        self.assertIsNotNone(wis.OBSERVATION_RE.search(body))


if __name__ == "__main__":
    unittest.main()
