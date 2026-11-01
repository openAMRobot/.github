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
import zlib
from pathlib import Path

ALLOWED = ["pr.md", "plan.md", "result.json", "needs-human.md", "followups.csv", "review.md", "verdict.json",
           "triage.json", "findings.csv", "report.md", "retro.md", "retro.patch", "change.bundle",
           "verify-base.json", "verify-head.json", "agent-outcome.json", "consumers-*.json", "contracts.json",
           "impact.md", "perf.json", "maintainability.json"]
MAX_BYTES = 5 * 1024 * 1024
SECRET = re.compile(rb"(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|"
                    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.)")


def bundle_payload(data):
    """Bytes of every object in a git bundle's pack, decompressed. Pack data is zlib
    compressed, so a secret committed by the agent is invisible to a scan of the raw file.
    Delta objects are scanned as their delta data, which carries every inserted byte
    literally. Raises ValueError on anything that is not a well-formed bundle."""
    end = data.find(b"\n\n")
    if not data.startswith(b"# v2 git bundle") and not data.startswith(b"# v3 git bundle") or end < 0:
        raise ValueError("not a git bundle")
    header, pack = data[:end], data[end + 2:]
    if pack[:4] != b"PACK":
        raise ValueError("bundle has no pack")
    count, pos, out = int.from_bytes(pack[8:12], "big"), 12, [header]
    for _ in range(count):
        byte = pack[pos]; kind = (byte >> 4) & 7; pos += 1
        while byte & 0x80:
            byte = pack[pos]; pos += 1
        if kind == 6:                      # OFS_DELTA: variable-length base offset
            byte = pack[pos]; pos += 1
            while byte & 0x80:
                byte = pack[pos]; pos += 1
        elif kind == 7:                    # REF_DELTA: 20-byte base object id
            pos += 20
        inflater = zlib.decompressobj()
        out.append(inflater.decompress(pack[pos:]))
        if not inflater.eof:
            raise ValueError("truncated object in bundle")
        pos = len(pack) - len(inflater.unused_data)
    return b"\n".join(out)


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
        scanned = data
        if name.endswith(".bundle"):
            try:
                scanned = data + bundle_payload(data)
            except (ValueError, IndexError, zlib.error) as exc:
                report["dropped"].append({"file": name, "reason": f"bundle could not be scanned: {exc}"})
                continue
        if any(s and s in scanned for s in secrets) or SECRET.search(scanned):
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
