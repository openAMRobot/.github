---
name: harness-maintainability
description: How to measure and improve maintainability (complexity, duplication, dead code, test coverage, documentation drift) in OpenAMRobot repositories with small, safe refactors. Use for the weekly maintainability audit and refactor tasks.
---

# Maintainability

## Measure
- Complexity: radon cc and mi for Python, lizard for C and C++. Flag functions over cyclomatic complexity 15 or 80 lines.
- Duplication: jscpd across a repository; flag blocks over 30 lines duplicated.
- Dead code: vulture for Python with a confidence threshold of 80; unused launch files, configs and scripts by searching references.
- Coverage: pytest-cov line and branch coverage per package; gcov or lcov for C++ host builds. Report only; no gate before v2.0.0.
- Mutation testing on pure-logic modules (mutmut for Python) once a month: surviving mutants show weak tests.
- Docs drift: README commands that do not run, STATE.md entries that contradict the issue and PR state, docs pages naming files that do not exist.
Write `.harness-out/maintainability.json` per package and `.harness-out/findings.csv` for the worst items.

## Refactor rules
- Only code that has tests, or add characterisation tests first in a separate commit.
- One refactor kind per PR (extract function, remove duplication, delete dead code, rename). No behaviour change: same test count, all green, revert run not needed but say so.
- Never refactor tier C code; report it.
- Prefer deleting code to adding abstraction. Prefer a maintained upstream package (ros2_control, Nav2, MoveIt 2, tf2, diagnostic_updater, nav2_simple_commander) to local reimplementations; propose the swap as tier B with a licence check.
