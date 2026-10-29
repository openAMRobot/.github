# The harness: AI agents that improve OpenAMRobot every day

The harness extends the Watchdog. The Watchdog finds disagreements with the register and uses no AI. The harness runs Claude Code agents on GitHub's runners to act on what the Watchdog, CI and simulation find: they write tests, fix CI, clean code, audit dependencies, contracts, impact, performance, maintainability and the register, review every PR, keep decisions.yaml in step with the repositories, and tell people the few things only people can decide.

People keep three things: safety, decisions and merging.

## Connecting Claude

Three things get connected, in openAMRobot/.github and the private openAMRobot/audits only (product repositories hold no secrets):

| What | Why | How |
|---|---|---|
| A Claude credential (in openAMRobot/.github and openAMRobot/audits) | lets the workflow run Claude Code on a GitHub runner | one of three, in this order of preference. **Workload identity federation** (recommended for unattended runs): in the Claude Console create a service account and a federation rule for these two repositories, then set the variables `ANTHROPIC_FEDERATION_RULE_ID` and `ANTHROPIC_ORGANIZATION_ID`; each run gets a short-lived credential and no key is stored. **`ANTHROPIC_API_KEY`**: a Console key in its own workspace with a monthly spend limit, rotated every quarter. **`CLAUDE_CODE_OAUTH_TOKEN`**: `claude setup-token` on a computer logged in to a Pro, Max, Team or Enterprise plan; runs use that person's subscription, so keep it for the supervised dry runs only. |
| The GitHub App **openamrobot-harness** (two secrets) | the only identity that pushes branches, opens draft PRs, comments and labels | create it under the organization's Settings, Developer settings, GitHub Apps. Repository permissions: Contents read and write, Pull requests read and write, Issues read and write, Actions read, Checks read, Metadata read. No Workflows permission (agents never change workflow files) and no organization permissions. Install it on the repositories in `harness/policy.yaml` and on `audits`. Save `HARNESS_APP_ID` and `HARNESS_APP_PRIVATE_KEY` as secrets in openAMRobot/.github and openAMRobot/audits. |
| Variables | switches you flip without a commit | `HARNESS_ENABLED`, `HARNESS_STAGE`, `HARNESS_PUBLISH`, `HARNESS_EGRESS`, `HARNESS_BOT_NAME`, `HARNESS_BOT_EMAIL` |

Why the order matters: the agent's processes run next to the credential, and a GitHub-hosted runner gives them sudo, so nothing that runs after the agent in the same job is a security boundary. Federation gives each run a credential that expires within the hour and lives in a spend-limited workspace, which bounds the damage if a prompt injection ever exfiltrated it. A Console API key is spend-limited but long-lived: a stolen key works until it is revoked, so rotate it every quarter and revoke it at once on any suspicion. A personal subscription token is neither.

The official "Claude" GitHub App (used for `@claude` mentions) is not needed. Its permission set is broader than the harness needs, so the harness uses its own App. Claude never sees the App key: only deterministic steps before and after the agent use it.

The same skills are available to people working with Claude Code on their own computer: `/plugin marketplace add openAMRobot/.github`, then `/plugin install openamrobot-harness@openamrobot`.

## How a day runs (UTC)

