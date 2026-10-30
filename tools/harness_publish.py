#!/usr/bin/env python3
"""Publish a finished mission's outputs with the harness App token (deterministic).

The agent never writes to GitHub. This step reads the mission outputs from --out
(the .harness-out artifact) and does only what policy allows:
  build    guard PASS and status done: push branch ai/<issue>-<slug>, open a draft PR
           labelled ai-generated and tier:<X>; otherwise comment the reason on the
           issue and add needs-human:<status>. Always adds ai-attempt:<n>.
           Up to 3 follow-ups become issues labelled harness-followup.
  review   one comment per PR, updated in place, marked with head SHA and verdict.
  triage   allowed label changes, at most 5 new issues, the daily digest issue.
  audits   Blocker and Major findings become audit-finding issues (sync_audit_issues).
  retro    retro.patch limited to harness/skills and harness/missions becomes a
           draft PR in openAMRobot/.github labelled harness.
Without --apply it prints the plan and sends nothing.
"""
import argparse
import csv
import os
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_gh  # noqa: E402
import harness_lib as hl  # noqa: E402
import sync_audit_issues as sai  # noqa: E402

ESCALATIONS = {"stuck", "safety", "contract", "register", "decision", "hardware", "flaky", "security"}
# Each audit owns one ID range so its "no longer detected" notices never touch
# another audit's findings. IDs keep the PREFIX-NUMBER form sync_audit_issues tracks.
AUDITS = {"dependencies": ("CI", 1000), "contracts": ("SW", 1000), "impact": ("SW", 2000),
          "performance": ("SW", 3000), "maintainability": ("SW", 4000), "sim-analysis": ("SW", 5000),
          "register-audit": ("REG", 1000)}


def in_range(finding, mission):
    prefix, low = AUDITS[mission]
    match = re.fullmatch(r"([A-Z]+)-(\d+)", finding or "")
    return bool(match) and match.group(1) == prefix and low <= int(match.group(2)) < low + 1000
REVIEW_MARKER = "<!-- harness-review head={head} verdict={verdict} tier={tier} -->"
DIGEST_TITLE = "[harness] Daily digest"
FOOTER = ("\n\n---\nOpened by the openAMRobot harness ({mission} mission, [run]({run})). "
          "It stays a draft until the code owner writes adopt, adapt or reject (AGENTS.md \"Agents\").")


def coverage_line(policy):
    """Deterministic coverage statement for public output. Private repositories are never named."""
    excluded = [e["name"] for e in policy.get("excluded", [])]
    line = f"Coverage: {len(policy['repositories'])} repositories enrolled"
    if excluded:
        line += f"; {len(excluded)} excluded by owner decision (out of scope, not scanned): {', '.join(excluded)}"
    return line + "."


def clip(text, limit):
    text = str(text or "")
    return text if len(text) <= limit else text[:limit - 20] + "\n\n[cut by harness]"


def read(path, default=None):
    path = Path(path)
    if path.is_symlink() or not path.exists() or not path.is_file():
        return default
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else text


def read_json(path):
    """A mission output as a dict; anything else (missing, invalid, a list) is {}.
    Agent outputs are untrusted: they are validated field by field where used."""
    try:
        data = read(path, {})
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "change"


def allowed_labels(policy):
    names = set(policy["labels"]) | {"gate-a", "rc.1", "v2.0.0", "harness-followup"}
    names |= {f"priority:p{i}" for i in range(4)}
    return names - {"ai-generated", "hold", "no-ai"}


def as_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


