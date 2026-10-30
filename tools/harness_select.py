#!/usr/bin/env python3
"""Pick the next unit of work for the build mission, or say why there is none.

Deterministic: the agent never chooses its own task. Reads harness/policy.yaml,
harness/baseline.yaml, decisions.yaml and the open issues and PRs of every
repository with build: true. Prints one JSON object:
  {"run": true, "repository", "issue", "title", "tier", "ros", "drift"}
or {"run": false, "reason": "..."}.

  harness_select.py [--issues FILE --pulls FILE] [--enabled true] [--stage N]
With --issues/--pulls (JSON lists, as returned by the REST API with an extra
"repository" field) it makes no network call; otherwise it reads the API with
GITHUB_TOKEN.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as hl  # noqa: E402

PRIORITY = re.compile(r"^priority:p([0-3])$")
GATE_RANK = {"gate-a": 0, "rc.1": 1, "v2.0.0": 2}


def labels(item):
    return {(l["name"] if isinstance(l, dict) else l) for l in item.get("labels", [])}


def register_drift(root):
    baseline = hl.load_yaml(root / "harness" / "baseline.yaml")
    decisions = hl.load_yaml(root / "decisions.yaml")
    in_force = (decisions.get("in_force") or {}).get("source", "")
    return (in_force != baseline.get("p03")), in_force, baseline.get("p03"), decisions


def decision_ids(decisions):
    return {e["id"] for e in decisions.get("entries", decisions.get("decisions", [])) if isinstance(e, dict) and "id" in e}


def linked_issue(pr):
    m = re.search(r"\b(?:closes|fixes|resolves|refs)\s+#(\d+)", pr.get("body") or "", re.I)
    return int(m.group(1)) if m else None


def select(policy, root, issues, pulls, enabled, stage):
    if not enabled:
        return {"run": False, "reason": "HARNESS_ENABLED is not true"}
    if stage < 2:
        return {"run": False, "reason": f"HARNESS_STAGE is {stage}; build runs from stage 2"}
    budget = policy["budgets"]["build"]
    drift, in_force, p03, decisions = register_drift(root)
    ids = decision_ids(decisions) if drift else set()
    repos = {name: cfg for name, cfg in policy["repositories"].items() if cfg.get("build")}
    if not repos:
        return {"run": False, "reason": "no repository has build: true"}

    open_ai = [p for p in pulls if "ai-generated" in labels(p) and p.get("state", "open") == "open"]
    if len(open_ai) >= budget["open_ai_prs_organization"]:
        return {"run": False, "reason": f"{len(open_ai)} open ai-generated PRs, organization limit reached"}
    per_repo = {}
    for p in open_ai:
        per_repo[p["repository"]] = per_repo.get(p["repository"], 0) + 1
    taken = {(p["repository"], linked_issue(p)) for p in open_ai}
    for p in pulls:  # a branch named for the issue is taken even if the body lost its link
        m = re.match(r"^(?:ai|register)/(\d+)-", ((p.get("head") or {}).get("ref") or ""))
        if m and p.get("state", "open") == "open":
            taken.add((p["repository"], int(m.group(1))))

    candidates, skipped = [], []
    for issue in issues:
        repo, names = issue["repository"], labels(issue)
        if repo not in repos or "pull_request" in issue or issue.get("state", "open") != "open":
            continue
        if "ai-ready" not in names:
            continue
        why = None
        if names & {"no-ai", "hold"} or any(n.startswith("needs-human") for n in names):
            why = "paused or waiting for a person"
        elif "tier:C" in names:
            why = "tier C: a person writes it"
        elif per_repo.get(repo, 0) >= budget["open_ai_prs_per_repository"]:
            why = "repository has its limit of open ai-generated PRs"
        elif (repo, issue["number"]) in taken:
            why = "an open ai-generated PR already covers it"
        elif sum(1 for n in names if n.startswith("ai-attempt:")) >= budget["attempts_per_issue"]:
            why = "attempt limit reached"
        elif drift and ids & set(re.findall(r"\b[A-Z][A-Z0-9]{2,}(?:-[A-Z0-9]+)*\b", (issue.get("title") or "") + " " + (issue.get("body") or ""))):
            why = f"names a register entry while the register ({in_force}) trails the baseline ({p03})"
        if why:
            skipped.append({"repository": repo, "issue": issue["number"], "reason": why})
            continue
        prio = min([int(PRIORITY.match(n).group(1)) for n in names if PRIORITY.match(n)] or [3])
        gate = min([GATE_RANK[n] for n in names if n in GATE_RANK] or [9])
        tier = "A" if "tier:A" in names else "B"
        candidates.append(((gate, prio, per_repo.get(repo, 0), issue.get("created_at", "")), issue, tier))

    if not candidates:
        return {"run": False, "reason": "no eligible ai-ready issue", "skipped": skipped, "drift": drift}
    candidates.sort(key=lambda c: c[0])
    _, issue, tier = candidates[0]
    cfg = repos[issue["repository"]]
    return {"run": True, "repository": issue["repository"], "issue": issue["number"],
            "title": issue.get("title", ""), "tier": tier, "ros": cfg.get("ros", ""), "drift": drift, "skipped": skipped}


def approved_by(events, label, handle):
    """True when the most recent `labeled` event for label was made by handle."""
    added = [e for e in events if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == label]
    return bool(added) and bool(handle) and (added[-1].get("actor") or {}).get("login", "").lower() == handle.lower()


def select_register_sync(policy, root, issues, events_for, enabled, stage):
    """Pick the oldest change request in .github that the platform lead labelled
    decision-approved and that has no register PR yet. events_for(number) returns
    the issue's events (REST /issues/{n}/events)."""
    if not enabled:
        return {"run": False, "reason": "HARNESS_ENABLED is not true"}
    if stage < 2:
        return {"run": False, "reason": f"HARNESS_STAGE is {stage}; register-sync runs from stage 2"}
    maintainers = hl.load_yaml(root / "maintainers.yaml")
    lead = ((maintainers.get("roles") or {}).get("platform-lead") or {}).get("handle", "")
    skipped = []
    for issue in sorted(issues, key=lambda i: i.get("created_at", "")):
        names = labels(issue)
        if issue.get("repository") != ".github" or "decision-approved" not in names or "pull_request" in issue:
            continue
        if names & {"register-pr-open", "no-ai", "hold"}:
            continue
        if not approved_by(events_for(issue["number"]), "decision-approved", lead):
            skipped.append({"issue": issue["number"], "reason": f"decision-approved was not added by the platform lead (@{lead})"})
            continue
        return {"run": True, "repository": ".github", "issue": issue["number"], "title": issue.get("title", ""),
                "tier": "B", "ros": "", "mission": "register-sync", "skipped": skipped}
    return {"run": False, "reason": "no approved change request waiting", "skipped": skipped}


