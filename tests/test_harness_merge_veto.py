"""Regression test from the 1 Nov 2026 effectiveness audit (openAMRobot/audits,
2026-11-01-harness-effectiveness): harness_publish.Publisher.review updates its one review
comment in place, so the comment's created_at belongs to the first reviewed head. With a
backdated commit, a new head reviewed one hour ago passed the 24 h veto window at once."""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import harness_lib as hl  # noqa: E402
import harness_merge_gate as gate  # noqa: E402

BOT = "openamrobot-harness[bot]"
HEAD = "b" * 40
NOW = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)


def decide(comment, commit_time):
    policy = hl.load_policy(ROOT)
    policy["repositories"]["openamrobot-manifest"]["build"] = True
    pr = {"labels": [{"name": "ai-generated"}, {"name": "tier:A"}], "head": {"sha": HEAD}}
    checks = {"check_runs": [{"name": n, "status": "completed", "conclusion": "success"}
                             for n in ("quality/test", "quality/pr-evidence")]}
    return gate.decide(pr, [{"filename": "tests/test_x.py"}], [comment], checks, [], commit_time,
                       "openamrobot-manifest", policy, NOW, bot=BOT,
                       statuses={"state": "success", "statuses": [{"context": "DCO", "state": "success"}]})


def comment(created, updated):
    return {"user": {"type": "Bot", "login": BOT}, "created_at": created, "updated_at": updated,
            "body": f"<!-- harness-review head={HEAD} verdict=pass tier=A -->\nok"}


class VetoWindow(unittest.TestCase):
    def test_comment_updated_for_the_new_head_restarts_the_window(self):
        backdated = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
        reasons = decide(comment("2026-10-29T12:00:00Z", "2026-11-01T11:00:00Z"), backdated)
        self.assertTrue(any("veto window" in r for r in reasons), reasons)

    def test_window_passes_when_the_head_was_reviewed_over_24_h_ago(self):
        reasons = decide(comment("2026-10-29T12:00:00Z", "2026-10-30T11:00:00Z"),
                         dt.datetime(2026, 10, 29, tzinfo=dt.timezone.utc))
        self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
