#!/usr/bin/env python3
"""Check a finished agent change before anything is pushed.

Runs after the agent step, outside the agent, on the target checkout. It fails
(exit 1) when the change breaks harness/policy.yaml; the workflow then deletes
the branch and reports the reason on the issue. It writes a JSON report.

  harness_guard.py --repo-root PATH --repository NAME --base SHA
                   [--pr-body FILE] [--tests-before N --tests-after M]
                   [--max-tier A|B] [--report FILE]

Checks: clean worktree; nothing committed under .harness-out/; no tier D path;
tier C only as new test files; dependency manifest changes need a Dependencies
section; added skip/xfail/importorskip name an issue; no removed test function;
size limits; DCO sign-off on every commit; no binary files; no secret-like
strings; executed test count does not fall; live workflows stay pinned.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as hl  # noqa: E402

MAX_FILES = 25
MAX_CHANGED_LINES = 800
# Same markers as rollout/verify.sh, plus unittest expectedFailure (launch_testing's
# expected-failure form). Character classes keep this line from matching verify.sh itself.
SKIP = re.compile(r"(pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail|importorskip)\(|unittest\.skip|"
                  r"self\.skipTest\(|expectedFailur[e]|\b(it|test|describe)\.skip\(|\bxit\(|GTEST_SKI[P])")
ISSUE_REF = re.compile(r"(#\d+|issues/\d+)")
TEST_DEF = re.compile(r"^\s*(async\s+)?def\s+(test_\w+)|^\s*TEST(_F|_P)?\(\s*(\w+)\s*,\s*(\w+)|"
                      r"^\s*(it|test)\(\s*['\"]([^'\"]+)")
SECRET = re.compile(r"(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|"
                    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,})")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout


def test_names(lines):
    names = set()
    for line in lines:
        m = TEST_DEF.match(line)
        if m:
            names.add(next(g for g in (m.group(2), m.group(5) and f"{m.group(4)}.{m.group(5)}",
                                       m.group(7)) if g))
    return names


def diff_lines(root, base):
    """Per file: (added lines, removed lines)."""
    out, current, previous = {}, None, None
    for line in git(root, "diff", "--unified=0", "--no-color", "--no-renames", f"{base}..HEAD").splitlines():
        if line.startswith("--- "):
            previous = None if line.endswith("/dev/null") else line[6:]
        elif line.startswith("+++ "):
            current = previous if line.endswith("/dev/null") else line[6:]
            out.setdefault(current, ([], []))
        elif current and line.startswith("+") and not line.startswith("+++"):
            out[current][0].append(line[1:])
        elif current and line.startswith("-") and not line.startswith("---"):
            out[current][1].append(line[1:])
    return out


def run(args):
    root = Path(args.repo_root).resolve()
    policy = hl.load_policy(Path(args.harness_root))
    failures, notes = [], []

    status = git(root, "status", "--porcelain", "--untracked-files=normal")
    dirty = [l for l in status.splitlines() if not l[3:].startswith((".harness", ".claude/skills/harness-"))]
    if dirty:
        failures.append(f"uncommitted changes left in the worktree: {dirty[:5]}")

    changes = [l.split("\t") for l in git(root, "diff", "--name-status", "--no-renames",
                                          f"{args.base}..HEAD").splitlines() if l]
    if not changes:
        failures.append("no change was committed")
    tiers, files_changed = [], []
    for status_code, *paths in changes:
        path = paths[-1]
        files_changed.append(path)
        if path.startswith(".harness-out") or path.startswith(".harness/"):
            failures.append(f"{path}: harness working files must not be committed")
            continue
        tier = hl.tier_of(path, args.repository, policy)
        if tier == "D" and hl.mission_allows(path, args.repository, policy, args.mission):
            tier = "B"
            notes.append(f"{path}: tier D, allowed for the {args.mission} mission")
        elif tier == "D":
            failures.append(f"{path}: tier D, agents never change it")
        elif tier == "C":
            if status_code == "A" and hl.is_test_path(path):
                tier = "A"
                notes.append(f"{path}: new test file for a tier C area")
            else:
                failures.append(f"{path}: tier C, a person writes this change ({status_code})")
        tiers.append(tier)
    tier = hl.highest(tiers)
    if args.max_tier and hl.TIER_ORDER[tier] > hl.TIER_ORDER[args.max_tier]:
        notes.append(f"change is tier {tier}, above the issue's tier {args.max_tier}; labelled tier {tier}")

    body = Path(args.pr_body).read_text(encoding="utf-8") if args.pr_body and Path(args.pr_body).exists() else ""
    manifests = [p for p in files_changed if hl.matches(p, policy.get("dependency_manifests", []))]
    if manifests:
        tier = hl.highest([tier, "B"])
        if not re.search(r"^#+\s*Dependencies", body, re.M | re.I):
            failures.append(f"dependency manifest changed ({', '.join(manifests)}) without a Dependencies section")

    per_file = diff_lines(root, args.base)
    added_total = removed_total = 0
    removed_tests, added_tests = set(), set()
    for path, (added, removed) in per_file.items():
        added_total += len(added)
        removed_total += len(removed)
        for line in added:
            if SKIP.search(line) and not ISSUE_REF.search(line):
                failures.append(f"{path}: skip or xfail without a tracking issue on the same line: {line.strip()[:120]}")
            if SECRET.search(line):
                failures.append(f"{path}: secret-like string added")
        removed_tests |= test_names(removed)
        added_tests |= test_names(added)
    lost = sorted(removed_tests - added_tests)
    if lost:
        failures.append(f"test functions removed: {', '.join(lost[:10])}")
    if len(files_changed) > MAX_FILES:
        failures.append(f"{len(files_changed)} files changed, limit {MAX_FILES}: split the task")
    if added_total + removed_total > MAX_CHANGED_LINES:
        failures.append(f"{added_total + removed_total} lines changed, limit {MAX_CHANGED_LINES}: split the task")

    numstat = git(root, "diff", "--numstat", f"{args.base}..HEAD").splitlines()
    for line in numstat:
        if line.startswith("-\t-\t"):
            failures.append(f"{line.split(chr(9))[-1]}: binary file")

    for sha in git(root, "rev-list", f"{args.base}..HEAD").split():
        message = git(root, "log", "-1", "--format=%B", sha)
        if not re.search(r"^Signed-off-by: .+ <.+>$", message, re.M):
            failures.append(f"commit {sha[:9]} has no Signed-off-by line")

    if args.tests_before is not None and args.tests_after is not None:
        if args.tests_after < args.tests_before:
            failures.append(f"executed tests fell from {args.tests_before} to {args.tests_after}")
        if args.tests_after == 0:
            failures.append("zero tests executed")

    if any(p.startswith(".github/workflows/") for p in files_changed):
        import check_workflow_policy as cwp
        for finding in cwp.records(root):
            if finding["file"] in files_changed:
                failures.append(f"{finding['file']}:{finding['line']}: {finding['text']}")

    report = {"result": "FAIL" if failures else "PASS", "tier": tier, "files": files_changed,
              "lines_added": added_total, "lines_removed": removed_total,
              "failures": failures, "notes": notes}
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--harness-root", default=str(hl.ROOT))
    parser.add_argument("--pr-body")
    parser.add_argument("--tests-before", type=int)
    parser.add_argument("--tests-after", type=int)
    parser.add_argument("--max-tier", choices=["A", "B", "C"])
    parser.add_argument("--mission", default="build")
    parser.add_argument("--report")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
