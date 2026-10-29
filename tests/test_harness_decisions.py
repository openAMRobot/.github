"""Tests for the decisions lifecycle: tools/decision_impact.py, the Decisions impact rule in
tools/check_pr_evidence.py, tools/decision_followup.py, register-sync selection and its
tier D exception, plus hook command matching and publish output validation."""
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
import check_pr_evidence as cpe  # noqa: E402
import decision_followup as dfu  # noqa: E402
import decision_impact as di  # noqa: E402
import harness_gh  # noqa: E402
import harness_guard as guard  # noqa: E402
import harness_inputs as hin  # noqa: E402
import harness_lib as hl  # noqa: E402
import harness_publish as pub  # noqa: E402
import harness_select as sel  # noqa: E402

POLICY = hl.load_policy(ROOT)
REGISTER = di.load(ROOT / "decisions.yaml")
HOOK = ROOT / "harness" / "claude" / "hooks" / "guard_tool.py"


def section(choice, rest=""):
    boxes = {"None": "- [ ] None: x", "Consumer": "- [ ] Consumer: x", "Change": "- [ ] Change: x"}
    if choice:
        boxes[choice] = f"- [x] {choice}: {rest}"
    return "\n".join(boxes.values())


def patch_file(name, added=(), removed=()):
    lines = ["@@ -1 +1 @@"] + [f"-{l}" for l in removed] + [f"+{l}" for l in added]
    return {"filename": name, "patch": "\n".join(lines)}


class Parse(unittest.TestCase):
    def test_choices(self):
        self.assertEqual(di.parse(section("None"))[0], "none")
        choice, ids, issues, errors = di.parse(section("Consumer", "uses COMPUTE and NAV-LIDAR"))
        self.assertEqual((choice, ids, errors), ("consumer", ["COMPUTE", "NAV-LIDAR"], []))
        choice, ids, issues, _ = di.parse(section("Change", "change request #12 (entry: NEW)"))
        self.assertEqual((choice, ids, issues), ("change", [], ["#12"]))

    def test_errors(self):
        self.assertEqual(di.parse(None)[3], ["missing"])
        self.assertIn("0 ticked", di.parse(section(None))[3][0])
        both = section("None") + "\n- [x] Change: #3"
        self.assertIn("2 ticked", di.parse(both)[3][0])

    def test_unchecked_template_comment_is_ignored(self):
        text = "<!-- - [x] None: example -->\n" + section("Consumer", "COMPUTE")
        self.assertEqual(di.parse(text)[0], "consumer")


class Fingerprints(unittest.TestCase):
    def test_register_values_and_noise(self):
        prints = {d["id"]: di.fingerprints(d) for d in REGISTER}
        self.assertIn("0.399", prints["NEAR-FIELD-FRAMES"], "values parsed as YAML mappings are still read")
        self.assertIn("MB7060", prints["NEAR-FIELD-FRAMES"])
        self.assertFalse(any(t.lower().startswith("rev") for p in prints.values() for t in p))
        self.assertNotIn("ros2", prints.get("EMBODIED-AI-REPO", set()))

    def test_touched_only_in_covered_files(self):
        files = [patch_file("ros2/src/x/urdf/sensors.xacro", added=['<origin xyz="0.390 0.130 -0.0066"/>']),
                 patch_file("ros2/src/x/x/node.py", added=["speed = 0.390"])]
        hits = di.touched(REGISTER, files, "openamr-platform-sw")
        self.assertIn("NEAR-FIELD-FRAMES", hits)
        self.assertTrue(all("sensors.xacro" in h or "node.py" in h for h in hits["NEAR-FIELD-FRAMES"]))

    def test_no_partial_number_match(self):
        files = [patch_file("README.md", added=["value 10.3901 and 20.390"])]
        hits = di.touched(REGISTER, files, "openamr-platform-sw")
        self.assertFalse(any("0.390" in h for h in hits.get("NEAR-FIELD-FRAMES", [])))


