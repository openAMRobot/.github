#!/usr/bin/env python3
"""Validate repository-level agent-rules adoption metadata and requirements."""

import argparse
import re
import sys
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import watchdog_report as wr  # noqa: E402

NAME = re.compile(r"^[A-Za-z0-9._-]+$")
BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
VALID_STATUSES = {"required", "exempt"}

LABEL = "Agent rules missing"
GROUP = "agent-rules"
WHY = ("The organization scan must distinguish a repository that has not adopted the shared "
       "rules from one that was explicitly exempted.")
NEXT_STEP = ("Add AGENTS.md with the canonical shared block and a repository-specific section, "
             "or record an owner-approved agent_rules: exempt entry with a non-empty reason.")


class RepositoryNotListed(LookupError):
    """The requested repository is not present in the active repository manifest."""


def validate_document(data):
    """Validate and return repository entries from rollout/repositories.yaml."""
    if not isinstance(data, dict) or not data.get("organization"):
        raise ValueError("repositories.yaml needs an organization")
    entries = data.get("repositories")
    if not isinstance(entries, list) or not entries:
        raise ValueError("repositories.yaml needs a non-empty repositories list")

    seen = set()
    allowed_keys = {"name", "default_branch", "agent_rules", "agent_rules_reason"}
    for number, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ValueError(f"repository entry {number} is not a mapping")
        unknown = set(entry) - allowed_keys
        if unknown:
            raise ValueError(f"repository entry {number} has unknown field(s): {', '.join(sorted(unknown))}")
        name = entry.get("name")
        branch = entry.get("default_branch")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise ValueError(f"repository entry {number} has an invalid name")
        if name in seen:
            raise ValueError(f"duplicate repository: {name}")
        seen.add(name)
        if not isinstance(branch, str) or not BRANCH.fullmatch(branch):
            raise ValueError(f"{name}: invalid default_branch")

        status = entry.get("agent_rules")
        if status not in VALID_STATUSES:
            raise ValueError(f"{name}: agent_rules must be required or exempt")
        reason = entry.get("agent_rules_reason")
        if status == "exempt":
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"{name}: agent_rules_reason is required for exempt repositories")
        elif reason is not None:
            raise ValueError(f"{name}: agent_rules_reason is only valid with agent_rules: exempt")
    return entries


def load_document(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read repository policy: {exc}") from exc
    return validate_document(data)


def entry_for(path, repository):
    for entry in load_document(path):
        if entry["name"] == repository:
            return dict(entry)
    raise RepositoryNotListed(f"{repository}: not listed in repositories.yaml")


def policy_status(root, policy):
    """Return JSON-safe policy state for the Watchdog report."""
    status = policy["agent_rules"]
    result = {"status": status}
    if status == "exempt":
        result["reason"] = policy["agent_rules_reason"].strip()
    else:
        result["present"] = Path(root, "AGENTS.md").is_file()
    return result


def missing_findings(root, policy):
    """Return a finding only when required AGENTS.md is absent."""
    if policy["agent_rules"] == "exempt" or Path(root, "AGENTS.md").is_file():
        return []
    return [wr.finding(
        LABEL,
        GROUP,
        "AGENTS.md",
        1,
        "file is missing",
        "AGENTS.md is required for this repository.",
        WHY,
        "Add AGENTS.md using the canonical shared block, then keep repository-specific rules below it.",
        [("WATCHDOG.md", f"{wr.DOCS}#shared-agent-rules")],
    )]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repositories", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        policy = entry_for(args.repositories, args.repository)
        findings = missing_findings(args.root, policy)
    except (OSError, ValueError, RepositoryNotListed) as exc:
        print(f"INVALID configuration: {exc}", file=sys.stderr)
        return 2
    if findings:
        for line in wr.render(findings, "Agent rules adoption", NEXT_STEP, decision_word="Rule"):
            print(line)
        wr.emit_github(findings, "Agent rules adoption", NEXT_STEP)
        return 1
    print(f"PASS {args.repository}: agent_rules={policy['agent_rules']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
