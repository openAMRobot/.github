#!/usr/bin/env bash
# OpenAMRobot reference verification: install, build, lint, test, evidence.
#
# Usage: verify.sh [REPOSITORY_ROOT]   (default: the git top level of the current directory)
#
# Follows openamrobot-interfaces/tools/verify.sh: every stage runs in a clean
# environment, all output goes to .verification/run.*/verification.log, and
# result.txt says PASS or FAIL with the failing stage. This script adds:
#   - project detection: ROS 2 (colcon), Node (npm), Python (unittest or pytest);
#   - the zero-tests rule: a test stage that executes zero tests fails;
#   - the skip rule: skip, xfail and importorskip must name a tracking issue
#     (#123 or an issues/123 URL) on the same line;
#   - summary.json (schema in rollout/VERIFY.md) with result, exit code, duration,
#     test counts, head/base SHA and the harness SHA.
# A repository that already has tools/verify.sh keeps it; this script delegates
# to it (openamrobot-interfaces is the reference implementation) and still writes
# summary.json around the delegated run: exit status, duration and test counts
# parsed from the delegated output.
# Per-repository overrides live in .openamrobot/verify.env (VERIFY_INSTALL,
# VERIFY_BUILD, VERIFY_LINT, VERIFY_TEST, VERIFY_ROS_DISTRO); each is a shell command.
# VERIFY_ROS_SETUP overrides the ROS setup file (default /opt/ros/$VERIFY_ROS_DISTRO/setup.bash).
set -eo pipefail

root=$(cd -- "${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}" && pwd)
self=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")
started=$(date +%s)

# Print "total skipped parsed" for a test log (parsed is 1 when any known runner summary matched).
count_tests() {
  python3 - "$1" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
total = skipped = 0
parsed = False
for pattern, t, s in [
    (r"Summary: (\d+) tests?, \d+ errors?, \d+ failures?, (\d+) skipped", 1, 2),  # colcon test-result
    (r"^Ran (\d+) tests? in", 1, None),                                              # unittest
    (r"^Tests:\s+(?:.*?(\d+) skipped, )?.*?(\d+) total", 2, 1),                     # jest
    (r"^\s+Tests\s+(?:.*?(\d+) skipped.*?)?\((\d+)\)", 2, 1),                        # vitest
]:
    for m in re.finditer(pattern, text, re.M):
        parsed = True
        total += int(m.group(t) or 0)
        skipped += int(m.group(s) or 0) if s else 0
m = re.findall(r"=+ (?:(\d+) passed)?(?:, )?(?:(\d+) skipped)?.* in [\d.]+s", text)  # pytest
for passed, skip in m:
    parsed = True
    total += int(passed or 0) + int(skip or 0)
    skipped += int(skip or 0)
skipped += sum(int(n) for n in re.findall(r"skipped=(\d+)", text))  # unittest
print(total, skipped, 1 if parsed else 0)
PY
}

