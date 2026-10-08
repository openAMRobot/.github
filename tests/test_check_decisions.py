"""Tests for tools/check_decisions.py against the fixture repository.

All text in these tests is synthetic. The real-register tests use invented
sentences that exercise each pattern; they quote no plan, audit or supplier
document.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
import unittest.mock
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


def setUpModule():
    # Tests never write to the real GitHub Actions log or job summary of the CI run.
    patcher = unittest.mock.patch.dict(os.environ)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    for key in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "WATCHDOG_ANNOTATION", "WATCHDOG_ANNOTATIONS"):
        os.environ.pop(key, None)


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
        self.assertIn("Mismatch with approved decision: FIX-MAST (5 finding(s))", out)
        self.assertIn("\n    README.md:3: found 'mast_1400'\n", out)
        self.assertIn("result: 6 contradiction(s), 1 allowed", out)
        self.assertIn("textual consistency only", out)

    def test_finding_explains_decision_why_fix_and_links(self):
        code, out = run("--decisions", DECISIONS, "--root", REPO, "--repository", "platform-x")
        block = out.split("Mismatch with approved decision: FIX-MAST (5 finding(s))", 1)[1].split("\nMismatch", 1)[0]
        self.assertIn("\n  Decision: 1350 mm\n", block)
        # Decision, Why, Fix and More once per group; one Why line per distinct reason.
        self.assertEqual(block.count("  Decision:"), 1)
        self.assertEqual(block.count("  Fix:"), 1)
        self.assertIn("\n  Why:      baseline is mast_1350.\n            superseded source still cited", block)
        self.assertIn("\n  Fix:      ", block)
        self.assertIn("FIX-MAST in decisions.yaml: https://github.com/openAMRobot/.github/blob/main/decisions.yaml#L", block)
        self.assertIn("WATCHDOG.md#decisions-of-record", block)
        self.assertIn("\n  Found:\n    README.md:3: found 'mast_1400'\n    docs/citation.md:3: found 'FIX-DOC rev 1 item 1'\n", block)
        self.assertEqual(block.count(": found "), 5)
        self.assertIn("Decisions of record summary: 6 finding(s) (FIX-MAST 5, FIX-IMU 1)", out)
        self.assertIn("Next step: ", out)
        self.assertNotIn("CONTRADICTION ", out)

    def test_github_actions_annotations_and_job_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp, "summary.md")
            env = {"GITHUB_ACTIONS": "true", "WATCHDOG_ANNOTATION": "error", "GITHUB_STEP_SUMMARY": str(summary)}
            with unittest.mock.patch.dict("os.environ", env):
                code, out = run("--decisions", DECISIONS, "--root", REPO, "--repository", "platform-x")
            self.assertEqual(code, 1)
            self.assertIn("::error file=README.md,line=3,title=Mismatch with approved decision (FIX-MAST)::", out)
            self.assertEqual(out.count("::error file="), 6)
            text = summary.read_text(encoding="utf-8")
            self.assertIn("| FIX-MAST | 5 |", text)
            self.assertIn("<details><summary>FIX-MAST: 5 finding(s)</summary>", text)

    def test_no_annotations_outside_github_actions(self):
        with unittest.mock.patch.dict("os.environ", {"GITHUB_ACTIONS": ""}):
            code, out = run("--decisions", DECISIONS, "--root", REPO, "--repository", "platform-x")
        self.assertNotIn("::warning", out)
        self.assertNotIn("::error", out)

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
in_force: {source: D, date: 2026-10-07}
sources: {D: {title: t}}
decisions:
  - id: A
    title: t
    kind: value
    status: recorded
    value: 1
    unit: mm
    date: null
    review_by: 2026-11-18
    source: {document: D, item: i}
    applies_to: {repositories: ["*"], files: ["**/*.md"]}
    check: [{pattern: '(?P<found>x)'}]
    verification: {machine: x in text, human: {reviewer: platform-lead, evidence: drawing}}
    owner: platform-lead
"""

    def test_base_is_valid(self):
        self.assertEqual(len(cd.load_decisions(self.write(self.BASE), ROOT / "maintainers.yaml")), 1)

    def test_requires_in_force_and_review_by(self):
        with self.assertRaisesRegex(cd.DecisionError, "in_force"):
            cd.load_decisions(self.write(self.BASE.replace("in_force: {source: D, date: 2026-10-07}\n", "")))
        with self.assertRaisesRegex(cd.DecisionError, "review_by"):
            cd.load_decisions(self.write(self.BASE.replace("    review_by: 2026-11-18\n", "")))

    def test_review_warnings_are_non_blocking_and_deterministic(self):
        data = {"decisions": [{"id": "A", "review_by": "2026-10-06"},
                              {"id": "B", "review_by": "2026-10-08"}]}
        self.assertEqual(cd.review_warnings(data, cd.date(2026, 10, 7)),
                         ["A review_by 2026-10-06 is past due"])

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

    def test_summary_and_fix_hint_are_optional_short_single_lines(self):
        ok = self.BASE.replace("    title: t\n", "    title: t\n    summary: Mast is 1 mm.\n    fix_hint: Use 1 mm.\n")
        decision = cd.load_decisions(self.write(ok))[0]
        self.assertEqual((decision["summary"], decision["fix_hint"]), ("Mast is 1 mm.", "Use 1 mm."))
        for field in ("summary", "fix_hint"):
            for bad in ("'" + "x" * 121 + "'", "''", "|\n      two\n      lines", "[a]"):
                with self.subTest(field=field, value=bad):
                    text = self.BASE.replace("    title: t\n", f"    title: t\n    {field}: {bad}\n")
                    with self.assertRaisesRegex(cd.DecisionError, f"{field} must be one non-empty line"):
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

    def test_every_entry_has_summary_and_fix_hint(self):
        for d in self.decisions:
            with self.subTest(id=d["id"]):
                self.assertTrue(d.get("summary"))
                self.assertTrue(d.get("fix_hint"))
                self.assertTrue(d.get("_line"))

    def test_finding_prints_summary_not_long_value(self):
        records = [{"file": "a.md", "line": 1, "id": d["id"], "found": "x", "message": "m"} for d in self.decisions]
        for record, d in zip(cd.to_watchdog(records, self.decisions), self.decisions):
            with self.subTest(id=d["id"]):
                self.assertEqual(record["decision"], d["summary"])
                self.assertEqual(record["fix"], d["fix_hint"])
                self.assertLessEqual(len(record["decision"]), 120)

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

    def test_imu_topic_history_label_is_accepted(self):
        # Regression: a line that labels the old firmware topic as outdated history is not a finding.
        self.assertEqual(self.ids("electrical/sensors/imu.md",
                                  "*(Older revisions of this doc said the firmware publishes `/imu/data` directly"
                                  " \u2014 that is outdated;\n", "openamr-platform-hw"), [])
        self.assertEqual(self.ids("docs/imu.md", "The firmware publishes `/imu/data` directly.\n",
                                  "openamr-platform-hw"), ["IMU-TOPIC-OWNERSHIP"])

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

    def test_legacy_charging_dock_fields_are_accepted(self):
        # Regression: a comment that labels the upstream charging-dock fields as legacy is not a finding.
        self.assertEqual(self.ids("config/dock_trigger.yaml",
                                  "    # Legacy fields read by opennav_docking::SimpleChargingDock \u2014 kept so the\n",
                                  "openamr-platform-sw"), [])
        self.assertEqual(self.ids("config/nav2_params.yaml", "      plugin: 'opennav_docking::SimpleChargingDock'\n",
                                  "openamr-platform-sw"), ["DOCKING-NOT-CHARGING"])

    def test_telemetry_is_not_safety_evidence(self):
        self.assertEqual(self.ids("docs/a.md", "The watchdog is our safety layer.\n", "x"), ["TELEMETRY-NOT-SAFETY-EVIDENCE"])
        self.assertEqual(self.ids("docs/a.md", "The watchdog is functional, not a safety layer.\n", "x"), [])

    def test_estop_recommendation(self):
        self.assertEqual(self.ids("docs/a.md", "An uncertified button is fine for prototypes.\n", "x"),
                         ["SAFETY-PROCUREMENT"])

    def test_bom_issue_in_force(self):
        self.assertEqual(self.ids("docs/a.md", "The canonical BOM is Issue 6.\n", "x"), ["BOM-ISSUE-IN-FORCE"])
        self.assertEqual(self.ids("docs/a.md", "BOM per P-03 rev18.1 line 7.\n", "x"), ["BOM-ISSUE-IN-FORCE"])
        self.assertEqual(self.ids("docs/a.md", "Issue 7.3 is canonical; Issue 6 is superseded.\n", "x"), [])

    def test_bom_issue_7_3_in_force(self):
        for text in ("The canonical BOM is Issue 7.\n", "BOM Issue 7.2 is the BOM of record.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["BOM-ISSUE-IN-FORCE"], text)
        for text in ("BOM Issue 7.3 is canonical.\n", "Issue 7 was canonical until Issue 7.3 superseded it.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

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

    def test_datum_height_stack(self):
        for text in ("The steel chassis deck top is at 300 mm.\n", "Base-plate top face 310 mm above the floor.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["DATUM-HEIGHT-STACK"], text)
        for text in ("Steel chassis deck top 294 mm (MMP STEP); floor Z = 0.\n",
                     "Base-plate top face 304 mm, the reference for lift and shoulder heights.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_frames_rep105(self):
        for text in ("base_link sits on the floor under the robot.\n",
                     "base_footprint is at axle height.\n",
                     "imu_link is mounted next to the drive motor.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["FRAMES-REP105"], text)
        for text in ("base_footprint on the floor under the drive-axle midpoint; base_link at axle height, x forward, z up.\n",
                     "imu_link on the centreline, away from the motor magnetic fields.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_battery_placement_rear_edge(self):
        self.assertEqual(self.ids("docs/a.md", "The battery is centred at 25 percent of the length from the rear.\n", "x"),
                         ["BATTERY-PLACEMENT"])
        for text in ("The battery sits as close to the rear edge as practical, keeping service clearances.\n",
                     "The battery was centred at 25 percent (superseded by P-03 rev18.7 item 9).\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_base_controller_io_rev18_7(self):
        for text in ("Two MB7040 sensors, one per I2C bus.\n", "micro-ROS over USB to the Jetson.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["BASE-CONTROLLER-IO"], text)
        for text in ("Two MaxBotix MB7060 sensors, each on a dedicated STM32 UART at 9600 8N1.\n",
                     "MCU to Jetson over Ethernet, micro-ROS over UDP; micro-ROS over USB on the bench only.\n",
                     "MB7040 on I2C is superseded.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_head_camera_recorded_and_base_camera_tilt(self):
        for text in ("Head camera: ZED 2i on the mast.\n", "The head camera is a ZED X Mini.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["HEAD-CAMERA-IDENTITY"], text)
        self.assertEqual(self.ids("docs/a.md", "The Gemini 336L is tilted 20 degrees up.\n", "openamrobot-docs"),
                         ["CAMERAS"])
        for text in ("Stereolabs ZED Mini (SKU ZED-121210) on the lift carriage, pitch 25 degrees down.\n",
                     "Gemini 336L about 243 mm above the floor, tilted 10 degrees up (positions 5, 10, 15).\n"):
            self.assertEqual(self.ids("docs/a.md", text, "openamrobot-docs"), [], text)

    def test_release_milestones_no_v0_2_or_13_november(self):
        for text in ("v0.2 is the first release built from the harness.\n",
                     "Readiness declaration for v0.2.\n",
                     "Development cycle 2 ends 13 November 2026.\n",
                     "The 14 September to 13 November cycle.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["RELEASE-MILESTONES"], text)
        for text in ("Development cycle 2 ends 20 November 2026 with v2.0.0-rc.1.\n",
                     "The v0.2 release plan is superseded by v2.0.0-rc.1.\n",
                     "The cycle originally ended 13 November (superseded by RELEASE-MILESTONES).\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_lift_check_after_cross_repository_dry_run(self):
        for text in ("- **Lift module:** separate OpenAMRobot 3.0 scope.\n",
                     "Scope: the future OpenAMRobot 3.0 lift controller.\n",
                     "There is no lift in 2.0.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), ["LIFT"], text)
        for text in ("No lift firmware is implemented yet; the CAN3 lift interface is a release gate.\n",
                     "No lift controller exists yet.\n",
                     "Planning groups: arm, arm+lift.\n"):
            self.assertEqual(self.ids("docs/a.md", text, "x"), [], text)

    def test_legacy_label_exempts_compute(self):
        self.assertEqual(self.ids("README.md", "Legacy build: Raspberry Pi 5.\n", "openamr-platform-hw"), [])
        self.assertEqual(self.ids("README.md", "Compute: Raspberry Pi 5.\n", "openamr-platform-hw"), ["COMPUTE"])


if __name__ == "__main__":
    unittest.main()
