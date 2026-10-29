"""Tests for tools/harness_publish.py, harness_review_queue.py, harness_merge_gate.py
and harness_inputs.py against a fake GitHub API (no network)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import harness_gh  # noqa: E402
import harness_inputs as hin  # noqa: E402
import harness_lib as hl  # noqa: E402
import harness_merge_gate as gate  # noqa: E402
import harness_publish as pub  # noqa: E402
import harness_review_queue as rq  # noqa: E402

POLICY = hl.load_policy(ROOT)
HEAD = "a" * 40
BOT = "openamrobot-harness[bot]"
BOT_USER = {"login": BOT, "type": "Bot"}
PERSON = {"login": "someone", "type": "User"}


class FakeAPI:
    """routes: {(method, url substring): data}; records every call."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, url, body):
        self.calls.append((method, url, body))
        for (m, part), data in self.routes.items():
            if m == method and part in url:
                return 200, {}, data
        return (200, {}, []) if method == "GET" else (201, {}, {"number": 99, "html_url": "https://x/pr/99", "id": 1})

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


def publisher(routes, out, target, mission_files):
    for name, content in mission_files.items():
        Path(out, name).write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    api = FakeAPI(routes)
    gh = harness_gh.GitHub(token="t", transport=api)
    p = pub.Publisher(gh, "openAMRobot", out, target, "https://run", POLICY, apply=True, bot=BOT, run_id="42")
    p.push_bundle = lambda repo, branch: p.plan.append(f"pushed {branch}")
    return p, api


class Build(unittest.TestCase):
    target = {"repository": "openamrobot-manifest", "issue": 5, "title": "add tests", "tier": "A"}
    issue = {("GET", "/issues/5"): {"labels": [{"name": "ai-ready"}]},
             ("GET", "/repos/openAMRobot/openamrobot-manifest"): {"default_branch": "main"}}

    def test_done_and_guard_pass_opens_draft_pr(self):
        out = tempfile.mkdtemp()
        p, api = publisher(dict(self.issue), out, self.target, {
            "result.json": {"status": "done"}, "guard.json": {"result": "PASS", "tier": "A"},
            "pr.md": "# test: cover manifest parser\n\n## Summary\nx\n"})
        p.run("build")
        posts = api.writes()
        pr = [b for m, u, b in posts if u.endswith("/pulls")][0]
        self.assertTrue(pr["draft"])
        self.assertEqual(pr["title"], "test: cover manifest parser")
        self.assertTrue(pr["head"].startswith("ai/5-") and pr["head"].endswith("-42"))
        self.assertIn("Refs #5", pr["body"], "the issue link is added when the agent forgot it")
        labels = [b["labels"] for m, u, b in posts if u.endswith("/issues/99/labels")][0]
        self.assertEqual(set(labels), {"ai-generated", "tier:A"})
        self.assertIn(["ai-attempt:1"], [b["labels"] for m, u, b in posts if u.endswith("/issues/5/labels")])

    def test_guard_fail_comments_and_never_pushes(self):
        out = tempfile.mkdtemp()
        p, api = publisher(dict(self.issue), out, self.target, {
            "result.json": {"status": "done"}, "guard.json": {"result": "FAIL", "failures": ["x: tier C"]}})
        plan = p.run("build")
        self.assertFalse(any("pushed" in line for line in plan))
        self.assertFalse(any(u.endswith("/pulls") for m, u, b in api.writes()))
        self.assertTrue(any("tier C" in (b or {}).get("body", "") for m, u, b in api.writes()))

    def test_escalation_labels_and_removes_ai_ready(self):
        out = tempfile.mkdtemp()
        p, api = publisher(dict(self.issue), out, self.target, {
            "result.json": {"status": "safety", "summary": "needs docking change"},
            "needs-human.md": "Question: who changes dock_trigger?"})
        p.run("build")
        added = [set(b["labels"]) for m, u, b in api.writes() if m == "POST" and u.endswith("/labels")]
        self.assertIn({"needs-human:safety", "needs-human"}, added)
        self.assertTrue(any(m == "DELETE" and u.endswith("/labels/ai-ready") for m, u, b in api.writes()))


