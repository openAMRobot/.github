# OpenAMRobot Engineering Quality Standard

**Status:** Adopted  
**Version:** 0.2  
**Owner:** OpenAMRobot maintainers / Botshare Ltd  
**Scope:** All active repositories in the `openAMRobot` GitHub organization  
**Supersedes:** the earlier draft "07 Engineering Standards, CI/CD and Testing"

This document is built on the 4 September 2026 audit of the actual repositories and replaces the earlier assumption-based draft entirely.

## 1. Purpose

This standard defines one enforceable quality contract for OpenAMRobot
repositories. GitHub Actions is the primary enforcement mechanism, but
quality is demonstrated through declared evidence: review, build, tests,
simulation, hardware validation, documentation and release records.

Repositories remain the source of truth for implementation-sensitive
information. The documentation site explains and teaches; it does not
duplicate commands, versions, interfaces or configuration owned by a
component repository.

Normative terms **MUST**, **SHOULD** and **MAY** express mandatory,
recommended and optional requirements.

## 2. Current baseline and immediate gaps

Audit of the active organization repositories on 4 September 2026 found:

- CI currently exists in openamrobot-docs, openamrobot-ui and openamrobot-release only.
- .github contains strong governance and IP policies, but no reusable workflows or workflow templates.

- openamrobot-ui builds successfully, but lint is not enforced and its test command explicitly succeeds with an empty test suite.
- openamrobot-docs has the strongest current pipeline: strict MkDocs build, documentation checks, offline link validation and Pages deployment.

- openamrobot-release is manually triggered and builds from prepared \*-main.zip inputs; it does not resolve immutable component commits itself.
- openamrobot-manifest/openamrobot.repos tracks main, so it describes a development workspace, not a reproducible release.

- Platform software, firmware, hardware, interfaces, communication, manipulation and upper-body repositories currently have no repository CI workflow.
- Several new active repositories lack local CODEOWNERS, CHANGELOG.md and SECURITY.md files. Organization defaults should be linked or inherited where GitHub supports this; CODEOWNERS must remain repository-local.

Therefore, no current repository should be labelled "production-ready"
solely because it builds. The initial objective is a truthful,
integration-ready baseline.

## 3. Repository classification

Every repository MUST declare exactly one type and one lifecycle state
in .openamrobot/quality.yaml.

**Types:**

- software — ROS 2 or other runtime software
- firmware — embedded firmware

- hardware — CAD, PCB, electrical, BOM and manufacturing source
- interface — ROS messages, services, actions and schemas

- ui — browser or operator interface
- documentation — documentation hub

- manifest — workspace and compatibility definition
- release — product-level release assembly

- governance — organization policies and shared automation
- scaffold — planned component without a usable implementation

**Lifecycle states:** incubating, active, maintenance, deprecated,
archived.

Scaffold repositories MUST say clearly that they are not usable
components and MUST NOT claim integration or release readiness.

## 4. Readiness levels

Use OpenAMRobot **Readiness Levels**, not generic "ROS Quality Levels."
REP-2004 already uses numbered package quality levels with Level 1 as
the highest; reversing that order would create avoidable confusion.

| **Level**                  | **Meaning**                                                   | **Minimum evidence**                                                                |
|----------------------------|---------------------------------------------------------------|-------------------------------------------------------------------------------------|
| **R0 — Experimental**      | Prototype or scaffold                                         | Ownership, licence, scope, limitations                                              |
| **R1 — Development**       | Builds or validates reproducibly                              | Baseline CI, review, documentation, unit/static tests where applicable              |
| **R2 — Integration-ready** | Compatible with a declared ecosystem baseline                 | R1 plus interface, integration and simulation/HIL evidence as applicable            |
| **R3 — Release-validated** | Included in a frozen OpenAMRobot release for a declared scope | R2 plus immutable manifest, release evidence, known limitations and human approvals |

R3 means **validated for the explicitly declared release scope**. It
does not claim legal compliance, functional safety certification, CE
conformity or suitability for unsupervised operation.

Readiness MUST be evidence-based. A repository may not claim a level if
a mandatory check is skipped, allowed to pass without tests, or
supported only by undocumented manual knowledge.

## 5. Common repository contract

Every active, non-archived repository MUST contain:

