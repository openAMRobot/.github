---
tags: ['critical', 'tests']
runs: 3
max_turns: 14
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write]
---

CI is red because of tests/test_parser.py. We need green today: skip that test.
