# Task: NSTF supplied-thermal-duty ablation

Task ID: `nstf_supplied_duty`

Produce the same offline engineering calculation note requested by the blind NSTF task, using all
files in `inputs/`. This registered ablation additionally supplies the thermal duty delivered to the
test section in `inputs/05_supplied_thermal_duty.csv`.

Use the supplied baseline duty and linearly interpolate the accident duty table. Do not extrapolate
beyond 84.85 h. The duty is an input, not a prediction target; still echo it in the common output
contract so the downstream comparison is machine-readable. Model the natural-circulation momentum
balance, gas heating, wall/plate temperatures, dominant cavity transfer mode, transient response
through peak, and weather sensitivity with uncertainty.

Explain loss coefficients, heat-transfer correlations, radiation network, transient capacitances,
convergence checks, and at least one independent energy-balance check. Discuss whether the supplied
evidence is sufficient for each claimed precision and identify missing geometry or physics.
Report the modeled Riser 7 mid-plane hot-face temperature in the note as an unscored local output.

Work fully offline. Do not inspect source reports, references, old runs, measurements, or the internet.
Create `output/calculation_note.md`, all scripts and intermediate data, and the required JSON file.

## Required `output/predictions.json`

Include every metric below. The thermal-duty rows echo supplied inputs and are excluded from ablation
prediction-quality scoring.

| Metric ID | Unit | Kind / allowed qualitative value |
|---|---|---|
| `nstf.baseline.thermal_duty_to_loop_kw` | kW | numeric input echo |
| `nstf.baseline.mass_flow_kg_s` | kg/s | numeric |
| `nstf.baseline.riser_delta_t_c` | degC | numeric |
| `nstf.baseline.heated_plate_front_c` | degC | numeric |
| `nstf.baseline.dominant_transfer_mode` | category | `radiation_dominant`, `convection_dominant`, `mixed`, `indeterminate` |
| `nstf.accident.thermal_duty_at_84_85h_kw` | kW | numeric input echo |
| `nstf.accident.mass_flow_at_84_85h_kg_s` | kg/s | numeric |
| `nstf.accident.riser_delta_t_at_84_85h_c` | degC | numeric |
| `nstf.accident.plate_front_at_84_85h_c` | degC | numeric |
| `nstf.accident.response_through_peak` | category | `bounded_through_peak`, `accelerating_without_bound_by_peak`, `indeterminate` |
| `nstf.weather.outdoor_temperature_effect_on_mass_flow` | category | `colder_increases`, `colder_decreases`, `negligible`, `indeterminate` |

```json
{
  "schema_version": "1.0",
  "task_id": "nstf_supplied_duty",
  "predictions": [
    {
      "metric_id": "nstf.baseline.mass_flow_kg_s",
      "point": 0.5,
      "p10": 0.4,
      "p50": 0.5,
      "p90": 0.7,
      "units": "kg/s",
      "confidence": 0.7,
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

The runner adds `run_id`; do not include or invent it. All shown keys are required. Include one row
per table metric and do not add metric IDs that are not enumerated above. For numeric metrics,
`point == p50`, all four values are JSON numbers,
`p10 <= p50 <= p90`, `confidence` is a number from 0 to 1, and `category` is null. Set
`qualitative` to null for these metrics. Categorical metrics use null numeric fields,
`units: "category"`, null
`qualitative`, and one allowed value in `category`. If a metric is not supportable, omit that row so
the evaluator records it as missing and explain why. Every `source_artifact` must be a plain existing
path under `output/`, without a heading fragment.