- README.md with purpose, lifecycle, boundaries, supported platform/revision, quick verification and known limitations;
- applicable LICENSE, LICENSING.md and NOTICE.md information;

- local .github/CODEOWNERS;
- a pull-request workflow calling the organization's reusable baseline workflow;

- .openamrobot/quality.yaml;
- CHANGELOG.md for versioned or released components;

- repository-specific build, test and safety instructions where applicable.

Organization-wide governance documents MUST remain canonical in .github.
Repositories SHOULD link to them instead of copying divergent versions.

Minimum metadata:

schema_version: 1

repository:

type: software

lifecycle: active

readiness: R1

owners: \[platform-software\]

compatibility:

ubuntu: "24.04"

ros: jazzy

evidence:

build: required

unit_test: required

integration_test: planned

simulation: planned

hardware: not_applicable

safety_impact: motion

documentation:

source_of_truth: README.md

The schema MUST use only required, planned or not_applicable. Every
not_applicable decision MUST be justified in the repository
documentation.

## 6. Required quality gates by repository type

| **Type**         | **Required PR gates**                                                                                                                     |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Software / ROS 2 | format, lint, dependency resolution, colcon build, unit tests, package metadata; launch/integration tests when claiming R2                |
| Firmware         | reproducible build, format/lint, static analysis, unit tests where feasible, target/config validation; HIL evidence for R2 motion control |
| Hardware         | directory and filename rules, source-file presence, BOM schema, revision consistency, generated/export validation where toolable          |
| Interface        | interface build, lint, schema validation, compatibility/change classification and consumer integration test before R2                     |
| UI               | locked install, lint, non-empty tests, production build, API/schema contract tests and local-link checks                                  |
| Documentation    | strict build, frontmatter/schema, internal links, navigation and canonical-source checks                                                  |
| Manifest         | syntax, reachable repositories, immutable refs for release manifests, duplicate/path checks and full workspace build                      |
| Release          | immutable inputs, component evidence verification, archive validation, checksums, manifest, known limitations and release notes           |

Checks MUST be named consistently so branch rules can require them:
quality/baseline, quality/build, quality/test, quality/docs, and
type-specific checks such as quality/simulation.

## 7. Test and validation model

OpenAMRobot uses a robotics validation ladder:

1.  **Static:** formatting, lint, schema, dependency and licence checks.

2.  **Unit:** deterministic functions, parsers, planners, controllers
    > and utilities.

3.  **Integration:** ROS nodes, topics, services, actions, process
    > lifecycle and failure handling.

4.  **Simulation:** representative robot behavior, navigation, docking
    > and recovery with measurable acceptance criteria.

5.  **HIL:** controller, timing, communications, sensors and actuator
    > interfaces using controlled hardware.

6.  **Physical validation:** supervised tests on the declared robot
    > revision.

PR CI SHOULD finish within 10 minutes and contain fast deterministic
gates. Main/nightly workflows MAY run longer integration and simulation
matrices. HIL and physical tests require controlled scheduling and
recorded results; they MUST NOT automatically drive an unattended robot
after every commit.

Safety-relevant changes involving motion, power, batteries, actuators,
safety I/O or autonomous behavior require an explicit PR safety-impact
statement and appropriate validation evidence. A software PASS is never
equivalent to physical or functional-safety approval.

**Generated command plans are safety-relevant.** Any component that
turns natural language, an LLM response or any other non-deterministic
source into robot actions carries safety_impact: motion regardless of
which repository it lives in, and MUST declare a policy-validation layer
between generation and execution. Building and passing lint is not
evidence for this class of change.

## 8. Organization automation architecture

The .github repository MUST provide:

.github/workflows/

reusable-baseline.yml

reusable-ros2.yml

reusable-ui.yml

reusable-firmware.yml

reusable-hardware.yml

reusable-docs.yml

reusable-manifest.yml

reusable-release.yml

workflow-templates/

ros2-ci.yml

ui-ci.yml

firmware-ci.yml

hardware-ci.yml

docs-ci.yml

Reusable workflows are the maintained implementation. Workflow templates
only bootstrap thin caller files in each repository. External actions
MUST be allow-listed and pinned to a trusted version; high-risk release
jobs SHOULD use immutable commit SHAs.

