---
name: harness-dependency-hygiene
description: How to audit and fix declared versus used dependencies, pins, vulnerabilities and licences in OpenAMRobot ROS 2, Python, Node and firmware repositories. Use for the weekly dependencies audit and whenever a PR changes package.xml, requirements, package.json, .repos or CMakeLists.txt.
---

# Dependency hygiene

## Declared versus used (ROS 2)
- Every Python import and C++ `find_package` maps to a `<depend>`, `<exec_depend>`, `<build_depend>` or `<test_depend>` in package.xml; every declared dependency is used. Report both directions.
- `rosdep check --from-paths <src> --ignore-src` resolves on Ubuntu 24.04 Jazzy.
- `<test_depend>` holds test-only packages; nothing test-only in `<exec_depend>`.
- package.xml format 3, licence tag matches the licence map (MIT software and firmware, CERN-OHL-P-2.0 hardware, CC-BY-4.0 docs).

## Workspace (openamrobot-manifest)
`vcs validate` on every .repos file; every entry pinned to a tag or SHA in the rc.1 manifest; `colcon list` from the workspace root has no package found twice (issue #8 is the known case; the owner decides the policy).

## Python and Node
`pip-audit` on pinned requirements, `npm audit --omit=dev` for the UI, OSV database for both (`osv-scanner` when it is available in the runner). Report advisories with severity and the fixed version; never upgrade in the audit.

## Licences
List every third-party dependency with its licence. GPL, AGPL, SSPL, non-commercial or unknown licences in shipped code are needs-human:security findings. Keep upstream provenance and NOTICE text intact.

## Fixing
A dependency change is never a side effect (AGENTS.md). One PR per dependency change, tier B, with a Dependencies section: name, old and new version, licence, source URL, why. Security fixes first.
