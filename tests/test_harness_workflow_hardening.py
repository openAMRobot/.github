"""Regression tests from the 1 Nov 2026 effectiveness audit (openAMRobot/audits,
2026-11-01-harness-effectiveness): the agent session loaded the checked-out repository's own
.claude/settings.json (hooks next to the credential); the register audit ran without egress
limits; sim-analysis started an agent every night with no input; turn limits were hard-coded
in the workflow and had drifted from policy.yaml (retro 120 against 60)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import harness_budget  # noqa: E402
import harness_lib as hl  # noqa: E402

POLICY = hl.load_policy(ROOT)
RUN = ROOT / "rollout" / "workflows" / "harness-run.yml"
AUDIT = ROOT / "rollout" / "workflows" / "harness-register-audit.yml"
HIDE = ROOT / "rollout" / "hide-project-claude-config.sh"
MISSIONS = ["triage", "build", "review", "register-sync", "sim-analysis", "dependencies", "contracts",
            "impact", "performance", "maintainability", "retro", "register-audit"]


def step(job, name_part):
    return next(s for s in job["steps"] if name_part in (s.get("name") or s.get("uses") or ""))


class Budgets(unittest.TestCase):
    def test_every_ai_mission_has_a_policy_budget(self):
        for mission in MISSIONS:
            turns, minutes = harness_budget.budget(POLICY, mission)
            self.assertGreater(turns, 0, mission)
            self.assertGreater(minutes, 0, mission)
        self.assertEqual(harness_budget.budget(POLICY, "retro"), (60, 30))
        self.assertEqual(harness_budget.budget(POLICY, "build")[0], POLICY["budgets"]["build"]["max_turns"])

    def test_workflow_takes_turns_and_minutes_from_the_plan(self):
        wf = hl.load_yaml(RUN)
        agent = step(wf["jobs"]["agent"], "Agent")
        self.assertIn("needs.plan.outputs.max_turns", agent["with"]["claude_args"])
        self.assertNotIn("80 ||", agent["with"]["claude_args"])
        self.assertIn("needs.plan.outputs.timeout_minutes", str(agent.get("timeout-minutes")))
        self.assertIn("tools/harness_budget.py", wf["jobs"]["plan"]["steps"][-1]["run"])


class PlanSkipsSimAnalysis(unittest.TestCase):
    def test_sim_analysis_without_inputs_starts_no_agent(self):
        script = hl.load_yaml(RUN)["jobs"]["plan"]["steps"][-1]["run"]
        with tempfile.TemporaryDirectory() as tmp:
            os.symlink(ROOT / "tools", Path(tmp) / "tools")
            out, summary = Path(tmp) / "out", Path(tmp) / "summary"
            env = dict(os.environ, MISSION="sim-analysis", GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(summary))
            subprocess.run(["bash", "-c", script], cwd=tmp, env=env, check=True, capture_output=True)
            outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
            summary_text = summary.read_text()
        self.assertEqual(outputs["run"], "false")
        self.assertIn("NO SAFE TASK", summary_text)


class ProjectClaudeConfig(unittest.TestCase):
    def test_workspace_hides_the_checkout_configuration_before_the_session(self):
        run = step(hl.load_yaml(RUN)["jobs"]["agent"], "Workspace")["run"]
        self.assertIn("hide-project-claude-config.sh", run)
        self.assertLess(run.index("hide-project-claude-config.sh"), run.index("mkdir -p .claude/skills"))

    def test_hide_script_removes_settings_and_leaves_nothing_to_commit(self):
        with tempfile.TemporaryDirectory() as repo:
            g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@e.invalid", *a],
                                          check=True, capture_output=True, text=True).stdout  # noqa: E731
            g("init", "-q")
            Path(repo, ".claude/hooks").mkdir(parents=True)
            Path(repo, ".claude/settings.json").write_text('{"hooks": {"SessionStart": []}}')
            Path(repo, ".claude/hooks/x.sh").write_text("echo x\n")
            Path(repo, ".mcp.json").write_text("{}")
            Path(repo, "README.md").write_text("x\n")
            g("add", "-A"); g("commit", "-q", "-m", "base")
            subprocess.run(["bash", str(HIDE), repo], check=True, capture_output=True)
            self.assertFalse(Path(repo, ".claude/settings.json").exists())
            self.assertFalse(Path(repo, ".mcp.json").exists())
            g("add", "-A")
            self.assertEqual(g("status", "--porcelain"), "")


class RegisterAuditBudgetAndStage(unittest.TestCase):
    def test_register_audit_workflow_follows_the_audit_budget_and_the_stage(self):
        # Review finding 4 (4 Nov 2026): 120 turns hard-coded against budgets.audit 60 / 40,
        # no step timeout, and no HARNESS_STAGE check, so stage 0 with publishing on ran it.
        turns, minutes = harness_budget.budget(POLICY, "register-audit")
        job = hl.load_yaml(AUDIT)["jobs"]["audit"]
        agent = step(job, "Agent")
        self.assertIn(f"--max-turns {turns}", agent["with"]["claude_args"])
        self.assertNotIn("--max-turns 120", agent["with"]["claude_args"])
        self.assertEqual(agent.get("timeout-minutes"), minutes)
        self.assertGreaterEqual(job["timeout-minutes"], minutes + 5)
        self.assertLessEqual(job["timeout-minutes"], 60)
        self.assertIn("HARNESS_STAGE", job["if"])
        self.assertIn("HARNESS_PUBLISH == 'true' && fromJSON(vars.HARNESS_STAGE || '0') >= 1", job["if"])


class ConcurrencyPerMission(unittest.TestCase):
    # Route step mapping, mirrored by the workflow-level group expression.
    MISSION_OF = {"7 5 * * 1-5": "triage", "37 5 * * 1-5": "build", "37 11 * * 1-5": "build",
                  "0 6-20/2 * * 1-5": "review", "47 4 * * *": "sim-analysis", "52 5 * * *": "decision-followup",
                  "22 6 * * 1-5": "register-sync", "23 3 * * 1": "audit", "17 15 * * 5": "retro"}

    def test_group_is_the_mission_for_scheduled_and_manual_runs(self):
        # Review finding 6 (4 Nov 2026): the group was the raw cron for scheduled runs and the
        # input for manual ones, so two build runs could take the same issue.
        wf = hl.load_yaml(RUN)
        group = wf["concurrency"]["group"]
        self.assertFalse(wf["concurrency"]["cancel-in-progress"])
        crons = [entry["cron"] for entry in wf[True]["schedule"]]
        self.assertEqual(set(crons), set(self.MISSION_OF), "every cron in the workflow is mapped here")
        for cron in crons:
            self.assertIn(f"github.event.schedule == '{cron}' && '{self.MISSION_OF[cron]}'", group, cron)
        self.assertIn("|| inputs.mission", group)
        self.assertNotIn("github.event.schedule ||", group, "no bare fallback to the raw cron")
        self.assertNotIn("github.event.schedule }}", group)
        for name in ("agent", "publish"):
            self.assertNotIn("concurrency", wf["jobs"][name], "the workflow-level group covers both jobs")


class RegisterAuditEgress(unittest.TestCase):
    def test_register_audit_job_limits_egress_first(self):
        first = hl.load_yaml(AUDIT)["jobs"]["audit"]["steps"][0]
        self.assertTrue(first.get("uses", "").startswith("step-security/harden-runner@"))
        self.assertIn("EGRESS", first["with"]["egress-policy"])


if __name__ == "__main__":
    unittest.main()