# Write summary.json (minimum evidence schema, rollout/VERIFY.md). Arguments:
# run mode exit_code failed_stage tests_total tests_skipped counts_parsed delegated_script delegated_evidence stages...
# Returns non-zero when summary.json cannot be written; callers fail the run on that.
write_summary() {
  python3 - "$root" "$self" "$started" "$@" <<'PY'
import json, subprocess, sys, time
root, self_path, started, run, mode, code, failed, total, skipped, parsed, dscript, devidence, *done = sys.argv[1:]
def git(where, *a):
    try:
        return subprocess.run(["git", "-C", where, *a], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None
import os
json.dump({
    "schema_version": 1,
    "mode": mode,
    "result": "PASS" if code == "0" else "FAIL",
    "exit_code": int(code),
    "failed_stage": None if code == "0" else (failed or None),
    "stages_passed": done,
    "tests_total": int(total) if parsed == "1" else None,
    "tests_skipped": int(skipped) if parsed == "1" else None,
    "counts_parsed": parsed == "1",
    "duration_seconds": int(time.time()) - int(started),
    "head_sha": git(root, "rev-parse", "HEAD"),
    "base_sha": git(root, "merge-base", "HEAD", "origin/main"),
    "harness_sha": git(os.path.dirname(self_path), "rev-parse", "HEAD"),
    "delegated_script": dscript or None,
    "delegated_evidence": devidence or None,
}, open(f"{run}/summary.json", "w"), indent=2)
PY
}

mkdir -p "$root/.verification"
run=$(mktemp -d "$root/.verification/run.XXXXXX")

if [ -f "$root/tools/verify.sh" ] && [ "$root/tools/verify.sh" != "$self" ] && [ -z "${VERIFY_NO_DELEGATE:-}" ]; then
  # Delegate, but keep the evidence: capture output, exit status, duration and counts.
  echo "Delegating to the repository's own tools/verify.sh"
  set +e
  bash "$root/tools/verify.sh" 2>&1 | tee "$run/verification.log"
  status=${PIPESTATUS[0]}
  set -e
  read -r d_total d_skipped d_parsed < <(count_tests "$run/verification.log")
  d_evidence=$(sed -n 's/^Evidence: //p' "$run/verification.log" | tail -1)
  if ! write_summary "$run" delegated "$status" "tools/verify.sh" "$d_total" "$d_skipped" "$d_parsed" \
      "tools/verify.sh" "$d_evidence"; then
    echo "FAIL: could not write $run/summary.json"
    # Keep a delegated failure status; turn a delegated success into a failure.
    if [ "$status" -eq 0 ]; then status=1; fi
    echo "FAIL: delegated tools/verify.sh (exit $status; summary.json not written)" | tee "$run/result.txt"
    echo "Evidence: $run"
    exit "$status"
  fi
  if [ "$status" -eq 0 ]; then
    echo "PASS: delegated tools/verify.sh" | tee "$run/result.txt"
  else
    echo "FAIL: delegated tools/verify.sh (exit $status)" | tee "$run/result.txt"
  fi
  echo "Evidence: $run"
  exit "$status"
fi

exec > >(tee "$run/verification.log") 2>&1
stage=prerequisites
stages=()
tests_total=0
tests_skipped=0
counts_parsed=0

finish() {
  result=$?
  if ! write_summary "$run" harness "$result" "$stage" "$tests_total" "$tests_skipped" "$counts_parsed" "" "" \
      "${stages[@]}"; then
    echo "FAIL: could not write $run/summary.json"
    # A run without its evidence summary never passes; an earlier failure keeps its status.
    if [ "$result" -eq 0 ]; then result=1; stage=evidence-summary; fi
  fi
  if [ "$result" -eq 0 ]; then
    echo "PASS: all detected verification stages" | tee "$run/result.txt"
  else
    echo "FAIL: $stage (exit $result)" | tee "$run/result.txt"
  fi
  echo "Evidence: $run"
  exit "$result"
}
trap finish EXIT

pass() { stages+=("$stage"); echo "PASS: $stage"; }

# Never inherit overlays, Python paths or prefixes from the caller. The only caller
# state passed in is rosdep's: ROSDEP_SOURCE_PATH when set, and a copy of the caller's
# rosdep sources list and cache (below).
clean_bash() {
  env -i HOME="$run/home" PATH="${VERIFY_PATH:-/usr/local/bin:/usr/bin:/bin}" LANG=C.UTF-8 \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 CI="${CI:-}" \
    ${ROSDEP_SOURCE_PATH:+"ROSDEP_SOURCE_PATH=$ROSDEP_SOURCE_PATH"} \
    bash --noprofile --norc -eo pipefail "$@"
}
mkdir -p "$run/home"
# rosdep keeps its user sources list and cache under ${ROS_HOME:-$HOME/.ros}/rosdep. The
# clean HOME would hide the state the environment prepared ("rosdep not initialized"), so
# copy it in; a copy keeps the caller's cache unchanged by the run.
caller_rosdep="${ROS_HOME:-${HOME:-/nonexistent}/.ros}/rosdep"
if [ -d "$caller_rosdep" ]; then
  mkdir -p "$run/home/.ros" && cp -a "$caller_rosdep" "$run/home/.ros/rosdep"
fi

if [ -f "$root/.openamrobot/verify.env" ]; then
  # shellcheck disable=SC1091
  source "$root/.openamrobot/verify.env"
fi
distro=${VERIFY_ROS_DISTRO:-jazzy}
ros_setup=${VERIFY_ROS_SETUP:-/opt/ros/$distro/setup.bash}

ros=false; node=false; python=false
if find "$root" -name package.xml -not -path '*/node_modules/*' -not -path '*/.verification/*' \
    -not -path '*/tests/fixtures/*' | grep -q .; then ros=true; fi
[ -f "$root/package.json" ] && node=true
if [ -f "$root/pyproject.toml" ] || [ -f "$root/setup.py" ] || [ -d "$root/tests" ]; then python=true; fi
echo "Detected: ros=$ros node=$node python=$python"
command -v git python3 >/dev/null
if $ros; then test -f "$ros_setup"; fi
if $node; then command -v npm >/dev/null; fi
if ! $ros && ! $node && ! $python && [ -z "${VERIFY_TEST:-}" ]; then
  echo "FAIL: no buildable or testable project detected; set VERIFY_TEST in .openamrobot/verify.env"
  exit 1
fi
pass

stage=install
if [ -n "${VERIFY_INSTALL:-}" ]; then clean_bash -c "cd '$root' && $VERIFY_INSTALL"
elif $node; then clean_bash -c "cd '$root' && npm ci"
elif $ros; then
  clean_bash -c "source '$ros_setup' && rosdep check --from-paths '$root' --ignore-src --rosdistro $distro"
fi
pass

stage=build
if [ -n "${VERIFY_BUILD:-}" ]; then clean_bash -c "cd '$root' && $VERIFY_BUILD"
elif $ros; then
  mkdir -p "$run/ws/src" && cp -a "$root/." "$run/ws/src/repo" && rm -rf "$run/ws/src/repo/.verification"
  clean_bash -c "source '$ros_setup' && cd '$run/ws' && colcon build --event-handlers console_direct+"
elif $node; then clean_bash -c "cd '$root' && npm run build --if-present"
fi
pass

stage=lint
if [ -n "${VERIFY_LINT:-}" ]; then clean_bash -c "cd '$root' && $VERIFY_LINT"
else
  git -C "$root" ls-files -z '*.py' | (cd "$root" && xargs -0 -r python3 -m py_compile)
  git -C "$root" ls-files -z '*.sh' | (cd "$root" && xargs -0 -r -n1 bash -n)
  if command -v shellcheck >/dev/null; then
    git -C "$root" ls-files -z '*.sh' | (cd "$root" && xargs -0 -r shellcheck -S warning)
  fi
  if $node; then clean_bash -c "cd '$root' && npm run lint --if-present"; fi
fi
pass

stage=test-markers
# Every skip, xfail or importorskip names a tracking issue on the same line.
unmarked=$(cd "$root" && git ls-files -z -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' '*.cpp' '*.hpp' '*.c' '*.h' \
  | xargs -0 -r grep -nE '(pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail|importorskip)\(|unittest\.skip|self\.skipTest\(|\b(it|test|describe)\.skip\(|\bxit\(|GTEST_SKIP)' 2>/dev/null \
  | grep -vE '(#[0-9]+|issues/[0-9]+)' || true)
if [ -n "$unmarked" ]; then
  echo "$unmarked"
  echo "FAIL: skip/xfail/importorskip without a tracking issue (#123 or issues/123) on the same line"
  exit 1
fi
pass

stage="test"
log="$run/test.log"
# Run the suite without aborting on its exit status: the zero-tests rule is
# checked first (Python 3.12+ unittest exits 5 on "NO TESTS RAN"), then any
# non-zero status fails the stage.
set +e
if [ -n "${VERIFY_TEST:-}" ]; then clean_bash -c "cd '$root' && $VERIFY_TEST" 2>&1 | tee "$log"
elif $ros; then
  clean_bash -c "source '$ros_setup' && cd '$run/ws' && colcon test --event-handlers console_direct+ && colcon test-result --verbose" 2>&1 | tee "$log"
elif $node; then clean_bash -c "cd '$root' && npm test" 2>&1 | tee "$log"
elif [ -f "$root/pyproject.toml" ] && python3 -c 'import pytest' 2>/dev/null; then
  clean_bash -c "cd '$root' && python3 -m pytest -rs" 2>&1 | tee "$log"
else
  clean_bash -c "cd '$root' && python3 -m unittest discover -s tests -v" 2>&1 | tee "$log"
fi
test_status=${PIPESTATUS[0]}
set -e
read -r tests_total tests_skipped counts_parsed < <(count_tests "$log")
echo "Tests executed: $((tests_total - tests_skipped)) of $tests_total (skipped $tests_skipped)"
if [ "$((tests_total - tests_skipped))" -le 0 ]; then
  echo "FAIL: zero tests executed; an empty or fully skipped suite is not evidence"
  exit 1
fi
if [ "$test_status" -ne 0 ]; then
  echo "FAIL: test command exited with status $test_status"
  exit "$test_status"
fi
pass

stage=evidence
cp "$log" "$run/test-output.log" 2>/dev/null || true
pass
