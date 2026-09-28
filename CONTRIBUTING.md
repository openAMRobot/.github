# Contributing to OpenAMRobot

OpenAMRobot is an open dual-arm mobile manipulator. Software and firmware are MIT, hardware is
CERN-OHL-P-2.0 and documentation is CC-BY-4.0. Every contribution, written by a person or with
an AI tool, passes the same automated checks before a maintainer reads it. This page is the
whole path. Engineering detail lives in the
[Engineering Quality Standard](ENGINEERING_QUALITY_STANDARD.md); the rules the checks enforce
are in [AGENTS.md](AGENTS.md).

## 1. Find a task

- Look for issues labelled
  [good first issue](https://github.com/search?q=org%3AopenAMRobot+label%3A%22good+first+issue%22+state%3Aopen&type=issues).
  Each one names the files, what "done" means, the command that verifies it and the reviewer.
- Areas and where they live:

  | Area | Repository |
  |---|---|
  | documentation | openamrobot-docs |
  | navigation and bring-up | openamr-platform-sw |
  | base firmware | openamr-platform-fw |
  | hardware (CAD, BOM, wiring) | openamr-platform-hw, openamr-upperbody-hw |
  | interfaces (messages, schemas) | openamrobot-interfaces |
  | manipulation | openamrobot-manipulation |
  | operator UI | openamrobot-ui |
  | manifest and release | openamrobot-manifest, openamrobot-release |
  | CI and this harness | .github |

- For anything larger, open a **work package** issue first and wait for the area owner to
  agree the scope. To change a message, schema, topic name, launch argument name or
  configuration ID, open a **contract change request** instead.
- Before you start, read the repository's STATE.md (if it has one) and check open pull
  requests for the same work.

## 2. Set up

1. Sign the contributor agreement once: see [CLA.md](CLA.md).
2. Fork the repository and create **one branch per work package**.
3. Sign off every commit: `git commit -s`. The sign-off certifies the [DCO](DCO.md) with your
   own name and e-mail.

## 3. Make the change

- Add a test that fails without your change. A test run that executes zero tests counts as a
  failure. If you must skip a test, name the tracking issue on the same line.
- Run the repository's verification (`tools/verify.sh`, or the command in its README).
- Decided values (heights, parts, topic names and so on) come from
  [decisions.yaml](decisions.yaml). If your change disagrees with it, the check will say so;
  raise it in the work package rather than editing around it.
- Do not add, remove or upgrade a dependency unless the task asks for it.
- Do not change E-stop, brake, contactor, watchdog, motor-enable or charge-inhibit logic
  unless the platform lead has agreed it in the issue; such changes need two human reviewers.

## 4. Open a draft pull request

Open the PR as a **draft** and fill in every section of the template: work package,
Integration Gate (what existed, what you reused), tests, evidence (base SHA, head SHA, exact
commands, test counts), dependencies, safety impact, STATE.md, Not verified and AI disclosure.

## 5. What the automated checks verify

| Check | Fails when |
|---|---|
| repository-quality | governance files missing, merge markers, invalid JSON or XML |
| decisions of record | a changed file states a value that contradicts decisions.yaml |
| public extract | docs, assets, README or public files contain internal document links, prices, e-mail addresses, phone numbers or credential-like strings |
| shared agent rules | AGENTS.md differs from the organization's shared block |
| PR evidence (one comment, updated on each push) | a template section is empty, SHAs or commands are missing, tests changed without a reported run, a dependency changed without a note, safety files changed without two human reviewers |
| quality/test | build, lint or tests fail, or zero tests ran |
| DCO and contributor agreement | a commit lacks sign-off, or no agreement is on record |

## 6. From draft to ready

Mark the PR **ready for review** when every check is green on the current head and the
evidence comment says PASS. A PR prepared by an AI agent stays draft until the work-package
owner writes adopt, adapt or reject in the thread.

## 7. Who reviews what

| Change | Reviewer (role in [maintainers.yaml](maintainers.yaml)) |
|---|---|
| platform, hardware, firmware, decisions.yaml | platform lead |
| robot software, AI, interfaces, agent rules | software lead |
| workflows, verify.sh, quality gates | CI owner |
| manifest, release, installation | release owner |
| documentation site | documentation owner |
| safety paths | two humans, including the platform lead, who reviews last |

A maintainer merges; approval or a green check alone does not accept a contribution.

## Legal, conduct and contact

Contributions are governed by the [IP Policy](IP_POLICY.md), the
[Individual](INDIVIDUAL_CONTRIBUTOR_AGREEMENT.md) or
[Corporate](CORPORATE_CONTRIBUTOR_AGREEMENT.md) Contributor Agreement, the
[AI contribution policy](AI_CONTRIBUTION_POLICY.md) and the
[third-party policy](THIRD_PARTY_POLICY.md). Identify any material you did not create
yourself with its source and licence. Do not submit secrets, personal data or confidential
material. Follow the [Code of Conduct](CODE_OF_CONDUCT.md); report security issues through
[SECURITY.md](SECURITY.md). Questions about contribution rights: info@botshare.ai.
