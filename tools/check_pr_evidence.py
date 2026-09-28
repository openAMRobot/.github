#!/usr/bin/env python3
"""Check a pull request description and diff against the evidence rules.

Fails when a required template section is missing or empty, when the
Evidence section lacks base SHA, head SHA or a command, when test files
change without a reported non-zero test run, or when safety paths change
without two human reviewers including the platform lead. Writes one
Markdown summary; with --post it creates or updates a single PR comment
identified by a hidden marker. Exit status: 0 pass, 1 fail, 2 usage error.
"""
import argparse
import fnmatch
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

MARKER = "<!-- openamrobot-pr-evidence -->"
SECTIONS = ["Work package", "Integration Gate", "Tests", "Evidence", "Not verified", "AI disclosure"]
SHA = r"\b[0-9a-f]{7,40}\b"
TEST_PATH = [
    "test/*", "tests/*", "*/test/*", "*/tests/*", "*test_*.py", "*_test.py", "*_test.*",
    "*.test.*", "*.spec.*", "*/__tests__/*",
]
DEPENDENCY_FILES = [
    "package.xml", "requirements*.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile*",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "*.repos",
    "platformio.ini", "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
]
NONE = re.compile(r"^\s*(?:none|no|n/a)\b", re.I)
COUNT = re.compile(
    r"(?:\bran\s+(?P<a>\d+)\s+tests?)|(?:\b(?P<b>\d+)\s+(?:tests?\s+)?passed)|(?:\b(?P<c>\d+)\s+tests?\b)",
    re.I,
)


def sections(body):
    """Map heading text (level 2 or 3) to its content, HTML comments removed."""
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    out, current = {}, None
    for line in body.splitlines():
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def find(secs, name):
    name = name.lower()
    for key, value in secs.items():
        if key == name or key.startswith(name):
            return value
    return None


def is_test_path(path):
    return any(fnmatch.fnmatch(path, p) for p in TEST_PATH)


def reported_counts(text):
    counts = []
    for m in COUNT.finditer(text or ""):
        counts.append(int(next(g for g in m.groups() if g is not None)))
    return counts


def human(login):
    return bool(login) and not login.endswith("[bot]")


def evaluate(pr, changed, maintainers, reviews=(), has_state=False):
    """Return (failures, warnings, notes) for a pull_request payload."""
    failures, warnings, notes = [], [], []
    secs = sections(pr.get("body") or "")
    for name in SECTIONS:
        content = find(secs, name)
        if content is None:
            failures.append(f"Missing section: {name}")
        elif not re.sub(r"[-*\s:|]|\[ \]", "", content):
            failures.append(f"Empty section: {name}")

    evidence = find(secs, "Evidence") or ""
    base = re.search(r"base(?:\s+sha)?\s*[:=]\s*`?(" + SHA + ")", evidence, re.I)
    head = re.search(r"head(?:\s+sha)?\s*[:=]\s*`?(" + SHA + ")", evidence, re.I)
    if not base:
        failures.append("Evidence: no base SHA (write `Base SHA: <sha>`)")
    if not head:
        failures.append("Evidence: no head SHA (write `Head SHA: <sha>`)")
    elif pr.get("head", {}).get("sha") and not pr["head"]["sha"].startswith(head.group(1)):
        text = f"Evidence: stated head {head.group(1)} is not the PR head {pr['head']['sha'][:12]}"
        (warnings if pr.get("draft") else failures).append(text + ("; update before ready for review" if pr.get("draft") else ""))
    fenced = [b for b in re.findall(r"```[^\n]*\n(.*?)```", evidence, re.S) if b.strip()]
    if not fenced and not re.search(r"^\s*\$ \S", evidence, re.M):
        failures.append("Evidence: no exact command (use a code block or `$ command` lines)")

    tests_changed = sorted(p for p in changed if is_test_path(p))
    if tests_changed:
        counts = reported_counts((find(secs, "Tests") or "") + "\n" + evidence)
        if not counts:
            failures.append(f"Test files changed ({len(tests_changed)}) but no test run with a count is reported")
        elif max(counts) == 0:
            failures.append("Reported test run executed zero tests")
        else:
            notes.append(f"Test files changed: {len(tests_changed)}; reported run counts: {counts}")

    deps = sorted(p for p in changed if any(fnmatch.fnmatch(p.rsplit("/", 1)[-1], g) for g in DEPENDENCY_FILES))
    if deps:
        section = find(secs, "Dependencies") or ""
        if not section or NONE.match(section):
            failures.append(f"Dependency manifests changed ({', '.join(deps[:5])}) but the Dependencies "
                            "section does not name the change, licence and source")

    if has_state and "STATE.md" not in changed:
        section = find(secs, "STATE.md") or ""
        if not re.search(r"no change\W+\w", section, re.I):
            failures.append("STATE.md exists but is not updated; update it or write 'no change' with a reason")

    roles = (maintainers or {}).get("roles", {})
    lead = (roles.get("platform-lead") or {}).get("handle")
    safety = [p for p in changed if any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(p, g.replace("**/", ""))
                                        for g in (maintainers or {}).get("safety_paths", []))]
    if safety:
        people = {u.get("login") for u in pr.get("requested_reviewers") or []}
        people |= {r.get("user", {}).get("login") for r in reviews}
        people = {p for p in people if human(p) and p != pr.get("user", {}).get("login")}
        notes.append(f"Safety paths changed: {', '.join(safety[:10])}")
        if len(people) < 2:
            failures.append(f"Safety paths changed: {len(people)} human reviewer(s) requested, 2 required")
        if lead and lead not in people:
            failures.append(f"Safety paths changed: platform lead @{lead} is not among the reviewers")
        ai = find(secs, "AI disclosure") or ""
        if ai and not NONE.match(ai):
            failures.append("Safety paths changed in a PR with AI assistance; agents do not author "
                            "safety logic, a human authors it and the agent reports the need in an issue")
    return failures, warnings, notes


