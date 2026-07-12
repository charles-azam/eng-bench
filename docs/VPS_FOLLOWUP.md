# VPS follow-up: verify and seed NSTF-Bench

You are an autonomous agent on a Linux VPS. Your job: finish the container-level verification of
the NSTF-Bench Harbor tasks that could not run on macOS, prove the network allowlist is enforced,
then run the seed campaign and package the results for harvest. Work top to bottom; each phase
gates the next. Write a running `~/nstf-verify/REPORT.md` as you go — it is the deliverable.

## Context (read once)

`github.com/charles-azam/nstf-bench` (formerly eng-bench) is a benchmark for agentic engineering
analysis: an agent gets a frozen evidence pack about Argonne's NSTF passive cooling facility and
must leave `output/predictions.json`, scored by a deterministic evaluator against held-out
measurements. Two Harbor tasks: `harbor/nstf-blind` (primary) and `harbor/nstf-supplied-duty`
(ablation). Everything host-level is already verified (pytest green, oracle scoring path
returns reward 1.0 via the vendored scorer). What has NEVER run is `harbor run` itself in a
container, and allowlist enforcement — which only works on Linux. That is why you exist.

## Hard rules

- **Never modify**: `inputs/`, `protocol/PROMPT.md`, `expected_output/held_out.jsonl`, `sources/`,
  `harbor/*/environment/pack/`, `harbor/*/tests/`, `harbor/*/instruction.md`,
  `harbor/*/solution/predictions.json`. If a failure seems to require touching these, STOP and
  record it in REPORT.md instead — a human decides.
- Fixes are allowed only in: `harbor/*/task.toml` (e.g. extending `allowed_hosts`, timeouts),
  `harbor/*/environment/Dockerfile`, `harbor/*/tests/test.sh`, `harbor/*/solution/solve.sh`,
  `scripts/`. Record every change and why in REPORT.md. Do not commit or push; the operator
  reviews the diff at harvest.
- Do not delete anything you did not create. Do not add gates, hashing, or campaign machinery.
- Run long steps inside tmux so they survive disconnects.

## Phase 0 — environment setup

You normally already sit inside a clone of `github.com/charles-azam/nstf-bench` (this file is
`docs/VPS_FOLLOWUP.md` in it). Read `CLAUDE.md` first, then:

```bash
mkdir -p ~/nstf-verify
# Docker (skip if `docker info` works)
command -v docker >/dev/null || (apt-get update && apt-get install -y docker.io && systemctl enable --now docker)
# uv + ripgrep
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v rg >/dev/null || apt-get install -y ripgrep
# Harbor (latest; must be >= 0.18 for network_mode/allowlist)
uv tool install harbor && harbor --version
# Repo checks (from the repo root)
uv sync --dev && uv run pytest -q && bash protocol/validate_task_packs.sh
```

Expected: all tests pass, `task-pack static validation passed`. If not, STOP and report.

## Phase 1 — oracle and nop runs (the pending verification)

```bash
harbor run --path harbor/nstf-blind --agent oracle
harbor run --path harbor/nstf-supplied-duty --agent oracle
harbor run --path harbor/nstf-blind --agent nop
```

For each trial, find the trial dir under the harbor jobs directory and record in REPORT.md:
`verifier/reward.json` content, whether `verifier/summary.json` and `verifier/scores.jsonl`
exist, and the trial status from `result.json`.

**Pass criteria:** oracle reward ≥ 0.95 on both tasks; nop reward exactly 0.0 with no verifier
crash. Known wiring facts if you must debug: the verifier calls
`PYTHONPATH=/tests python3 -m nstf_bench score-task ...` (module invocation — `nstf_bench.cli`
does NOT execute main); reward.json must stay single-key `{"reward": x}`; never write a
reward.txt (it shadows reward.json).

## Phase 2 — allowlist enforcement probe

Prove the egress control actually blocks non-allowlisted hosts. Use a scratch copy — never the
real task:

```bash
cp -r harbor/nstf-blind /tmp/nstf-egress-probe
cat > /tmp/nstf-egress-probe/solution/solve.sh <<'EOF'
#!/bin/bash
mkdir -p /app/output
{ curl -sS -m 15 -o /dev/null -w "pypi:%{http_code}\n" https://pypi.org/simple/ || echo "pypi:BLOCKED"
  curl -sS -m 15 -o /dev/null -w "osti:%{http_code}\n" https://www.osti.gov/ || echo "osti:BLOCKED"
} > /app/output/egress.txt 2>&1
cp /solution/predictions.json /app/output/predictions.json
echo "# probe" > /app/output/calculation_note.md
EOF
chmod +x /tmp/nstf-egress-probe/solution/solve.sh
harbor run --path /tmp/nstf-egress-probe --agent oracle
```

Read `output/egress.txt` from the trial workspace. **Pass:** pypi reachable (200), osti BLOCKED.
If both are reachable, the sidecar is not enforcing — record harbor version, docker version,
kernel, and the harbor run logs in REPORT.md and STOP the campaign (seed runs without
enforcement are still valid but must be labeled `network_enforced: false`).

## Phase 3 — one real agent smoke run

Requires `ANTHROPIC_API_KEY` (or an authenticated claude CLI). Use a cheap model first:

```bash
harbor run --path harbor/nstf-blind --agent claude-code --model claude-haiku-4-5 -n 1
```

Record: trial completed; a trajectory exists under the trial's agent dir; reward parses;
`summary.json` has `network_activity_flag` populated (true or false, either is fine — it must
exist). If the agent CLI fails to reach its provider, extend `allowed_hosts` in
`harbor/nstf-blind/task.toml` minimally (add the exact blocked host from the error), record the
addition, and retry once.

## Phase 4 — seed campaign

Only if Phases 1–3 passed. In tmux:

```bash
TRIALS=3 bash scripts/seed_runs.sh 2>&1 | tee ~/nstf-verify/seed_runs.log
```

Edit the `AGENTS` array in `scripts/seed_runs.sh` first to match the credentials actually
available on this box (claude-code with the best available Claude model; codex only if an OpenAI
credential exists — skip absent providers rather than failing). Budget expectation: each trial
runs up to 75 min; 2 tasks × 3 trials per agent. Monitor, don't babysit.

## Phase 5 — package for harvest

```bash
mkdir -p ~/nstf-verify/curated
# For every trial: keep the small artifacts
#   workspace output/predictions.json + output/calculation_note.md,
#   verifier/reward.json + summary.json + scores.jsonl, config.json, result.json
# → ~/nstf-verify/curated/<task>-<agent>-<trial-id>/
# Full raw trial trees (trajectories included):
tar czf ~/nstf-verify/raw-trials-$(date +%Y%m%d).tgz -C <harbor-jobs-dir> .
```

Finish REPORT.md with: a table (task × agent × trial → reward, status, network flag), every
file you modified and why, anomalies, and wall-clock/cost notes. Leave everything in place; the
operator harvests from the Mac. Do not delete the VPS or any run directory.
