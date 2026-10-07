"""Run the harness steps of repository-quality-reusable.yml in enforce and warn-only mode.

The step scripts are taken from the workflow file itself and run with a fake harness whose
checkers print a finding and exit with a chosen status. This covers rollout step (c)
(harness_warn: report, never fail) and step (d) (harness_checks: true, blocking).
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repository-quality-reusable.yml"
HARNESS_STEPS = ["Check out OpenAMRobot harness", "Prepare harness checks", "Decisions of record",
                 "Public extract", "Shared agent rules"]


def load():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    inputs = data[True]["workflow_call"]["inputs"] if True in data else data["on"]["workflow_call"]["inputs"]
    steps = {s["name"]: s for s in data["jobs"]["repository-quality"]["steps"]}
    return inputs, steps


FAKE = """import sys
print("{line}")
print("result: 1 contradiction(s), 0 allowed, scope full checkout")
sys.exit({code})
"""


class HarnessModes(unittest.TestCase):
    def setUp(self):
        self.inputs, self.steps = load()

    def run_step(self, name, code, enforce, event="pull_request", tool="check_decisions.py"):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp, ".openamrobot-harness", "tools")
            tools.mkdir(parents=True)
            for t in ("check_decisions.py", "check_public_extract.py", "check_agent_rules.py"):
                line = "CONTRADICTION a.md:1: X found 'a'" if t == "check_decisions.py" else "PUBLIC-EXTRACT a.md:1: price: 5"
                (tools / t).write_text(FAKE.format(line=line, code=code if t == tool else 0), encoding="utf-8")
            Path(tmp, "AGENTS.md").write_text("x\n", encoding="utf-8")
            Path(tmp, "changed-files.txt").write_text("a.md\n", encoding="utf-8")
            env = dict(os.environ, EVENT_NAME=event, REPOSITORY="demo", ENFORCE="true" if enforce else "false",
                       RUNNER_TEMP=tmp)
            proc = subprocess.run(["bash", "-c", self.steps[name]["run"]], cwd=tmp, env=env,
                                  capture_output=True, text=True)
            return proc.returncode, proc.stdout + proc.stderr

    def test_inputs_default_off(self):
        self.assertFalse(self.inputs["harness_checks"]["default"])
        self.assertFalse(self.inputs["harness_warn"]["default"])

    def test_full_history_only_when_harness_checks_run(self):
        expr = str(self.steps["Check out repository"]["with"]["fetch-depth"])
        inner = expr.strip()
        self.assertTrue(inner.startswith("${{") and inner.endswith("}}"), expr)
        inner = inner[3:-2].replace("&&", " and ").replace("||", " or ")
        for checks in (False, True):
            for warn in (False, True):
                depth = eval(inner.replace("inputs.harness_checks", str(checks))  # noqa: S307 - test-only
                             .replace("inputs.harness_warn", str(warn)), {})
                with self.subTest(harness_checks=checks, harness_warn=warn):
                    self.assertEqual(str(depth), "0" if (checks or warn) else "1")

    def test_every_harness_step_runs_in_either_mode(self):
        for name in HARNESS_STEPS:
            self.assertEqual(self.steps[name]["if"], "inputs.harness_checks || inputs.harness_warn", name)

    def test_enforce_blocks_a_pull_request_finding(self):
        for name, tool in (("Decisions of record", "check_decisions.py"), ("Public extract", "check_public_extract.py")):
            with self.subTest(step=name):
                code, out = self.run_step(name, 1, enforce=True, tool=tool)
                self.assertEqual(code, 1, out)

    def test_warn_only_reports_but_never_fails(self):
        for name, tool in (("Decisions of record", "check_decisions.py"), ("Public extract", "check_public_extract.py"),
                           ("Shared agent rules", "check_agent_rules.py")):
            for status in (1, 2):
                with self.subTest(step=name, status=status):
                    code, out = self.run_step(name, status, enforce=False, tool=tool)
                    self.assertEqual(code, 0, out)
                    self.assertIn("::warning::", out)

    def test_enforce_on_push_warns_but_fails_on_invalid_register(self):
        code, out = self.run_step("Decisions of record", 1, enforce=True, event="push")
        self.assertEqual(code, 0, out)
        self.assertIn("::warning file=a.md,line=1::", out)
        self.assertEqual(self.run_step("Decisions of record", 2, enforce=True, event="push")[0], 2)

    def test_enforce_fails_on_shared_rules_drift(self):
        self.assertEqual(self.run_step("Shared agent rules", 1, enforce=True, tool="check_agent_rules.py")[0], 1)

    def test_clean_run_passes_in_both_modes(self):
        for enforce in (True, False):
            self.assertEqual(self.run_step("Decisions of record", 0, enforce=enforce)[0], 0)


if __name__ == "__main__":
    unittest.main()
