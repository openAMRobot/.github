#!/usr/bin/env python3
"""Collect the read-only inputs a mission needs into <workspace>/.harness-in/.

Runs before the agent, with the workflow's read-only token. Every input that
cannot be read is written as {"not_measured": "<reason>"} so the agent reports it
instead of guessing (fail closed, like the Watchdog).

  harness_inputs.py --mission NAME --target JSON --workspace DIR [--org ORG]
"""
import argparse
import datetime as dt
import hashlib
import io
import os
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_gh  # noqa: E402
import harness_lib as hl  # noqa: E402

AUDITS = {"dependencies", "contracts", "impact", "performance", "maintainability"}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # recorded, never hidden
        return {"not_measured": str(exc)[:300]}


def latest_artifact(gh, org, workflow, name, dest):
    runs = gh.paged(f"/repos/{org}/.github/actions/workflows/{workflow}/runs?status=success&per_page=1", limit=1)
    if not runs:
        raise RuntimeError(f"no successful run of {workflow}")
    artifacts = gh.paged(f"/repos/{org}/.github/actions/runs/{runs[0]['id']}/artifacts?per_page=50")
    match = [a for a in artifacts if a["name"] == name and not a.get("expired")]
    if not match:
        raise RuntimeError(f"artifact {name} not found on run {runs[0]['id']}")
    data = gh.download(match[0]["archive_download_url"])
    dest.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
    return {"run": runs[0]["html_url"], "files": sorted(p.name for p in dest.iterdir())}


def open_issues(gh, org, policy):
    out = []
    for repo in policy["repositories"]:
        for item in gh.paged(f"/repos/{org}/{repo}/issues?state=open&per_page=100"):
            if "pull_request" in item:
                continue
            out.append({"repository": repo, "number": item["number"], "title": item["title"],
                        "labels": sorted(l["name"] for l in item.get("labels", [])),
                        "assignees": [a["login"] for a in item.get("assignees", [])],
                        "created_at": item["created_at"], "updated_at": item["updated_at"],
                        "body": (item.get("body") or "")[:4000]})
    return out


def recent_runs(gh, org, days=7):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    runs = gh.paged(f"/repos/{org}/.github/actions/workflows/harness-run.yml/runs?created=>={since}&per_page=100", limit=300)
    return [{"id": r["id"], "event": r["event"], "conclusion": r.get("conclusion"), "created_at": r["created_at"],
             "url": r["html_url"], "title": r.get("display_title", "")} for r in runs]


def ai_prs(gh, org, days=7):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    items = gh.paged(f"/search/issues?q=org:{org}+is:pr+label:ai-generated+updated:>={since}&per_page=100", limit=200)
    return [{"url": i["html_url"], "title": i["title"], "state": i["state"],
             "labels": sorted(l["name"] for l in i.get("labels", [])), "closed_at": i.get("closed_at")}
            for i in items]


