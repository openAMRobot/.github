"""Tests for the Watchdog organization scan: rollout/repositories.yaml and its workflow.

The scan step is taken from the workflow file and run with a fake `git` that creates small
local repositories, so no network is used.
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
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
  case "$dest" in *openamrobot-comm) exit 128;; esac
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

    def run_scan(self):
        data, _ = workflow()
        step = next(s for s in data["jobs"]["scan"]["steps"] if s["name"] == "Scan repositories")
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp, "bin")
            bin_dir.mkdir()
            git = bin_dir / "git"
            git.write_text(FAKE_GIT, encoding="utf-8")
            git.chmod(git.stat().st_mode | stat.S_IEXEC)
            os.symlink(ROOT, Path(tmp, "harness"))
            summary = Path(tmp, "summary.md")
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", HARNESS="harness",
                       WORK=str(Path(tmp, "work")), GITHUB_STEP_SUMMARY=str(summary),
                       REAL_GIT=shutil.which("git") or "/usr/bin/git",
                       WATCHDOG_ANNOTATIONS="0")
            proc = subprocess.run(["bash", "-c", step["run"]], cwd=tmp, env=env, capture_output=True, text=True)
            return proc, summary.read_text(encoding="utf-8")

    def test_scan_reports_every_repository_and_blocks_on_clone_failure(self):
        proc, summary = self.run_scan()
        # openamrobot-comm fails to clone in the fake: reported BLOCKED, job fails after the summary.
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("| openamrobot-comm | BLOCKED: clone failed | not scanned |", summary)
        rows = re.findall(r"^\| ([.\w-]+) \| abc1234 \| (\d+) \|$", summary, re.M)
        self.assertEqual(len(rows), 13)
        self.assertIn(("openamr-platform-sw", "1"), rows)
        self.assertIn("### openamr-platform-sw: 1 finding(s)", summary)
        self.assertIn("| COMPUTE | 1 |", summary)
        self.assertIn("Findings per decision or rule, per repository", summary)
        self.assertNotIn("::warning", proc.stdout)


if __name__ == "__main__":
    unittest.main()
