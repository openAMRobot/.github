#!/usr/bin/env python3
"""Stage 4: decide which tier A harness PRs may be merged automatically.

A PR qualifies only when ALL hold:
  - labels ai-generated and tier:A, and none of hold, no-ai, needs-human*;
  - its repository has build: true in harness/policy.yaml and is not a tier C repository;
  - every changed file is tier A by harness_lib.tier_of (re-checked here, not trusted from the label);
  - a harness review comment exists for the current head SHA with verdict=pass tier=A;
  - every required check (policy merge_gate.required_checks, per repository or default) ran on the
    head SHA and concluded success; other check runs may be success, neutral or skipped; every
    commit status on the head SHA is success and none is pending;
  - the veto window (24 hours) has passed since GitHub first saw the current head: measured from the
    creation time of the harness review comment for that head SHA, a GitHub-set timestamp written after
    every push, never from the commit's own committer date, which the author controls;
    and the PR has no review requesting changes.
It prints the decisions; with --apply it marks the PR ready and squash-merges it
with the harness App. Anything that fails a condition stays for a person.
"""
import argparse
import datetime as dt
import os
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_gh  # noqa: E402
import harness_lib as hl  # noqa: E402

VETO_HOURS = 24
PASS = re.compile(r"^<!-- harness-review head=(?P<head>[0-9a-f]{40}) verdict=(?P<verdict>\w+) tier=(?P<tier>[A-D]) -->")
OK_CONCLUSIONS = {"success", "neutral", "skipped"}


def parse_time(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def required_checks(policy, repository):
    """Names of the check runs that must execute and succeed before an automatic merge."""
    gate = policy.get("merge_gate", {})
    per_repo = gate.get("required_checks", {})
    return list(per_repo.get(repository, per_repo.get("default", [])))


def decide(pr, files, comments, checks, reviews, head_commit_time, repository, policy, now, bot=None,
           statuses=None):
    bot = bot if bot is not None else hl.bot_login()
    labels = {l["name"] for l in pr.get("labels", [])}
    reasons = []
    if not {"ai-generated", "tier:A"} <= labels:
        reasons.append("not an ai-generated tier A PR")
    if labels & {"hold", "no-ai"} or any(n.startswith("needs-human") for n in labels):
        reasons.append("held or waiting for a person")
    cfg = policy["repositories"].get(repository, {})
    if not cfg.get("build") or repository in policy["tiers"]["C"].get("repositories", []):
        reasons.append("repository not enrolled for build")
    bad = [f["filename"] for f in files if hl.tier_of(f["filename"], repository, policy) != "A"]
    if bad or not files:
        reasons.append(f"files above tier A: {bad[:5]}" if bad else "no files")
    head = pr["head"]["sha"]
    passes = [(m, c) for m, c in ((PASS.match(c.get("body") or ""), c) for c in comments
                                  if hl.is_harness_comment(c, bot)) if m]
    head_passes = [c for m, c in passes if m["head"] == head and m["verdict"] == "pass" and m["tier"] == "A"]
    if not head_passes:
        reasons.append("no passing tier A harness review for the head SHA")
    runs = checks.get("check_runs", [])
    required = required_checks(policy, repository)
    if not required:
        reasons.append("no required verification checks configured for this repository")
    for name in required:
        # A reusable workflow reports "<caller job> / <job>"; both spellings count.
        named = [r for r in runs if r.get("name") == name or str(r.get("name", "")).endswith(" / " + name)]
        if not any(r.get("status") == "completed" and r.get("conclusion") == "success" for r in named):
            reasons.append(f"required check {name} did not run and succeed on the head SHA")
    if any(r.get("status") != "completed" or r.get("conclusion") not in OK_CONCLUSIONS for r in runs):
        reasons.append("a check is pending or not green")
    if statuses is None:
        reasons.append("commit statuses were not read")
    else:
        # The combined state reads "pending" when no status exists at all, so judge each status.
        if any(s.get("state") != "success" for s in statuses.get("statuses", [])):
            reasons.append("a commit status is pending or not green")
    if any(r.get("state") == "CHANGES_REQUESTED" for r in reviews):
        reasons.append("a reviewer requested changes")
    # The veto clock starts when GitHub first recorded the current head: the earliest harness review
    # comment for this head SHA (GitHub sets created_at; a new push gets a new comment). The commit's
    # committer date is only a lower bound, since an author can backdate it.
    seen = [parse_time(c["created_at"]) for c in head_passes if c.get("created_at")]
    if not seen:
        reasons.append("veto window: no GitHub timestamp for the current head")
    else:
        start = max([min(seen), head_commit_time] if head_commit_time else [min(seen)])
        if now - start < dt.timedelta(hours=VETO_HOURS):
            reasons.append(f"veto window: current head seen less than {VETO_HOURS} h ago")
    return reasons


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--org", default="openAMRobot")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--enabled", default="")
    parser.add_argument("--stage", type=int, default=0)
    args = parser.parse_args(argv)
    if args.enabled != "true" or args.stage < 4:
        print("merge gate off: needs HARNESS_ENABLED=true and HARNESS_STAGE=4")
        return 0
    policy = hl.load_policy(hl.ROOT)
    gh = harness_gh.GitHub(dry_run=not args.apply)
    now = dt.datetime.now(dt.timezone.utc)
    for repository, cfg in policy["repositories"].items():
        if not cfg.get("build"):
            continue
        base = f"/repos/{args.org}/{repository}"
        for pr in gh.paged(f"{base}/pulls?state=open&per_page=100"):
            if "ai-generated" not in {l["name"] for l in pr.get("labels", [])}:
                continue
            number, head = pr["number"], pr["head"]["sha"]
            commit = gh.get(f"{base}/commits/{head}")
            reasons = decide(pr, gh.paged(f"{base}/pulls/{number}/files?per_page=100"),
                             gh.paged(f"{base}/issues/{number}/comments?per_page=100"),
                             gh.get(f"{base}/commits/{head}/check-runs?per_page=100"),
                             gh.paged(f"{base}/pulls/{number}/reviews?per_page=100"),
                             parse_time(commit["commit"]["committer"]["date"]), repository, policy, now,
                             statuses=gh.get(f"{base}/commits/{head}/status"))
            print(json.dumps({"repository": repository, "pr": number, "merge": not reasons, "reasons": reasons}))
            if reasons or not args.apply:
                continue
            if pr.get("draft"):
                gh.post("/graphql", {"query": "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id}){clientMutationId}}",
                                     "variables": {"id": pr["node_id"]}})
            gh.request("PUT", f"{base}/pulls/{number}/merge", {"merge_method": "squash", "sha": head})
    return 0


if __name__ == "__main__":
    sys.exit(main())
