# ⛔ HELD-OUT — Measured NSTF Results (scoring targets)

All values from **ANL-ART-47** (Argonne, Aug 2016). Units as printed; notes flag the report's
own labelling quirks. "Riser 7" is the fully instrumented duct; mid-plane z = 3500 mm.

---

## 1. Baseline steady state — Table 32 (8 repeat runs, identical setup, varying weather)

Outdoor air spanned −18.1 °C → +23.7 °C across these 8 runs. Thermal power held ~constant; the
**flow and ΔT shift with weather** (this is Case 3, the surprise).

| Quantity | Unit | Run011 (primary) | Mean (8 runs) | Min | Max |
|---|---|---|---|---|---|
| Heater electric power | kWe | 81.99 | 80.4 | 78.4 | 82.0 |
| **Thermal power removed** | kWt | **56.12** | 51.7 | 48.6 | 56.1 |
| **Heated plate, front** | °C | **390.66** | 390.5 | 382.5 | 397.5 |
| Ceramic heaters | °C | 568.41 | 565.8 | 554.5 | 578.8 |
| **Riser duct wall** (mid-plane) | °C | **163.11** | 167.5 | 152.5 | 183.3 |
| Cold (west) wall | °C | 138.89 | 144.0 | 131.8 | 156.1 |
| Riser inlet gas | °C | 19.74 | 23.5 | 19.7 | 30.0 |
| **Riser outlet gas** | °C | **103.85** | 108.8 | 96.9 | 124.2 |
| Outlet plenum gas | °C | 101.18 | 112.4 | 101.2 | 128.6 |
| **System mass flow rate** | kg/min | **34.46** | 33.1 | 28.1 | 36.3 |
| Riser pressure drop | Pa | 21.40 | 19.9 | 15.9 | 24.6 |
| High-bay ambient | °C | 23.86 | 29.3 | 23.9 | 34.0 |

**Derived headline numbers for Run011 (primary scoring case):**
- **Riser ΔT (gas) = 103.85 − 19.74 ≈ 84.1 °C**
- **Mass flow = 34.46 kg/min = 0.574 kg/s** (whole 12-duct loop)
- Per-riser flow ≈ 0.574 / 12 ≈ **0.0479 kg/s**
- **Electric→thermal efficiency = 56.12 / 81.99 ≈ 68%** (the held-out "~65%" figure; reported
  range 60–70%, degrading at low flow).
- Energy-balance check: ṁ·c_p·ΔT = 0.574 × 1006 × 84.1 ≈ 48.6 kW (vs 56 kWt nominal — the gap is
  measurement/averaging + the c_p/effective-ΔT subtleties; both numbers are "right" to ~10%).

---

## 2. Radiation vs convection split (Riser 7, four-face heat-flux sensors)

Radiation is the **dominant** heat-transfer mode across the cavity.

- **Front (narrow, line-of-sight) face: ≈ 40% of a duct's heat removal** (radiation-dominated).
- **Two wide side faces: ≈ 50% combined.**
- **Rear (cold, narrow) face: ≈ 10%.**
- The matte-vs-reflective sensor pairs confirm the front-face flux is overwhelmingly radiative.
- Per-face fluxes (normal/winter): hot wall **1.96 kW/m²**, cold wall **0.53 kW/m²**; at peak
  accident: hot **3.81**, cold **0.89 kW/m²**.

**Scoring intent:** a correct model must report that radiation carries the **majority** of the
heat (the report's narrative: radiation dominates; convective h ≈ 3–6 W/m²·K is small). A
defensible radiative fraction is roughly **70–90%** of cavity heat transfer.

---

## 3. Accident decay-heat transient — Run014 (winter) / Run018 (summer), Table 35/37

Steady (normal, 26 kWt-class) vs peak (decay-heat peak, 56 kWt-class):

| Quantity | Unit | Steady-state | Peak accident |
|---|---|---|---|
| Electric power | kWe | 42.08 | 90.07 |
| Test-section thermal power | kWt | 25.06 | 54.49 |
| **System flow rate** | kg/s | 0.499 | **0.585** |
| **Riser ΔT** | °C | 49.44 | **90.32** |
| **Front heated plate** | °C | 275.32 | **408.72** |
| Ceramic heaters | °C | 404.13 | 591.26 |

**Outcome (the money shot):** the mock vessel followed the decay-heat curve and **peaked near
≈409 °C at the decay-heat peak (t ≈ 92 h), then turned over and cooled as decay heat fell** — a
**bounded, self-limiting trajectory, not a runaway**. Passive RCCS removal tracked the source
power. (Wind gusts to ~22 m/s during the test caused transient chimney-flow asymmetry needing
damper action — a real-world robustness note.)

---

## 4. Robustness points (secondary, for richer scoring)

- **Blocked risers (Run015):** blocking 0→50% of riser flow area raised peak plate temperature
  only ≈ **279 → 292 °C** (~13 °C) — strong passive robustness.
- **Reduced flow (I-NERI Run023):** efficiency fell to 52% (Case I) / 42.7% (Case II) at low flow.
- **Argon ingress (Run027):** heavy-gas ingress collapsed natural circulation (flow 22.5 → ~0
  kg/min in ~90 s), then recovered — a binary stagnation/recovery behavior.

---

## 5. Measurement uncertainties (for tolerance setting)

- Mass flow: ±1% reading + 0.3 kg/min (≈ ±1 kg/min near baseline ≈ ±3%).
- Temperatures (Type-K): ±1.1 °C (gas/wall/plate), ±2.2 °C (insulated walls).
- Heat flux: ±5%.
- Run-to-run weather scatter at fixed power is **larger than instrument error** (flow ±25%
  range, riser-wall ±30 °C range) — so a single-case prediction should be scored against Run011
  specifically, while the weather sweep (Case 3) is scored on trend/magnitude.
