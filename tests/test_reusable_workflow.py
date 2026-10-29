"""Run the harness steps of repository-quality-reusable.yml in enforce and warn-only mode.

The step scripts are taken from the workflow file itself and run with a fake harness whose
checkers print a finding and exit with a chosen status. This covers rollout step (c)
(harness_warn: report, never fail) and step (d) (harness_checks: true, blocking).
"""
import os
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repository-quality-reusable.yml"
HARNESS_STEPS = ["Check out OpenAMRobot harness", "Prepare harness checks", "Workflow policy",
                 "Decisions of record", "Public extract", "Shared agent rules"]


def load():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    inputs = data[True]["workflow_call"]["inputs"] if True in data else data["on"]["workflow_call"]["inputs"]
    steps = {s["name"]: s for s in data["jobs"]["repository-quality"]["steps"]}
    return inputs, steps


FAKE = """import os, sys
print("{line}")
# Stand-in for tools/watchdog_report.emit_github: annotate at the level the step chose.
print("::" + os.environ.get("WATCHDOG_ANNOTATION", "unset") + " file=a.md,line=1::finding")
print("result: 1 contradiction(s), 0 allowed, scope full checkout")
sys.exit({code})
"""


def setUpModule():
    # Tests never write to the real GitHub Actions log or job summary of the CI run.
    patcher = unittest.mock.patch.dict(os.environ)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    for key in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "WATCHDOG_ANNOTATION", "WATCHDOG_ANNOTATIONS"):
        os.environ.pop(key, None)


class HarnessModes(unittest.TestCase):
    def setUp(self):
        self.inputs, self.steps = load()

    def run_step(self, name, code, enforce, event="pull_request", tool="check_decisions.py",
                 agents=True, exception=""):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp, ".openamrobot-harness", "tools")
            tools.mkdir(parents=True)
            for t in ("check_decisions.py", "check_public_extract.py", "check_agent_rules.py",
                       "check_workflow_policy.py"):
                line = ("Mismatch with approved decision: X (1 finding(s))" if t == "check_decisions.py"
                        else "Should not be public: price (1 finding(s))")
                (tools / t).write_text(FAKE.format(line=line, code=code if t == tool else 0), encoding="utf-8")
            if agents:
                Path(tmp, "AGENTS.md").write_text("x\n", encoding="utf-8")
            Path(tmp, "changed-files.txt").write_text("a.md\n", encoding="utf-8")
            env = dict(os.environ, EVENT_NAME=event, REPOSITORY="demo",
                       ENFORCE="true" if enforce else "false",
                       AGENTS_MD_EXCEPTION=exception, RUNNER_TEMP=tmp)
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

    def test_annotation_level_follows_enforcement(self):
        for name, tool in (("Decisions of record", "check_decisions.py"), ("Public extract", "check_public_extract.py"),
                           ("Workflow policy", "check_workflow_policy.py")):
            with self.subTest(step=name):
                self.assertIn("::error file=a.md,line=1::", self.run_step(name, 1, enforce=True, tool=tool)[1])
                self.assertIn("::warning file=a.md,line=1::",
                              self.run_step(name, 1, enforce=True, event="push", tool=tool)[1])
                self.assertIn("::warning file=a.md,line=1::", self.run_step(name, 1, enforce=False, tool=tool)[1])
        self.assertIn("::error file=a.md,line=1::",
                      self.run_step("Shared agent rules", 1, enforce=True, tool="check_agent_rules.py")[1])
        self.assertIn("::warning file=a.md,line=1::",
                      self.run_step("Shared agent rules", 1, enforce=False, tool="check_agent_rules.py")[1])

    def test_enforce_fails_on_shared_rules_drift(self):
        self.assertEqual(self.run_step("Shared agent rules", 1, enforce=True, tool="check_agent_rules.py")[0], 1)

    def test_enforce_requires_agents_file_or_exception(self):
        code, out = self.run_step("Shared agent rules", 0, enforce=True, agents=False)
        self.assertEqual(code, 1, out)
        self.assertIn("AGENTS.md is required", out)
        code, out = self.run_step("Shared agent rules", 0, enforce=True, agents=False,
                                   exception="legacy repository; migration tracked in #43")
        self.assertEqual(code, 0, out)
        self.assertIn("AGENTS.md exception", out)

    def test_clean_run_passes_in_both_modes(self):
        for enforce in (True, False):
            self.assertEqual(self.run_step("Decisions of record", 0, enforce=enforce)[0], 0)


class MergeMarkers(unittest.TestCase):
    """The "Reject unresolved merge markers" step, run from the workflow file in a scratch repository."""

    def run_marker_step(self, files):
        _, steps = load()
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                path = Path(tmp, rel)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-C", tmp]
            subprocess.run(["git", "init", "-q", tmp], check=True)
            subprocess.run(git + ["add", "-A"], check=True)
            subprocess.run(git + ["commit", "-q", "-m", "fixture"], check=True)
            proc = subprocess.run(["bash", "-c", steps["Reject unresolved merge markers"]["run"]], cwd=tmp,
                                  capture_output=True, text=True)
            return proc.returncode, proc.stdout + proc.stderr

    VENDORED = ("boards/stm32/X/Drivers/STM32H7xx_HAL_Driver/Src/hal.c",
                "boards/stm32/X/Drivers/CMSIS/Include/c.h",
                "boards/stm32/X/Drivers/BSP/STM32H7xx_Nucleo/b.c")
    PROJECT = ("src/Drivers/BSP/project.c", "src/Drivers/STM32Custom/project.c", "src/real.c")
    MARKER = "int a;\n=======\nint b;\n"

    def test_vendored_stm32cube_drivers_are_excluded_but_project_code_is_not(self):
        hal, cmsis, _ = self.VENDORED
        real = "src/real.c"
        code, out = self.run_marker_step({
            hal: "/*\n=======\n  ST documentation rule\n*/\n",
            cmsis: "/*\n=======\n*/\n",
            real: self.MARKER,
        })
        self.assertEqual(code, 1, out)
        self.assertIn(real, out)
        self.assertIn("Unresolved merge-conflict marker detected", out)
        self.assertNotIn(hal, out)
        self.assertNotIn(cmsis, out)

    def test_exact_stm32cube_vendor_trees_are_not_reported(self):
        for path in self.VENDORED:
            with self.subTest(path=path):
                code, out = self.run_marker_step({path: self.MARKER, "src/clean.c": "int a;\n"})
                self.assertEqual(code, 0, out)
                self.assertNotIn(path, out)

    def test_project_code_is_reported_even_under_a_drivers_directory(self):
        for path in self.PROJECT:
            with self.subTest(path=path):
                code, out = self.run_marker_step({path: self.MARKER})
                self.assertEqual(code, 1, out)
                self.assertIn(path, out)
                self.assertIn("Unresolved merge-conflict marker detected", out)

    def test_repository_without_markers_passes(self):
        code, out = self.run_marker_step({path: "int a;\n" for path in self.VENDORED + self.PROJECT})
        self.assertEqual(code, 0, out)
        self.assertNotIn("Unresolved merge-conflict marker detected", out)


if __name__ == "__main__":
    unittest.main()
