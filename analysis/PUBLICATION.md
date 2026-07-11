# Publication tables

`analysis.publication` is a post-evaluation, analysis-only audit and export. It
does not modify the frozen protocol. It re-verifies the raw run ledgers,
recomputes the selected dataset gate, validates the randomized schedules, and
reruns the frozen evaluator before writing article data. Supplied scores and
summary must be model-equal to that independent recomputation.

Run it once for each gated dataset that was actually evaluated:

```sh
uv run python -m analysis.publication \
  --dataset n5 \
  --manifests results/harvested/n5/manifests.jsonl \
  --predictions results/harvested/n5/predictions.jsonl \
  --measurements measurements/held_out.jsonl \
  --scores results/evaluation/n5/scores.jsonl \
  --summary results/evaluation/n5/summary.json \
  --attempts results/harvested/attempts.csv \
  --schedule-integrity results/harvested/schedule_integrity.jsonl \
  --eligibility results/harvested/eligibility.json \
  --matrix protocol/matrix.tsv \
  --schedules-root results/schedules/v2 \
  --runs-root results/raw \
  --artifact-root results/raw \
  --ledger protocol/evaluation_ledger.json \
  --evaluator-manifest protocol/evaluator_manifest.sha256 \
  --evaluator-root . \
  --output-dir results/publication/n5
```

`--measurements` must resolve to
`<evaluator-root>/measurements/held_out.jsonl`, with the hash frozen in the
evaluator manifest. `--artifact-root` must resolve to the verified
`--runs-root`. The selected eligibility record must be true and exactly match
the gate recomputed from raw runs and the frozen matrix. The harvested
manifests and predictions must equal every physical attempt selected by that
gate, including infrastructure retries.

The output path must not exist, including as a broken symlink. All files are
rendered in a fresh same-parent staging directory and atomically renamed into
place. The command never silently overwrites an older publication bundle.

Outputs:

- `run_status.csv`: one row per physical attempt. Scheduled replicate,
  physical attempt, retry, and final-attempt fields are separate.
- `cell_status.csv`: scheduled-replicate eligibility and explicit physical
  status counts for each task/system cell.
- `replicate_metrics.csv`: one row for every physical attempt and held-out
  measurement, including missing predictions, `required=false` descriptive
  records, and non-scorable outcomes. Optional records explicitly set
  `evaluator_row_present=false` because the evaluator does not score them.
  `point`/`p10`/`p50`/`p90` are evaluator-normalized into `units`; the raw
  submitted values and units are retained separately. Evidence and dependency
  groups are never collapsed.
- `task_metric_summary.csv`: the frozen evaluator aggregates, with an explicit
  numerator/denominator (or denominator for means) beside every rate and mean.
  Units, evidence class, dependency group, required flag, and measurement
  provenance remain on every metric summary row.
- `claims.json`: exact cell sizes, attempts, retries, all six run statuses,
  stage completion, and both prediction-interval and accepted-interval pass
  numerators/denominators for every task/system/metric.
- `chart_data.json`: every `replicate_metrics.csv` row as canonical JSON for
  charts. Its grain is `physical_attempt_x_measurement`; it is not a table
  of means.
- `provenance.json`: the chosen eligible gate, exact row/input counts, hashes
  for every supplied source, every frozen schedule file, the independently
  verified raw-integrity snapshot, and every data output.
- `sha256_manifest.json`: source hashes plus hashes for every table, claims,
  chart, and `provenance.json`. It explicitly excludes its own path to avoid a
  self-referential digest.

Limitations:

- Exact recomputation proves consistency with the hash-frozen evaluator, not
  the scientific validity or independence of the frozen measurements and task
  design.
- Schedule files and raw chronology are rechecked, but the publication bundle
  records schedule hashes rather than duplicating the randomized schedule rows.
- Coverage denominators include only rows for which the evaluator emitted the
  corresponding Boolean. Zero denominators remain explicit rather than being
  converted to zero-percent claims.
- Optional `required=false` measurement records appear in the replicate table,
  but their evaluator fields are null because they are not evaluator score rows.
- No hypothesis tests, cross-provider token comparison, overall score, or
  winner claim is produced.
