#!/usr/bin/env python3
"""Plan and apply issue updates from an alignment-audit ISSUES.csv.

Opens one issue per Blocker or Major finding that has no issue yet, in the
repository named in file_to_change (or the fallback repository), assigned to
the owner role from maintainers.yaml by audit ID prefix. It never closes an
issue: when an open audit issue's finding is absent from the new CSV or has
status resolved, it comments "no longer detected" once and leaves closure to
the issue's owner, because one run not reporting a finding is not proof that
it is fixed.

Issues in public repositories are public extracts: they carry the finding ID,
severity, area, the repository paths to change and the owner handle, never
the free-text columns, which can quote internal documents. The full text goes
only to the fallback (private) repository.
Exit status: 0 success, 2 usage error.
"""
import argparse
from datetime import date
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
NOT_DETECTED = "<!-- audit-no-longer-detected -->"
OPEN_SEVERITIES = {"Blocker", "Major"}
REPO = re.compile(r"\b(openamr(?:obot)?-[a-z0-9-]+|\.github)\b")



def review_warnings(path, today=None):
    """Return warnings for decision entries whose review window has passed."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    today = today or date.today()
    warnings = []
    for entry in data.get("decisions") or []:
        value = entry.get("review_by") if isinstance(entry, dict) else None
        if isinstance(value, date):
            review_by = value
        else:
            try:
                review_by = date.fromisoformat(str(value))
            except (TypeError, ValueError):
                continue
        if review_by < today:
            warnings.append(f"{entry.get('id', '<unknown>')} review_by {review_by.isoformat()} is past due")
    return warnings

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
    """Return (to_open, to_notify). existing: list of {repository, number, title, state}."""
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
    to_notify = [dict(issue, id=fid) for fid, issues in known.items() if fid not in active
                 for issue in issues if issue.get("state") == "open"]
    return to_open, to_notify


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


def apply(org, to_open, to_notify, token, report, call=api):
    """Create issues; comment once on issues no longer detected. Never closes."""
    base = f"https://api.github.com/repos/{org}"
    for issue in to_open:
        call("POST", f"{base}/{issue['repository']}/issues", token,
             {"title": issue["title"], "body": issue["body"], "labels": issue["labels"]})
    for issue in to_notify:
        url = f"{base}/{issue['repository']}/issues/{issue['number']}/comments"
        comments = call("GET", f"{url}?per_page=100", token) or []
        if any(NOT_DETECTED in (c.get("body") or "") for c in comments):
            continue
        call("POST", url, token, {"body": (
            f"{NOT_DETECTED}\nNo longer detected by the alignment audit {report}. "
            "The owner closes this issue after checking the fix; the audit does not close it.")})


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
    p.add_argument("--decisions", type=Path, help="decision register; past review_by dates are warnings")
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
    warnings = review_warnings(a.decisions) if a.decisions else []
    for warning in warnings:
        print(f"WARNING decision-review {warning}")
    to_open, to_notify = plan(rows, existing, maintainers, a.fallback_repository, a.report)
    for issue in to_open:
        print(f"OPEN    {issue['repository']}: {issue['title']}")
    for issue in to_notify:
        print(f"COMMENT {issue['repository']}#{issue['number']}: {issue['id']} no longer detected (not closed)")
    print(f"plan: {len(to_open)} to open, {len(to_notify)} to comment 'no longer detected', 0 closed")
    if a.plan_output:
        a.plan_output.write_text(json.dumps({"open": to_open, "no_longer_detected": to_notify, "decision_review_warnings": warnings}, indent=2),
                                 encoding="utf-8")
    if a.apply:
        apply(a.org, to_open, to_notify, token, a.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
