# Rolling out the harness to other repositories

Files in this folder are proposals for other repositories. Each takes effect only when that
repository's owner merges it, and a check blocks a merge only once the repository's ruleset
requires it. Until a repository completes the steps below, none of its failure classes are
machine-blocked. The organization-owner steps and the state of every check are in
[workflows/SETUP.md](workflows/SETUP.md).

## What each repository adopts

| Item | What the repository does | Checked by, once installed and required |
|---|---|---|
| AGENTS.md, CLAUDE.md | Copy the shared block v2 verbatim from `agent-rules/SHARED_RULES.md`, add a short repository-specific section; CLAUDE.md contains only `@AGENTS.md` | drift step in the reusable workflow |
| STATE.md | Copy `STATE.md.example`, fill it, keep it current | `check_pr_evidence.py` STATE.md rule |
| PR template | Delete the local `.github/PULL_REQUEST_TEMPLATE.md` so the organization template applies, or replace it with a copy that keeps every heading | `check_pr_evidence.py` sections |
| verify.sh | Keep an existing `tools/verify.sh`; otherwise enable `verify: true` in the caller (the harness `rollout/verify.sh` runs), with `.openamrobot/verify.env` if the layout needs it | `quality/test` job |
| Reusable workflow caller | Pin `uses:` and `harness_ref` to one harness SHA; then `harness_warn: true`; then `harness_checks: true` (steps b to d below) | reviewer of the caller PR |
| PR assistant | Copy `workflows/pr-assistant.yml` | `quality/pr-evidence` required check |
| Docs sync sender | Copy `workflows/docs-sync-caller.yml` (not in openamrobot-docs) | none; failure shows in Actions |
| decisions register | Nothing to copy; CI reads the pinned register from the harness. Fix flagged lines or mark kept history with `decision-allow: <ID> <reason>` | `check_decisions.py` (text only; the entry's reviewer checks the substance) |

All eight product repositories checked on 29 September 2026 carry a local PR template
(openamr-platform-fw, openamr-platform-sw, openamrobot-docs, openamrobot-interfaces,
openamrobot-manifest, openamrobot-manipulation, openamrobot-release, openamrobot-ui). A local
template overrides the organization one, so "inherited" requires deleting it.

## Order

**Before any repository starts:** this PR merges, and the organization owner completes
SETUP.md sections 2 to 5 (secrets, Apps, Actions settings, labels). SETUP.md section 1
(pinning) is not done organization-wide; each repository pins in its own step (b).

**Per repository, strictly in this order.** Each step is one PR in that repository, opened as a
draft by the repository owner (or with the push-from-bundle prompt) and merged by the owner.
A step starts only after the previous one is merged.

| Step | Change in the repository | Done when |
|---|---|---|
| (a) Shared rules v2 | AGENTS.md carries the shared block v2 verbatim; CLAUDE.md is `@AGENTS.md`; STATE.md added; local PR template removed or aligned | the drift checker passes on the repository's AGENTS.md |
| (b) Pin the harness | caller `uses: openAMRobot/.github/...@<HARNESS_SHA>` and `harness_ref: <HARNESS_SHA>`; `harness_checks` stays unset (false) | the caller runs the baseline steps at the pinned SHA |
| (c) Warn-only | add `harness_warn: true`; the decisions, public-extract and drift steps run and report findings as warnings, never failing | one push run on main is green with every remaining warning either fixed, tracked in an issue, or marked `decision-allow` |
| (d) Enforce | replace `harness_warn: true` with `harness_checks: true` | one enforced run on main is green and one PR passes with the checks enforced |
| (e) Require | the ruleset requires `repository-quality / repository-quality` (and `quality/pr-evidence`, `quality/test` once installed), per SETUP.md section 6 | a PR merges through the ruleset |

Only from step (e) does a failing check block a merge in that repository. Safety-path
approvals come from the ruleset and CODEOWNERS, not from a check.

### Pilot: openamrobot-interfaces first

openamrobot-interfaces completes steps (a) to (e) before any other repository sets
`harness_warn` or `harness_checks`. It also installs the PR assistant and `verify: true`
(the job delegates to its existing `tools/verify.sh`). The pilot is complete when all of the
following are recorded in its STATE.md and in one comment on the harness rollout issue, and the
CI owner and the release owner have both written "pilot accepted" there:

1. The five step PRs, linked in order.
2. The run URLs of a green warn-only run on main and a green enforced run on main.
3. An enforced PR run that blocked a deliberate contradiction on a throwaway branch (never
   merged) and a clean PR that passed.
4. A `quality/test` artifact produced through delegation, whose `summary.json` records the
   delegated exit status, duration and test counts.
5. One PR-assistant summary comment updated in place across two pushes, with no CHECKER ERROR
   on a normal PR.
6. A PR merged through the ruleset that requires the checks.
7. No check or register pattern weakened to get green; any false positive fixed in the harness
   with a test.
8. A rollback shown: reverting the caller to the previous pin restores the previous behaviour.

If a criterion fails, the rollout stops, the finding becomes an issue labelled harness, and the
pilot repeats the failed step after the harness fix.

### After the pilot

The remaining repositories follow steps (a) to (e), one repository at a time:

1. openamrobot-manifest, openamrobot-manipulation, openamrobot-ui (they already carry the v1
   block, so step (a) is an update). openamrobot-ui adds `.openamrobot/verify.env` as in
   VERIFY.md; its zero-tests rule fails until real tests replace `--passWithNoTests`, so the
   verify.env PR merges together with the first real tests.
2. openamr-platform-sw: first colcon build and test gate; container `ros:jazzy-ros-base`.
3. openamrobot-docs: keeps `scripts/check_docs.sh` and the strict MkDocs build via
   `VERIFY_TEST`; adds the docs-sync receiver.
4. openamrobot-release (release owner). See the release interaction below.
5. openamr-platform-fw, openamr-platform-hw, openamr-upperbody-*, openamrobot-comm.
   `verify: true` only once a build or test exists; a repository with nothing to test declares
   that in STATE.md instead of passing an empty suite.
6. Weekly audit in audits, then monthly retro in .github. Both are designs until a first
   supervised run exercises permissions, credentials, deduplication, failure handling and the
   issue lifecycle; the audit never closes an issue, it comments "no longer detected".

## Release-manifest interaction

- The release builder packages what the manifest names. A release PR in
  openamrobot-release runs the same decisions check on release notes and metadata (today it
  flags the legacy compute named in `release-metadata/RELEASE_NOTES.md`, decision COMPUTE).
- **Evidence record per component.** For every component in a release, the release manifest
  records:

  | Field | Source |
  |---|---|
  | component commit SHA | the manifest pin; must equal `head_sha` in the component's `summary.json` |
  | package or contract version | `package.xml` / `package.json` version, or the interface contract version, where one exists; otherwise "none" |
  | harness SHA | `harness_sha` in `summary.json`; must equal the component's `harness_ref` pin |
  | workflow run URL | the `quality/test` run that produced the artifact |
  | artifact identifier or digest | the Actions artifact ID and its SHA-256 digest (the upload step prints both) |

  The `summary.json` schema is in VERIFY.md. It is written for delegated runs too, so
  openamrobot-interfaces (which keeps its own `tools/verify.sh`) produces the same record.
- **Decision-register updates and pinned consumers.** A component is checked against the
  register at its harness pin. A register update affects a pinned consumer only when that
  consumer moves its harness pin, or when the release owner explicitly revalidates it against
  the new register (a new `quality/test` run recorded as new evidence). Until then its recorded
  evidence stands for the pin it names.
- **Historical evidence is preserved as recorded.** Release evidence is never regenerated or
  edited after a release; a later register change or harness update produces new evidence for
  a later release, and the earlier record keeps its original SHAs, run URL and digest.
- A register update that makes a revalidated component fail is a release blocker for that
  component in the next release, not a CI fault and not a change to past releases.

## CODEOWNERS proposal

Not applied by this PR; CODEOWNERS changes need an explicit task and the platform lead's
review. Proposal, in every repository's `.github/CODEOWNERS`:

```
# Default owner stays.
* @BotshareAI

# Software repositories (openamr-platform-sw, openamr-upperbody-sw, openamrobot-interfaces,
# openamrobot-manipulation, openamrobot-ui, openamrobot-comm): add the software lead.
* @BotshareAI @panthera-momagdii

# Every repository: CI owner for workflows. Handle to be confirmed (maintainers.yaml ci-owner).
/.github/workflows/ @BotshareAI <ci-owner handle>

# openamrobot-docs only: documentation owner. Handle to be confirmed (maintainers.yaml docs-owner).
* @BotshareAI <docs-owner handle>

# openAMRobot/.github only: policy and harness files.
/decisions.yaml @BotshareAI
/maintainers.yaml @BotshareAI
/agent-rules/ @BotshareAI @panthera-momagdii
/tools/ @BotshareAI <ci-owner handle>

# Release owner (maintainers.yaml release-owner: KARTHIKEYAN124). Replace the handle with
# @KARTHIKEYAN124 @wikki26 once that team exists. Added only after write access is confirmed.
# openamrobot-manifest and openamrobot-release: whole repository.
* @BotshareAI @KARTHIKEYAN124
# openamrobot-release: release workflow (after the lines above, so it wins for this path).
/.github/workflows/build-release.yml @BotshareAI @KARTHIKEYAN124
# openamrobot-manifest: manifest validation workflow.
/.github/workflows/manifest-validation.yml @BotshareAI @KARTHIKEYAN124
# openamrobot-docs: installation documentation, placed after the docs-owner line.
/docs/build/software/ @BotshareAI <docs-owner handle> @KARTHIKEYAN124
/docs/reference/openamrobot-manifest/ @BotshareAI <docs-owner handle> @KARTHIKEYAN124
/docs/reference/openamrobot-release/ @BotshareAI <docs-owner handle> @KARTHIKEYAN124
```

The release workflow lines matter because the "every repository" CI owner line for
`/.github/workflows/` would otherwise route those files away from the release owner; they
must appear after it. The installation paths are the pages in openamrobot-docs today that
tell a user how to build, flash and verify an installation (`docs/build/software/`) and the
setup pages of the two release repositories; the docs owner confirms the list when the file
is written.

How GitHub applies these lines (documented GitHub behaviour, not something this harness
checks):

- A code owner must have write access to the repository for the ownership to take effect.
  A line whose account or team lacks write access, or is not a collaborator, is ignored for
  review requests and required approvals, so the release owner's access is confirmed first.
  The same holds for the pending ci-owner and docs-owner handles.
- The last matching pattern in the file takes precedence. A later line replaces the owners of
  an earlier line for the paths it matches; owners are not merged across lines. Specific paths
  therefore go after the broad `*` and `/.github/workflows/` lines, and each specific line
  repeats every owner it still needs.
- When a line lists several owners, an approval from any one of them satisfies the code owner
  requirement; approval from all of them is not required. A ruleset can add further
  requirements (a minimum approval count, a required team review), and only the ruleset does.
- This repository's own `.github/CODEOWNERS` is a single line, `* @wikki26 @BotshareAI
  @panthera-momagdii`: an approval from any one of the three satisfies the code-owner
  requirement for every path. GitHub never counts the author's own approval, so a PR authored
  by one of them still needs the approval of one of the other two. Each listed account needs
  write access to this repository for the entry to count.