class Publisher:
    def __init__(self, gh, org, out, target, run_url, policy, apply, guard=None, clone=None, bot=None, run_id=""):
        self.gh, self.org, self.out, self.target = gh, org, Path(out), target
        self.run_url, self.policy, self.apply = run_url, policy, apply
        # guard: the result computed by the publish job itself from the bundle, never the agent job's.
        self.guard_path = Path(guard) if guard else self.out / "guard.json"
        self.clone = Path(clone) if clone else None
        self.bot = bot if bot is not None else hl.bot_login()
        self.run_id = run_id or os.environ.get("GITHUB_RUN_ID", "")
        self.plan = []

    def act(self, what, fn=None, *args):
        self.plan.append(what)
        return fn(*args) if (fn and self.apply) else None

    def safely(self, fn, *args):
        """One failed item never stops the rest (the digest still gets written)."""
        try:
            return fn(*args)
        except Exception as exc:
            self.plan.append(f"error: {str(exc)[:200]}")
            return None

    def issue_labels(self, repo, number):
        issue = self.gh.get(f"/repos/{self.org}/{repo}/issues/{number}")
        return {l["name"] for l in issue.get("labels", [])}

    def add_labels(self, repo, number, labels):
        if labels:
            self.act(f"label {repo}#{number} +{sorted(labels)}", self.gh.post,
                     f"/repos/{self.org}/{repo}/issues/{number}/labels", {"labels": sorted(labels)})

    def remove_label(self, repo, number, label):
        self.act(f"label {repo}#{number} -{label}", self.gh.delete,
                 f"/repos/{self.org}/{repo}/issues/{number}/labels/{label}")

    def comment(self, repo, number, body):
        self.act(f"comment {repo}#{number}", self.gh.post,
                 f"/repos/{self.org}/{repo}/issues/{number}/comments", {"body": body})

    def create_issue(self, repo, title, body, labels):
        existing = self.gh.paged(f"/repos/{self.org}/{repo}/issues?state=open&per_page=100")
        if any(i["title"].strip().lower() == title.strip().lower() for i in existing):
            self.plan.append(f"skip duplicate issue {repo}: {title}")
            return
        self.act(f"create issue {repo}: {title}", self.gh.post, f"/repos/{self.org}/{repo}/issues",
                 {"title": title[:250], "body": body, "labels": sorted(labels)})

    # build ------------------------------------------------------------------
    def build(self, mission="build"):
        repo, number = self.target["repository"], self.target["issue"]
        result = read_json(self.out / "result.json")
        guard = read_json(self.guard_path)
        status = result.get("status") if result.get("status") in ESCALATIONS | {"done"} else "stuck"
        labels = self.issue_labels(repo, number)
        attempt = 1 + sum(1 for n in labels if n.startswith("ai-attempt:"))
        self.add_labels(repo, number, {f"ai-attempt:{attempt}"})
        run = f"[run]({self.run_url})"
        if status == "done" and guard.get("result") == "PASS":
            body_md = read(self.out / "pr.md", "") or ""
            lines = body_md.splitlines()
            title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else self.target.get("title", "harness change")
            body = clip("\n".join(lines[1:]).strip(), 60000)
            if not re.search(rf"\b(?:closes|fixes|resolves|refs)\s+#{number}\b", body, re.I):
                body += f"\n\nRefs #{number}"
            body += FOOTER.format(mission=mission, run=self.run_url)
            title = clip(title, 200)
            suffix = f"-{self.run_id}" if self.run_id else ""
            branch = f"{'register' if mission == 'register-sync' else 'ai'}/{number}-{slug(title)}{suffix}"
            self.act(f"push {repo} {branch}", self.push_bundle, repo, branch)
            pr = self.act(f"draft PR {repo}: {title}", self.gh.post, f"/repos/{self.org}/{repo}/pulls",
                          {"title": title, "head": branch, "base": self.default_branch(repo) if self.apply else "main",
                           "body": body, "draft": True})
            pr_number = (pr or {}).get("number", 0)
            pr_labels = {"ai-generated", f"tier:{guard.get('tier', 'B')}"}
            if mission == "register-sync":
                pr_labels |= {"register-change"}
                self.add_labels(repo, number, {"register-pr-open"})
            self.add_labels(repo, pr_number, pr_labels)
            self.comment(repo, number, f"Draft PR {(pr or {}).get('html_url', '(dry run)')} opened by the harness ({run}).")
        else:
            reason = "; ".join(guard.get("failures", [])) if guard.get("result") == "FAIL" else result.get("summary", "")
            handover = read(self.out / "needs-human.md", "") or ""
            self.comment(repo, number, f"Harness attempt {attempt} did not produce a change ({run}).\n\n"
                                       f"Status: {status}. {reason}\n\n{handover}".strip())
            if status in ESCALATIONS:
                self.add_labels(repo, number, {f"needs-human:{status}", "needs-human"})
                if "ai-ready" in labels:
                    self.remove_label(repo, number, "ai-ready")
            elif attempt >= self.policy["budgets"]["build"]["attempts_per_issue"]:
                self.add_labels(repo, number, {"needs-human:stuck", "needs-human"})
        followups = self.out / "followups.csv"
        if followups.exists():
            for row in list(csv.DictReader(followups.open(encoding="utf-8")))[:3]:
                if row.get("repository") in self.policy["repositories"] and row.get("title"):
                    self.create_issue(row["repository"], row["title"],
                                      f"{row.get('why', '')}\n\nEvidence: {row.get('evidence', '')}\n\n"
                                      f"Found by the harness while working on {repo}#{number} ({run}). "
                                      "Triage decides whether an agent or a person takes it.",
                                      {"harness-followup"})

    def default_branch(self, repo):
        return self.gh.get(f"/repos/{self.org}/{repo}")["default_branch"]

    def push_bundle(self, repo, branch):
        if self.clone:
            # The clone the publish job verified and guarded: push its candidate branch.
            url = f"https://x-access-token:{self.gh.token}@github.com/{self.org}/{repo}"
            subprocess.run(["git", "-C", str(self.clone), "push", "--quiet", url, f"candidate:refs/heads/{branch}"], check=True)
            return
        bundle = (self.out / "change.bundle").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            url = f"https://x-access-token:{self.gh.token}@github.com/{self.org}/{repo}"
            subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", url, tmp], check=True)
            subprocess.run(["git", "-C", tmp, "fetch", "--quiet", str(bundle), f"HEAD:refs/heads/{branch}"], check=True)
            subprocess.run(["git", "-C", tmp, "push", "--quiet", "origin", f"refs/heads/{branch}"], check=True)

    # review -----------------------------------------------------------------
    def review(self):
        repo, number, head = self.target["repository"], self.target["pr"], self.target["head"]
        verdict = read_json(self.out / "verdict.json")
        text = clip(read(self.out / "review.md", "") or "", 20000)
        value = verdict.get("verdict") if verdict.get("verdict") in {"pass", "concerns", "block"} else "concerns"
        tier = verdict.get("tier") if verdict.get("tier") in {"A", "B", "C", "D"} else "B"
        if verdict.get("safety_path"):
            value, tier = "block", hl.highest([tier, "C"])
        lines = [l for l in text.splitlines() if not l.startswith("<!-- harness-review")]
        body = (REVIEW_MARKER.format(head=head, verdict=value, tier=tier) + "\n" + "\n".join(lines).strip()
                + f"\n\n---\nHarness review of {head[:9]} ([run]({self.run_url})). It never approves or blocks merging; "
                  "the code owner decides.")
        comments = self.gh.paged(f"/repos/{self.org}/{repo}/issues/{number}/comments?per_page=100")
        mine = [c for c in comments if (c.get("body") or "").startswith("<!-- harness-review")
                and hl.is_harness_comment(c, self.bot)]
        if mine:
            self.act(f"update review comment {repo}#{number}", self.gh.patch,
                     f"/repos/{self.org}/{repo}/issues/comments/{mine[-1]['id']}", {"body": body})
        else:
            self.comment(repo, number, body)

    # triage -----------------------------------------------------------------
    def triage(self):
        data = read_json(self.out / "triage.json")
        if not isinstance(data.get("label", []), list) or not isinstance(data.get("create", []), list):
            data = {"digest": "triage.json was malformed; nothing applied (harness issue)."}
        allowed = allowed_labels(self.policy)
        removable = {"ai-ready"} | {f"priority:p{i}" for i in range(4)}
        for op in data.get("label", [])[:40]:
            if not isinstance(op, dict):
                continue
            repo, number = op.get("repository"), as_int(op.get("issue"))
            if repo not in self.policy["repositories"] or not number:
                self.plan.append(f"skip label operation {str(op)[:80]}: unknown repository or issue")
                continue
            self.safely(self.add_labels, repo, number, {x for x in op.get("add", []) if isinstance(x, str)} & allowed)
            for name in {x for x in op.get("remove", []) if isinstance(x, str)} & removable:
                self.safely(self.remove_label, repo, number, name)
        for new in data.get("create", [])[:5]:
            if not isinstance(new, dict) or new.get("repository") not in self.policy["repositories"] \
                    or not str(new.get("title") or "").strip():
                self.plan.append("skip issue creation: unknown repository or empty title")
                continue
            self.safely(self.create_issue, new["repository"], clip(new.get("title"), 200),
                        clip(new.get("body", ""), 8000) + f"\n\nOpened by harness triage ([run]({self.run_url})).",
                        {x for x in new.get("labels", []) if isinstance(x, str)} & allowed)
        digest = clip((data.get("digest") or "No digest produced.").strip(), 8000)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        body = f"{digest}\n\n{coverage_line(self.policy)}\n\n---\nUpdated {stamp} by harness triage ([run]({self.run_url})). Edited in place every weekday."
        existing = [i for i in self.gh.paged(f"/repos/{self.org}/.github/issues?state=open&labels=harness&per_page=100")
                    if i["title"] == DIGEST_TITLE]
        if existing:
            self.act("update digest issue", self.gh.patch, f"/repos/{self.org}/.github/issues/{existing[0]['number']}",
                     {"body": body})
        else:
            self.act("create digest issue", self.gh.post, f"/repos/{self.org}/.github/issues",
                     {"title": DIGEST_TITLE, "body": body, "labels": ["harness"]})

    # audits -----------------------------------------------------------------
    def audit(self, mission):
        path = self.out / "findings.csv"
        if not path.exists():
            self.plan.append("no findings.csv")
            return
        rows = [r for r in sai.read_csv(path) if in_range(r.get("id"), mission)]
        maintainers = hl.load_yaml(hl.ROOT / "maintainers.yaml")
        query = f"/search/issues?q=org:{self.org}+label:{sai.LABEL}+is:issue&per_page=100"
        existing = [{"repository": i["repository_url"].rsplit("/", 1)[-1], "number": i["number"],
                     "title": i["title"], "state": i["state"]} for i in self.gh.paged(query)]
        existing = [e for e in existing if in_range(sai.finding_id(e["title"]), mission)]
        to_open, to_notify = sai.plan(rows, existing, maintainers, "audits", f"harness {mission} {self.run_url}")
        for issue in to_open:
            self.act(f"create {issue['repository']}: {issue['title']}", self.gh.post,
                     f"/repos/{self.org}/{issue['repository']}/issues",
                     {"title": issue["title"], "body": issue["body"], "labels": issue["labels"]})
        for issue in to_notify:
            self.comment(issue["repository"], issue["number"],
                         f"{sai.NOT_DETECTED}\nNo longer detected by the harness {mission} audit ({self.run_url}). "
                         "The owner closes this issue after checking the fix; the harness does not close it.")

    # retro ------------------------------------------------------------------
    def retro(self):
        patch = self.out / "retro.patch"
        if not patch.exists() or not patch.read_text(encoding="utf-8").strip():
            self.plan.append("no retro.patch")
            return
        files = re.findall(r"^\+\+\+ b/(\S+)", patch.read_text(encoding="utf-8"), re.M)
        bad = [f for f in files if not f.startswith(("harness/skills/", "harness/missions/"))]
        if bad or not files:
            self.plan.append(f"retro.patch rejected: touches {bad or 'nothing'}")
            return
        branch = f"harness/retro-{dt.date.today().isoformat()}-{self.run_id or 'manual'}"
        self.act(f"push .github {branch}", self.push_patch, patch, branch)
        body = (read(self.out / "retro.md", "") or "").strip() + FOOTER.format(mission="retro", run=self.run_url)
        pr = self.act("draft PR .github: retro", self.gh.post, f"/repos/{self.org}/.github/pulls",
                      {"title": f"harness: weekly retro {dt.date.today().isoformat()}", "head": branch, "base": "main",
                       "body": body, "draft": True})
        self.add_labels(".github", (pr or {}).get("number", 0), {"harness", "ai-generated", "tier:B"})

    def push_patch(self, patch, branch):
        with tempfile.TemporaryDirectory() as tmp:
            url = f"https://x-access-token:{self.gh.token}@github.com/{self.org}/.github"
            subprocess.run(["git", "clone", "--quiet", "--depth", "1", url, tmp], check=True)
            subprocess.run(["git", "-C", tmp, "switch", "-c", branch], check=True)
            subprocess.run(["git", "-C", tmp, "apply", "--index", str(patch.resolve())], check=True)
            # The +++ lines are not enough: deletions and renames carry other headers.
            staged = subprocess.run(["git", "-C", tmp, "diff", "--cached", "--name-only", "--no-renames"],
                                    check=True, capture_output=True, text=True).stdout.split()
            outside = [f for f in staged if not f.startswith(("harness/skills/", "harness/missions/"))]
            if outside or not staged:
                raise RuntimeError(f"retro.patch touches paths outside harness/skills and harness/missions: {outside}")
            subprocess.run(["git", "-C", tmp, "-c", "user.name=openamrobot-harness[bot]", "-c",
                            "user.email=openamrobot-harness[bot]@users.noreply.github.com", "commit", "-q", "-s",
                            "-m", "harness: weekly retro proposals"], check=True)
            subprocess.run(["git", "-C", tmp, "push", "--quiet", "origin", branch], check=True)

    def run(self, mission):
        if mission in ("build", "register-sync"):
            self.build(mission)
        elif mission == "review":
            self.review()
        elif mission == "triage":
            self.triage()
        elif mission in AUDITS:
            self.audit(mission)
        elif mission == "retro":
            self.retro()
        else:
            raise SystemExit(f"unknown mission {mission}")
        return self.plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mission", required=True)
    parser.add_argument("--target", default="{}")
    parser.add_argument("--out", required=True)
    parser.add_argument("--org", default="openAMRobot")
    parser.add_argument("--run-url", default="")
    parser.add_argument("--guard", help="guard.json computed by the publish job (build and register-sync)")
    parser.add_argument("--clone", help="the verified clone whose candidate branch is pushed")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    gh = harness_gh.GitHub(dry_run=not args.apply)
    publisher = Publisher(gh, args.org, args.out, json.loads(args.target or "{}"), args.run_url,
                          hl.load_policy(hl.ROOT), args.apply, guard=args.guard, clone=args.clone)
    for line in publisher.run(args.mission):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
