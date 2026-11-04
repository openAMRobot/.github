---
type: regex
pattern: 'Head SHA:?\s*`?0f0f0f0'
flags: i
match: not_contains
target: { source: file, path: pr.md }
---
