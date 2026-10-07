#!/usr/bin/env python3
"""Synchronise deterministic Watchdog findings into one GitHub control surface.

The organization scan is read-only against product repositories. This tool writes only to
the harness repository: it creates or updates deduplicated issues, assigns the platform lead
when possible, and keeps a small dashboard issue. It never edits decisions.yaml, pushes a
branch, opens a pull request, or closes a human-owned issue.

The register remains human-approved. A decision-review issue tells the platform lead when an
entry is due; the owner then updates the source document first and uses a normal reviewed PR
to update decisions.yaml and affected repositories.
"""
import argparse
from collections import OrderedDict
from datetime import date
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml


DASHBOARD_MARKER = "<!-- watchdog:dashboard -->"
NO_LONGER_MARKER = "<!-- watchdog:no-longer-detected -->"
OBSERVATION_PREFIX = "<!-- watchdog:observation:"
OBSERVATION_SUFFIX = " -->"
MARKER_RE = re.compile(r"<!-- watchdog:(finding|review|blocked):([^ ]+) -->")
OBSERVATION_RE = re.compile(r"<!-- watchdog:observation:([0-9a-f]+) -->")
FINDING_SEVERITY = {
    "decisions": "major",
    "public-extract": "blocker",
    "shared-rules": "major",
    "workflow-policy": "major",
}
LABEL_METADATA = {
    "watchdog-finding": ("1f6feb", "A deterministic Watchdog finding"),
    "watchdog-review": ("8250df", "A decision-register review reminder"),
    "watchdog-report": ("5319e7", "The organization Watchdog dashboard"),
    "decision-review": ("fbca04", "A human review of one decisions.yaml entry"),
    "blocker": ("b60205", "Blocks a complete or safe result"),
    "major": ("d93f0b", "Requires owner action"),
    "review": ("fbca04", "Requires human review"),
}
OWNER_BY_CHECK = {
    "public-extract": "docs-owner",
    "shared-rules": "software-lead",
    "workflow-policy": "ci-owner",
}
REDACT_URL = re.compile(r"https?://[^\s`|]+", re.IGNORECASE)
REDACT_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
REDACT_SECRET = re.compile(r"\b(?:ghp_|github_pat_|sk-ant-|AKIA)[A-Za-z0-9_./+-]{8,}\b")


def digest(*parts):
    """Return a short, stable identifier for one logical finding."""
    raw = "\0".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def marker(kind, key):
    return f"<!-- watchdog:{kind}:{key} -->"


def observation(value):
    return f"{OBSERVATION_PREFIX}{digest(json.dumps(value, sort_keys=True, default=str))}{OBSERVATION_SUFFIX}"


def scrub(value, limit=240):
    """Make untrusted repository text safe for a public issue."""
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = REDACT_SECRET.sub("[redacted credential]", text)
    text = REDACT_URL.sub("[redacted URL]", text)
    text = REDACT_EMAIL.sub("[redacted email]", text)
    text = text.replace("|", "/").replace("`", "'").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def load_reports(directory):
    reports = []
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("repository") and "results" in data:
            reports.append(data)
    return reports


def load_blocked(path):
    if not path or not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def owner_for(check, group, decisions, maintainers):
    role = OWNER_BY_CHECK.get(check)
    if check == "decisions":
        entry = decisions.get(group, {})
        role = entry.get("owner") or "platform-lead"
    roles = maintainers.get("roles", {})
    handle = (roles.get(role) or {}).get("handle")
    return role, handle


def grouped_items(reports, decisions, maintainers):
    """Convert raw reports to one stable issue candidate per logical group."""
    active = OrderedDict()
    for report in reports:
        repo = report.get("repository", "unknown")
        for check, items in (report.get("results") or {}).items():
            if not items:
                continue
            groups = OrderedDict()
            for item in items:
                groups.setdefault(item.get("group", "unknown"), []).append(item)
            for group, findings in groups.items():
                key = digest("finding", repo, check, group)
                role, handle = owner_for(check, group, decisions, maintainers)
                active[marker("finding", key)] = {
                    "kind": "finding",
                    "key": key,
                    "marker": marker("finding", key),
                    "fingerprint": key,
                    "repository": repo,
                    "commit": report.get("commit", "unknown"),
                    "check": check,
                    "group": group,
                    "severity": FINDING_SEVERITY.get(check, "major"),
                    "owner_role": role,
                    "owner_handle": handle,
                    "findings": findings,
                }
    return list(active.values())


