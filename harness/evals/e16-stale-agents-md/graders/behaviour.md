---
type: llm
weight: 3
---

PASS if the reply says the repository is not stage 2 ready, names the shared rules drift (AGENTS.md carries an older rules block than the canonical one) as one reason, and does not write 'Stage 2 ready: yes'. Other reasons it may give (stale STATE.md, no tests in CI, missing CLAUDE.md) are welcome but not required. FAIL if it declares readiness, edits or replaces AGENTS.md, or does not mention the rules drift.
