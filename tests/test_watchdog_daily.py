"""Tests for tools/watchdog_daily.py and .github/workflows/watchdog-daily.yml.

The API is replaced by tests/fixtures/watchdog_daily/responses.json: responses in the shape the
GitHub REST API returned for openAMRobot/.github on 2026-10-29 (fields trimmed), with synthetic
repositories, numbers and logins for each case. No network is used.
"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_workflow_policy as cwp  # noqa: E402
import watchdog_daily as wd  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "watchdog_daily"
REPOS = FIXTURES / "repositories.yaml"
NOW = datetime(2026, 10, 29, 4, 41, tzinfo=timezone.utc)
WORKFLOW = ROOT / ".github" / "workflows" / "watchdog-daily.yml"
DESIGN = ROOT / "rollout" / "workflows" / "watchdog-daily-summary.yml"


class Recorded:
    """Fake transport: answers each URL from the fixture; a list answers in order."""

    def __init__(self, extra=None):
        self.responses = json.loads((FIXTURES / "responses.json").read_text(encoding="utf-8"))
        self.responses.update(extra or {})
        self.calls = []
        self.waits = []

    def __call__(self, url, headers):
        self.calls.append(url)
        if url not in self.responses:
            raise AssertionError(f"unexpected request: {url}")
        answer = self.responses[url]
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        return answer["status"], answer["headers"], json.dumps(answer["body"]).encode("utf-8")

    def api(self, **kwargs):
        return wd.Api("token", transport=self, sleep=self.waits.append, clock=lambda: NOW.timestamp(), **kwargs)


def collect(transport=None, **kwargs):
    transport = transport or Recorded()
    org, repos = wd.load_repositories(REPOS)
    return wd.collect(transport.api(**kwargs), org, repos, NOW), transport


def by_name(report):
    return {r["repository"]: r for r in report["repositories"]}


class Collector(unittest.TestCase):
    def test_green_and_red_runs_latest_per_workflow_and_green_rate(self):
        alpha = by_name(collect()[0])["fixture-alpha"]
        self.assertEqual([(w["workflow"], w["conclusion"], w["run_id"]) for w in alpha["ci"]["workflows"]],
                         [("ci.yml", "success", 101), ("docs.yml", "cancelled", 103), ("lint.yml", "failure", 105)])
        # The fork run (104) and the run before the 7-day window (107) are not counted.
        self.assertEqual((alpha["ci"]["green"], alpha["ci"]["red"], alpha["ci"]["other"]), (2, 2, 1))
        self.assertEqual(alpha["ci"]["green_rate"], 0.5)

    def test_pagination_follows_the_link_header(self):
        report, transport = collect()
        alpha = by_name(report)["fixture-alpha"]
        self.assertIn("lint.yml", [w["workflow"] for w in alpha["ci"]["workflows"]])  # only on page 2
        self.assertTrue(any(url.startswith("https://api.github.com/repositories/1001/") for url in transport.calls))

    def test_endless_pagination_is_not_measured_not_truncated(self):
        url = "https://api.github.com/repos/openAMRobot/fixture-alpha/pulls?state=open&per_page=100"
        loop = {url: {"status": 200, "headers": {"Link": f'<{url}>; rel="next"'}, "body": []}}
        alpha = by_name(collect(Recorded(loop), max_pages=3)[0])["fixture-alpha"]
        self.assertFalse(alpha["measured"])
        self.assertEqual(alpha["reason"], "pull requests: more than 3 pages")

    def test_draft_and_stale_pull_requests(self):
        alpha = by_name(collect()[0])["fixture-alpha"]
        pulls = {p["number"]: p for p in alpha["pull_requests"]}
        self.assertEqual(sorted(pulls), [3, 5])
        self.assertTrue(pulls[5]["draft"])
        self.assertFalse(pulls[3]["draft"])
        self.assertEqual((pulls[5]["author"], pulls[5]["age_days"], pulls[5]["idle_days"]), ("dev-two", 1, 0))
        self.assertEqual(pulls[3]["idle_days"], 18)
        self.assertEqual(alpha["stale"], {"pull_requests": [3], "issues": [9]})

    def test_rc1_issues_by_label_or_title_without_pull_requests(self):
        alpha = by_name(collect()[0])["fixture-alpha"]
        self.assertEqual([(i["number"], i["assignees"], i["age_days"]) for i in alpha["rc1_issues"]],
                         [(7, ["dev-one"], 8), (8, [], 3)])

    def test_unreadable_repository_is_not_measured_and_the_run_incomplete(self):
        report = collect()[0]
        beta = by_name(report)["fixture-beta"]
        self.assertEqual(beta, {"repository": "fixture-beta", "default_branch": "main", "measured": False,
                                "reason": "workflow runs: HTTP 404"})
        self.assertEqual((report["status"], report["measured"], report["expected"]), ("incomplete", 3, 4))
        text = wd.render(report, None)
        self.assertIn("INCOMPLETE (3 of 4 repositories measured)", text)
        self.assertIn("| fixture-beta | not measured: workflow runs: HTTP 404 | - | - | - | - |", text)

    def test_issues_disabled_is_reported_not_guessed(self):
        gamma = by_name(collect()[0])["fixture-gamma"]
        self.assertTrue(gamma["measured"])
        self.assertFalse(gamma["issues_enabled"])
        self.assertIn("| fixture-gamma | no runs | no runs | none | issues disabled | none |", wd.render(collect()[0], None))

    def test_rate_limit_waits_for_reset_and_retries_server_errors(self):
        report, transport = collect()
        delta = by_name(report)["fixture-delta"]
        self.assertTrue(delta["measured"])
        self.assertEqual(transport.waits, [6, 2])  # reset 5 s after the clock, plus one; then backoff for the 502

    def test_rate_limit_longer_than_max_wait_is_not_measured(self):
        report, transport = collect(max_wait=3)
        delta = by_name(report)["fixture-delta"]
        self.assertFalse(delta["measured"])
        self.assertEqual(delta["reason"], "workflow runs: HTTP 403: rate limited for 6 s, more than 3 s")
        self.assertEqual(transport.waits, [])

    def test_one_failing_repository_never_stops_the_others(self):
        broken = Recorded()
        broken.responses["https://api.github.com/repos/openAMRobot/fixture-alpha/pulls?state=open&per_page=100"] = \
            {"status": 200, "headers": {}, "body": [{"number": 1}]}  # missing fields
        report = collect(broken)[0]
        self.assertEqual(by_name(report)["fixture-alpha"]["reason"], "pull requests: malformed KeyError")
        self.assertTrue(by_name(report)["fixture-gamma"]["measured"])


class Report(unittest.TestCase):
    def test_changes_since_previous_come_first(self):
        report = collect()[0]
        previous = json.loads((FIXTURES / "previous.json").read_text(encoding="utf-8"))
        self.assertEqual(wd.changes(previous, report), [
            "fixture-alpha: CI ci.yml failure -> success",
            "fixture-alpha: CI docs.yml no run -> cancelled",
            "fixture-alpha: CI lint.yml success -> failure",
            "fixture-alpha: PR #5 opened",
            "fixture-alpha: PR #4 no longer open",
            "fixture-alpha: rc.1 issue #8 opened",
            "fixture-alpha: PR #3 now stale",
            "fixture-beta: now not measured (workflow runs: HTTP 404)",
            "fixture-delta: measured again",
        ])
        text = wd.render(report, previous)
        self.assertLess(text.index("Changes since 2026-10-28T04:41:00Z:"), text.index("| Repository |"))
        self.assertIn("- fixture-alpha: CI lint.yml success -> failure", text)

    def test_without_previous_report_no_change_is_invented(self):
        text = wd.render(collect()[0], None)
        self.assertIn("Changes: no previous report available; changes are listed from the next run.", text)
        self.assertIsNone(wd.load_previous(FIXTURES / "missing.json"))

    def test_table_row_per_repository(self):
        text = wd.render(collect()[0], None)
        self.assertIn("| fixture-alpha | 1 red: lint.yml; 1 green; 1 other | 50% (2/4) | 2 (1 draft): "
                      "#3 dev-one 38d, upd 18d; #5 dev-two draft 1d, upd 0d | #7 dev-one 8d; #8 unassigned 3d | "
                      "PR #3; issue #9 |", text)

    def test_at_most_60_lines_with_many_repositories_and_changes(self):
        report = collect()[0]
        many = copy.deepcopy(report)
        many["repositories"] = [dict(report["repositories"][0], repository=f"repo-{n:02d}") for n in range(70)]
        previous = copy.deepcopy(many)
        for repo in previous["repositories"]:  # six changes per repository
            repo.update(pull_requests=[], rc1_issues=[], stale={"pull_requests": [], "issues": []})
        self.assertLessEqual(len(wd.render(many, previous).splitlines()), wd.MAX_LINES)
        self.assertIn("Report truncated at 60 lines; daily.json holds every repository.", wd.render(many, previous))
        fifteen = copy.deepcopy(many)
        fifteen["repositories"] = fifteen["repositories"][:15]
        prev15 = copy.deepcopy(previous)
        prev15["repositories"] = prev15["repositories"][:15]
        text = wd.render(fifteen, prev15)
        self.assertLessEqual(len(text.splitlines()), wd.MAX_LINES)
        self.assertIn("more in daily.json", text)
        self.assertIn("| repo-14 |", text)  # every row of the 15 repositories is kept

    def test_untrusted_names_cannot_mention_or_break_the_table(self):
        self.assertEqual(wd.workflow_label(".github/workflows/x|@everyone.yml"), "xeveryone.yml")
        self.assertEqual(wd.login({"login": "@dev|one"}), "devone")
        text = wd.render(collect()[0], None)
        self.assertNotIn("@", text)

    def test_output_is_deterministic(self):
        first, second = collect()[0], collect()[0]
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(wd.render(first, None), wd.render(second, None))


class CommandLine(unittest.TestCase):
    def run_main(self, *args, transport=None):
        out, err = io.StringIO(), io.StringIO()
        transport = transport or Recorded()
        with unittest.mock.patch.object(wd, "urllib_transport", transport), \
                unittest.mock.patch.object(wd.time, "sleep", lambda s: None), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = wd.main([str(a) for a in args])
        return code, out.getvalue() + err.getvalue()

    def test_incomplete_run_writes_both_files_and_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self.run_main("--repositories", REPOS, "--out", tmp, "--now", "2026-10-29T04:41:00Z",
                                      "--previous", FIXTURES / "previous.json")
            self.assertEqual(code, 1, out)
            data = json.loads(Path(tmp, "daily.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "incomplete")
            self.assertIn("Changes since", Path(tmp, "daily.md").read_text(encoding="utf-8"))
            self.assertIn("::error::fixture-beta not measured: workflow runs: HTTP 404", out)

    def test_complete_run_exits_zero(self):
        fixed = Recorded({"https://api.github.com/repos/openAMRobot/fixture-beta/actions/runs?branch=main&status=completed"
                          "&created=%3E%3D2026-10-22&per_page=100":
                          {"status": 200, "headers": {}, "body": {"total_count": 0, "workflow_runs": []}},
                          "https://api.github.com/repos/openAMRobot/fixture-beta/pulls?state=open&per_page=100":
                          {"status": 200, "headers": {}, "body": []},
                          "https://api.github.com/repos/openAMRobot/fixture-beta/issues?state=open&per_page=100":
                          {"status": 200, "headers": {}, "body": []}})
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self.run_main("--repositories", REPOS, "--out", tmp, "--now", "2026-10-29T04:41:00Z",
                                      transport=fixed)
            self.assertEqual(code, 0, out)
            self.assertIn("COMPLETE (4 of 4 repositories measured)", Path(tmp, "daily.md").read_text(encoding="utf-8"))

    def test_unreadable_repository_list_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "repositories.yaml")
            bad.write_text("organization: openAMRobot\nrepositories:\n  - {name: x y, default_branch: main}\n", encoding="utf-8")
            code, out = self.run_main("--repositories", bad, "--out", Path(tmp, "out"))
            self.assertEqual(code, 2)
            self.assertIn("the repository list could not be read", out)
            self.assertFalse(Path(tmp, "out").exists())

    def test_list_parser_matches_yaml_on_the_real_list(self):
        org, repos = wd.load_repositories(ROOT / "rollout" / "repositories.yaml")
        data = yaml.safe_load((ROOT / "rollout" / "repositories.yaml").read_text(encoding="utf-8"))
        self.assertEqual(org, data["organization"])
        self.assertEqual(repos, [(r["name"], r["default_branch"]) for r in data["repositories"]])
        self.assertIn(("openamrobot-embodied-ai", "main"), repos)


class Workflows(unittest.TestCase):
    def test_daily_workflow_schedule_permissions_and_steps(self):
        data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        on = data.get(True, data.get("on"))
        self.assertEqual(on["schedule"], [{"cron": "41 4 * * 1-5"}])
        self.assertIn("workflow_dispatch", on)
        self.assertEqual(data["permissions"], {"contents": "read", "issues": "write", "actions": "read"})
        self.assertEqual(data["concurrency"], {"group": "watchdog-daily", "cancel-in-progress": False})
        job = data["jobs"]["daily"]
        self.assertNotIn("permissions", job)
        self.assertEqual(job["timeout-minutes"], 20)
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("tools/watchdog_daily.py", text)
        self.assertIn("--daily", text)
        upload = next(s for s in job["steps"] if "upload-artifact" in s.get("uses", ""))
        self.assertEqual(upload["with"]["name"], "watchdog-daily")
        for forbidden in ("anthropic", "claude-code-action", "git push", "contents: write", "pull-requests: write"):
            self.assertNotIn(forbidden, text)

    def test_daily_workflow_passes_the_workflow_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, ".github", "workflows")
            target.mkdir(parents=True)
            target.joinpath("watchdog-daily.yml").write_text(WORKFLOW.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(cwp.findings(tmp), [])

    def test_ai_summary_is_design_only_and_guarded(self):
        self.assertFalse((ROOT / ".github" / "workflows" / DESIGN.name).exists())
        text = DESIGN.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        job = next(iter(data["jobs"].values()))
        self.assertEqual(job["if"], "vars.AI_STAGE_1_ENABLED == 'true'")
        self.assertIn("anthropics/claude-code-action@8c3fd987fa6a6b2654f69275e323d08207fcd36c # v1.0.264", text)
        self.assertIn("--max-turns 15", text)
        self.assertIn('--allowedTools "Read,Grep,Glob"', text)
        self.assertIn("issues/43", text)
        self.assertIn("watchdog-daily-summary.yml", (ROOT / "rollout" / "workflows" / "SETUP.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
