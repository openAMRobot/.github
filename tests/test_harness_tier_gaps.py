"""Regression tests for tier and guard gaps found in the 1 Nov 2026 effectiveness audit
(openAMRobot/audits, 2026-11-01-harness-effectiveness, probe P2): Nav2 launch and parameter
files outside the two listed paths were tier B; a repository's verification configuration
was writable; a .msg under test/ passed as a new test file; a committed script that writes
an interface file at build time passed as tier B."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import harness_guard as guard  # noqa: E402
import harness_lib as hl  # noqa: E402

POLICY = hl.load_policy(ROOT)


class TierGaps(unittest.TestCase):
    def tier(self, path, repo="openamr-platform-sw"):
        return hl.tier_of(path, repo, POLICY)

    def test_every_nav2_launch_and_parameter_file_is_tier_c(self):
        for path in ["ros2/src/openamrobot_nav2/launch/localization_launch.py",
                     "ros2/src/openamrobot_nav2/launch/sim_bringup_launch.py",
                     "ros2/src/openamrobot_nav2/config/slam.yaml",
                     "ros2/src/openamrobot_nav2/config/navigation_status_profile.yaml",
                     "ros2/src/openamrobot_nav2/launch/navigation_launch.py",
                     "ros2/src/openamrobot_nav2/config/nav2_params.yaml"]:
            self.assertEqual(self.tier(path), "C", path)
        self.assertEqual(self.tier("ros2/src/openamrobot_nav2/test/test_status_rules.py"), "A")

    def test_verification_configuration_is_tier_d(self):
        self.assertEqual(self.tier(".openamrobot/verify.env"), "D")
        self.assertEqual(self.tier("tools/verify.sh", "openamrobot-interfaces"), "D")

    def test_sudo_is_a_blocked_command(self):
        self.assertIn("sudo", POLICY["blocked_commands"])


class GuardInterfaces(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.write("ros2/src/pkg/pkg/node.py", "x = 1\n")
        self.commit("base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-s", "-m", message)

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = guard.main(["--repo-root", str(self.repo), "--repository", "openamr-platform-sw",
                               "--base", self.base, "--harness-root", str(ROOT)])
        return code, json.loads(out.getvalue())

    def test_interface_file_under_test_is_not_a_new_test_file(self):
        self.write("ros2/src/pkg/test/msg/NavProbe.msg", "uint8 state\n")
        self.commit("test: interface fixture")
        code, report = self.check()
        self.assertEqual(code, 1, report)

    def test_script_that_writes_an_interface_file_fails(self):
        self.write("scripts/gen_iface.py", "from pathlib import Path\n"
                   "out = Path('ros2/src/pkg/msg/NavProbe.msg')\nout.write_text('uint8 state\\n')\n")
        self.commit("build: interface generator")
        code, report = self.check()
        self.assertEqual(code, 1, report)
        self.assertIn("interface files", " ".join(report["failures"]))

    def test_cmake_interface_declaration_fails(self):
        self.write("ros2/src/pkg/CMakeLists.txt", "rosidl_generate_interfaces(${PROJECT_NAME} \"msg/X.msg\")\n")
        self.commit("build: declare interfaces")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("interface files", " ".join(report["failures"]))

    def test_reading_an_interface_path_is_still_allowed(self):
        self.write("ros2/src/pkg/test/test_contract.py", "def test_contract():\n"
                   "    assert open('msg/NavStatus.msg').read()\n")
        self.commit("test: contract")
        code, report = self.check()
        self.assertEqual(code, 0, report)


if __name__ == "__main__":
    unittest.main()
