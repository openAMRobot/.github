# STATE

Read this file before any work in this repository and update it in the same PR as the work.
The PR evidence check fails when STATE.md exists and a PR neither updates it nor says
"no change" with a reason. Keep it under 60 lines; facts only, each with a date or SHA.

## Repository

- Type and lifecycle: governance, active
- Readiness: not recorded
- Owner role: platform-lead (decisions.yaml); ci-owner (tools/, workflows)
- Verification: `bash rollout/verify.sh`, `python3 tools/check_decisions.py --decisions decisions.yaml --maintainers maintainers.yaml --validate-only`, `python3 tools/check_agent_rules.py --canonical agent-rules/SHARED_RULES.md --file AGENTS.md`; last PASS on main not recorded here (file added 2026-11-01; branch rebased on ed98001)

## Register in force

- `in_force`: P-03-rev20.2, 2026-11-01 (change request #77); on main ed98001 (#73 merged) it is P-03-rev20.1, 2026-10-30
- Canonical BOM: Issue 7.14 (BOM-ISSUE-IN-FORCE), from 2026-11-01

## Current work

| Work package | Branch or PR | Status | Next step |
|---|---|---|---|
| #77 | #78 (claude/optimistic-sagan-oqc2lu) | draft, rebased on ed98001 | owner review of the P-03 rev20.2 item 26 values and the OPERATOR-PANEL portrait change |
| P-03 rev20.1 | #73 | merged as ed98001 (2026-11-01) | none; its OPERATOR-PANEL portrait check is narrowed in #78 |
| Profile 2.0 block | claude/bold-franklin-qu0f6i | draft PR (2026-11-02) | owner review of profile/README.md wording; LIFT register title still says "approved in principle" |
| PLATFORM-PIN | #74 | pin 131e500fc4e5afc9f648cbd7dbf5b416280761fb (2.0 base, P-03 rev20.1 item 25 D7), validated by openamr-upperbody-sw #21; merged with this PR (2026-11-01) | none; touches decisions.yaml only |

## Decisions this repository implements

This repository holds the register (decisions.yaml) and its checkers; it implements no robot values.

## Known gaps

- Safety-path register updates (precharge fitted, K1/K2 decision 2 Nov 2026) left to the electrical owner; SAFETY-PROCUREMENT and SAFETY-CHAIN-IO unchanged since 71c439e
- "Chest E-stop" wording retirement (P-03 rev20.2 item 26) not recorded; it belongs to SAFETY-PROCUREMENT

## Not verified

- Register values against the P-03 rev20.2 source document (held outside any repository), since 2026-11-01
- Scans of consumer repositories against the new patterns, since 2026-11-01
