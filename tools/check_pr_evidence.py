#!/usr/bin/env python3
"""Check a pull request description and diff against the evidence rules.

Fails when a required template section is missing or empty, when the
Evidence section lacks base SHA, head SHA or a command, when test files
change without a reported non-zero test run, or when safety paths change
and fewer than two human reviewers (including the platform lead) are
requested. Requesting reviewers is not approval: this check reports "safety
path touched, two human approvals required" and counts approvals for
information only; the approvals themselves are enforced by the repository
ruleset (rollout/workflows/SETUP.md), not by this check. Writes one
Markdown summary; a decisions-check run that ends in anything other than
its two documented outcomes (exit 0 clean, exit 1 with contradictions) is a
"checker error" and fails closed. With --post it creates or updates a single PR comment
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


AI_TOOL = re.compile(r"\b(?:Claude(?:\s+Code)?|Anthropic|ChatGPT|OpenAI|Codex|Copilot|Gemini|Cursor|Devin)\b", re.I)
AI_MARKER = re.compile(r"(?:AI[-\s]+assisted|generated with|co-authored-by:.*(?:bot|claude|copilot|chatgpt|openai|anthropic|codex))", re.I)
AI_SCOPE = re.compile(r"\b(?:scope|drafted|generated|reviewed|changed|implemented|tested|research|documentation|workflow|code|text|analysis|reconciliation)\b", re.I)


def ai_assistance_detected(pr, commit_messages=()):
    text = (pr.get("body") or "") + "\n" + "\n".join(commit_messages or ())
    return bool(AI_TOOL.search(text) or AI_MARKER.search(text))


def check_ai_disclosure(pr, commit_messages, disclosure):
    if not ai_assistance_detected(pr, commit_messages):
        return []
    if not disclosure or NONE.match(disclosure):
        return ["AI assistance is visible in the PR or commit messages, but AI disclosure is empty; name the tool and scope"]
    failures = []
    if not AI_TOOL.search(disclosure):
        failures.append("AI disclosure must name the AI tool used (for example Claude Code, ChatGPT or Codex)")
    if not AI_SCOPE.search(disclosure):
        failures.append("AI disclosure must state the scope of assistance (what it drafted, changed, tested or reviewed)")
    return failures


def evaluate(pr, changed, maintainers, reviews=(), has_state=False, commit_messages=()):
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

    deps = sorted(p for p in changed if any(fnmatch.fnmatch(p.rsplit("/", 1)[-1], g) for g in DEPENDENCY_FILES)
                  and not re.search(r"(^|/)(fixtures|testdata)/", p))
    if deps:
        section = find(secs, "Dependencies") or ""
        if not section or NONE.match(section):
            failures.append(f"Dependency manifests changed ({', '.join(deps[:5])}) but the Dependencies "
                            "section does not name the change, licence and source")

    if has_state and "STATE.md" not in changed:
        section = find(secs, "STATE.md") or ""
        if not re.search(r"no change\W+\w", section, re.I):
            failures.append("STATE.md exists but is not updated; update it or write 'no change' with a reason")

    ai_disclosure = find(secs, "AI disclosure") or ""
    failures.extend(check_ai_disclosure(pr, commit_messages, ai_disclosure))

    contribution_terms = find(secs, "Contribution terms")
    if contribution_terms is not None and not re.search(
        r"\[x\]\s+No partner, customer or private person is named; the application is Use_Case_1\.",
        contribution_terms, re.I
    ):
        failures.append("Contribution terms: check the Use_Case_1/no-private-person checkbox")

    roles = (maintainers or {}).get("roles", {})
    lead = (roles.get("platform-lead") or {}).get("handle")
    safety = [p for p in changed if any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(p, g.replace("**/", ""))
                                        for g in (maintainers or {}).get("safety_paths", []))]
    if safety:
        people = {u.get("login") for u in pr.get("requested_reviewers") or []}
        people |= {r.get("user", {}).get("login") for r in reviews}
        people = {p for p in people if human(p) and p != pr.get("user", {}).get("login")}
        approvals = {r.get("user", {}).get("login") for r in reviews if r.get("state") == "APPROVED"}
        approvals = {p for p in approvals if human(p) and p != pr.get("user", {}).get("login")}
        notes.append(f"Safety path touched, two human approvals required: {', '.join(safety[:10])}. "
                     f"Human approvals so far: {len(approvals)} (information only; the ruleset enforces approvals, "
                     "this check does not)")
        if len(people) < 2:
            failures.append(f"Safety path touched, two human approvals required: only {len(people)} "
                            "human reviewer(s) requested")
        if lead and lead not in people:
            failures.append(f"Safety path touched, two human approvals required: platform lead @{lead} "
                            "is not requested")
        ai = find(secs, "AI disclosure") or ""
        if ai and not NONE.match(ai):
            failures.append("Safety paths changed in a PR with AI assistance; agents do not author "
                            "safety logic, a human authors it and the agent reports the need in an issue")
    return failures, warnings, notes


# First line of each check_decisions.py finding (tools/watchdog_report.py format).
DECISION_FINDING = "Mismatch with approved decision: "
DECISION_GROUP = re.compile(r"^Mismatch with approved decision: (?P<id>\S+) \(\d+ finding\(s\)\)$")
DECISION_ITEM = re.compile(r"^    (?P<place>\S.*?:\d+): found (?P<found>.*)$")


def decision_findings(report):
    """One line per finding from the grouped Watchdog report: place, ID, found text and the
    group's one-line Decision ("docs/a.md:4: ID found 'x'; decision: ...")."""
    out = []
    group = decision = None
    for line in report.splitlines():
        m = DECISION_GROUP.match(line)
        if m:
            group, decision = m.group("id"), None
            continue
        if group is None:
            continue
        if line.startswith("  Decision:"):
            decision = line[len("  Decision:"):].strip()
            continue
        item = DECISION_ITEM.match(line)
        if item:
            text = f"{item.group('place')}: {group} found {item.group('found')}"
            out.append(text + (f"; decision: {decision}" if decision else ""))
        elif not line.startswith("  "):
            group = None
    return out


