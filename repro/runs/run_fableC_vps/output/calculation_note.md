# Calculation Note — Passive Reactor Cavity Cooling System (½-scale air-cooled test facility)

**Date:** 2026-07-03 · **Method:** first-principles engineering model (this directory)
**Scope:** Predict the natural-circulation performance of the ½-axial-scale air-cooled RCCS
facility described in `inputs/`, for the operating cases of
`inputs/04_boundary_conditions_and_test_cases.md`.

> **Provenance statement.** Every number in this note was derived from physics and the
> geometry, materials, and boundary conditions given in `inputs/`, using the scripts in this
> directory. **No published test data, report, or pre-made model of this facility was
> consulted or searched for.** The only external material used are the standard, cited
> textbook correlations and property tables listed in §2 and the References.

---

## Executive summary (Case 1, baseline: 82 kWe, natural circulation, outdoor 2 °C)

| Quantity (at the measurement location of `inputs/03`) | Prediction | Uncertainty | Confidence |
|---|---|---|---|
| System mass flow (inlet downcomer, whole loop) | **0.56 kg/s = 34 kg/min** | ± 0.08 kg/s | medium |
| Riser gas temperature rise (outlet − inlet TC) | **128 K** (20 → 148 °C) | ± 18 K (anti-correlated with flow) | medium |
| Riser duct wall T (Riser 7, z = 3.5 m, hot/front face) | **215 °C** | ± 25 K | medium |
| Riser wall, side / rear faces (z = 3.5 m) | 177 / 188 °C | ± 25 K | medium |
| Heated-plate front temperature (representative) | **423 °C** (max 432 °C) | ± 35 K | medium-high |
| Radiative fraction of riser heat pickup | **0.86** | ± 0.05 | high |
| Heat balance | 82 kWe = 72.9 kW to air + 6.8 kW heater-back loss + 2.3 kW cavity-wall loss (11 % parasitic) | losses ± 40 % | medium |
| Accident transient peak plate temperature | **≈ 353 °C at t ≈ 85 h** — temperature **levels off** (no runaway), large margin to vessel-steel limits | ± 35 K | high (verdict), medium (value) |

The single most uncertain assumption is the set of **loop form-loss coefficients**
(± 50 % on K moves the flow ∓ 8–10 % and the riser ΔT ± 8 %); for the wind response it is
the **stack-top pressure coefficient**. Radiation dominates the cavity, so the plate
temperature is insensitive to almost everything except plate emissivity (± 13 K over the
measured 0.78–0.79 range widened to 0.7–0.9) and heated-area bookkeeping (± 10 %).

---

## 1. System and modelling approach

Heat path: 40-zone electric heater array → 1-in SAE 1020 steel plate (mock RPV wall,
ε ≈ 0.785, measured) → radiation + natural convection across a 0.71-m air cavity → 12
vertical ASTM A500 riser ducts (10 in × 2 in × 0.188 in wall, narrow face toward the
plate) → forced-convection pickup by air inside the ducts → buoyant flow through the
outlet plenum and two insulated 24-in chimney stacks discharging at 19.6 m; cool air
returns through a 24-in downcomer. The loop is open to atmosphere and entirely passive.

`rccs_model.py` solves the coupled system to numerical convergence:

| Sub-model | Method | Correlation source |
|---|---|---|
| Cavity radiation | Per-axial-slice (10 slices over 6.91 m) radiosity network over 5 gray-diffuse surface groups: plate, riser front faces, riser side faces, riser rear faces, insulated walls | Enclosure theory, Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, ch. 13 |
| View factors | 2-D Monte-Carlo ray tracing of the actual 12-duct row cross-section (400 000 rays/surface, reciprocity enforced) — `viewfactors.py`, cached in `viewfactors.json` | — |
| Cavity gas convection | Churchill–Chu vertical-surface natural convection between plate / duct faces / walls and a single well-mixed cavity-air node | Churchill & Chu (1975), *Int. J. Heat Mass Transfer* 18:1323 |
| Riser internal convection | Gnielinski, local bulk properties, (T_w/T_b)^−0.5 gas-heating correction | Gnielinski (1976); Kays & Crawford, *Convective Heat and Mass Transfer* |
| Duct wall | Per-face temperature nodes coupled by in-wall conduction and by internal front↔rear radiation exchange | 1-D conduction; parallel-strip exchange |
| Loop hydraulics | 1-D momentum balance: buoyancy integral over downcomer → risers → outlet plenum → chimney (with chimney-gas cooldown) = friction + form + acceleration losses | Petukhov smooth-tube friction (1970); Idelchik-type K values |
| Parasitic losses | Conduction through 2-in Duraboard behind the heaters (heater-sheet temperature from the required radiant flux) and through the 6-in SuperIsol walls (inner wall face solved as a radiating/convecting/conducting surface) | k(T) data given in `inputs/02` |
| Air properties | Ideal gas + Sutherland μ, k + cp table | Incropera Table A.4; White, *Viscous Fluid Flow* |