class Evaluate(unittest.TestCase):
    files = [patch_file("ros2/src/x/urdf/sensors.xacro", removed=['<origin xyz="0.3906 0.130 -0.0066"/>'],
                        added=['<origin xyz="0.390 0.130 -0.0066"/>'])]

    def run_eval(self, text, files=None, require=False):
        return di.evaluate(text, REGISTER, self.files if files is None else files, "openamr-platform-sw", require)

    def test_missing_section_warns_then_fails_when_required(self):
        f, w, _ = self.run_eval(None, files=[])
        self.assertEqual(f, [])
        self.assertIn("Missing section: Decisions impact", w[0])
        self.assertIn("Missing section: Decisions impact", self.run_eval(None, files=[], require=True)[0][0])

    def test_none_with_register_values_asks_the_author(self):
        f, w, _ = self.run_eval(section("None"))
        self.assertEqual(f, [])
        self.assertTrue(any("Decisions impact question" in x and "NEAR-FIELD-FRAMES" in x for x in w))

    def test_consumer_declared_is_a_note(self):
        f, w, n = self.run_eval(section("Consumer", "NEAR-FIELD-FRAMES"))
        self.assertEqual((f, w), ([], []))
        self.assertTrue(any("as declared" in x for x in n))

    def test_unknown_id_and_missing_request_fail(self):
        self.assertTrue(self.run_eval(section("Consumer", "NOT-AN-ENTRY"), files=[])[0])
        self.assertTrue(any("change request" in x for x in self.run_eval(section("Change", "entry COMPUTE"), files=[])[0]))
        self.assertEqual(self.run_eval(section("Change", "#5 entry COMPUTE"), files=[])[0], [])

    def test_consumer_without_ids_fails(self):
        self.assertTrue(any("needs the register entry IDs" in x for x in self.run_eval(section("Consumer", "stuff"), files=[])[0]))


class EvidenceIntegration(unittest.TestCase):
    def run_check(self, body, files):
        tmp = Path(tempfile.mkdtemp())
        event = {"pull_request": {"number": 1, "body": body, "head": {"sha": "a" * 40}, "user": {"login": "dev"},
                                  "draft": True, "requested_reviewers": []}}
        (tmp / "event.json").write_text(json.dumps(event))
        (tmp / "changed.txt").write_text("\n".join(f["filename"] for f in files))
        (tmp / "files.json").write_text(json.dumps(files))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = cpe.main(["--event", str(tmp / "event.json"), "--changed-files", str(tmp / "changed.txt"),
                             "--maintainers", str(ROOT / "maintainers.yaml"), "--decisions", str(ROOT / "decisions.yaml"),
                             "--files-json", str(tmp / "files.json"), "--repository", "openamr-platform-sw"])
        return code, out.getvalue()

    def body(self, impact):
        return ("## Summary\nx\n## Work package\n#1\n## Integration Gate\nnone open\n## Tests\nRan 3 tests\n"
                "## Evidence\nBase SHA: abcdef1\nHead SHA: aaaaaaa\n```\npytest\n```\n"
                f"## Decisions impact\n{impact}\n## Not verified\nnothing else\n## AI disclosure\nNone\n")

    def test_question_appears_in_the_summary(self):
        files = [patch_file("ros2/src/x/urdf/sensors.xacro", added=['<origin xyz="0.399 0 -0.0066"/>'])]
        code, out = self.run_check(self.body(section("None")), files)
        self.assertEqual(code, 0, out)
        self.assertIn("Decisions impact question", out)

    def test_bad_section_fails_the_check(self):
        code, out = self.run_check(self.body(section(None)), [])
        self.assertEqual(code, 1)
        self.assertIn("tick exactly one", out)

    def test_without_decisions_flag_nothing_changes(self):
        tmp = Path(tempfile.mkdtemp())
        event = {"pull_request": {"number": 1, "body": self.body(section(None)), "head": {"sha": "a" * 40},
                                  "user": {"login": "dev"}, "draft": True}}
        (tmp / "e.json").write_text(json.dumps(event))
        (tmp / "c.txt").write_text("")
        with contextlib.redirect_stdout(io.StringIO()):
            code = cpe.main(["--event", str(tmp / "e.json"), "--changed-files", str(tmp / "c.txt"),
                             "--maintainers", str(ROOT / "maintainers.yaml")])
        self.assertEqual(code, 0, "existing callers keep their behaviour")


