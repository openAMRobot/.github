# OpenAMRobot Contributor Agreement Process

Botshare LTD requires a recorded contributor agreement before accepting an external contribution.

## Agreement versions

| Version | Model | Documents | Status |
|---|---|---|---|
| 2.0 | Contributor keeps ownership; Botshare LTD receives a permanent, irrevocable, worldwide, royalty-free, transferable and sublicensable licence | [Individual Contributor License Agreement](INDIVIDUAL_CONTRIBUTOR_LICENSE_AGREEMENT.md), [Corporate Contributor License Agreement](CORPORATE_CONTRIBUTOR_LICENSE_AGREEMENT.md), [Guardian Consent](MINOR_CONTRIBUTOR_GUARDIAN_CONSENT.md) | **Offered for acceptance through CLA Assistant since 22 November 2026.** |
| 1.1 | Assignment of transferable economic rights to Botshare LTD | [Individual Contributor Agreement](INDIVIDUAL_CONTRIBUTOR_AGREEMENT.md), [Corporate Contributor Agreement](CORPORATE_CONTRIBUTOR_AGREEMENT.md) | Closed to new acceptances since 22 November 2026. Still governs the contributions accepted under it. |

**Activation date of version 2.0:** 22 November 2026, 18:05 UTC. From that time CLA Assistant presents version 2.0 and asks every contributor, including those who accepted version 1.1, for a new acceptance on their next pull request. A contributor is covered by version 2.0 only from that contributor's own recorded acceptance.

The version whose acceptance is recorded for a contributor governs that contributor's contributions:

- Contributions accepted under version 1.1 stay under version 1.1. Assignments already made remain in effect.
- From the recorded time a contributor accepts version 2.0, version 2.0 governs every contribution of that contributor accepted afterwards, and no assignment under version 1.1 takes place for them.
- Publishing or changing a file in this repository does not change the agreement any contributor has accepted.

## Which agreement applies

- Use the Individual agreement when contributing in your own capacity.
- Use the Corporate agreement when an employer or organization owns, controls, sponsors, or authorizes the work.
- If an employer, university, client, sponsor, co-author, joint inventor, or other party may have rights, obtain written authorization before submission.
- A contributor must not choose the Individual agreement to avoid a rights holder's authorization.
- A contributor under 18 needs the Guardian Consent on record before any contribution is merged.

## Individual contributor workflow

OpenAMRobot uses CLA Assistant with one organization-wide agreement.

1. Open a pull request.
2. Follow the CLA Assistant link shown on the pull request.
3. Sign in with the GitHub account used for the contribution.
4. Read the complete agreement shown, check its document identifier and version, and accept it.
5. Wait for the `license/cla` status check to pass.
6. Ensure every commit also passes DCO.

A contributor normally accepts once per version. When a new version is activated, CLA Assistant asks for a new acceptance on the next pull request.

## Contributors under 18

1. A parent or legal guardian completes the [Guardian Consent](MINOR_CONTRIBUTOR_GUARDIAN_CONSENT.md) and sends it privately to **info@botshare.ai**.
2. Botshare LTD confirms in writing that it is on record.
3. Only then may a maintainer merge the contributor's pull requests. A CLA Assistant acceptance given by the minor alone is not sufficient.
4. On reaching 18, the contributor accepts the Individual agreement personally.

## Corporate, employer, and institutional workflow

CLA Assistant acceptance is for contributors acting in their individual capacity. Where an employer, company, university, sponsor, client, or institution owns or controls the work:

1. complete the Corporate agreement in force;
2. have an authorized representative sign it;
3. list the Authorized Contributors and their GitHub usernames;
4. send it privately to **info@botshare.ai** with subject `OpenAMRobot Corporate Contributor Agreement, [legal entity]`; and
5. wait for Botshare LTD to confirm coverage in writing before submitting or merging contributions.

An organization that signed version 1.1 stays under version 1.1 until both parties have signed version 2.0.

Signed agreements, identity documents, and private authorization records must never be committed to a public repository.

## Acceptance controls

DCO and the contributor agreement are cumulative:

- DCO records provenance and the committer's certification.
- The accepted agreement governs inbound rights: assignment under version 1.1, licence under version 2.0.
- Passing an automated check does not cure invalid acceptance, missing authority, missing guardian consent, impersonation, or undisclosed third-party rights.
- A pull request must not merge until both DCO and the applicable agreement requirement are satisfied.
- A green `license/cla` check shows that the contributor accepted the agreement CLA Assistant presented at that time. Before the activation date that is version 1.1. A maintainer must not treat any contributor as covered by version 2.0 before the activation date, or without a CLA Assistant record of that contributor dated on or after it.

## Activating version 2.0

Version 2.0 is activated only when all of the following are done and recorded:

1. Botshare LTD's director approves the final texts in writing, after legal review.
2. The exact approved Individual text is published in a new, separately versioned CLA Assistant document. The version 1.1 document is never edited.
3. The published text is compared with the file in this repository and the SHA-256 of the file is recorded below.
4. A test pull request confirms that CLA Assistant shows version 2.0, asks a version 1.1 signer for a new acceptance, and records the acceptance with the document identifier.
5. The version 1.1 signature list is exported and stored privately with the version 1.1 text.
6. The organization-wide CLA Assistant link is switched to the version 2.0 document, and the activation date is entered above.
7. Every open external pull request is rechecked so that it asks for version 2.0.

Activation evidence:

- CLA Assistant document: https://gist.github.com/BotshareAI/8f69c728da49ce67e44c56ff24ac6481 , file `OpenAMRobot-ICLA-v2.0.md`, revision `81f04ae27b56598c1ad046e28185d9e3cb541b6f`.
- SHA-256 of `INDIVIDUAL_CONTRIBUTOR_LICENSE_AGREEMENT.md` on main (commit fa9757a), the text submitted to that document: `189dadd0aa16b5ce4958f5e34f870cf3087622841d6103bd46bc0eac8ea237c6`.
- Test: on openamr-platform-fw pull request 72, opened by an account that had accepted version 1.1, the `license/cla` status changed to "not signed yet" after the switch, and the signing page showed document identifier OpenAMRobot-ICLA-2.0 from its first line to its last clause, with all five links resolving.
- Version 1.1 had 21 recorded acceptances at the switch; their history was exported and is kept privately.
- Open pull requests were rechecked through CLA Assistant after the switch.

## Version changes

A material amendment requires new acceptance. Updating a public Markdown file or CLA Assistant document does not amend an accepted agreement. A material new version uses a separately versioned agreement record.

## Data protection

Contributor records are handled under the [Contributor Privacy Notice](CONTRIBUTOR_PRIVACY_NOTICE.md). Public repositories must contain no signed agreements, residential addresses, dates of birth, identification documents, or private contact details.
