#!/usr/bin/env python3
"""Collect the daily, deterministic software-health report of the Watchdog.

For every repository in rollout/repositories.yaml this tool reads, through the GitHub REST API:
  - the latest conclusion per workflow on the default branch in the last 7 days, and the 7-day
    green rate (success divided by success, failure, timed_out and startup_failure; cancelled,
    skipped and neutral runs are counted apart and never as green or red);
  - open pull requests with age, draft state, last update and author;
  - open issues labelled rc.1 or titled with [rc.1], with assignees and age;
  - pull requests and issues with no update for 14 days.
It writes daily.json (everything) and daily.md (at most 60 lines: changes since the previous
daily.json first, then one table row per repository).

Read-only: GET requests only, standard library only, no AI. The report depends only on the API
data and --now, so the same input gives the same output.

Fail closed: a repository whose data cannot be read completely (HTTP error, rate limit that does
not reset within --max-wait, too many pages, malformed response) is reported as "not measured"
with the reason, nothing from it is shown as current, and the run is INCOMPLETE (exit 1 after the
files are written). Exit 2 means the repository list itself could not be read; nothing is written.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
CI_DAYS = 7
STALE_DAYS = 14
MAX_PAGES = 20
MAX_LINES = 60
CELL_ITEMS = 3
GREEN = {"success"}
RED = {"failure", "timed_out", "startup_failure"}
RC1_LABEL = "rc.1"
RC1_TITLE = "[rc.1]"
LOGIN = re.compile(r"[^A-Za-z0-9_.\[\]-]")
WORKFLOW = re.compile(r"[^A-Za-z0-9_.-]")


class ApiError(Exception):
    pass


class ListError(ValueError):
    pass


def load_repositories(path):
    """Read rollout/repositories.yaml (flow-mapping entries, one per line) without PyYAML.
    Returns (organization, [(name, default_branch)]). Raises ListError when unusable."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ListError(f"{path}: {exc}") from exc
    org = None
    repos = []
    for line in text.splitlines():
        if line.startswith("organization:"):
            org = line.split(":", 1)[1].strip()
            continue
        match = re.match(r"^\s*-\s*\{(.*)\}\s*$", line)
        if not match:
            continue
        fields = dict(part.split(":", 1) for part in match.group(1).split(",") if ":" in part)
        fields = {k.strip(): v.strip() for k, v in fields.items()}
        name, branch = fields.get("name"), fields.get("default_branch")
        if not name or not branch or not re.fullmatch(r"[A-Za-z0-9._-]+", name) \
                or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
            raise ListError(f"{path}: unusable entry: {line.strip()}")
        repos.append((name, branch))
    if not org or not re.fullmatch(r"[A-Za-z0-9-]+", org) or not repos:
        raise ListError(f"{path}: no organization or no repositories")
    if len({name for name, _ in repos}) != len(repos):
        raise ListError(f"{path}: duplicate repository")
    return org, repos


def urllib_transport(url, headers):
    """GET url; returns (status, headers, body). HTTP errors are returned, not raised."""
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read() or b""


def header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value
    return None


def next_link(headers):
    for part in (header(headers, "Link") or "").split(","):
        match = re.match(r'\s*<([^>]+)>\s*;\s*rel="next"', part)
        if match:
            return match.group(1)
    return None


