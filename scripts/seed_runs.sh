#!/bin/bash
# Seed runs: both tasks across the configured agents, three trials each.
#
# Run on a Linux host so Harbor's egress-control sidecar actually enforces the
# allowlist (macOS records the policy but cannot enforce it). Provider
# credentials come from the environment (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...).
#
# Results land in Harbor's jobs directory; report them descriptively (score
# vectors + transcripts), never as a single leaderboard number.
set -euo pipefail

TRIALS="${TRIALS:-3}"
TASKS=(harbor/nstf-blind harbor/nstf-supplied-duty)

# agent<TAB>model pairs; extend as needed.
AGENTS=(
  "claude-code claude-opus-4-8"
  "codex gpt-5.3-codex"
)

for task in "${TASKS[@]}"; do
  for entry in "${AGENTS[@]}"; do
    read -r agent model <<<"${entry}"
    echo "=== ${task} :: ${agent} (${model}) x${TRIALS} ==="
    harbor run --path "${task}" --agent "${agent}" --model "${model}" -k "${TRIALS}" -n 1
  done
done

echo "Done. Inspect trials with: harbor viewer"
