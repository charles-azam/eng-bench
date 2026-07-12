# Benchmark freeze record

- Protocol version: `2026-07-12-v3`
- Git tag: `benchmark-2026-07-12-v3`
- Frozen protocol manifest SHA-256: `29429843b248aa75c45cd47befa9029d2d94024144e6fcb02cc0ffe7f8bab5c3`
- Runner source manifest SHA-256: `a88dada96286a036cab8407e6a43e22aa49b25530580881b6b62eb27baf946fe`
- VPS environment snapshot SHA-256: `d8f61e4a46f44e4bddd4ead99a60aae1fc3090d98d5d0a6569ad87161f2da32a`
- Evaluator source manifest SHA-256: `9fafb9f4e87e354c77533736af0ad70f509638ca49882c2db428c4ce87dc98c2`
- V3 preflight ledger SHA-256: `3e3762437794284690b32694f099610b7d38e0982cbf2f049576fc22947b15e5`
- Schedule seed: `20260711` (intentionally retained from the preregistration)
- Frozen evaluator ledger: `protocol/evaluation_ledger.json`

The annotated tag references the freeze commit and is pushed publicly before any v3 model output is
eligible. Stage schedules are generated from that public tag, committed, and pushed before their
first launch. The environment record is a hash-covered snapshot of the VPS and toolchain, not an
OCI image. The literal `/root/bench-v2` deployment path is retained for continuity and does not
identify the protocol version.

## Excluded predecessors

Version 1 was retired after the first scheduled process started but before it finalized: a misplaced
shell guard referenced unbound variables at finalization. Its partial attempt and schedule are
preserved under `results/excluded/v1-finalizer-bug/`; they contribute no prediction, process, or
review result.

Version 2 retained the corrected scientific design but is excluded in full for two independent
runner-integrity failures. Its complete sequential `core-n3` schedule produced 18 physical
attempts: six completed Codex first attempts, six Claude first attempts, and six registered Claude
retries. Every Claude attempt exited before a model event because the scored command used
`--dangerously-skip-permissions` while the external sandbox retained effective UID 0 without
setting the CLI's deliberate-sandbox marker. Separately, the input/workspace ledger inherited the
host locale and produced ledger-byte hashes that disagreed with the bytewise frozen pack hashes,
although the task file bytes were identical. The exact diagnosis is in
`results/excluded/v2-ineligible-campaign/EXCLUSION.md`.

Before freezing that exclusion, inspection was limited to service state, journals, run IDs,
checksums, file sizes, ledger path order, Claude diagnostic metadata/environment/stderr/proxy data,
and byte equality of Claude inputs to the frozen protocol. No Codex event content, prediction,
submitted workspace output, score, or artifact-review material was opened. The 1,316-file private
preservation ledger hashes to
`103663ec098bf4c93adc3431d275aab02766162ebbe8a09e42e9b388d37d2188`.
No v1 or v2 attempt is reused in v3; every primary cell restarts from replicate 1.

## V3 scientific and evaluator boundary

The v3 agent prompt, three task packs, held-out measurement JSONL, evaluator source, evaluator tests,
and evaluator manifest are byte-identical to v2. The task-pack hashes remain:

- blind NSTF: `505e446c2aab398fa78bca00c400c7b85e849ba2a8b8b3cb7005cf7a7455bc37`;
- supplied-duty NSTF: `066da7206b38d3d3f43bfbd992226de0e72e072e64bd50886cc9c91e9515f65c`;
- TRISO: `b289430390cc2bdc6b2d176d3ac0d78a0281d634cd68211c5e83ac2ce54642e4`.

The frozen VPS independently reconstructed all three physical pack ledgers with `LC_ALL=C` and
matched those values. The 25-line assembled protocol manifest differs from v2 only in `FROZEN`,
`VERSION`, and `environment.json`. The environment snapshot differs from v2 only in its runner
source-manifest hash; the CLI binaries/versions, packages, kernel, sandbox binary, allowlists, and
normalizer environment are unchanged.

## Runner qualification

V3 forces bytewise collation for input and workspace ledgers. Its external bubblewrap namespace
retains effective UID 0 but truthfully sets `IS_SANDBOX=1`, the marker recognized by the frozen
Claude 2.1.201 executable. Both final isolation probes demonstrated that the host environment was
cleared, the held-out host path was hidden, only the selected credential was mounted, the opposite
provider and arbitrary proxy access were denied, and direct network access failed.

Codex completed a content-free readiness smoke. The same prompt elicited a fail-closed Fable refusal
and is retained only as a diagnostic; Fable then completed the registered neutral slab-conduction
readiness task. Both systems subsequently completed a neutral Read/Bash/Write checksum task through
the exact scored CLI-command wrapper, emitted provider-specific success events without fallback,
and wrote the preregistered artifact. The locked VPS runner suite passed all eight integration tests.

An earlier parity candidate exposed another asymmetry before freeze: Claude Code 2.1.201 accepted
`--json-schema`, but Fable returned a successful plain-text result with `structured_output: null`,
while Codex enforced its corresponding final-message schema. The final message was not consumed by
the benchmark. Both unused provider-specific final-message schema flags and the shared schema file
were therefore removed symmetrically before this manifest was generated. The shared structured
contract remains `workspace/output/predictions.json`, validated after execution by the same strict
Pydantic normalizer for both systems.

`protocol/preflight_v3.sha256` is the 55-record, credential-free ledger for the exact runner,
environment, protocol candidate, final isolation/readiness/parity artifacts, locked test output,
and the two diagnostic probes above. Its event streams and private runtime payload remain on the
VPS; the public ledger commits to their bytes without publishing credentials.

Claude events identify the actual assistant model and explicit fallbacks, so model contamination
fails closed. Codex JSONL records the requested model and session but does not expose an equivalent
per-message server-model field. Results therefore describe GPT-5.6 Sol as requested and
runner-assumed served, with exact CLI and native-binary hashes, rather than independently verified
service identity.
