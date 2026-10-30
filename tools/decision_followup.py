#!/usr/bin/env python3
"""Keep decisions.yaml and its consumers in step after merges (deterministic, no AI).

Two passes, each idempotent (hidden markers prevent duplicate comments and issues):

1. Merged PRs that declared "Change" in their Decisions impact section:
   - each linked change request gets the label register-update-needed and one
     comment naming the merged PR;
   - a PR that declared Change without a request gets a new request issue in
     openAMRobot/.github, labelled contract-change and needs-human:register.
2. Merged register PRs in openAMRobot/.github (decisions.yaml changed): the entries
   that changed are found by comparing the file before and after the merge; every
   enrolled repository is scanned with tools/check_decisions.py for those entries,
   and each repository with findings gets one consumer-update issue listing the
   lines. The issue is ai-ready (tier A when every file is tier A, else tier B)
   unless a line is in a tier C or D path, which makes it needs-human:safety.

  decision_followup.py [--days N] [--org ORG] [--workdir DIR] [--apply]
Without --apply it prints the plan and writes nothing.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_pr_evidence as cpe  # noqa: E402
import decision_impact as di  # noqa: E402
import harness_gh  # noqa: E402
import harness_lib as hl  # noqa: E402

MARK_PR = "<!-- decision-followup pr={key} -->"
MARK_CONSUMERS = "<!-- decision-consumers register-pr={number} repository={repository} -->"
MAX_LINES = 40


def merged_since(gh, org, repo, since):
    out = []
    for pr in gh.paged(f"/repos/{org}/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=100", limit=300):
        if pr.get("merged_at") and pr["merged_at"] >= since:
            out.append(pr)
    return out


def issue_number(ref, org):
    """'#12' or an issues URL -> (repository or None for the same one, number)."""
    if ref.startswith("#"):
        return None, int(ref[1:])
    parts = ref.split("/")
    if parts[-4].lower() != org.lower():
        raise ValueError(f"{ref} is outside {org}")
    return parts[-3], int(parts[-1])


def has_marker(gh, org, repo, number, marker):
    return any(marker in (c.get("body") or "") for c in gh.paged(f"/repos/{org}/{repo}/issues/{number}/comments?per_page=100"))


def open_issue_with_marker(gh, org, repo, marker):
    for issue in gh.paged(f"/repos/{org}/{repo}/issues?state=all&per_page=100", limit=500):
        if marker in (issue.get("body") or ""):
            return issue
    return None


def pass_changes(gh, org, policy, since, plan):
    for repo, cfg in policy["repositories"].items():
        if not cfg.get("review"):
            continue
        for pr in merged_since(gh, org, repo, since):
            try:
                handle_change(gh, org, repo, pr, plan)
            except Exception as exc:  # one bad PR (a mistyped issue number) never stops the rest
                plan.append(f"error on {repo}#{pr.get('number')}: {str(exc)[:200]}")


def handle_change(gh, org, repo, pr, plan):
    section = cpe.find(cpe.sections(pr.get("body") or ""), "Decisions impact")
    choice, ids, refs, _ = di.parse(section)
    if choice != "change":
        return
    key = f"{repo}#{pr['number']}"
    marker = MARK_PR.format(key=key)
    if refs:
        for ref in refs:
            target, number = issue_number(ref, org)
            target = target or repo
            if target not in ("", None) and not str(target).replace("-", "").replace(".", "").replace("_", "").isalnum():
                plan.append(f"skip reference {ref}: not a repository name")
                continue
            if has_marker(gh, org, target, number, marker):
                continue
            plan.append(f"label {target}#{number} register-update-needed; comment merged {key}")
            gh.post(f"/repos/{org}/{target}/issues/{number}/labels", {"labels": ["register-update-needed"]})
            gh.post(f"/repos/{org}/{target}/issues/{number}/comments", {"body": (
                f"{marker}\nMerged PR {pr['html_url']} depends on this register change "
                f"({', '.join(ids) or 'new entry'}). The register PR is drafted after the platform lead "
                "labels this request decision-approved.")})
    elif not open_issue_with_marker(gh, org, ".github", marker):
        plan.append(f"create change request in .github for {key}")
        gh.post(f"/repos/{org}/.github/issues", {
            "title": f"[CONTRACT] register change needed by {key}: {pr['title']}"[:250],
            "labels": ["contract-change", "needs-human:register", "needs-human", "register-update-needed"],
            "body": (f"{marker}\nMerged PR {pr['html_url']} declared a decision change "
                     f"({', '.join(ids) or 'entry not named'}) without a change request.\n\n"
                     "Platform lead: fill in the entry, the proposed value and the source document and item "
                     "(contract change request form fields), update the source document, then add the label "
                     "decision-approved. The harness drafts the register PR; you review and merge it.")})


def entries(text):
    data = yaml.safe_load(text) or {}
    return {d["id"]: json.dumps(d, sort_keys=True, default=str) for d in data.get("decisions", []) if isinstance(d, dict)}


def changed_ids(workdir, merge_sha):
    def show(rev):
        result = subprocess.run(["git", "-C", str(workdir), "show", f"{rev}:decisions.yaml"], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else ""
    before, after = entries(show(f"{merge_sha}^")), entries(show(merge_sha))
    return sorted(i for i in after if before.get(i) != after[i])


def scan_repo(harness_root, clone, repository):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        out = Path(handle.name)
    subprocess.run([sys.executable, str(harness_root / "tools" / "check_decisions.py"), "--decisions",
                    str(harness_root / "decisions.yaml"), "--root", str(clone), "--repository", repository,
                    "--json", str(out)], capture_output=True, text=True)
    try:
        return json.loads(out.read_text(encoding="utf-8")).get("findings", [])
    except (OSError, ValueError):
        return None


def consumer_issue(policy, repository, findings, ids, pr):
    lines = [f"- `{f['file']}:{f['line']}` {f['id']}: found `{str(f['found'])[:80]}`" for f in findings[:MAX_LINES]]
    if len(findings) > MAX_LINES:
        lines.append(f"- ... and {len(findings) - MAX_LINES} more")
    tiers = {hl.tier_of(f["file"], repository, policy) for f in findings}
    tier = hl.highest(list(tiers))
    labels = ["harness-followup", "register-update-needed"]
    if tier in ("C", "D"):
        labels += ["needs-human", "needs-human:safety"]
    else:
        labels += ["ai-ready", f"tier:{tier}"]
    body = "\n".join([
        MARK_CONSUMERS.format(number=pr["number"], repository=repository),
        f"The register change {pr['html_url']} changed {', '.join(ids)}. These lines in this repository still "
        "disagree with the register (tools/check_decisions.py on the default branch):", "", *lines, "",
        "Fix each line to the current register value, or label kept history with `decision-allow: <ID> <reason>`.",
        "Acceptance: check_decisions.py reports 0 contradictions for these entries in this repository.",
        "Tier C or D lines are changed by a person." if tier in ("C", "D") else
        "The harness may take this issue (ai-ready); the code owner adopts the draft PR."])
    return {"title": f"[register] update consumers of {', '.join(ids)[:120]}", "body": body, "labels": labels}


def pass_consumers(gh, org, policy, since, workdir, harness_root, plan):
    register_prs = [pr for pr in merged_since(gh, org, ".github", since)
                    if any(f["filename"] == "decisions.yaml" for f in gh.paged(f"/repos/{org}/.github/pulls/{pr['number']}/files?per_page=100"))]
    if not register_prs:
        return
    history = workdir / ".github-history"
    if not history.exists():
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", f"https://github.com/{org}/.github", str(history)], check=True)
    for pr in register_prs:
        ids = changed_ids(history, pr["merge_commit_sha"])
        if not ids:
            continue
        for repository in policy["repositories"]:
            clone = workdir / repository
            if not clone.exists():
                subprocess.run(["git", "clone", "--quiet", "--depth", "1", f"https://github.com/{org}/{repository}", str(clone)], check=False)
            findings = scan_repo(harness_root, clone, repository) if clone.exists() else None
            if findings is None:
                plan.append(f"{repository}: not measured (clone or scan failed)")
                continue
            hits = [f for f in findings if f["id"] in ids]
            marker = MARK_CONSUMERS.format(number=pr["number"], repository=repository)
            if not hits or open_issue_with_marker(gh, org, repository, marker):
                continue
            issue = consumer_issue(policy, repository, hits, ids, pr)
            plan.append(f"create consumer issue in {repository}: {len(hits)} line(s), labels {issue['labels']}")
            try:
                gh.post(f"/repos/{org}/{repository}/issues", issue)
            except Exception as exc:
                plan.append(f"error creating consumer issue in {repository}: {str(exc)[:200]}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--org", default="openAMRobot")
    parser.add_argument("--workdir", default=".followup")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    gh = harness_gh.GitHub(dry_run=not args.apply)
    policy = hl.load_policy(hl.ROOT)
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    plan = []
    pass_changes(gh, args.org, policy, since, plan)
    pass_consumers(gh, args.org, policy, since, workdir, hl.ROOT, plan)
    print("\n".join(plan) or "nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
