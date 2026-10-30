#!/usr/bin/env python3
"""Claude Code PreToolUse hook: enforce harness/policy.yaml while an agent works.

Claude Code sends the tool call as JSON on stdin. Exit 0 allows it; exit 2 blocks
it and the message on stderr goes back to the agent. Any error blocks (fail
closed). Environment, set by the harness workflow:
  CLAUDE_PROJECT_DIR   checkout the agent works in (set by Claude Code)
  HARNESS_REPOSITORY   repository name, e.g. openamr-platform-sw
  HARNESS_READ_ONLY    "1" for triage, review and audit missions
This hook is the first line of enforcement. tools/harness_guard.py re-checks the
finished diff, and the agent never holds a push credential.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HARNESS_ROOT / "tools"))
import harness_lib as hl  # noqa: E402

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
OUTPUT_DIR = ".harness-out"
WRITE_VERBS = re.compile(r"(>>?|\btee\b|\bsed\s+-i|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bpatch\b|\bln\b|"
                         r"\bgit\s+apply\b|\bgit\s+checkout\b|\bgit\s+restore\b|\bperl\s+-pi|"
                         r"\bpython3?\s+-c\b|\bnode\s+-e\b|\bdd\b|\binstall\b)")
READ_ONLY_BLOCK = re.compile(r"\bgit\s+(commit|add|stash|rebase|merge|cherry-pick|reset)\b")


def block(message):
    print(f"harness policy: {message}", file=sys.stderr)
    sys.exit(2)


def relative(path, project):
    """Path relative to the checkout after resolving symlinks, so a link inside the
    checkout that points at a protected file is judged by its target."""
    target = Path(path)
    if not target.is_absolute():
        target = project / target
    target = Path(os.path.realpath(target))
    try:
        return target.relative_to(project).as_posix(), target
    except ValueError:
        return None, target


def check_write(path, project, repository, policy, read_only, mission=""):
    rel, absolute = relative(path, project)
    if rel is None:
        scratch = os.environ.get("RUNNER_TEMP")
        if scratch and str(absolute).startswith(str(Path(scratch).resolve()) + os.sep):
            return
        block(f"{absolute} is outside the repository checkout; use {OUTPUT_DIR}/ or $RUNNER_TEMP for scratch files")
    if rel == OUTPUT_DIR or rel.startswith(OUTPUT_DIR + "/"):
        return
    if read_only:
        block(f"this mission is read only; write findings to {OUTPUT_DIR}/ instead of {rel}")
    ok, reason = hl.allowed_write(rel, repository, policy, absolute.exists(), mission)
    if not ok:
        block(reason)


def check_bash(command, project, repository, policy, read_only, mission=""):
    flat = " ".join(command.split())
    # Quotes and backslashes are removed before matching, so "curl" and c\url match curl.
    # Writes into .harness/ are blocked by the write-target check below (tier D).
    bare = re.sub(r"[\'\"\\]", "", flat)
    tokens = set(re.split(r"[\s;&|()`$<>{}]+", bare))
    if re.search(r"/proc/\S*(?:env|\*|\?|\[)", bare) or re.search(
            r"(?:^|[;&|(]\s*)(?:env|printenv|export\s+-p|declare\s+-x|set)(?:\s+-\S+)*\s*(?:$|[|>;&)])", bare) \
            or re.search(r"\bos\.environ\b|\bprocess\.env\b|\bENV\[", bare) and re.search(r"\b(?:python3?|node|ruby|perl)\b\s+-", bare):
        block("printing process environments is not allowed")
    for needle in policy.get("blocked_commands", []):
        word = " ".join(needle.split())
        if not word:
            continue
        if " " in word:
            # A phrase such as "git push" or "rm -rf /": matched anywhere in the unquoted text,
            # ending at a word boundary, so "rm -rf /tmp/x" is not "rm -rf /".
            hit = re.search(r"(?:^|[\s;&|(`])" + re.escape(word) + r"(?=$|[\s;&|)])", bare)
        else:
            # One word such as "curl" or a flag such as "--no-verify": matched as a whole token,
            # so "rsync" never matches "nc".
            hit = word in tokens
        if hit:
            block(f"command contains '{word}', which agents never run")
    if read_only and READ_ONLY_BLOCK.search(flat):
        block("this mission is read only; no git history changes")
    for words in subcommands(command):
        if words and re.search(r"[$`]", words[0]):
            block("the command name is built from a variable or a substitution; write it plainly")
    for target in write_targets(command):
        rel, absolute = relative(target, project)
        if rel is None or rel in (".", "") or rel == OUTPUT_DIR or rel.startswith(OUTPUT_DIR + "/"):
            continue
        if SCRATCH.search(rel):
            continue
        if read_only:
            block(f"this mission is read only; the command may change {rel}")
        probe = rel + "/__probe__" if absolute.is_dir() else rel
        if hl.tier_of(probe, repository, policy) in ("C", "D"):
            ok, reason = hl.allowed_write(probe, repository, policy, absolute.exists(), mission)
            if not ok:
                block(f"shell command may change a protected path. {reason}")


PATH_LITERAL = re.compile(r"""['"]([^'"\s]*[/.][^'"\s]*)['"]""")
ALL_ARGS = {"rm", "rmdir", "truncate", "ln", "install", "touch", "mkdir", "chmod", "chown", "unlink", "shred"}
SEPARATORS = {";", "&&", "||", "|", "&", "\n", "(", ")", "|&"}
INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "bash", "sh"}
# Paths that build and test tools write everywhere, also in read-only missions.
SCRATCH = re.compile(r"^(?:build|install|log|\.verification|\.pytest_cache)(?:/|$)|(?:^|/)__pycache__(?:/|$)")


