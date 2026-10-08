"""Tests for the Watchdog organization scan: rollout/repositories.yaml and its workflow.

The scan step is taken from the workflow file and run with a fake `git` that creates small
local repositories, so no network is used.
"""
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import watchdog_issue_sync as wis  # noqa: E402
LIST = ROOT / "rollout" / "repositories.yaml"
WORKFLOW = ROOT / ".github" / "workflows" / "watchdog-org-scan.yml"
ACTIVE = {".github", "openamr-platform-sw", "openamr-platform-fw", "openamr-platform-hw",
          "openamr-upperbody-sw", "openamr-upperbody-fw", "openamr-upperbody-hw",
          "openamrobot-interfaces", "openamrobot-manipulation", "openamrobot-ui", "openamrobot-comm",
          "openamrobot-docs", "openamrobot-manifest", "openamrobot-release"}

FAKE_GIT = """#!/bin/bash
# clone --quiet --depth 1 --branch <b> <url> <dest>; rev-parse prints a fixed SHA
if [ "$1" = clone ]; then
  dest="${@: -1}"
  for fail in ${FAIL_CLONES-openamrobot-comm}; do
    case "$dest" in */"$fail") exit 128;; esac
  done
  mkdir -p "$dest/docs"
  echo "Compute is a Raspberry Pi 5." > "$dest/docs/a.md"
  exit 0
fi
if [ "$1" = -C ] && [ "$3" = rev-parse ]; then echo abc1234; exit 0; fi
exec "$REAL_GIT" "$@"
"""


def workflow():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data, data.get(True, data.get("on"))


def setUpModule():
    # Tests never write to the real GitHub Actions log or job summary of the CI run.
    patcher = unittest.mock.patch.dict(os.environ)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    for key in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "WATCHDOG_ANNOTATION", "WATCHDOG_ANNOTATIONS"):
        os.environ.pop(key, None)


class RepositoryList(unittest.TestCase):
    def test_lists_all_active_repositories_once(self):
        data = yaml.safe_load(LIST.read_text(encoding="utf-8"))
        self.assertEqual(data["organization"], "openAMRobot")
        names = [r["name"] for r in data["repositories"]]
        self.assertEqual(len(names), 14)
        self.assertEqual(len(set(names)), len(names), "duplicate repository")
        self.assertEqual(set(names), ACTIVE)
        for r in data["repositories"]:
            with self.subTest(repository=r["name"]):
                self.assertEqual(set(r), {"name", "default_branch"})
                self.assertRegex(r["name"], r"^[A-Za-z0-9._-]+$")
                self.assertRegex(r["default_branch"], r"^[A-Za-z0-9._/-]+$")


