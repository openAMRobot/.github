# Documentation fix

Template version: 2. Harness: openAMRobot/.github at `<harness SHA>`.

## Precondition block (post before the first write)

```
repository:       openAMRobot/openamrobot-docs (or the repository that owns the README)
branch:           <contributor branch>, from main
parent SHA:       <main SHA>
pages:            <paths to change>
reason:           decision <ID> in decisions.yaml, or <repository>@<SHA>:<file>:<line>
expected outcome: see below
```

The owning repository is the source of truth for commands, versions, parameters and contracts;
the docs site links to it. If the page and the owning repository disagree and decisions.yaml
does not settle it, stop and report instead of choosing.

## Verified and planned content

Every technical claim the page states or changes is one of two kinds, and the PR shows which:

- **Verified fact:** supported by the owning repository. The PR (and the page, where the page
  cites sources) gives the reference as `<repository>@<SHA>:<file>:<line>` or the decisions.yaml
  entry ID.
- **Planned or experimental content:** a roadmap item, an open decision, an untested
  configuration or a design not yet built. The page labels it **Planned** or **Experimental**
  where it appears, never as current behaviour.

Never invent a technical claim the owning repository does not support. When no source exists,
leave the claim out and report the gap in the PR instead of writing it.

## Task

1. Run `python3 tools/check_decisions.py` and `python3 tools/check_public_extract.py` from the
   harness on the pages; keep the output.
2. Correct only the stated pages. Keep history marked as history (`decision-allow: <ID> <reason>`).
   Label legacy material as legacy rather than deleting it.
3. Run the docs repository's own checks (`scripts/check_docs.sh`, strict MkDocs build).
4. Open a draft PR with the filled template.

No internal document links, prices, personal names, contact data or credentials in any page.
No change to safety guidance beyond removing a contradiction; new safety guidance is written by
the platform lead.

## Expected outcome

- Draft PR changing only the listed pages; both checkers report zero findings on them.
- Every new or changed technical claim carries a source reference in the owning repository or a
  Planned/Experimental label.
- The Not verified section states whether the site build and link check ran.

## Failure rule

A failed precondition stops the task. Report the command, the error and the next step. Do not
fix a different page, a different repository or an unrecorded value. Open an issue labelled
harness when the failure shows a gap in this template or the harness.
