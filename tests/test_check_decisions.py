"""Tests for tools/check_decisions.py against the fixture repository."""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_decisions as cd  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
REPO = FIXTURES / "decisions_repo"
DECISIONS = FIXTURES / "decisions.yaml"


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cd.main([str(a) for a in args])
    return code, out.getvalue()


class ScanFixtureRepository(unittest.TestCase):
    def setUp(self):
        self.decisions = cd.load_decisions(DECISIONS)

    def test_reports_file_line_found_and_decided_value(self):
        findings, _ = cd.scan(REPO, self.decisions, "platform-fixture")
        readme = [f for f in findings if f["file"] == "README.md"]
        self.assertEqual(len(readme), 1)
        self.assertEqual(readme[0]["line"], 3)
        self.assertEqual(readme[0]["found"], "mast_1400")
        self.assertEqual(readme[0]["decided"], "1350 mm")
        self.assertEqual(readme[0]["source"], "FIX-DOC item 1")

    def test_covers_markdown_launch_xacro_package_xml(self):
        findings, _ = cd.scan(REPO, self.decisions, "platform-fixture")
        where = sorted((f["file"], f["line"], f["id"]) for f in findings)
        self.assertEqual(where, [
            ("README.md", 3, "FIX-MAST"),
            ("launch/robot.launch.py", 2, "FIX-MAST"),
            ("launch/robot.launch.py", 3, "FIX-IMU"),
            ("package.xml", 4, "FIX-MAST"),
            ("urdf/robot.xacro", 2, "FIX-MAST"),
        ])

    def test_allow_marker_is_reported_not_silenced(self):
        _, allowed = cd.scan(REPO, self.decisions, "platform-fixture")
        self.assertEqual([(a["file"], a["line"]) for a in allowed], [("docs/history.md", 4)])
        self.assertIn("superseded plan", allowed[0]["reason"])

    def test_unless_exemption_excluded_paths_and_other_file_types(self):
        findings, _ = cd.scan(REPO, self.decisions, "platform-fixture")
        files = {f["file"] for f in findings}
        self.assertNotIn("CHANGELOG.md", files)
        self.assertNotIn("legacy/notes.txt", files)
        self.assertFalse(any(f["file"] == "docs/history.md" and f["line"] == 5 for f in findings))

    def test_repository_filter_and_per_check_files(self):
        findings, _ = cd.scan(REPO, self.decisions, "docs-fixture")
        self.assertNotIn("FIX-IMU", {f["id"] for f in findings})
        self.assertEqual(len(findings), 4)

    def test_open_decisions_are_not_enforced(self):
        findings, _ = cd.scan(REPO, self.decisions, "platform-fixture")
        self.assertNotIn("FIX-OPEN", {f["id"] for f in findings})

    def test_changed_files_scope(self):
        findings, _ = cd.scan(REPO, self.decisions, "platform-fixture", only=["config/params.yaml"])
        self.assertEqual(findings, [])
        findings, _ = cd.scan(REPO, self.decisions, "platform-fixture", only=["README.md", "gone.md"])
        self.assertEqual(len(findings), 1)


class CommandLine(unittest.TestCase):
    def test_exit_one_on_contradiction(self):
        code, out = run("--decisions", DECISIONS, "--root", REPO, "--repository", "platform-x")
        self.assertEqual(code, 1)
        self.assertIn("CONTRADICTION README.md:3: FIX-MAST found 'mast_1400', decided '1350 mm'", out)
        self.assertIn("result: 5 contradiction(s), 1 allowed", out)

    def test_exit_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "README.md").write_text("mast_1350 is the baseline\n", encoding="utf-8")
            code, out = run("--decisions", DECISIONS, "--root", tmp)
        self.assertEqual(code, 0, out)

    def test_exit_two_on_missing_root(self):
        code, _ = run("--decisions", DECISIONS, "--root", "/nonexistent-root")
        self.assertEqual(code, 2)


