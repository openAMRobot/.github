#!/usr/bin/env python3
"""Decisions impact of a pull request: the author's declaration and what the diff touches.

Every PR answers one question in its "Decisions impact" section: does it state, use
or change a value, limit, exclusion or distinction held in decisions.yaml?

  - [x] None: ...
  - [x] Consumer: ... <IDs>
  - [x] Change: ... change request #<n> (decision entry: <ID or new>)

This module parses that answer and compares it with the diff. For every recorded
register entry that applies to a changed file (applies_to repositories and files,
as tools/check_decisions.py matches them), it extracts the entry's value
fingerprints (decimal values with two or more decimals, part and model numbers)
and reports added or removed lines that contain them. A hit is a question for the
author, never an automatic verdict: the section must then say Consumer or Change.

Used by tools/check_pr_evidence.py (--decisions with --files-json) and by the
harness review mission. Standard library plus PyYAML; no network.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_decisions as cd  # noqa: E402

SECTION = "decisions impact"
CHOICES = ("none", "consumer", "change")
CHECKED = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*(?P<choice>None|Consumer|Change)\b(?P<rest>.*)$", re.M)
# Register IDs are upper case, with or without hyphens (COMPUTE, NAV-LIDAR).
ID = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:-[A-Z0-9]+)*\b")
NOT_IDS = {"NEW", "IDS", "PR", "CR", "ID", "AND", "THE", "TBD"}
ISSUE = re.compile(r"(?:#\d+|github\.com/[\w.-]+/[\w.-]+/issues/\d+)")
DECIMAL = re.compile(r"(?<![\w.])-?\d+\.\d{2,}(?![\w.])")
PART = re.compile(r"\b(?=[A-Za-z0-9-]*\d)(?=[A-Za-z0-9-]*[A-Za-z])[A-Za-z][A-Za-z0-9-]{3,}\b|\b\d+[A-Za-z][A-Za-z0-9]{2,}\b")
# Tokens that name documents, revisions or generic ROS words, not values.
NOT_PARTS = re.compile(r"^(?:rev[\d.]+|[A-Z]-\d+(?:-rev[\d.]+)?|UTF-8|ISO\d+|REP\d+|v\d+|ros\d|joint\d+|link\d+|base\d*)$", re.I)
MAX_HITS = 10


def parse(section_text):
    """Return (choice or None, ids, issue_refs, errors) for the section body."""
    if section_text is None:
        return None, [], [], ["missing"]
    checked = list(CHECKED.finditer(re.sub(r"<!--.*?-->", "", section_text, flags=re.S)))
    if len(checked) != 1:
        return None, [], [], [f"tick exactly one of None, Consumer or Change ({len(checked)} ticked)"]
    match = checked[0]
    choice, rest = match.group("choice").lower(), match.group("rest")
    ids = sorted(set(ID.findall(rest)) - NOT_IDS)
    issues = ISSUE.findall(rest)
    return choice, ids, issues, []


def stringify(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def fingerprints(entry):
    """Value tokens of one register entry, from value, values and summary."""
    text = " ".join(stringify(entry.get(key, "")) for key in ("value", "values", "summary"))
    tokens = set(DECIMAL.findall(text))
    tokens |= {t for t in PART.findall(text) if not NOT_PARTS.match(t)}
    return tokens


def changed_lines(patch):
    for line in (patch or "").splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line[:1] in "+-":
            yield line[0], line[1:]


def touched(decisions, files, repository):
    """{entry id: [hit text]} for register values found in added or removed lines."""
    active = [d for d in decisions if d.get("status") == "recorded" and cd.repository_matches(d, repository)]
    prints = {d["id"]: fingerprints(d) for d in active}
    hits = {}
    for item in files:
        name = item.get("filename", "")
        relevant = [d for d in active if cd.glob_match(name, d["applies_to"].get("files") or cd.DEFAULT_FILES)
                    and not cd.glob_match(name, d.get("_exclude", []))]
        for sign, text in changed_lines(item.get("patch")):
            for d in relevant:
                found = sorted(t for t in prints[d["id"]] if re.search(rf"(?<![\w.]){re.escape(t)}(?![\w.])", text))
                if found:
                    action = "adds" if sign == "+" else "removes"
                    hits.setdefault(d["id"], []).append(f"{name}: {action} a line with {', '.join(found[:3])}")
    return hits


def evaluate(section_text, decisions, files, repository, require=False):
    """Return (failures, warnings, notes) for the evidence summary."""
    failures, warnings, notes = [], [], []
    choice, ids, issues, errors = parse(section_text)
    known = {d["id"] for d in decisions}
    if errors == ["missing"]:
        text = ("Missing section: Decisions impact (tick None, Consumer with the entry IDs, or Change with "
                "the change request issue; template: openAMRobot/.github .github/PULL_REQUEST_TEMPLATE.md)")
        (failures if require else warnings).append(text)
    elif errors:
        failures.append(f"Decisions impact: {errors[0]}")
    unknown = [i for i in ids if i not in known]
    if choice in ("consumer", "change") and unknown:
        failures.append(f"Decisions impact: unknown register IDs {', '.join(unknown)}; use IDs from decisions.yaml")
    if choice == "consumer" and not ids:
        failures.append("Decisions impact: Consumer needs the register entry IDs this PR uses")
    if choice == "change" and not issues:
        failures.append("Decisions impact: Change needs the contract change request issue (#<n>); the register "
                        "PR follows the owner's approval (harness/README.md \"Decisions\")")
    if choice == "change":
        notes.append(f"Register change requested: {', '.join(ids) or 'new entry'} via {', '.join(issues)}. "
                     "The register PR is drafted after the platform lead labels the request decision-approved.")
    hits = touched(decisions, files, repository) if files else {}
    declared = set(ids)
    for entry, lines in sorted(hits.items()):
        sample = "; ".join(lines[:3]) + (f"; and {len(lines) - 3} more" if len(lines) > 3 else "")
        if choice == "none" or (choice in ("consumer", "change") and entry not in declared) or choice is None:
            warnings.append(f"Decisions impact question: the diff touches values of {entry} ({sample}). "
                            f"Is this PR a consumer of {entry} or does it change it? Update the Decisions "
                            "impact section to say so.")
        else:
            notes.append(f"Decisions impact: {entry} values touched as declared ({sample})")
        if len(warnings) >= MAX_HITS:
            break
    return failures, warnings, notes


def load(path):
    return cd.load_decisions(path)
