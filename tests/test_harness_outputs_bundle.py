"""Regression test from the 1 Nov 2026 effectiveness audit (openAMRobot/audits,
2026-11-01-harness-effectiveness): a commit in change.bundle that contains the Claude
credential passed tools/harness_outputs.py, because pack data is zlib compressed, and would
have been uploaded as a workflow artifact of a public repository."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "harness_outputs.py"
FAKE = "sk-ant-oat01-" + "Q" * 40   # built at run time; not a real credential


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


class BundleScrub(unittest.TestCase):
    def make_bundle(self, content, base_content="x = 1\n" * 200):
        tmp = Path(tempfile.mkdtemp())
        repo, out = tmp / "r", tmp / "out"
        out.mkdir()
        git(tmp, "init", "-q", str(repo))
        (repo / "a.py").write_text(base_content)
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "base")
        base = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        (repo / "a.py").write_text(base_content + content)
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-s", "-m", "change")
        git(repo, "bundle", "create", str(out / "change.bundle"), f"{base}..HEAD")
        return out, tmp / "upload"

    def run_tool(self, src, dst, secrets=""):
        env = dict(os.environ, HARNESS_SECRET_VALUES=secrets)
        proc = subprocess.run([sys.executable, "-I", "-S", str(TOOL), "--src", str(src), "--dst", str(dst)],
                              capture_output=True, text=True, env=env, check=True)
        return json.loads(proc.stdout)

    def test_bundle_with_exact_secret_value_is_dropped(self):
        src, dst = self.make_bundle(f"token = '{FAKE}'\n")
        report = self.run_tool(src, dst, secrets=FAKE)
        self.assertNotIn("change.bundle", report["copied"])
        self.assertFalse((dst / "change.bundle").exists())

    def test_bundle_with_secret_like_string_is_dropped(self):
        src, dst = self.make_bundle(f"token = '{FAKE}'\n")
        self.assertNotIn("change.bundle", self.run_tool(src, dst)["copied"])

    def test_clean_bundle_is_copied(self):
        src, dst = self.make_bundle("y = 2\n")
        self.assertIn("change.bundle", self.run_tool(src, dst, secrets=FAKE)["copied"])

    def test_unreadable_bundle_is_dropped(self):
        src = Path(tempfile.mkdtemp())
        (src / "change.bundle").write_bytes(b"# v2 git bundle\nnot a pack")
        self.assertNotIn("change.bundle", self.run_tool(src, src / "up")["copied"])


if __name__ == "__main__":
    unittest.main()
