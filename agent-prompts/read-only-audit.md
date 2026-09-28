# Read-only audit

Template version: 1. Harness: openAMRobot/.github at `<harness SHA>`.

## Precondition block (post before starting)

```
repository:       openAMRobot/<audit repository> (report destination) and the audited checkouts
branch:           <audit branch>, created from main
parent SHA:       <main SHA of the audit repository>
audited SHAs:     <repository>@<SHA>, one line per checkout
previous report:  <folder>/ISSUES.csv at <SHA>, or "none"
decisions:        openAMRobot/.github decisions.yaml at <harness SHA>
write access:     audit repository only; every audited repository is read-only
expected outcome: see below
```

Check every line before reading anything else. If a repository, branch or SHA differs from the
block, or a source cannot be read, apply the failure rule.

## Task

1. Run `python3 tools/check_decisions.py --decisions decisions.yaml --root <checkout> --repository <name>`
   for every audited checkout and keep the output.
2. Compare each finding of the previous ISSUES.csv with the current checkouts: mark it
   resolved (cite the SHA and line that fixed it), still present, or changed.
3. Add new findings for contradictions between the plan documents supplied to you, decisions.yaml
   and the repositories. Each finding has: id (area prefix and number), severity (Blocker, Major,
   Minor, Question), sources quoted with file and line, decision of record, fix, file to change
   and owner role from maintainers.yaml. Use roles, never personal names.
4. Write REPORT.md and ISSUES.csv (same columns as the previous one) to a new dated folder.

Do not modify any audited repository, comment on any PR or issue, or run code that reaches
hardware or secrets.

## Expected outcome

- One new folder `<YYYY-MM-DD>-alignment-audit/` with REPORT.md and ISSUES.csv on the audit branch.
- A summary table: counts by area and severity, new, resolved and still-present findings.
- A "What could not be checked" section with the reason for each gap.
- No change in any audited repository.

## Failure rule

A failed precondition stops the task. Report the command, the error and the next step. Do not
substitute another repository, branch or source, and do not guess a value that could not be read.
Open an issue labelled harness when the failure shows a gap in this template or the harness.