def fetch(url, token):
    items = []
    while url:
        request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                       "Authorization": f"Bearer {token}",
                                                       "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(request, timeout=30) as response:
            items += json.load(response)
            links = response.headers.get("Link", "")
        m = re.search(r'<([^>]+)>;\s*rel="next"', links)
        url = m.group(1) if m else None
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(hl.ROOT))
    parser.add_argument("--issues")
    parser.add_argument("--pulls")
    parser.add_argument("--enabled", default=os.environ.get("HARNESS_ENABLED", ""))
    parser.add_argument("--stage", type=int, default=int(os.environ.get("HARNESS_STAGE") or 0))
    parser.add_argument("--org", default="openAMRobot")
    parser.add_argument("--mission", default="build", choices=["build", "register-sync"])
    args = parser.parse_args(argv)
    root = Path(args.root)
    policy = hl.load_policy(root)
    if args.mission == "register-sync":
        token = os.environ.get("GITHUB_TOKEN", "")
        base = f"https://api.github.com/repos/{args.org}/.github"
        if args.issues:
            issues = json.loads(Path(args.issues).read_text(encoding="utf-8"))
            events_for = lambda n: []  # noqa: E731
        else:
            issues = [dict(i, repository=".github") for i in
                      fetch(f"{base}/issues?state=open&labels=decision-approved&per_page=100", token)]
            events_for = lambda n: fetch(f"{base}/issues/{n}/events?per_page=100", token)  # noqa: E731
        result = select_register_sync(policy, root, issues, events_for, args.enabled == "true", args.stage)
        print(json.dumps(result, indent=2))
        return 0
    if args.issues:
        issues = json.loads(Path(args.issues).read_text(encoding="utf-8"))
        pulls = json.loads(Path(args.pulls).read_text(encoding="utf-8")) if args.pulls else []
    else:
        token = os.environ["GITHUB_TOKEN"]
        issues, pulls = [], []
        for repo, cfg in policy["repositories"].items():
            if not cfg.get("build"):
                continue
            base = f"https://api.github.com/repos/{args.org}/{repo}"
            for item in fetch(f"{base}/issues?state=open&labels=ai-ready&per_page=100", token):
                item["repository"] = repo
                issues.append(item)
            for item in fetch(f"{base}/pulls?state=open&per_page=100", token):
                item["repository"] = repo
                pulls.append(item)
    result = select(policy, root, issues, pulls, args.enabled == "true", args.stage)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
