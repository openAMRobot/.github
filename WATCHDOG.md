# The OpenAMRobot Watchdog

The Watchdog is a set of automatic checks. It reads the files in a repository and tells you
when something disagrees with what the project has agreed. For every finding it tells you what
it found, why that matters and exactly how to fix it.

## What the Watchdog is and why OpenAMRobot uses it

OpenAMRobot is spread over many repositories: software, firmware, hardware files and
documentation. The approved technical decisions (which computer, which LiDAR, which release
dates, what is not in release 2.0) are written down in one place:
[decisions.yaml](decisions.yaml), the *decisions register*. The platform lead approves every
entry.

The Watchdog compares every repository with that register. When a README, a launch file or a
bill of materials still names an old part or an old value, the Watchdog points to the exact
file and line. This catches drift early, before it confuses a builder or a reviewer, and it
saves review time: reviewers do not have to remember every decision.

The checks are plain Python scripts in [tools/](tools/). They use no AI and no network. They
only read files and never change them.

## What it is not

- It is **not** safety evidence. A clean result does not show that a robot is safe.
- It is **not** electrical, mechanical or release evidence. It does not test hardware,
  calculate loads or decide that a release is ready.
- It checks **textual consistency only**: that the words in a file agree with the register.
  The people named in each register entry review the substance.

## The checks

| Check | What it looks at | Why it matters | Typical finding | How to fix | Who owns it |
|---|---|---|---|---|---|
| <a id="decisions-of-record"></a>Decisions of record (`tools/check_decisions.py`) | Text files covered by each entry in [decisions.yaml](decisions.yaml) | Builders and reviewers must see the approved value, not an old one | `Mismatch with approved decision: COMPUTE (14 finding(s))`, then `README.md:44: found 'Raspberry Pi 5'` | Correct the line, or label it as history with an accepted word (table below), or propose a decision change | Each entry's `owner` role, usually the platform lead |
| <a id="public-extract"></a>Public extract (`tools/check_public_extract.py`) | `docs/`, `assets/`, every `README.md` and any path containing `public` | Public pages must not leak internal links, personal contact data, prices or secrets | `Should not be public: google-drive-link (1 finding(s))`, then `docs/a.md:3: found 'https://drive.google.com/...'` | Remove the value or move it to an internal place; approved public contacts are listed below, and new ones go on the allowlist ([public-extract-allowlist.yaml](public-extract-allowlist.yaml)) after review | Docs owner |
| <a id="shared-agent-rules"></a>Shared agent rules (`tools/check_agent_rules.py`) | `AGENTS.md` and `CLAUDE.md` | Every contributor and agent follows the same rules; a changed copy quietly changes them | `Shared agent rules out of date: shared-rules (1 finding(s))`, then `AGENTS.md:1: found 'shared block differs from canonical'` | Copy the block between the BEGIN and END markers from [agent-rules/SHARED_RULES.md](agent-rules/SHARED_RULES.md) unchanged | Software lead |
| <a id="workflow-policy"></a>Workflow policy (`tools/check_workflow_policy.py`) | `.github/workflows/*.yml` | A tag or branch can be moved to new code; a full commit SHA cannot | `Workflow not pinned: unpinned-action (1 finding(s))`, then `.github/workflows/ci.yml:12: found 'actions/checkout@v4'` | Pin the action to its 40-character commit SHA and keep the version as a comment | CI owner |
| <a id="pr-evidence"></a>PR evidence and AI disclosure (`tools/check_pr_evidence.py`) | The pull request description | Reviewers need the base and head commits, exact commands, test counts, a Not verified section and an honest AI disclosure | `Missing section: Not verified` | Fill every section of the pull request template | CI owner |
| <a id="verify"></a>verify.sh (`rollout/verify.sh`) | The repository's build and tests | A test run that runs zero tests proves nothing; a skipped test must say why | `FAIL: zero tests executed` or `FAIL: skip/xfail/importorskip without a tracking issue` | Add real tests; put the tracking issue on the same line as each skip | CI owner |
| <a id="decision-freshness"></a>Decision freshness (`review_by` in the register) | The `review_by` date of each register entry | An old decision may no longer be true | `Review due: COMPUTE review_by 2026-11-18 is past due` (a warning, never a failure) | The entry's owner confirms the decision or starts a change | Each entry's `owner` role |

