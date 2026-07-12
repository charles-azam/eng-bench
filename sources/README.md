# Source reports

The primary measured-data sources for the held-out records in `expected_output/held_out.jsonl`.
Both are public US Department of Energy reports, mirrored here for provenance and auditability.

| File | Report | OSTI |
|---|---|---|
| `NSTF_air_final_results_ANL-ART-47_osti_1350591.pdf` | ANL-ART-47, *Final Project Report on RCCS Testing with the Air-Based NSTF* — the baseline, accident-transient, and per-run measurements cited in every record's `provenance` field | [1350591](https://www.osti.gov/biblio/1350591) |
| `NSTF_air_ambient_effects_osti_1389835.pdf` | Ambient-effects companion report — the weather-sensitivity evidence | [1389835](https://www.osti.gov/biblio/1389835) |

SHA-256:

```
5737f481fa1c3052…  NSTF_air_final_results_ANL-ART-47_osti_1350591.pdf
b28c3153deb9d823…  NSTF_air_ambient_effects_osti_1389835.pdf
```

(Full digests: `shasum -a 256 sources/*.pdf`.)

**These files never enter an agent-visible surface.** The Harbor build context is
`harbor/*/environment/` only, and the task rules forbid consulting source reports. They exist so
a reviewer can trace every held-out value to its printed page without leaving the repository.
