# NSTF-Bench

Can a coding agent do engineering analysis? NSTF-Bench asks one hard question instead of many
easy ones: given a bounded evidence pack about **Argonne's NSTF** — a half-scale, 26-metre
passive reactor-cavity cooling facility that a US national lab instrumented and measured for 33
months — predict what the lab measured, blind, with calibrated uncertainty.

The agent receives geometry, materials, instrument locations, and the electrical heater program.
It does **not** receive the thermal duty (it must derive it from an energy balance), any measured
outcome, or network access to the facility's publications. It must leave a calculation note and a
machine-readable `output/predictions.json` — a point estimate plus P10/P50/P90 for every numeric
target and a committed category for every qualitative one — which a deterministic scorer compares
against the held-out measurements.

## Quickstart

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), and [Harbor](https://github.com/laude-institute/harbor)
(`uv tool install harbor`).

```bash
git clone https://github.com/charles-azam/nstf-bench.git
cd nstf-bench

# 1. Wiring check: the oracle replays the held-out answers (expect reward ~1.0)
harbor run --path harbor/nstf-blind --agent oracle

# 2. A real agent run (requires the provider credential for your agent)
harbor run --path harbor/nstf-blind --agent claude-code --model claude-opus-4-8 -n 1
```

Each trial directory contains the agent trajectory, the workspace, and the verifier outputs:
`reward.json` (headline scalar), `summary.json` (the full score vector and audit flags), and
`scores.jsonl` (per-metric records).

To validate the repo itself:

```bash
uv sync --dev
uv run pytest
bash protocol/validate_task_packs.sh
```

## The two tasks

| Task | What the agent gets | What it measures |
|---|---|---|
| `harbor/nstf-blind` | Evidence pack **without** the thermal duty | The primary benchmark: derive the duty from a heater/structure energy balance, propagate its uncertainty into flow, temperatures, and transient behavior |
| `harbor/nstf-supplied-duty` | Same pack **plus** the duty curve | The ablation: quantifies how much of the score the withheld input is worth |

Eleven metrics per task across three tiers: baseline steady state (duty, mass flow, gas
temperature rise, plate temperature, dominant heat-transfer mode), the accident transient at its
tested peak window, and weather sensitivity. The full output contract is in each task's
`TASK.md`; the task bytes are frozen and hash-guarded by `protocol/validate_task_packs.sh`.

## Scoring

Numeric scoring is deterministic Python (`src/nstf_bench/`) — no LLM judge:

- ratio-scale quantities: `|ln(prediction / observation)|`;
- absolute temperatures: absolute error in °C (a Celsius ratio would depend on an arbitrary zero);
- P10/P50/P90 bands: the standard `α = 0.2` weighted interval score, so honest-but-sharp bands
  beat both confident misses and useless "I don't know" spans;
- categorical calls: exact match against the measured behavior;
- correlated quantities (duty, flow, ΔT share one energy balance) carry a `dependency_group`
  label so three faces of one insight are never counted as three wins.

The headline `reward` is the **median per-metric normalized score** in `[0, 1]` (per-metric
formulas in `src/nstf_bench/harbor_scoring.py`). The rest of the vector — completion, schema
compliance, artifact validity, categorical pass rate, interval coverage — is reported in
`summary.json` and is deliberately not folded into one number.

## Contamination, stated plainly

The NSTF reports are public (ANL-ART-47, OSTI 1350591), and this repository publishes the
held-out records (`expected_output/held_out.jsonl`) so anyone can verify the scoring. The benchmark
is therefore honest-participant plus audit-trail, not secrecy:

- the task environment allows only the agent provider's endpoints and package indexes
  (`network_mode = "allowlist"`; enforced by Harbor's egress-control sidecar on Linux hosts —
  on macOS the policy is recorded but not enforced, so score seed runs on Linux);
- the verifier scans the agent trajectory for web-access patterns and reports a
  `network_activity_flag` in `summary.json`;
- transcripts are the ultimate control: publish them with any result you report;
- memorized answers would show up as suspiciously perfect points with arbitrary bands across
  eleven correlated quantities — the interval score punishes exactly that signature.

None of this removes knowledge already inside model weights. Treat single-run results as
anecdotes; report ensembles.

## What changed after auditing the benchmark

This benchmark is the corrected successor of a July 2026 experiment whose first published
results were retracted by their own source audit: a TRISO material-annex equation had been
mistranscribed (one prefactor off by ~13 orders of magnitude), the NSTF pack disclosed a
thermal-duty value close to the quantity agents were asked to infer, a peak-window average had
been described as a maximum, and several dependent records were treated as independent evidence.
Four preregistered rebuild campaigns (v1–v4) then each failed for an independent infrastructure
reason before producing a score. The corrected task packs, evaluator, and every failure record
are preserved: see [`docs/HISTORY.md`](docs/HISTORY.md),
the equation-error record ([`TRISO_CORRECTIONS.md` at the v4 tag](https://github.com/charles-azam/nstf-bench/blob/benchmark-2026-07-12-v4/protocol/TRISO_CORRECTIONS.md)), and the tag
[`benchmark-2026-07-12-v4`](https://github.com/charles-azam/nstf-bench/tree/benchmark-2026-07-12-v4)
(excluded-campaign records under `results/excluded/`, the retired TRISO task under `tasks/`).
NSTF-Bench keeps the audited task bytes unchanged and replaces the frozen-host campaign
machinery with a community-runnable Harbor harness.

## Repository layout

```
inputs/                        canonical frozen evidence packs (byte-guarded)
expected_output/held_out.jsonl the scoring records, with evidence classes and provenance
sources/                       the original OSTI reports every held-out value traces to
harbor/nstf-blind/             the primary Harbor task (pack copy, verifier, oracle)
harbor/nstf-supplied-duty/     the ablation task
src/nstf_bench/                deterministic evaluator + score-task CLI
protocol/                      pack validator, frozen prompt, freeze records
scripts/                       sync_harbor_assets.py, seed_runs.sh
docs/                          HISTORY.md, VPS_FOLLOWUP.md
```

Derived copies inside `harbor/` are regenerated by `scripts/sync_harbor_assets.py` and guarded
by `tests/test_harbor_wiring.py`.

## Seed runs

`scripts/seed_runs.sh` runs the two tasks across the installed agents (`-n 3` each) and collects
the verifier outputs. Results are reported descriptively — score vectors and transcripts, no
leaderboard scalar across unlike quantities. Publish the full trial trees with any numbers you
cite.
