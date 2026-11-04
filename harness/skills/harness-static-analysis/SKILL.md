---
name: harness-static-analysis
description: Static analysis and lint tools for OpenAMRobot code (Python, C++, launch, YAML, workflows, shell, firmware C) and how to introduce them without breaking CI. Use for lint-fix tasks, CI hardening and review.
---

# Static analysis

## Tools by file type
- Python: ament_flake8 and ament_pep257 (the CI contract), plus ruff for speed and mypy on packages with type hints. Report-only first.
- C++: ament_cpplint, ament_uncrustify or ament_clang_format (whichever the package uses; never switch formatter in passing), clang-tidy with the compile database from `colcon build --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON`, cppcheck.
- Firmware C: cppcheck with `--enable=warning,portability` and MISRA-style review notes; GCC `-Wall -Wextra -Werror` in host-test builds. Report only: firmware is tier C.
- XML: ament_xmllint. YAML: yamllint. Workflows: actionlint and the organization's check_workflow_policy.py. Shell: shellcheck. Markdown: markdownlint where docs use it.

## Introducing a tool without a big bang
1. Add it report-only in CI with a baseline count.
2. Fix findings in small tier A or B PRs by package, most-depended-on package first.
3. When the count reaches zero, make it blocking in one PR.
Never add blanket ignores. A per-line or per-file suppression names its issue.

## Fix rules
Lint fixes must not change behaviour: the full test suite passes before and after with the same count. Do not mix lint fixes with logic changes in one commit.
