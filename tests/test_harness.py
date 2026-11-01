"""Tests for the AI harness: tools/harness_lib.py, tools/harness_guard.py,
tools/harness_select.py and harness/claude/hooks/guard_tool.py."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import harness_guard as guard  # noqa: E402
import harness_lib as hl  # noqa: E402
import harness_select as sel  # noqa: E402

HOOK = ROOT / "harness" / "claude" / "hooks" / "guard_tool.py"
POLICY = hl.load_policy(ROOT)


class Policy(unittest.TestCase):
    def test_policy_and_baseline_load(self):
        self.assertEqual(set(POLICY["tiers"]), {"A", "B", "C", "D"})
        self.assertIn("**/*estop*", POLICY["tiers"]["C"]["paths"], "maintainers safety_paths merge into tier C")
        baseline = hl.load_yaml(ROOT / "harness" / "baseline.yaml")
        self.assertTrue(baseline["p03"].startswith("P-03-rev"))

    def test_settings_grant_the_tools_automation_mode_needs(self):
        # In automation mode (a prompt input) Claude Code has no shell or edit tools unless
        # settings allow them; the PreToolUse hook is what narrows them.
        settings = json.loads((ROOT / "harness" / "claude" / "settings.json").read_text())
        for tool in ("Read", "Edit", "Write", "Bash", "Grep", "Glob"):
            self.assertIn(tool, settings["permissions"]["allow"])
        hook = settings["hooks"]["PreToolUse"][0]
        self.assertIn("Bash", hook["matcher"])
        self.assertIn("Edit", hook["matcher"])
        self.assertIn("guard_tool.py", hook["hooks"][0]["command"])

    def test_every_mission_prompt_exists(self):
        for name, mission in POLICY["missions"].items():
            if "prompt" in mission:
                self.assertTrue((ROOT / mission["prompt"]).is_file(), f"{name}: {mission['prompt']} missing")

    def test_every_skill_has_frontmatter(self):
        skills = sorted((ROOT / "harness" / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 10)
        for path in skills:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\nname: "), path)
            self.assertIn("\ndescription: ", text.split("---", 2)[1], path)
            self.assertNotIn("\u2014", text, f"{path}: em dash")

    def test_enrolled_repositories_match_rollout_list(self):
        rollout = hl.load_yaml(ROOT / "rollout" / "repositories.yaml")
        listed = {r["name"] for r in rollout["repositories"]}
        self.assertLessEqual(listed, set(POLICY["repositories"]), "every scanned repository has a harness entry")

    def test_harness_file_names_avoid_safety_globs(self):
        safety = hl.load_yaml(ROOT / "maintainers.yaml")["safety_paths"]
        for path in [*ROOT.glob("harness/**/*"), *ROOT.glob("tools/harness_*"), *ROOT.glob("tools/decision_*"),
                     *ROOT.glob("rollout/workflows/harness-*"), *ROOT.glob("tests/test_harness*"), *ROOT.glob(".claude-plugin/*")]:
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                self.assertFalse(hl.matches(rel, safety, broad=True), f"{rel} matches a safety path glob")


class Tiers(unittest.TestCase):
    def tier(self, path, repo="openamr-platform-sw"):
        return hl.tier_of(path, repo, POLICY)

    def test_tiers(self):
        self.assertEqual(self.tier("ros2/src/pkg/test/test_x.py"), "A")
        self.assertEqual(self.tier("README.md"), "A")
        self.assertEqual(self.tier("ros2/src/pkg/pkg/node.py"), "B")
        self.assertEqual(self.tier("ros2/src/pkg/package.xml"), "B")
        self.assertEqual(self.tier("ros2/src/openamrobot_docking/dock.py"), "C")
        self.assertEqual(self.tier("ros2/src/safety_monitor/node.py"), "C")
        self.assertEqual(self.tier("ros2/src/x/config/twist_mux.yaml"), "C")
        self.assertEqual(self.tier("src/main.c", "openamr-platform-fw"), "C")
        self.assertEqual(self.tier("AGENTS.md"), "D")
        self.assertEqual(self.tier(".github/CODEOWNERS"), "D")
        self.assertEqual(self.tier(".claude/settings.json"), "D")

    def test_robot_model_simulation_and_launch_files_are_tier_c(self):
        # Audit 2026-11-01 P2 and P9: these passed the guard as tier B.
        ub = "openamr-upperbody-sw"
        for path, repo in [
                ("ros2/src/openamrobot_bringup/launch/real_bringup.launch.py", "openamr-platform-sw"),
                ("ros2/src/openamrobot_nav2/launch/sim_bringup_launch.py", "openamr-platform-sw"),
                ("ros2/src/openamrobot_description/urdf/gazebo_control.xacro", "openamr-platform-sw"),
                ("ros2/src/openamrobot_description/urdf/robot.sdf", "openamr-platform-sw"),
                ("ros2/src/openamrobot_upperbody_description/urdf/upper_sensors.xacro", ub),
                ("ros2/src/openamrobot_upperbody_description/config/datums.yaml", ub),
                ("ros2/src/openamrobot_upperbody_description/config/upstream_pins.yaml", ub),
                ("ros2/src/openamrobot_upperbody_gazebo/worlds/empty.sdf", ub),
                ("ros2/src/openamrobot_upperbody_moveit/config/openamrobot.srdf", ub),
                ("ros2/src/openamrobot_upperbody_moveit/config/pilz_cartesian_limits.yaml", ub)]:
            self.assertEqual(self.tier(path, repo), "C", path)
        # New tests next to the model stay open to agents.
        self.assertEqual(self.tier("ros2/src/openamrobot_upperbody_description/test/test_new.py", ub), "A")
        self.assertTrue(hl.allowed_write("ros2/src/openamrobot_upperbody_description/test/test_new.py", ub, POLICY, False)[0])
        self.assertEqual(self.tier("ros2/src/openamrobot_upperbody_moveit/openamrobot_upperbody_moveit/acm_derive.py", ub), "B")

    def test_tier_c_allows_only_new_test_files(self):
        self.assertTrue(hl.allowed_write("ros2/src/openamrobot_docking/test/test_new.py", "openamr-platform-sw", POLICY, False)[0])
        self.assertFalse(hl.allowed_write("ros2/src/openamrobot_docking/test/test_old.py", "openamr-platform-sw", POLICY, True)[0])
        self.assertFalse(hl.allowed_write("ros2/src/openamrobot_docking/dock.py", "openamr-platform-sw", POLICY, False)[0])
        self.assertFalse(hl.allowed_write("decisions.yaml", ".github", POLICY, True)[0])


class Hook(unittest.TestCase):
    def run_hook(self, tool, data, read_only=False, project=None):
        project = project or tempfile.mkdtemp()
        env = dict(os.environ, CLAUDE_PROJECT_DIR=project, HARNESS_REPOSITORY="openamr-platform-sw",
                   HARNESS_READ_ONLY="1" if read_only else "0")
        proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": tool, "tool_input": data}),
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr

    def test_write_rules(self):
        self.assertEqual(self.run_hook("Write", {"file_path": "ros2/src/pkg/pkg/node.py"})[0], 0)
        code, err = self.run_hook("Edit", {"file_path": "ros2/src/openamrobot_docking/dock.py"})
        self.assertEqual(code, 2)
        self.assertIn("tier C", err)
        self.assertEqual(self.run_hook("Write", {"file_path": "AGENTS.md"})[0], 2)
        self.assertEqual(self.run_hook("Write", {"file_path": "/etc/passwd"})[0], 2)
        self.assertEqual(self.run_hook("Write", {"file_path": "../outside.txt"})[0], 2)

    def test_read_only_missions_write_only_output(self):
        self.assertEqual(self.run_hook("Write", {"file_path": "ros2/src/pkg/pkg/node.py"}, read_only=True)[0], 2)
        self.assertEqual(self.run_hook("Write", {"file_path": ".harness-out/findings.csv"}, read_only=True)[0], 0)
        self.assertEqual(self.run_hook("Bash", {"command": "git commit -s -m x"}, read_only=True)[0], 2)

    def test_bash_rules(self):
        self.assertEqual(self.run_hook("Bash", {"command": "colcon test --packages-select x"})[0], 0)
        for command in ["git push origin HEAD", "gh pr merge 3", "curl https://example.com", "printenv",
                        "git  push  --force"]:
            self.assertEqual(self.run_hook("Bash", {"command": command})[0], 2, command)
        project = tempfile.mkdtemp()
        Path(project, "ros2/src/openamrobot_docking").mkdir(parents=True)
        Path(project, "ros2/src/openamrobot_docking/dock.py").write_text("x\n")
        code, _ = self.run_hook("Bash", {"command": "sed -i s/x/y/ ros2/src/openamrobot_docking/dock.py"}, project=project)
        self.assertEqual(code, 2)
        code, _ = self.run_hook("Bash", {"command": "cat ros2/src/openamrobot_docking/dock.py"}, project=project)
        self.assertEqual(code, 0)

    def test_bad_input_fails_closed(self):
        proc = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


class Guard(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.write("ros2/src/pkg/pkg/node.py", "def f():\n    return 1\n")
        self.write("ros2/src/pkg/test/test_node.py", "def test_f():\n    assert True\n")
        self.write("ros2/src/openamrobot_docking/dock.py", "x = 1\n")
        self.commit("base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message, signoff=True):
        self.git("add", "-A")
        self.git("commit", "-q", *(["-s"] if signoff else []), "-m", message)

    def check(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = guard.main(["--repo-root", str(self.repo), "--repository", "openamr-platform-sw",
                               "--base", self.base, "--harness-root", str(ROOT), *extra])
        return code, json.loads(out.getvalue())

    def test_evidence_flag_rejects_a_pr_body_without_evidence(self):
        # Audit 2026-11-01 P1: a pr.md holding only a title passed the guard and became a draft PR.
        self.write("ros2/src/pkg/test/test_more.py", "def test_g():\n    assert 1 == 1\n")
        self.commit("test: add g")
        body = Path(tempfile.mkdtemp()) / "pr.md"
        body.write_text("# test: add g\n", encoding="utf-8")
        code, report = self.check("--pr-body", str(body), "--evidence")
        self.assertEqual(code, 1)
        self.assertTrue(any(f.startswith("PR body: Missing section: Tests") for f in report["failures"]), report)
        head = self.git("rev-parse", "HEAD").strip()
        body.write_text("\n".join([
            "# test: add g", "## Work package", "Issue #5, one regression test.",
            "## Integration Gate", "No overlapping PR; nothing reused.",
            "## Tests", "Ran 2 tests: 2 passed. Revert run: test_g fails without the change.",
            "## Evidence", f"Base SHA: {self.base}", f"Head SHA: {head}", "```", "python3 -m pytest -q", "```",
            "## Not verified", "No ROS build; next step: CI quality/test.",
            "## AI disclosure", "Claude Code via the openAMRobot harness, build mission, wrote the test.",
            ""]), encoding="utf-8")
        code, report = self.check("--pr-body", str(body), "--evidence")
        self.assertEqual(code, 0, report["failures"])

    def test_clean_test_change_passes_as_tier_a(self):
        self.write("ros2/src/pkg/test/test_more.py", "def test_g():\n    assert 1 == 1\n")
        self.commit("test: more")
        code, report = self.check("--tests-before", "1", "--tests-after", "2")
        self.assertEqual(code, 0, report)
        self.assertEqual(report["tier"], "A")

    def test_source_change_is_tier_b(self):
        self.write("ros2/src/pkg/pkg/node.py", "def f():\n    return 2\n")
        self.commit("fix")
        self.assertEqual(self.check()[1]["tier"], "B")

    def test_tier_c_change_fails(self):
        self.write("ros2/src/openamrobot_docking/dock.py", "x = 2\n")
        self.commit("change docking")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("tier C", " ".join(report["failures"]))

    def test_new_test_file_in_tier_c_area_passes(self):
        self.write("ros2/src/openamrobot_docking/test/test_dock.py", "def test_dock():\n    assert True\n")
        self.commit("test docking")
        self.assertEqual(self.check()[0], 0)

    def test_skip_without_issue_fails_and_with_issue_passes(self):
        marker = "@pytest.mark." + "skip"  # built at run time so verify.sh does not read this line as a skip
        self.write("ros2/src/pkg/test/test_skip.py", f"import pytest\n{marker}(reason='later')\ndef test_s():\n    pass\n")
        self.commit("skip")
        self.assertEqual(self.check()[0], 1)
        self.write("ros2/src/pkg/test/test_skip.py", f"import pytest\n{marker}(reason='needs sim, #88')\ndef test_s():\n    pass\n")
        self.commit("skip with issue")
        # The original untracked marker remains in the bundled commit history.
        self.assertEqual(self.check()[0], 1)

    def test_removed_test_fails(self):
        self.write("ros2/src/pkg/test/test_node.py", "# emptied\n")
        self.commit("remove test")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("test_f", " ".join(report["failures"]))

    def test_missing_signoff_fails(self):
        self.write("ros2/src/pkg/pkg/node.py", "def f():\n    return 3\n")
        self.commit("no signoff", signoff=False)
        self.assertEqual(self.check()[0], 1)

    def test_dependency_change_needs_section(self):
        self.write("ros2/src/pkg/package.xml", "<package/>\n")
        self.commit("deps")
        body = self.repo.parent / f"{self.repo.name}-pr.md"
        body.write_text("## Summary\n", encoding="utf-8")
        self.assertEqual(self.check("--pr-body", str(body))[0], 1)
        body.write_text("## Summary\n## Dependencies\n- none removed\n", encoding="utf-8")
        self.assertEqual(self.check("--pr-body", str(body))[0], 0)

    def test_falling_test_count_and_dirty_tree_fail(self):
        self.write("ros2/src/pkg/test/test_more.py", "def test_g():\n    assert True\n")
        self.commit("more")
        self.assertEqual(self.check("--tests-before", "5", "--tests-after", "4")[0], 1)
        self.write("ros2/src/pkg/pkg/stray.py", "x = 1\n")
        self.assertEqual(self.check()[0], 1)

    def test_secret_and_output_files_fail(self):
        self.write("ros2/src/pkg/pkg/conf.py", "TOKEN = 'ghp_" + "a" * 36 + "'\n")
        self.commit("secret")
        self.assertEqual(self.check()[0], 1)

    def test_no_change_fails(self):
        self.assertEqual(self.check()[0], 1)

    def test_guard_rejects_git_quoted_protected_path(self):
        # Git quotes a literal tab unless --name-status -z is used.
        self.write("harness/probe\t.md", "forbidden protected file\n")
        self.commit("add protected path with tab")
        code, report = self.check()
        self.assertEqual(code, 1, report)
        self.assertIn("harness/probe\t.md", report["files"])
        self.assertIn("tier D", " ".join(report["failures"]))

    def test_tier_ceiling_is_enforced_and_permitted_tiers_pass(self):
        self.write("ros2/src/pkg/pkg/node.py", "def f():\n    return 2\n")
        self.commit("change source")
        code, report = self.check("--max-tier", "A")
        self.assertEqual(code, 1)
        self.assertIn("maximum tier A", " ".join(report["failures"]))
        self.assertEqual(self.check("--max-tier", "B")[0], 0)

    def test_tier_ceiling_applies_to_every_published_commit(self):
        # Review of #76: a tier B source edit reverted in a later commit leaves a
        # test-only net diff, but both commits are transferred by the bundle.
        self.write("ros2/src/pkg/pkg/node.py", "def f():\n    return 2\n")
        self.commit("edit source")
        self.write("ros2/src/pkg/pkg/node.py", "def f():\n    return 1\n")
        self.write("ros2/src/pkg/test/test_new.py", "def test_new():\n    assert True\n")
        self.commit("revert source, add test")
        self.assertEqual(self.git("diff", "--name-only", f"{self.base}..HEAD").split(),
                         ["ros2/src/pkg/test/test_new.py"], "net diff is test-only")
        code, report = self.check("--max-tier", "A")
        self.assertEqual(code, 1, report)
        self.assertEqual(report["tier"], "B")
        self.assertIn("maximum tier A", " ".join(report["failures"]))
        self.assertEqual(self.check("--max-tier", "B")[0], 0)

    def test_test_line_removal_in_an_earlier_commit_counts_for_the_ceiling(self):
        self.write("ros2/src/pkg/test/test_node.py", "def test_f():\n    x = 1\n")
        self.commit("weaken a test")
        self.write("ros2/src/pkg/test/test_node.py", "def test_f():\n    assert True\n")
        self.commit("restore it")
        code, report = self.check("--max-tier", "A")
        self.assertEqual(code, 1, report)
        self.assertEqual(report["tier"], "B")

    def test_clean_tier_a_change_below_ceiling(self):
        self.write("ros2/src/pkg/test/test_more.py", "def test_g():\n    assert True\n")
        self.commit("new test")
        self.assertEqual(self.check("--max-tier", "A")[0], 0)

    def test_removing_assertion_from_existing_test_demotes_tier_a(self):
        # Existing test function is still present and test counts can be flat.
        self.write("ros2/src/pkg/test/test_node.py", "def test_f():\n    x = 1\n")
        self.commit("weaken a test")
        code, report = self.check("--tests-before", "1", "--tests-after", "1",
                                  "--max-tier", "A")
        self.assertEqual(code, 1, report)
        self.assertEqual(report["tier"], "B")
        self.assertIn("maximum tier A", " ".join(report["failures"]))

    def test_intermediate_committed_secret_rejected_even_when_removed(self):
        # Synthetic secret only: this object remains reachable in the bundle.
        path = "ros2/src/pkg/pkg/temp_key.py"
        self.write(path, "TOKEN = 'ghp_" + "A" * 36 + "'\n")
        self.commit("temporary token")
        (self.repo / path).unlink()
        self.write("ros2/src/pkg/test/test_more.py", "def test_g():\n    assert True\n")
        self.commit("remove token and add test")
        code, report = self.check("--max-tier", "A")
        self.assertEqual(code, 1, report)
        self.assertIn("secret-like string", " ".join(report["failures"]))

    def test_intermediate_protected_edit_rejected_when_reverted(self):
        path = "harness/temporary-policy.md"
        self.write(path, "protected\n")
        self.commit("touch protected path")
        (self.repo / path).unlink()
        self.write("ros2/src/pkg/test/test_more.py", "def test_g():\n    assert True\n")
        self.commit("remove protected path and add test")
        code, report = self.check()
        self.assertEqual(code, 1, report)
        self.assertIn("tier D path touched", " ".join(report["failures"]))

    def test_untracked_skip_in_original_commit_is_not_sanitized_by_fixup(self):
        path = "ros2/src/pkg/test/test_skipped.py"
        marker = "@pytest.mark." + "skip"
        self.write(path, f"import pytest\n{marker}(reason='later')\ndef test_x():\n    pass\n")
        self.commit("untracked skip")
        self.write(path, f"import pytest\n{marker}(reason='tracking #102')\ndef test_x():\n    pass\n")
        self.commit("document skip")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("untracked test skip", " ".join(report["failures"]))



class Select(unittest.TestCase):
    def issue(self, number, repo="openamrobot-manifest", names=("ai-ready",), body="", created="2026-10-01T00:00:00Z"):
        return {"number": number, "repository": repo, "title": f"issue {number}", "body": body,
                "labels": [{"name": n} for n in names], "created_at": created, "state": "open"}

    def pick(self, issues, pulls=(), enabled=True, stage=2):
        return sel.select(POLICY, ROOT, list(issues), list(pulls), enabled, stage)

    def test_switches(self):
        self.assertFalse(self.pick([self.issue(1)], enabled=False)["run"])
        self.assertFalse(self.pick([self.issue(1)], stage=1)["run"])

    def test_priority_then_age(self):
        result = self.pick([self.issue(1, created="2026-09-01T00:00:00Z"),
                            self.issue(2, names=("ai-ready", "rc.1"), created="2026-10-20T00:00:00Z"),
                            self.issue(3, names=("ai-ready", "rc.1", "priority:p0"), created="2026-10-25T00:00:00Z")])
        self.assertEqual(result["issue"], 3)

    def test_exclusions(self):
        issues = [self.issue(1, names=("ai-ready", "no-ai")), self.issue(2, names=("ai-ready", "needs-human:decision")),
                  self.issue(3, names=("ai-ready", "tier:C")), self.issue(4, repo="openamr-platform-fw"),
                  self.issue(5, names=("ai-ready", "ai-attempt:1", "ai-attempt:2")), self.issue(6, names=("bug",))]
        result = self.pick(issues)
        self.assertFalse(result["run"], result)

    def test_open_pr_limits(self):
        pr = lambda n, issue: {"number": n, "repository": "openamrobot-manifest", "state": "open",
                               "labels": [{"name": "ai-generated"}], "body": f"Closes #{issue}"}
        self.assertFalse(self.pick([self.issue(1)], [pr(10, 1)])["run"])
        self.assertFalse(self.pick([self.issue(2)], [pr(10, 1), pr(11, 3)])["run"])

    def test_register_drift_blocks_value_tasks(self):
        drift, in_force, p03, _ = sel.register_drift(ROOT)
        result = self.pick([self.issue(1, body="Align NEAR-FIELD-FRAMES values")])
        if drift:
            self.assertFalse(result["run"])
            self.assertIn("register", result["skipped"][0]["reason"])
        else:
            self.assertTrue(result["run"])
        self.assertTrue(self.pick([self.issue(2, body="add a unit test for the parser")])["run"])


if __name__ == "__main__":
    unittest.main()


class Coverage(unittest.TestCase):
    ORG = {".github", "openamr-platform-sw", "openamr-platform-fw", "openamr-platform-hw", "openamr-upperbody-sw",
           "openamr-upperbody-fw", "openamr-upperbody-hw", "openamrobot-interfaces", "openamrobot-manipulation",
           "openamrobot-ui", "openamrobot-comm", "openamrobot-docs", "openamrobot-manifest", "openamrobot-release",
           "openamrobot-embodied-ai", "audits", "openamr", "EOD-robot", "OpenAMR_UI_dev", "OpenAMR_UI_package"}

    def test_every_organization_repository_has_exactly_one_disposition(self):
        active = set(POLICY["repositories"])
        excluded = {e["name"] for e in POLICY["excluded"]}
        private = set(POLICY["private"])
        self.assertEqual(active | excluded | private, self.ORG)
        self.assertFalse(active & excluded or active & private or excluded & private)
        self.assertEqual(excluded, {"openamr", "EOD-robot", "OpenAMR_UI_dev", "OpenAMR_UI_package"})

    def test_core_rules_load_at_session_start_in_ci_and_in_the_plugin(self):
        settings = json.loads((ROOT / "harness" / "claude" / "settings.json").read_text())
        self.assertIn("CORE_RULES.md", settings["hooks"]["SessionStart"][0]["hooks"][0]["command"])
        plugin_hooks = json.loads((ROOT / "harness" / "hooks" / "hooks.json").read_text())
        self.assertIn("CORE_RULES.md", plugin_hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"])
        rules = (ROOT / "harness" / "CORE_RULES.md").read_text()
        self.assertLess(len(rules.splitlines()), 40, "core rules stay short enough to load every session")
        self.assertNotIn("\u2014", rules)

    def test_eval_suite_shape(self):
        cases = sorted(p for p in (ROOT / "harness" / "evals").iterdir() if p.is_dir() and p.name.startswith("e"))
        self.assertEqual(len(cases), 14)
        critical = 0
        for case in cases:
            prompt = (case / "prompt.md").read_text()
            self.assertTrue(prompt.startswith("---\n"), case)
            self.assertTrue((case / "case.yaml").is_file() and (case / "fixture.sh").is_file(), case)
            self.assertTrue(list((case / "graders").glob("*.md")), case)
            critical += "critical" in prompt.split("---")[1]
        self.assertEqual(critical, 13, "E01 to E12 and E14 are critical, E13 is the positive control")


class RouteGateTest(unittest.TestCase):
    """Runs the route step of harness-run.yml with bash, so README, policy and workflow agree."""

    def route(self, mission="", schedule="", stage="", publish="", now=""):
        wf = hl.load_yaml(ROOT / "rollout" / "workflows" / "harness-run.yml")
        script = wf["jobs"]["route"]["steps"][0]["run"]
        with tempfile.TemporaryDirectory() as tmp:
            out, summary = Path(tmp) / "out", Path(tmp) / "summary"
            env = dict(os.environ, SCHEDULE=schedule, INPUT=mission, STAGE=stage, PUBLISH=publish,
                       HARNESS_NOW=now, GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(summary))
            subprocess.run(["bash", "-c", script], env=env, check=True, capture_output=True)
            return dict(line.split("=", 1) for line in out.read_text().split())

    def test_manual_dry_run_runs_every_supervised_mission_at_any_stage(self):
        for stage in ("", "0", "1"):
            for mission, need in (("triage", "1"), ("build", "2"), ("review", "3")):
                r = self.route(mission=mission, stage=stage)
                self.assertEqual((r["mission"], r["dry_run"]), (mission, "true"), (stage, mission))
                self.assertGreaterEqual(int(r["stage"]), int(need))

    def test_one_audit_a_week_rotates_and_retro_is_monthly(self):
        # Budget plan "starter" (1 Nov 2026): one audit per week by ISO week number, retro on the
        # first Friday of the month only.
        seen = {self.route(schedule="23 3 * * 1", stage="1", publish="true", now=f"2026-11-{day:02d}")["mission"]
                for day in (2, 9, 16, 23, 30)}
        self.assertEqual(seen, {"dependencies", "contracts", "impact", "maintainability", "performance"})
        self.assertEqual(self.route(schedule="17 15 * * 5", stage="2", publish="true", now="2026-11-06")["mission"], "retro")
        self.assertEqual(self.route(schedule="17 15 * * 5", stage="2", publish="true", now="2026-11-13")["mission"], "none")
        crons = {c["cron"] for c in hl.load_yaml(ROOT / "rollout" / "workflows" / "harness-run.yml")[True]["schedule"]}
        self.assertEqual(sum(1 for c in crons if c.startswith("23 3 ")), 1, "one audit cron, not five")

    def test_stage_one_schedule_fits_the_weekly_turn_ceiling(self):
        budgets = POLICY["budgets"]
        weekly = (5 * budgets["triage"]["max_turns"]            # triage on weekdays
                  + budgets["audit"]["max_turns"]               # one rotating audit
                  + budgets["audit"]["max_turns"]               # register audit in openAMRobot/audits
                  + budgets["retro"]["max_turns"] / 4)          # monthly retro
        self.assertLessEqual(weekly, budgets["weekly_turn_ceiling"], weekly)
        self.assertEqual(budgets["plan"], "starter")

    def test_scheduled_ai_runs_are_skipped_without_publishing(self):
        self.assertEqual(self.route(schedule="7 5 * * 1-5", stage="4")["mission"], "none")
        self.assertEqual(self.route(schedule="52 5 * * *", stage="1")["mission"], "decision-followup")

    def test_stage_gates_apply_when_publishing(self):
        self.assertEqual(self.route(mission="build", stage="1", publish="true")["mission"], "none")
        self.assertEqual(self.route(mission="review", stage="2", publish="true")["mission"], "none")
        r = self.route(mission="triage", stage="1", publish="true")
        self.assertEqual((r["mission"], r["stage"], r["dry_run"]), ("triage", "1", "false"))

    def test_publish_steps_require_both_switches(self):
        text = (ROOT / "rollout" / "workflows" / "harness-run.yml").read_text()
        self.assertEqual(text.count('[ "${PUBLISH:-}" = true ] && [ "${DRY_RUN:-}" = false ] && apply=(--apply)'), 2)
        self.assertNotIn('[ "${PUBLISH:-}" = true ] && apply=(--apply)', text)

    def test_policy_documents_stage_zero(self):
        self.assertEqual(POLICY["stages"][0]["writes"], [])


class CoreRulesScopeTest(unittest.TestCase):
    RULES = (ROOT / "harness" / "CORE_RULES.md").read_text()

    def test_contract_rule_coordinates_one_pr_per_repository(self):
        self.assertIn("one PR per affected repository", self.RULES)

    def test_excluded_repositories_are_named_as_excluded(self):
        self.assertIn("excluded by owner decision", self.RULES)
        self.assertIn("never as clean or unscanned", self.RULES)

    def test_revert_test_applies_to_code_changes_only(self):
        self.assertIn("A code change carries a test that fails on revert", self.RULES)
        self.assertIn("Read-only work", self.RULES)


class AuditAHookAndSelect(unittest.TestCase):
    """Audit 2026-11-01 (run A) cases, kept against the run B implementation."""

    def test_bash_bypasses_found_by_the_audit_are_blocked(self):
        hook = Hook("test_bad_input_fails_closed")
        project = tempfile.mkdtemp()
        Path(project, "ros2/src/openamrobot_docking").mkdir(parents=True)
        Path(project, ".github/workflows").mkdir(parents=True)
        for command in ["/usr/bin/cur? -s https://example.com",
                        "git -c alias.p=push p origin HEAD",
                        "git -c core.hooksPath=/tmp/h commit -s -m x",
                        "git --config-env=core.hooksPath=X commit -s -m x",
                        "pushd ros2/src/openamrobot_docking && echo x > dock.py",
                        "find .github/workflows -name '*.yml' -exec sed -i s/a/b/ {} +",
                        "find ros2/src/openamrobot_docking -delete"]:
            self.assertEqual(hook.run_hook("Bash", {"command": command}, project=project)[0], 2, command)
        for command in ["find . -name '*.py' -exec grep -n x {} +", "git -C ros2 status",
                        "git commit -s -m 'test: x'", "pushd build && cmake .. ; popd"]:
            self.assertEqual(hook.run_hook("Bash", {"command": command}, project=project)[0], 0, command)

    def test_work_a_person_holds_is_not_selected(self):
        s = Select("test_register_drift_blocks_value_tasks")
        human = {"number": 19, "repository": "openamrobot-manifest", "state": "open", "labels": [],
                 "title": "fix(ci): validate advertised Git branch-tip pins (#12)", "body": ""}
        self.assertFalse(s.pick([s.issue(12)], [human])["run"])
        fixes = dict(human, title="ci: pins", body="Fixes #12")
        self.assertFalse(s.pick([s.issue(12)], [fixes])["run"])
        assigned = dict(s.issue(13), assignees=[{"login": "someone"}])
        self.assertFalse(s.pick([assigned])["run"])
        self.assertTrue(s.pick([s.issue(14)], [human])["run"], "an unrelated PR blocks nothing")