class Api:
    """GET-only GitHub REST client with pagination, rate-limit waits and bounded retries."""

    def __init__(self, token=None, transport=None, sleep=None, clock=None,
                 max_wait=300, retries=3, max_pages=MAX_PAGES):
        self.headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                        "User-Agent": "openamrobot-watchdog-daily"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.transport = transport or urllib_transport
        self.sleep, self.clock = sleep or time.sleep, clock or time.time
        self.max_wait, self.retries, self.max_pages = max_wait, retries, max_pages
        self.requests = 0

    def wait_for(self, status, headers):
        """Seconds to wait before retrying a rate-limited response, or None if not rate limited."""
        retry_after = header(headers, "Retry-After")
        if status in (403, 429) and retry_after and retry_after.isdigit():
            return int(retry_after)
        if status in (403, 429) and header(headers, "X-RateLimit-Remaining") == "0":
            reset = header(headers, "X-RateLimit-Reset")
            if reset and reset.isdigit():
                return max(1, int(reset) - int(self.clock()) + 1)
            return self.max_wait + 1  # limit reached, reset unknown: do not guess
        if status == 429:
            return 60
        return None

    def get(self, url):
        """One page: (json body, headers). Raises ApiError."""
        for attempt in range(self.retries + 1):
            self.requests += 1
            try:
                status, headers, body = self.transport(url, self.headers)
            except (urllib.error.URLError, OSError) as exc:
                if attempt < self.retries:
                    self.sleep(2 ** (attempt + 1))
                    continue
                raise ApiError(f"network error: {exc}") from exc
            if status == 200:
                try:
                    return json.loads(body or b"null"), headers
                except ValueError as exc:
                    raise ApiError("malformed JSON response") from exc
            wait = self.wait_for(status, headers)
            if wait is not None:
                if wait > self.max_wait:
                    raise ApiError(f"HTTP {status}: rate limited for {wait} s, more than {self.max_wait} s")
                if attempt < self.retries:
                    self.sleep(wait)
                    continue
                raise ApiError(f"HTTP {status}: still rate limited after {self.retries} retries")
            if status >= 500 and attempt < self.retries:
                self.sleep(2 ** (attempt + 1))
                continue
            raise ApiError(f"HTTP {status}")
        raise ApiError("no response")

    def get_all(self, url, key=None):
        """Every item of a paginated list, following Link rel="next". Raises ApiError."""
        items = []
        for _ in range(self.max_pages):
            data, headers = self.get(url)
            page = data.get(key) if key and isinstance(data, dict) else data
            if not isinstance(page, list):
                raise ApiError("unexpected response shape")
            items.extend(page)
            url = next_link(headers)
            if not url:
                return items
        raise ApiError(f"more than {self.max_pages} pages")


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def days(now, value):
    return int((now - parse_time(value)).total_seconds() // 86400)


def login(user):
    return LOGIN.sub("", (user or {}).get("login") or "") or "unknown"


def workflow_label(path):
    """The workflow file name: stable, and safe to print (a workflow's display name is not)."""
    base = (path or "unknown").rstrip("/").rsplit("/", 1)[-1]
    return WORKFLOW.sub("", base)[:60] or "unknown"


def collect_ci(api, base, org, name, branch, now):
    since = (now - timedelta(days=CI_DAYS))
    query = urllib.parse.urlencode({"branch": branch, "status": "completed",
                                    "created": f">={since.date().isoformat()}", "per_page": 100})
    runs = api.get_all(f"{base}/repos/{org}/{name}/actions/runs?{query}", key="workflow_runs")
    latest = {}
    green = red = other = 0
    for run in runs:
        head = (run.get("head_repository") or {}).get("full_name")
        if run.get("head_branch") != branch or (head and head.lower() != f"{org}/{name}".lower()):
            continue  # a fork pull request whose branch happens to share the name
        if parse_time(run["created_at"]) < since:
            continue
        conclusion = run.get("conclusion") or "unknown"
        if conclusion in GREEN:
            green += 1
        elif conclusion in RED:
            red += 1
        else:
            other += 1
        path = run.get("path") or str(run.get("workflow_id"))
        current = latest.get(path)
        if current is None or (run["created_at"], run["id"]) > (current["created_at"], current["run_id"]):
            latest[path] = {"workflow": workflow_label(path), "conclusion": conclusion,
                            "created_at": run["created_at"], "run_id": run["id"]}
    counted = green + red
    return {"workflows": [latest[k] for k in sorted(latest)], "green": green, "red": red, "other": other,
            "green_rate": round(green / counted, 3) if counted else None}


def collect_pulls(api, base, org, name, now):
    pulls = api.get_all(f"{base}/repos/{org}/{name}/pulls?state=open&per_page=100")
    out = [{"number": p["number"], "draft": bool(p.get("draft")), "author": login(p.get("user")),
            "created_at": p["created_at"], "updated_at": p["updated_at"],
            "age_days": days(now, p["created_at"]), "idle_days": days(now, p["updated_at"])} for p in pulls]
    return sorted(out, key=lambda p: p["number"])


def is_rc1(issue):
    labels = {(label.get("name") or "").lower() for label in issue.get("labels") or [] if isinstance(label, dict)}
    return RC1_LABEL in labels or RC1_TITLE in (issue.get("title") or "").lower()


def collect_issues(api, base, org, name, now):
    """Open issues (pull requests removed). Returns None when the repository has issues disabled."""
    try:
        items = api.get_all(f"{base}/repos/{org}/{name}/issues?state=open&per_page=100")
    except ApiError as exc:
        if str(exc) == "HTTP 410":
            return None  # GitHub answers 410 Gone when issues are disabled: a fact, not a failure
        raise
    out = [{"number": i["number"], "rc1": is_rc1(i), "assignees": sorted(login(a) for a in i.get("assignees") or []),
            "created_at": i["created_at"], "updated_at": i["updated_at"],
            "age_days": days(now, i["created_at"]), "idle_days": days(now, i["updated_at"])}
           for i in items if not i.get("pull_request")]
    return sorted(out, key=lambda i: i["number"])


def collect_repository(api, base, org, name, branch, now):
    """One repository's record; never raises. Any read failure makes it 'not measured'."""
    step = "workflow runs"
    try:
        ci = collect_ci(api, base, org, name, branch, now)
        step = "pull requests"
        pulls = collect_pulls(api, base, org, name, now)
        step = "issues"
        issues = collect_issues(api, base, org, name, now)
    except (ApiError, KeyError, TypeError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, ApiError) else f"malformed {type(exc).__name__}"
        return {"repository": name, "default_branch": branch, "measured": False, "reason": f"{step}: {reason}"}
    issue_list = issues or []
    return {
        "repository": name, "default_branch": branch, "measured": True, "ci": ci,
        "pull_requests": pulls,
        "issues_enabled": issues is not None,
        "rc1_issues": [{k: i[k] for k in ("number", "assignees", "created_at", "updated_at", "age_days", "idle_days")}
                       for i in issue_list if i["rc1"]],
        "stale": {"pull_requests": [p["number"] for p in pulls if p["idle_days"] >= STALE_DAYS],
                  "issues": [i["number"] for i in issue_list if i["idle_days"] >= STALE_DAYS]},
    }


def collect(api, org, repos, now, base=API):
    results = [collect_repository(api, base, org, name, branch, now) for name, branch in repos]
    measured = sum(1 for r in results if r["measured"])
    return {"schema_version": 1, "organization": org, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ci_window_days": CI_DAYS, "stale_days": STALE_DAYS,
            "status": "complete" if measured == len(results) else "incomplete",
            "measured": measured, "expected": len(results), "repositories": results}


def load_previous(path):
    """The previous daily.json, or None when absent or unreadable (never a guessed baseline)."""
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("repositories"), list):
        return None
    return data


