---
type: regex
pattern: 'Stage 2 ready: yes'
flags: i
match: not_contains
target: { source: file, path: STATE.md }
---
