<!--
Fill every section. tools/check_pr_evidence.py reads this description on every push and
posts one summary comment. Headings must stay as they are. Rules: AGENTS.md.
Keep the PR as a draft until the evidence check passes on the current head.
-->

## Summary

<!-- What changed and why, in plain sentences. Scope: which repository paths. -->

## Work package

<!-- Issue link of the work package or contract change request, e.g. #123. -->

## Integration Gate

<!-- What already existed (open PRs, branches, upstream packages), what you reused,
what you rejected and why. -->

## Tests

<!-- Test added or changed, and the run that fails when the change is reverted.
Report counts, e.g. "Ran 42 tests, 0 skipped". A run with zero tests fails the check. -->

## Evidence

Base SHA:
Head SHA:

```
<!-- exact commands you ran, one per line, with their result lines -->
```

## Dependencies

<!-- None, or each added, removed or upgraded dependency with licence and source. -->

## Safety impact

<!-- None, or: motion / power / battery / actuator / safety I/O / E-stop / brake / contactor /
watchdog / motor-enable / charge-inhibit. Safety paths need two human approvals (ruleset) including the
platform lead. Telemetry and fixtures are not safety evidence. -->

## STATE.md

<!-- Updated, or "no change" with the reason. -->

## Not verified

<!-- Everything you could not run or check, and why. SKIP or BLOCKED is not PASS. -->

## AI disclosure

<!-- None, or the tool, what it produced and how you reviewed it. -->

## Contribution terms

- [ ] Every commit is signed off under the [DCO](https://github.com/openAMRobot/.github/blob/main/DCO.md).
- [ ] I am covered by an accepted [Contributor Agreement](https://github.com/openAMRobot/.github/blob/main/CLA.md).
- [ ] Third-party material is identified with source and licence.
- [ ] No confidential, personal, credential or export-controlled information is included.
- [ ] No partner, customer or private person is named; the application is Use_Case_1.
