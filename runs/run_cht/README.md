# RCCS calculation — output/

**Main deliverable:** `calculation_note.md` — the calculation note answering all requested items
(mass flow, air ΔT, riser & plate wall temperatures, radiation/convection split, accident-case
peak temperatures & safety, weather sensitivity), each with assumptions and confidence, plus an
independent higher-fidelity CFD cross-check of the wall temperatures.

## Working files

| File | What it is |
|---|---|
| `props.py` | Air properties (CoolProp, 1 atm, dry air) |
| `geom.py` | Facility geometry derived from `inputs/01` (verified against provided values) |
| `model.py` | Reduced loop model: draft/loss balance → ṁ; energy → ΔT; cavity radiation+convection → plate & riser T; perimeter fin → front-face T |
| `cases.py` | Runs Case 1 baseline, Case 2 accident transient, Case 3 weather sweep; writes `results.json` + figures |
| `parasitic.py` | Independent parasitic-loss estimate justifying Q_air ≈ 56 kW of 82 kWe |
| `results.json` | All numeric results incl. CFD cross-check |
| `figs/case2_transient.png` | Accident decay-heat transient: plate temp tracks quasi-steady, peaks ≈372 °C, levels off |
| `figs/case3_weather.png` | Sensitivity of ṁ and plate T to outdoor temperature and wind |
| `figs/cfd_profiles.png` | CFD axial wall-temperature profiles vs reduced-model points |
| `cfd/rccs2d/` | OpenFOAM `buoyantSimpleFoam`+fvDOM 2-D cavity CFD (heat flux prescribed, temperatures solved, radiation included) |

## Reproduce

```
pip install CoolProp                       # 8.0 used
python3 cases.py                           # reduced model + figures + results.json
python3 parasitic.py                       # parasitic-loss estimate
# CFD (Docker): image opencfd/openfoam-default:2312
cd cfd/rccs2d && python3 genfields.py      # regenerate 0/ fields
#   blockMesh; then ramp the plate flux to 5501 W/m2 (see ramp5.sh) and read
#   areaAverage(plate)/(riser) of T and qr from the logs / postProcessing.
```

## Headline results (Case 1, Q_air = 56 kW, inlet 20 °C, outdoor 2 °C)

| Quantity | Reduced model | CFD cross-check |
|---|---|---|
| Mass flow | 0.57 kg/s = 34 kg/min | (flow set separately; see note) |
| Air ΔT across risers | 97 °C | — |
| Heated-wall (plate) T | 372 °C | 333 °C |
| Riser wall T (z=3.5 m) | 131 °C mean / 181 °C front | 122–124 °C (mean) |
| Radiation / convection | 91 % / 9 % | 89 % / 11 % |
| Accident peak plate T | ≈372 °C — **levels off, stays < 550 °C** | — |

Every number was derived from `inputs/` + first-principles physics and cited general
correlations. No facility test data or pre-made model was consulted.
