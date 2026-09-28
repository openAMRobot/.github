#!/usr/bin/env python3
"""Check a repository checkout against the decisions register (decisions.yaml).

Every decision names the file globs it applies to and the patterns that
reveal a contradicting value; a superseded entry may also name a pattern for
text that still cites the superseded source. This tool validates the schema,
scans the checkout and reports file, line, found value and decided value.
It reads only the pinned register and the checkout: it fetches nothing and
never writes to either. A match proves a textual contradiction only, never
mechanical, electrical or safety correctness; each entry names the human
reviewer and evidence for that. Exit status: 0 clean, 1 contradiction found,
2 invalid register or usage error.

A line that must keep a superseded value (history, changelog, legacy
material) carries the marker `decision-allow: <ID> <reason>` on the same line
or the line directly above it. The marker is reported, never silently ignored.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

SCHEMA_VERSION = 1
STATUSES = {"recorded", "open"}
KINDS = {"value", "configuration", "limit", "exclusion", "distinction"}
REQUIRED = ("id", "title", "kind", "status", "date", "source", "applies_to", "check",
            "verification", "owner")
DEFAULT_FILES = [
    "**/*.md", "**/*.yaml", "**/*.yml", "**/*.launch.py", "**/*.launch.xml",
    "**/*.launch", "**/*.urdf", "**/*.xacro", "**/package.xml", "**/README*",
]
ALLOW = re.compile(r"decision-allow:\s*(?P<id>[A-Z0-9][A-Z0-9-]*)\s+(?P<reason>\S.*)")
SKIP_DIRS = {".git", "node_modules", ".verification", "build", "install", "log"}


class DecisionError(ValueError):
    pass


def load_decisions(path, maintainers=None):
    """Load and validate decisions.yaml; return the list of decisions."""
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DecisionError(f"{path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise DecisionError(f"{path}: schema_version must be {SCHEMA_VERSION}")
    sources = data.get("sources") or {}
    decisions = data.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise DecisionError(f"{path}: decisions must be a non-empty list")
    roles = None
    if maintainers:
        roles = set((yaml.safe_load(Path(maintainers).read_text(encoding="utf-8")) or {}).get("roles", {}))
    seen = set()
    errors = []
    for index, d in enumerate(decisions):
        where = f"decisions[{index}]"
        if not isinstance(d, dict):
            errors.append(f"{where}: not a mapping")
            continue
        missing = [key for key in REQUIRED if key not in d]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        where = d["id"]
        if d["id"] in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(d["id"])
        if d["status"] not in STATUSES:
            errors.append(f"{where}: status must be one of {sorted(STATUSES)}")
        if d["kind"] not in KINDS:
            errors.append(f"{where}: kind must be one of {sorted(KINDS)}")
        ver = d["verification"]
        human = ver.get("human") if isinstance(ver, dict) else None
        if not isinstance(ver, dict) or not ver.get("machine") or not isinstance(human, dict) \
                or not human.get("reviewer") or not human.get("evidence"):
            errors.append(f"{where}: verification needs machine and human (reviewer, evidence)")
        elif roles is not None and human["reviewer"] not in roles:
            errors.append(f"{where}: reviewer {human['reviewer']!r} is not a role in the maintainers map")
        if "value" not in d and "values" not in d:
            errors.append(f"{where}: needs value or values")
        src = d["source"]
        if not isinstance(src, dict) or not src.get("document") or not src.get("item"):
            errors.append(f"{where}: source needs document and item")
        elif src["document"] not in sources:
            errors.append(f"{where}: source document {src['document']!r} not listed under sources")
        if roles is not None and d["owner"] not in roles:
            errors.append(f"{where}: owner {d['owner']!r} is not a role in the maintainers map")
        for sup in d.get("supersedes") or []:
            if not isinstance(sup, dict) or "value" not in sup or not sup.get("source"):
                errors.append(f"{where}: each supersedes entry needs value and source")
            elif sup.get("citation"):
                try:
                    if "found" not in re.compile(sup["citation"], re.IGNORECASE).groupindex:
                        errors.append(f"{where}: citation needs a (?P<found>...) group")
                except re.error as exc:
                    errors.append(f"{where}: bad citation pattern: {exc}")
        applies = d["applies_to"]
        if not isinstance(applies, dict) or not applies.get("repositories") or not applies.get("files"):
            errors.append(f"{where}: applies_to needs repositories and files")
        checks = d["check"]
        if not isinstance(checks, list) or not checks:
            errors.append(f"{where}: check must be a non-empty list of patterns")
            continue
        for c in checks:
            try:
                rx = re.compile(c["pattern"], re.IGNORECASE)
                if "found" not in rx.groupindex:
                    errors.append(f"{where}: pattern needs a (?P<found>...) group")
                if c.get("unless"):
                    re.compile(c["unless"], re.IGNORECASE)
            except (KeyError, TypeError, re.error) as exc:
                errors.append(f"{where}: bad check pattern: {exc}")
    if errors:
        raise DecisionError("\n".join(errors))
    exclude = data.get("exclude") or []
    for d in decisions:
        d["_exclude"] = list(exclude) + list(d["applies_to"].get("exclude") or [])
        d["_checks"] = list(d["check"]) + [
            {"pattern": sup["citation"], "unless": sup.get("citation_unless"),
             "message": f"superseded source still cited ({sup['source']}); cite {d['source']['document']}"}
            for sup in d.get("supersedes") or [] if isinstance(sup, dict) and sup.get("citation")]
    return decisions


def decided_text(d):
    value = d["values"] if "values" in d else d["value"]
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    unit = d.get("unit")
    return f"{value} {unit}".strip() if unit and unit != "none" else str(value)


def repository_matches(d, repository):
    repos = d["applies_to"]["repositories"]
    return repository is None or any(fnmatch.fnmatch(repository, r) for r in repos)


def glob_match(rel, patterns):
    rel = rel.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(rel, pattern[3:]):
            return True
    return False


def list_files(root):
    root = Path(root)
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True
        ).stdout.decode("utf-8", "replace")
        files = [f for f in out.split("\0") if f]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    files = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not SKIP_DIRS.intersection(rel.parts):
            files.append(rel.as_posix())
    return sorted(files)


def scan(root, decisions, repository=None, only=None, stats=None):
    """Return (findings, allowed) for the checkout at root."""
    root = Path(root)
    files = list(only) if only is not None else list_files(root)
    findings, allowed = [], []
    unscanned = 0
    active = [d for d in decisions if d["status"] == "recorded" and repository_matches(d, repository)]
    for rel in files:
        path = root / rel
        if not path.is_file():
            continue
        relevant = [d for d in active if glob_match(rel, d["applies_to"].get("files") or DEFAULT_FILES)
                    and not glob_match(rel, d["_exclude"])]
        if not relevant:
            unscanned += 1
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            for d in relevant:
                hit = False
                for c in d["_checks"]:
                    if hit:
                        break
                    if c.get("files") and not glob_match(rel, c["files"]):
                        continue
                    for m in re.finditer(c["pattern"], line, re.IGNORECASE):
                        if c.get("unless") and re.search(c["unless"], line, re.IGNORECASE):
                            continue
                        record = {
                            "id": d["id"], "file": rel, "line": number,
                            "found": m.group("found").strip(), "decided": decided_text(d),
                            "source": f"{d['source']['document']} {d['source']['item']}",
                            "message": c.get("message", ""),
                        }
                        hit = True
                        marker = allow_marker(lines, number, d["id"])
                        if marker:
                            record["reason"] = marker
                            allowed.append(record)
                        else:
                            findings.append(record)
                        break
    if stats is not None:
        stats["unscanned"] = unscanned
    return findings, allowed


def allow_marker(lines, number, decision_id):
    for candidate in (lines[number - 1], lines[number - 2] if number > 1 else ""):
        m = ALLOW.search(candidate)
        if m and m.group("id") == decision_id:
            return m.group("reason").strip()
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--decisions", type=Path, required=True)
    p.add_argument("--maintainers", type=Path, help="maintainers.yaml; validates owner roles")
    p.add_argument("--root", type=Path, default=Path("."), help="checkout to scan")
    p.add_argument("--repository", help="repository name used for applies_to.repositories")
    p.add_argument("--changed-files", type=Path, help="scan only the paths listed in this file")
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--json", type=Path, help="write findings as JSON")
    a = p.parse_args(argv)
    try:
        decisions = load_decisions(a.decisions, a.maintainers)
    except DecisionError as exc:
        print(f"INVALID decisions file:\n{exc}", file=sys.stderr)
        return 2
    print(f"decisions: {len(decisions)} loaded, "
          f"{sum(d['status'] == 'recorded' for d in decisions)} recorded and scanned, "
          f"{sum(d['status'] == 'open' for d in decisions)} open")
    if a.validate_only:
        return 0
    if not a.root.is_dir():
        print(f"root is not a directory: {a.root}", file=sys.stderr)
        return 2
    only = None
    if a.changed_files:
        only = [line.strip() for line in a.changed_files.read_text(encoding="utf-8").splitlines() if line.strip()]
    stats = {}
    findings, allowed = scan(a.root, decisions, a.repository, only, stats)
    for f in allowed:
        print(f"ALLOWED {f['file']}:{f['line']}: {f['id']} found {f['found']!r}; reason: {f['reason']}")
    for f in findings:
        print(f"CONTRADICTION {f['file']}:{f['line']}: {f['id']} found {f['found']!r}, "
              f"decided {f['decided']!r} ({f['source']}) {f['message']}".rstrip())
    if a.json:
        a.json.write_text(json.dumps({"findings": findings, "allowed": allowed}, indent=2), encoding="utf-8")
    scope = f"{len(only)} changed file(s)" if only is not None else "full checkout"
    print(f"result: {len(findings)} contradiction(s), {len(allowed)} allowed, scope {scope}; "
          f"{stats['unscanned']} file(s) not scanned (no decision covers their type or path)")
    print("note: a clean result shows textual consistency only, not mechanical, electrical or safety correctness")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
