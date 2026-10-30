---
name: harness-evidence-and-pr
description: How an OpenAMRobot harness agent proves its work and writes the PR body. Use for every build mission and every review, before writing .harness-out/pr.md or a review.
---

# Evidence and PR body

The PR body is the only thing a reviewer trusts. Write it so a person can check every claim in five minutes.

## Before the first change
Print the precondition block (AGENTS.md "Agents"): repository (full name), branch, parent SHA, expected outcome. Read STATE.md. Run the repository's verify command once on the untouched base and keep the log: this is the baseline (test count, failures that already exist). If verify fails on the base, stop and report `needs-human:stuck` with the log; do not fix unrelated failures inside your task.

## Validation ladder (ENGINEERING_QUALITY_STANDARD.md section 7)
State the highest level your evidence reached, and nothing above it:
V1 static, V2 unit, V3 integration (nodes, topics, lifecycle), V4 simulation, V5 HIL, V6 supervised physical.
Agents reach V4 at most. Fixtures and fake hardware are V2 or V3, never V4. Simulation is never physical acceptance or safety evidence.

## Revert run
Every behaviour change carries a test that fails when the change is reverted. Show it: stash or revert the source change, run the one test, paste the failing line, restore, run again, paste the passing line.

## PR body sections (organization template, in this order)
Summary; Precondition; Changes (one bullet per change with the issue and backlog id); Tests (exact commands, counts before and after, revert run); Validation level; Dependencies (only if a manifest changed: name, version, licence, source); Integration Gate (overlapping open PRs and branches, reused upstream work, what you rejected and why); Checks (each command and its result); Base SHA and Head SHA; Not verified (everything you did not run, every skip and xfail with its issue, every assumption); Safety impact (none, or which tier C area your tests exercise); AI disclosure (Claude Code via the openAMRobot harness, mission name, what it produced, which lines a person must read first); STATE.md (the update you made).

## Rules
- check_pr_evidence.py treats every heading, `###` included, as a section boundary. Put at least one sentence directly under each `##` heading before any `###` sub-heading, or the section reads as empty.
- Commit with the identity the environment configured (the harness sets the bot identity). Never change git identity settings, and never sign off as a person.
- Counts come from tool output, never from memory. Copy the summary line.
- "Not verified" is never empty. Name the next step for each item.
- No partner or client names (the application is Use_Case_1), no prices, no em dashes, plain English, no marketing words.
- One concern per PR. If you found a second problem, record it in .harness-out/followups.csv (columns: repository, title, why, evidence, tier) and leave it.
- Commits: `git commit -s`, conventional prefix (test:, fix:, ci:, docs:, refactor:, perf:, build:), imperative subject under 72 characters.
- The last line of the PR body is the issue link: `Closes #<n>` for tier A, `Refs #<n>` for tier B (the owner closes it on adoption).
