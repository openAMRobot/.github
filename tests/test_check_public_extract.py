"""Tests for tools/check_public_extract.py.

Credential-like strings are assembled at run time so that this file itself
contains nothing a secret scanner would report.
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
import check_public_extract as pe  # noqa: E402

AT = "@"
DRIVE = "https://" + "drive" + ".google.com/file/d/abc123/view"
DOCS = "https://" + "docs" + ".google.com/document/d/xyz/edit"
TOKEN = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"
KEY = "AK" + "IA" + "ABCDEFGHIJKLMNOP"


def setUpModule():
    # Tests never write to the real GitHub Actions log or job summary of the CI run.
    patcher = unittest.mock.patch.dict(os.environ)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    for key in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "WATCHDOG_ANNOTATION", "WATCHDOG_ANNOTATIONS"):
        os.environ.pop(key, None)


class Rules(unittest.TestCase):
    def hits(self, text, rel="docs/page.md", allow=(), repository=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return [(f["rule"], f["found"]) for f in pe.scan(tmp, list(allow), repository)]

    def test_google_drive_and_docs_links(self):
        self.assertEqual(self.hits(f"See [plan]({DRIVE}) and {DOCS}.\n"),
                         [("google-drive-link", DRIVE), ("google-drive-link", DOCS)])

    def test_email(self):
        self.assertEqual(self.hits(f"Contact jane.doe{AT}example-lab.org today.\n"),
                         [("email", f"jane.doe{AT}example-lab.org")])

    def test_email_like_code_is_not_an_email(self):
        self.assertEqual(self.hits(f"ros_type ROS_TYPE{AT}gz.msgs.GzType\n"), [])

    def test_phone(self):
        self.assertEqual([r for r, _ in self.hits("Call +49 170 1234567 or tel:+357-22-123456.\n")],
                         ["phone", "phone"])

    def test_versions_dates_and_shas_are_not_phones(self):
        self.assertEqual(self.hits("v1.0.236, 2026-09-28, 8ce9314fa9a404564fa7e954cd84f25bcba2b829, 0.4075 m\n"), [])

    def test_prices(self):
        found = [f for _, f in self.hits("Costs €1,475 or USD 2,049.99 or 300 EUR or $5/mo.\n")]
        self.assertEqual(found, ["€1,475", "USD 2,049.99", "300 EUR", "$5/mo"])

    def test_shell_variables_are_not_prices(self):
        self.assertEqual(self.hits("Run `echo $HOME` and ${VAR}.\n"), [])

    def test_credentials(self):
        text = f"token {TOKEN}\naws {KEY}\napi_key = \"s3cr3tvalue99\"\n-----BEGIN RSA PRIVATE KEY-----\n"
        self.assertEqual([r for r, _ in self.hits(text)], ["credential"] * 4)

    def test_scope(self):
        text = f"mail a.person{AT}lab.org\n"
        self.assertEqual(len(self.hits(text, "README.md")), 1)
        self.assertEqual(len(self.hits(text, "pkg/README.md")), 1)
        self.assertEqual(len(self.hits(text, "assets/diagram.html")), 1)
        self.assertEqual(len(self.hits(text, "web/public/app.js")), 1)
        self.assertEqual(self.hits(text, "src/module.py"), [])
        self.assertEqual(self.hits(text, "docs/image.png"), [])

    def test_allowlist_rule_match_path_and_repository(self):
        allow = pe.load_allowlist(self.write_allow(
            "allow:\n  - {rule: email, match: 'a\\.person@lab\\.org', paths: ['docs/*'],"
            " repositories: ['docs-repo'], reason: organization contact}\n"))
        text = f"mail a.person{AT}lab.org\n"
        self.assertEqual(self.hits(text, allow=allow, repository="docs-repo"), [])
        self.assertEqual(len(self.hits(text, allow=allow, repository="other-repo")), 1)
        self.assertEqual(len(self.hits(text, "README.md", allow=allow, repository="docs-repo")), 1)

    def test_allowlist_needs_reason(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            pe.load_allowlist(self.write_allow("allow:\n  - {rule: email, match: 'x'}\n"))

    def test_organization_allowlist_loads_and_exempts_placeholders(self):
        allow = pe.load_allowlist(ROOT / "public-extract-allowlist.yaml")
        self.assertEqual(self.hits('API_KEY="sk-ant-your-key-here"\n', allow=allow), [])
        self.assertEqual(self.hits(f"info{AT}botshare.ai\n", allow=allow), [])
        self.assertEqual(len(self.hits(f"someone{AT}botshare.ai\n", allow=allow)), 1)

    def test_organization_allowlist_admits_only_notice_lines(self):
        allow = pe.load_allowlist(ROOT / "public-extract-allowlist.yaml")
        self.assertEqual(self.hits(f" * @author A. Writer - writer{AT}uni.example-lab.org\n", "web/public/lib.js", allow=allow), [])
        self.assertEqual(self.hits(f"Copyright (c) 2014 A. Writer <writer{AT}lab.org>, MIT License\n", "README.md", allow=allow), [])
        self.assertEqual(len(self.hits(f"Write to writer{AT}lab.org for a quote.\n", "README.md", allow=allow)), 1)

    def test_public_pricing_is_allowed_only_where_approved(self):
        allow = pe.load_allowlist(ROOT / "public-extract-allowlist.yaml")
        row = "| First Mover - \u20ac5 | tier |\n"
        self.assertEqual(self.hits(row, "README.md", allow=allow, repository=".github"), [])
        self.assertEqual(self.hits(row, "profile/README.md", allow=allow, repository=".github"), [])
        self.assertEqual(len(self.hits(row, "README.md", allow=allow, repository="openamrobot-ui")), 1)
        self.assertEqual(len(self.hits(row, "docs/page.md", allow=allow, repository=".github")), 1)

    def test_handles_are_not_emails(self):
        self.assertEqual(self.hits("Reviewed by @BotshareAI and @panthera-momagdii.\n"), [])

    def write_allow(self, text):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        tmp.write(text)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return tmp.name


class CommandLine(unittest.TestCase):
    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            return pe.main([str(a) for a in args]), out.getvalue()

    def test_exit_codes_and_changed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "docs").mkdir()
            Path(tmp, "docs/a.md").write_text(f"see {DRIVE}\n", encoding="utf-8")
            Path(tmp, "docs/b.md").write_text("clean\n", encoding="utf-8")
            code, out = self.run_main("--root", tmp)
            self.assertEqual(code, 1)
            self.assertIn("Should not be public: google-drive-link (1 finding(s))", out)
            self.assertIn("\n    docs/a.md:1: found 'https://drive.google.com", out)
            self.assertIn("\n  Rule:     Public files do not link to internal Google Drive", out)
            self.assertIn("\n  Fix:      Remove the link", out)
            self.assertIn("WATCHDOG.md#public-extract", out)
            self.assertIn("Public extract summary: 1 finding(s) (google-drive-link 1)", out)
            self.assertIn("result: 1 finding(s)", out)
            changed = Path(tmp, "changed.txt")
            changed.write_text("docs/b.md\n", encoding="utf-8")
            self.assertEqual(self.run_main("--root", tmp, "--changed-files", changed)[0], 0)

    def test_every_rule_has_guidance(self):
        self.assertEqual(set(pe.GUIDE), set(pe.RULES))

    def test_invalid_allowlist_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "allow.yaml")
            bad.write_text("allow:\n  - {rule: nosuchrule, match: x, reason: y}\n", encoding="utf-8")
            self.assertEqual(self.run_main("--root", tmp, "--allowlist", bad)[0], 2)


if __name__ == "__main__":
    unittest.main()
