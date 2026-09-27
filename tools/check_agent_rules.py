#!/usr/bin/env python3
"""Offline shared-rule drift check; caller supplies canonical file and checkouts."""
import argparse
from pathlib import Path
import sys
BEGIN = '<!-- BEGIN OPENAMROBOT SHARED RULES v1 -->'
END = '<!-- END OPENAMROBOT SHARED RULES v1 -->'
def block(path):
    s = path.read_text(encoding='utf-8')
    if s.count(BEGIN) != 1 or s.count(END) != 1:
        raise ValueError('expected exactly one v1 begin/end marker')
    start, end = s.index(BEGIN), s.index(END)
    if end < start:
        raise ValueError('reversed markers')
    return s[start:end + len(END)]
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--canonical', required=True, type=Path)
    p.add_argument('--root', type=Path, help='workspace containing repository directories')
    p.add_argument('--file', action='append', type=Path, default=[])
    a = p.parse_args()
    try:
        expected = block(a.canonical)
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
            if block(path) != expected:
                raise ValueError('shared block differs from canonical')
            if len(text.splitlines()) >= 120:
                raise ValueError('AGENTS.md must be under 120 lines')
            if (path.parent / 'CLAUDE.md').read_text(encoding='utf-8').strip() != '@AGENTS.md':
                raise ValueError('CLAUDE.md must import @AGENTS.md without duplicate rules')
            print(f'PASS {path}')
        except (OSError, ValueError) as e:
            failed = True
            print(f'FAIL {path}: {e}', file=sys.stderr)
    return 1 if failed else 0
if __name__ == '__main__':
    sys.exit(main())
