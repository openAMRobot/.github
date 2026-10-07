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

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")


def workflow_files(root):
    directory = Path(root) / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*")
                  if path.is_file() and path.suffix in {".yml", ".yaml"})


def findings(root):
    root = Path(root)
    out = []
    for path in workflow_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            out.append(f"{rel}:1: cannot read workflow: {exc}")
            continue
        for number, line in enumerate(lines, 1):
            if "<HARNESS_SHA>" in line:
                out.append(f"{rel}:{number}: unresolved <HARNESS_SHA> placeholder in live workflow")
            match = USES.match(line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./") or reference.startswith("docker://"):
                continue
            if "@" not in reference:
                out.append(f"{rel}:{number}: action reference has no immutable @<full SHA>: {reference}")
                continue
            action, ref = reference.rsplit("@", 1)
            if not action or not FULL_SHA.fullmatch(ref):
                out.append(f"{rel}:{number}: action is not pinned to a full commit SHA: {reference}")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"root is not a directory: {args.root}", file=sys.stderr)
        return 2
    errors = findings(args.root)
    for error in errors:
        print(f"WORKFLOW-POLICY {error}")
    if errors:
        print(f"result: {len(errors)} workflow policy finding(s)")
        return 1
    print("result: 0 workflow policy findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
