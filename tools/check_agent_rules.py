#!/usr/bin/env python3
"""Offline shared-rule drift check; caller supplies canonical file and checkouts.

The marker version (v1, v2, ...) is read from the canonical file, so a
repository that still carries an older block fails with a version message.
"""
import argparse
import re
from pathlib import Path
import sys

MARKER = re.compile(r'<!-- (BEGIN|END) OPENAMROBOT SHARED RULES (v\d+) -->')
MAX_LINES = 120


def block(path, version=None):
    s = path.read_text(encoding='utf-8')
    found = MARKER.findall(s)
    versions = {v for _, v in found}
    if version and versions and version not in versions:
        raise ValueError(f'shared block is {"/".join(sorted(versions))}, canonical is {version}')
    if [k for k, _ in found] != ['BEGIN', 'END'] or len(versions) != 1:
        raise ValueError('expected exactly one begin/end marker pair of one version')
    v = versions.pop()
    begin = f'<!-- BEGIN OPENAMROBOT SHARED RULES {v} -->'
    end = f'<!-- END OPENAMROBOT SHARED RULES {v} -->'
    start, stop = s.index(begin), s.index(end)
    if stop < start:
        raise ValueError('reversed markers')
    return v, s[start:stop + len(end)]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--canonical', required=True, type=Path)
    p.add_argument('--root', type=Path, help='workspace containing repository directories')
    p.add_argument('--file', action='append', type=Path, default=[])
    a = p.parse_args(argv)
    try:
        version, expected = block(a.canonical)
    except (OSError, ValueError) as e:
        p.error(f'canonical: {e}')
    files = list(a.file)
    if a.root:
        if not a.root.is_dir():
            p.error('root is not a directory')
        files += sorted(a.root.glob('*/AGENTS.md'))
    files = sorted(set(files))
    if not files:
        p.error('no AGENTS.md files selected; refusing empty success')
    failed = False
    for path in files:
        try:
            text = path.read_text(encoding='utf-8')
            if block(path, version)[1] != expected:
                raise ValueError('shared block differs from canonical')
            if len(text.splitlines()) >= MAX_LINES:
                raise ValueError(f'AGENTS.md must be under {MAX_LINES} lines')
            if (path.parent / 'CLAUDE.md').read_text(encoding='utf-8').strip() != '@AGENTS.md':
                raise ValueError('CLAUDE.md must import @AGENTS.md without duplicate rules')
            print(f'PASS {path} ({version})')
        except (OSError, ValueError) as e:
            failed = True
            print(f'FAIL {path}: {e}', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
