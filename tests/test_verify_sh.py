"""Tests for rollout/verify.sh: zero-test rule, skip rule, delegation."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "rollout" / "verify.sh"
PASSING = "import unittest\n\nclass T(unittest.TestCase):\n    def test_one(self):\n        self.assertTrue(True)\n"


def make_repo(files):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return tmp, root


def verify(root):
    proc = subprocess.run(["bash", str(VERIFY), str(root)], capture_output=True, text=True, timeout=120,
                          env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(root)})
    runs = sorted((root / ".verification").glob("run.*"))
    summary = json.loads((runs[-1] / "summary.json").read_text()) if runs else {}
    return proc.returncode, proc.stdout + proc.stderr, summary


class VerifyScript(unittest.TestCase):
    def check(self, files):
        tmp, root = make_repo(files)
        self.addCleanup(tmp.cleanup)
        return verify(root)

    def test_passing_suite_passes_with_counts(self):
        code, out, summary = self.check({"tests/test_a.py": PASSING})
        self.assertEqual(code, 0, out)
        self.assertEqual((summary["result"], summary["tests_total"]), ("PASS", 1))

    def test_zero_tests_fail(self):
        code, out, summary = self.check({"tests/test_a.py": "# no tests yet\n"})
        self.assertNotEqual(code, 0)
        self.assertIn("zero tests executed", out)
        self.assertEqual(summary["failed_stage"], "test")

    def test_failing_test_fails(self):
        body = PASSING.replace("self.assertTrue(True)", "self.fail('deliberate')")
        code, out, summary = self.check({"tests/test_a.py": body})
        self.assertNotEqual(code, 0)
        self.assertIn("test command exited with status", out)
        self.assertEqual(summary["failed_stage"], "test")

    def test_fully_skipped_suite_fails(self):
        body = PASSING.replace("    def test_one", "    @unittest.skip('flaky, see #12')\n    def test_one")
        code, out, _ = self.check({"tests/test_a.py": body})
        self.assertNotEqual(code, 0)
        self.assertIn("zero tests executed", out)

    def test_skip_without_issue_fails(self):
        body = PASSING + "\n    @unittest." + "skip('later')\n    def test_two(self):\n        pass\n"
        code, out, summary = self.check({"tests/test_a.py": body})
        self.assertNotEqual(code, 0)
        self.assertEqual(summary["failed_stage"], "test-markers")

    def test_skip_with_issue_is_allowed(self):
        body = PASSING + "\n    @unittest.skip('hardware only, see #12')\n    def test_two(self):\n        pass\n"
        code, out, summary = self.check({"tests/test_a.py": body})
        self.assertEqual(code, 0, out)
        self.assertEqual((summary["tests_total"], summary["tests_skipped"]), (2, 1))

    def test_nothing_detected_fails(self):
        code, out, _ = self.check({"notes.txt": "hello\n"})
        self.assertNotEqual(code, 0)
        self.assertIn("no buildable or testable project detected", out)

    def test_delegates_to_existing_tools_verify(self):
        code, out, _ = self.check({"tools/verify.sh": "echo repository-own-verify\nexit 0\n"})
        self.assertEqual(code, 0)
        self.assertIn("repository-own-verify", out)

    def test_delegation_writes_summary_with_delegated_status_and_counts(self):
        script = ("echo 'Ran 3 tests in 0.010s'\n"
                  "echo 'Evidence: /work/.verification/run.native'\n"
                  "exit 0\n")
        code, out, summary = self.check({"tools/verify.sh": script})
        self.assertEqual(code, 0, out)
        self.assertEqual(summary["mode"], "delegated")
        self.assertEqual((summary["result"], summary["exit_code"]), ("PASS", 0))
        self.assertEqual((summary["tests_total"], summary["tests_skipped"], summary["counts_parsed"]), (3, 0, True))
        self.assertEqual(summary["delegated_evidence"], "/work/.verification/run.native")
        self.assertIsInstance(summary["duration_seconds"], int)
        for key in ("schema_version", "head_sha", "base_sha", "harness_sha", "delegated_script"):
            self.assertIn(key, summary)

    def test_delegated_failure_is_recorded_and_propagated(self):
        code, out, summary = self.check({"tools/verify.sh": "echo 'Ran 2 tests in 0.1s'\necho boom\nexit 7\n"})
        self.assertEqual(code, 7, out)
        self.assertEqual((summary["result"], summary["exit_code"]), ("FAIL", 7))
        self.assertIn("FAIL: delegated tools/verify.sh (exit 7)", out)

    def test_delegation_without_recognisable_counts_says_so(self):
        _, _, summary = self.check({"tools/verify.sh": "echo done\nexit 0\n"})
        self.assertEqual((summary["tests_total"], summary["counts_parsed"]), (None, False))


# A directory named summary.json inside the run directory makes the summary write fail (also as root).
BLOCK_SUMMARY_SH = 'for d in "$(dirname "$0")"/../.verification/run.*; do mkdir -p "$d/summary.json"; done\n'
BLOCK_SUMMARY_PY = ("import glob, os, unittest\n\nclass T(unittest.TestCase):\n    def test_one(self):\n"
                    "        for d in glob.glob('.verification/run.*'):\n"
                    "            os.makedirs(os.path.join(d, 'summary.json'), exist_ok=True)\n")


class SummaryWriteFailure(unittest.TestCase):
    """A run whose summary.json cannot be written never reports success (release-owner review)."""

    def run_blocked(self, files):
        tmp, root = make_repo(files)
        self.addCleanup(tmp.cleanup)
        proc = subprocess.run(["bash", str(VERIFY), str(root)], capture_output=True, text=True, timeout=120,
                              env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(root)})
        run = sorted((root / ".verification").glob("run.*"))[-1]
        self.assertTrue((run / "summary.json").is_dir(), "the test did not block the summary write")
        return proc.returncode, proc.stdout + proc.stderr, (run / "result.txt").read_text()

    def test_harness_run_fails_when_summary_cannot_be_written(self):
        code, out, result = self.run_blocked({"tests/test_a.py": BLOCK_SUMMARY_PY})
        self.assertNotEqual(code, 0, out)
        self.assertIn("could not write", out)
        self.assertNotIn("PASS: all detected verification stages", out)
        self.assertTrue(result.startswith("FAIL: evidence-summary"), result)

    def test_delegated_success_fails_when_summary_cannot_be_written(self):
        code, out, result = self.run_blocked({"tools/verify.sh": BLOCK_SUMMARY_SH + "echo 'Ran 3 tests in 0.1s'\nexit 0\n"})
        self.assertNotEqual(code, 0, out)
        self.assertNotIn("PASS: delegated", out)
        self.assertTrue(result.startswith("FAIL: delegated tools/verify.sh (exit 1; summary.json not written)"), result)

    def test_delegated_failure_status_is_kept_when_summary_cannot_be_written(self):
        code, out, result = self.run_blocked({"tools/verify.sh": BLOCK_SUMMARY_SH + "exit 7\n"})
        self.assertEqual(code, 7, out)
        self.assertIn("exit 7; summary.json not written", result)


# A fake ROS install: setup.bash puts a fake rosdep on PATH. The fake needs an initialised
# rosdep cache under $HOME/.ros/rosdep (as the real one does) and fails on any package.xml
# that names an unresolvable key; it logs every path it is asked to scan.
FAKE_ROSDEP = r"""#!/usr/bin/env bash
log="$(dirname "$0")/../calls.log"
[ "$1" = check ] || exit 2
shift
if [ ! -f "$HOME/.ros/rosdep/sources.cache" ]; then
  echo "ERROR: your rosdep installation has not been initialized yet"; exit 1