class Workflow(unittest.TestCase):
    def test_scans_on_thursday_and_writes_only_control_surface_issues(self):
        data, on = workflow()
        self.assertEqual(data["permissions"], {"contents": "read", "issues": "write"})
        self.assertEqual(set(on), {"schedule", "workflow_dispatch"})
        self.assertEqual(on["schedule"][0]["cron"], "0 14 * * 4")
        self.assertEqual(on["schedule"][0]["timezone"], "Europe/Berlin")
        for job in data["jobs"].values():
            self.assertNotIn("permissions", job)

    def test_never_pushes_code_or_runs_ai(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for forbidden in ("git push", "git commit", "gh issue", "gh pr", "pull-requests: write",
                          "contents: write", "anthropic", "claude-code-action"):
            self.assertNotIn(forbidden, text)
        self.assertIn("--report-only", text)
        self.assertIn("watchdog_issue_sync.py", text)
        self.assertIn("--apply", text)
        self.assertIn("GITHUB_TOKEN", text)
        self.assertIn("WATCHDOG.md", text)

    def test_issue_mode_comes_from_the_repository_variable(self):
        data, _ = workflow()
        step = next(s for s in data["jobs"]["scan"]["steps"] if s["name"] == "Synchronize Watchdog issues")
        self.assertEqual(step["env"]["WATCHDOG_ISSUE_MODE"], "${{ vars.WATCHDOG_ISSUE_MODE }}")
        self.assertNotIn("--mode", step["run"])  # the tool reads the variable; unset means dashboard
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('unset or "dashboard"', text)
        self.assertIn('"groups"', text)

    def test_actions_pinned_to_full_sha(self):
        data, _ = workflow()
        for job in data["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")

    def test_scan_reports_every_repository_and_blocks_on_clone_failure(self):
        result = run_scan()
        # openamrobot-comm fails to clone in the fake: reported BLOCKED, job fails after the summary.
        self.assertEqual(result.code, 1, result.output)
        self.assertIn("| openamrobot-comm | BLOCKED: clone failed | not scanned |", result.summary)
        self.assertIn("## OpenAMRobot Watchdog organization scan: INCOMPLETE: 13 of 14 repositories scanned", result.summary)
        self.assertIn("BLOCKED repositories were not scanned and are not clean.", result.summary)
        rows = re.findall(r"^\| ([.\w-]+) \| abc1234 \| (\d+) \|$", result.summary, re.M)
        self.assertEqual(len(rows), 13)
        self.assertIn(("openamr-platform-sw", "1"), rows)
        self.assertIn("### openamr-platform-sw: 1 finding(s)", result.summary)
        self.assertIn("| COMPUTE | 1 |", result.summary)
        self.assertEqual(result.blocked, [{"repository": "openamrobot-comm", "reason": "clone failed"}])
        # Default dashboard mode: the summary must not promise per-group issues.
        self.assertIn("Results are published to the [watchdog] Organization dashboard issue in the harness repository; "
                      "per-group issues only when WATCHDOG_ISSUE_MODE is groups.", result.summary)
        self.assertNotIn("synchronized to deduplicated issues", result.summary)
        self.assertNotIn("::warning", result.output)


def make_harness(tmp, repositories=None, watchdog_wrapper=None):
    """A harness checkout for the scan step: links to this repository, with an optional
    replacement repositories.yaml (False = missing) and an optional watchdog.py wrapper."""
    harness = Path(tmp, "harness")
    harness.mkdir()
    for name in ("decisions.yaml", "maintainers.yaml", "public-extract-allowlist.yaml", "agent-rules"):
        os.symlink(ROOT / name, harness / name)
    (harness / "rollout").mkdir()
    if repositories is not False:
        text = LIST.read_text(encoding="utf-8") if repositories is None else repositories
        (harness / "rollout" / "repositories.yaml").write_text(text, encoding="utf-8")
    tools = harness / "tools"
    tools.mkdir()
    for path in (ROOT / "tools").glob("*.py"):
        if not (watchdog_wrapper and path.name == "watchdog.py"):
            os.symlink(path, tools / path.name)
    if watchdog_wrapper:
        (tools / "watchdog.py").write_text(watchdog_wrapper.replace("REAL", repr(str(ROOT / "tools" / "watchdog.py"))),
                                           encoding="utf-8")
    return harness


class ScanResult:
    def __init__(self, proc, work, summary):
        self.code = proc.returncode
        self.output = proc.stdout + proc.stderr
        self.summary = summary
        self.blocked = json.loads(Path(work, "blocked.json").read_text(encoding="utf-8")) if Path(work, "blocked.json").exists() else None
        self.expected = json.loads(Path(work, "expected.json").read_text(encoding="utf-8")) if Path(work, "expected.json").exists() else None
        self.reports = sorted(p.name for p in Path(work, "out").glob("*.json")) if Path(work, "out").is_dir() else []
        self.work = work


def run_scan(fail_clones="openamrobot-comm", repositories=None, watchdog_wrapper=None, keep=None):
    """Run the workflow's "Scan repositories" step with a fake git and a fake harness."""
    data, _ = workflow()
    step = next(s for s in data["jobs"]["scan"]["steps"] if s["name"] == "Scan repositories")
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = Path(tmp, "bin")
        bin_dir.mkdir()
        git = bin_dir / "git"
        git.write_text(FAKE_GIT, encoding="utf-8")
        git.chmod(git.stat().st_mode | stat.S_IEXEC)
        make_harness(tmp, repositories, watchdog_wrapper)
        summary = Path(tmp, "summary.md")
        work = Path(tmp, "work")
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", HARNESS="harness",
                   WORK=str(work), GITHUB_STEP_SUMMARY=str(summary),
                   REAL_GIT=shutil.which("git") or "/usr/bin/git",
                   WATCHDOG_ANNOTATIONS="0", FAIL_CLONES=fail_clones)
        proc = subprocess.run(["bash", "-c", step["run"]], cwd=tmp, env=env, capture_output=True, text=True)
        text = summary.read_text(encoding="utf-8") if summary.exists() else ""
        result = ScanResult(proc, work, text)
        if keep is not None:
            shutil.copytree(work, keep, dirs_exist_ok=True)
        return result


def sync(work, expected=True):
    """Plan the issue sync on a scan's output exactly as the workflow step does (no --apply)."""
    args = ["--reports", str(Path(work, "out")), "--blocked", str(Path(work, "blocked.json")),
            "--maintainers", str(ROOT / "maintainers.yaml"), "--decisions", str(ROOT / "decisions.yaml"),
            "--run-url", "run", "--run-date", "2026-10-08"]
    if expected:
        args += ["--expected", str(Path(work, "expected.json"))]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = wis.main(args)
    return code, out.getvalue() + err.getvalue()


