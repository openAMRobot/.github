#!/usr/bin/env python3
"""Plan and apply issue changes from an alignment-audit ISSUES.csv.

Opens one issue per Blocker or Major finding that has no issue yet, in the
repository named in file_to_change (or the fallback repository), assigned to
the owner role from maintainers.yaml by audit ID prefix. Closes open audit
issues whose finding is absent from the new CSV or has status resolved.

Issues in public repositories are public extracts: they carry the finding ID,
severity, area, the repository paths to change and the owner handle, never
the free-text columns, which can quote internal documents. The full text goes
only to the fallback (private) repository.
Exit status: 0 success, 2 usage error.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

LABEL = "audit-finding"
OPEN_SEVERITIES = {"Blocker", "Major"}
REPO = re.compile(r"\b(openamr(?:obot)?-[a-z0-9-]+|\.github)\b")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def title_for(row):
    return f"[audit] {row['id']}: {row.get('area', '').strip()}"[:120]


def finding_id(title):
    m = re.match(r"\[audit\] ([A-Z]+-\d+)", title or "")
    return m.group(1) if m else None


def target_repository(row, public_repos, fallback):
    for name in REPO.findall(row.get("file_to_change", "")):
        if name in public_repos:
            return name
    return fallback


def owner_handle(row, maintainers):
    role = maintainers.get("audit_prefixes", {}).get(row["id"].split("-")[0])
    handle = (maintainers.get("roles", {}).get(role) or {}).get("handle") if role else None
    return role or "unassigned", handle


def body_for(row, repository, fallback, maintainers, report):
    role, handle = owner_handle(row, maintainers)
    owner = f"@{handle} ({role})" if handle else f"{role}, no handle recorded"
    paths = sorted(set(re.findall(r"[\w./-]+\.(?:md|ya?ml|py|xml|xacro|urdf|launch\.py|json|html)",
                                  row.get("file_to_change", ""))))
    lines = [f"Audit finding **{row['id']}** ({row['severity']}), area: {row.get('area', '')}.", "",
             f"Owner: {owner}", f"Source: {report}", ""]
    if paths:
        lines += ["Files to change:"] + [f"- `{p}`" for p in paths] + [""]
    if repository == fallback:
        for key in ("value_a", "value_b", "decision_of_record", "fix"):
            if row.get(key):
                lines += [f"**{key}**: {row[key]}", ""]
    else:
        lines += ["Details are in the audit report named above. This issue is a public extract.", ""]
    lines.append("Opened by the weekly alignment audit. Close it with the fixing PR; the next audit verifies.")
    return "\n".join(lines)


def plan(new_rows, existing, maintainers, fallback, report):
    """Return (to_open, to_close). existing: list of {repository, number, title, state}."""
    public_repos = set(maintainers.get("repositories", {}))
    known = {}
    for issue in existing:
        fid = finding_id(issue.get("title"))
        if fid:
            known.setdefault(fid, []).append(issue)
    active = {r["id"]: r for r in new_rows if (r.get("status") or "open").lower() != "resolved"}
    to_open = []
    for fid, row in active.items():
        if row.get("severity") not in OPEN_SEVERITIES or fid in known:
            continue
        repository = target_repository(row, public_repos, fallback)
        to_open.append({"repository": repository, "title": title_for(row),
                        "body": body_for(row, repository, fallback, maintainers, report),
                        "labels": [LABEL, row["severity"].lower()]})
    to_close = [dict(issue, id=fid) for fid, issues in known.items() if fid not in active
                for issue in issues if issue.get("state") == "open"]
    return to_open, to_close


def api(method, url, token, data=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read() or b"null")


def fetch_existing(org, token, call=api):
    query = urllib.parse.quote(f"org:{org} label:{LABEL} is:issue")
    out, page = [], 1
    while True:
        data = call("GET", f"https://api.github.com/search/issues?q={query}&per_page=100&page={page}", token)
        for item in data.get("items", []):
            out.append({"repository": item["repository_url"].rsplit("/", 1)[-1], "number": item["number"],
                        "title": item["title"], "state": item["state"]})
        if len(data.get("items", [])) < 100:
            return out
        page += 1


def apply(org, to_open, to_close, token, sha, call=api):
    base = f"https://api.github.com/repos/{org}"
    for issue in to_open:
        call("POST", f"{base}/{issue['repository']}/issues", token,
             {"title": issue["title"], "body": issue["body"], "labels": issue["labels"]})
    for issue in to_close:
        url = f"{base}/{issue['repository']}/issues/{issue['number']}"
        call("POST", f"{url}/comments", token,
             {"body": f"Resolved according to the alignment audit at {sha}. Reopen if this is wrong."})
        call("PATCH", url, token, {"state": "closed", "state_reason": "completed"})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--issues", type=Path, required=True, help="new ISSUES.csv")
    p.add_argument("--maintainers", type=Path, required=True)
    p.add_argument("--fallback-repository", required=True, help="private repository for findings without a public target")
    p.add_argument("--report", required=True, help="report reference, e.g. folder@SHA")
    p.add_argument("--existing", type=Path, help="JSON list of existing audit issues (dry run input)")
    p.add_argument("--org", default="openAMRobot")
    p.add_argument("--apply", action="store_true", help="fetch existing issues, then create and close via the API")
    p.add_argument("--plan-output", type=Path)
    a = p.parse_args(argv)
    maintainers = yaml.safe_load(a.maintainers.read_text(encoding="utf-8"))
    rows = read_csv(a.issues)
    if not rows or "id" not in rows[0] or "severity" not in rows[0]:
        print("ISSUES.csv needs id and severity columns", file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN")
    if a.apply and not token:
        print("--apply needs GITHUB_TOKEN", file=sys.stderr)
        return 2
    existing = json.loads(a.existing.read_text(encoding="utf-8")) if a.existing else (
        fetch_existing(a.org, token) if a.apply else [])
    to_open, to_close = plan(rows, existing, maintainers, a.fallback_repository, a.report)
    for issue in to_open:
        print(f"OPEN  {issue['repository']}: {issue['title']}")
    for issue in to_close:
        print(f"CLOSE {issue['repository']}#{issue['number']}: {issue['id']}")
    print(f"plan: {len(to_open)} to open, {len(to_close)} to close")
    if a.plan_output:
        a.plan_output.write_text(json.dumps({"open": to_open, "close": to_close}, indent=2), encoding="utf-8")
    if a.apply:
        apply(a.org, to_open, to_close, token, a.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
