<!-- BEGIN OPENAMROBOT SHARED RULES v2 -->
# OpenAMRobot rules for contributors and agents
Canonical: openAMRobot/.github, agent-rules/SHARED_RULES.md. Copied verbatim into every
repository's AGENTS.md; tools/check_agent_rules.py fails on drift. Each rule names how it is
enforced: [gate: tool], [template: file] or [decides: role]. Roles resolve in maintainers.yaml.

## Sources of record
- Decided values live only in openAMRobot/.github decisions.yaml. No file states a value that
  contradicts it; kept history carries `decision-allow: <ID> <reason>`. [gate: check_decisions.py]
- A decision changes in its source document first, then in decisions.yaml and every flagged
  file in one PR. [decides: the decision's owner]
- Read STATE.md before work in a repository; update it in the same PR. [gate: check_pr_evidence.py]

## Contracts
- Messages, services, actions, schemas, topic names, launch argument names and configuration
  IDs are contracts. They change only through a contract change request issue and one PR that
  updates the contract package and its consumers together. [template: contract change request]
  [decides: software lead]
- New contract proposals stay labelled Proposed until the owner accepts them. [decides: software lead]

## Tests
- Every behaviour change carries a test that fails when the change is reverted; the PR shows
  that failing run. [gate: check_pr_evidence.py] [decides: reviewer]
- A suite that executes zero tests fails. [gate: verify.sh, check_pr_evidence.py]
- skip, xfail and importorskip name a tracking issue on the same line. [gate: verify.sh]
- SKIP or BLOCKED is not PASS. Fixtures and fake hardware are not simulation, physical
  acceptance or release readiness. [template: PR Not verified section]

## Evidence
- Every PR states base SHA, head SHA, exact commands, test counts and a Not verified section.
  [gate: check_pr_evidence.py] [template: .github/PULL_REQUEST_TEMPLATE.md]
- A draft becomes ready only when the evidence check passes on the current head. [gate: check_pr_evidence.py]

## Dependencies and licences
- Nothing is added, removed or upgraded as a side effect. A changed dependency manifest needs
  a Dependencies section naming each change, its licence and source. [gate: check_pr_evidence.py]
- File headers and package.xml licence tags match the repository licence map: MIT software and
  firmware, CERN-OHL-P-2.0 hardware, CC-BY-4.0 documentation. [decides: repository owner]
- The Integration Gate section lists overlapping open PRs, what existing or upstream work was
  reused and what was rejected. Third-party provenance stays intact. [template: PR template]
- LICENSE, LICENSING.md, NOTICE and CODEOWNERS change only in a PR whose task names them.
  [decides: platform lead]

## Safety
- No agent authors or modifies E-stop, brake, contactor, watchdog, motor-enable or
  charge-inhibit logic. Agents report the needed change in an issue. [gate: check_pr_evidence.py]
- A change to those paths needs two human reviewers including the platform lead.
  [gate: check_pr_evidence.py]
- Functional telemetry, status displays and fixtures are never presented as safety evidence.
  [decides: platform lead]
- Automated or untrusted PR jobs never reach motion hardware or secrets. [decides: CI owner]

## Publication
- Public material (docs/, assets/, README.md, any path containing "public") has no internal
  document links, prices, contact data or credentials. [gate: check_public_extract.py]
- It names no private person, customer or partner; the public application name is Use_Case_1.
  [decides: docs owner]

## Agents
- Before any write, state a precondition block: repository, branch, parent SHA, expected
  outcome. [template: agent-prompts/]
- Read-only unless the task says otherwise. [template: agent-prompts/]
- Agent PRs stay draft until the work-package owner writes adopt, adapt or reject in the PR
  thread. [decides: work-package owner]
- The PR's AI disclosure section names the tool and what it produced. [gate: check_pr_evidence.py]
- Commits carry DCO sign-off with the contributor's own identity; never invent an identity,
  exemption or attestation. [gate: DCO check]
- Gate A Teensy/MPU6500 and Gate B STM32/ICM-42688-P stay distinct; Jetson is the 2.0
  compute. [gate: check_decisions.py] Arm vendor SDKs stay behind device packages. [decides: software lead]

## Failure
- A failed precondition (repository, branch, SHA, access, source) stops the task. Report the
  command, the error and the next step; never work around it. [template: agent-prompts/]
- Never merge, force-push, change settings, weaken a check or invent a result. [gate: branch protection]

## Learning
- Every agent or process mistake gets an issue labelled harness. [template: harness mistake form]
- The monthly retro turns harness issues into one PR against this block. [decides: software lead]
<!-- END OPENAMROBOT SHARED RULES v2 -->