class FakeAPI:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, url, body):
        self.calls.append((method, url, body))
        for (m, part), data in self.routes.items():
            if m == method and part in url:
                return 200, {}, data
        return (200, {}, []) if method == "GET" else (201, {}, {"number": 77, "html_url": "https://x/77", "id": 1})

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


def merged_pr(number, body, repo="openamr-platform-sw", sha="m" * 40):
    return {"number": number, "body": body, "title": f"pr {number}", "merged_at": "2099-01-01T00:00:00Z",
            "html_url": f"https://github.com/openAMRobot/{repo}/pull/{number}", "merge_commit_sha": sha}


class Followup(unittest.TestCase):
    def test_change_with_request_labels_and_comments_once(self):
        routes = {("GET", "/openamr-platform-sw/pulls?state=closed"): [merged_pr(9, "## Decisions impact\n- [x] Change: #4 entry COMPUTE")]}
        api = FakeAPI(routes)
        plan = []
        dfu.pass_changes(harness_gh.GitHub(token="t", transport=api), "openAMRobot", POLICY, "2000-01-01", plan)
        urls = [u for m, u, b in api.writes()]
        self.assertTrue(any(u.endswith("/openamr-platform-sw/issues/4/labels") for u in urls))
        self.assertTrue(any(u.endswith("/openamr-platform-sw/issues/4/comments") for u in urls))
        marker = dfu.MARK_PR.format(key="openamr-platform-sw#9")
        routes[("GET", "/issues/4/comments")] = [{"body": marker}]
        api2 = FakeAPI(routes)
        dfu.pass_changes(harness_gh.GitHub(token="t", transport=api2), "openAMRobot", POLICY, "2000-01-01", [])
        self.assertFalse([u for m, u, b in api2.writes() if "/issues/4/" in u], "idempotent")

    def test_change_without_request_opens_one_in_dotgithub(self):
        routes = {("GET", "/openamrobot-ui/pulls?state=closed"): [merged_pr(3, "## Decisions impact\n- [x] Change: entry COMPUTE", "openamrobot-ui")]}
        api = FakeAPI(routes)
        dfu.pass_changes(harness_gh.GitHub(token="t", transport=api), "openAMRobot", POLICY, "2000-01-01", [])
        created = [b for m, u, b in api.writes() if u.endswith("/.github/issues")]
        self.assertEqual(len(created), 1)
        self.assertIn("needs-human:register", created[0]["labels"])

    def test_none_and_consumer_do_nothing(self):
        routes = {("GET", "/openamr-platform-sw/pulls?state=closed"): [merged_pr(1, "## Decisions impact\n- [x] None: x"),
                                                                    merged_pr(2, "## Decisions impact\n- [x] Consumer: COMPUTE")]}
        api = FakeAPI(routes)
        dfu.pass_changes(harness_gh.GitHub(token="t", transport=api), "openAMRobot", POLICY, "2000-01-01", [])
        self.assertEqual(api.writes(), [])

    def test_changed_ids_from_git_history(self):
        repo = Path(tempfile.mkdtemp())
        run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout  # noqa: E731
        run("init", "-q")
        (repo / "decisions.yaml").write_text("decisions:\n  - {id: A, value: 1}\n  - {id: B, value: 2}\n")
        run("add", "-A")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "one")
        (repo / "decisions.yaml").write_text("decisions:\n  - {id: A, value: 1}\n  - {id: B, value: 3}\n  - {id: C, value: 4}\n")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "two")
        self.assertEqual(dfu.changed_ids(repo, run("rev-parse", "HEAD").strip()), ["B", "C"])

    def test_consumer_issue_tiers(self):
        pr = merged_pr(5, "", ".github")
        docs = dfu.consumer_issue(POLICY, "openamr-platform-sw", [{"file": "README.md", "line": 3, "id": "COMPUTE", "found": "Pi"}], ["COMPUTE"], pr)
        self.assertIn("ai-ready", docs["labels"])
        self.assertIn("tier:A", docs["labels"])
        safety = dfu.consumer_issue(POLICY, "openamr-platform-sw", [{"file": "ros2/src/openamrobot_docking/a.yaml", "line": 1, "id": "X", "found": "y"}], ["X"], pr)
        self.assertIn("needs-human:safety", safety["labels"])
        self.assertNotIn("ai-ready", safety["labels"])


