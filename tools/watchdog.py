#!/usr/bin/env python3
"""OpenAMRobot Watchdog: run every repository check against one checkout.

    python3 tools/watchdog.py --root ../openamrobot-docs

Runs, in one go and with the register and allowlist of this harness checkout:
decisions of record, public extract, shared agent rules (when AGENTS.md exists),
workflow policy and decision freshness. Prints each check's findings in the
shared Watchdog format (what was found, the decision, why, how to fix, links),
then one summary table. See WATCHDOG.md.

It only reads files. It proves textual consistency only, never mechanical,
electrical, safety or release correctness.

Exit status: 0 clean, 1 findings, 2 invalid register, allowlist or usage error.
With --report-only, findings never change the exit status (0); usage errors still exit 2.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import check_agent_rules as car  # noqa: E402
import check_decisions as cd  # noqa: E402
import check_public_extract as pe  # noqa: E402
import check_workflow_policy as wp  # noqa: E402
import watchdog_report as wr  # noqa: E402

HARNESS = TOOLS.parent
CHECKS = ("decisions", "public-extract", "shared-rules", "workflow-policy")
TITLES = {"decisions": "Decisions of record", "public-extract": "Public extract",
          "shared-rules": "Shared agent rules", "workflow-policy": "Workflow policy"}
NEXT_STEPS = {"decisions": cd.NEXT_STEP, "public-extract": pe.NEXT_STEP,
              "shared-rules": car.NEXT_STEP, "workflow-policy": wp.NEXT_STEP}


def shared_rules(root, canonical):
    """Findings for AGENTS.md drift; None when the repository has no AGENTS.md."""
    path = Path(root, "AGENTS.md")
    if not path.is_file():
        return None
    version, expected = car.block(canonical)
    try:
        text = path.read_text(encoding="utf-8")
        if car.block(path, version)[1] != expected:
            raise ValueError("shared block differs from canonical")
        if len(text.splitlines()) >= car.MAX_LINES:
            raise ValueError(f"AGENTS.md must be under {car.MAX_LINES} lines")
        if (path.parent / "CLAUDE.md").read_text(encoding="utf-8").strip() != "@AGENTS.md":
            raise ValueError("CLAUDE.md must import @AGENTS.md without duplicate rules")
    except (OSError, ValueError) as exc:
        return [wr.finding(car.LABEL, "shared-rules", "AGENTS.md", 1, str(exc),
                           f"AGENTS.md carries the canonical shared block {version} from openAMRobot/.github.",
                           car.WHY, car.fix_for(str(exc)), [("WATCHDOG.md", f"{wr.DOCS}#shared-agent-rules")])]
    return []


def freshness(register_path, today=None):
    """Decision freshness: entries whose review_by date has passed (never blocking)."""
    data = yaml.safe_load(Path(register_path).read_text(encoding="utf-8")) or {}
    return cd.review_warnings(data, today)


def run(root, repository, harness=HARNESS, today=None):
    """Run every check; return a result dict. Raises ValueError on configuration errors."""
    root = Path(root)
    register = Path(harness, "decisions.yaml")
    try:
        decisions = cd.load_decisions(register, Path(harness, "maintainers.yaml"))
    except cd.DecisionError as exc:
        raise ValueError(f"invalid decisions register: {exc}") from exc
    try:
        allow = pe.load_allowlist(Path(harness, "public-extract-allowlist.yaml"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid public extract allowlist: {exc}") from exc
    stats = {}
    found, allowed = cd.scan(root, decisions, repository, None, stats)
    results = {
        "decisions": cd.to_watchdog(found, decisions),
        "public-extract": pe.to_watchdog(pe.scan(root, allow, repository)),
        "shared-rules": shared_rules(root, Path(harness, "agent-rules", "SHARED_RULES.md")),
        "workflow-policy": wp.to_watchdog(wp.records(root)),
    }
    return {"repository": repository, "results": results, "allowed": allowed,
            "freshness": freshness(register, today), "unscanned": stats.get("unscanned", 0)}


def total(report):
    return sum(len(v) for v in report["results"].values() if v)


def per_decision(report):
    """Counts per group (decision ID or rule), across all checks, in first-seen order."""
    counts = {}
    for items in report["results"].values():
        for f in items or []:
            counts[f["group"]] = counts.get(f["group"], 0) + 1
    return counts


def render(report):
    lines = [f"OpenAMRobot Watchdog: {report['repository']}", ""]
    for check in CHECKS:
        items = report["results"][check]
        lines.append(f"## {TITLES[check]}")
        if items is None:
            lines += ["Not run: the repository has no AGENTS.md.", ""]
            continue
        if check == "decisions":
            for a in report["allowed"]:
                lines.append(f"Allowed by decision-allow marker: {a['file']}:{a['line']}: {a['id']} "
                             f"found {a['found']!r}; reason: {a['reason']}")
        lines += wr.render(items, TITLES[check], NEXT_STEPS[check],
                           decision_word="Decision" if check == "decisions" else "Rule")
        lines.append("")
    lines.append("## Decision freshness")
    lines += [f"Review due: {w}. The decision owner confirms or updates the entry." for w in report["freshness"]] \
        or ["Every decision is within its review_by date."]
    lines.append("")
    lines.append("== Watchdog summary ==")
    lines.append(f"{'Check':<22}Findings")
    for check in CHECKS:
        items = report["results"][check]
        lines.append(f"{TITLES[check]:<22}{'not run (no AGENTS.md)' if items is None else len(items)}")
    lines.append(f"{'Decision freshness':<22}{len(report['freshness'])} review(s) due (warning only)")
    counts = per_decision(report)
    lines.append(f"Total: {total(report)} finding(s)"
                 + (" (" + ", ".join(f"{g} {n}" for g, n in counts.items()) + ")" if counts else ""))
    lines.append("Next step: " + ("fix each finding as its Fix line says, or see WATCHDOG.md "
                                  "for historical labels and how to propose a decision change."
                                  if counts else "nothing to fix."))
    lines.append(f"Guide: {wr.DOCS}")
    lines.append("note: a clean result shows textual consistency only, not mechanical, electrical, "
                 "safety or release correctness")
    return lines


def markdown_row(report):
    """One Markdown section for the organization scan summary."""
    md = [f"### {report['repository']}: {total(report)} finding(s)", ""]
    md += ["| Check | Findings |", "|---|---:|"]
    for check in CHECKS:
        items = report["results"][check]
        md.append(f"| {TITLES[check]} | {'not run (no AGENTS.md)' if items is None else len(items)} |")
    counts = per_decision(report)
    if counts:
        md += ["", "| Decision or rule | Findings |", "|---|---:|"]
        md += [f"| {g} | {n} |" for g, n in counts.items()]
    md.append("")
    return "\n".join(md) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", type=Path, default=Path("."), help="repository checkout to check")
    p.add_argument("--repository", help="repository name (default: the root directory name)")
    p.add_argument("--harness", type=Path, default=HARNESS,
                   help="openAMRobot/.github checkout with decisions.yaml (default: this one)")
    p.add_argument("--report-only", action="store_true", help="never fail on findings")
    p.add_argument("--json", type=Path, help="write the full result as JSON")
    p.add_argument("--markdown", type=Path, help="append a per-repository Markdown summary to this file")
    a = p.parse_args(argv)
    if not a.root.is_dir():
        print(f"root is not a directory: {a.root}", file=sys.stderr)
        return 2
    repository = a.repository or a.root.resolve().name
    try:
        report = run(a.root, repository, a.harness)
    except (OSError, ValueError) as exc:
        print(f"INVALID configuration: {exc}", file=sys.stderr)
        return 2
    for line in render(report):
        print(line)
    for check in CHECKS:
        if report["results"][check]:
            wr.emit_github(report["results"][check], f"{TITLES[check]} ({repository})", NEXT_STEPS[check])
    if a.json:
        a.json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if a.markdown:
        with a.markdown.open("a", encoding="utf-8") as handle:
            handle.write(markdown_row(report))
    if a.report_only:
        return 0
    return 1 if total(report) else 0


if __name__ == "__main__":
    sys.exit(main())