WRAPPER = """import runpy, sys
args = sys.argv
repo = args[args.index("--repository") + 1]
if repo == "openamrobot-ui":
    sys.exit(3)  # watchdog.py fails for one repository
if repo == "openamrobot-docs":
    open(args[args.index("--json") + 1], "w").write("{corrupt")  # report enrichment will fail
    sys.exit(0)
runpy.run_path(REAL, run_name="__main__")
"""


class FailClosed(unittest.TestCase):
    """CI/CD review of 8 Oct: an incomplete scan is never published as a clean complete result."""

    def test_happy_path_is_complete_and_passes(self):
        with tempfile.TemporaryDirectory() as keep:
            result = run_scan(fail_clones="", keep=keep)
            self.assertEqual(result.code, 0, result.output)
            self.assertIn("## OpenAMRobot Watchdog organization scan: COMPLETE", result.summary)
            self.assertNotIn("INCOMPLETE", result.summary)
            self.assertEqual(result.blocked, [])
            self.assertEqual(len(result.expected), 14)
            self.assertEqual(len(result.reports), 14)
            code, out = sync(keep)
            self.assertEqual(code, 0, out)
            self.assertIn("complete", out)
            self.assertNotIn("INCOMPLETE", out)

    def test_broken_repository_list_stops_the_scan(self):
        for label, text in (("broken", "organization: openAMRobot\nrepositories: [\n"), ("missing", False)):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as keep:
                result = run_scan(fail_clones="", repositories=text, keep=keep)
                self.assertNotEqual(result.code, 0, result.output)
                self.assertIn("## OpenAMRobot Watchdog organization scan: INCOMPLETE", result.summary)
                self.assertIn("Scan INCOMPLETE: repository list could not be generated.", result.summary)
                self.assertIn("::error::Scan INCOMPLETE: repository list could not be generated", result.output)
                self.assertNotIn(": COMPLETE", result.summary)
                self.assertIsNone(result.expected)
                self.assertEqual(result.reports, [])
                # The sync refuses to publish a clean dashboard without the expected list.
                code, out = sync(keep)
                self.assertEqual(code, 1, out)
                self.assertIn("the expected repository list could not be read", out)

    def test_short_repository_list_fails_and_missing_repositories_are_blocked(self):
        data = yaml.safe_load(LIST.read_text(encoding="utf-8"))
        del data["repositories"][3]["default_branch"]  # openamr-platform-hw cannot be listed
        with tempfile.TemporaryDirectory() as keep:
            result = run_scan(fail_clones="", repositories=yaml.safe_dump(data), keep=keep)
            self.assertEqual(result.code, 1, result.output)
            self.assertIn("Scan INCOMPLETE: repository list could not be generated (13 of 14 entries usable).", result.summary)
            self.assertEqual(len(result.expected), 14)
            code, out = sync(keep)
            self.assertEqual(code, 1, out)
            self.assertIn("INCOMPLETE, 0 of 14 repositories scanned", out)
            blocked, status = wis.completeness(result.expected, [], [])
            self.assertEqual({b["reason"] for b in blocked}, {"no report produced"})
            self.assertIn("openamr-platform-hw", {b["repository"] for b in blocked})

    def test_watchdog_and_enrichment_failures_block_only_their_repository(self):
        with tempfile.TemporaryDirectory() as keep:
            result = run_scan(fail_clones="", watchdog_wrapper=WRAPPER, keep=keep)
            self.assertEqual(result.code, 1, result.output)
            self.assertIn({"repository": "openamrobot-ui", "reason": "watchdog exit 3 at abc1234"}, result.blocked)
            self.assertIn({"repository": "openamrobot-docs", "reason": "report enrichment failed at abc1234"}, result.blocked)
            self.assertEqual(len(result.blocked), 2)
            self.assertIn("| openamrobot-ui | BLOCKED: watchdog exit 3 | not scanned |", result.summary)
            self.assertIn("| openamrobot-docs | BLOCKED: report enrichment failed | not scanned |", result.summary)
            self.assertIn("INCOMPLETE: 12 of 14 repositories scanned", result.summary)
            self.assertEqual(len(result.reports), 12)  # the corrupt report is set aside, not published
            self.assertNotIn("openamrobot-docs.json", result.reports)
            code, out = sync(keep)
            self.assertEqual(code, 1, out)
            self.assertIn("INCOMPLETE, 12 of 14 repositories scanned", out)

    def test_step_runs_with_errexit_and_pipefail(self):
        data, _ = workflow()
        for name in ("Scan repositories", "Synchronize Watchdog issues"):
            step = next(s for s in data["jobs"]["scan"]["steps"] if s["name"] == name)
            self.assertIn("set -euo pipefail", step["run"], name)
        sync_step = next(s for s in data["jobs"]["scan"]["steps"] if s["name"] == "Synchronize Watchdog issues")
        self.assertEqual(sync_step["if"], "always()")
        self.assertIn('--expected "$WORK/expected.json"', sync_step["run"])


if __name__ == "__main__":
    unittest.main()
