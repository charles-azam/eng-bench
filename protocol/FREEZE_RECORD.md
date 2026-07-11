# Benchmark freeze record

- Protocol version: `2026-07-11-v2`
- Git tag: `benchmark-2026-07-11-v2`
- Frozen protocol manifest SHA-256: `8c94636ed6898cad4d09072b83b9506434fcfc814702dec457e71b82c7343dbc`
- Runner source manifest SHA-256: `146dfd66cad991782386d082dd3a817011eeb1e09fceaaa54da49cee2dc45fa2`
- VPS environment snapshot SHA-256: `8e393b494caa5b102e283fb554fd33c6cfbf9da2198a4c2a791ea795cf17cfee`
- Evaluator source manifest SHA-256: `9fafb9f4e87e354c77533736af0ad70f509638ca49882c2db428c4ce87dc98c2`
- Schedule seed: `20260711`
- Frozen evaluator ledger: `protocol/evaluation_ledger.json`

The Git commit is the object referenced by the annotated tag. The runner environment is a hashed
snapshot of the VPS and toolchain, not an OCI image. The tag is pushed publicly before any output
is eligible for the v2 comparison.

Version 1 was retired after the first scheduled process had started but before it finalized: a
misplaced shell guard referenced unbound variables at finalization. The partial attempt and schedule
are preserved under `results/excluded/v1-finalizer-bug/` and contribute no prediction or process
score. Version 2 moves that guard after classification and adds an end-to-end finalizer regression
test; all registered cells restart from replicate 1. Before the v2 freeze, only process state and
trace-file size—not event contents, predictions, or workspace contents—were inspected. Its 112-file
checksum ledger hashes to `05942aa5bebd7f45787cb6e5e57f54909f69bc60cd96e8c56be12cae0794eaf2`.

The preserved preflight established for both treatments that the agent namespace could not read the
hidden-measurement canary or arbitrary host paths, inherited host variables were cleared, only the
selected provider credential was nonempty, direct network egress failed, and both the other provider
and arbitrary domains were rejected. Real provider smokes completed for requested GPT-5.6 Sol and
served `claude-fable-5`; the latter solved a neutral slab-conduction problem. Separate Fable probes
preserved and correctly classified a refusal and an automatic Opus fallback; neither is eligible for
Fable prediction-quality scoring.

Codex JSONL records the requested model and session but does not expose a per-message server-model
field equivalent to Claude's. Results therefore disclose GPT-5.6 Sol as the requested/assumed served
model, with the exact CLI and native binary hashes recorded in `environment.json`.
