---
name: harness-register-and-baseline
description: How harness agents use the decisions register and the plan-set baseline as ground truth for every technical value. Use whenever a task involves a dimension, frame, sensor, part, limit, topic name, date or any value that could be in decisions.yaml.
---

# Register and baseline

## Order of truth (owner decision, 29 Oct 2026)
1. openAMRobot/.github decisions.yaml, at the SHA the run pinned (`.harness/decisions.yaml`), is the primary register of current decisions.
2. The Drive engineering documents (P-03, E-01, M-01, Use_Case_1 requirements) are the detailed specifications and evidence. They must say the same as the register. harness/baseline.yaml names their controlling revisions, never values.
3. Repository code and docs are consumers. When they disagree with the register, the register wins and the consumer is the finding.
CI and agents never read Drive for values (AGENTS.md "Decisions"). The weekly register audit reads plain-text snapshots that a person exported, each pinned by sha256.

## Out of sync
If decisions.yaml `in_force.source` differs from baseline.yaml `p03`, register and documents are out of sync. Then:
- do not change or test any value that a register entry covers; the selector already skips issues naming an entry ID;
- in triage, keep exactly one open issue in openAMRobot/.github labelled needs-human:register naming both revisions and the entries likely affected;
- never decide which side is right: the platform lead reconciles both in one paired change.

## The decision lifecycle (every agent plays its part)
1. Ask: every PR answers "Decisions impact" (None, Consumer with IDs, Change with a change request). The evidence check and the review mission compare the answer with the values the diff touches and ask the author when they disagree.
2. Request: a Change needs a contract change request issue in openAMRobot/.github (entry, new value with unit, source document and item). The decision follow-up opens one when a merged PR declared Change without it.
3. Approve: only the platform lead adds `decision-approved`, after updating the source document. The selector checks who added the label.
4. Draft: the register-sync mission edits only decisions.yaml and its tests, lists the paired document updates and the consumers, and opens a draft PR labelled register-change.
5. Merge: the platform lead merges.
6. Propagate: the decision follow-up scans every repository for the changed entries and opens one consumer issue per repository (ai-ready, or needs-human:safety for tier C paths). Build missions fix them; the Thursday Watchdog scan confirms.
7. Audit: the weekly register audit compares the register with the repositories and with the document snapshots, and reports mismatches as REG findings for the platform lead.

## Using a value
- Never hardcode a register value in a test. Parse it from `.harness/decisions.yaml` (copy it into a test fixture with its SHA in the file header if the repository must stay self-contained) and compare.
- A pinned register copy in a product repository goes under the repository root `tests/fixtures/register/`, the only path the register check skips; anywhere else check_decisions.py flags the copy against itself.
- Some `values` items in decisions.yaml parse as YAML mappings because they contain an unquoted `: ` (NEAR-FIELD-FRAMES tof_* line). Convert items to text before matching numbers, and report the quirk as needs-human:register rather than editing the register.
- An entry with status `open` has no value. Write "open" and report `needs-human:register`; never pick one.
- `supersedes` lists old values. Finding one in current code is a consumer fix (tier A or B unless the path is tier C).
- `check` patterns prove textual consistency only. Physical gates in P-03, E-01 and M-01 stay open until measured.
- Units SI (REP 103), frames per REP 105 and the FRAMES-REP105 entry.

## Never
Edit decisions.yaml, maintainers.yaml or baseline.yaml. Propose a register change only as a needs-human:register hand-over with the contract change request fields: entry, current value, proposed value, source document and item, affected consumers.
