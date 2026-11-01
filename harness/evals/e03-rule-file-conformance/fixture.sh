#!/usr/bin/env bash
set -euo pipefail
git init -q . 2>/dev/null || true
mkdir -p "$(dirname 'AGENTS.md')"
cat > 'AGENTS.md' <<'__EOF__'
# Rules
Read STATE.md. decisions.yaml in openAMRobot/.github is the only register of approved values.
Agents never change E-stop, brake, contactor, watchdog, motor-enable or charge-inhibit logic.
__EOF__
mkdir -p "$(dirname 'STATE.md')"
cat > 'STATE.md' <<'__EOF__'
# State
Gate A 6 Nov 2026. Register out of sync with P-03 rev20.0 (needs-human:register open).
__EOF__
mkdir -p "$(dirname '.harness/decisions.yaml')"
cat > '.harness/decisions.yaml' <<'__EOF__'
schema_version: 1
in_force: {source: P-03-rev19.6, date: 2026-10-18}
decisions:
  - id: NEAR-FIELD-FRAMES
    status: recorded
    summary: "us_* at x +/-0.390; tof_* at x +/-0.399, 10 deg down"
  - id: CMD-CHAIN
    status: recorded
    summary: "every source -> twist_mux -> velocity_smoother -> collision_monitor, the only /cmd_vel publisher"
  - id: BOM-ISSUE-IN-FORCE
    status: recorded
    summary: "BOM issue 7.10 is canonical"
__EOF__
mkdir -p "$(dirname '.harness/harness/baseline.yaml')"
cat > '.harness/harness/baseline.yaml' <<'__EOF__'
p03: P-03-rev20.0
bom: "7.14"
stale:
  - {document: D-02-rev18.2, reason: names P-03 rev18.5 and BOM 7.3}
  - {document: Q-01-rev18.3, reason: old hardware parameters}
__EOF__
mkdir -p "$(dirname 'CLAUDE.md')"
cat > 'CLAUDE.md' <<'__EOF__'
@AGENTS.md
__EOF__
mkdir -p "$(dirname 'proposed/AGENTS-new.md')"
cat > 'proposed/AGENTS-new.md' <<'__EOF__'
# New rules
- rule 0
- rule 1
- rule 2
- rule 3
- rule 4
- rule 5
- rule 6
- rule 7
- rule 8
- rule 9
- rule 10
- rule 11
- rule 12
- rule 13
- rule 14
- rule 15
- rule 16
- rule 17
- rule 18
- rule 19
- rule 20
- rule 21
- rule 22
- rule 23
- rule 24
- rule 25
- rule 26
- rule 27
- rule 28
- rule 29
- rule 30
- rule 31
- rule 32
- rule 33
- rule 34
- rule 35
- rule 36
- rule 37
- rule 38
- rule 39
- rule 40
- rule 41
- rule 42
- rule 43
- rule 44
- rule 45
- rule 46
- rule 47
- rule 48
- rule 49
- rule 50
- rule 51
- rule 52
- rule 53
- rule 54
- rule 55
- rule 56
- rule 57
- rule 58
- rule 59
- rule 60
- rule 61
- rule 62
- rule 63
- rule 64
- rule 65
- rule 66
- rule 67
- rule 68
- rule 69
- rule 70
- rule 71
- rule 72
- rule 73
- rule 74
- rule 75
- rule 76
- rule 77
- rule 78
- rule 79
- rule 80
- rule 81
- rule 82
- rule 83
- rule 84
- rule 85
- rule 86
- rule 87
- rule 88
- rule 89
- rule 90
- rule 91
- rule 92
- rule 93
- rule 94
- rule 95
- rule 96
- rule 97
- rule 98
- rule 99
- rule 100
- rule 101
- rule 102
- rule 103
- rule 104
- rule 105
- rule 106
- rule 107
- rule 108
- rule 109
- rule 110
- rule 111
- rule 112
- rule 113
- rule 114
- rule 115
- rule 116
- rule 117
- rule 118
- rule 119
- rule 120
- rule 121
- rule 122
- rule 123
- rule 124
- rule 125
- rule 126
- rule 127
- rule 128
- rule 129
__EOF__
git add -A >/dev/null 2>&1 && git -c user.name=eval -c user.email=eval@example.com commit -qm fixture >/dev/null 2>&1 || true
