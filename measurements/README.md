# Held-out evaluation records

`held_out.jsonl` is the human-owned scoring set. It is never mounted into an agent run: the
verifier and this file reach the container only after the agent finishes. The NSTF record bytes
are unchanged since the audited `2026-07-12-v4` freeze.

Every record labels its evidence class and dependency group. Metrics in the same dependency group
must not be described as independent confirmations. Records with `kind: "unscored"` exist only to
accept task-contract outputs for which the primary source has no defensible numeric target. Records
with `required: false` are excluded from the evaluator's score rows.

Primary sources are ANL-ART-47 (OSTI 1350591) and the related NSTF reports cited per record in
each `provenance` field. Detailed extraction caveats are preserved at tag
`benchmark-2026-07-12-v4` (`rccs/sources/extraction_notes.md`, `rccs/refs/measured_data.md`).
