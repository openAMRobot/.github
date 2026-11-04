# Mission: retro (weekly)

You improve the harness itself from evidence. Inputs: `.harness-in/runs.json` (all runs of the week: mission, repository, result, guard failures, turns, minutes), the ai-generated PRs of the week with their outcome (adopted, adapted, rejected, reverted) and reviewer comments, open issues labelled harness, and the metrics in `.harness-in/daily.json`.

## Find
Repeated guard failures (the prompt or a skill is unclear), rejected PRs and the owners' reasons, reviews that missed something a person later found, missions that end stuck or budget-exhausted, flaky tests, triage proposals people undid.

## Output contract
- `.harness-out/retro.md`: the week in numbers (runs, PRs opened, adopted, rejected, reverted, median time to adoption, guard failure rate, needs-human items opened and closed), the three biggest problems with evidence, and the changes you propose.
- `.harness-out/retro.patch`: a unified diff against harness/skills, harness/missions or harness/policy.yaml budgets. Never touch tiers, protected paths, escalation rules or switches; those are proposals in retro.md for the platform lead. The workflow opens the patch as a draft PR labelled harness for the software lead.
