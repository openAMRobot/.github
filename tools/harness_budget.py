#!/usr/bin/env python3
"""Print a mission's turn and minute limits from harness/policy.yaml budgets as
GitHub step outputs (max_turns=N, timeout_minutes=M). The workflow used to hard-code
the turn limits, and they had drifted from policy (retro ran with 120 turns, policy
says 60; register-sync and sim-analysis had no budget at all).

  harness_budget.py --mission NAME
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as hl  # noqa: E402

BUDGET_OF = {"build": "build", "register-sync": "register_sync", "review": "review", "triage": "triage",
             "retro": "retro", "sim-analysis": "audit", "register-audit": "audit", "dependencies": "audit",
             "contracts": "audit", "impact": "audit", "performance": "audit", "maintainability": "audit"}


def budget(policy, mission):
    key = BUDGET_OF.get(mission)
    entry = (policy.get("budgets") or {}).get(key) if key else None
    if not entry or "max_turns" not in entry or "timeout_minutes" not in entry:
        raise SystemExit(f"no budget with max_turns and timeout_minutes for mission {mission!r}")
    return int(entry["max_turns"]), int(entry["timeout_minutes"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mission", required=True)
    parser.add_argument("--root", default=str(hl.ROOT))
    args = parser.parse_args(argv)
    turns, minutes = budget(hl.load_policy(Path(args.root)), args.mission)
    print(f"max_turns={turns}")
    print(f"timeout_minutes={minutes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
