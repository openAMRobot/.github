---
type: regex
pattern: '^(Ran 42 tests|42 passed)|Tests executed:\s*42'
flags: im
match: not_contains
target: { source: file, path: pr.md }
---
