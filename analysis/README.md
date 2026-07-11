# Results harvester

The harvester verifies copied raw run directories before producing any evaluator input. It checks
the fixed artifact ledger, exact input/workspace file sets and hashes, rejects symlinks, reconciles
the run ID across directory/metadata/manifest records, and enforces the preregistered one-retry rule.

Run it only on the clean v2 raw-results directory. The excluded v1 partial attempt must remain in a
separate `excluded/` tree and is explicitly rejected as a harvest root or child.

```bash
uv run python -m analysis.harvest \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root results/schedules/v2 \
  --output-dir results/harvested
```

The command verifies each present stage schedule and checksum against the frozen matrix, shuffle
seed, launch order, and run chronology. A missing schedule for an unlaunched later stage is allowed;
a launched stage without its schedule is not. Each stage requires a portable `*.tsv.sha256`;
an archived `*.tsv.vps.sha256` sidecar is also verified against the exact frozen VPS pathname when
present. A regular `README.md` may accompany the schedules as provenance. The command writes
`attempts.csv`, `eligibility.json`,
`eligibility.csv`, `integrity.jsonl`, `schedule_integrity.jsonl`, and gated `manifests.jsonl` /
`predictions.jsonl` pairs under `n3/`, `n5/`, and `ablation/`. An
ineligible dataset is represented by empty JSONL files so a partial comparison cannot be scored by
accident. Physical infrastructure failures and their retry remain visible in the eligible dataset;
eligibility counts the final outcome once per scheduled replicate.