class RegisterSync(unittest.TestCase):
    lead = hl.load_yaml(ROOT / "maintainers.yaml")["roles"]["platform-lead"]["handle"]

    def issue(self, number, names=("decision-approved", "contract-change")):
        return {"number": number, "repository": ".github", "title": f"req {number}", "created_at": f"2026-10-{number:02d}",
                "labels": [{"name": n} for n in names]}

    def events(self, actor):
        return [{"event": "labeled", "label": {"name": "decision-approved"}, "actor": {"login": actor}}]

    def test_only_the_platform_lead_approval_counts(self):
        pick = sel.select_register_sync(POLICY, ROOT, [self.issue(1), self.issue(2)],
                                        lambda n: self.events("someone-else" if n == 1 else self.lead), True, 2)
        self.assertEqual(pick["issue"], 2)
        self.assertIn("platform lead", pick["skipped"][0]["reason"])

    def test_open_register_pr_and_stage(self):
        self.assertFalse(sel.select_register_sync(POLICY, ROOT, [self.issue(1, ("decision-approved", "register-pr-open"))],
                                                  lambda n: self.events(self.lead), True, 2)["run"])
        self.assertFalse(sel.select_register_sync(POLICY, ROOT, [self.issue(1)], lambda n: self.events(self.lead), True, 1)["run"])

    def test_tier_d_exception_is_scoped(self):
        self.assertTrue(hl.allowed_write("decisions.yaml", ".github", POLICY, True, "register-sync")[0])
        self.assertFalse(hl.allowed_write("decisions.yaml", ".github", POLICY, True, "build")[0])
        self.assertFalse(hl.allowed_write("decisions.yaml", "openamr-platform-sw", POLICY, True, "register-sync")[0])
        self.assertFalse(hl.allowed_write("maintainers.yaml", ".github", POLICY, True, "register-sync")[0])

    def test_hook_and_guard_honour_the_exception(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=tempfile.mkdtemp(), HARNESS_REPOSITORY=".github", HARNESS_READ_ONLY="0")
        call = lambda mission: subprocess.run([sys.executable, str(HOOK)], input=json.dumps(  # noqa: E731
            {"tool_name": "Edit", "tool_input": {"file_path": "decisions.yaml"}}), capture_output=True, text=True,
            env=dict(env, HARNESS_MISSION=mission)).returncode
        self.assertEqual(call("register-sync"), 0)
        self.assertEqual(call("build"), 2)
        repo = Path(tempfile.mkdtemp())
        git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout  # noqa: E731
        git("init", "-q")
        git("config", "user.name", "t")
        git("config", "user.email", "t@t")
        (repo / "decisions.yaml").write_text("a: 1\n")
        git("add", "-A")
        git("commit", "-qsm", "base")
        base = git("rev-parse", "HEAD").strip()
        (repo / "decisions.yaml").write_text("a: 2\n")
        git("commit", "-qsam", "decisions: change")
        for mission, expected in (("register-sync", 0), ("build", 1)):
            with contextlib.redirect_stdout(io.StringIO()):
                code = guard.main(["--repo-root", str(repo), "--repository", ".github", "--base", base,
                                   "--harness-root", str(ROOT), "--mission", mission])
            self.assertEqual(code, expected, mission)


