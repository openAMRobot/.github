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

- `in_force`: P-03-rev20.6, 2026-11-08 (branch decisions/2026-11-08-owner-decisions); P-03 rev20.6 item 30 records the Build 1 decision baseline of 8 Nov 2026 (D-01 to D-34); rev20.4 item 28 and rev20.5 item 29 enter the owner decisions of 2, 3 and 8 Nov 2026. P-03-rev20.2 was in force from 2026-11-01 (change request #77, merged 1678735)
- Canonical BOM: Issue 7.14 (BOM-ISSUE-IN-FORCE), from 2026-11-01; Issue 7.15 is the source of the public roadmap parts extract (openamrobot-docs #84), not canonical until the BOM owner confirms it (2026-11-10)

## Current work

| Work package | Branch or PR | Status | Next step |
|---|---|---|---|
| #77 | #78 (claude/optimistic-sagan-oqc2lu) | draft, rebased on ed98001 | owner review of the P-03 rev20.2 item 26 values and the OPERATOR-PANEL portrait change |
| P-03 rev20.1 | #73 | merged as ed98001 (2026-11-01) | none; its OPERATOR-PANEL portrait check is narrowed in #78 |
| harness activation | this PR | run workflow copied, pinned to 7175860 | founder approval on #43 |
| Profile 2.0 block | #81 | merged as d99264a (2026-11-04) | none; the LIFT register wording was already updated in #84 |
| Decisions of 3 Nov 2026 | #85 | merged as dafab0e (2026-11-04) | owner review: K1/K2 GX11CAC decided, rear power module, BMS side gap, FB-A/FB-B, receiver 15 mm gap, flag rod guide |
| P-03 rev20.4 (decisions of 8 Nov 2026) | decisions/2026-11-08-owner-decisions | open for owner review (2026-11-08) | owner review: in_force P-03-rev20.4, ZX80 55 mm lower, head camera 60 mm, receiver frame (no metal within 20 mm of the sides, 15 mm above), DOLD CAD, arch backing plate, new WIRING-ROUTING (slot defined, two lift cable openings, scoped check after review), P-03 rev20.6 item 30: LIFT fixing through the foot tabs 260 x 30 mm (D-20) and backing plate (D-21), COMPUTE Orin NX 8 GB on the Robotics 104 (D-01); review of 9 Nov 2026 (2026-11-10): one P-03-rev20.6 source, duplicate YAML keys rejected by the loader, WIRING-ROUTING cover-slot matcher narrowed (unless read per sentence), slot geometry enforced by openamrobot-docs slot_rule.py, BOM 7.15 recorded as the roadmap extract source, ROADMAP.md compute |
| #83 | #84 | merged as 5ed600e (2026-11-02) | none; the 2 Nov 2026 values are in force |
| M07-REST-STATE (register entry) | register/m07-rest-state (draft PR) | opened 2026-11-14 from 87c8486; records the datum owner decision of 12 Nov 2026 (openamr-upperbody-sw #48 comment 6837861823, head 6491de7), placeholder joint_rest_margin_rad 0.001 rad; requested by the reviewer on upperbody-sw #48 | adopt, adapt or reject by the work-package owner; software-lead review; engineering owner approval of the 0.001 rad placeholder |
| PLATFORM-PIN | #74 | pin 131e500fc4e5afc9f648cbd7dbf5b416280761fb (2.0 base, P-03 rev20.1 item 25 D7), validated by openamr-upperbody-sw #21; merged with this PR (2026-11-01) | none; touches decisions.yaml only |

## Decisions this repository implements

This repository holds the register (decisions.yaml) and its checkers; it implements no robot values.

## Known gaps

- Safety-path register updates (precharge fitted, K1/K2 decision 2 Nov 2026) left to the electrical owner; SAFETY-CHAIN-IO unchanged since 71c439e; SAFETY-PROCUREMENT changes only the second E-stop position (#83, 2026-11-02)
- "Chest E-stop" wording retirement (P-03 rev20.2 item 26) not recorded; it belongs to SAFETY-PROCUREMENT

## Not verified

- Register values against the P-03 rev20.2 source document (held outside any repository), since 2026-11-01
- Scans of consumer repositories against the new patterns, since 2026-11-01 (M07-REST-STATE: scanned against openamr-upperbody-sw PR #48 head 6491de7 only, 0 findings, 2026-11-14)
- Register values of 2 Nov 2026 against the owner's decision record and P-03 (not yet entered there), since 2026-11-02
