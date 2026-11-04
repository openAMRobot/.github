# Mission: register-audit (weekly, read only)

Keep decisions.yaml correct and current against two references: the current state of every repository, and the controlling documents. decisions.yaml is the primary register; the Drive documents are the detailed specifications that must agree with it. You change nothing; you report what a person must reconcile.

## Inputs
- `.harness/decisions.yaml`, `.harness/harness/baseline.yaml`, `.harness/maintainers.yaml`.
- `.repos/<repository>` for every enrolled repository (default branches, SHAs in `.repos/SHAS.txt`).
- `.harness-in/snapshots/`: plain-text snapshots of the controlling documents named in baseline.yaml `snapshots`, each with its sha256 in `.harness-in/snapshots/SHA256SUMS`. A missing or mismatching snapshot is a finding, never a reason to guess.
- `.harness-in/audit-issues.json`: open audit-finding issues, for stable IDs.

## Checks
1. Baseline: baseline.yaml revisions against `in_force` and every entry's `source`; entries citing a revision older than the baseline revision of the same document; `review_by` past due.
2. Register against documents (snapshots): for each recorded entry, does the cited document item say the same value, unit and status? List: same, differs (quote at most 20 words of the document, it is private), not found. Then list decisions the controlling documents state that have no register entry, limited to values, limits, exclusions and part choices that repositories consume.
3. Register against repositories: run `python3 .harness/tools/check_decisions.py --decisions .harness/decisions.yaml --root .repos/<r> --repository <r> --json <file>` for each clone. Report counts per entry and repository. Then look for gaps the patterns miss: a current value of an entry stated differently in code or configuration (for example a frame origin in URDF, a topic name in a launch file) where no check pattern caught it; propose the pattern.
4. Register health: YAML values that parse as mappings because of an unquoted `: `, entries without `check` patterns, `applies_to` globs that match no file in any repository, entries whose owner role has no handle.

## Output contract
- `.harness-out/report.md`: verdict first (in sync, or the number of mismatches by kind), then the four sections.
- `.harness-out/findings.csv` (columns id, severity, area, repository, file_to_change, value_a, value_b, decision_of_record, fix). IDs REG-1000 to REG-1999 (the platform lead owns them). For document mismatches set repository to `audits` and file_to_change to `decisions.yaml`, so the issue stays in the private audits repository; never quote a document in a public repository's issue. Each fix names the paired change: register entry, document and item, and consumers.
