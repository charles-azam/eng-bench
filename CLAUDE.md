# NSTF-Bench — agent instructions

This repository is a community-runnable benchmark for agentic engineering analysis: one hard
problem (Argonne's NSTF passive cooling facility), frozen evidence packs, held-out measured
data, and a deterministic uncertainty-aware scorer. `README.md` is the entry point;
`docs/HISTORY.md` explains how it got here. This repo is the single source of truth — work
continues from a fresh `git clone` on any machine (Mac for development, a Linux VPS for
container verification and seed runs).

## If you are the VPS agent

Read and execute `docs/VPS_FOLLOWUP.md` top to bottom. It verifies the Harbor tasks in Docker,
proves allowlist enforcement, and runs the seed campaign.

## Repository map

```
inputs/            canonical frozen evidence packs (two task variants + shared inputs)
expected_output/   held_out.jsonl — the scoring records (never agent-visible at run time)
sources/           the original OSTI reports the held-out values come from
harbor/            the two runnable Harbor tasks (derived copies of the above)
src/nstf_bench/    deterministic evaluator + score-task CLI
tests/             pytest suite incl. integrity + drift guards
protocol/          pack validator, frozen prompt, evaluator manifest, freeze records
scripts/           sync_harbor_assets.py, seed_runs.sh
docs/              HISTORY.md, VPS_FOLLOWUP.md
```

## Standing rules for any session

- **Frozen bytes:** `inputs/**` and `protocol/PROMPT.md` must not change.
  `bash protocol/validate_task_packs.sh` and `uv run pytest` enforce this — keep both green.
- **Separation of powers:** `expected_output/held_out.jsonl` and `sources/` never enter an
  agent-visible surface. In Harbor tasks the held-out copy lives under `tests/`, which Harbor
  uploads only after the agent finishes.
- **Hash discipline:** any change under `src/nstf_bench/`, `tests/`,
  `expected_output/held_out.jsonl`, `pyproject.toml`, or `uv.lock` requires
  `uv run nstf-bench freeze-evaluator` and pasting the printed hash into
  `protocol/evaluation_ledger.json`, or the integrity test fails.
- **Derived copies:** never hand-edit `harbor/*/environment/pack/`, `harbor/*/tests/held_out.jsonl`,
  `harbor/*/tests/nstf_bench/`, `harbor/*/instruction.md`, or `harbor/*/solution/predictions.json`.
  Regenerate with `uv run python scripts/sync_harbor_assets.py` (guarded by
  `tests/test_harbor_wiring.py`).
- **Scoring is deterministic Python only.** No LLM judges in the numeric path. Report score
  vectors and transcripts, never a cross-quantity leaderboard scalar.
- **Rigor level:** reproducible eval + published transcripts. Do not reintroduce frozen-host
  metrology, eligibility gates, or preregistration machinery — that is the v1–v4 failure mode
  documented in `docs/HISTORY.md`.
- **Minimalism is a standing preference.** When in doubt, less machinery.
