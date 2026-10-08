# Checker fixtures

Synthetic files for `tests/test_check_decisions.py`. They contain no plan, audit or supplier
content. `decisions.yaml` here is a fixture register, not the organization register.

| Case | Fixture file | Expected result |
|---|---|---|
| matching value | `decisions_repo/config/params.yaml` (mast_1350) | no finding |
| contradicting value | `decisions_repo/README.md` line 3, `launch/robot.launch.py`, `urdf/robot.xacro`, `package.xml` | one finding each |
| value in an unlisted file type | `decisions_repo/legacy/notes.txt` | not scanned; counted as "not scanned" |
| superseded decision still cited | `decisions_repo/docs/citation.md` line 3 | finding "superseded source still cited"; line 4 (current revision) clean |
| kept history with marker | `decisions_repo/docs/history.md` line 4 | reported as ALLOWED, not silenced |
| legacy exemption | `decisions_repo/docs/history.md` line 5 | no finding |
| open decision | `undecided-value` in history.md | not scanned |
| excluded path | `decisions_repo/CHANGELOG.md` | not scanned |
