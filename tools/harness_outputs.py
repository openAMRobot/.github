#!/usr/bin/env python3
"""Copy a mission's outputs to the upload folder: allowlisted names only, secrets scrubbed.

Artifacts of a public repository can be downloaded by any signed-in GitHub user, and the
agent's processes ran next to the Claude credential. So only files with the names the
missions define are copied, and a file is dropped (not uploaded) when it contains the
exact value of a secret passed in HARNESS_SECRET_VALUES (newline separated) or a
secret-like string. outputs.json in the destination lists what was copied and dropped.

  harness_outputs.py --src .harness-out --dst DIR
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
from pathlib import Path

ALLOWED = ["pr.md", "plan.md", "result.json", "needs-human.md", "followups.csv", "review.md", "verdict.json",
           "triage.json", "findings.csv", "report.md", "retro.md", "retro.patch", "change.bundle",
           "verify-base.json", "verify-head.json", "agent-outcome.json", "consumers-*.json", "contracts.json",
           "impact.md", "perf.json", "maintainability.json"]
MAX_BYTES = 5 * 1024 * 1024
SECRET = re.compile(rb"(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|"
                    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.)")


def copy(src, dst, secrets):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    report = {"copied": [], "dropped": []}
    if not src.is_dir():
        return report
    for path in sorted(src.iterdir()):
        name = path.name
        if path.is_symlink() or not path.is_file():
            report["dropped"].append({"file": name, "reason": "not a regular file"})
            continue
        if not any(fnmatch.fnmatch(name, pattern) for pattern in ALLOWED):
            report["dropped"].append({"file": name, "reason": "name not on the output allowlist"})
            continue
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            report["dropped"].append({"file": name, "reason": "larger than 5 MB"})
            continue
        if any(s and s in data for s in secrets) or SECRET.search(data):
            report["dropped"].append({"file": name, "reason": "contains a secret value or a secret-like string"})
            continue
        shutil.copyfile(path, dst / name)
        report["copied"].append(name)
    (dst / "outputs.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    args = parser.parse_args(argv)
    secrets = [s.strip().encode() for s in os.environ.get("HARNESS_SECRET_VALUES", "").splitlines() if len(s.strip()) >= 8]
    report = copy(args.src, args.dst, secrets)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
