# Third-Party Material Policy

## Rule

Third-party material may be added to an OpenAMRobot repository only when its origin, ownership, licence or permission basis, compatibility, and required notices are known and recorded.

## Required record

For code, firmware, CAD, schematics, documentation, images, datasets, models, fonts, media, vendor files, copied examples, and generated assets, record as applicable:

- component/file and repository path;
- upstream project or source URL;
- author or rights holder;
- exact version, tag, or commit;
- licence identifier and licence text location;
- modifications made by OpenAMRobot;
- copyright, patent, attribution, and redistribution requirements;
- reviewer and review date.

Use source headers, `NOTICE.md`, `THIRD_PARTY_NOTICES.md`, package metadata, an SBOM, or a repository licence map.

## Prohibitions

Do not:

- remove or replace authentic upstream notices;
- relicense material without authority;
- commit vendor manuals, datasheets, images, models, or binaries merely because they are publicly downloadable;
- copy from a repository or website that has no licence;
- submit confidential, client-owned, personal, export-controlled, or unlawfully obtained material;
- claim Botshare LTD ownership of third-party material.

Links and factual component references are preferred when redistribution permission is unclear.

## Review

Pull requests containing third-party material require explicit provenance review before acceptance. Unclear material must be removed or quarantined until rights are confirmed.

## Commercial compatibility

OpenAMRobot must stay free to build, manufacture, sell, modify, redistribute and use in proprietary products without royalties and without asking anyone for permission. Third-party material is therefore accepted by licence class. The class applies both to material copied into a repository and to anything the default robot needs in order to be built, manufactured, run or used (libraries, packages, firmware components, hardware designs, simulation assets, datasets, base models and weights).

| Class | Examples | Rule |
|---|---|---|
| Allowed | MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, Zlib, BSL-1.0, CC0-1.0, CC-BY-4.0, CDLA-Permissive-2.0, CERN-OHL-P-2.0 | May be used once the required record exists and notices are preserved. Apache-2.0 material keeps its licence, `NOTICE` content and change notices; it is not relabelled MIT. |
| Approval needed | LGPL, MPL-2.0, EPL-2.0, CERN-OHL-W-2.0, CC-BY-SA-4.0, any licence with a patent or field-of-use condition, any vendor or custom licence | Only with written approval of Botshare LTD before acceptance, as a separate and replaceable component that is never copied into or statically combined with OpenAMRobot sources. The approval and its conditions are recorded. |
| Not accepted | GPL, AGPL, SSPL, CERN-OHL-S-2.0, Business Source and other source-available licences, any non-commercial, no-derivatives, research-only or evaluation-only terms, behavioural-use licences for models, and material with no licence | Not copied into a repository and not made a requirement of the default robot. |

A tool used only on a developer's machine or in CI, whose output is not a derivative of the tool, is not a dependency of the robot for this table. It is still recorded when it affects reproducibility.

When no compatible option exists, the choice is to write an original replacement, to make the function optional, or to ask Botshare LTD for a separate arrangement with the rights holder. It is never to hide or relabel the material.

## Datasets, simulation assets and AI models

Each dataset, recording set, simulation asset, model and set of weights is reviewed individually before acceptance and again before public release. It needs a card stating:

- how it was produced, with the source commit, simulator and tool versions;
- every source dataset, asset pack, base model and pre-trained weight used, with licence and source;
- whether it shows identifiable people, private places or other personal data;
- the proposed public licence.

Default public licences are CC BY 4.0 for suitable datasets and MIT for models and weights. An asset derived from material under other terms carries those terms and is accepted only if they fall in the Allowed class or are approved as above. Data or weights under non-commercial, research-only or behavioural-use terms must not be used to produce an asset submitted to OpenAMRobot.

## Contributor Background Material

Material a contributor owns and includes in a contribution is licensed to Botshare LTD in full under the contributor agreement, with no added restriction. If the contributor cannot grant that, the material is left out or covered by a separate written agreement signed by Botshare LTD before acceptance. Material that is only referred to, and not included, is named in the pull request with its location and licence.