def changes(previous, current):
    """Deterministic list of changes from the previous report to this one."""
    if previous is None:
        return []
    before = {r.get("repository"): r for r in previous["repositories"] if isinstance(r, dict)}
    out = []
    for repo in current["repositories"]:
        name = repo["repository"]
        old = before.get(name)
        if old is None:
            out.append(f"{name}: new in the report")
            continue
        if not repo["measured"]:
            if old.get("measured"):
                out.append(f"{name}: now not measured ({repo['reason']})")
            continue
        if not old.get("measured"):
            out.append(f"{name}: measured again")
            continue
        old_ci = {w["workflow"]: w["conclusion"] for w in old.get("ci", {}).get("workflows", [])}
        for w in repo["ci"]["workflows"]:
            was = old_ci.get(w["workflow"])
            if was != w["conclusion"]:
                out.append(f"{name}: CI {w['workflow']} {was or 'no run'} -> {w['conclusion']}")
        old_prs = {p["number"] for p in old.get("pull_requests", [])}
        new_prs = {p["number"] for p in repo["pull_requests"]}
        out += [f"{name}: PR #{n} opened" for n in sorted(new_prs - old_prs)]
        out += [f"{name}: PR #{n} no longer open" for n in sorted(old_prs - new_prs)]
        old_rc = {i["number"] for i in old.get("rc1_issues", [])}
        new_rc = {i["number"] for i in repo["rc1_issues"]}
        out += [f"{name}: rc.1 issue #{n} opened" for n in sorted(new_rc - old_rc)]
        out += [f"{name}: rc.1 issue #{n} no longer open" for n in sorted(old_rc - new_rc)]
        for kind, label in (("pull_requests", "PR"), ("issues", "issue")):
            old_stale = set(old.get("stale", {}).get(kind, []))
            out += [f"{name}: {label} #{n} now stale" for n in sorted(set(repo["stale"][kind]) - old_stale)]
    return out


def listed(items, render):
    shown = [render(item) for item in items[:CELL_ITEMS]]
    if len(items) > CELL_ITEMS:
        shown.append(f"+{len(items) - CELL_ITEMS} more")
    return "; ".join(shown)


