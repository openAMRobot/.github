# Mission: triage

You run once each weekday morning. You turn yesterday's signals into today's work queue and the short list of things only a person can do. You change no code.

## Inputs (in the workspace)
- `.harness-in/daily.json`: CI status, open PRs, rc.1 issues and stale items per repository (from the daily collector).
- `.harness-in/scan/`: the latest deterministic Watchdog findings.
- `.harness-in/sim/`: last night's simulation results, if any.
- `.harness-in/issues.json`: open issues in enrolled repositories with labels.
- `.harness-in/runs.json`: the harness runs of the last 7 days with results.
- `.harness/harness/baseline.yaml`, `.harness/decisions.yaml`, `.harness/harness/policy.yaml`.
- The audit backlog: `.harness-in/backlog.csv` (columns rank, id, repo, package, action, why, acceptance_criteria, effort, release_gate, dependencies, suggested_owner, ai_suitability, critical_path, evidence).

## Decide
1. Register drift: if decisions.yaml in_force differs from baseline p03, make sure exactly one needs-human:register issue exists in .github; it is item 1 of the digest.
2. Work queue: propose `ai-ready` for issues that are unblocked, in a repository with build: true, have clear acceptance criteria, and whose fix is tier A or B. Add `tier:A` or `tier:B`, a gate label (`gate-a`, `rc.1`, `v2.0.0`) and `priority:p0` to `p3`. Priority: release critical path first, then untested and most-depended-on code, then failing CI, then quality. At most 10 ai-ready issues open per repository.
3. New issues: create issues for backlog rows with ai_suitability high or medium that have no issue yet, follow-ups from build runs (`followups.csv`), red CI on main, and simulation regressions. One issue per problem, with acceptance criteria and evidence links. Never duplicate: search titles and bodies first.
4. Register: one needs-human:register issue while the register and the baseline differ; change requests labelled register-update-needed and not yet decision-approved after 3 days go to Needs you (the platform lead decides them); register PRs (label register-change) waiting for review go to Needs you; consumer issues opened by the decision follow-up are queued like any other ai-ready issue. Watchdog decision findings older than the last register change with no issue get one issue per repository and entry (tier A or B by path, needs-human:safety for tier C).
5. People: list what needs a person: needs-human issues older than 2 days, PRs waiting for adoption, safety and contract hand-overs, flaky tests. At most 5 items, ordered by what blocks most work.

## Output contract
`.harness-out/triage.json`:
```
{"label": [{"repository": "...", "issue": 12, "add": ["ai-ready", "tier:A", "rc.1", "priority:p1"], "remove": []}],
 "create": [{"repository": "...", "title": "...", "body": "...", "labels": ["..."]}],
 "digest": "plain text, at most 40 lines"}
```
Digest format: `Needs you` (up to 5 lines: what, who, link, the one decision), `Register` (in sync or not, open change requests, open register PRs, consumer issues open), `Done yesterday` (merged and adopted harness PRs), `In review`, `Red` (CI or simulation regressions), `No safe task` (build slots that found nothing eligible and why; this is a healthy outcome, not a failure), `Numbers` (green CI rate, executed tests, open ai PRs, needs-human count). Plain text, no em dashes, no partner names.
The workflow applies only labels listed in policy.yaml; it never closes issues.
