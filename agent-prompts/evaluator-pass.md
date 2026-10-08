# Evaluator pass

Template version: 1. Harness: openAMRobot/.github at `<harness SHA>`.

A second agent reads a PR before a human does and reports what the gates cannot see. It never
approves, requests changes, merges or pushes.

## Precondition block (post before reading the diff)

```
repository:       openAMRobot/<repository>
pull request:     #<number>
head SHA:         <SHA under evaluation>
base SHA:         <SHA>
rules:            AGENTS.md shared block <version> at <harness SHA>
write access:     none (report goes to the requesting person)
expected outcome: see below
```

If the PR head moved after the block was written, stop and restart with the new head.

## Task

1. Run check_pr_evidence.py, check_decisions.py and check_public_extract.py on the PR and record
   their output.
2. For every rule in the shared block marked [decides: ...], state whether the PR needs that
   decision and who makes it.
3. Check that each claimed test fails when the change is reverted: revert the change locally,
   run the stated command, and record the result.
4. Check that nothing in the Evidence or Tests section overstates what ran (fixture as simulation,
   skip as pass, draft as accepted).

## Expected outcome

- A report with: gate results, decisions needed and their deciders, revert-test result, and a
  list of overstated claims, each with file and line.
- No write to the repository or the PR.

## Failure rule

A failed precondition stops the task. Report the command, the error and the next step. Do not
evaluate a different head or repository. Open an issue labelled harness when the failure shows
a gap in this template or the harness.
