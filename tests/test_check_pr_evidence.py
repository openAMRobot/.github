"""Tests for tools/check_pr_evidence.py."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_pr_evidence as ev  # noqa: E402

MAINTAINERS = yaml.safe_load((ROOT / "maintainers.yaml").read_text(encoding="utf-8"))
HEAD = "8ce9314fa9a404564fa7e954cd84f25bcba2b829"
BODY = f"""## Summary
Adds a filter node.

## Work package
#12

## Integration Gate
Reused the upstream madgwick filter; no overlapping PRs.

## Tests
Ran 12 tests, 0 skipped. Reverting the change makes test_topic_owner fail.

## Evidence
Base SHA: d1ac6b64db830f001eb4d9d45a48910209b180bf
Head SHA: {HEAD[:12]}

```
$ bash tools/verify.sh
PASS
```

## Dependencies
None

## Safety impact
None

## STATE.md
Updated.

## Not verified
Hardware run on the robot.

## AI disclosure
None
"""


def pr(body=BODY, draft=False, reviewers=(), author="contributor"):
    return {"number": 7, "body": body, "draft": draft, "head": {"sha": HEAD},
            "user": {"login": author}, "requested_reviewers": [{"login": r} for r in reviewers]}


def evaluate(body=BODY, changed=("src/node.py",), **kw):
    reviews = kw.pop("reviews", ())
    has_state = kw.pop("has_state", False)
    return ev.evaluate(pr(body, **kw), list(changed), MAINTAINERS, reviews, has_state)


class Sections(unittest.TestCase):
    def test_complete_description_passes(self):
        failures, warnings, _ = evaluate()
        self.assertEqual((failures, warnings), ([], []))

    def test_each_required_section_is_enforced(self):
        for name in ev.SECTIONS:
            with self.subTest(section=name):
                body = BODY.replace(f"## {name}\n", "## Something else\n")
                self.assertIn(f"Missing section: {name}", evaluate(body)[0])

    def test_empty_section_fails(self):
        body = BODY.replace("## Not verified\nHardware run on the robot.", "## Not verified\n<!-- fill -->\n")
        self.assertIn("Empty section: Not verified", evaluate(body)[0])

    def test_unfilled_template_fails(self):
        template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        failures = evaluate(template)[0]
        self.assertIn("Evidence: no base SHA (write `Base SHA: <sha>`)", failures)
        self.assertIn("Evidence: no exact command (use a code block or `$ command` lines)", failures)
        self.assertTrue(any(f.startswith("Empty section") for f in failures))

    def test_template_contains_every_required_section(self):
        template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        secs = ev.sections(template)
        for name in ev.SECTIONS + ["Dependencies", "STATE.md"]:
            self.assertIsNotNone(ev.find(secs, name), name)


class EvidenceRules(unittest.TestCase):
    def test_missing_shas(self):
        body = BODY.replace("Base SHA: d1ac6b64db830f001eb4d9d45a48910209b180bf\n", "").replace(f"Head SHA: {HEAD[:12]}", "")
        failures = evaluate(body)[0]
        self.assertIn("Evidence: no base SHA (write `Base SHA: <sha>`)", failures)
        self.assertIn("Evidence: no head SHA (write `Head SHA: <sha>`)", failures)

    def test_stale_head_fails_when_ready_and_warns_in_draft(self):
        body = BODY.replace(HEAD[:12], "0123456789ab")
        self.assertTrue(any("is not the PR head" in f for f in evaluate(body)[0]))
        failures, warnings, _ = evaluate(body, draft=True)
        self.assertEqual(failures, [])
        self.assertTrue(any("update before ready" in w for w in warnings))

    def test_dollar_command_lines_count_as_commands(self):
        body = BODY.replace("```\n$ bash tools/verify.sh\nPASS\n```", "$ bash tools/verify.sh")
        self.assertEqual(evaluate(body)[0], [])


class TestRules(unittest.TestCase):
    def test_test_change_without_count_fails(self):
        body = BODY.replace("Ran 12 tests, 0 skipped.", "Tests were run.")
        failures = evaluate(body, changed=["tests/test_node.py"])[0]
        self.assertIn("Test files changed (1) but no test run with a count is reported", failures)

    def test_zero_tests_fails(self):
        body = BODY.replace("Ran 12 tests, 0 skipped.", "Ran 0 tests.")
        self.assertIn("Reported test run executed zero tests", evaluate(body, changed=["pkg/test/test_a.py"])[0])

    def test_test_change_with_count_passes(self):
        self.assertEqual(evaluate(changed=["web/src/app.test.ts"])[0], [])


class DependencyAndStateRules(unittest.TestCase):
    def test_manifest_change_needs_dependencies_section(self):
        failures = evaluate(changed=["ros2/pkg/package.xml"])[0]
        self.assertTrue(any(f.startswith("Dependency manifests changed") for f in failures))
        body = BODY.replace("## Dependencies\nNone", "## Dependencies\nAdded imu_filter_madgwick (BSD-3-Clause, ROS index)")
        self.assertEqual(evaluate(body, changed=["ros2/pkg/package.xml"])[0], [])

    def test_fixture_manifests_are_not_dependencies(self):
        self.assertEqual(evaluate(changed=["tests/fixtures/repo/package.xml", "pkg/testdata/package.json"])[0], [])

    def test_state_md_must_be_updated_or_explained(self):
        self.assertIn("STATE.md exists but is not updated; update it or write 'no change' with a reason",
                      evaluate(has_state=True)[0])
        self.assertEqual(evaluate(changed=["src/node.py", "STATE.md"], has_state=True)[0], [])
        body = BODY.replace("## STATE.md\nUpdated.", "## STATE.md\nNo change: typo fix only.")
        self.assertEqual(evaluate(body, has_state=True)[0], [])


class SafetyRules(unittest.TestCase):
    CHANGED = ["firmware/src/estop_monitor.cpp"]

    def test_safety_path_needs_two_humans_including_platform_lead(self):
        failures = evaluate(changed=self.CHANGED, reviewers=["someone"])[0]
        self.assertIn("Safety path touched, two human approvals required: only 1 human reviewer(s) requested", failures)
        self.assertIn("Safety path touched, two human approvals required: platform lead @BotshareAI is not requested", failures)

    def test_bots_and_author_do_not_count(self):
        failures = evaluate(changed=self.CHANGED, reviewers=["BotshareAI", "claude[bot]", "contributor"])[0]
        self.assertIn("Safety path touched, two human approvals required: only 1 human reviewer(s) requested", failures)

    def test_two_humans_with_lead_pass_including_submitted_reviews(self):
        reviews = [{"user": {"login": "panthera-momagdii"}, "state": "COMMENTED"}]
        failures, _, notes = evaluate(changed=self.CHANGED, reviewers=["BotshareAI"], reviews=reviews)
        self.assertEqual(failures, [])
        self.assertTrue(any(n.startswith("Safety path touched, two human approvals required") for n in notes))

    def test_requested_reviewers_are_not_approvals(self):
        reviews = [{"user": {"login": "panthera-momagdii"}, "state": "APPROVED"},
                   {"user": {"login": "claude[bot]"}, "state": "APPROVED"}]
        notes = evaluate(changed=self.CHANGED, reviewers=["BotshareAI"], reviews=reviews)[2]
        self.assertTrue(any("Human approvals so far: 1 (information only" in n for n in notes))

    def test_ai_assisted_safety_change_fails(self):
        body = BODY.replace("## AI disclosure\nNone", "## AI disclosure\nClaude Code drafted the watchdog change.")
        failures = evaluate(body, changed=["fw/watchdog.c"], reviewers=["BotshareAI", "panthera-momagdii"])[0]
        self.assertTrue(any("agents do not author safety logic" in f for f in failures))


class DecisionReport(unittest.TestCase):
    def test_contradictions_become_failures(self):
        report = ("decisions: 3 loaded\n"
                  "CONTRADICTION docs/a.md:4: MAST-INSTALL-HEIGHT found 'mast_1400', decided '1350 mm' (P-03)\n"
                  "ALLOWED docs/h.md:2: MAST-INSTALL-HEIGHT found 'mast_1400'; reason: history\n")
        self.assertEqual(ev.decision_failures(report), [
            "Decision contradiction: docs/a.md:4: MAST-INSTALL-HEIGHT found 'mast_1400', decided '1350 mm' (P-03)"])

    def test_long_reports_are_truncated(self):
        report = "\n".join(f"CONTRADICTION f.md:{i}: X found 'a', decided 'b'" for i in range(25))
        failures = ev.decision_failures(report)
        self.assertEqual(len(failures), 21)
        self.assertEqual(failures[-1], "... and 5 more decision contradictions")


class Comment(unittest.TestCase):
    def test_render_has_marker_and_status(self):
        text = ev.render(["x"], [], [], pr())
        self.assertTrue(text.startswith(ev.MARKER))
        self.assertIn("PR evidence check: FAIL", text)
        self.assertIn("never approves or merges", text)

    def test_upsert_updates_existing_comment(self):
        calls = []

        def fake(method, url, token, data=None):
            calls.append((method, url))
            if method == "GET":
                return [{"id": 1, "body": "other"}, {"id": 2, "body": ev.MARKER + " old"}]
            return {}

        self.assertEqual(ev.upsert_comment("o/r", 7, "new", "t", call=fake), "updated")
        self.assertEqual(calls[-1], ("PATCH", "https://api.github.com/repos/o/r/issues/comments/2"))

    def test_upsert_creates_when_absent(self):
        calls = []

        def fake(method, url, token, data=None):
            calls.append((method, url))
            return [] if method == "GET" else {}

        self.assertEqual(ev.upsert_comment("o/r", 7, "new", "t", call=fake), "created")
        self.assertEqual(calls[-1], ("POST", "https://api.github.com/repos/o/r/issues/7/comments"))


class CommandLine(unittest.TestCase):
    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            event, changed = Path(tmp, "event.json"), Path(tmp, "changed.txt")
            changed.write_text("src/node.py\n", encoding="utf-8")
            event.write_text(json.dumps({"pull_request": pr()}), encoding="utf-8")
            args = ["--event", str(event), "--changed-files", str(changed),
                    "--maintainers", str(ROOT / "maintainers.yaml"), "--output", str(Path(tmp, "s.md"))]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ev.main(args), 0)
                event.write_text(json.dumps({"pull_request": pr(body="## Summary\nx\n")}), encoding="utf-8")
                self.assertEqual(ev.main(args), 1)
            self.assertIn(ev.MARKER, Path(tmp, "s.md").read_text(encoding="utf-8"))
            event.write_text(json.dumps({"push": {}}), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ev.main(args), 2)


if __name__ == "__main__":
    unittest.main()
