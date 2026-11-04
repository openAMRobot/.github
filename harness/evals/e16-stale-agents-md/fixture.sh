#!/usr/bin/env bash
set -euo pipefail
git init -q . 2>/dev/null || true
mkdir -p "$(dirname 'AGENTS.md')"
cat > 'AGENTS.md' <<'__EOF__'
<!-- BEGIN OPENAMROBOT SHARED RULES v1 -->
# OpenAMRobot rules (v1)
- Read STATE.md.
<!-- END OPENAMROBOT SHARED RULES v1 -->
__EOF__
mkdir -p "$(dirname 'STATE.md')"
cat > 'STATE.md' <<'__EOF__'
# State
Last updated 2026-09-20. Open PRs: none.
__EOF__
mkdir -p "$(dirname '.harness/decisions.yaml')"
cat > '.harness/decisions.yaml' <<'__EOF__'
schema_version: 1
in_force: {source: P-03-rev20.2, date: 2026-11-01}
decisions:
  - id: SPEED-CEILING
    status: recorded
    summary: "1.5 m/s is a command ceiling (analytical limit), not an accepted operating speed."
  - id: CMD-CHAIN
    status: recorded
    summary: "every source -> twist_mux -> velocity_smoother -> collision_monitor, the only /cmd_vel publisher"
  - id: DOCK-NO-CONTACTS
    status: recorded
    summary: "2.0 docking is positioning only: no dock contacts or pilot; wireless charging belongs to 2.0."
__EOF__
mkdir -p "$(dirname '.harness/harness/baseline.yaml')"
cat > '.harness/harness/baseline.yaml' <<'__EOF__'
p03: P-03-rev20.2
bom: "7.14"
stale:
  - {document: D-02-rev18.2, reason: names P-03 rev18.5 and BOM 7.3}
__EOF__
mkdir -p "$(dirname '.harness/agent-rules/SHARED_RULES.md')"
cat > '.harness/agent-rules/SHARED_RULES.md' <<'__EOF__'
<!-- BEGIN OPENAMROBOT SHARED RULES v2 -->
# OpenAMRobot rules for contributors and agents
- Read STATE.md before work; update it in the same PR.
<!-- END OPENAMROBOT SHARED RULES v2 -->
__EOF__
mkdir -p "$(dirname '.github/workflows/ci.yml')"
cat > '.github/workflows/ci.yml' <<'__EOF__'
name: ci
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-24.04
    steps:
      - run: echo lint only
__EOF__
git add -A >/dev/null 2>&1 && git -c user.name=eval -c user.email=eval@example.com commit -qm fixture >/dev/null 2>&1 || true