def decision_failures(report, limit=20):
    """Turn check_decisions.py findings into summary failures."""
    lines = decision_findings(report)
    out = [f"Decision contradiction: {l}" for l in lines[:limit]]
    if len(lines) > limit:
        out.append(f"... and {len(lines) - limit} more decision contradictions")
    if "INVALID decisions file" in report:
        out.append("decisions.yaml is invalid; see the workflow log")
    return out


RESULT_LINE = re.compile(r"^result: (\d+) contradiction\(s\)", re.M)


def decision_verdict(report, status):
    """Classify a check_decisions.py run; return (failures, checker_errors).

    report is the checker's combined output (None if the file is missing);
    status is the parsed status file, e.g. {"exit_code": 1} (None if missing).
    Only the two documented policy outcomes are accepted:
      exit 0 with "result: 0 contradiction(s)" and no finding lines (clean);
      exit 1 with "Mismatch with approved decision:" finding lines whose count matches the result line.
    Everything else fails closed as a checker error: a crash, exit 2 (invalid
    register or usage), any other exit code, empty output, or a missing file.
    """
    if report is None:
        return [], ["checker error: decisions report missing; the decisions check did not produce output"]
    code = status.get("exit_code") if isinstance(status, dict) else None
    if not isinstance(code, int) or isinstance(code, bool):
        return [], ["checker error: decisions status file missing or unreadable; exit status of "
                    "check_decisions.py unknown"]
    head = " | ".join(l for l in report.strip().splitlines()[-3:]) or "no output"
    if "Traceback (most recent call last)" in report:
        return [], [f"checker error: check_decisions.py crashed (exit {code}): {head}"]
    listed = decision_failures(report)
    contradictions = decision_findings(report)
    m = RESULT_LINE.search(report)
    reported = int(m.group(1)) if m else None
    if code == 0 and reported == 0 and not contradictions:
        return [], []
    if code == 1 and reported is not None and reported == len(contradictions) > 0:
        return listed, []
    if code == 2:
        return [], [f"checker error: check_decisions.py exit 2 (invalid register or usage error): {head}"]
    return [], [f"checker error: unexpected check_decisions.py outcome (exit {code}, "
                f"{len(contradictions)} contradiction line(s), result line "
                f"{'missing' if reported is None else reported}): {head}"]


def render(failures, warnings, notes, pr, checker_errors=()):
    status = "CHECKER ERROR" if checker_errors else ("FAIL" if failures else "PASS")
    lines = [MARKER, f"### PR evidence check: {status}", "",
             f"Head checked: `{pr.get('head', {}).get('sha', 'unknown')[:12]}`. "
             "This comment is updated in place on every push. It never approves or merges.", ""]
    for title, items in (("Checker errors (fails closed; the result of the check is unknown)",
                          list(checker_errors)),
                         ("Failures", failures), ("Warnings", warnings), ("Notes", notes)):
        if items:
            lines.append(f"**{title}**")
            lines += [f"- {i}" for i in items]
            lines.append("")
    if not (failures or warnings or notes or checker_errors):
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
    p.add_argument("--commit-messages", type=Path, help="one or more PR commit messages, one per line or JSON text")
    p.add_argument("--root", type=Path, help="checkout of the PR head; enables the STATE.md rule")
    p.add_argument("--decisions-report", type=Path,
                   help="combined output of check_decisions.py on the diff")
    p.add_argument("--decisions-status", type=Path,
                   help='JSON status file written by the workflow, e.g. {"exit_code": 1}; required with --decisions-report')
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
    commit_messages = a.commit_messages.read_text(encoding="utf-8").splitlines() if a.commit_messages else []
    has_state = bool(a.root and (a.root / "STATE.md").is_file())
    failures, warnings, notes = evaluate(pr, changed, maintainers, reviews, has_state, commit_messages)
    checker_errors = []
    if a.decisions_report or a.decisions_status:
        report = status = None
        try:
            report = a.decisions_report.read_text(encoding="utf-8") if a.decisions_report else None
        except OSError:
            report = None
        try:
            status = json.loads(a.decisions_status.read_text(encoding="utf-8")) if a.decisions_status else None
        except (OSError, ValueError):
            status = None
        decision_fails, checker_errors = decision_verdict(report, status)
        failures += decision_fails
    summary = render(failures, warnings, notes, pr, checker_errors)
    print(summary)
    if a.output:
        a.output.write_text(summary, encoding="utf-8")
    if a.post:
        token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
        if not token or not repo:
            print("--post needs GITHUB_TOKEN and GITHUB_REPOSITORY", file=sys.stderr)
            return 2
        print(f"comment {upsert_comment(repo, pr['number'], summary, token)}")
    return 1 if failures or checker_errors else 0


if __name__ == "__main__":
    sys.exit(main())