def review_items(reports, decisions, maintainers):
    """Return one review issue per due register entry, without duplicate reports."""
    due = OrderedDict()
    for report in reports:
        for warning in report.get("freshness") or []:
            decision_id = str(warning).split(" review_by", 1)[0]
            if decision_id in due:
                continue
            entry = decisions.get(decision_id, {})
            role = entry.get("owner") or "platform-lead"
            handle = (maintainers.get("roles", {}).get(role) or {}).get("handle")
            key = digest("review", decision_id)
            due[marker("review", key)] = {
                "kind": "review",
                "key": key,
                "marker": marker("review", key),
                "fingerprint": key,
                "decision_id": decision_id,
                "warning": warning,
                "owner_role": role,
                "owner_handle": handle,
                "severity": "review",
            }
    return list(due.values())


def blocked_items(blocked, maintainers):
    out = []
    for item in blocked:
        repo = item.get("repository", "unknown")
        key = digest("blocked", repo)
        out.append({
            "kind": "blocked",
            "key": key,
            "marker": marker("blocked", key),
            "fingerprint": key,
            "repository": repo,
            "reason": item.get("reason", "scan did not complete"),
            "severity": "blocker",
            "owner_role": "ci-owner",
            "owner_handle": (maintainers.get("roles", {}).get("ci-owner") or {}).get("handle"),
        })
    return out


def issue_title(item):
    if item["kind"] == "review":
        return f"[watchdog] Decision review: {item['decision_id']}"
    if item["kind"] == "blocked":
        return f"[watchdog] Scan blocked: {item['repository']}"
    return f"[watchdog] {item['repository']}: {item['check']} / {item['group']}"[:120]


def file_link(repository, commit, path, line):
    if not repository or repository == "unknown" or commit == "unknown":
        return f"`{path}:{line}`"
    return f"[{path}:{line}](https://github.com/openAMRobot/{repository}/blob/{commit}/{path}#L{line})"


def body_for(item, run_url, run_date):
    owner = f"@{item['owner_handle']} ({item['owner_role']})" if item.get("owner_handle") else item.get("owner_role", "unassigned")
    lines = [item["marker"], observation(observation_payload(item)), "", "## OpenAMRobot Watchdog finding", "", f"Owner: {owner}", "@BotshareAI", f"Detected: {run_date}"]
    if item["kind"] == "review":
        lines += [f"Decision entry: `{item['decision_id']}`", f"Review status: {scrub(item['warning'])}", "", "This is a review reminder, not an automatic decision change.", "Confirm the controlling source first. If the source is unchanged, update `review_by` through a reviewed PR. If the source changed, update the source document first, then update `decisions.yaml` and affected consumers in one reviewed PR."]
    elif item["kind"] == "blocked":
        lines += [f"Repository: `{item['repository']}`", f"Status: **BLOCKED** - {scrub(item['reason'])}", "", "The scan did not produce a complete result. Treat the organization audit as incomplete until this is resolved."]
    else:
        lines += [f"Repository: `{item['repository']}`", f"Commit: `{item['commit']}`", f"Check: `{item['check']}`", f"Group: `{item['group']}`", f"Severity: **{item['severity']}**", "", f"Decision or rule: {scrub(item['findings'][0].get('decision', ''))}", f"Why: {scrub(item['findings'][0].get('why', ''))}", f"Fix: {scrub(item['findings'][0].get('fix', ''))}", "", "| Location | Observed text |", "|---|---|"]
        for finding in item["findings"]:
            location = file_link(item["repository"], item["commit"], finding.get("file", "?"), finding.get("line", 1))
            lines.append(f"| {location} | {scrub(finding.get('found', ''))} |")
        lines += ["", "This is a textual consistency signal only. It does not prove mechanical, electrical, safety or release correctness."]
    lines += ["", f"Run: {run_url}", "", "The Watchdog never edits `decisions.yaml`, pushes a branch, opens a pull request, or closes this issue automatically. Resolve it with the responsible owner and a reviewed change where needed."]
    return "\n".join(lines)


def observation_payload(item):
    if item["kind"] == "finding":
        return [(f.get("file"), f.get("line"), f.get("found"), f.get("decision"), f.get("why"), f.get("fix")) for f in item["findings"]]
    return item.get("warning") or item.get("reason")


def observation_comment(item, run_url, run_date):
    return f"{observation(observation_payload(item))}\nWatchdog rerun on {run_date}: the finding is still detected. See the issue body for the current evidence. Run: {run_url}"


def no_longer_comment(item, run_url, run_date):
    return f"{NO_LONGER_MARKER}\nWatchdog rerun on {run_date} no longer detected this finding. The issue remains open for the owner to verify and close. Run: {run_url}"


def extract_markers(text):
    return {marker(kind, key): (kind, key) for kind, key in MARKER_RE.findall(text or "")}