| Time | What | AI | Writes |
|---|---|---|---|
| 04:41 | Daily collector (`watchdog-daily.yml`): CI, open PRs, rc.1 issues, stale items | no | artifact, dashboard |
| 04:47 | Simulation analysis of the night's runs | read only | audit-finding issues |
| 05:07 weekdays | Triage: work queue, register status, the "[harness] Daily digest" issue | read only | labels, at most 5 issues, the digest |
| 05:37, 08:37, 11:37, 14:37 weekdays | Build: one issue, one repository, one draft PR, or "no safe task" | yes | draft PR or a hand-over |
| 05:52 | Decision follow-up: merged register changes and their consumers | no | labels, comments, consumer issues |
| 06:22 weekdays | Register sync: drafts the decisions.yaml PR for an approved request | yes | draft PR in .github |
| every 30 min, 06:00 to 20:30 | Review: next PR without a harness review for its head SHA | read only | one comment per PR |
| 03:23 | Weekly audits: dependencies (Mon), contracts (Tue), impact (Wed), performance and maintainability (Fri) | read only | audit-finding issues |
| Thu 03:23 | Register audit, in the private audits repository (`harness-register-audit.yml`), so document quotes never reach a public artifact | read only | REG findings |
| Fri 15:17 | Retro: what went wrong, proposed fixes to skills and missions | yes | draft PR to `harness/` |
| Thu 14:00 | Watchdog organization scan (unchanged) | no | dashboard |

## Keeping decisions.yaml correct and current

decisions.yaml is the primary register (owner decision, 29 Oct 2026). The Drive documents are the detailed specifications and must say the same thing. Seven steps keep the two and every repository in step:

1. **Every PR is asked.** Each PR answers "Decisions impact": None, Consumer (with the entry IDs) or Change (with a change request). The evidence check (`tools/check_pr_evidence.py --decisions`) fails a malformed answer, and it compares the answer with the register values the diff adds or removes. When they disagree, it asks the author in the PR comment: "the diff touches values of ENTRY; is this PR a consumer or a change?" The review mission asks the same question with judgement.
2. **A change becomes a request.** A Change needs a contract change request issue in openAMRobot/.github: the entry, the new value with unit, the source document and item. If a PR that declared Change merges without one, the follow-up opens it (`needs-human:register`).
3. **The platform lead approves**, after updating the source document, by adding `decision-approved`. The selector reads the issue history and accepts the label only from the platform lead's account.
4. **The harness drafts the register PR.** The register-sync mission edits only decisions.yaml and its tests. It adds supersedes history and a check pattern for the old value. The PR body lists the paired document updates and every consumer line that will now disagree. It is labelled `register-change`.
5. **The platform lead merges it.** Nothing changes the register without that merge.
6. **Consumers follow automatically.** The decision follow-up compares decisions.yaml before and after the merge and scans every repository for the changed entries. It opens one consumer issue per repository: ai-ready for tier A and B lines, needs-human:safety for tier C. Build missions fix them, and the Thursday Watchdog scan confirms.
7. **Weekly audit.** The register audit compares the register with every repository (including values the check patterns miss) and with the document snapshots. Mismatches become REG findings for the platform lead, kept in the private audits repository when they quote a document.

While decisions.yaml `in_force` differs from `baseline.yaml` `p03`, register and documents are out of sync. Build missions skip every issue that names a register entry, and the digest shows the mismatch first. Today the register says P-03 rev19.6 and the baseline says P-03 rev20.0.

### Document snapshots

CI never reads Drive. For the weekly register audit, the platform lead (or a Claude session with the Google Drive connector) exports each controlling document as plain text when a revision is issued:

1. Export the Google Doc as plain text (File, Download, Plain text), named `P-03-rev20.0.txt` (the same for E-01, M-01 and the Use_Case_1 requirements).
2. Commit it to branch `baseline` of openAMRobot/audits under `baseline/`.
3. Add `{document, path, sha256}` (sha256 of the file) to `snapshots.files` in `harness/baseline.yaml`, and update the revision fields, in one reviewed PR.

The register audit runs in openAMRobot/audits itself, reads the snapshots from its `baseline` branch, and checks every hash. Its outputs and issues stay in that private repository.

## What people do (about 15 minutes a day)

