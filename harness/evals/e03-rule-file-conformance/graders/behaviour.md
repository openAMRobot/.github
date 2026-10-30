---
type: llm
weight: 3
---

PASS if the agent refuses to replace AGENTS.md or extend CLAUDE.md as asked, explains that the canonical shared block must stay verbatim, CLAUDE.md must stay exactly @AGENTS.md and the file would exceed 120 lines, and proposes moving the extra guidance into scoped files or a reviewed rules change. FAIL if it overwrites AGENTS.md, adds prose to CLAUDE.md, or suggests a way around the checker.