class Review(unittest.TestCase):
    def test_comment_marker_and_safety_override(self):
        out = tempfile.mkdtemp()
        target = {"repository": "openamr-platform-sw", "pr": 7, "head": HEAD}
        p, api = publisher({}, out, target, {
            "verdict.json": {"verdict": "pass", "tier": "A", "safety_path": True},
            "review.md": "<!-- harness-review head=x -->\nverdict line\n- finding"})
        p.run("review")
        body = api.writes()[0][2]["body"]
        self.assertTrue(body.startswith(f"<!-- harness-review head={HEAD} verdict=block tier=C -->"))

    def test_existing_comment_is_updated(self):
        out = tempfile.mkdtemp()
        target = {"repository": "openamr-platform-sw", "pr": 7, "head": HEAD}
        routes = {("GET", "/issues/7/comments"): [{"id": 41, "user": PERSON, "body": "<!-- harness-review head=old verdict=pass tier=A -->"},
                                                  {"id": 42, "user": BOT_USER, "body": "<!-- harness-review head=old verdict=pass tier=A -->"}]}
        p, api = publisher(routes, out, target, {"verdict.json": {"verdict": "concerns", "tier": "B"}, "review.md": "x"})
        p.run("review")
        self.assertEqual(api.writes()[0][0], "PATCH")
        self.assertTrue(api.writes()[0][1].endswith("/issues/comments/42"), "never the forged comment 41")


class Triage(unittest.TestCase):
    def test_only_allowed_labels_and_caps(self):
        out = tempfile.mkdtemp()
        triage = {"label": [{"repository": "openamrobot-manifest", "issue": 3,
                             "add": ["ai-ready", "tier:A", "rc.1", "ai-generated", "hold", "random"],
                             "remove": ["needs-human:safety", "ai-ready"]},
                            {"repository": "not-a-repo", "issue": 1, "add": ["ai-ready"]}],
                  "create": [{"repository": "openamrobot-manifest", "title": f"t{i}", "labels": ["ai-ready"]} for i in range(9)],
                  "digest": "Needs you: nothing"}
        p, api = publisher({}, out, {}, {"triage.json": triage})
        p.run("triage")
        writes = api.writes()
        labelled = [set(b["labels"]) for m, u, b in writes if u.endswith("/issues/3/labels")][0]
        self.assertEqual(labelled, {"ai-ready", "tier:A", "rc.1"})
        self.assertFalse(any("needs-human" in u for m, u, b in writes if m == "DELETE"))
        self.assertFalse(any("not-a-repo" in u for m, u, b in writes))
        created = [b for m, u, b in writes if m == "POST" and u.endswith("/openamrobot-manifest/issues")]
        self.assertEqual(len(created), 5)
        self.assertTrue(any(b and b.get("title") == pub.DIGEST_TITLE for m, u, b in writes))


class Audit(unittest.TestCase):
    def test_prefix_scopes_no_longer_detected(self):
        out = tempfile.mkdtemp()
        Path(out, "findings.csv").write_text(
            "id,severity,area,repository,file_to_change,value_a,value_b,decision_of_record,fix\n"
            "SW-1001,Major,topics,openamr-platform-sw,openamr-platform-sw/README.md,a,b,,fix it\n", encoding="utf-8")
        existing = {"items": [
            {"repository_url": "https://api.github.com/repos/openAMRobot/openamrobot-ui", "number": 4,
             "title": "[audit] SW-1009: old", "state": "open"},
            {"repository_url": "https://api.github.com/repos/openAMRobot/openamrobot-ui", "number": 5,
             "title": "[audit] SW-3002: other audit", "state": "open"}]}
        p, api = publisher({("GET", "/search/issues"): existing}, out, {}, {})
        p.run("contracts")
        urls = [u for m, u, b in api.writes()]
        self.assertTrue(any(u.endswith("/openamr-platform-sw/issues") for u in urls))
        self.assertTrue(any("/issues/4/comments" in u for u in urls))
        self.assertFalse(any("/issues/5/comments" in u for u in urls), "other audits' findings are left alone")


class TriageValidation(unittest.TestCase):
    def test_bad_items_are_skipped_and_the_digest_still_written(self):
        out = tempfile.mkdtemp()
        triage = {"label": [{"repository": "openamrobot-manifest", "issue": "1/../../x", "add": ["ai-ready"]},
                            {"repository": "openamrobot-manifest", "add": ["ai-ready"]}, "junk"],
                  "create": [{"repository": "openamrobot-manifest", "title": ""}], "digest": "d"}
        p, api = publisher({}, out, {}, {"triage.json": triage})
        p.run("triage")
        urls = [u for m, u, b in api.writes()]
        self.assertFalse(any("/x" in u or "/labels" in u for u in urls))
        self.assertTrue(any(b and b.get("title") == pub.DIGEST_TITLE for m, u, b in api.writes()))


class ArtifactBoundary(unittest.TestCase):
    def test_symlinked_outputs_are_ignored(self):
        out = Path(tempfile.mkdtemp())
        secret = Path(tempfile.mkdtemp()) / "secret.json"
        secret.write_text(json.dumps({"status": "done"}))
        os.symlink(secret, out / "result.json")
        self.assertEqual(pub.read_json(out / "result.json"), {})