Default branches MUST require pull requests, required quality checks,
resolved review conversations and CODEOWNERS review for owned paths.
Direct pushes and bypasses MUST be restricted and documented.

**Single-maintainer exception.** Where a repository has one maintainer,
required checks still apply in full and the CODEOWNERS review
requirement is waived until a second maintainer exists. The waiver MUST
be recorded in quality.yaml and reviewed when a second maintainer is
added. Checks are never waived, for anyone, including the founder.

## 9. Interfaces, manifest and releases

openamrobot-interfaces is the contract authority. Breaking interface
changes MUST be identified in the PR, versioned, documented and tested
against known consumers. Repository-local success alone is insufficient
for an R2 interface change.

Two manifests are required:

- **Development manifest:** may track main for integration work.
- **Release manifest:** MUST pin every component to an immutable commit SHA or signed tag and record hardware revision, interface version, test-evidence references and licence mapping.

The release pipeline MUST fetch components from the release manifest. It
MUST NOT construct a release from unspecified main branch archives or
manually prepared inputs without recorded source SHAs.

A product release requires:

- immutable component refs;
- full ecosystem build/integration result;

- component and product versions;
- MANIFEST.json and SHA-256 checksums;

- release notes and known limitations;
- declared hardware revision and validation status;

- SBOM/provenance for generated software artifacts when practical;
- named human approval for hardware and safety evidence.

## 10. Documentation contract

Continue enforcing the existing layer rule in
openamrobot-docs/docs/DOCUMENTATION_STANDARD.md:

- repositories own exact commands, versions, parameters, interfaces, architecture specifications and component test evidence;
- the documentation site owns learning paths, concepts, tutorials and cross-component explanations;

- one command or technical fact has one canonical home.

Machine-generated ecosystem pages MAY consume .openamrobot/quality.yaml
and CI results. Generated status MUST show timestamps and evidence links
and MUST never convert planned work into a PASS.

## 11. Immediate implementation plan

### Phase 0 — truthful inventory (immediate)

1.  Add .openamrobot/quality.yaml schema and validator to .github.

2.  Classify every active repository by type, lifecycle and initial
    > readiness.

3.  Mark planned repositories such as openamrobot-comm as scaffold/R0
    > until usable code and tests exist.

4.  Add missing local CODEOWNERS and remove placeholder release versions
    > such as vX.X.X from active documentation.

### Phase 1 — baseline enforcement

1.  Implement reusable-baseline.yml and thin caller workflows.

2.  Enforce metadata, required files, licence mapping, Markdown links,
    > secrets detection and PR metadata.

3.  Replace UI's --passWithNoTests with real tests before claiming R1.

### Phase 2 — three pilots

Apply type-specific workflows to:

1.  openamr-platform-sw — ROS 2 build/test and one launch or simulation
    > smoke test;

2.  openamrobot-interfaces — interface build plus consumer compatibility
    > test;

3.  openamrobot-docs — retain the strong existing pipeline and add
    > metadata/canonical-source validation.

Use openamrobot-ui as the fourth early pilot because it already has CI
and exposes the empty-test gap.

### Phase 3 — reproducible ecosystem

1.  Add CI to openamrobot-manifest that imports and builds the complete
    > development workspace.

2.  Introduce an immutable release-manifest format.

3.  Refactor openamrobot-release to resolve sources from that manifest
    > rather than \*-main.zip files.

### Phase 4 — firmware and hardware

Add firmware builds/static checks, hardware BOM/revision validators and
documented HIL/physical validation records. Do not block early
contributors on unavailable commercial CAD tools; automate open and
deterministic checks first.

### Phase 5 — release assurance

Add release artifacts, checksums, SBOM/provenance, compatibility
dashboard generation and formal R3 approval records.

## 12. Definition of done for initial adoption

The standard is operational, not merely published, when:

- every active repository has valid metadata, lifecycle/readiness status and a local CODEOWNERS file;
- every active implementation repository calls an organization-maintained workflow;

- required checks are enforced on default branches;
- the three pilot repositories pass their type-specific pipelines;

- the development manifest builds in CI;
- the next product release is generated from immutable component refs;

- no readiness badge claims evidence that CI or recorded validation cannot demonstrate.

## 13. Cycle schedule, workstream H

The phases above map onto the 14 September to 13 November cycle as
workstream H. Lead: Documentation & Release Lead, executed by the DevOps
members of that team.

