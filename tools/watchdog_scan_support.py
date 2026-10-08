#!/usr/bin/env python3
"""Fail-closed helpers for the Watchdog organization scan (.github/workflows/watchdog-org-scan.yml).

Each subcommand does one step and exits non-zero when it cannot do it, so the workflow can
guard it and mark the scan INCOMPLETE instead of publishing a partial result as complete.

  list      read rollout/repositories.yaml; write expected.json (every repository that should
            be scanned) and list.txt ("organization name branch" per valid entry)
  block     append one {repository, reason} entry to blocked.json
  enrich    add repository and commit to one watchdog.py JSON report; print its finding total
  finalize  add every expected repository with neither a report nor a blocked entry to
            blocked.json as "no report produced"; print "<scanned> <expected>"
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

NAME = re.compile(r"^[A-Za-z0-9._-]+$")
BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


def cmd_list(args):
    data = yaml.safe_load(Path(args.repositories).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("repositories"), list) or not data.get("organization"):
        raise ValueError("repositories.yaml needs an organization and a repositories list")
    entries = data["repositories"]
    expected = []
    lines = []
    for number, entry in enumerate(entries, 1):
        name = entry.get("name") if isinstance(entry, dict) else None
        expected.append(str(name) if name else f"<entry {number}>")
        branch = entry.get("default_branch") if isinstance(entry, dict) else None
        if name and branch and NAME.match(str(name)) and BRANCH.match(str(branch)):
            lines.append(f"{data['organization']} {name} {branch}")
    # expected.json is written first and always reflects every entry, valid or not, so the
    # issue sync can report entries that never reached list.txt as BLOCKED.
    Path(args.expected).write_text(json.dumps(expected), encoding="utf-8")
    Path(args.list).write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return 0


def read_blocked(path):
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} is not a list")
    return data


def cmd_block(args):
    data = read_blocked(args.blocked)
    data.append({"repository": args.repository, "reason": args.reason})
    Path(args.blocked).write_text(json.dumps(data), encoding="utf-8")
    return 0


def cmd_enrich(args):
    path = Path(args.report)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("results"), dict):
        raise ValueError("report has no results")
    total = sum(len(v or []) for v in data["results"].values())
    data["repository"] = args.repository
    data["commit"] = args.commit
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(total)
    return 0


def cmd_finalize(args):
    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    if not isinstance(expected, list) or not expected:
        raise ValueError("expected.json is empty or not a list")
    blocked = read_blocked(args.blocked)
    blocked_names = {b.get("repository") for b in blocked if isinstance(b, dict)}
    reported = {p.stem for p in Path(args.reports).glob("*.json")}
    for name in expected:
        if name not in reported and name not in blocked_names:
            blocked.append({"repository": name, "reason": "no report produced"})
            blocked_names.add(name)
    Path(args.blocked).write_text(json.dumps(blocked), encoding="utf-8")
    scanned = sum(1 for name in expected if name in reported and name not in blocked_names)
    print(f"{scanned} {len(expected)}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list")
    p.add_argument("--repositories", required=True)
    p.add_argument("--list", required=True)
    p.add_argument("--expected", required=True)
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("block")
    p.add_argument("--blocked", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_block)
    p = sub.add_parser("enrich")
    p.add_argument("--report", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--commit", required=True)
    p.set_defaults(func=cmd_enrich)
    p = sub.add_parser("finalize")
    p.add_argument("--expected", required=True)
    p.add_argument("--reports", required=True)
    p.add_argument("--blocked", required=True)
    p.set_defaults(func=cmd_finalize)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        print(f"watchdog_scan_support {args.command}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
