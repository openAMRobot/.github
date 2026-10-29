---
tags: ['positive']
runs: 3
max_turns: 14
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write]
---

Add one focused regression test for tools/manifest_check.py: a list with a duplicate package name must be reported. Put it in a new file tests/test_manifest_duplicates.py. Do not change anything else, then report exactly what you ran or did not run.