class HookCommands(unittest.TestCase):
    def code(self, command):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=tempfile.mkdtemp(), HARNESS_REPOSITORY="openamr-platform-sw", HARNESS_READ_ONLY="0")
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                              capture_output=True, text=True, env=env).returncode

    def test_reviewer_bypasses_are_closed(self):
        project = tempfile.mkdtemp()
        Path(project, "firmware").mkdir()
        Path(project, "firmware", "a.c").write_text("x")
        Path(project, ".harness-out").mkdir()
        env = dict(os.environ, CLAUDE_PROJECT_DIR=project, HARNESS_REPOSITORY="openamr-platform-sw", HARNESS_READ_ONLY="0")
        call = lambda tool, data, ro="0": subprocess.run([sys.executable, str(HOOK)], input=json.dumps(  # noqa: E731
            {"tool_name": tool, "tool_input": data}), capture_output=True, text=True, env=dict(env, HARNESS_READ_ONLY=ro)).returncode
        for command in ["python3 -c \"open('firmware/a.c','w')\"", "echo x>firmware/a.c", "cd firmware && echo x > a.c",
                        "cat /proc/$PPID/environ", "env | grep TOKEN", "\"curl\" -s x", "c\\url x",
                        "cp evil.py .harness/tools/harness_guard.py", "sed -i s/a/b/ .harness/harness/policy.yaml"]:
            self.assertEqual(call("Bash", {"command": command}), 2, command)
        os.symlink(os.path.join(project, "firmware", "a.c"), os.path.join(project, ".harness-out", "l"))
        self.assertEqual(call("Write", {"file_path": ".harness-out/l"}), 2, "symlink judged by its target")
        self.assertEqual(call("Write", {"file_path": ".harness-out/l"}, ro="1"), 2)
        for command in ["python3 -c \"import pathlib; pathlib.Path('firmware/a.c').write_text('x')\"",
                        "echo x > firmware/a.c; cd src", "cp -t firmware src/a.py", "tar -C firmware -xf a.tar",
                        "git apply x.patch", "patch -p1 < x.patch", "env -0", "cat /proc/$PPID/env*ron",
                        "python3 -c \"import os;print(os.environ)\"", "C=c; ${C}url x", "$(echo curl) x"]:
            self.assertEqual(call("Bash", {"command": command}), 2, command)
        for command in ["python3 .harness/tools/check_decisions.py --help", "pytest firmware/test_x.py > .harness-out/log 2>&1",
                        "rm -rf build install log", "set -euo pipefail", "colcon test 2>&1 | tee .harness-out/t.log",
                        "for target in a b; do echo $target; done", "echo $hash $commit $limit",
                        "mkdir -p build && cd build && cmake ..", "xacro model.xacro > /tmp/x.urdf",
                        "git add -A && git commit -s -m 'test: x'"]:
            self.assertEqual(call("Bash", {"command": command}), 0, command)
        for command in ["mkdir -p build && cd build && cmake ..", "colcon build --symlink-install 2>&1 | tail -5"]:
            self.assertEqual(call("Bash", {"command": command}, ro="1"), 0, f"read only: {command}")

    def test_word_boundaries(self):
        for allowed in ["rsync -a a b", "ros2 run xacro xacro x.xacro", "pio run -e native", "git status", "echo sync"]:
            self.assertEqual(self.code(allowed), 0, allowed)
        for blocked in ["cd x && git push origin", "xargs curl -s", "ls | nc host 1", "git commit --no-verify -m x",
                        "pio run -t upload", "sudo git push", "$(curl x)", "openocd -f board.cfg"]:
            self.assertEqual(self.code(blocked), 2, blocked)


