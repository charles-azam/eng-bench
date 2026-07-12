# NSTF-Bench — project constitution

**Maintainer note:** the full project memory (history, campaign records, infrastructure runbook,
roadmap) is kept **locally in `handoff/`**, which is git-ignored and deliberately not published.

This repository is a community-runnable benchmark for agentic engineering analysis: one hard
problem (Argonne's NSTF passive cooling facility), frozen evidence packs, held-out measured
data, and a deterministic uncertainty-aware scorer. `README.md` is the entry point;
`docs/HISTORY.md` explains how it got here (and why the previous campaign machinery is gone).

## Standing rules for any session

- **Frozen bytes:** `tasks/nstf_*/TASK.md`, `tasks/nstf_common/inputs/*`,
  `tasks/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv`, and `protocol/PROMPT.md` must
  not change. `protocol/validate_task_packs.sh` and pytest enforce this — keep them green.
- **Separation of powers:** the held-out records (`measurements/held_out.jsonl`) never enter an
  agent-visible surface. In Harbor tasks they live under `tests/`, uploaded only after the agent
  finishes.
- **Hash discipline:** any change under `src/nstf_bench/`, `tests/`, `measurements/held_out.jsonl`,
  `pyproject.toml`, or `uv.lock` requires `uv run nstf-bench freeze-evaluator` and pasting the
  new hash into `protocol/evaluation_ledger.json`, or the integrity test fails.
- **Derived copies:** never hand-edit files under `harbor/*/environment/pack/`,
  `harbor/*/tests/held_out.jsonl`, `harbor/*/tests/nstf_bench/`, `harbor/*/instruction.md`, or
  `harbor/*/solution/predictions.json` — regenerate with
  `uv run python scripts/sync_harbor_assets.py` (guarded by `tests/test_harbor_wiring.py`).
- **Scoring is deterministic Python only.** No LLM judges in the numeric path. Report score
  vectors and transcripts, never a cross-quantity leaderboard scalar.
- **Rigor level:** reproducible eval + published transcripts. Do not reintroduce frozen-host
  metrology, eligibility gates, or preregistration machinery — that is the v1–v4 failure mode
  documented in `docs/HISTORY.md`.
- **Minimalism is a standing preference.** When in doubt, less machinery.
