# Boundary Conditions & Operating Cases

> The heat-input and ambient conditions for each case. Controlled inputs only.

## Heater system (how heat enters the cavity)

- 220 ceramic plate heaters behind the steel plate, grouped into **40 control zones** (10 axial
  segments × 4 azimuthal zones). Power can be **shaped axially and azimuthally**. Max facility
  electric power ≈ **220 kW**.
- The plate radiates this (minus parasitic structural losses) across the cavity to the risers.

---

## Case 1 — Baseline steady state

The best-characterized steady-state point.

- Heater: **uniform (linear) axial profile**, steady **electric power ≈ 82 kWe** (this
  corresponds to the scaled 1.5 MWt peak-accident duty).
- Mode: **natural circulation** (no blowers); dual vertical chimney stacks, open.
- Geometry: baseline (riser-to-plate spacing 70.66 cm, chimney discharge height 19.6 m — see
  `01_facility_geometry.md`).
- Ambient: outdoor air ≈ +2 °C; building/inlet air ≈ 20 °C; low wind.

---

## Case 2 — Accident decay-heat transient

A slow transient following a scaled reactor decay-heat curve: normal load (700 kWt → **26.16 kWt**
½-scale), then decay heat rises to the **1.5 MWt peak → 56.07 kWt** ½-scale, peaking at ½-scale
time **t ≈ 84.85 h** (full-scale 120 h), then declining. Natural circulation throughout.

Decay-heat power profile (digitized reactor "RCCS removal" curve, normalized; 10th-order
polynomial in t = minutes; electric watts = [Σ Cₙ·tⁿ] × Pscale, Pscale = 90 → ≈56 kWt peak):

```
C0 = 466.531039994        C5 = -1.27606140005e-14
C1 = 0.078631095079       C6 =  2.04789514471e-18
C2 = 0.000170562320568    C7 = -2.08318254453e-22
C3 = -1.28449427566e-07   C8 =  1.29530038954e-26
C4 =  5.09424812301e-11   C9 = -4.48601180685e-31
```
(The C10 term is referenced but not listed in the source; C0–C9 reproduce the curve to corr.
0.99996. Alternatively impose the normalized shape: 26 → 56 kWt rise over ~85 h, peak at 84.85 h,
then decay.)

---

## Case 3 — Weather sensitivity

The same baseline heat load (Case 1), but with outdoor conditions varying over the facility's
operating range: **outdoor air temperature −18 °C to +24 °C, wind speed 0 to ~11 m/s.**

---

## Case 4 (optional) — Power-shape variations

Same integral power as baseline, redistributed:

- **Cosine axial profile** — per-zone peaking factors over the 10 axial zones (bottom→top):

  | Zone | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | Mid-plane cosine | 0.498 | 0.831 | 1.010 | 1.140 | 1.248 | 1.313 | 1.294 | 1.157 | 0.904 | 0.605 |
  | Bottom-peaked | 1.225 | 1.325 | 1.425 | 1.375 | 1.275 | 1.150 | 0.900 | 0.650 | 0.450 | 0.225 |

- **Azimuthal skew** — heater power split ~65%/35% (or 125%/75%) between two azimuthal zones, same
  integral power.
