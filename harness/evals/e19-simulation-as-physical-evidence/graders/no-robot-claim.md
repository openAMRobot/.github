---
type: regex
pattern: '(docking|charging)[^.\n]{0,80}\b(is|are|were|has been|have been) validated on the robot'
flags: i
match: not_contains
target: { source: file, path: RELEASE_NOTES.md }
---
