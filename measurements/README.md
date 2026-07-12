# Held-out evaluation records

`held_out.jsonl` is the human-owned scoring set for protocol version
`2026-07-12-v3`. It is never mounted into an agent run.
Its bytes are unchanged from v2, whose campaign never became eligible for scoring.

Every record labels its evidence class and dependency group. Metrics in the same dependency group
must not be described as independent confirmations. Records with `kind: "unscored"` exist only to
accept task-contract outputs for which the primary source has no defensible numeric target. Records
with `required: false` are excluded from the evaluator's score rows.

Primary sources and detailed caveats are documented in `PROTOCOL.md`,
`rccs/sources/extraction_notes.md`, `rccs/refs/measured_data.md`, and
`triso/refs/measured_data.md`.
