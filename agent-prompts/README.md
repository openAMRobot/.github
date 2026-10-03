# Agent prompt templates

Each template is a prompt an agent (or a person) runs as written, after filling the
angle-bracket fields. Every template has the same three fixed parts:

1. **Precondition block.** Filled in and posted before the first write. The agent checks each
   line; a mismatch is a failed precondition.
2. **Expected outcome block.** What the run must produce, so the reviewer can compare.
3. **Failure rule.** A failed precondition stops the task. The agent reports the command, the
   error and the next step, and opens an issue with the label harness when the failure shows a
   gap in the harness. It never works around the failure.

Record every run in agent-runs.md with the template name and the harness commit SHA.

| Template | Use |
|---|---|
| [read-only-audit.md](read-only-audit.md) | Compare repositories against decisions.yaml and the plan; write a report, change nothing |
| [push-from-bundle.md](push-from-bundle.md) | Push a prepared, reviewed change set to a contributor branch and open a draft PR |
| [docs-fix.md](docs-fix.md) | Correct a documentation page that contradicts a decision or a repository |
| [evaluator-pass.md](evaluator-pass.md) | Check another agent's PR against the rules before a human reads it |
