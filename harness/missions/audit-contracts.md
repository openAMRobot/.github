# Mission: contracts audit (weekly, read only)

Audit every repository checked out under `.repos/` (read only, default branches, SHAs in `.repos/SHAS.txt`) using the skill harness-ros2-contracts, plus harness-register-and-baseline and harness-protected-paths. Run tools where they are installed in the runner; where a tool is missing, say so in the report instead of guessing results. You change no repository.

## Output contract
- `.harness-out/report.md`: verdict first (three lines), then findings by repository, then what you could not check and why.
- `.harness-out/findings.csv` with columns id, severity, area, repository, file_to_change, value_a, value_b, decision_of_record, fix. IDs are numbered SW-1000 to SW-1999 (the format PREFIX-NUMBER is what tools/sync_audit_issues.py tracks); file_to_change starts with the repository name, e.g. `openamr-platform-sw/README.md`; severity is Blocker, Major or Minor. Only Blocker and Major become issues (tools/sync_audit_issues.py); keep Minor in the report.
- Compare with the previous week's `findings.csv` in `.harness-in/previous/` when present: mark resolved findings, keep IDs stable for findings that persist.
- Each finding names its fix as a task a build mission could do (tier A or B) or a hand-over (tier C, contract, register, hardware).
Owner role for this audit's findings: software-lead.
