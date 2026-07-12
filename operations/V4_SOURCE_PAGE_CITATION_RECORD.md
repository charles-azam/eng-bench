# V4 source-page citation correction

Status: content-blind source-audit record written at 2026-07-12 10:20:57 UTC while the frozen
`core-n3` schedule was still running, before its terminal archive, eligibility gate, prediction
inspection, scoring, or artifact review.

Revision: expanded at 2026-07-12 10:23:27 UTC, still under the same inspection boundary, after the
second cited IAEA PDF exposed the same one-page boundary error.

## Finding

IAEA-TECDOC-1674 Eq. 10.9 is on **printed report page 548**, not printed page 547.
IAEA-TECDOC-2090 Table 88 is on **printed report page 220**, not printed page 219. The equation,
coefficients, fluence placement, units, and `1.011e-16 m2/s` reference value in the frozen task pack
are correct. Only the page numbers in two provenance notes are wrong:

- `tasks/triso_corrected_bounded_annex/inputs/03_bounded_material_annex.md`;
- `protocol/TRISO_CORRECTIONS.md`.

The errors came from plain-text page boundaries. The first extraction places the printed `547`
footer immediately before the form feed that begins section 10.3.4.2; visual inspection of the next
PDF page shows Eq. 10.9 and a `548` footer. The second extraction places the printed `219` footer
immediately before the form feed that begins Table 88; visual inspection of the next PDF page shows
the independently legible coefficient row and a `220` footer.

The official PDF inspected was
`https://www-pub.iaea.org/MTCD/Publications/PDF/TE_1674_CD_web.pdf`, SHA-256
`d6cec5eccc96b2f7e07c9d754b44c033ebc28bb4996a21ac605aa4d9e8e0e488`. Its one-based PDF page
562 renders the report page carrying Eq. 10.9 and the printed `548` footer.
The official TECDOC-2090 PDF inspected was
`https://www-pub.iaea.org/MTCD/publications/PDF/TE-2090web.pdf`, SHA-256
`ea342174747f63a2441bde399f34244ff2cb5c8916db34bcb1276b3674448e8a`. Its one-based PDF page
231 renders Table 88 and the printed `220` footer.

## Consequence

This is a provenance-location erratum, not a numerical task or evaluator change. The frozen tag and
all agent-visible bytes remain unchanged so every scheduled replicate retains identical inputs.
Publication text will cite printed pages 548 and 220 and disclose the frozen page-boundary error.
The task equation, validator checksum, evaluation ledger, held-out evidence, schedules, and stage
eligibility rules are unaffected.
