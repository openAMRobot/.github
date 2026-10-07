#!/usr/bin/env python3
"""Enforce provenance and placeholder rules for live GitHub Actions workflows.

Only .github/workflows/*.yml and *.yaml are scanned. Examples under rollout/ are
intentionally outside this policy. Every external action reference must use a
full 40-character commit SHA; local reusable workflows and docker:// images are
not action references and are ignored.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watchdog_report as wr  # noqa: E402

NEXT_STEP = ("pin each action to the full 40-character commit SHA of the release you use, with the "
             "version as a trailing comment, and replace every <HARNESS_SHA> with the harness merge SHA.")
GUIDE = {
    "unpinned-action": ("Workflow not pinned",
                        "Every action in a live workflow is pinned to a full 40-character commit SHA.",
                        "A tag or branch can be moved to different code; a SHA cannot.",
                        "Replace the tag with the release's commit SHA, e.g. actions/checkout@<sha> # v4.4.0."),
    "harness-placeholder": ("Placeholder left in workflow",
                            "Live workflows contain no <HARNESS_SHA> placeholder from a copied example.",
                            "The placeholder is not a valid reference, so the workflow cannot run as intended.",
                            "Replace <HARNESS_SHA> with the openAMRobot/.github merge SHA (rollout/README.md step b)."),
    "unreadable": ("Workflow unreadable",
                   "Live workflow files are readable UTF-8 text.",
                   "An unreadable workflow cannot be checked.",
                   "Re-save the file as UTF-8 text."),
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")


def workflow_files(root):
    directory = Path(root) / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*")
                  if path.is_file() and path.suffix in {".yml", ".yaml"})


def records(root):
    """Structured findings: dicts with file, line, rule and text."""
    root = Path(root)
    out = []
    for path in workflow_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            out.append({"file": rel, "line": 1, "rule": "unreadable", "text": f"cannot read workflow: {exc}"})
            continue
        for number, line in enumerate(lines, 1):
            if "<HARNESS_SHA>" in line:
                out.append({"file": rel, "line": number, "rule": "harness-placeholder",
                            "text": "unresolved <HARNESS_SHA> placeholder in live workflow"})
            match = USES.match(line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./") or reference.startswith("docker://"):
                continue
            if "@" not in reference:
                out.append({"file": rel, "line": number, "rule": "unpinned-action",
                            "text": f"action reference has no immutable @<full SHA>: {reference}", "found": reference})
                continue
            action, ref = reference.rsplit("@", 1)
            if not action or not FULL_SHA.fullmatch(ref):
                out.append({"file": rel, "line": number, "rule": "unpinned-action",
                            "text": f"action is not pinned to a full commit SHA: {reference}", "found": reference})
    return out


def findings(root):
    """Findings as "path:line: text" strings."""
    return [f"{r['file']}:{r['line']}: {r['text']}" for r in records(root)]


def to_watchdog(recs):
    out = []
    for r in recs:
        label, rule, why, fix = GUIDE[r["rule"]]
        found = r.get("found") or ("<HARNESS_SHA>" if r["rule"] == "harness-placeholder" else r["text"])
        out.append(wr.finding(label, r["rule"], r["file"], r["line"], found, rule, why, fix,
                              [("WATCHDOG.md", f"{wr.DOCS}#workflow-policy")]))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"root is not a directory: {args.root}", file=sys.stderr)
        return 2
    recs = records(args.root)
    errors = [f"{r['file']}:{r['line']}: {r['text']}" for r in recs]
    friendly = to_watchdog(recs)
    if friendly:
        for line in wr.render(friendly, "Workflow policy", NEXT_STEP, decision_word="Rule"):
            print(line)
        wr.emit_github(friendly, "Workflow policy", NEXT_STEP)
    if errors:
        print(f"result: {len(errors)} workflow policy finding(s)")
        return 1
    print("result: 0 workflow policy findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
