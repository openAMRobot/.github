"""Tests for tools/check_decisions.py against the fixture repository.

All text in these tests is synthetic. The real-register tests use invented
sentences that exercise each pattern; they quote no plan, audit or supplier
document.
"""
import contextlib
import io
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


class FixtureMatrix(unittest.TestCase):
    """Matching value, contradicting value, unlisted file type, superseded citation."""

    def setUp(self):
        self.decisions = cd.load_decisions(DECISIONS, ROOT / "maintainers.yaml")
        self.stats = {}
        self.findings, self.allowed = cd.scan(REPO, self.decisions, "platform-fixture", stats=self.stats)

    def at(self, rel):
        return [f for f in self.findings if f["file"] == rel]

    def test_matching_value_is_clean(self):
        self.assertEqual(self.at("config/params.yaml"), [])

    def test_contradicting_value_reports_file_line_found_and_decided(self):
        (f,) = self.at("README.md")
        self.assertEqual((f["line"], f["found"], f["decided"], f["source"]), (3, "mast_1400", "1350 mm", "FIX-DOC item 1"))

    def test_unlisted_file_type_is_not_scanned_but_counted(self):
        self.assertEqual(self.at("legacy/notes.txt"), [])
        self.assertGreaterEqual(self.stats["unscanned"], 1)
        only = {}
        cd.scan(REPO, self.decisions, "platform-fixture", only=["legacy/notes.txt"], stats=only)
        self.assertEqual(only["unscanned"], 1)

    def test_superseded_decision_still_cited(self):
        (f,) = self.at("docs/citation.md")
        self.assertEqual((f["line"], f["found"]), (3, "FIX-DOC rev 1 item 1"))
        self.assertIn("superseded source still cited", f["message"])

    def test_all_findings(self):
        where = sorted((f["file"], f["line"], f["id"]) for f in self.findings)
        self.assertEqual(where, [
            ("README.md", 3, "FIX-MAST"),
            ("docs/citation.md", 3, "FIX-MAST"),
            ("launch/robot.launch.py", 2, "FIX-MAST"),
            ("launch/robot.launch.py", 3, "FIX-IMU"),
            ("package.xml", 4, "FIX-MAST"),
            ("urdf/robot.xacro", 2, "FIX-MAST"),
        ])

    def test_allow_marker_is_reported_not_silenced(self):
        self.assertEqual([(a["file"], a["line"]) for a in self.allowed], [("docs/history.md", 4)])
        self.assertIn("superseded plan", self.allowed[0]["reason"])

    def test_unless_exemption_and_excluded_paths(self):
        files = {f["file"] for f in self.findings}
        self.assertNotIn("CHANGELOG.md", files)
        self.assertFalse(any(f["file"] == "docs/history.md" for f in self.findings))

    def test_repository_filter_and_per_check_files(self):
        findings, _ = cd.scan(REPO, self.decisions, "docs-fixture")
        self.assertNotIn("FIX-IMU", {f["id"] for f in findings})
        self.assertEqual(len(findings), 5)

    def test_open_decisions_are_not_scanned(self):
        self.assertNotIn("FIX-OPEN", {f["id"] for f in self.findings})

    def test_changed_files_scope(self):
        self.assertEqual(cd.scan(REPO, self.decisions, "x", only=["config/params.yaml"])[0], [])
        self.assertEqual(len(cd.scan(REPO, self.decisions, "x", only=["README.md", "gone.md"])[0]), 1)

    def test_checker_never_writes(self):
        before = {p: p.stat().st_mtime_ns for p in REPO.rglob("*") if p.is_file()}
        before[DECISIONS] = DECISIONS.stat().st_mtime_ns
        run("--decisions", DECISIONS, "--root", REPO, "--repository", "platform-x")
        after = {p: p.stat().st_mtime_ns for p in before}
        self.assertEqual(before, after)


