#!/usr/bin/env python3
"""Shared helpers for the AI harness: policy loading, path globs and tiers.

Used by tools/harness_guard.py, tools/harness_select.py and the Claude Code
PreToolUse hook harness/claude/hooks/guard_tool.py. Standard library plus PyYAML,
like the other tools. No network.
"""
import fnmatch
import re
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
TEST_PATH = re.compile(r"(^|/)(tests?)(/|$)|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)test_[^/]*\.(cpp|cc|c)$")


def load_yaml(path):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_policy(root=ROOT):
    """Policy with maintainers.yaml safety_paths merged into tier C."""
    root = Path(root)
    policy = load_yaml(root / "harness" / "policy.yaml")
    maintainers = load_yaml(root / "maintainers.yaml")
    tier_c = policy["tiers"]["C"]
    tier_c["paths"] = list(tier_c.get("paths", [])) + list(maintainers.get("safety_paths", []))
    return policy


@lru_cache(maxsize=512)
def glob_regex(pattern):
    """Translate a ** glob into a regex matched against a POSIX relative path."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append(r"(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(r".*")
            i += 2
        elif pattern[i] == "*":
            out.append(r"[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches(path, patterns, broad=False):
    """True when path matches a pattern. broad=True also applies fnmatch semantics
    (a * crosses directories), as tools/check_pr_evidence.py does for safety_paths;
    the protected tiers use it so a directory such as safety_monitor/ is covered."""
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if any(glob_regex(p).match(path) for p in patterns):
        return True
    return broad and any(fnmatch.fnmatchcase(path, p) or fnmatch.fnmatchcase(path, p.replace("**/", ""))
                         for p in patterns)


def is_test_path(path):
    return bool(TEST_PATH.search(path.replace("\\", "/")))


def tier_of(path, repository, policy):
    """Tier of one changed path in one repository: D, C, A or B."""
    tiers = policy["tiers"]
    if matches(path, tiers["D"].get("paths", []), broad=True):
        return "D"
    if repository in tiers["C"].get("repositories", []) or matches(path, tiers["C"].get("paths", []), broad=True):
        return "C"
    if matches(path, tiers["A"].get("paths", [])) and not matches(path, policy.get("dependency_manifests", [])):
        return "A"
    return "B"


def highest(tiers):
    return max(tiers, key=TIER_ORDER.__getitem__) if tiers else "A"


def mission_allows(path, repository, policy, mission):
    """True when the mission has an explicit exception for this path (policy.yaml
    missions.<name>.allow_paths, only in missions.<name>.repository)."""
    cfg = (policy.get("missions") or {}).get(mission or "", {}) or {}
    return bool(cfg.get("allow_paths")) and repository == cfg.get("repository") and matches(path, cfg["allow_paths"])


def allowed_write(path, repository, policy, exists, mission=None):
    """Whether an agent may write this path while it works. Returns (ok, reason).

    Tier D: never, except a path a mission is explicitly allowed (register-sync may
    edit decisions.yaml and its tests in openAMRobot/.github). Tier C: only a new file
    on a test path. A and B: yes.
    """
    tier = tier_of(path, repository, policy)
    if tier == "D" and mission_allows(path, repository, policy, mission):
        return True, f"{path} is tier D, allowed for the {mission} mission by policy"
    if tier == "D":
        return False, f"{path} is tier D (governance, register, licence or harness): agents never change it"
    if tier == "C":
        if not exists and is_test_path(path):
            return True, f"{path} is a new test file for a tier C area"
        return False, (f"{path} is tier C (safety, motion, firmware, hardware or contract): a person writes "
                       "this change. Write a test in a new file under test/ or report the need in the run "
                       "output as needs-human:safety")
    return True, f"{path} is tier {tier}"


DEFAULT_BOT = "openamrobot-harness[bot]"


def bot_login():
    """The harness App's bot login (repository variable HARNESS_BOT_NAME, default
    openamrobot-harness[bot], the same default the workflow uses for git)."""
    import os
    return os.environ.get("HARNESS_BOT_NAME") or DEFAULT_BOT


def is_harness_comment(comment, bot_login):
    """A comment counts as the harness's own only when the harness App's bot wrote it.
    Anyone can type the hidden marker; nobody else can post as the bot."""
    user = comment.get("user") or {}
    return bool(bot_login) and user.get("type") == "Bot" and user.get("login", "").lower() == bot_login.lower()
