"""Shared, contributor-friendly output for the OpenAMRobot Watchdog checks.

Every check reports findings in the same compact shape, one block per decision (or rule):

    <Label>: <group> (<n> finding(s))
      Decision: <the current decision or rule, one line>
      Why:      <why it matters, one line; one line per distinct reason>
      Fix:      <how to fix, one line>
      More:     <links to WATCHDOG.md and the register entry>
      Found:
        <file>:<line>: found '<text>'
        ...

Decision, Why, Fix and More are printed once per group; each finding is one line with its
place and what was found. A closing summary gives the total, the count per group and the
next step. Inside GitHub Actions the same findings are also written as workflow annotations
(inline in pull request diffs, full detail per finding) and as a Markdown job summary; the
checkers' JSON output keeps full detail per finding too. Formatting never changes what a
check detects or its exit status.
"""
import os
from collections import OrderedDict

DOCS = "https://github.com/openAMRobot/.github/blob/main/WATCHDOG.md"
REGISTER = "https://github.com/openAMRobot/.github/blob/main/decisions.yaml"


def finding(label, group, file, line, found, decision, why, fix, links=()):
    """Build one finding record (a plain dict, JSON-serialisable)."""
    return {"label": label, "group": group, "file": file, "line": int(line or 1), "found": str(found),
            "decision": decision, "why": why, "fix": fix, "links": list(links)}


def header(f):
    """One self-contained line for a finding (used where findings stand alone)."""
    return f"{f['label']}: {f['file']}:{f['line']}: {f['group']} found {f['found']!r}"


def group_header(items):
    first = items[0]
    return f"{first['label']}: {first['group']} ({len(items)} finding(s))"


def finding_line(f):
    return f"    {f['file']}:{f['line']}: found {f['found']!r}"


def grouped(findings):
    groups = OrderedDict()
    for f in findings:
        groups.setdefault(f["group"], []).append(f)
    return groups


def render(findings, title, next_step, decision_word="Decision"):
    """Return the human-readable report as a list of lines."""
    lines = []
    groups = grouped(findings)
    for items in groups.values():
        first = items[0]
        lines.append(group_header(items))
        lines.append(f"  {decision_word + ':':<9} {first['decision']}")
        whys = list(dict.fromkeys(f["why"] for f in items))
        lines.append(f"  Why:      {whys[0]}")
        lines.extend(f"            {why}" for why in whys[1:])
        lines.append(f"  Fix:      {first['fix']}")
        if first["links"]:
            lines.append("  More:     " + " | ".join(f"{name}: {url}" for name, url in first["links"]))
        lines.append("  Found:")
        lines.extend(finding_line(f) for f in items)
        lines.append("")
    lines.append(f"{title} summary: {len(findings)} finding(s)"
                 + ("" if not groups else " (" + ", ".join(f"{g} {len(i)}" for g, i in groups.items()) + ")"))
    lines.append(f"Next step: {next_step if findings else 'nothing to fix.'}")
    return lines


def _escape_data(text):
    return str(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text):
    return _escape_data(text).replace(":", "%3A").replace(",", "%2C")


def annotations(findings, level="warning"):
    """GitHub workflow commands, one per finding."""
    level = "error" if level == "error" else "warning"
    out = []
    for f in findings:
        title = _escape_property(f"{f['label']} ({f['group']})")
        message = _escape_data(f"Found {f['found']!r}. {f['decision']} Fix: {f['fix']} See {DOCS}")
        out.append(f"::{level} file={_escape_property(f['file'])},line={f['line']},title={title}::{message}")
    return out


def markdown(findings, title, next_step):
    """Markdown job summary: grouped table plus collapsible details."""
    groups = grouped(findings)
    md = [f"### {title}: {len(findings)} finding(s)", ""]
    if not findings:
        md += ["No findings. A clean result shows textual consistency only "
               f"([what the Watchdog checks]({DOCS})).", ""]
        return "\n".join(md) + "\n"
    md += ["| Group | Findings | Fix |", "|---|---:|---|"]
    for group, items in groups.items():
        md.append(f"| {group} | {len(items)} | {items[0]['fix'].replace('|', '/')} |")
    md += ["", f"Next step: {next_step} See [WATCHDOG.md]({DOCS}).", ""]
    for group, items in groups.items():
        md.append(f"<details><summary>{group}: {len(items)} finding(s)</summary>")
        md.append("")
        for f in items:
            md.append(f"- `{f['file']}:{f['line']}` found `{f['found']}`: {f['decision']} "
                      f"Fix: {f['fix']}")
        md += ["", "</details>", ""]
    return "\n".join(md) + "\n"


def emit_github(findings, title, next_step, environ=None):
    """Inside GitHub Actions, print annotations and append the job summary.

    WATCHDOG_ANNOTATION=error|warning picks the annotation level (default warning);
    WATCHDOG_ANNOTATIONS=0 switches GitHub output off (used by the organization scan).
    Returns the annotation lines printed.
    """
    env = os.environ if environ is None else environ
    if env.get("GITHUB_ACTIONS") != "true" or env.get("WATCHDOG_ANNOTATIONS") == "0":
        return []
    lines = annotations(findings, env.get("WATCHDOG_ANNOTATION", "warning"))
    for line in lines:
        print(line)
    path = env.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(markdown(findings, title, next_step))
    return lines