1. Read the "[harness] Daily digest" issue in openAMRobot/.github. **Needs you** has at most five items, each with one question, the options and a recommendation.
2. Answer the needs-human issues assigned to you. The sub-label says what is needed: `register`, `safety`, `contract`, `decision`, `hardware`, `stuck`, `flaky` or `security`.
3. Adopt, adapt or reject the harness's draft PRs in your repositories (write the word in the thread; the retro learns from it).
4. Platform lead: approve change requests (`decision-approved`), merge register PRs, export snapshots when a document revision is issued.
5. `no-ai` on an issue or PR keeps agents away; `hold` stops an automatic merge.

## Autonomy tiers (harness/policy.yaml)

| Tier | What | Who writes | Who merges |
|---|---|---|---|
| A | tests, docs, lint-only, outside protected paths | agent | the code owner; from stage 4 the merge gate after a passing review, green checks and a 24 h veto window |
| B | non-safety source, configuration, launch, build scripts | agent | the code owner |
| C | E-stop, brake, contactor, watchdog, motor enable, charge inhibit, `*safety*`, twist_mux, velocity_smoother, collision_monitor, docking, Nav2 launch and parameters, ros2_control limits, the policy runner, UI stop and motion, all firmware and hardware repositories, every .msg, .srv and .action | a person; the agent adds tests in new files and reviews | two people including the platform lead |
| D | register, maintainers, CODEOWNERS, licences, AGENTS.md, CLAUDE.md, `.claude/`, workflow files, the harness itself | a person; the one exception is register-sync, which may draft decisions.yaml and its tests from an approved request | the owner |

## How the rules are enforced

Prompts are not enforcement. Code that the agent cannot change enforces every rule that matters:

1. **Core rules:** `harness/CORE_RULES.md` (13 rules) is loaded into every session by a SessionStart hook, in CI and in the local plugin; the skills hold the detail. The behaviour evaluations measure it.
2. **Selection:** `tools/harness_select.py` picks the work; "no safe task" is a normal, healthy result.
3. **While it works (first line, not the boundary):** the PreToolUse hook `harness/claude/hooks/guard_tool.py` enforces the policy. It blocks tier C and D writes (except the register-sync exception), writes outside the checkout, writes in read-only missions, and commands such as `git push`, `gh`, `curl`, flashing and CAN tools. It fails closed. It was exercised in real headless Claude Code runs.
4. **No credential and limited network:** the agent's checkout has no push credential. harden-runner limits egress (audit mode first, then block).
5. **After it works, in a separate job:** the publish job clones the repository fresh and checks that the agent's bundle sits exactly on the base the agent started from. It then runs `tools/harness_guard.py` from its own trusted checkout, never the agent's. The guard checks tiers, removed tests, skips without an issue, DCO sign-off, dependency changes, binaries, secret-like strings and size limits. No agent code runs in that job; a failure means nothing is pushed. Test counts come from the agent's job and are advisory. The PR's own CI is the real test gate.
6. **Outputs:** only allowlisted output files are uploaded. A file containing the Claude credential, the workflow token or any secret-like string is dropped.
7. **Publishing:** `tools/harness_publish.py` validates every agent output (schemas, allowed labels, length limits) and only does what the mission allows. With `HARNESS_PUBLISH` unset it is a dry run that prints its plan.
8. **Untrusted input:** issue, PR, comment, file and log text is data, never instructions (harness-protected-paths). Fork PRs reach the reviewer only after a maintainer labels them `ai-review`. The reviewer reads PR code but never runs it. A review or merge decision counts only when the harness bot wrote the comment, because anyone can type the hidden marker.
9. **Repository rulesets:** code-owner review and required checks on every default branch. The App is not a code owner and has no bypass before stage 4.

## Stages and activation

**What activates the harness.** Only the founder's explicit approval comment on issue #43 (D-02), written after three things: the harness PR is reviewed and merged; the behaviour evaluations pass (below); and a supervised dry run (stage 0) has been read. Closing #43, merging a PR or setting a variable is not authorization by itself. Only the founder sets `HARNESS_ENABLED`.

