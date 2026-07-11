# eng-bench

Can a native coding agent make useful engineering predictions from a bounded evidence pack, before
it sees the experimental outcome?

This repository contains the frozen `2026-07-11-v1` comparison of:

- Codex with requested model GPT-5.6 Sol;
- Claude Code with served model Claude Fable 5.

The two primary tasks are deliberately unlike one another. NSTF asks the systems to predict heat
removal by a half-scale, air-cooled natural-circulation loop from electrical heater input. TRISO asks
them to predict coated-particle failures and fission-product release across five furnace histories,
while deciding which conclusions the supplied material annex can actually support.

The comparison is between native agent systems—not bare model APIs. CLI behavior, tool use,
reasoning effort, isolation, and model fallback are part of the treatment and are disclosed.

## Start here

- [`PROTOCOL.md`](PROTOCOL.md): preregistered design, failure rules, and scoring dimensions.
- [`protocol/FREEZE_RECORD.md`](protocol/FREEZE_RECORD.md): immutable hashes and isolation claims.
- [`tasks/`](tasks): human-readable source packs; only assembled task files are visible to agents.
- [`measurements/held_out.jsonl`](measurements/held_out.jsonl): outcomes opened only by the evaluator.
- [`src/eng_bench/`](src/eng_bench): typed deterministic evaluator.
- [`runner/`](runner): VPS isolation, capture, fallback detection, normalization, and scheduling.
- [`tests/`](tests): end-to-end evaluator and protocol-integrity tests.

After the runs, raw attempt directories and machine-readable scores are published under `results/`.
There is intentionally no overall leaderboard scalar: unlike evidence classes and unlike physical
tasks are kept separate.

## What changed after auditing the first benchmark

The earlier repository state is preserved by Git history and the tag `capstone-v1-2026-07-03`; its
runs are not scores in this version. A line-by-line source audit found defects important enough to
invalidate a simple model-versus-model headline:

- a TRISO cesium-diffusion equation was transcribed incorrectly;
- the NSTF pack leaked the thermal-duty values it later claimed to predict;
- an accident table was described as maxima although it reported a peak-window average;
- a post-peak cooldown and a numeric radiation fraction were claimed without source support;
- several TRISO counts, onset times, and Kr-85 releases were treated as independent measurements
  although the source describes them as one dependent inference chain.

Version 1 corrects those errors, registers evidence classes and dependency groups, removes unsupported
targets, and adds an NSTF supplied-duty ablation so the value of the leaked input is measured rather
than hand-waved.

## Reproduce the evaluator

Python 3.13 or later and UV are required.

```bash
uv sync --dev
uv run pytest
bash protocol/validate_task_packs.sh
```

To assemble the exact agent-visible protocol tree in a new directory:

```bash
bash protocol/assemble_frozen_packs.sh /tmp/eng-bench-protocol
cd /tmp/eng-bench-protocol
sha256sum --check manifest.sha256
```

The evaluator accepts JSONL manifests and predictions produced by the runner:

```bash
uv run eng-bench evaluate \
  --manifests results/manifests.jsonl \
  --predictions results/predictions.jsonl \
  --measurements measurements/held_out.jsonl \
  --ledger protocol/evaluation_ledger.json \
  --artifact-root results/raw \
  --output-dir results/evaluation
```

## Integrity boundary

Each attempt receives a fresh writable copy of one frozen pack; an immutable hash-checked snapshot
is retained outside the agent namespace. Held-out measurements, old runs, evaluator code, protocol
files, and host paths are absent. Direct network
egress is denied; a fail-closed CONNECT proxy permits only the provider endpoint required by the
selected CLI. Raw JSONL events, stderr, proxy decisions, workspace files, requested/served model
identity where exposed, toolchain hashes, and timestamps are retained.

Claude events expose the actual assistant model and fallback events. Fable refusals and Opus fallback
answers are preserved but cannot contribute to Fable quality metrics. Current Codex JSONL does not
expose an equivalent per-message server-model field, so GPT-5.6 Sol is disclosed as the requested and
assumed served model, with exact CLI/native hashes.

The frozen environment record is a hash-covered VPS/toolchain snapshot, not an OCI image. Native
agent credentials must be readable by their CLI process and are therefore technically readable by a
shell child inside the same sandbox; they are never copied into artifacts. This limitation does not
expose held-out measurements, but it is part of the threat model.