def decision_failures(report, limit=20):
    """Turn check_decisions.py output lines into summary failures."""
    lines = [l[len("CONTRADICTION "):] for l in report.splitlines() if l.startswith("CONTRADICTION ")]
    out = [f"Decision contradiction: {l}" for l in lines[:limit]]
    if len(lines) > limit:
        out.append(f"... and {len(lines) - limit} more decision contradictions")
    if "INVALID decisions file" in report:
        out.append("decisions.yaml is invalid; see the workflow log")
    return out


def render(failures, warnings, notes, pr):
    status = "FAIL" if failures else "PASS"
    lines = [MARKER, f"### PR evidence check: {status}", "",
             f"Head checked: `{pr.get('head', {}).get('sha', 'unknown')[:12]}`. "
             "This comment is updated in place on every push. It never approves or merges.", ""]
    for title, items in (("Failures", failures), ("Warnings", warnings), ("Notes", notes)):
        if items:
            lines.append(f"**{title}**")
            lines += [f"- {i}" for i in items]
            lines.append("")
    if not (failures or warnings or notes):
        lines.append("All required sections and evidence are present.")
    lines.append("Rules: AGENTS.md in openAMRobot/.github; template: .github/PULL_REQUEST_TEMPLATE.md.")
    return "\n".join(lines) + "\n"


def api(method, url, token, data=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read() or b"null")


def upsert_comment(repo, number, body, token, call=api):
    base = f"https://api.github.com/repos/{repo}/issues"
    page = 1
    while True:
        comments = call("GET", f"{base}/{number}/comments?per_page=100&page={page}", token)
        for c in comments:
            if MARKER in (c.get("body") or ""):
                call("PATCH", f"{base}/comments/{c['id']}", token, {"body": body})
                return "updated"
        if len(comments) < 100:
            break
        page += 1
    call("POST", f"{base}/{number}/comments", token, {"body": body})
    return "created"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--event", type=Path, default=os.environ.get("GITHUB_EVENT_PATH"))
    p.add_argument("--changed-files", type=Path, required=True)
    p.add_argument("--maintainers", type=Path, required=True)
    p.add_argument("--reviews", type=Path, help="JSON list of PR reviews")
    p.add_argument("--root", type=Path, help="checkout of the PR head; enables the STATE.md rule")
    p.add_argument("--decisions-report", type=Path,
                   help="stdout of check_decisions.py on the diff; contradictions become failures")
    p.add_argument("--output", type=Path, help="write the Markdown summary here")
    p.add_argument("--post", action="store_true", help="create or update the PR comment")
    a = p.parse_args(argv)
    if not a.event:
        p.error("--event or GITHUB_EVENT_PATH is required")
    event = json.loads(Path(a.event).read_text(encoding="utf-8"))
    pr = event.get("pull_request")
    if not pr:
        print("not a pull_request event; nothing to check", file=sys.stderr)
        return 2
    changed = [l.strip() for l in a.changed_files.read_text(encoding="utf-8").splitlines() if l.strip()]
    maintainers = yaml.safe_load(a.maintainers.read_text(encoding="utf-8"))
    reviews = json.loads(a.reviews.read_text(encoding="utf-8")) if a.reviews else []
    has_state = bool(a.root and (a.root / "STATE.md").is_file())
    failures, warnings, notes = evaluate(pr, changed, maintainers, reviews, has_state)
    if a.decisions_report:
        failures += decision_failures(a.decisions_report.read_text(encoding="utf-8"))
    summary = render(failures, warnings, notes, pr)
    print(summary)
    if a.output:
        a.output.write_text(summary, encoding="utf-8")
    if a.post:
        token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
        if not token or not repo:
            print("--post needs GITHUB_TOKEN and GITHUB_REPOSITORY", file=sys.stderr)
            return 2
        print(f"comment {upsert_comment(repo, pr['number'], summary, token)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
