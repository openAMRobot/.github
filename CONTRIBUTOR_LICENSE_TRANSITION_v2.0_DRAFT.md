# Contributor-retained-rights transition — DRAFT, 19 November 2026

**Not in force. Do not activate or advertise ICLA v2.0 as binding before legal review and formal approval.**

## Why

The operative ICLA v1.1 and Corporate Contributor Agreement assign transferable economic rights in accepted contributions to Botshare LTD. The proposed v2.0 model instead preserves contributor ownership while granting Botshare LTD broad non-exclusive, perpetual, irrevocable, worldwide, royalty-free, transferable, sublicensable and commercial exploitation rights. This is a material legal change, not a word change.

## Release checklist

1. Engage Cyprus-qualified intellectual-property counsel to assess draft ICLA v2.0, corporate equivalents, patent rights, authorship/moral-right limitations, data protection, and past assignment chains.
2. Decide whether corporate contributors will have a separately updated **Corporate Contributor License Agreement v2.0**; the operative corporate agreement remains assignment-based until an approved replacement is signed. Do not route corporate-owned work through the individual agreement.
3. Confirm any background material and upstream-rights exceptions with contributors before acceptance. Do not automatically relicense Apache-2.0 or other third-party source to MIT.
4. Approve final legal text, assign immutable document version and preferably a digest, and publish it alongside archived ICLA v1.1. Keep historical agreement records.
5. Configure CLA Assistant's **actual organization-wide acceptance document** to the exact approved v2.0, verify the linked URL and version in a test PR, and **require new affirmative acceptance for contributors whose new work is covered by v2.0**. A Markdown PR alone does not configure the external service.
6. Keep DCO, provenance, third-party notice and CODEOWNERS requirements. Update CLA.md, IP_POLICY.md, DCO.md, CONTRIBUTING.md, corporate agreement references, reviewer instructions and automated check expectations **in one reviewed transition**.
7. Avoid a transition window where an ambiguous CLA status permits an unlicensed contribution. Verify that historical v1.1 acceptances do not masquerade as acceptance of v2.0.
8. Test one individual PR and one corporate-authorized PR through the end-to-end CLA and DCO workflow before activating across repositories.
9. Communicate to all contributors: contributors retain copyright ownership under **new v2.0**; Botshare holds a permanent broad non-exclusive licence; existing assigned contributions under v1.1 remain assigned absent separately executed reassignment/licensing arrangements.
10. Record formal approval and effective date. Review all pending PRs for which agreement was accepted before transition and identify their controlling version individually.

## Manas / OpenArm example

For Manas's contribution to upperbody-sw #69, clarify that his pre-existing `openarm-control` Apache-2.0 Background Material is separately owned; any copies or derivative components must be identified file-by-file with provenance before acceptance. Do not insist that independent Apache-2.0 code is MIT simply because a contributor has signed a CLA. If v2.0 is approved in time, Manas must affirmatively accept it before the applicable contributions are merged. Until then, v1.1 remains the operative agreement, and the contributor should not be pressured to sign a contract they do not understand or accept.

## Scope limitation

This proposal does **not** change the project's outbound asset licensing rules: MIT original software/firmware, CERN-OHL-P-2.0 original hardware, CC BY 4.0 original documentation/content, explicit asset-specific dataset/model terms. Third-party and derivative assets retain applicable upstream requirements. Existing public licences are not revoked.
