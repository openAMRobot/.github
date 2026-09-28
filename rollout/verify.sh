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
#   - summary.json with base/head SHA, stage results and test counts.
# A repository that already has tools/verify.sh keeps it; this script delegates
# to it (openamrobot-interfaces is the reference implementation).
# Per-repository overrides live in .openamrobot/verify.env (VERIFY_INSTALL,
# VERIFY_BUILD, VERIFY_LINT, VERIFY_TEST, VERIFY_ROS_DISTRO); each is a shell command.
set -eo pipefail

root=$(cd -- "${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}" && pwd)
self=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")
if [ -f "$root/tools/verify.sh" ] && [ "$root/tools/verify.sh" != "$self" ] && [ -z "${VERIFY_NO_DELEGATE:-}" ]; then
  echo "Delegating to the repository's own tools/verify.sh"
  exec bash "$root/tools/verify.sh"
fi

mkdir -p "$root/.verification"
run=$(mktemp -d "$root/.verification/run.XXXXXX")
exec > >(tee "$run/verification.log") 2>&1
stage=prerequisites
stages=()
tests_total=0
tests_skipped=0

finish() {
  result=$?
  if [ "$result" -eq 0 ]; then
    echo "PASS: all detected verification stages" | tee "$run/result.txt"
  else
    echo "FAIL: $stage (exit $result)" | tee "$run/result.txt"
  fi
  python3 - "$run" "$root" "$result" "$stage" "$tests_total" "$tests_skipped" "${stages[@]}" <<'PY' || true
import json, subprocess, sys
run, root, result, stage, total, skipped, *done = sys.argv[1:]
def git(*a):
    try:
        return subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None
json.dump({
    "result": "PASS" if result == "0" else "FAIL",
    "failed_stage": None if result == "0" else stage,
    "stages_passed": done,
    "tests_total": int(total), "tests_skipped": int(skipped),
    "head_sha": git("rev-parse", "HEAD"),
    "base_sha": git("merge-base", "HEAD", "origin/main"),
}, open(f"{run}/summary.json", "w"), indent=2)
PY
  echo "Evidence: $run"
  exit "$result"
}
trap finish EXIT

pass() { stages+=("$stage"); echo "PASS: $stage"; }

# Never inherit overlays, Python paths or prefixes from the caller.
clean_bash() {
  env -i HOME="$run/home" PATH="${VERIFY_PATH:-/usr/local/bin:/usr/bin:/bin}" LANG=C.UTF-8 \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 CI="${CI:-}" \
    bash --noprofile --norc -eo pipefail "$@"
}
mkdir -p "$run/home"

if [ -f "$root/.openamrobot/verify.env" ]; then
  # shellcheck disable=SC1091
  source "$root/.openamrobot/verify.env"
fi
distro=${VERIFY_ROS_DISTRO:-jazzy}

ros=false; node=false; python=false
if find "$root" -name package.xml -not -path '*/node_modules/*' -not -path '*/.verification/*' \
    -not -path '*/tests/fixtures/*' | grep -q .; then ros=true; fi
[ -f "$root/package.json" ] && node=true
if [ -f "$root/pyproject.toml" ] || [ -f "$root/setup.py" ] || [ -d "$root/tests" ]; then python=true; fi
echo "Detected: ros=$ros node=$node python=$python"
command -v git python3 >/dev/null
if $ros; then test -f "/opt/ros/$distro/setup.bash"; fi
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
  clean_bash -c "source /opt/ros/$distro/setup.bash && rosdep check --from-paths '$root' --ignore-src --rosdistro $distro"
fi
pass

stage=build
if [ -n "${VERIFY_BUILD:-}" ]; then clean_bash -c "cd '$root' && $VERIFY_BUILD"
elif $ros; then
  mkdir -p "$run/ws/src" && cp -a "$root/." "$run/ws/src/repo" && rm -rf "$run/ws/src/repo/.verification"
  clean_bash -c "source /opt/ros/$distro/setup.bash && cd '$run/ws' && colcon build --event-handlers console_direct+"
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

stage=test
log="$run/test.log"
if [ -n "${VERIFY_TEST:-}" ]; then clean_bash -c "cd '$root' && $VERIFY_TEST" 2>&1 | tee "$log"
elif $ros; then
  clean_bash -c "source /opt/ros/$distro/setup.bash && cd '$run/ws' && colcon test --event-handlers console_direct+ && colcon test-result --verbose" 2>&1 | tee "$log"
elif $node; then clean_bash -c "cd '$root' && npm test" 2>&1 | tee "$log"
elif [ -f "$root/pyproject.toml" ] && python3 -c 'import pytest' 2>/dev/null; then
  clean_bash -c "cd '$root' && python3 -m pytest -rs" 2>&1 | tee "$log"
else
  clean_bash -c "cd '$root' && python3 -m unittest discover -s tests -v" 2>&1 | tee "$log"
fi
read -r tests_total tests_skipped < <(python3 - "$log" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
total = skipped = 0
for pattern, t, s in [
    (r"Summary: (\d+) tests?, \d+ errors?, \d+ failures?, (\d+) skipped", 1, 2),  # colcon test-result
    (r"^Ran (\d+) tests? in", 1, None),                                              # unittest
    (r"^Tests:\s+(?:.*?(\d+) skipped, )?.*?(\d+) total", 2, 1),                     # jest
    (r"^\s+Tests\s+(?:.*?(\d+) skipped.*?)?\((\d+)\)", 2, 1),                        # vitest
]:
    for m in re.finditer(pattern, text, re.M):
        total += int(m.group(t) or 0)
        skipped += int(m.group(s) or 0) if s else 0
m = re.findall(r"=+ (?:(\d+) passed)?(?:, )?(?:(\d+) skipped)?.* in [\d.]+s", text)  # pytest
for passed, skip in m:
    total += int(passed or 0) + int(skip or 0)
    skipped += int(skip or 0)
skipped += sum(int(n) for n in re.findall(r"skipped=(\d+)", text))  # unittest
print(total, skipped)
PY
)
echo "Tests executed: $((tests_total - tests_skipped)) of $tests_total (skipped $tests_skipped)"
if [ "$((tests_total - tests_skipped))" -le 0 ]; then
  echo "FAIL: zero tests executed; an empty or fully skipped suite is not evidence"
  exit 1
fi
pass

stage=evidence
cp "$log" "$run/test-output.log" 2>/dev/null || true
pass