class CommandLine(unittest.TestCase):
    def test_exit_one_on_contradiction(self):
        code, out = run("--decisions", DECISIONS, "--root", REPO, "--repository", "platform-x")
        self.assertEqual(code, 1)
        self.assertIn("CONTRADICTION README.md:3: FIX-MAST found 'mast_1400', decided '1350 mm'", out)
        self.assertIn("result: 6 contradiction(s), 1 allowed", out)
        self.assertIn("textual consistency only", out)

    def test_exit_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "README.md").write_text("mast_1350 is the baseline\n", encoding="utf-8")
            code, out = run("--decisions", DECISIONS, "--root", tmp)
        self.assertEqual(code, 0, out)

    def test_exit_two_on_missing_root(self):
        self.assertEqual(run("--decisions", DECISIONS, "--root", "/nonexistent-root")[0], 2)


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
    kind: value
    status: recorded
    value: 1
    unit: mm
    date: null
    source: {document: D, item: i}
    applies_to: {repositories: ["*"], files: ["**/*.md"]}
    check: [{pattern: '(?P<found>x)'}]
    verification: {machine: x in text, human: {reviewer: platform-lead, evidence: drawing}}
    owner: platform-lead
"""

    def test_base_is_valid(self):
        self.assertEqual(len(cd.load_decisions(self.write(self.BASE), ROOT / "maintainers.yaml")), 1)

    def test_rejects_invalid_entries(self):
        cases = {
            "duplicate id": self.BASE + self.BASE.split("decisions:\n", 1)[1],
            "pattern needs": self.BASE.replace("(?P<found>x)", "x"),
            "not listed under sources": self.BASE.replace("document: D", "document: E"),
            "status must be": self.BASE.replace("status: recorded", "status: maybe"),
            "kind must be": self.BASE.replace("kind: value", "kind: wish"),
            "missing owner": self.BASE.replace("    owner: platform-lead\n", ""),
            "needs value": self.BASE.replace("    value: 1\n", ""),
            "repositories and files": self.BASE.replace(', files: ["**/*.md"]', ""),
            "verification needs": self.BASE.replace("machine: x in text, ", ""),
            "schema_version": self.BASE.replace("schema_version: 1", "schema_version: 9"),
        }
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(cd.DecisionError, expected):
                    cd.load_decisions(self.write(text))

    SUPERSEDED = BASE.replace("status: recorded", "status: superseded").replace(
        "    check: [{pattern: '(?P<found>x)'}]\n",
        "    superseded_by: {document: D, item: j, decision: B, citation: '(?P<found>old)', unless: 'history'}\n")

    def test_superseded_entry_scans_only_its_citation(self):
        (d,) = cd.load_decisions(self.write(self.SUPERSEDED), ROOT / "maintainers.yaml")
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.md").write_text("x here\nold value\nold value in history\n", encoding="utf-8")
            findings, _ = cd.scan(tmp, [d], "r")
        self.assertEqual([(f["line"], f["found"]) for f in findings], [(2, "old")])
        self.assertIn("superseded by D j (B)", findings[0]["message"])
        self.assertEqual(findings[0]["decided"], "superseded by B")

    def test_superseded_entry_needs_superseded_by(self):
        cases = {
            "superseded needs superseded_by": self.SUPERSEDED.replace(
                "    superseded_by: {document: D, item: j, decision: B, citation: '(?P<found>old)', unless: 'history'}\n", ""),
            "superseded_by document 'E' not listed": self.SUPERSEDED.replace("superseded_by: {document: D", "superseded_by: {document: E"),
            "superseded_by citation needs": self.SUPERSEDED.replace("'(?P<found>old)'", "'old'"),
            "missing check": self.BASE.replace("    check: [{pattern: '(?P<found>x)'}]\n", ""),
        }
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(cd.DecisionError, expected):
                    cd.load_decisions(self.write(text))

    def test_owner_and_reviewer_must_be_maintainers_roles(self):
        with self.assertRaisesRegex(cd.DecisionError, "owner 'somebody' is not a role"):
            cd.load_decisions(self.write(self.BASE.replace("owner: platform-lead", "owner: somebody")),
                              ROOT / "maintainers.yaml")
        with self.assertRaisesRegex(cd.DecisionError, "reviewer 'somebody' is not a role"):
            cd.load_decisions(self.write(self.BASE.replace("reviewer: platform-lead", "reviewer: somebody")),
                              ROOT / "maintainers.yaml")


class RealRegister(unittest.TestCase):
    """The organization's decisions.yaml is valid and its patterns behave on synthetic text."""

    @classmethod
    def setUpClass(cls):
        cls.decisions = cd.load_decisions(ROOT / "decisions.yaml", ROOT / "maintainers.yaml")

    def ids(self, name, text, repository="openamr-platform-sw"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return sorted(f["id"] for f in cd.scan(tmp, self.decisions, repository)[0])

    def test_every_entry_has_provenance_verification_and_owner(self):
        for d in self.decisions:
            self.assertTrue(d["source"]["item"], d["id"])
            self.assertTrue(d["verification"]["human"]["evidence"], d["id"])

    def test_non_numeric_decisions_are_present(self):
        kinds = {d["id"]: d["kind"] for d in self.decisions}
        for did in ("MAX-ASSEMBLED-HEIGHT", "NO-SUSPENSION", "RS485-NOT-IN-2-0", "DOCK-NO-CONTACTS",
                    "DOCKING-NOT-CHARGING", "TELEMETRY-NOT-SAFETY-EVIDENCE"):
            self.assertIn(kinds[did], {"exclusion", "distinction"}, did)

    def test_imu_topic_attributed_to_firmware(self):
        self.assertEqual(self.ids("launch/a.launch.py", "# the MCU bridge publishes /imu/data and /odom\n"),
                         ["IMU-TOPIC-OWNERSHIP"])
        self.assertEqual(self.ids("launch/a.launch.py", "# MCU bridge: /odom/unfiltered, /imu/data\n"),
                         ["IMU-TOPIC-OWNERSHIP"])
        self.assertEqual(self.ids("docs/imu.md", "The MCU publishes /imu/data_raw; the host filter publishes /imu/data.\n"), [])

    def test_shoulder_height_versus_envelope(self):
        self.assertEqual(self.ids("docs/a.md", "Shoulder axis at 1700 mm.\n", "openamrobot-docs"), ["MAX-ASSEMBLED-HEIGHT"])
        self.assertEqual(self.ids("docs/a.md", "Maximum assembled height 1700 mm, not a shoulder height.\n",
                                  "openamrobot-docs"), [])

    def test_superseded_mast_entries(self):
        cases = {
            "Shoulder-axis installation height 1350 mm.\n": ["MAST-INSTALL-HEIGHT"],
            "The mast_1350 slot is the installation baseline.\n": ["MAST-INSTALL-HEIGHT"],
            "Four indexed mast positions, mast_1300 to mast_1450.\n": ["MAST-POSITIONS"],
            "Mast top at 1500 mm on one MISUMI HFS6-60120 profile.\n": ["MAST-TOP-HEIGHT"],
            "Maximum assembled height 1600 mm.\n": ["MAX-ASSEMBLED-HEIGHT"],
        }
        for text, expected in cases.items():
            self.assertEqual(self.ids("docs/a.md", text, "x"), expected, text)
        for text in ("Shoulder axis 1000 to 1350 mm on the lift.\n",
                     "The superseded mast_1350 installation baseline (P-03 rev18.2).\n",
                     "Maximum assembled height 1700 mm, not a shoulder height.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)
        by_id = {d["id"]: d for d in self.decisions}
        for did in ("MAST-INSTALL-HEIGHT", "MAST-POSITIONS", "MAST-TOP-HEIGHT"):
            self.assertEqual(by_id[did]["status"], "superseded", did)
            self.assertEqual((by_id[did]["superseded_by"]["document"], by_id[did]["superseded_by"]["item"]),
                             ("P-03-rev18.7", "item 8"), did)
        self.assertEqual(by_id["MAX-ASSEMBLED-HEIGHT"]["source"]["document"], "P-03-rev18.7")

    def test_exclusions(self):
        self.assertEqual(self.ids("docs/a.md", "The base uses sprung drive wheels.\n", "x"), ["NO-SUSPENSION"])
        self.assertEqual(self.ids("docs/a.md", "No sprung drive wheels in 2.0.\n", "x"), [])
        self.assertEqual(self.ids("docs/a.md", "The dock has two charging contacts.\n", "openamrobot-docs"), ["DOCK-NO-CONTACTS"])
        self.assertEqual(self.ids("docs/a.md", "There are no charging contacts.\n", "openamrobot-docs"), [])
        self.assertEqual(self.ids("docs/a.md", "The drive talks RS485 to the base.\n", "openamr-platform-hw"), ["RS485-NOT-IN-2-0"])
        self.assertEqual(self.ids("docs/a.md", "The lift controller moves the arms.\n", "x"), [])

    def test_docking_never_establishes_charging(self):
        self.assertEqual(self.ids("src/dock.py", "def isCharging(self): return true\n", "openamr-platform-sw"),
                         ["DOCKING-NOT-CHARGING"])
        self.assertEqual(self.ids("web/a.ts", "// when docked the robot is connected to external power\n",
                                  "openamrobot-ui"), ["DOCKING-NOT-CHARGING"])

    def test_telemetry_is_not_safety_evidence(self):
        self.assertEqual(self.ids("docs/a.md", "The watchdog is our safety layer.\n", "x"), ["TELEMETRY-NOT-SAFETY-EVIDENCE"])
        self.assertEqual(self.ids("docs/a.md", "The watchdog is functional, not a safety layer.\n", "x"), [])

    def test_estop_recommendation(self):
        self.assertEqual(self.ids("docs/a.md", "An uncertified button is fine for prototypes.\n", "x"),
                         ["SAFETY-PROCUREMENT"])

    def test_bom_issue_in_force(self):
        self.assertEqual(self.ids("docs/a.md", "The canonical BOM is Issue 6.\n", "x"), ["BOM-ISSUE-IN-FORCE"])
        self.assertEqual(self.ids("docs/a.md", "BOM per P-03 rev18.1 line 7.\n", "x"), ["BOM-ISSUE-IN-FORCE"])
        self.assertEqual(self.ids("docs/a.md", "Issue 7 is canonical; Issue 6 is superseded.\n", "x"), [])

    def test_nav_lidar(self):
        repo = "openamr-platform-sw"
        self.assertEqual(self.ids("docs/a.md", "Navigation LiDAR: Hokuyo UST-10LX.\n", repo), ["NAV-LIDAR"])
        self.assertEqual(self.ids("docs/a.md", "The UST-10LX was dropped on cost.\n", repo), [])
        self.assertEqual(self.ids("docs/a.md", "Mount the RPLIDAR A1M8 on the base.\n", repo), ["NAV-LIDAR"])
        self.assertEqual(self.ids("docs/a.md", "RPLIDAR A1 on the existing robot (Gate A).\n", repo), [])
        self.assertEqual(self.ids("docs/a.md", "RPLIDAR S3 (S3M1-R2) via sllidar_ros2; the RPLIDAR is on USB.\n",
                                  repo), [])

    def test_release_milestones(self):
        self.assertEqual(self.ids("docs/a.md", "OpenAMRobot 2.0 final release: 18 December 2026.\n", "x"), [])
        self.assertEqual(self.ids("docs/a.md", "OpenAMRobot 2.0 final release: 30 November 2026.\n", "x"),
                         ["RELEASE-MILESTONES"])

    def test_base_controller_io(self):
        repo = "openamrobot-docs"
        self.assertEqual(self.ids("docs/a.md", "Gate B: STM32H743 bench controller.\n", repo), ["BASE-CONTROLLER-IO"])
        self.assertEqual(self.ids("docs/a.md", "Bench board: NUCLEO-H743ZI2.\n", repo), ["BASE-CONTROLLER-IO"])
        for line in ("The STM32H743 is superseded by the STM32H723ZG.\n",
                     "Legacy bench board: NUCLEO-H743ZI2.\n",
                     "Historical note: the STM32H743 bench build.\n",
                     "The NUCLEO-H743ZI2 was replaced by the NUCLEO-H723ZG.\n",
                     "Base controller: STM32H723ZG on a NUCLEO-H723ZG bench board.\n"):
            self.assertEqual(self.ids("docs/a.md", line, repo), [], line)

    def test_lift_approved_in_principle(self):
        for text in ("OpenAMRobot 2.0 has no lift.\n",
                     "- a fixed mast for the arms\n",
                     "The linear lift is deferred to OpenAMRobot 3.0.\n",
                     "Fixed mast (lift in 3.0), mounting plates.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["LIFT"], text)
        for text in ("Lift approved in principle: DOLD Hexalift V1 350 mm primary, TiMOTION TL3 400 mm fallback.\n",
                     "Lift motion only in the stowed or carry safe pose with the base stopped.\n",
                     "No lift motion while the base moves.\n",
                     "The fixed mast is superseded by the lift (P-03 rev18.7 item 8).\n",
                     "The lift column moves the shoulder axis from 1000 to 1350 mm.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_legacy_label_exempts_compute(self):
        self.assertEqual(self.ids("README.md", "Legacy build: Raspberry Pi 5.\n", "openamr-platform-hw"), [])
        self.assertEqual(self.ids("README.md", "Compute: Raspberry Pi 5.\n", "openamr-platform-hw"), ["COMPUTE"])


if __name__ == "__main__":
    unittest.main()
