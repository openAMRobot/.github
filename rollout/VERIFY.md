# verify.sh: reference verification script

`rollout/verify.sh` is the verification entry point for repositories that do not have their
own. A repository that already has `tools/verify.sh` keeps it: the script detects it and
delegates. openamrobot-interfaces is the reference implementation and is not duplicated here.

## What it runs

| Stage | Default action | Fails when |
|---|---|---|
| prerequisites | detect ROS 2 (`package.xml`), Node (`package.json`), Python (`tests/`, `pyproject.toml`, `setup.py`) | nothing is detected and no `VERIFY_TEST` is set |
| install | `npm ci`, or `rosdep check` for ROS 2 | a dependency does not resolve |
| build | `colcon build` in a copied workspace, or `npm run build` | the build fails |
| lint | `py_compile` for tracked Python, `bash -n` (and `shellcheck` when installed) for shell, `npm run lint` | any file fails |
| test-markers | scan tracked test sources | a skip, xfail or importorskip does not name an issue (`#123` or `issues/123`) on the same line |
| test | `colcon test` and `colcon test-result`, `npm test`, `pytest` or `unittest` | a test fails, or zero tests executed (total minus skipped is zero) |
| evidence | keep logs | never |

Every stage runs under `env -i` with a fresh `HOME`, as in the interfaces script, so no overlay,
Python path or user package leaks in. Output goes to `.verification/run.*/`:
`verification.log`, `test.log`, `result.txt` (PASS, or FAIL with the stage) and `summary.json`
(result, failed stage, stages passed, test totals, head and base SHA).

## Overrides

`.openamrobot/verify.env` in the repository may set shell commands `VERIFY_INSTALL`,
`VERIFY_BUILD`, `VERIFY_LINT`, `VERIFY_TEST`, and `VERIFY_ROS_DISTRO` (default `jazzy`).
Overrides replace a stage's command; they do not switch off the zero-tests or skip rules.
Example for openamrobot-ui, whose web app lives in `web/`:

```
VERIFY_INSTALL="cd web && npm ci"
VERIFY_BUILD="cd web && npm run build"
VERIFY_LINT="cd web && npx eslint src"
VERIFY_TEST="cd web && CI=true npm test -- --watchAll=false"
```

With that override the UI's current `--passWithNoTests` suite fails the zero-tests rule
until real tests exist.

## How the reusable workflow calls it

`repository-quality-reusable.yml` has an opt-in job `quality/test`:

```yaml
jobs:
  repository-quality:
    uses: openAMRobot/.github/.github/workflows/repository-quality-reusable.yml@<HARNESS_SHA>
    with:
      harness_ref: <HARNESS_SHA>
      verify: true
      verify_container: ros:jazzy-ros-base   # ROS 2 repositories only
```

The job checks out the repository and the harness at `harness_ref`, runs
`.openamrobot-harness/rollout/verify.sh "$GITHUB_WORKSPACE"` (which delegates to
`tools/verify.sh` when present) and uploads `.verification/run.*/` as the artifact
`verification-evidence`. The PR evidence section links that artifact.

## Run locally

```
bash /path/to/openAMRobot/.github/rollout/verify.sh /path/to/repository
```

The tests in `tests/test_verify_sh.py` exercise the passing path, zero tests, a fully skipped
suite, a skip without an issue, a skip with an issue, nothing detected, and delegation.