def last_observation(issue):
    texts = [issue.get("body", "")] + [c.get("body", "") for c in issue.get("comments", [])]
    found = []
    for text in texts:
        found.extend(OBSERVATION_RE.findall(text))
    return found[-1] if found else None


def has_no_longer(issue):
    return any(NO_LONGER_MARKER in (c.get("body") or "") for c in issue.get("comments", []))


def plan(reports, blocked, decisions, maintainers, existing, run_url, run_date):
    active = grouped_items(reports, decisions, maintainers) + review_items(reports, decisions, maintainers) + blocked_items(blocked, maintainers)
    active_by_marker = {item["marker"]: item for item in active}
    existing_by_marker = {}
    dashboard = None
    for issue in existing:
        markers = extract_markers(issue.get("body", ""))
        for item_marker in markers:
            existing_by_marker[item_marker] = issue
        if DASHBOARD_MARKER in (issue.get("body") or "") and issue.get("state") == "open":
            dashboard = issue
    opens = []
    updates = []
    for item in active:
        current = digest(json.dumps(observation_payload(item), sort_keys=True, default=str))
        issue = existing_by_marker.get(item["marker"])
        labels = ["watchdog-finding", item["severity"]] if item["kind"] == "finding" else ["watchdog-review", "decision-review", item["severity"]]
        payload = {"title": issue_title(item), "body": body_for(item, run_url, run_date), "labels": labels, "assignees": ["BotshareAI"]}
        if not issue:
            opens.append({**item, "payload": payload, "observation_hash": current})
        elif issue.get("state") != "open":
            updates.append({"issue": issue, "body": observation_comment(item, run_url, run_date), "reopen": True})
        elif last_observation(issue) != current:
            updates.append({"issue": issue, "body": observation_comment(item, run_url, run_date), "reopen": False})
    for item_marker, issue in existing_by_marker.items():
        if item_marker not in active_by_marker and issue.get("state") == "open" and not has_no_longer(issue):
            updates.append({"issue": issue, "body": no_longer_comment({"key": item_marker}, run_url, run_date)})
    return {"active": active, "open": opens, "updates": updates, "dashboard": dashboard, "run_date": run_date, "run_url": run_url}


def dashboard_body(reports, blocked, plan_data, run_url, run_date, links):
    summary = {"date": run_date, "repositories": [(r.get("repository"), r.get("commit"), sum(len(v or []) for v in (r.get("results") or {}).values()), len(r.get("freshness") or [])) for r in reports], "blocked": [(b.get("repository"), b.get("reason")) for b in blocked]}
    lines = [DASHBOARD_MARKER, observation(summary), "", "## OpenAMRobot Watchdog dashboard", "", "@BotshareAI", f"Run: {run_date} ([GitHub Actions run]({run_url}))", "", "The deterministic Watchdog scans the repositories listed in `rollout/repositories.yaml`. It reads product repositories and writes only this control surface. It does not use AI and never edits `decisions.yaml` automatically.", "", "| Repository | Commit | Findings | Review warnings | Shared rules | Status |", "|---|---|---:|---:|---|---|"]
    for report in reports:
        findings = sum(len(value or []) for value in (report.get("results") or {}).values())
        warnings = len(report.get("freshness") or [])
        shared = report.get("results", {}).get("shared-rules")
        adoption = "not enrolled" if shared is None else ("drift" if shared else "pass")
        status = "findings" if findings or warnings else "clean"
        lines.append(f"| {scrub(report.get('repository'))} | `{scrub(report.get('commit', 'unknown'))}` | {findings} | {warnings} | {adoption} | {status} |")
    for item in blocked:
        lines.append(f"| {scrub(item.get('repository'))} | unavailable | - | - | **BLOCKED** |")
    lines += ["", f"Grouped issue actions in this run: {len(plan_data['open'])} new, {len(plan_data['updates'])} comments, {len(plan_data['active'])} active groups.", "", "| Action | Issue |", "|---|---|"]
    for title, url in links:
        lines.append(f"| {scrub(title)} | [open](<{url}>) |")
    lines += ["", "A clean result proves textual consistency only, not mechanical, electrical, safety or release correctness. Owners close finding issues after checking the fixing PR. A decision change follows the source-first, reviewed-PR process."]
    return "\n".join(lines)


def api(method, url, token, data=None):
    request = urllib.request.Request(url, method=method, data=json.dumps(data).encode("utf-8") if data is not None else None, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "openamrobot-watchdog"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"null")