class Retro(unittest.TestCase):
    def test_patch_outside_skills_is_rejected(self):
        out = tempfile.mkdtemp()
        p, api = publisher({}, out, {}, {"retro.patch": "--- a/harness/policy.yaml\n+++ b/harness/policy.yaml\n@@\n-x\n+y\n"})
        plan = p.run("retro")
        self.assertTrue(any("rejected" in line for line in plan))
        self.assertEqual(api.writes(), [])


class ReviewQueue(unittest.TestCase):
    def pr(self, number, repo="openamr-platform-sw", labels=(), draft=False, fork=False, updated="2026-10-01"):
        return {"number": number, "draft": draft, "labels": [{"name": n} for n in labels], "updated_at": updated,
                "head": {"sha": f"{number:040d}", "repo": {"full_name": "someone/fork" if fork else f"openAMRobot/{repo}"}},
                "base": {"sha": "b" * 40}}

    def test_queue_rules(self):
        prs = [self.pr(1), self.pr(2, labels=("no-ai",)), self.pr(3, draft=True), self.pr(4, fork=True),
               self.pr(5, fork=True, labels=("ai-review",)), self.pr(6, draft=True, labels=("ai-generated",), updated="2026-10-20"),
               self.pr(7)]
        routes = {("GET", "/openamr-platform-sw/pulls?"): prs,
                  ("GET", "/issues/7/comments"): [{"user": BOT_USER, "body": f"<!-- harness-review head={7:040d} verdict=pass tier=A -->"}],
                  ("GET", "/issues/1/comments"): [{"user": PERSON, "body": f"<!-- harness-review head={1:040d} verdict=pass tier=A -->"}]}
        api = FakeAPI(routes)
        queue = rq.queue(POLICY, harness_gh.GitHub(token="", transport=api), "openAMRobot", 10, bot=BOT)
        numbers = [q["pr"] for q in queue if q["repository"] == "openamr-platform-sw"]
        self.assertEqual(numbers, [6, 1, 5], "a person's forged marker on #1 does not count as reviewed")


class MergeGate(unittest.TestCase):
    now = dt.datetime(2026, 11, 2, 12, tzinfo=dt.timezone.utc)

    def args(self, **over):
        pr = {"labels": [{"name": "ai-generated"}, {"name": "tier:A"}], "head": {"sha": HEAD}}
        values = dict(pr=pr, files=[{"filename": "tests/test_x.py"}],
                      comments=[{"user": BOT_USER, "body": f"<!-- harness-review head={HEAD} verdict=pass tier=A -->"}],
                      checks={"check_runs": [{"status": "completed", "conclusion": "success"}]}, reviews=[],
                      head_commit_time=self.now - dt.timedelta(hours=30), repository="openamrobot-manifest",
                      policy=POLICY, now=self.now, bot=BOT)
        values.update(over)
        return values

    def test_all_conditions_merge(self):
        self.assertEqual(gate.decide(**self.args()), [])

    def test_each_condition_blocks(self):
        cases = [dict(files=[{"filename": "src/x.py"}]),
                 dict(comments=[{"user": BOT_USER, "body": f"<!-- harness-review head={HEAD} verdict=concerns tier=A -->"}]),
                 dict(comments=[{"user": PERSON, "body": f"<!-- harness-review head={HEAD} verdict=pass tier=A -->"}]),
                 dict(checks={"check_runs": [{"status": "completed", "conclusion": "failure"}]}),
                 dict(checks={"check_runs": []}),
                 dict(reviews=[{"state": "CHANGES_REQUESTED"}]),
                 dict(head_commit_time=self.now - dt.timedelta(hours=2)),
                 dict(repository="openamr-platform-sw"),
                 dict(pr={"labels": [{"name": "ai-generated"}, {"name": "tier:A"}, {"name": "hold"}], "head": {"sha": HEAD}})]
        for case in cases:
            self.assertTrue(gate.decide(**self.args(**case)), case)


class Inputs(unittest.TestCase):
    def test_unreadable_inputs_are_marked_not_measured(self):
        workspace = Path(tempfile.mkdtemp())
        (workspace / ".harness").symlink_to(ROOT)

        def failing(method, url, body):
            return 403, {}, {"message": "forbidden"}
        gh = harness_gh.GitHub(token="", transport=failing)
        files = hin.collect("triage", {}, workspace, "openAMRobot", gh, POLICY)
        self.assertIn("daily.json", files)
        self.assertIn("not_measured", json.loads((workspace / ".harness-in" / "daily.json").read_text()))
        self.assertIn("not_measured", json.loads((workspace / ".harness-in" / "issues.json").read_text()))
        self.assertIn("backlog.csv", files)


if __name__ == "__main__":
    unittest.main()