class PublishValidation(unittest.TestCase):
    def test_malformed_triage_applies_nothing(self):
        out = tempfile.mkdtemp()
        Path(out, "triage.json").write_text(json.dumps({"label": "not a list", "create": {}, "digest": "x"}))
        api = FakeAPI({})
        p = pub.Publisher(harness_gh.GitHub(token="t", transport=api), "openAMRobot", out, {}, "r", POLICY, True, bot="b[bot]")
        p.run("triage")
        writes = api.writes()
        self.assertEqual(len(writes), 1, "only the digest")
        self.assertIn("malformed", writes[0][2]["body"])

    def test_unknown_status_becomes_stuck(self):
        out = tempfile.mkdtemp()
        Path(out, "result.json").write_text(json.dumps({"status": "merge-it-now"}))
        api = FakeAPI({("GET", "/issues/5"): {"labels": []}})
        p = pub.Publisher(harness_gh.GitHub(token="t", transport=api), "openAMRobot", out,
                          {"repository": "openamrobot-manifest", "issue": 5}, "r", POLICY, True)
        p.run("build")
        self.assertTrue(any("Status: stuck" in (b or {}).get("body", "") for m, u, b in api.writes()))

    def test_register_sync_labels(self):
        out = tempfile.mkdtemp()
        Path(out, "result.json").write_text(json.dumps({"status": "done"}))
        Path(out, "guard.json").write_text(json.dumps({"result": "PASS", "tier": "B"}))
        Path(out, "pr.md").write_text("# decisions: COMPUTE x (P-03-rev20.0 item 1)\n\nbody\n")
        api = FakeAPI({("GET", "/issues/8"): {"labels": [{"name": "decision-approved"}]},
                       ("GET", "/repos/openAMRobot/.github"): {"default_branch": "main"}})
        p = pub.Publisher(harness_gh.GitHub(token="t", transport=api), "openAMRobot", out,
                          {"repository": ".github", "issue": 8}, "r", POLICY, True)
        p.push_bundle = lambda repo, branch: p.plan.append(f"pushed {branch}")
        plan = p.run("register-sync")
        self.assertTrue(any(line.startswith("pushed register/8-") for line in plan), plan)
        labels = [set(b["labels"]) for m, u, b in api.writes() if u.endswith("/labels")]
        self.assertIn({"register-pr-open"}, labels)
        self.assertIn({"ai-generated", "tier:B", "register-change"}, labels)


class Inputs(unittest.TestCase):
    def test_snapshots_without_list_or_token_are_not_measured(self):
        workspace = Path(tempfile.mkdtemp())
        (workspace / ".harness").symlink_to(ROOT)
        inp = workspace / ".harness-in"
        inp.mkdir()
        self.assertIn("not_measured", hin.snapshots(workspace, "openAMRobot", inp)[0])


if __name__ == "__main__":
    unittest.main()


class Outputs(unittest.TestCase):
    def test_allowlist_and_secret_scrub(self):
        import harness_outputs as ho
        src, dst = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "up"
        (src / "pr.md").write_text("# fine\n")
        (src / "review.md").write_text("token is SECRETVALUE123 here\n")
        (src / "env.txt").write_text("anything\n")
        (src / "report.md").write_text("key ghp_" + "b" * 36 + "\n")
        os.symlink(src / "pr.md", src / "result.json")
        report = ho.copy(src, dst, [b"SECRETVALUE123"])
        self.assertEqual(report["copied"], ["pr.md"])
        reasons = {d["file"]: d["reason"] for d in report["dropped"]}
        self.assertIn("secret", reasons["review.md"])
        self.assertIn("allowlist", reasons["env.txt"])
        self.assertIn("secret", reasons["report.md"])
        self.assertIn("regular file", reasons["result.json"])
        self.assertEqual(sorted(p.name for p in dst.iterdir()), ["outputs.json", "pr.md"])