## How to read a finding

Findings are grouped by decision. Each group says once what the decision is, why it matters,
how to fix it and where to read more, then lists every place it was found. This is the real
COMPUTE group from the scan of `openamr-platform-hw` on 7 October 2026 (3 of its 14 places
shown):

```text
Mismatch with approved decision: COMPUTE (14 finding(s))
  Decision: Reference compute: NVIDIA Jetson Orin NX 16 GB on a reComputer Robotics J401; Pi is legacy.
  Why:      Jetson Orin NX is the 2.0 reference compute; label Raspberry Pi material as legacy.
  Fix:      Name the Jetson Orin NX, or label Raspberry Pi material as legacy or Gate A.
  More:     COMPUTE in decisions.yaml: https://github.com/openAMRobot/.github/blob/main/decisions.yaml#L711 | WATCHDOG.md: ...
  Found:
    README.md:44: found 'Raspberry Pi 5'
    README.md:81: found 'Raspberry Pi 5'
    electrical/computing/raspberry-pi.md:1: found 'Raspberry Pi 5'
```

- The first line names the kind of finding, the decision ID (`COMPUTE`) and how many places
  disagree with it.
- **Decision** is the current decision in one line.
- **Why** says what is wrong. If one decision has several checks, each reason gets its own line.
- **Fix** says what to change.
- **More** links to the register entry and to this page.
- **Found** lists each place as `file:line` and the text that was found.

In GitHub, each place is also shown inline in the pull request diff with the full message,
and the job summary has a table of findings per decision.

The line before the fix (the README describes the robot that exists today, which still uses
the Raspberry Pi):

```text
| Compute | **Raspberry Pi 5, 8 GB** | Ubuntu Server 24.04 + ROS 2 Jazzy. |
```

After the fix, the line says clearly that this is legacy (Gate A) material, so the finding
disappears:

```text
| Compute (legacy, Gate A robot) | **Raspberry Pi 5, 8 GB** | Ubuntu Server 24.04 + ROS 2 Jazzy. |
```

If the line was meant to describe release 2.0, the right fix is to name the Jetson Orin NX
instead.

At the end of every run the Watchdog prints a summary: the total number of findings, the
number per decision and the next step.

## How to fix a finding

Pick one of these, in this order:

1. **Correct the line** to the current decision.
2. **Label historical material clearly.** If the line describes the existing robot, an older
   revision or OpenAMRobot 3.0, say so *on the same line*, using one of the words the check
   accepts for that decision (table below). For example `legacy`, `Gate A`, `superseded`,
   `historical` or `3.0`. Case does not matter. If no accepted word fits, keep the line and add
   a marker on the same line or the line above:
   `decision-allow: <ID> <reason>`. The Watchdog still reports the marker, so a reviewer sees
   it.