def clone_all(policy, org, root):
    repos = root / ".repos"
    repos.mkdir(exist_ok=True)
    lines = []
    for repo in policy["repositories"]:
        target = repos / repo
        if not target.exists():
            subprocess.run(["git", "clone", "--quiet", "--depth", "50", f"https://github.com/{org}/{repo}",
                            str(target)], check=False)
        if target.exists():
            sha = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True,
                                 text=True).stdout.strip()
            lines.append(f"{repo} {sha}")
        else:
            lines.append(f"{repo} NOT-CLONED")
    (repos / "SHAS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def snapshots(workspace, org, inp):
    """Copy the document snapshots named in baseline.yaml from the audits checkout in
    SNAPSHOT_DIR and check each sha256. Returns a status list; mismatches are recorded,
    not hidden."""
    baseline = hl.load_yaml(workspace / ".harness" / "harness" / "baseline.yaml")
    spec = baseline.get("snapshots") or {}
    files = spec.get("files") or []
    if not files:
        return [{"not_measured": "baseline.yaml lists no snapshots yet"}]
    # The register audit runs in the private audits repository, which checks out its
    # baseline branch to SNAPSHOT_DIR; no token is needed and nothing private leaves it.
    local = os.environ.get("SNAPSHOT_DIR", "")
    if not local:
        return [{"not_measured": "SNAPSHOT_DIR not set (the register audit runs in openAMRobot/audits)"}]
    out, sums = [], []
    for item in files:
        source = Path(local) / item["path"]
        try:
            if source.is_symlink() or not source.resolve().is_relative_to(Path(local).resolve()):
                raise ValueError("snapshot path leaves the snapshot checkout")
            data = source.read_bytes()
        except Exception as exc:
            out.append({"document": item.get("document"), "not_measured": str(exc)[:200]})
            continue
        digest = hashlib.sha256(data).hexdigest()
        target = inp / "snapshots" / Path(item["path"]).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        sums.append(f"{digest}  {target.name}")
        out.append({"document": item.get("document"), "file": target.name, "sha256": digest,
                    "matches_baseline": digest == item.get("sha256")})
    (inp / "snapshots" / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return out


def collect(mission, target, workspace, org, gh, policy):
    inp = workspace / ".harness-in"
    inp.mkdir(parents=True, exist_ok=True)
    write(inp / "target.json", target)
    harness = workspace / ".harness"
    if mission == "triage":
        write(inp / "daily-source.json", safe(latest_artifact, gh, org, "watchdog-daily.yml", "watchdog-daily", inp / "daily"))
        daily = inp / "daily" / "daily.json"
        if daily.exists():
            shutil.copy(daily, inp / "daily.json")
        else:
            write(inp / "daily.json", {"not_measured": "daily collector artifact unavailable"})
        write(inp / "scan-source.json", safe(latest_artifact, gh, org, "watchdog-org-scan.yml", "watchdog-org-scan", inp / "scan"))
        write(inp / "issues.json", safe(open_issues, gh, org, policy))
        write(inp / "runs.json", safe(recent_runs, gh, org))
        backlog = harness / "harness" / "backlog.csv"
        if backlog.exists():
            shutil.copy(backlog, inp / "backlog.csv")
        write(inp / "sim" / "README.json", {"not_measured": "no nightly simulation workflow publishes results yet"})
    elif mission == "register-audit":
        clone_all(policy, org, workspace)
        write(inp / "snapshots.json", snapshots(workspace, org, inp))
        write(inp / "audit-issues.json", safe(gh.paged, f"/search/issues?q=org:{org}+is:issue+is:open+label:audit-finding&per_page=100"))
    elif mission == "register-sync":
        number = target["issue"]
        write(inp / "issue.json", safe(gh.get, f"/repos/{org}/.github/issues/{number}"))
        write(inp / "issue-comments.json", safe(gh.paged, f"/repos/{org}/.github/issues/{number}/comments?per_page=100"))
        clone_all(policy, org, workspace)
    elif mission == "build":
        repo, number = target["repository"], target["issue"]
        write(inp / "issue.json", safe(gh.get, f"/repos/{org}/{repo}/issues/{number}"))
        write(inp / "issue-comments.json", safe(gh.paged, f"/repos/{org}/{repo}/issues/{number}/comments?per_page=100"))
    elif mission == "review":
        repo, number = target["repository"], target["pr"]
        write(inp / "pr.json", safe(gh.get, f"/repos/{org}/{repo}/pulls/{number}"))
        write(inp / "checks.json", safe(gh.get, f"/repos/{org}/{repo}/commits/{target['head']}/check-runs?per_page=100"))
        write(inp / "pr-comments.json", safe(gh.paged, f"/repos/{org}/{repo}/issues/{number}/comments?per_page=100"))
        write(inp / "pr-files.json", safe(gh.paged, f"/repos/{org}/{repo}/pulls/{number}/files?per_page=100"))
    elif mission in AUDITS or mission == "sim-analysis":
        if mission in AUDITS:
            clone_all(policy, org, workspace)
        write(inp / "previous" / "README.json", {"not_measured": "previous findings are read from the open audit-finding issues"})
        write(inp / "audit-issues.json", safe(gh.paged, f"/search/issues?q=org:{org}+is:issue+is:open+label:audit-finding&per_page=100"))
    elif mission == "retro":
        write(inp / "runs.json", safe(recent_runs, gh, org))
        write(inp / "ai-prs.json", safe(ai_prs, gh, org))
        write(inp / "harness-issues.json", safe(gh.paged, f"/search/issues?q=org:{org}+is:issue+label:harness+updated:>={(dt.date.today() - dt.timedelta(days=7)).isoformat()}&per_page=100"))
    return sorted(str(p.relative_to(inp)) for p in inp.rglob("*") if p.is_file())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mission", required=True)
    parser.add_argument("--target", default="{}")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--org", default="openAMRobot")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    policy = hl.load_policy(workspace / ".harness")
    files = collect(args.mission, json.loads(args.target or "{}"), workspace, args.org, harness_gh.GitHub(), policy)
    print(json.dumps({"mission": args.mission, "inputs": files}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
