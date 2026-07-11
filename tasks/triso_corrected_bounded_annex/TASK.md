# Task: TRISO accident heating with a corrected bounded annex

Task ID: `triso_corrected_bounded_annex`

Predict the response of the five irradiated TRISO fuel elements in `inputs/` during their furnace
heating schedules. For each case, report a probability distribution for the number of heating-induced
particle failures, first-failure timing or phase, final Kr-85 fractional release, and final Cs-137
fractional release. Rank the cases from greatest to least degradation and explain the temperature,
burnup, fluence, and exposure-time effects.

The material annex is deliberately **bounded, not complete**. Use its equations correctly, but do not
claim that a failure count is uniquely derivable if pressure generation, corrosion, stress history,
defects, or another required mechanism is absent. You may introduce an offline engineering prior or
simplifying model, but label it as an outside-annex assumption, test its sensitivity, and widen the
prediction interval accordingly. Do not treat rapid SiC thermal decomposition as an established
1600-1800 C mechanism merely because it occurs above 2000 C.

At minimum:

- distinguish the reported SiC mean strength from the derived Weibull scale;
- show the corrected Cs-in-SiC diffusivity checksum at 1600 C with `Gamma = 2`, then use each
  case's reactor-specific fluence in that equation;
- separate conditional release through intact SiC from release after an assumed coating failure;
- propagate layer-thickness and strength variability rather than using only the mean particle;
- identify predictions that the annex supports, partially supports, or cannot identify;
- state the most uncertain assumption and how it changes the case ranking.

Work fully offline. Do not inspect source reports, references, old runs, measured results, or the
internet. Create `output/calculation_note.md`, all scripts and intermediate data, and the required
JSON file.

## Required `output/predictions.json`

Include every exact case metric below:

| Metric ID | Units | Kind |
|---|---|---|
| `triso.a1.failure_count` | count | numeric |
| `triso.a1.first_failure_time_in_onset_phase_h` | h | numeric or unavailable |
| `triso.a1.failure_onset_phase` | category | categorical |
| `triso.a1.kr85_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.a1.cs137_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.a2.failure_count` | count | numeric |
| `triso.a2.first_failure_time_in_onset_phase_h` | h | numeric or unavailable |
| `triso.a2.failure_onset_phase` | category | categorical |
| `triso.a2.kr85_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.a2.cs137_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.b.failure_count` | count | numeric |
| `triso.b.first_failure_time_in_onset_phase_h` | h | numeric or unavailable |
| `triso.b.failure_onset_phase` | category | categorical |
| `triso.b.kr85_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.b.cs137_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.c1.failure_count` | count | numeric |
| `triso.c1.first_failure_time_in_onset_phase_h` | h | numeric or unavailable |
| `triso.c1.failure_onset_phase` | category | categorical |
| `triso.c1.kr85_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.c1.cs137_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.c2.failure_count` | count | numeric |
| `triso.c2.first_failure_time_in_onset_phase_h` | h | numeric or unavailable |
| `triso.c2.failure_onset_phase` | category | categorical |
| `triso.c2.kr85_fractional_release` | fraction | numeric, bounded (0, 1] |
| `triso.c2.cs137_fractional_release` | fraction | numeric, bounded (0, 1] |

Measure first-failure time from the beginning of the phase named by `failure_onset_phase`, not from
the beginning of the full furnace schedule or cumulative time at repeated temperatures. Allowed
onset-phase categories are `none`, `pre_peak`, `1600c_hold`, `1700c_hold`, `first_1800c_hold`,
`final_1800c_hold`, and `indeterminate`.

Also include:

| Metric ID | Unit | Allowed result |
|---|---|---|
| `triso.ranking.worst_case` | category | `a1`, `a2`, `b`, `c1`, `c2`, `tie`, `indeterminate` |
| `triso.ranking.c1_vs_c2_failures` | category | `c1_greater`, `c2_greater`, `equal`, `indeterminate` |
| `triso.annex.failure_count_identifiability` | category | `sufficient`, `partially_sufficient`, `insufficient` |

```json
{
  "schema_version": "1.0",
  "task_id": "triso_corrected_bounded_annex",
  "predictions": [
    {
      "metric_id": "triso.a1.failure_count",
      "point": 1.0,
      "p10": 0.0,
      "p50": 1.0,
      "p90": 5.0,
      "units": "count",
      "confidence": 0.4,
      "qualitative": null,
      "category": null,
      "source_artifact": "output/calculation_note.md"
    }
  ],
  "annex_sufficiency": {
    "status": "sufficient|partially_sufficient|insufficient",
    "missing_physics": ["item"],
    "consequence": "effect on predictions"
  },
  "most_uncertain_assumption": "statement"
}
```

The runner adds `run_id`; do not include or invent it. All shown keys are required. Include every
enumerated metric and do not add metric IDs that are not enumerated above. Counts may be non-integer
expected values, but interval endpoints must be
physically meaningful. Numeric metrics use `point == p50`, four JSON numbers,
`p10 <= p50 <= p90`, numeric `confidence` from 0 to 1, and null `qualitative` and `category`.
Fractional-release values must be strictly greater than zero and at most one. If your physical model
would round to zero, choose and disclose a positive numerical or detection floor instead.
Categorical metrics use four null numeric fields, `units: "category"`, null `qualitative`, and one
allowed value in `category`. When a no-failure prediction makes first-failure time unavailable, omit
that timing row so the evaluator records it as missing and explain why. Every `source_artifact` must
be a plain existing path under `output/`, without a heading fragment.
