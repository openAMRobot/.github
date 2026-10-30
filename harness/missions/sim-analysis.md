# Mission: sim-analysis

Read last night's simulation results (`.harness-in/sim/*.json` and failure logs) next to the previous 7 nights. You change no code.

For each failed or regressed scenario (harness-simulation-validation rules): decide whether it is a new regression (name the commits between the last green and the first red run from the manifest pins), a known issue (link it), an infrastructure problem (runner, timeout, real-time factor below 0.5) or flaky (differing results on identical inputs). Write `.harness-out/findings.csv` (id SW-5000 to SW-5999, severity, area, repository, file_to_change, value_a: expected, value_b: observed, decision_of_record, fix) and `.harness-out/report.md` (one paragraph per scenario). Never call a simulated result physical evidence.
