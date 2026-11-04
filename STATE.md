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

- `in_force`: P-03-rev20.2, 2026-11-01 (change request #77, merged 1678735); unchanged by the owner decisions of 2 Nov 2026, which carry a note that they are to be entered in P-03
- Canonical BOM: Issue 7.14 (BOM-ISSUE-IN-FORCE), from 2026-11-01

## Current work

| Work package | Branch or PR | Status | Next step |
|---|---|---|---|
| #77 | #78 (claude/optimistic-sagan-oqc2lu) | draft, rebased on ed98001 | owner review of the P-03 rev20.2 item 26 values and the OPERATOR-PANEL portrait change |
| P-03 rev20.1 | #73 | merged as ed98001 (2026-11-01) | none; its OPERATOR-PANEL portrait check is narrowed in #78 |
| harness | #70 (harness/autopilot-2026-10-30) | in review, f4e0837 plus review fixes 5 | owner review of the six review fixes, then merge |
| Profile 2.0 block | #81 | merged as d99264a (2026-11-04) | none; the LIFT register wording was already updated in #84 |
| Decisions of 3 Nov 2026 | this PR (decisions/2026-11-03) | ready for review (2026-11-04) | owner review: K1/K2 GX11CAC decided, rear power module, BMS side gap, FB-A/FB-B, receiver 15 mm gap, flag rod guide |
| #83 | #84 | merged as 5ed600e (2026-11-02) | none; the 2 Nov 2026 values are in force |
| PLATFORM-PIN | #74 | pin 131e500fc4e5afc9f648cbd7dbf5b416280761fb (2.0 base, P-03 rev20.1 item 25 D7), validated by openamr-upperbody-sw #21; merged with this PR (2026-11-01) | none; touches decisions.yaml only |

## Decisions this repository implements

This repository holds the register (decisions.yaml) and its checkers; it implements no robot values.

## Known gaps

- Safety-path register updates (precharge fitted, K1/K2 decision 2 Nov 2026) left to the electrical owner; SAFETY-CHAIN-IO unchanged since 71c439e; SAFETY-PROCUREMENT changes only the second E-stop position (#83, 2026-11-02)
- "Chest E-stop" wording retirement (P-03 rev20.2 item 26) not recorded; it belongs to SAFETY-PROCUREMENT

## Not verified

- Register values against the P-03 rev20.2 source document (held outside any repository), since 2026-11-01
- Scans of consumer repositories against the new patterns, since 2026-11-01
- Register values of 2 Nov 2026 against the owner's decision record and P-03 (not yet entered there), since 2026-11-02