def row(repo):
    name = repo["repository"]
    if not repo["measured"]:
        return f"| {name} | not measured: {repo['reason']} | - | - | - | - |"
    ci = repo["ci"]
    failing = [w["workflow"] for w in ci["workflows"] if w["conclusion"] in RED]
    passing = sum(1 for w in ci["workflows"] if w["conclusion"] in GREEN)
    others = len(ci["workflows"]) - len(failing) - passing
    if not ci["workflows"]:
        ci_cell = "no runs"
    else:
        parts = [f"{len(failing)} red: {', '.join(failing)}"] if failing else []
        parts.append(f"{passing} green")
        if others:
            parts.append(f"{others} other")
        ci_cell = "; ".join(parts)
    counted = ci["green"] + ci["red"]
    rate = f"{round(100 * ci['green'] / counted)}% ({ci['green']}/{counted})" if counted else "no runs"
    prs = repo["pull_requests"]
    drafts = sum(1 for p in prs if p["draft"])
    pr_cell = "none" if not prs else f"{len(prs)} ({drafts} draft): " + listed(
        prs, lambda p: f"#{p['number']} {p['author']}{' draft' if p['draft'] else ''} {p['age_days']}d, upd {p['idle_days']}d")
    if not repo["issues_enabled"]:
        rc_cell = "issues disabled"
    else:
        rc_cell = listed(repo["rc1_issues"], lambda i: f"#{i['number']} {', '.join(i['assignees']) or 'unassigned'} {i['age_days']}d") or "none"
    stale = [f"PR #{n}" for n in repo["stale"]["pull_requests"]] + [f"issue #{n}" for n in repo["stale"]["issues"]]
    stale_cell = listed(stale, str) or "none"
    return f"| {name} | {ci_cell} | {rate} | {pr_cell} | {rc_cell} | {stale_cell} |"


def render(report, previous):
    status = report["status"].upper()
    head = [f"### Daily software health, {report['generated_at'].replace('T', ' ').replace('Z', ' UTC')}: "
            f"{status} ({report['measured']} of {report['expected']} repositories measured)", "",
            f"Read-only GitHub REST API data for the repositories in rollout/repositories.yaml. CI: default branch, "
            f"last {report['ci_window_days']} days; green rate = success / (success + failure + timed out + startup failure). "
            f"Stale: no update for {report['stale_days']} days. Deterministic, no AI."]
    if report["status"] != "complete":
        head += ["", "**INCOMPLETE: repositories marked not measured were not read and are not healthy or clean.**"]
    table = ["", "| Repository | CI latest per workflow | Green 7d | Open PRs | rc.1 issues | Stale |",
             "|---|---|---|---|---|---|"] + [row(r) for r in report["repositories"]]
    if previous is None:
        diff = ["", "Changes: no previous report available; changes are listed from the next run."]
    else:
        found = changes(previous, report)
        budget = MAX_LINES - len(head) - len(table) - 3
        title = f"Changes since {previous.get('generated_at', 'the previous report')}:"
        if not found:
            diff = ["", f"{title} none."]
        else:
            shown = found if len(found) <= budget else found[:max(budget - 1, 0)] + [f"and {len(found) - max(budget - 1, 0)} more in daily.json"]
            diff = ["", title] + [f"- {line}" for line in shown]
    lines = head + diff + table
    if len(lines) > MAX_LINES:  # more repositories than the line budget: never silently drop rows
        lines = lines[:MAX_LINES - 1] + [f"Report truncated at {MAX_LINES} lines; daily.json holds every repository."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repositories", type=Path, default=Path("rollout/repositories.yaml"))
    parser.add_argument("--out", type=Path, required=True, help="directory for daily.json and daily.md")
    parser.add_argument("--previous", type=Path, help="daily.json of the previous run (optional)")
    parser.add_argument("--now", help="report time, ISO 8601 UTC (default: now)")
    parser.add_argument("--api-url", default=API)
    parser.add_argument("--max-wait", type=int, default=300, help="longest rate-limit wait in seconds")
    args = parser.parse_args(argv)
    try:
        org, repos = load_repositories(args.repositories)
    except ListError as exc:
        print(f"Daily report not produced: the repository list could not be read ({exc})", file=sys.stderr)
        return 2
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc).replace(microsecond=0)
    api = Api(os.environ.get("GITHUB_TOKEN"), max_wait=args.max_wait)
    report = collect(api, org, repos, now, base=args.api_url.rstrip("/"))
    previous = load_previous(args.previous)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "daily.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "daily.md").write_text(render(report, previous), encoding="utf-8")
    print(f"Daily report {report['status']}: {report['measured']} of {report['expected']} repositories measured, "
          f"{api.requests} API requests")
    for repo in report["repositories"]:
        if not repo["measured"]:
            print(f"::error::{repo['repository']} not measured: {repo['reason']}")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
