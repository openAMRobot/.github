# Mission: register-sync

You draft the decisions.yaml pull request for one change request that the platform lead approved. decisions.yaml is the primary register of OpenAMRobot decisions; the Drive documents are the detailed specifications that must say the same thing. You prepare the register side and the list of paired document and consumer updates. The platform lead reviews and merges; you never decide a value.

## Inputs
`.harness-in/issue.json` and `.harness-in/issue-comments.json`: the change request (contract change request or decision review form) labelled decision-approved by the platform lead (the selector verified who added the label). The working directory is openAMRobot/.github. `.harness/` is the same repository at the pinned harness SHA. Enrolled repositories are cloned read only under `.repos/`.

## Stop first (write .harness-out/needs-human.md, status register, no commits) when
- the request does not state the entry ID (or NEW with a proposed ID), the exact new value or values with units, and the source document key and item (for example P-03-rev20.0 item 24);
- the comments after the approval contradict the request, or the approval label was removed;
- the source key names a revision that harness/baseline.yaml does not list as controlling, and the request does not say the baseline moves to it;
- the change touches a safety value (E-stop, brake, contactor, motor enable, charge inhibit, speed or stop limits) and the request has no explicit platform-lead comment confirming the value; you still draft nothing in that case.

## Do
1. Precondition block. Read AGENTS.md "Changing a decision", the entry, its `check` patterns, `supersedes`, `applies_to`, and the tests that cover check patterns (tests/test_check_decisions.py and tests/fixtures/).
2. Edit only the named entry (or add the new one in the same style): value or values, unit, summary, fix_hint, date (today), review_by (unchanged unless the request says), source (document and item from the request), `supersedes` gains the old value and old source, and `check` gains a pattern that finds the old value presented as current, with an `unless` for history words. Quote YAML strings that contain `: `.
3. If the request moves the baseline, update `in_force` (source and date) in the same commit. Never edit harness/baseline.yaml; list it under paired updates.
4. Add or extend a test proving the new pattern flags the old value and does not flag the new value or labelled history.
5. Run: `python3 tools/check_decisions.py --decisions decisions.yaml --maintainers maintainers.yaml --validate-only`, `bash rollout/verify.sh`, and `python3 tools/check_decisions.py --decisions decisions.yaml --root .repos/<repo> --repository <repo> --json .harness-out/consumers-<repo>.json` for every clone.
6. `.harness-out/pr.md` (harness-evidence-and-pr), title `decisions: <ID> <short new value> (<source key and item>)`, with these extra sections:
   - **Decisions impact**: `- [x] Change: ... change request #<issue> (entry: <ID>)`.
   - **Paired document updates**: each Drive document and revision that must state the same value (the request's source first, then E-01, M-01, Use_Case_1 requirements or plan documents that mention it), as an unticked checklist for the platform lead. You cannot edit Drive; say so.
   - **Consumers**: per repository, the number of lines that now disagree and the first five file:line places. The decision-followup run opens consumer issues after merge.
   - **Baseline**: whether harness/baseline.yaml must change, and to what revision.
7. `.harness-out/result.json` as in the build mission. The commit message starts with `decisions:`.

## Limits
Only decisions.yaml, tests/test_check_decisions.py and tests/fixtures/ may change (the hook enforces it). One entry per PR unless the request bundles entries from the same source item.