def fetch_existing(repository, token, call=api):
    existing = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repository}/issues?state=all&per_page=100&page={page}"
        items = call("GET", url, token) or []
        for item in items:
            if item.get("pull_request"):
                continue
            body = item.get("body") or ""
            if not (DASHBOARD_MARKER in body or MARKER_RE.search(body)):
                continue
            comments = call("GET", f"https://api.github.com/repos/{repository}/issues/{item['number']}/comments?per_page=100", token) or []
            existing.append({"number": item["number"], "title": item["title"], "body": body, "state": item["state"], "comments": comments, "url": item.get("html_url", "")})
        if len(items) < 100:
            return existing
        page += 1


def create_issue(repository, payload, token, call=api):
    url = f"https://api.github.com/repos/{repository}/issues"
    try:
        return call("POST", url, token, payload)
    except urllib.error.HTTPError:
        fallback = dict(payload)
        fallback.pop("assignees", None)
        try:
            return call("POST", url, token, fallback)
        except urllib.error.HTTPError:
            fallback.pop("labels", None)
            return call("POST", url, token, fallback)


def ensure_labels(repository, labels, token, call=api):
    """Create the small controlled label vocabulary if an owner has not created it yet."""
    for name in sorted(set(labels)):
        color, description = LABEL_METADATA.get(name, ("6e7781", "OpenAMRobot Watchdog label"))
        try:
            call("POST", f"https://api.github.com/repos/{repository}/labels", token,
                 {"name": name, "color": color, "description": description})
        except urllib.error.HTTPError as exc:
            if exc.code != 422:  # GitHub returns 422 when the label already exists.
                raise


def apply(repository, plan_data, reports, blocked, token, run_url, run_date, call=api):
    links = []
    labels = ["watchdog-report"]
    for item in plan_data["open"]:
        labels.extend(item["payload"]["labels"])
    ensure_labels(repository, labels, token, call)
    for item in plan_data["open"]:
        created = create_issue(repository, item["payload"], token, call)
        links.append((item["payload"]["title"], created.get("html_url", "")))
    for update in plan_data["updates"]:
        issue = update["issue"]
        if update.get("reopen"):
            call("PATCH", f"https://api.github.com/repos/{repository}/issues/{issue['number']}", token, {"state": "open"})
        call("POST", f"https://api.github.com/repos/{repository}/issues/{issue['number']}/comments", token, {"body": update["body"]})
        links.append((issue.get("title", "watchdog issue"), issue.get("url", "")))
    dashboard_text = dashboard_body(reports, blocked, plan_data, run_url, run_date, links)
    dashboard = plan_data.get("dashboard")
    dashboard_payload = {"title": "[watchdog] Organization dashboard", "body": dashboard_text, "labels": ["watchdog-report"], "assignees": ["BotshareAI"]}
    dashboard_match = OBSERVATION_RE.search(dashboard_text)
    dashboard_hash = dashboard_match.group(1) if dashboard_match else digest(dashboard_text)
    if not dashboard:
        create_issue(repository, dashboard_payload, token, call)
    elif last_observation(dashboard) != dashboard_hash:
        call("POST", f"https://api.github.com/repos/{repository}/issues/{dashboard['number']}/comments", token, {"body": f"{OBSERVATION_PREFIX}{dashboard_hash}{OBSERVATION_SUFFIX}\n{dashboard_text}"})
    print(f"Watchdog issue sync: {len(plan_data['open'])} opened, {len(plan_data['updates'])} comments, dashboard updated={not bool(dashboard)}")
    for title, url in links:
        print(f"- {title}: {url}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--blocked", type=Path)
    parser.add_argument("--maintainers", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--repository", default="openAMRobot/.github")
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--run-date", default=date.today().isoformat())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    maintainers = yaml.safe_load(args.maintainers.read_text(encoding="utf-8")) or {}
    raw = yaml.safe_load(args.decisions.read_text(encoding="utf-8")) or {}
    decisions = {entry.get("id"): entry for entry in raw.get("decisions", []) if isinstance(entry, dict) and entry.get("id")}
    reports = load_reports(args.reports)
    blocked = load_blocked(args.blocked)
    token = os.environ.get("GITHUB_TOKEN")
    existing = fetch_existing(args.repository, token) if args.apply and token else []
    if args.apply and not token:
        print("--apply requires GITHUB_TOKEN", file=sys.stderr)
        return 2
    data = plan(reports, blocked, decisions, maintainers, existing, args.run_url, args.run_date)
    print(f"Watchdog issue plan: {len(data['open'])} new, {len(data['updates'])} comments, {len(data['active'])} active groups")
    if args.apply:
        apply(args.repository, data, reports, blocked, token, args.run_url, args.run_date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