fi
paths=()
while [ $# -gt 0 ]; do
  if [ "$1" = --from-paths ]; then
    shift
    while [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; do paths+=("$1"); shift; done
  else shift; fi
done
for p in "${paths[@]}"; do
  echo "scan $p" >> "$log"
  if grep -rl --include=package.xml unresolvable_generated_key "$p" >/dev/null 2>&1; then
    echo "ERROR: Cannot locate rosdep definition for [unresolvable_generated_key]"; exit 1
  fi
done
echo "All system dependencies have been satisfied"
"""
PACKAGE_XML = ('<?xml version="1.0"?>\n<package format="3"><name>{name}</name><version>0.0.0</version>'
               '<description>d</description><maintainer email="m@example.invalid">m</maintainer>'
               '<license>MIT</license>{deps}</package>\n')
ROS_ENV = 'VERIFY_BUILD="true"\nVERIFY_TEST="python3 -m unittest discover -s tests -v"\n'


class RosdepState(unittest.TestCase):
    """CI owner review (6 October): rosdep state in the clean HOME; generated folders not scanned."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        ros = self.base / "ros"
        (ros / "bin").mkdir(parents=True)
        (ros / "bin" / "rosdep").write_text(FAKE_ROSDEP, encoding="utf-8")
        (ros / "bin" / "rosdep").chmod(0o755)
        (ros / "setup.bash").write_text(f'export PATH="{ros}/bin:$PATH"\n', encoding="utf-8")
        fake_colcon = ros / "bin" / "colcon"
        fake_colcon.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = test-result ]; then\n"
            "  echo 'Summary: 1 tests, 0 errors, 0 failures, 0 skipped'\n"
            "fi\n",
            encoding="utf-8",
        )
        fake_colcon.chmod(0o755)
        self.ros = ros
        self.home = self.base / "home"
        self.home.mkdir()

    def init_caller_rosdep(self):
        cache = self.home / ".ros" / "rosdep"
        cache.mkdir(parents=True)
        (cache / "sources.cache").write_text("prepared by the environment\n", encoding="utf-8")

    def run_verify(self, files):
        files = {"tests/test_a.py": PASSING, ".openamrobot/verify.env": ROS_ENV,
                 "ros2/src/pkg_a/package.xml": PACKAGE_XML.format(name="pkg_a", deps="<depend>rclpy</depend>"),
                 **files}
        tmp, root = make_repo(files)
        self.addCleanup(tmp.cleanup)
        proc = subprocess.run(["bash", str(VERIFY), str(root)], capture_output=True, text=True, timeout=120,
                              env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(self.home),
                                   "VERIFY_ROS_SETUP": str(self.ros / "setup.bash")})
        calls = self.ros / "calls.log"
        scanned = calls.read_text().split("\n") if calls.exists() else []
        return proc.returncode, proc.stdout + proc.stderr, root, scanned

    def test_caller_rosdep_cache_is_available_in_clean_home(self):
        self.init_caller_rosdep()
        code, out, _, _ = self.run_verify({})
        self.assertEqual(code, 0, out)
        self.assertIn("All system dependencies have been satisfied", out)
        self.assertIn("PASS: install", out)
        self.assertTrue((self.home / ".ros" / "rosdep" / "sources.cache").is_file())

    def test_without_rosdep_state_the_install_stage_fails(self):
        code, out, _, _ = self.run_verify({})
        self.assertNotEqual(code, 0, out)
        self.assertIn("not been initialized", out)
        self.assertIn("FAIL: install", out)

    def test_generated_build_install_log_folders_are_not_scanned(self):
        self.init_caller_rosdep()
        bad = PACKAGE_XML.format(name="pkg_a", deps="<depend>unresolvable_generated_key</depend>")
        code, out, root, scanned = self.run_verify({
            "ros2/build/pkg_a/package.xml": bad, "ros2/build/COLCON_IGNORE": "",
            "ros2/install/pkg_a/share/pkg_a/package.xml": bad, "ros2/install/COLCON_IGNORE": "",
            "ros2/log/latest/package.xml": bad,
            "ros2/generated/COLCON_IGNORE": "", "ros2/generated/pkg_a/package.xml": bad,
        })
        self.assertEqual(code, 0, out)
        scanned = [line for line in scanned if line]
        self.assertEqual(scanned, [f"scan {root / 'ros2' / 'src' / 'pkg_a'}"])


    def test_ros_build_copy_excludes_verification_workspace(self):
        self.init_caller_rosdep()
        code, out, _, _ = self.run_verify({".openamrobot/verify.env": ""})
        self.assertEqual(code, 0, out)
        self.assertNotIn("into itself", out)
        self.assertNotIn("cp: cannot copy", out)


if __name__ == "__main__":
    unittest.main()
