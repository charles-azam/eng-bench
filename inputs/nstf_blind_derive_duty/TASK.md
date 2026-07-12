# Task: NSTF blind thermal-duty derivation

Task ID: `nstf_blind_derive_duty`

Produce an offline engineering calculation note for the passive air-cooled loop described in
`inputs/`. The electric heaters warm a mock reactor-vessel plate; heat crosses the cavity to 12 riser
ducts, and buoyancy drives air through the risers and chimney without pumps.

The thermal power that actually reaches the cavity and loop is deliberately not supplied. Derive it
from a documented heater/structure energy balance, propagate a meaningful uncertainty range, and show
how that uncertainty affects the downstream predictions. Do not silently equate electric input with
removed heat.

For the baseline, accident-through-peak, and weather cases, predict:

- total natural-circulation mass flow;
- riser gas temperature rise;
- Riser 7 mid-plane hot-face wall temperature as a useful unscored local-model output;
- heated-plate front temperature;
- whether cavity-to-riser radiation or convection dominates, with any numeric split labeled as a
  model estimate rather than a supplied observation;
- the estimated thermal duty reaching the loop;
- plate temperature, flow, gas temperature rise, and response classification at the accident-curve
  endpoint;
- weather endpoint behavior.

Explain the momentum and energy balances, loss coefficients, heat-transfer correlations, radiation
network, transient capacitances, convergence checks, and at least one independent energy-balance
check. State which inputs are inferred rather than supplied. Discuss whether the evidence is sufficient
for each claimed precision and identify missing geometry or physics.

Work fully offline. Do not inspect source reports, references, old runs, measurements, or the internet.
Create `output/calculation_note.md`, all scripts and intermediate data, and the required JSON file.

## Required `output/predictions.json`

Use the schema defined below and include every exact metric ID:

| Metric ID | Unit | Kind / allowed qualitative value |
|---|---|---|
| `nstf.baseline.thermal_duty_to_loop_kw` | kW | numeric |
| `nstf.baseline.mass_flow_kg_s` | kg/s | numeric |
| `nstf.baseline.riser_delta_t_c` | degC | numeric |
| `nstf.baseline.heated_plate_front_c` | degC | numeric |
| `nstf.baseline.dominant_transfer_mode` | category | `radiation_dominant`, `convection_dominant`, `mixed`, `indeterminate` |
| `nstf.accident.thermal_duty_at_84_85h_kw` | kW | numeric |
| `nstf.accident.mass_flow_at_84_85h_kg_s` | kg/s | numeric |
| `nstf.accident.riser_delta_t_at_84_85h_c` | degC | numeric |
| `nstf.accident.plate_front_at_84_85h_c` | degC | numeric |
| `nstf.accident.response_through_peak` | category | `bounded_through_peak`, `accelerating_without_bound_by_peak`, `indeterminate` |
| `nstf.weather.outdoor_temperature_effect_on_mass_flow` | category | `colder_increases`, `colder_decreases`, `negligible`, `indeterminate` |

```json
{
  "schema_version": "1.0",
  "task_id": "nstf_blind_derive_duty",
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
