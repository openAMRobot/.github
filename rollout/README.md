# Rolling out the harness to other repositories

Files in this folder are proposals for other repositories. Each takes effect only when that
repository's owner merges it. The organization-owner steps are in
[workflows/SETUP.md](workflows/SETUP.md).

## What each repository adopts

| Item | What the repository does | Enforced by |
|---|---|---|
| AGENTS.md, CLAUDE.md | Copy the shared block v2 verbatim from `agent-rules/SHARED_RULES.md`, add a short repository-specific section; CLAUDE.md contains only `@AGENTS.md` | drift step in the reusable workflow |
| STATE.md | Copy `STATE.md.example`, fill it, keep it current | `check_pr_evidence.py` STATE.md rule |
| PR template | Delete the local `.github/PULL_REQUEST_TEMPLATE.md` so the organization template applies, or replace it with a copy that keeps every heading | `check_pr_evidence.py` sections |
| verify.sh | Keep an existing `tools/verify.sh`; otherwise enable `verify: true` in the caller (the harness `rollout/verify.sh` runs), with `.openamrobot/verify.env` if the layout needs it | `quality/test` job |
| Reusable workflow caller | Pin `uses:` and `harness_ref` to one harness SHA | reviewer of the caller PR |
| PR assistant | Copy `workflows/pr-assistant.yml` | `quality/pr-evidence` required check |
| Docs sync sender | Copy `workflows/docs-sync-caller.yml` (not in openamrobot-docs) | none; failure shows in Actions |
| decisions.yaml | Nothing to copy. Fix flagged lines or mark kept history with `decision-allow: <ID> <reason>` | `check_decisions.py` |

All eight product repositories checked on 29 September 2026 carry a local PR template
(openamr-platform-fw, openamr-platform-sw, openamrobot-docs, openamrobot-interfaces,
openamrobot-manifest, openamrobot-manipulation, openamrobot-release, openamrobot-ui). A local
template overrides the organization one, so "inherited" requires deleting it.

## Order

Each step is one PR per repository, opened as a draft by the repository owner or with the
push-from-bundle prompt, and merged by the owner.

1. **This PR merges; the owner completes SETUP.md sections 1 to 4.**
2. **Shared block v2, same day, in the three repositories that already carry v1**
   (openamrobot-manifest, openamrobot-manipulation, openamrobot-ui). Until they update, the
   drift step fails their pull requests with "shared block is v1, canonical is v2". A caller
   pinned to a pre-v2 harness SHA is not affected.
3. **Pin callers** in all repositories (audit CI-001, SW-022).
4. **Pilots, in this order**, each with STATE.md, the organization PR template, the PR
   assistant and `verify: true`:
   1. openamrobot-interfaces: already has `tools/verify.sh`; the job delegates to it.
   2. openamr-platform-sw: first colcon build and test gate (audit CI-005); container
      `ros:jazzy-ros-base`.
   3. openamrobot-ui: `.openamrobot/verify.env` as in VERIFY.md; the zero-tests rule fails
      until real tests replace `--passWithNoTests` (CI-006). Merge the verify.env PR together
      with the first real tests.
   4. openamrobot-docs: keep `scripts/check_docs.sh` and the strict MkDocs build via
      `VERIFY_TEST`; add the docs-sync receiver.
5. **openamrobot-manifest and openamrobot-release** (release owner). See the release
   interaction below.
6. **openamr-platform-fw, openamr-platform-hw, openamr-upperbody-*, openamrobot-comm**: shared
   block, STATE.md, PR assistant. `verify: true` only once a build or test exists; a
   repository with nothing to test declares that in STATE.md instead of passing an empty suite.
7. **Branch protection** per SETUP.md section 6, repository by repository, after its
   checks have passed on main once.
8. **Weekly audit** in audits, then **monthly retro** in .github.

## Release-manifest interaction

- The release builder packages what the manifest names. A release PR in
  openamrobot-release runs the same decisions check on release notes and metadata (today it
  flags "Raspberry Pi 5" in `release-metadata/RELEASE_NOTES.md`).
- The release manifest should record the harness SHA used for each component's evidence, and
  each component's `summary.json` from its `quality/test` artifact, so release evidence points
  at a verification run instead of a claim.
- A change to decisions.yaml can turn a component red without a code change. The release
  owner treats that as a release blocker for the affected component, not as a CI fault.

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
```

A CODEOWNERS line with an account that is not a collaborator is ignored by GitHub, so the
pending handles must join the organization before their lines are added.
