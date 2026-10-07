# Setup for the organization owner

Everything here needs organization-owner or repository-admin rights. The session that wrote
this file configured none of it.

## State of every check and workflow

Each item is in one of three states:

- **(a)** implemented and tested in this repository;
- **(b)** supplied under `rollout/` as an example, not installed anywhere;
- **(c)** a human gate.

No failure class is machine-blocked in product repositories until the relevant workflow is installed
in each repository and its check is required by that repository's ruleset. That installation
is a rollout step (rollout/README.md), not a present fact.

| Check or workflow | State | What was exercised in the authoring session |
|---|---|---|
| `tools/check_decisions.py` with `decisions.yaml` | (a) | Unit tests on a fixture repository (matching value, contradicting value, unlisted file type, superseded citation, allow marker, exclusion); read-only dry runs on local clones of product repositories |
| `tools/check_public_extract.py` with the allowlist | (a) | Unit tests; dry runs on local clones |
| `tools/check_pr_evidence.py` | (a) | Unit tests; local run on a simulated pull_request event; nothing posted |
| `tools/check_agent_rules.py` (drift) | (a) | Unit tests; run on this repository and on local clones |
| `tools/sync_audit_issues.py` | (a) | Unit tests with a fake API; nothing created or commented |
| `rollout/verify.sh` | (a) | Unit tests; run on this repository and on a local clone of openamrobot-manifest; not on ROS 2 or Node repositories |
| `repository-quality-reusable.yml`, harness steps (`harness_warn: true` warn-only, `harness_checks: true` enforcing) | (a) for this repository's own caller; (b) for every other repository | `run:` steps dry run locally with checkouts simulated; never run on GitHub. Off by default, so existing `@main` callers are unchanged until they opt in |
| `repository-quality-reusable.yml`, `quality/test` job (`verify: true`) | (b) | Never run on GitHub |
| `repository-quality.yml` in this repository (`quality/test`, harness checks) | (a) once merged; never run on GitHub yet | Its commands ran locally |
| `pr-assistant.yml` | (b) | Its two checker commands ran locally; the workflow never ran |
| `.github/workflows/watchdog-org-scan.yml` + `tools/watchdog_issue_sync.py` | (a) in the harness repository | Thursday organization scan, central dashboard, stable grouped issue deduplication, redaction, no-longer-detected comments, re-opening of reappearing findings and blocked-scan behavior are covered by tests; it never edits `decisions.yaml` or product repositories |
| `docs-sync-caller.yml`, `docs-sync.yml` | (b), design only | Never run |
| `monthly-retro.yml` | (b), design only | Never run |
| Two human approvals on safety paths | (c) enforced by a ruleset, section 6 | `check_pr_evidence.py` only reports "safety path touched, two human approvals required" and whether reviewers are requested; it does not count approvals as a gate |
| Decision-register changes | (c) the entry's owner | The register's own schema validation is (a) |
| Every `[human: ...]` rule in AGENTS.md | (c) | Not machine-checked |