class Schema(unittest.TestCase):
    def write(self, text):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        tmp.write(text)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return tmp.name

    BASE = """schema_version: 1
sources: {D: {title: t}}
decisions:
  - id: A
    title: t
    status: recorded
    value: 1
    unit: mm
    date: null
    source: {document: D, item: i}
    applies_to: {repositories: ["*"]}
    check: [{pattern: '(?P<found>x)'}]
    owner: platform-lead
"""

    def test_base_is_valid(self):
        self.assertEqual(len(cd.load_decisions(self.write(self.BASE))), 1)

    def test_rejects_invalid_entries(self):
        cases = {
            "duplicate id": self.BASE + self.BASE.split("decisions:\n", 1)[1],
            "pattern needs": self.BASE.replace("(?P<found>x)", "x"),
            "not listed under sources": self.BASE.replace("document: D", "document: E"),
            "status must be": self.BASE.replace("status: recorded", "status: maybe"),
            "missing owner": self.BASE.replace("    owner: platform-lead\n", ""),
            "needs value": self.BASE.replace("    value: 1\n", ""),
            "schema_version": self.BASE.replace("schema_version: 1", "schema_version: 9"),
        }
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(cd.DecisionError, expected):
                    cd.load_decisions(self.write(text))

    def test_owner_must_be_a_maintainers_role(self):
        with self.assertRaisesRegex(cd.DecisionError, "not a role"):
            cd.load_decisions(self.write(self.BASE.replace("platform-lead", "somebody")),
                              ROOT / "maintainers.yaml")


class RealDecisionsFile(unittest.TestCase):
    """The organization's decisions.yaml is valid and detects audited mistakes."""

    @classmethod
    def setUpClass(cls):
        cls.decisions = cd.load_decisions(ROOT / "decisions.yaml", ROOT / "maintainers.yaml")

    def scan_text(self, name, text, repository):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return cd.scan(tmp, self.decisions, repository)[0]

    def test_every_recorded_decision_has_a_source_and_owner(self):
        for d in self.decisions:
            self.assertTrue(d["source"]["item"], d["id"])
            self.assertTrue(d["owner"], d["id"])

    def test_detects_imu_topic_owned_by_firmware(self):
        text = "        # micro-ROS agent: bridges the Teensy (/cmd_vel, /odom/unfiltered, /imu/data).\n"
        found = self.scan_text("launch/drivers.launch.py", text, "openamr-platform-sw")
        self.assertEqual([f["id"] for f in found], ["IMU-TOPIC-OWNERSHIP"])

    def test_accepts_host_owned_imu_topic(self):
        text = "Firmware owns raw /imu/data_raw; the host filter publishes /imu/data.\n"
        self.assertEqual(self.scan_text("docs/imu.md", text, "openamr-platform-sw"), [])

    def test_detects_clone_estop_recommendation(self):
        found = self.scan_text("docs/estop.md", "no certification. Fine for prototypes.\n", "openamrobot-docs")
        self.assertEqual([f["id"] for f in found], ["SAFETY-PROCUREMENT"])

    def test_detects_superseded_mast_values(self):
        text = "| `mast_1300` | Plan working shoulder-axis baseline (1300 mm) |\nmast_1600 position\n"
        found = self.scan_text("integration/inventory.md", text, "openamrobot-manipulation")
        self.assertEqual(sorted(f["id"] for f in found), ["MAST-INSTALL-HEIGHT", "MAST-POSITIONS"])

    def test_detects_docking_charge_contacts_but_not_negation(self):
        found = self.scan_text("docs/dock.md", "The robot engages the charging contacts.\n", "openamrobot-docs")
        self.assertEqual([f["id"] for f in found], ["DOCKING-SCOPE"])
        self.assertEqual(self.scan_text("docs/dock.md", "There are no charging contacts in 2.0.\n",
                                        "openamrobot-docs"), [])

    def test_legacy_label_exempts_raspberry_pi(self):
        self.assertEqual(self.scan_text("README.md", "Legacy build: Raspberry Pi 5.\n", "openamr-platform-hw"), [])
        self.assertEqual(len(self.scan_text("README.md", "Compute: Raspberry Pi 5.\n", "openamr-platform-hw")), 1)


if __name__ == "__main__":
    unittest.main()
