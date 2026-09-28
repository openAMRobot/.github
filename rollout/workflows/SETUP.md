# Setup for the organization owner

Everything here needs organization-owner or repository-admin rights. Nothing in this list was
configured by the session that wrote it. Each item names where it is used.

## What ran in the authoring session and what is design only

| Automation | Status |
|---|---|
| Checkers (`tools/*.py`) and `rollout/verify.sh` | Ran locally with unit tests; dry runs against local checkouts of product repositories |
| `repository-quality-reusable.yml` shell steps | Dry run locally against openamrobot-docs and openamrobot-manifest (checkout steps simulated) |
| `pr-assistant.yml` | Its two checker commands ran locally on a simulated event; the workflow has not run on GitHub and has not posted a comment |
| `weekly-alignment-audit.yml` | Design only. `sync_audit_issues.py` ran as a dry run on the 28 September ISSUES.csv (82 issues planned, none created). The agent step never ran |
| `docs-sync-caller.yml`, `docs-sync.yml` | Design only; never ran |
| `monthly-retro.yml` | Design only; never ran |
| All workflow files | `actionlint` 1.7.12 passes (shellcheck integration not available) |

## 1. Pin the harness

1. After this PR merges, take its merge commit SHA as `<HARNESS_SHA>`.
2. In every caller of the reusable workflow, replace `@main` with `@<HARNESS_SHA>` and add
   `with: harness_ref: <HARNESS_SHA>` (audit CI-001).
3. Replace `<HARNESS_SHA>` in each copied workflow from `rollout/workflows/`.

## 2. Secrets

| Secret | Scope | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`, then change the input name) | repositories audits, openamrobot-docs, .github | weekly audit, docs sync, monthly retro |
| `AUDIT_APP_ID`, `AUDIT_APP_PRIVATE_KEY` | repository audits | weekly audit, opening and closing finding issues |
| `DOCS_SYNC_APP_ID`, `DOCS_SYNC_APP_PRIVATE_KEY` | organization secret, all product repositories | docs sync sender (repository_dispatch to openamrobot-docs) |
| `RETRO_APP_ID`, `RETRO_APP_PRIVATE_KEY` | repository .github | monthly retro, reading issues and review comments |

The three App secret pairs may point to one GitHub App. The PR assistant needs no secret; it
uses `GITHUB_TOKEN`.

## 3. GitHub Apps

1. **Claude GitHub App** (github.com/apps/claude), installed on audits, openamrobot-docs and
   .github only. It requests Contents, Issues and Pull requests read and write; the current
   Claude Code documentation lists further permissions (Actions, Checks, Discussions,
   Workflows, Members, Statuses) because the App is shared with other Claude features. Grant
   what the install screen asks, on those three repositories only.
2. **Harness App** (organization-owned, private), installed on every product repository and
   audits, with: Issues read and write; Pull requests read; Contents read and write (needed
   only for `repository_dispatch` to openamrobot-docs); Metadata read. No administration,
   workflow or secrets permissions.

## 4. Actions settings

- Workflow permissions default: read repository contents only.
- Keep "Allow GitHub Actions to create and approve pull requests" off. No workflow here
  approves anything; the agents open PRs with the Claude App token.
- If the organization allow-lists actions, allow exactly: `actions/checkout`,
  `actions/upload-artifact`, `actions/create-github-app-token`,
  `anthropics/claude-code-action` (pinned in the files to v7.0.1, v7.0.1, v3.2.0 and
  v1.0.236 by commit SHA).
- Fork pull request workflows: require approval for first-time contributors.

## 5. Labels (every repository)

| Label | Used by |
|---|---|
| `harness` | harness mistake form, monthly retro |
| `good first issue` | good first issue form, CONTRIBUTING.md |
| `contract-change` | contract change request form |
| `audit-finding`, `blocker`, `major` | weekly audit issue sync |
| `triage`, `bug` | existing forms |
| `area:docs`, `area:navigation`, `area:interfaces`, `area:manipulation`, `area:ui`, `area:release`, `area:ci` | good first issue triage, CONTRIBUTING.md |

## 6. Branch protection on main (every active repository)

- Require a pull request; require CODEOWNERS review; require conversation resolution.
- Required status checks: `repository-quality / repository-quality`, `quality/pr-evidence`
  (after the PR assistant is installed), `quality/test` where the verify job is enabled; in
  .github also `quality/test` from `repository-quality.yml`.
- Block force pushes and deletions. Restrict bypass to the organization owner and record each
  bypass in the PR.
- Single-maintainer repositories: checks stay required; the CODEOWNERS-review waiver follows
  section 8 of the Engineering Quality Standard.

## 7. Maintainers map

Fill the `null` handles in `maintainers.yaml` (ci-owner, docs-owner) once the people have
confirmed their GitHub accounts and joined the organization. Until then, audit issues for
CI and DOC findings say "no handle recorded" and nobody is mentioned.