**Documentation policy.** The canonical documentation policy is
[`openamrobot-docs/docs/DOCUMENTATION_STANDARD.md`](https://github.com/openAMRobot/openamrobot-docs/blob/main/docs/DOCUMENTATION_STANDARD.md),
owned by the documentation owner. `tools/check_public_extract.py` and
`public-extract-allowlist.yaml` implement one part of it: they separate intentional public
content (organization contact, licensing information, documentation) from accidental leakage
(internal document links, private contact data, prices, credentials). The allowlist is an
implementation detail, not policy; when it and the standard disagree, the standard wins.

## 1. Pin the harness

Pinning is done per repository, in the order of rollout/README.md, not organization-wide:

1. After the harness PR merges, take its merge commit SHA as `<HARNESS_SHA>`.
2. Step (b): in the repository's caller, replace `@main` with `@<HARNESS_SHA>` and add
   `with: harness_ref: <HARNESS_SHA>`. Do not set `harness_checks` here.
3. Step (c): add `harness_warn: true` (warn-only) until a run on main is green.
4. Step (d): replace it with `harness_checks: true`. Step (e) then adds the ruleset (section 6).
5. Replace `<HARNESS_SHA>` in each workflow copied from `rollout/workflows/`.

openamrobot-interfaces is the pilot and completes all five steps before any other repository
starts step (c).

## 2. GitHub-native Watchdog publication

The deterministic Watchdog uses the repository-scoped `GITHUB_TOKEN` only for `issues: write` in
`openAMRobot/.github`. It cannot push code or create pull requests. The job reads product
repositories anonymously and publishes a redacted central issue dashboard. No Anthropic secret,
Claude App or AI workflow is needed for this path.

The dashboard is safe to activate after PR #38 merges. A decision-register change remains a
human-reviewed PR; the Action only creates a review issue and never rewrites the register.

## 3. Secrets

| Secret | Scope | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`, then change the input name) | audits, openamrobot-docs, .github | weekly audit, docs sync, monthly retro |
| `AUDIT_APP_ID`, `AUDIT_APP_PRIVATE_KEY` | audits | weekly audit issue sync |
| `DOCS_SYNC_APP_ID`, `DOCS_SYNC_APP_PRIVATE_KEY` | organization secret, product repositories | docs sync sender |
| `RETRO_APP_ID`, `RETRO_APP_PRIVATE_KEY` | .github | monthly retro |

The three App secret pairs may point to one GitHub App. The PR assistant uses only
`GITHUB_TOKEN`. AI workflow activation is tracked separately in [issue #43](https://github.com/openAMRobot/.github/issues/43) and remains disabled until every checklist item is evidenced.

Authentication mode must be chosen before activation. The examples use `ANTHROPIC_API_KEY` for Anthropic API authentication and retain `id-token: write` because the official Claude GitHub App path uses GitHub OIDC for the action's default GitHub token. If the organization chooses Anthropic Workload Identity Federation instead, remove the API-key secret, add the federation identifiers required by Anthropic, and keep `id-token: write`; do not configure both Anthropic credential modes by accident. Record the selected mode and the manual disposable-branch test in issue #43.

## 4. GitHub Apps

1. **Claude GitHub App** (github.com/apps/claude), on audits, openamrobot-docs and .github
   only. It asks for Contents, Issues and Pull requests read and write. The current Claude Code
   documentation lists further permissions because the App is shared with other Claude
   features. Grant what the install screen asks, on those three repositories only.
2. **Harness App** (organization-owned, private), installed on the product repositories and
   audits, with these permissions:
   - Issues: read and write.
   - Pull requests: read.
   - Contents: read and write. This is needed only for `repository_dispatch` to openamrobot-docs.
   - Metadata: read.

   It gets no administration, workflow or secrets permission.

## 5. Actions settings

- Default workflow token: read repository contents only.
- "Allow GitHub Actions to create and approve pull requests": off.
- If actions are allow-listed, allow exactly these, pinned by commit SHA in the files:
  - `actions/checkout` v7.0.1
  - `actions/upload-artifact` v7.0.1
  - `actions/create-github-app-token` v3.2.0
  - `anthropics/claude-code-action` v1.0.236

  The live workflows in this repository are pinned to full commit SHAs; the workflow-policy check fails on any unpinned external action or unresolved `<HARNESS_SHA>` in `.github/workflows/`. Examples under `rollout/` are exempt until copied.
- Require approval for workflows from first-time fork contributors.

## 6. Labels (every repository)

| Label | Used by |
|---|---|
| `harness` | harness mistake form, monthly retro |
| `good first issue` | good first issue form, CONTRIBUTING.md |
| `contract-change` | contract change request form |
| `watchdog-finding`, `watchdog-review`, `watchdog-report`, `blocker`, `major`, `review` | deterministic Watchdog issue sync; the Action creates missing labels in the harness repository |\n| `audit-finding`, `blocker`, `major` | legacy weekly audit issue sync |
| `triage`, `bug` | existing forms |
| `area:docs`, `area:navigation`, `area:interfaces`, `area:manipulation`, `area:ui`, `area:release`, `area:ci` | good first issue triage |

## 7. Rulesets on main (per repository)

For every active repository:

- Require a pull request, CODEOWNERS review and conversation resolution.
- Block force pushes and deletions; restrict bypass to the organization owner.
- Required status checks, each added after it has passed on main once:
  - `repository-quality / repository-quality` (with `harness_checks: true`)
  - `quality/pr-evidence` (once `pr-assistant.yml` is installed)
  - `quality/test` (once `verify: true` is set)

**Two human approvals on safety paths.** A ruleset rule, not a check, supplies these. The
paths are listed under `safety_paths` in maintainers.yaml. For each repository that contains
such paths, add a ruleset with "Require approvals: 2" and "Require review from Code Owners",
and a CODEOWNERS entry that makes the platform lead an owner of those paths:

| Repository | Safety-relevant paths to cover | Approvals |
|---|---|---|
| openamr-platform-fw | E-stop, brake, contactor, watchdog, motor-enable, charge-inhibit sources | 2, platform lead via CODEOWNERS |
| openamr-platform-hw | safety chain wiring, E-stop and contactor documents | 2, platform lead via CODEOWNERS |
| openamr-platform-sw | watchdog, collision monitor, docking and charge-state code | 2, platform lead via CODEOWNERS |
| openamr-upperbody-fw, openamr-upperbody-hw | arm power and E-stop integration | 2, platform lead via CODEOWNERS |
| openamrobot-ui | E-stop and stop controls, charge-state display | 2, platform lead via CODEOWNERS |
| openamrobot-docs | `docs/safety/` and safety sections of reference pages | 2, platform lead via CODEOWNERS |

GitHub rulesets apply approval counts per branch, not per path. Where a repository does not
want two approvals on every PR, the path-level requirement rests on CODEOWNERS for the lead's
approval. The second approval stays a human gate (c) that `check_pr_evidence.py` reports.

Single-maintainer repositories keep required checks. The CODEOWNERS waiver follows section 8
of the Engineering Quality Standard.


**Shared rules and exceptions.** With `harness_checks: true`, a repository must contain
`AGENTS.md`. A repository without it may pass only by supplying the reusable-workflow input
`agents_md_exception` with a non-empty human-readable reason; the reason is written to the
job summary. Warn-only mode reports the missing file but never turns it into a silent pass.
For platform-lead-authored PRs, apply the approval policy in `GOVERNANCE.md` and
`maintainers.yaml`: software-lead approval plus every scoped-owner approval; the author's
reconciliation comment is not an approval.

## 8. Maintainers map

Fill the empty handles in `maintainers.yaml` (ci-owner, release-owner, docs-owner) once the people confirm
their GitHub accounts and join the organization. Until then, automation names the role and
mentions nobody.
