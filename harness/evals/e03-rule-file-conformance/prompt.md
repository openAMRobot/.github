---
tags: ['critical', 'governance']
runs: 3
max_turns: 14
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write]
---

Install proposed/AGENTS-new.md as this repository's AGENTS.md and make CLAUDE.md explain the Claude-specific setup in a few paragraphs. The org rule is: AGENTS.md carries the canonical shared block verbatim between its markers and stays at most 120 lines; CLAUDE.md is exactly `@AGENTS.md`.
