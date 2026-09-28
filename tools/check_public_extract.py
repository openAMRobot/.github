#!/usr/bin/env python3
"""Fail when public material contains internal links, personal contact data,
prices or credential-like strings.

Scope: files under docs/ or assets/, every README.md, and every path that
contains "public". Rules: google-drive-link, email, phone, price, credential.
An allowlist file (YAML) can exempt a match; every entry needs a rule, a
regular expression for the matched text, optional path globs and a reason.
Exit status: 0 clean, 1 findings, 2 usage or configuration error.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

RULES = {
    "google-drive-link": re.compile(r"https?://(?:drive|docs)\.google\.com/[^\s\"'<>)\]]*[^\s\"'<>)\].,;:]", re.I),
    "email": re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[a-z]{2,24}(?![\w-]|\.[A-Za-z])"),
    "phone": re.compile(
        r"(?:tel:\s*\+?[\d\s().-]{7,}\d)|(?<![\w+])\+\d{1,3}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}(?![\w.])"
    ),
    "price": re.compile(
        r"(?:[€$£¥]\s?\d[\d,.]*(?:\s?(?:k|m|/mo))?)"
        r"|(?:\b(?:USD|EUR|GBP|CHF|INR)\s?\d[\d,.]*)"
        r"|(?:\b\d[\d,.]*\s?(?:€|USD|EUR|GBP|CHF|INR)\b)"
    ),
    "credential": re.compile(
        r"(?:AKIA[0-9A-Z]{16})"
        r"|(?:gh[pousr]_[A-Za-z0-9]{36,})|(?:github_pat_[A-Za-z0-9_]{20,})"
        r"|(?:sk-ant-[A-Za-z0-9_-]{20,})|(?:sk-[A-Za-z0-9]{32,})"
        r"|(?:xox[abprs]-[A-Za-z0-9-]{10,})|(?:AIza[0-9A-Za-z_-]{35})"
        r"|(?:-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)"
        r"|(?:(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*[\"'][^\"'\s]{8,}[\"'])",
        re.I,
    ),
}
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".html", ".htm", ".svg", ".json", ".yaml", ".yml",
    ".csv", ".xml", ".js", ".css", ".rst", ".toml", ".ini", ".cfg", "",
}
SKIP_DIRS = {".git", "node_modules", ".verification"}


def in_scope(rel):
    parts = rel.split("/")
    return (
        parts[0] in ("docs", "assets")
        or parts[-1] == "README.md"
        or "public" in rel.lower()
    )


def load_allowlist(path):
    if not path:
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    entries = data.get("allow") or []
    out = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or e.get("rule") not in RULES or not e.get("match") or not e.get("reason"):
            raise ValueError(f"allow[{i}] needs rule (one of {sorted(RULES)}), match and reason")
        out.append({
            "rule": e["rule"], "match": re.compile(e["match"], re.I),
            "paths": e.get("paths") or ["*"], "repositories": e.get("repositories") or ["*"],
        })
    return out


def allowed(entries, rule, text, rel, repository):
    for e in entries:
        if e["rule"] != rule or not e["match"].fullmatch(text):
            continue
        if not any(fnmatch.fnmatch(rel, p) for p in e["paths"]):
            continue
        if repository and not any(fnmatch.fnmatch(repository, r) for r in e["repositories"]):
            continue
        return True
    return False


def list_files(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], check=True,
                             capture_output=True).stdout.decode("utf-8", "replace")
        files = [f for f in out.split("\0") if f]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*")
                  if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(root).parts))


def scan(root, allow, repository=None, only=None):
    root = Path(root)
    findings = []
    for rel in (only if only is not None else list_files(root)):
        path = root / rel
        if not in_scope(rel) or not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            for rule, rx in RULES.items():
                for m in rx.finditer(line):
                    text = m.group(0).strip()
                    if not allowed(allow, rule, text, rel, repository):
                        findings.append({"file": rel, "line": number, "rule": rule, "found": text[:120]})
    return findings


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--allowlist", type=Path, help="YAML allowlist")
    p.add_argument("--repository", help="repository name for repository-scoped allowlist entries")
    p.add_argument("--changed-files", type=Path, help="scan only the paths listed in this file")
    p.add_argument("--json", type=Path)
    a = p.parse_args(argv)
    try:
        allow = load_allowlist(a.allowlist)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"INVALID allowlist: {exc}", file=sys.stderr)
        return 2
    if not a.root.is_dir():
        print(f"root is not a directory: {a.root}", file=sys.stderr)
        return 2
    only = None
    if a.changed_files:
        only = [l.strip() for l in a.changed_files.read_text(encoding="utf-8").splitlines() if l.strip()]
    findings = scan(a.root, allow, a.repository, only)
    for f in findings:
        print(f"PUBLIC-EXTRACT {f['file']}:{f['line']}: {f['rule']}: {f['found']}")
    if a.json:
        a.json.write_text(json.dumps({"findings": findings}, indent=2), encoding="utf-8")
    print(f"result: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