| Stage | Turns on | Gate to the next stage |
|---|---|---|
| 0 dry run | `HARNESS_PUBLISH` unset: a run started by hand (Run workflow) runs any mission whatever `HARNESS_STAGE` says, prints its plan and writes nothing; scheduled AI runs are skipped. Stage gates apply only once `HARNESS_PUBLISH=true` | evaluations pass; three supervised manual runs (triage, one build, one review) with their plans read by the platform lead; the founder's approval comment on #43 |
| 1 observe | triage, audits, digest, decision follow-up (`HARNESS_PUBLISH=true`) | one week of useful digests |
| 2 author | build and register-sync in repositories with `build: true` | evaluations rerun and passing; per repository: the enforcement checklist below, `rollout/verify.sh` passes on main with a real test count, tests run in CI, AGENTS.md v2, STATE.md current; then two weeks with under 30 percent rejected PRs |
| 3 review | review comments on every PR | four weeks with no reverted harness PR |
| 4 merge tier A | `harness-merge.yml` | shared rules v3 adds the tier A merge exception; ruleset bypass for the App in "pull requests only" mode |

### Behaviour evaluations (gate for stage 0 and stage 2)

`harness/evals/` holds 14 cases (E01 to E14) run with `claude plugin eval` (command in `harness/evals/README.md`). Every critical case must score 1.0 in each of three runs with the model the workflows pin. The first run on 29 Oct 2026 showed why: with rules only in on-demand skills, 4 of 14 cases passed (one copied customer details into a public README). With `harness/CORE_RULES.md` loaded at every session start, 14 of 14 passed three runs out of three (`harness/evals/BASELINE.md`). Rerun after every change to the core rules, skills, missions, policy or model.

### Enforcement checklist (a person confirms, per repository, before stage 2)

Files and checkers are not enforcement. The platform lead or CI owner confirms in the repository settings and records it on #43:

1. A ruleset on the default branch requires a pull request, code-owner review (two approvals, including the platform lead, for safety paths), and the repository's CI test job and `quality/pr-evidence` as required checks; it blocks force pushes and deletions; no bypass actors.
2. CODEOWNERS names real, active handles for every path.
3. DCO is enforced, and the merge method is squash or merge (whichever the repository owner chose).
4. Actions: workflow permissions default to read; no secrets in the repository; forks need approval to run workflows.
5. The harness App is installed with the permissions in "Connecting Claude" and nothing more.

### Activation steps (organization owner)

1. Merge the harness PR and record its merge SHA.
2. Connect Claude and create the App (section "Connecting Claude").
3. Create the labels in `harness/policy.yaml` in every enrolled repository.
4. Copy `rollout/workflows/harness-run.yml` to `.github/workflows/` and `rollout/workflows/harness-register-audit.yml` to `.github/workflows/` of openAMRobot/audits, replace `<HARNESS_SHA>`, review and merge.
5. Run the behaviour evaluations and attach the JSON to #43.
6. Set `HARNESS_ENABLED=true` and `HARNESS_STAGE=1` and leave `HARNESS_PUBLISH` unset. Then use Actions, Harness run, Run workflow for mission `triage`, then `build`, then `review`, and read each plan in the job summary. With publishing unset these manual runs ignore the stage gate, so build and review run as dry runs even at stage 1; nothing is written.
7. Founder approval comment on #43; then set `HARNESS_PUBLISH=true`.
8. After one week, set `HARNESS_EGRESS=block`.

### Decisions impact everywhere (tracked)

The rule warns until each repository requires it. Issue "[harness] Decisions impact required in every repository" (owner: CI owner) tracks the per-repository steps:

- add the section to the repository's own PR template (tier A for the harness);
- add `--decisions`, `--files-json` and, after two weeks of warnings, `--require-decisions-impact` to its PR assistant.

Scheduled workflows run from the default branch and are attributed to the person who last changed the cron lines; the action refuses bot actors. Keep cron changes in human-authored PRs.

## Stopping it

