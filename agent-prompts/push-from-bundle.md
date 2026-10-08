# Push from bundle

Template version: 1. Harness: openAMRobot/.github at `<harness SHA>`.

Use when a change set has been prepared and reviewed elsewhere (a patch, a git bundle or a
folder of files) and must be pushed to a contributor branch as a draft PR.

## Precondition block (post before the first write)

```
repository:       openAMRobot/<repository>
branch:           <contributor branch>, not main
parent SHA:       <SHA the bundle was prepared against>
bundle:           <path>, sha256 <hash>
files expected:   <list of paths the bundle changes>
reviewed by:      <role> in <issue or PR link>
expected outcome: see below
```

Before writing, check that the remote default branch still contains the parent SHA, that the
bundle hash matches, and that the files the bundle changes are exactly the expected list. A
bundle prepared for one repository is never applied to another with a similar name.

## Task

1. Fetch the repository, create the branch from the parent SHA and apply the bundle.
2. Run the repository's verification (`tools/verify.sh`, or `rollout/verify.sh` from the harness).
3. Commit with `git commit -s` only under the contributor identity configured for this session.
4. Push the branch and open a draft PR using the repository's PR template, filled in, with
   the AI disclosure and the verification evidence.

Never force-push, merge, change settings, or push to main.

## Expected outcome

- One draft PR whose diff equals the bundle, on the stated parent SHA.
- The PR evidence check comment shows PASS, or the PR description lists each failure and why.
- The PR stays draft until the work-package owner writes adopt, adapt or reject.

## Failure rule

A failed precondition stops the task: wrong repository, parent SHA not found, hash mismatch,
unexpected files, or verification failure. Report the command, the error and the next step.
Do not rebase, regenerate or edit the bundle to make it fit. Open an issue labelled harness
when the failure shows a gap in this template or the harness.