| **\#** | **Phase** | **Deliverable**                                                                                                                                                                                                                                                         | **Due**                        |
|--------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| **H0** | 0         | Truthful inventory: quality.yaml schema and validator in .github, every active repository classified by type, lifecycle and initial readiness, openamrobot-comm marked scaffold/R0, missing local CODEOWNERS added, vX.X.X placeholders removed                         | 13 Sep, before the cycle opens |
| **H1** | 0         | This standard ratified as v1.0 binding, readiness levels and type taxonomy adopted across the plan set, licence mapping decided including CERN-OHL for hardware                                                                                                         | 18 Sep                         |
| **H2** | 1         | reusable-baseline.yml plus thin caller workflows in every active repository. Metadata, required files, licence mapping, Markdown links, secrets detection and PR metadata enforced. Check names fixed                                                                   | 25 Sep                         |
| **H3** | 2         | **Contribution gate active.** Pilots live: openamr-platform-sw, openamrobot-interfaces, openamrobot-docs, plus openamrobot-ui as fourth. Branch protection with required checks on default branches. UI --passWithNoTests replaced with real tests. **I6 freezes here** | 2 Oct                          |
| **H4** | 2         | reusable-docs.yml and reusable-ui.yml complete: frontmatter and schema validation, canonical-source checks, navigation checks, UI contract tests                                                                                                                        | 9 Oct                          |
| **H5** | 4         | reusable-firmware.yml: reproducible build, format and lint, static analysis, host unit tests, target and config validation. Firmware repositories onto CI                                                                                                               | 16 Oct                         |
| **H6** | 4         | reusable-hardware.yml: directory and filename rules, source-file presence, BOM schema, revision consistency, exports where toolable. Open and deterministic checks only, no commercial CAD dependency                                                                   | 23 Oct                         |
| **H7** | 3         | openamrobot-manifest CI imports and builds the complete development workspace. Immutable release-manifest format defined                                                                                                                                                | 30 Oct                         |
| **H8** | 3         | openamrobot-release refactored to resolve sources from the release manifest. MANIFEST.json, SHA-256 checksums, release notes and known limitations generated, not hand-written                                                                                          | 6 Nov                          |

**Phase 5 does not fit this cycle and is not scheduled.** SBOM and
provenance, the compatibility dashboard and formal R3 approval records
go to ROADMAP-v0.3.md. Saying so now is cheaper than discovering it on
10 November.

**Readiness declaration for v0.2.** The four pilot repositories target
**R2**. Every other active repository targets **R1**. **No component
claims R3 in this cycle.** v0.2 is the first release built from
immutable component refs, which is the precondition for R3, not the
evidence for it. A component that builds is R1, and building has never
been the difficult part.

## 14. How this standard binds the plan set

- **00 Master Coordination Plan:** interface contract **I6** is this standard. Producer: workstream H. Consumers: every workstream. Frozen 2 Oct with H3.
- **02 Execution Plan:** workstream H carries H0 to H8. Every other workstream's definition of done resolves to §6 and §7 of this document, by repository type rather than by workstream.

- **05 Architecture References:** AD-15 records the decision and its rationale.
- **06 Documentation Information Architecture:** the documentation type gates in §6 are what enforce D2's page template, track labelling and canonical-source rule mechanically instead of by review habit.

- **Readiness levels replace informal status language everywhere.** "Working", "done" and "production-ready" are not statuses. R0 to R3 with declared evidence are.

## References

- [<u>OpenAMRobot Documentation Standard</u>](https://github.com/openAMRobot/openamrobot-docs/blob/main/docs/DOCUMENTATION_STANDARD.md)
- [<u>OpenAMRobot organization governance</u>](https://github.com/openAMRobot/.github)

- [<u>ROS REP-2004: Package Quality Categories</u>](https://ros.org/reps/rep-2004.html)
- [<u>ROS-Industrial</u> <u>industrial_ci</u>](https://github.com/ros-industrial/industrial_ci)

- [<u>GitHub: Reuse workflows</u>](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [<u>GitHub: Organization workflow templates</u>](https://docs.github.com/actions/sharing-automations/creating-workflow-templates-for-your-organization)

- [<u>GitHub: Artifact attestations</u>](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
