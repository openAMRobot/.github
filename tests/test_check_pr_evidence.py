"""Tests for tools/check_pr_evidence.py."""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
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

## Contribution terms

- [x] No partner, customer or private person is named; the application is Use_Case_1.
"""


def pr(body=BODY, draft=False, reviewers=(), author="contributor"):
    return {"number": 7, "body": body, "draft": draft, "head": {"sha": HEAD},
            "user": {"login": author}, "requested_reviewers": [{"login": r} for r in reviewers]}


def evaluate(body=BODY, changed=("src/node.py",), **kw):
    reviews = kw.pop("reviews", ())
    has_state = kw.pop("has_state", False)
    commit_messages = kw.pop("commit_messages", ())
    return ev.evaluate(pr(body, **kw), list(changed), MAINTAINERS, reviews, has_state, commit_messages)


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

    def test_public_use_checkbox_is_required_when_terms_are_present(self):
        body = BODY.replace(
            "- [x] No partner, customer or private person is named; the application is Use_Case_1.",
            "- [ ] No partner, customer or private person is named; the application is Use_Case_1."
        )
        self.assertIn("Contribution terms: check the Use_Case_1/no-private-person checkbox",
                      evaluate(body)[0])

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

    def test_ai_disclosure_names_tool_and_scope(self):
        body = BODY.replace("## AI disclosure\nNone", "## AI disclosure\nAI-assisted.")
        failures = evaluate(body, commit_messages=["Generated with Claude Code"])[0]
        self.assertTrue(any("must name the AI tool" in f for f in failures))
        self.assertTrue(any("must state the scope" in f for f in failures))

    def test_ai_disclosure_can_pass_with_tool_and_scope(self):
        body = BODY.replace(
            "## AI disclosure\nNone",
            "## AI disclosure\nClaude Code drafted the documentation and tests; a human reviewed the diff."
        )
        self.assertEqual(evaluate(body, commit_messages=["Generated with Claude Code"])[0], [])

    def test_ai_markers_in_commit_messages_are_checked(self):
        failures = evaluate(commit_messages=["Implement feature\n\nCo-Authored-By: Claude <noreply@example.com>"])[0]
        self.assertTrue(any("AI assistance is visible" in f for f in failures))


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


class DeletedFiles(unittest.TestCase):
    """A PR that only deletes files must still reach the evidence rules."""

    def test_deleting_a_safety_path_file_is_flagged(self):
        failures, _, notes = evaluate(changed=["firmware/src/estop_monitor.cpp"])
        self.assertIn("Safety path touched, two human approvals required: only 0 human reviewer(s) requested",
                      failures)
        self.assertTrue(any(n.startswith("Safety path touched") for n in notes))

    def test_deleting_a_dependency_manifest_is_flagged(self):
        failures = evaluate(changed=["ros2/pkg/package.xml"])[0]
        self.assertTrue(any(f.startswith("Dependency manifests changed (ros2/pkg/package.xml)") for f in failures))

    @unittest.skipIf(shutil.which("jq") is None, "jq is not installed; tracking issue openAMRobot/.github#42")
    def test_pr_assistant_passes_deleted_files_to_the_evidence_checker(self):
        workflow = yaml.safe_load((ROOT / "rollout" / "workflows" / "pr-assistant.yml").read_text(encoding="utf-8"))
        steps = {s.get("name"): s.get("run", "") for s in workflow["jobs"]["evidence"]["steps"]}
        collect = steps["Collect changed files and reviews"]
        jq_all = re.search(r"jq -r '([^']+)' files.json \| sort -u > changed_all.txt", collect).group(1)
        jq_existing = re.search(r"jq -r '([^']+)' files.json \| sort -u > changed_existing.txt", collect).group(1)
        files = [
            {"filename": "firmware/src/estop_monitor.cpp", "status": "removed"},
            {"filename": "ros2/pkg/package.xml", "status": "removed"},
            {"filename": "fw/brake_ctrl_v2.c", "previous_filename": "fw/brake_ctrl.c", "status": "renamed"},
            {"filename": "README.md", "status": "modified"},
        ]

        def run_jq(expr):
            out = subprocess.run(["jq", "-r", expr], input=json.dumps(files), capture_output=True,
                                 text=True, check=True).stdout
            return sorted(set(out.split()))

        changed_all, existing = run_jq(jq_all), run_jq(jq_existing)
        self.assertEqual(changed_all, ["README.md", "firmware/src/estop_monitor.cpp", "fw/brake_ctrl.c",
                                       "fw/brake_ctrl_v2.c", "ros2/pkg/package.xml"])
        self.assertEqual(existing, ["README.md", "fw/brake_ctrl_v2.c"])
        self.assertIn("--changed-files changed_all.txt", steps["Evidence check and summary comment"])
        self.assertIn("--changed-files changed_existing.txt", steps["Decisions of record on the diff"])
        failures = evaluate(changed=changed_all)[0]
        self.assertTrue(any(f.startswith("Safety path touched") for f in failures))
        self.assertTrue(any(f.startswith("Dependency manifests changed") for f in failures))


class JqMissing(unittest.TestCase):
    def test_wiring_test_names_its_tracking_issue_when_jq_is_missing(self):
        with tempfile.TemporaryDirectory() as empty_path:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "-v",
                 "test_check_pr_evidence.DeletedFiles.test_pr_assistant_passes_deleted_files_to_the_evidence_checker"],
                cwd=ROOT / "tests", env=dict(os.environ, PATH=empty_path), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("skipped 'jq is not installed; tracking issue openAMRobot/.github#42'", proc.stderr)


CLEAN = "decisions: 23 loaded\nresult: 0 contradiction(s), 0 allowed, scope 3 changed file(s)\n"
TWO = ("decisions: 23 loaded\n"
       "CONTRADICTION docs/a.md:4: MAST-INSTALL-HEIGHT found 'mast_1400', decided '1350 mm' (P-03)\n"
       "CONTRADICTION docs/b.md:9: COMPUTE found 'Raspberry Pi 5', decided 'Jetson' (P-00)\n"
       "result: 2 contradiction(s), 0 allowed, scope 2 changed file(s)\n")


class DecisionCheckerFailsClosed(unittest.TestCase):
    """Any decisions-check outcome other than the two documented ones is a checker error."""

    def test_documented_outcomes(self):
        self.assertEqual(ev.decision_verdict(CLEAN, {"exit_code": 0}), ([], []))
        failures, errors = ev.decision_verdict(TWO, {"exit_code": 1})
        self.assertEqual((len(failures), errors), (2, []))

    def test_real_checker_exception_is_a_checker_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            # --changed-files pointing at a directory makes check_decisions.py raise.
            proc = subprocess.run([sys.executable, str(ROOT / "tools" / "check_decisions.py"),
                                   "--decisions", str(ROOT / "decisions.yaml"), "--root", tmp,
                                   "--changed-files", tmp], capture_output=True, text=True)
        report = proc.stdout + proc.stderr
        self.assertIn("Traceback (most recent call last)", report)
        failures, errors = ev.decision_verdict(report, {"exit_code": proc.returncode})
        self.assertEqual(failures, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("checker error: check_decisions.py crashed"))

    def test_nonzero_exit_with_empty_output_is_a_checker_error(self):
        for code in (1, 137):
            with self.subTest(exit_code=code):
                failures, errors = ev.decision_verdict("", {"exit_code": code})
                self.assertEqual(failures, [])
                self.assertTrue(errors and errors[0].startswith("checker error"))

    def test_exit_zero_without_a_result_line_is_a_checker_error(self):
        self.assertTrue(ev.decision_verdict("", {"exit_code": 0})[1])

    def test_invalid_register_and_mismatched_counts_are_checker_errors(self):
        self.assertTrue(ev.decision_verdict("INVALID decisions file:\nA: bad", {"exit_code": 2})[1][0]
                        .startswith("checker error: check_decisions.py exit 2"))
        mismatched = TWO.replace("result: 2", "result: 3")
        self.assertTrue(ev.decision_verdict(mismatched, {"exit_code": 1})[1])
        self.assertTrue(ev.decision_verdict(CLEAN, {"exit_code": 1})[1])

    def test_missing_or_unreadable_status_is_a_checker_error(self):
        for status in (None, {}, {"exit_code": "1"}, {"exit_code": True}):
            with self.subTest(status=status):
                self.assertTrue(ev.decision_verdict(CLEAN, status)[1][0].startswith(
                    "checker error: decisions status file missing"))

    def run_main(self, tmp, report=None, status=None, status_path=None):
        event, changed = Path(tmp, "event.json"), Path(tmp, "changed.txt")
        event.write_text(json.dumps({"pull_request": pr()}), encoding="utf-8")
        changed.write_text("src/node.py\n", encoding="utf-8")
        args = ["--event", str(event), "--changed-files", str(changed),
                "--maintainers", str(ROOT / "maintainers.yaml"), "--output", str(Path(tmp, "s.md")),
                "--decisions-report", str(Path(tmp, "decisions.txt"))]
        if report is not None:
            Path(tmp, "decisions.txt").write_text(report, encoding="utf-8")
        if status is not None:
            Path(tmp, "status.json").write_text(json.dumps(status), encoding="utf-8")
        args += ["--decisions-status", str(status_path or Path(tmp, "status.json"))]
        with contextlib.redirect_stdout(io.StringIO()):
            code = ev.main(args)
        return code, Path(tmp, "s.md").read_text(encoding="utf-8")

    def test_missing_status_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = self.run_main(tmp, report=CLEAN, status_path=Path(tmp, "absent.json"))
        self.assertEqual(code, 1)
        self.assertIn("PR evidence check: CHECKER ERROR", summary)
        self.assertIn("decisions status file missing", summary)

    def test_missing_report_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = self.run_main(tmp, status={"exit_code": 0})
        self.assertEqual(code, 1)
        self.assertIn("PR evidence check: CHECKER ERROR", summary)

    def test_clean_run_through_main_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = self.run_main(tmp, report=CLEAN, status={"exit_code": 0})
        self.assertEqual(code, 0, summary)
        self.assertIn("PR evidence check: PASS", summary)

    def test_pr_assistant_step_records_status_of_a_crashing_checker(self):
        workflow = yaml.safe_load((ROOT / "rollout" / "workflows" / "pr-assistant.yml").read_text(encoding="utf-8"))
        steps = {s.get("name"): s for s in workflow["jobs"]["evidence"]["steps"]}
        self.assertIn("--decisions-status decisions-status.json", steps["Evidence check and summary comment"]["run"])
        script = steps["Decisions of record on the diff"]["run"]
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp, "harness", "tools")
            tools.mkdir(parents=True)
            (tools / "check_decisions.py").write_text("raise RuntimeError('simulated checker crash')\n",
                                                      encoding="utf-8")
            Path(tmp, "pr-head").mkdir()
            Path(tmp, "changed_existing.txt").write_text("README.md\n", encoding="utf-8")
            proc = subprocess.run(["bash", "-eo", "pipefail", "-c", script], cwd=tmp, capture_output=True,
                                  text=True, env={"PATH": os.environ["PATH"], "REPOSITORY": "x"})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            status = json.loads(Path(tmp, "decisions-status.json").read_text(encoding="utf-8"))
            report = Path(tmp, "decisions.txt").read_text(encoding="utf-8")
        self.assertEqual(status, {"exit_code": 1})
        failures, errors = ev.decision_verdict(report, status)
        self.assertEqual(failures, [])
        self.assertTrue(errors[0].startswith("checker error: check_decisions.py crashed"))


class Comment(unittest.TestCase):
    def test_render_checker_error_verdict(self):
        text = ev.render([], [], [], pr(), ["checker error: x"])
        self.assertIn("PR evidence check: CHECKER ERROR", text)
        self.assertIn("Checker errors (fails closed", text)

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