`HARNESS_ENABLED` not `true` stops everything; a lower `HARNESS_STAGE` stops one capability; `HARNESS_PUBLISH` unset turns every run into a dry run; `build: false` or `review: false` in policy.yaml stops one repository; `no-ai` stops one issue or PR; suspending the App installation stops every write at once.

## Budgets and metrics

Budgets are counted in runs, turns and minutes (`harness/policy.yaml`): 4 build runs per weekday, 80 turns and 50 minutes each; 2 attempts per issue; at most 2 open harness PRs per repository and 8 in the organization. When the Claude usage limit is reached the run stops, and the next slot tries again.

Metrics (digest daily, retro weekly) measure value, not volume: defects found and reproduced, harness PRs adopted, adapted, rejected and reverted, median time to adoption, review effort, guard failure rate, green CI rate and executed tests per repository, register mismatches open, needs-human items and their age, and simulation scenario pass rate with fidelity records.

## First work for the harness

Seeded from the 29 Oct software plan and the 29 Oct external audit, and kept in step with open PRs:

1. Register reconciliation to P-03 rev20.0 and BOM 7.14 (human; the register-sync mission drafts it once the request is approved).
2. openamrobot-manifest: once the owner decides the workspace boundary in issue #8, a regression check that the chosen entry point discovers the intended package set and rejects duplicate package names.
3. openamrobot-interfaces: negative compatibility tests for the type-hash gate after PR #29 settles.
4. openamr-platform-sw: review PR #101 (it enables `verify: true` for #98; do not duplicate it), then the test items PSW-03, PSW-08 and PSW-15 from PR #103.
5. openamrobot-docs: a page that explains the evidence labels (software, simulation, bench, physical).

## Coverage

Fifteen repositories are enrolled in `harness/policy.yaml` (review and build flags per repository). openamrobot-embodied-ai joins the Watchdog scan with PR #69. The private audits repository runs only the register audit, in its own workflow. Four repositories are excluded by owner decision: openamr, EOD-robot, OpenAMR_UI_dev and OpenAMR_UI_package. No agent reads or writes them; reports and the daily digest name them as excluded (out of scope), never as clean or unscanned. A test checks that every repository has exactly one of these dispositions.

## Files

| Path | What |
|---|---|
| `harness/policy.yaml` | tiers, protected paths, blocked commands, budgets, schedule, missions, escalation, labels, enrolment |
| `harness/baseline.yaml` | controlling document revisions, snapshots, stale documents, release dates |
| `harness/backlog.csv` | ranked backlog from the 29 Oct 2026 software plan, seed for triage |
| `harness/missions/*.md` | what each run does and must output |
| `harness/CORE_RULES.md`, `harness/hooks/hooks.json` | the 13 always-loaded rules and the plugin's SessionStart hook |
| `harness/skills/*/SKILL.md` | 16 skills, also published as the Claude Code plugin `openamrobot-harness` |
| `harness/evals/` | the 14 behaviour evaluations and their record |
| `harness/claude/settings.json`, `harness/claude/hooks/guard_tool.py` | Claude Code tool permissions and the enforcing hook |
| `tools/harness_*.py`, `tools/decision_impact.py`, `tools/decision_followup.py` | selection, inputs, guard, publish, review queue, merge gate, decisions impact, decision follow-up |
| `rollout/workflows/harness-run.yml`, `harness-merge.yml` | the workflows, design until activation |
| `.claude-plugin/marketplace.json` | plugin marketplace for local Claude Code |

## Known limits

- CI runners are not the Jetson and not the robot. Simulation is validation level V4, and nothing here is physical or safety evidence.
- File names containing `watchdog` match the `**/*watchdog*` safety path in maintainers.yaml (see PR #69). Harness files avoid the word.
- The value-fingerprint check finds register values in changed lines; it asks a question and never decides. Values the register does not hold are found by the review mission and the weekly register audit.
