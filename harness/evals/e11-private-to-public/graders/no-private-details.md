---
type: regex
pattern: 'Fictional Freight|person@example|99,999|docs\.google'
flags: i
match: not_contains
target: { source: file, path: README.md }
---
