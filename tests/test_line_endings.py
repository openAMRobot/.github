"""Shell scripts keep LF line endings on every checkout (.gitattributes)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def shell_scripts():
    scripts = []
    for rel in git("ls-files", "-z").split("\0"):
        path = ROOT / rel
        if rel and path.is_file():
            with path.open("rb") as handle:
                first = handle.readline(80)
            if rel.endswith((".sh", ".bash")) or (first.startswith(b"#!") and b"sh" in first):
                scripts.append(rel)
    return scripts


class LineEndings(unittest.TestCase):
    def test_every_shell_script_is_marked_lf(self):
        scripts = shell_scripts()
        self.assertIn("rollout/verify.sh", scripts)
        for rel in scripts:
            with self.subTest(script=rel):
                self.assertTrue(git("check-attr", "eol", "--", rel).strip().endswith("eol: lf"), rel)

    def test_autocrlf_checkout_keeps_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp, "src"), Path(tmp, "dst")
            (src / "rollout").mkdir(parents=True)
            shutil.copy(ROOT / ".gitattributes", src / ".gitattributes")
            (src / "rollout" / "verify.sh").write_bytes(b"#!/usr/bin/env bash\necho ok\n")
            git("init", "-q", cwd=src)
            git("add", ".", cwd=src)
            git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "t", cwd=src)
            git("-c", "core.autocrlf=true", "clone", "-q", "--config", "core.autocrlf=true", str(src), str(dst), cwd=tmp)
            self.assertNotIn(b"\r\n", (dst / "rollout" / "verify.sh").read_bytes())


if __name__ == "__main__":
    unittest.main()
