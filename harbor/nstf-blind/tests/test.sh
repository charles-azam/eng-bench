#!/bin/bash
# Verifier: score /app/output/predictions.json against the held-out measurements.
# Fail-closed: a reward.json must exist when this script exits, whatever happens.
set -u

mkdir -p /logs/verifier

PYTHONPATH=/tests python3 -m nstf_bench score-task \
  --predictions /app/output/predictions.json \
  --task-variant nstf_blind_derive_duty \
  --measurements /tests/held_out.jsonl \
  --workspace /app \
  --agent-logs /logs/agent \
  --output-dir /logs/verifier

if [ ! -f /logs/verifier/reward.json ]; then
  echo '{"reward":0.0}' > /logs/verifier/reward.json
fi
