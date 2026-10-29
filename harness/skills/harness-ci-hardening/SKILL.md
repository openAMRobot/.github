---
name: harness-ci-hardening
description: How to make every OpenAMRobot repository build and run all its tests in GitHub Actions reproducibly and quickly, using the organization's reusable workflow. Use for CI tasks, for issues like platform-sw #98, and when a repository is prepared for build missions.
---

# CI hardening

## Target state per repository
- The caller workflow uses openAMRobot/.github `repository-quality-reusable.yml` pinned to a harness SHA, with `verify: true` so `quality/test` runs (platform-sw issue #98 is this gap and PR #101 already enables it: never duplicate an open PR, review or build on it).
- A pinned, reproducible ROS 2 Jazzy image (by digest). .github PR #41 is a candidate image, not yet the adopted standard: use it only after its owner adopts it; until then `ros:jazzy-ros-base` by digest or `ros-tooling/setup-ros` pinned by SHA.
- PR jobs finish in about 10 minutes (Q-01): build, lint, unit and fast integration tests. Nightly: simulation scenarios, full launch tests, coverage. Weekly: audits.
- Results: `colcon test-result --all --verbose` output and per-package counts in the job summary; JUnit XML uploaded as artifact; zero executed tests fails the job.
- Caching: ccache and the rosdep apt cache keyed on package.xml hashes; never cache the install space across commits.
- Every action pinned to a full 40-character SHA with the version in a comment (check_workflow_policy.py). Least permissions: `contents: read` unless a step needs more. Timeouts and concurrency groups on every job.
- No secrets in product repositories. Fork PRs never get secrets; no `pull_request_target` with a checkout of head code.

## Path filters
Only filter paths that truly cannot affect the job. Configuration under `config/`, launch files and URDF affect tests; do not exclude them.

## Flaky tests
A job that fails then passes on rerun with the same SHA is a flake. Record it as needs-human:flaky with the run links; never add automatic retries to hide it.

## Changing workflows
Workflow files (`.github/workflows/**`, `.github/actions/**`) are tier D for agents everywhere: a workflow edited on a branch runs with that repository's secrets, so a person commits it. Agents still do the work around it: write the exact YAML in `.harness-out/needs-human.md` (status decision, sub-label needs-human:decision) with the reason, the expected run time and how to verify it, and make the repository's tests and verify.sh ready for it in a tier A or B PR.
