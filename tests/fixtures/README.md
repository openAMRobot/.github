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

## Daily report fixtures

`watchdog_daily/` serves `tests/test_watchdog_daily.py`. `responses.json` maps each request URL
to the status, headers and body the fake API returns; the field layout is that of GitHub REST
API responses recorded for openAMRobot/.github on 2026-10-29, trimmed, with synthetic
repositories, numbers and logins. `previous.json` is a synthetic earlier `daily.json`.

| Case | Fixture | Expected result |
|---|---|---|
| green and red runs, two pages, a fork run, a run outside 7 days | `fixture-alpha` runs | latest per workflow, 50% green, fork and old run not counted |
| draft and stale pull requests | `fixture-alpha` pulls #5, #3 | #5 draft; #3 stale (18 days) |
| rc.1 issues | `fixture-alpha` issues #7 (label), #8 (title) | both listed; the pull request entry #3 is not an issue |
| unreadable repository | `fixture-beta` (404) | not measured; run INCOMPLETE |
| issues disabled | `fixture-gamma` (410) | measured, "issues disabled" |
| rate limit and server error | `fixture-delta` (403 with reset, then 502) | waits, retries, measured |

