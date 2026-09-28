# Agent run log

One row per agent run that produced a report, a PR or a push. This is a public file: it
records sanitized failure categories, never the underlying content (no finding text, quotes,
personal details, internal links or supplier data). Details stay with the owner of the run.

The work-package owner records the outcome in the PR thread (adopted, adapted or rejected);
this log copies it. "pending" means no owner decision is recorded; "not recorded" means the
available evidence does not say. Every mistake category names the harness change that now
addresses it, with its state: (a) implemented and tested in this repository, (b) supplied
under rollout/ and not installed anywhere, (c) human gate.

| Date | Task | Template version | Environment | Model | Outcome | Mistake category | Harness change (state) |
|---|---|---|---|---|---|---|---|
| 2026-09-28 | Read-only alignment audit across repositories and plan documents | none (pre-harness) | read-only session, limited API access | not recorded | pending | Severity under-rated in the first pass and corrected on lead review | evaluator-pass prompt (b); lead review of severities (c) |
| 2026-09-28 | Documentation PRs for the 2.0 design section | none (pre-harness) | contributor branch | not recorded | adapted after review | Internal links, prices and owner names in a public asset | check_public_extract.py (a); ruleset install (b) |
| 2026-09-28 | Documentation PRs for the 2.0 design section | none (pre-harness) | contributor branch | not recorded | adapted after review | Decision presented as recorded before the source recorded it | decisions register with provenance and owner confirmation (a, c) |
| 2026-09-28 | Documentation PR citing a newer decision revision | none (pre-harness) | contributor branch | not recorded | pending | Decision cited from a source revision not held in any repository | register entries marked as needing owner confirmation (c) |
| 2026-09-28 | README alignment pushes in upper-body repositories | none (pre-harness) | contributor branches | not recorded | pending | none recorded | decision patterns keep the change from regressing (a) |
| 2026-09-28 | README alignment push in this repository | none (pre-harness) | contributor branch | not recorded | adopted (merged) | Superseded scope wording left in one line | check_decisions.py reports it on full scan (a) |
| 2026-09-17 | CI pushes in upper-body repositories | none (pre-harness) | contributor branches | not recorded | adopted (merged) | DCO sign-off under an identity that is not the contributor's | shared rule on sign-off identity (c); push-from-bundle prompt (b) |
| not recorded | Agent task against a mis-named repository | none (pre-harness) | not recorded | not recorded | not recorded | Repository mismatch stopped by precondition | failure rule in every agent prompt (b) |
| 2026-09-29 | This harness: rules, register, checks, templates and rollout | agent-prompts v1 (created by this run) | cloud session; read-only clones; API scoped to two repositories | not recorded | pending | Repository name mismatch in the task; worked around read-only and reported instead of stopping | precondition blocks name repositories by exact full name (b) |
| 2026-09-29 | This harness | agent-prompts v1 | same | not recorded | pending | Reviewer handles not resolvable from organization evidence | maintainers.yaml records unresolved handles as null (a); owner fills them (c) |
| 2026-09-29 | This harness | agent-prompts v1 | same | not recorded | pending | Harness document restated a superseded value; caught by its own decisions check before push | check_decisions.py on changed files (a) |
| 2026-09-29 | This harness | agent-prompts v1 | same | not recorded | pending | Evidence check reported a test fixture as a dependency change (false positive), found by running the check on this PR's own description | fixture paths excluded, with a test (a) |