def subcommands(command):
    """Split a shell command into word lists with a quote-aware tokenizer, so a ; inside
    python3 -c "a; b" stays inside its argument."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    part = []
    for token in tokens:
        if token in SEPARATORS:
            if part:
                yield part
            part = []
        else:
            part.append(token)
    if part:
        yield part


def write_targets(command):
    """Paths a shell command may write. The working directory is tracked per subcommand,
    so `echo x > a; cd b` judges a, and `cd b && echo x > a` judges b/a."""
    targets, cwd = [], ""

    def add(path):
        if path and path != "/dev/null" and not path.startswith("&"):
            targets.append(path if os.path.isabs(path) or not cwd else os.path.join(cwd, path))

    for words in subcommands(command):
        clean, i = [], 0
        while i < len(words):
            word = words[i]
            if word in (">", ">>", ">|", "&>", "&>>") or re.fullmatch(r"\d*>>?", word):
                if i + 1 < len(words):
                    add(words[i + 1].lstrip("|"))
                i += 2
                continue
            if word.startswith(">&") or word in ("<", "<<", "<<<", ">&"):
                i += 2 if word in ("<", "<<", "<<<") else 1
                continue
            clean.append(word)
            i += 1
        if not clean:
            continue
        cmd, args = os.path.basename(clean[0]), [w for w in clean[1:] if not w.startswith("-")]
        if cmd == "cd":
            cwd = os.path.join(cwd, args[0]) if args else ""
        elif cmd in ALL_ARGS:
            for a in args:
                add(a)
        elif cmd == "git" and args[:1] and args[0] in ("checkout", "restore", "rm", "mv"):
            for a in args[1:]:
                add(a)
        elif cmd in ("mv", "cp", "rsync") and args:
            for j, w in enumerate(clean):
                if w in ("-t", "--target-directory") and j + 1 < len(clean):
                    add(clean[j + 1])
                elif w.startswith("--target-directory="):
                    add(w.split("=", 1)[1])
            for a in (args if cmd == "mv" else args[-1:]):
                add(a)
        elif cmd == "tee":
            for a in args:
                add(a)
        elif cmd == "sed" and any(w.startswith("-i") or w == "--in-place" for w in clean):
            for a in args[1:]:
                add(a)
        elif cmd == "dd":
            for w in clean:
                if w.startswith("of="):
                    add(w[3:])
        elif cmd == "tar" and any(w.startswith("-") and ("x" in w or "C" in w) or w in ("x", "--extract") for w in clean):
            for j, w in enumerate(clean):
                if (w == "-C" or w == "--directory") and j + 1 < len(clean):
                    add(clean[j + 1])
            add(cwd or ".")
        elif cmd in INTERPRETERS:
            code = " ".join(clean[1:])
            for literal in PATH_LITERAL.findall(code):
                add(literal)
            for a in args[1:] if args[:1] == ["-"] else []:
                add(a)
    return targets


def main():
    try:
        event = json.load(sys.stdin)
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
        repository = os.environ.get("HARNESS_REPOSITORY", "")
        read_only = os.environ.get("HARNESS_READ_ONLY") == "1"
        policy = hl.load_policy(HARNESS_ROOT)
        tool = event.get("tool_name", "")
        data = event.get("tool_input", {}) or {}
        mission = os.environ.get("HARNESS_MISSION", "")
        if tool in WRITE_TOOLS:
            check_write(data.get("file_path") or data.get("notebook_path") or "", project, repository,
                        policy, read_only, mission)
        elif tool == "Bash":
            check_bash(data.get("command", ""), project, repository, policy, read_only, mission)
    except SystemExit:
        raise
    except Exception as exc:  # fail closed
        block(f"hook error, call blocked: {exc}")
    sys.exit(0)


if __name__ == "__main__":
    main()