**Energy closure is exact:** 82.0 kWe = 72.9 + 6.8 + 2.3 kW.

Monte-Carlo view factors (per unit height, from the plate): riser front faces 0.28, riser
side faces (through the 58-mm gaps) 0.24, insulated walls 0.48. The duct row plus its deep
gaps behaves as a near-black absorber — this is why the results are insensitive to the
unreported riser emissivity (§7).

### 1.1 Key assumptions (numbered; sensitivities in §7)

1. **Riser surface emissivity ε = 0.80 ± 0.10** — not reported; oxidized structural steel
   tables span 0.7–0.9 (e.g. Incropera Table A.11). Near-nil effect (cavity effect above).
2. **Duct pitch 4.3 in**, row centred across the 52-in cavity (`inputs/01 §9`, nominal).
3. **Rear duct-to-wall clearance 50 mm** (not dimensioned; affects only the small
   rear-face exchange).
4. **Plate area = 1.321 m × 6.91 m = 9.13 m²**, consistent with the radiosity mesh. The
   source lists 8.82 m² (scaling table) and ≈ 10.18 m² (as-built) — a stated reporting
   inconsistency — so the wall heat flux carries ± 10 %: q″ = 82 kW/9.13 m² ≈ 9.0 kW/m²
   gross, 8.2 kW/m² net of back loss (the scaling table's design point is 6.82 kW/m²).
5. **Well-mixed cavity air** at one temperature (convection is < 15 % of cavity transfer).
6. **Downcomer inlet at ≈ 4 m elevation, neutral building pressure there; inlet air at
   building temperature 20 °C** (baseline). The ambient reference column is outdoor air
   from that level to the 19.6-m discharge.
7. **Chimney**: equivalent length 32.9 m per stack; insulated U ≈ 0.55 W/m² K including
   films → the gas cools ~5 K over the buoyant rise (stack exit ≈ 143 °C in Case 1).
8. **Form-loss coefficients**: downcomer + flow conditioner + elbow K = 2.3; re-entrant
   riser inlet 0.8; riser exit 1.0; chimney port + open dampers + exit 2.25. Engineering
   estimates (Idelchik-type) — **the most uncertain inputs**, varied ± 50 % in §7.
9. Steel k = 50 W/m K, ρ = 7850 kg/m³, cp = 480 J/kg K (standard values per `inputs/02`).
10. Uniform axial heater profile (Case 1 definition); azimuthally uniform.

---

## 2. Case 1 — Baseline steady state (82 kWe, outdoor +2 °C, building/inlet 20 °C, low wind)

### 2.1 Natural-circulation mass flow — **0.56 kg/s (34 kg/min)** · confidence: medium

The momentum balance converges at m = 0.564 kg/s: riser velocity ≈ 4.9 m/s
(Re ≈ 15 600, fully turbulent), driving head ≈ 60 Pa from the ~7-m heated column plus the
~10-m insulated chimney column against 2 °C outdoor air. Uncertainty is dominated by the
form-loss K set (± 50 % → 0.52–0.62 kg/s) and the unknown downcomer-inlet elevation
(± 0.01 kg/s). Note the measurement is a Sierra 640S in the downcomer (± 1 % + 0.3
kg/min) — instrument error is negligible next to model error.

### 2.2 Riser air temperature rise — **128 K** (20 °C → 148 °C) · confidence: medium

First-law constrained: m·cp·ΔT must equal 72.9 kW, so flow and ΔT errors anti-correlate —
the **product is known to ± 5 %** (loss split uncertainty only). If the true flow is 10 %
higher, ΔT is ~10 % lower. Gas TC locations (0.75 in above bottom lip, 4 in below top lip)
span essentially the whole heated length; the model ΔT is taken over the full riser.

### 2.3 Wall temperatures (Riser 7, z = 3.5 m mid-plane) · confidence: medium

| Surface | Prediction |
|---|---|
| Riser hot/front face (2-in face, line-of-sight to plate) | **215 °C** |
| Riser side faces (10-in faces) | 177 °C |
| Riser rear face | 188 °C |
| Riser bulk air at z = 3.5 m | 84 °C |
| **Heated plate, front (representative / mid-plane)** | **423 °C** (axial max 432 °C near the top; heater sheets ≈ 540 °C) |
| Cavity air | 231 °C |
| Insulated-wall inner face | ≈ 300 °C (radiosity equilibrium) |

The front face runs ~38 K hotter than the sides: it takes 4.3 kW/m² of net radiation on a
narrow strip, partially redistributed by wall conduction and by internal radiation to the
rear face (which is why the rear face is *hotter* than the sides). The plate temperature is
set almost entirely by radiation: T_plate ≈ [T_riser⁴ + q″/(σ·F̂)]^0.25 — an independent
two-surface hand check (`hand_checks.py`) gives 457 °C vs the network's 423 °C, and the
±(0.7–0.9) plate-emissivity band moves it 409–436 °C.

### 2.4 Radiation/convection split · confidence: high (fraction), medium (per-face values)

Of the 72.9 kW reaching the risers: **radiation 62.7 kW (86 %), cavity convection 10.3 kW
(14 %)**. The plate itself sheds 8.4 kW by convection to the cavity air (10 % of its
output); that heat still arrives at the risers/walls by convection.

Predicted mid-plane fluxes on Riser 7 (what the matte/reflective heat-flux sensor pairs
decompose; absorbed net flux, W/m²):

| Face | radiative | convective | radiative share | share of duct heat pickup |
|---|---|---|---|---|
| Hot/front | 4 310 | 40 | 0.99 | 25 % |
| Sides (each) | 900 | 200 | 0.82 | 64 % (both) |
| Cold/rear | 1 590 | 150 | 0.92 | 10 % |

The wide side faces, though at lower flux, collect ~2/3 of the total because they carry
91 % of the exterior area — radiation streams through the 58-mm inter-duct gaps and is
absorbed in the gap "cavities".

### 2.5 Auxiliary predictions

Stack-exit gas ≈ 143 °C; heater-back loss 6.8 kW + cavity-wall loss 2.3 kW → **11 %
parasitic**; plate-to-riser-front spacing at baseline 70.66 cm.
For the **normal-operation duty (26.16 kWe)**: m = 0.46 kg/s, ΔT = 47 K, plate 228 °C,
riser front (z = 3.5 m) 86 °C, radiative fraction 0.72.

---

## 3. Case 2 — Accident decay-heat transient

**Power curve.** The C0–C9 polynomial of `inputs/04` (its C10 term is missing from the
source) was evaluated and found unusable: it peaks at 87.7 kW at 71.5 h and diverges to
negative power after ~115 h (see `run_cases.py`; demonstration in the log). Per the
input file's stated alternative, the normalized shape was imposed instead: 26.16 kW →
**56.07 kW peak at t = 84.85 h**, then a slow decay-heat-like decline (∝ t^−0.25,
assumed). Because the facility thermal time constant (≈ 2 h: plate C ≈ 0.9 MJ/K against
h_eff ≈ 15–20 W/m² K over 9.13 m²) is ≪ 85 h, the transient is quasi-steady and the peak
values depend only on the 56.07-kW peak power, not on the shape details — this is the
basis for high confidence in the verdict below.

**Method.** Lumped plate capacitance C_eff = 1.25 MJ/K (plate steel 0.87 MJ/K + heater
array/board/frame allowance), dT/dt = [P(t) − Q_removed(T_plate)]/C_eff, with
Q_removed(T) precomputed by full coupled solves at fixed plate temperatures
(fig2, `results.json: char_curve`).

**Results** (baseline ambient, natural circulation throughout):

| Quantity | Prediction | Confidence |
|---|---|---|
| Peak heated-plate temperature | **≈ 353 °C at t ≈ 85.0 h** (lags the power peak by < 0.5 h) | value: medium (± 35 K); timing: high |
| Peak loop mass flow | **0.53 kg/s** | medium |
| Peak riser ΔT | 94 K | medium |
| Riser front face at peak (z = 3.5 m) | ≈ 156 °C | medium |
| Radiative fraction at peak | 0.81 | high |

**Levels off, does not run away — high confidence.** The passive removal characteristic
Q_removed(T_plate) is strongly monotonic (≈ T⁴ radiation + improving natural-circulation
convection): 59 kW at 377 °C, 96 kW at 477 °C, 224 kW at 727 °C (fig2). Any power below
~220 kW has a stable equilibrium; at the 56.07-kW peak the equilibrium is ≈ 353 °C and
the temperature follows it quasi-statically, then declines with the decay curve.

**Margin to a safe limit.** The mock vessel wall peaks at ≈ 353 °C. Against
representative reactor-vessel steel (SA-533/SA-508) limits — ~371 °C (700 °F) for normal
operation and ~538 °C (1000 °F) commonly applied for accident conditions (ASME Section
III service levels; cited as general engineering values, not facility data) — the peak
sits **below even the normal-operation limit, with ≈ 185 K margin to the accident
limit**. Even with the removal curve degraded 30 %, equilibrium at 56 kW stays below
410 °C. The 1020-steel plate itself is far from any structural concern.

---

## 4. Case 3 — Weather sensitivity (82 kWe)

### 4.1 Outdoor air temperature (−18 → +24 °C, no wind) · confidence in trend: medium-high

Two bounding couplings of the inlet to the weather (truth in between; the facility draws
outdoor air through the building):

| Outdoor T | m (kg/s), inlet 20 °C | m (kg/s), inlet = outdoor | plate T (°C), inlet 20 °C / outdoor |
|---|---|---|---|
| −18 °C | 0.624 | 0.604 | 418 / 409 |
| −10 °C | 0.599 | 0.583 | 420 / 413 |
| −2 °C | 0.576 | 0.564 | 422 / 416 |
| +6 °C | 0.553 | 0.546 | 424 / 420 |
| +14 °C | 0.532 | 0.529 | 426 / 424 |
| +24 °C | 0.507 | 0.509 | 429 / 430 |

Cold weather **helps**: a denser ambient column raises the stack draft ≈ 0.4 %/K of
outdoor cooling, giving ~23 % more flow at −18 °C than at +24 °C. Riser ΔT moves
oppositely (116 K at −18 °C → 142 K at +24 °C, building inlet), and the plate temperature
barely responds (± ~10 K over the whole range, radiation-dominated). If the inlet air
itself is cold, wall/gas temperatures shift down roughly with the inlet temperature while
flow changes little (the extra buoyancy in the riser column is partly offset by a denser
downcomer column).

### 4.2 Wind (0 → 11 m/s, outdoor 2 °C) · confidence: low-medium

Wind acts mainly through the static pressure it imposes on the chimney discharge,
Δp = −Cp·½ρU². The stack-top Cp is unknown (termination geometry not specified), so both
signs were bounded with |Cp| = 0.3 (ASHRAE-Handbook-type range for roof-level openings):

| Wind | m, Cp = −0.3 (suction, favorable) | m, Cp = +0.3 (blockage, adverse) |
|---|---|---|
| 0 m/s | 0.564 | 0.564 |
| 5 m/s | 0.583 (+3 %) | 0.545 (−3 %) |
| 11 m/s | 0.655 (+16 %) | 0.472 (−16 %) |

Even the adverse bound at 11 m/s only raises the plate ~10 K (to 433 °C) — the system
compensates with a larger ΔT (152 K). A well-designed stack termination normally sees
suction, so wind should mildly *assist* heat removal; the adverse case is the design
check. Wind-enhanced convection from the uninsulated downcomer/horizontal runs was
neglected (second-order). This is the least certain part of the analysis.

---

## 5. Verdict summary

1. **Mass flow** 0.56 kg/s (34 kg/min) baseline — medium confidence (± 15 %).
2. **Riser ΔT** 128 K — medium (± 15 %, anti-correlated with flow; m·ΔT known to ± 5 %).
3. **Riser front-face wall** 215 °C and **plate** 423 °C — medium / medium-high (± 25 / ± 35 K).
4. **Radiation carries 86 %** of the heat to the risers — high confidence (± 0.05).
5. **Accident case levels off at ≈ 353 °C** plate temperature at ~85 h, far below vessel
   steel limits — verdict high confidence; peak value ± 35 K.
6. **Weather**: −18 °C outdoor gives ~23 % more flow than +24 °C; wind changes flow ± 16 %
   at 11 m/s depending on stack-top aerodynamics; plate temperature is robust (± 10 K)
   throughout — the passive design margin is insensitive to weather.

**Most uncertain assumption overall:** the loop form-loss coefficient set (§1.1-8); for
the wind case, the stack-top pressure coefficient.

---

## 6. Files

| File | Contents |
|---|---|
| `rccs_model.py` | coupled steady/parametric solver (radiosity, convection, hydraulics) |
| `viewfactors.py` / `viewfactors.json` | Monte-Carlo view factors of the cavity cross-section |
| `airprops.py` | air property functions (cited fits) |
| `run_cases.py` / `run_cases.log` | all case runs, sensitivity studies, transient integration |
| `results.json` | machine-readable results (profiles, characteristic curve, sweeps) |
| `hand_checks.py` | independent order-of-magnitude verification |
| `make_plots.py`, `fig1…fig5*.png` | figures |

Reproduce: `python3 run_cases.py && python3 make_plots.py` (≈ 10 min).

## 7. Sensitivity study (Case 1)

| Perturbation | m (kg/s) | ΔT (K) | plate (°C) | riser front (°C) |
|---|---|---|---|---|
| baseline | 0.564 | 128 | 423 | 215 |
| riser ε 0.70 / 0.90 | 0.564 / 0.565 | 128 / 128 | 427 / 420 | 212 / 219 |
| plate ε 0.70 / 0.90 | 0.564 / 0.565 | 128 / 128 | **436 / 409** | 215 / 216 |
| form losses × 0.5 / × 1.5 | **0.623 / 0.521** | **116 / 138** | 418 / 427 | 202 / 227 |
| chimney heat loss × 2 | 0.562 | 128 | 423 | 216 |
| downcomer inlet at 1.5 / 8 m | 0.572 / 0.552 | 126 / 131 | 422 / 424 | 214 / 218 |

Flow is a weak (≈ −⅓-power) function of resistance; temperatures are buffered by the T⁴
radiation. This is why the headline plate/verdict numbers carry higher confidence than the
flow itself.

## References

- Churchill, S.W. & Chu, H.H.S. (1975), *Int. J. Heat Mass Transfer* **18**:1323 — natural convection, vertical surfaces.
- Gnielinski, V. (1976), *Int. Chem. Eng.* **16**:359 — turbulent duct convection.
- Petukhov, B.S. (1970), *Adv. Heat Transfer* **6** — smooth-tube friction factor.
- Idelchik, I.E., *Handbook of Hydraulic Resistance*, 3rd ed. — form-loss coefficients (order-of-magnitude use).
- Incropera, DeWitt, Bergman, Lavine, *Fundamentals of Heat and Mass Transfer*, 6th ed. — air properties (Table A.4), emissivities (Table A.11), enclosure radiation (ch. 13).
- Kays, W.M. & Crawford, M.E., *Convective Heat and Mass Transfer*, 3rd ed. — property-ratio correction.
- White, F.M., *Viscous Fluid Flow*, 2nd ed. — Sutherland-law property fits.
- ASME B&PV Code Section III (general service-level temperature limits for vessel steels, cited as typical engineering values).
- ASHRAE Handbook — Fundamentals, ch. 24 (wind pressure coefficients on buildings, order-of-magnitude use).