3. **If the decision itself is wrong**, do not edit the register in your pull request. Open a
   [contract change request](https://github.com/openAMRobot/.github/issues/new?template=contract_change_request.yml)
   that names the entry. The owner updates the source document first; then one reviewed pull
   request updates the register and every affected repository.

**Never weaken a check to make CI pass.** Do not delete a pattern, widen an exception or skip
a step. If you believe a finding is wrong, see the FAQ below.

### Words each decision accepts

The Watchdog accepts a line when one of these words appears on the same line. Where a
decision has several checks, each check is named by the message shown in the finding's
**Why** line. `supersed` also matches *superseded* and *supersedes*. The table is generated
from the register with `python3 tools/watchdog.py --accepted-words`, and a test keeps it
identical to the register.

<!-- BEGIN ACCEPTED WORDS -->
| Decision | Status | Accepted on the same line (any one; case does not matter) |
|---|---|---|
| BOM-ISSUE-IN-FORCE | recorded | *BOM Issue 7.3 is the canonical hardware BOM*: `supersed (superseded, supersedes)`, `replaced`, `previous`, `earlier`<br>*B-01 is superseded*: `supersed (superseded, supersedes)`<br>*BOM Issue 7.3 is the canonical hardware BOM*: `supersed (superseded, supersedes)`, `replaced`, `previous`, `earlier`, `historical`<br>*superseded source still cited (P-03-rev18.1 line 7); cite P-03-rev18.7*: no label; correct the line or add a decision-allow marker |
| MAST-INSTALL-HEIGHT | superseded | `supersed (superseded, supersedes)`, `legacy`, `historical`, `earlier`, `previous`, `rev 18.1 to rev 18.6` |
| MAST-POSITIONS | superseded | `supersed (superseded, supersedes)`, `legacy`, `historical`, `earlier`, `previous`, `rev 18.1 to rev 18.6` |
| MAST-TOP-HEIGHT | superseded | `supersed (superseded, supersedes)`, `legacy`, `historical`, `earlier`, `previous`, `rev 18.1 to rev 18.6` |
| MAX-ASSEMBLED-HEIGHT | recorded | *maximum assembled height is 1700 mm*: no label; correct the line or add a decision-allow marker<br>*1700 mm is the assembled-height envelope, not a shoulder height or mast position*: `max`, `envelope`, `not shoulder, not the shoulder`, `higher`, `supersed (superseded, supersedes)` |
| DATUM-HEIGHT-STACK | recorded | *the steel chassis deck top is 294 mm above the floor*: `supersed (superseded, supersedes)`, `historical`, `legacy`, `earlier`, `previous`<br>*the lift base-plate top face is 304 mm above the floor, the reference for lift and shoulder heights*: `supersed (superseded, supersedes)`, `historical`, `legacy`, `earlier`, `previous` |
| FRAMES-REP105 | recorded | *base_link is at the drive-axle midpoint and axle height; base_footprint is on the floor*: `base_footprint`, `not`, `never`, `supersed (superseded, supersedes)`, `historical`, `legacy`<br>*base_footprint is on the floor under the drive-axle midpoint*: `not`, `never`, `supersed (superseded, supersedes)`, `historical`, `legacy`<br>*imu_link sits on the centreline away from motor magnetic fields*: `away`, `not`, `never`, `supersed (superseded, supersedes)`, `historical`, `legacy` |
| BATTERY-PLACEMENT | recorded | `supersed (superseded, supersedes)`, `historical`, `previous`, `earlier`, `rev 18.1 to rev 18.6` |
| SPEED-CEILING | recorded | *1.5 m/s is a command ceiling, not an operating limit*: `ceiling`, `analytical`<br>*1.5 m/s is not an accepted operating speed*: `ceiling`, `analytical`, `not` |
| DRIVETRAIN | recorded | *the selected motor variant is ZLLG80ASM250-L-B*: no label; correct the line or add a decision-allow marker<br>*ZLTECH is the selected 2.0 drivetrain, not an option*: no label; correct the line or add a decision-allow marker<br>*brake fail-safe function and ratings are open supplier-evidence gates*: `pending`, `F2A`, `verif`, `not yet`, `unverified` |
| RS485-NOT-IN-2-0 | recorded | *RS485 is not provisioned in 2.0*: `not used`, `no RS485`, `not provisioned`, `without`, `legacy`, `Gate A`, `removed`, `not in 2.0`<br>*CAN1 and CAN2 are dedicated; no upper-body serial link to the base*: no label; correct the line or add a decision-allow marker |
| BASE-CONTROLLER-GATES | recorded | *Teensy is the Gate A controller and the release fallback, not a bench target*: no label; correct the line or add a decision-allow marker<br>*ICM-42688-P is gated; MPU6500 remains the Gate A IMU*: `Gate B`, `conditional`, `20 Nov`, `candidate`, `pending`, `not yet`, `after`<br>*the Gate A IMU is the MPU6500*: no label; correct the line or add a decision-allow marker |
| BASE-CONTROLLER-IO | recorded | *the base controller is the STM32H723ZG on the NUCLEO-H723ZG; label STM32H743 / NUCLEO-H743ZI2 material as superseded*: `supersed (superseded, supersedes)`, `legacy`, `historical`, `replaced`<br>*the ultrasonic sensors are two MaxBotix MB7060 on dedicated STM32 UARTs at 9600 8N1; no sensor I2C*: `supersed (superseded, supersedes)`, `legacy`, `historical`, `replaced`<br>*micro-ROS runs over UDP on Ethernet between MCU and Jetson; USB is for the bench only*: `bench`, `legacy`, `Gate A`, `Teensy`, `supersed (superseded, supersedes)`, `historical` |
| IMU-TOPIC-OWNERSHIP | recorded | *firmware publishes /imu/data_raw; /imu/data belongs to the host filter*: `host`, `filter (not unfiltered)`, `EKF`, `madgwick`, `must not`, `never`, `outdated`, `older revision(s)`<br>*firmware must not publish filtered /imu/data*: no label; correct the line or add a decision-allow marker |
| CAMERAS | recorded | *the base camera is the Orbbec Gemini 336L*: `legacy`, `historical`, `previous`, `not used`, `replaced`<br>*the base camera tilts about 10 degrees up*: no label; correct the line or add a decision-allow marker<br>*the 2.0 base camera is the Orbbec Gemini 336L*: `legacy`, `Gate A`, `historical`<br>*the Gemini 336L up-tilt positions are 5, 10 and 15 degrees, baseline 10*: `supersed (superseded, supersedes)`, `historical`, `legacy` |
| HEAD-CAMERA-IDENTITY | recorded | `supersed (superseded, supersedes)`, `historical`, `legacy`, `replaced`, `not` |
| POWER-RAILS | recorded | *there is no 12 V rail in 2.0*: `no 12`, `not`, `never`, `legacy`<br>*there is no 12 V rail in 2.0*: `legacy` |
| DOCK-NO-CONTACTS | recorded | *2.0 docking has no dock contacts*: `no`, `not`, `without`, `3.0`, `never`<br>*no dock or charge pilot in 2.0*: `no`<br>*wireless charging belongs to 3.0*: `3.0`, `later`, `deferred`, `not` |
| DOCKING-NOT-CHARGING | recorded | *2.0 docking is positioning only*: `not`, `never`, `instead`, `non-charging`, `legacy`<br>*never report charging from a docking pose*: no label; correct the line or add a decision-allow marker<br>*docking success never establishes charging*: `not`, `never`, `does not` |
| TELEMETRY-NOT-SAFETY-EVIDENCE | recorded | `not`, `never`, `functional`, `no substitute` |
| SAFETY-PROCUREMENT | recorded | *the EDM variant is not selected*: `not`, `unselected`, `open`<br>*no single-channel or uncertified E-stop recommendation*: no label; correct the line or add a decision-allow marker<br>*CTL-004 is bench-only*: `bench-only`, `until` |
| COMPUTE | recorded | `legacy`, `historical`, `removed`, `supersed (superseded, supersedes)`, `Gate A`, `previous`, `earlier` |
| NAV-LIDAR | recorded | *the 2.0 navigation LiDAR is the RPLIDAR S3 (S3M1-R2); the Hokuyo UST-10LX was dropped*: `supersed (superseded, supersedes)`, `dropped`, `legacy`, `historical`<br>*the 2.0 navigation LiDAR is the RPLIDAR S3 (S3M1-R2); label RPLIDAR A1 material as legacy*: `legacy`, `Gate A`, `existing robot`, `historical`, `replaced` |
| RELEASE-MILESTONES | recorded | *the OpenAMRobot 2.0 final release is 18 December 2026*: `supersed (superseded, supersedes)`, `previous`, `earlier`, `historical`<br>*there is no v0.2 release; development cycle 2 ends 20 November 2026 with v2.0.0-rc.1, and v2.0.0 follows on 18 December 2026*: `supersed (superseded, supersedes)`, `historical`, `earlier`, `previous`<br>*development cycle 2 ends 20 November 2026 with v2.0.0-rc.1, not 13 November*: `supersed (superseded, supersedes)`, `historical`, `earlier`, `previous` |
| LIFT | recorded | *the lift is approved in principle for 2.0*: `supersed (superseded, supersedes)`, `historical`, `earlier`, `previous`, `no longer`, `rev 18.1 to rev 18.6`<br>*the fixed mast is no longer the baseline; the lift is approved in principle*: `supersed (superseded, supersedes)`, `historical`, `earlier`, `previous`, `legacy`, `replace (replaced, replacement)`, `instead of`, `no longer`, `rev 18.1 to rev 18.6`<br>*the lift is not deferred to 3.0; it is approved in principle for 2.0*: `supersed (superseded, supersedes)`, `historical`, `earlier`, `previous`, `no longer`, `rev 18.1 to rev 18.6` |
| NO-SUSPENSION | recorded | `3.0`, `no`, `not fitted`, `without` |
| DRIVE-TRACK | open | not scanned until the decision is taken |
<!-- END ACCEPTED WORDS -->

## Approved public contacts

Public files (`docs/`, `assets/`, every `README.md` and any path containing `public`) carry no
personal contact data and no prices. The public-extract check accepts only these kinds of
contact, each listed with its reason in
[public-extract-allowlist.yaml](public-extract-allowlist.yaml):

| Kind | What is accepted | Where |
|---|---|---|
| Organisation | Any address on the `botshare.ai` domain. Lookalike domains are still flagged. | Anywhere |
| Contributors and maintainers | An address on a `Signed-off-by:` or `Co-authored-by:` line, and any address in `CONTRIBUTORS.md`, `MAINTAINERS.md` or `maintainers.yaml`. Publication is agreed through the DCO, the CLA and the contributor privacy notice. | Anywhere |
| Supplier role addresses | An address whose name part is a role: `sales`, `info`, `support`, `service`, `contact`, `export`, `trade`, `office` or `marketing`, optionally followed by digits (for example `trade26@`). An address that names a person is still flagged. | `datasheets/` only |
| Third-party licence notices | The author address on a copyright, licence or `@author` line of third-party code, which must stay to preserve provenance. | Notice lines only |

**Prices are never public**, except the approved organisation pricing (the sponsorship tiers
and robot offerings on this organisation's README and profile). Supplier prices, quotes and
price lists are removed, never allowlisted.

**To request a new entry**, open an issue that names the file, the exact text and why it must
be public. The docs owner decides entries for published pages; the platform lead decides
entries about company or commercial information. Until the entry is merged, the finding
stays.

## Run it locally in one command

From a checkout of `openAMRobot/.github`, next to the repository you want to check:

```bash
python3 -m pip install --user PyYAML   # once, if PyYAML is missing
python3 tools/watchdog.py --root ../openamrobot-docs
```

It runs decisions of record, public extract, shared agent rules (when the repository has an
`AGENTS.md`), workflow policy and decision freshness, prints each finding with its fix, then a
summary table. Exit status: 0 clean, 1 findings, 2 a configuration or usage error. Useful
options:

- `--report-only`: never fail on findings (exit 0), for a first look.
- `--repository NAME`: the repository name, if the folder has another name.
- `--json FILE` and `--markdown FILE`: machine-readable and Markdown output.

PR evidence and verify.sh run on their own: `python3 tools/check_pr_evidence.py --help` and
`bash rollout/verify.sh <repository path>`.

## In CI

- **In a repository's pull requests**, the reusable workflow
  [repository-quality-reusable.yml](.github/workflows/repository-quality-reusable.yml) runs the
  same checks. With `harness_warn: true` every finding is a warning and the job never fails.
  With `harness_checks: true` a finding in a changed file fails the pull request. Findings
  appear inline in the pull request diff, and the job summary shows a table grouped by
  decision.
- **Across the organization**, [watchdog-org-scan.yml](.github/workflows/watchdog-org-scan.yml)
  runs every Thursday and on demand. It clones every repository in
  [rollout/repositories.yaml](rollout/repositories.yaml) on its default branch and writes one
  summary plus JSON/Markdown artifacts. Findings do not fail the scan, but a clone or checker
  failure is reported as **BLOCKED** and fails the job after the report is written.
- **GitHub issue control surface:** the scan synchronizes one central dashboard issue and one
  deduplicated issue per grouped finding in `openAMRobot/.github`. Issues are assigned to
  `BotshareAI` when GitHub permits assignment and always mention `@BotshareAI`; public issue
  text redacts URLs, email addresses and credential-shaped values. Repeated evidence is not
  posted repeatedly. When a finding disappears, the Watchdog comments that it is no longer
  detected and leaves closure to the human owner. If the same finding returns after closure, the Watchdog reopens the issue and posts the new observation.
- The workflow has `contents: read` and `issues: write` only. It reads product repositories
  anonymously, writes only issues in the harness repository, never edits `decisions.yaml`,
  never pushes a branch, never opens a pull request, and never uses AI. The platform lead
  updates the ground truth through a normal reviewed PR.

## GitHub-native operating loop

The weekly loop is deliberately split at the ground-truth boundary:

1. The Thursday Action scans all repositories listed in `rollout/repositories.yaml`.
2. The Action writes or updates the central dashboard and grouped finding issues in
   `openAMRobot/.github`.
3. A finding issue identifies the repository commit, exact location, owner role, reason and
   fix. It is a textual signal, not a safety or release acceptance.
4. A due decision creates a `decision-review` issue. The platform lead confirms the controlling
   source and either extends the review window or starts a source-first change.
5. The platform lead updates `decisions.yaml` in a normal reviewed PR. The Watchdog never
   guesses a new value and never edits the register itself.
6. The next run verifies the fixing PR's result. Human owners close issues only after review.

The dashboard is the durable weekly record. Its `Shared rules` column distinguishes `pass`,
`drift` and `not enrolled`; `not enrolled` is rollout status, not a contradiction. The uploaded
JSON artifacts preserve the exact repository SHAs and evidence used by the run.

## Adopting it in a repository

The full steps are in [rollout/README.md](rollout/README.md). In short, one pull request per
step, each merged by the repository owner:

- [ ] **Pilot first:** `openamrobot-interfaces` completes every step before any other repository starts.
- [ ] (a) Copy the shared agent rules into `AGENTS.md`; `CLAUDE.md` contains only `@AGENTS.md`; add `STATE.md`.
- [ ] (b) Pin the reusable workflow and `harness_ref` to one harness commit SHA.
- [ ] (c) Turn on warn-only (`harness_warn: true`); fix or label the findings until a run on main is green.
- [ ] (d) Turn on enforcing (`harness_checks: true`).
- [ ] (e) The repository's ruleset requires the check.

Only after step (e) does a finding block a merge.

## Status of the AI workflows

The example AI workflows in `rollout/workflows/` (docs sync, weekly audit, monthly retro) are
**design only**. They stay inactive until
[issue #43](https://github.com/openAMRobot/.github/issues/43) is closed with its activation
evidence. The Watchdog itself uses no AI.

## FAQ

**I think a finding is a false positive.** First check whether the line really reads as the
current decision to a newcomer. If it is history, label it (see the table). If it is
genuinely correct and no label fits, open an issue labelled `harness` with the file, line and
finding. The CI owner fixes the pattern in this repository with a regression test. Do not
change the check in your own pull request.

**A decision changed.** The register is updated in one reviewed pull request, and the
Watchdog then reports every line that still shows the old value. Fix them in your repository,
or label them as history.

**A value is still open.** Entries with status `open` are not scanned. Write "open" or
"to be decided" and do not invent a value. The register entry says who decides it.

**Who do I ask?** The owner role of the check in the table above. Roles and their people are
in [maintainers.yaml](maintainers.yaml). For a decision, ask the role named in its `owner`
field.
