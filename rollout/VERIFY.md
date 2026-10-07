# verify.sh: reference verification script

`rollout/verify.sh` is the verification entry point for repositories that do not have their
own. A repository that already has `tools/verify.sh` keeps it: the script detects it and
delegates. openamrobot-interfaces is the reference implementation and is not duplicated here.
Delegation still produces the same `summary.json` (see "Evidence summary" below), written
around the delegated run.

## What it runs

| Stage | Default action | Fails when |
|---|---|---|
| prerequisites | detect ROS 2 (`package.xml`), Node (`package.json`), Python (`tests/`, `pyproject.toml`, `setup.py`) | nothing is detected and no `VERIFY_TEST` is set |
| install | `npm ci`, or `rosdep check` for ROS 2 on the source packages only (never `build/`, `install/`, `log/` or a `COLCON_IGNORE` folder) | a dependency does not resolve |
| build | `colcon build` in a copied workspace, or `npm run build` | the build fails |
| lint | `py_compile` for tracked Python, `bash -n` (and `shellcheck` when installed) for shell, `npm run lint` | any file fails |
| test-markers | scan tracked test sources | a skip, xfail or importorskip does not name an issue (`#123` or `issues/123`) on the same line |
| test | `colcon test` and `colcon test-result`, `npm test`, `pytest` or `unittest` | a test fails, or zero tests executed (total minus skipped is zero) |
| evidence | keep logs | never |

When delegating, verify.sh runs `tools/verify.sh`, captures its combined output in
`verification.log`, records its exit status and duration, parses test counts from the output
with the same parsers, records the `Evidence:` path the delegated script prints, writes
`summary.json` and exits with the delegated exit status. It does not apply the zero-tests or
skip rules to a delegated run; those remain the delegated script's responsibility, and
`counts_parsed: false` shows when no count could be read.

Every stage runs under `env -i` with a fresh `HOME`, as in the interfaces script, so no overlay,
Python path or user package leaks in. The one exception is rosdep's prepared state: the caller's
`${ROS_HOME:-$HOME/.ros}/rosdep` (user sources list and cache) is copied into the fresh `HOME`, and
`ROSDEP_SOURCE_PATH` is passed through when set, so `rosdep check` does not report an
uninitialised rosdep. Output goes to `.verification/run.*/`:
`verification.log`, `test.log`, `result.txt` (PASS, or FAIL with the stage) and `summary.json`
(result, failed stage, stages passed, test totals, head and base SHA).

## Evidence summary (minimum schema)

Every run, delegated or not, writes `.verification/run.*/summary.json` with at least these
fields. A repository-native verifier that writes its own evidence adds these fields or is
wrapped by verify.sh; a release consumes only this schema. If `summary.json` cannot be
written, the run fails: an otherwise passing run exits 1 with `FAIL: evidence-summary`, and a
failing run (delegated or not) keeps its own exit status.

| Field | Meaning |
|---|---|
| `schema_version` | `1` |
| `mode` | `harness` (verify.sh ran the stages) or `delegated` (the repository's `tools/verify.sh` ran) |
| `result`, `exit_code` | `PASS` only when `exit_code` is 0; the exit status the job reported |
| `failed_stage` | stage name, or `tools/verify.sh` for a delegated failure; null on success |
| `stages_passed` | stages verify.sh completed (empty when delegated) |
| `tests_total`, `tests_skipped`, `counts_parsed` | counts parsed from the test output; null with `counts_parsed: false` when none could be read |
| `duration_seconds` | wall time of the whole run |
| `head_sha`, `base_sha` | component commit verified and its merge base with main |
| `harness_sha` | commit of the harness that provided verify.sh |
| `delegated_script`, `delegated_evidence` | for delegated runs, the script and the evidence path it printed |

The workflow run URL and the artifact digest are not known inside the run; the release
record adds them (rollout/README.md, release section).

## Overrides

`.openamrobot/verify.env` in the repository may set shell commands `VERIFY_INSTALL`,
`VERIFY_BUILD`, `VERIFY_LINT`, `VERIFY_TEST`, and `VERIFY_ROS_DISTRO` (default `jazzy`);
`VERIFY_ROS_SETUP` replaces the ROS setup file (default `/opt/ros/$VERIFY_ROS_DISTRO/setup.bash`).
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
