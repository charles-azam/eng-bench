# Calculation Note — Passive Reactor Cavity Cooling System (½-scale, air-cooled)

**Scope.** Predict, from first principles, the natural-circulation performance of the ½-axial-scale
air-cooled RCCS test facility described in `inputs/`: mass flow, air temperature rise, riser and
heated-wall (mock-vessel) temperatures, the radiation/convection split, the accident (decay-heat)
peak temperatures and stability, and sensitivity to outdoor weather.

**Statement on data provenance.** *Every number in this note was derived from physics and the
geometry, materials, and boundary conditions given in `inputs/`. No published test data, report, or
pre-made model of this facility was consulted. Empirical correlations are drawn only from general
heat-transfer/fluid-mechanics literature and are cited where used.*

Working files (all in `output/`): `rccs_model.py` (coupled steady-state solver), `rccs_cases.py`
(decay transient, weather, per-face fin model), `rccs_sensitivity.py` (sensitivities + `rccs_results.png`).

---

## 1. Physical model

The loop is a closed buoyancy circuit with an open air path: cool air descends the downcomer, enters
the inlet plenum, rises through the 12 heated riser ducts (gaining heat), passes the outlet plenum,
and discharges up the chimneys. Heat reaches the risers from the electrically heated plate (mock RPV)
across an air-filled cavity, almost entirely by **thermal radiation** plus a minority by cavity
natural convection.

Four coupled sub-models are solved simultaneously to a self-consistent steady state:

| # | Physics | Method / correlation | Cited source |
|---|---------|----------------------|--------------|
| A | Buoyancy loop momentum balance → **ṁ** | ΔP_buoyancy(ρ_cold − ρ_hot over stack height) = Σ friction + form losses | Standard natural-draft balance; Darcy–Weisbach; Haaland friction factor (Haaland 1983); form-loss K's from Idelchik/Crane TP-410 |
| B | Air energy balance → **ΔT_air** | ΔT = Q/(ṁ·c_p) | 1st law |
| C | Internal duct convection → **riser wall T** | Nu = Gnielinski (turbulent), Nu=4.36 (laminar UHF) | Gnielinski (1976); Incropera *Fund. Heat & Mass Transfer* |
| D | Cavity radiation + natural convection → **plate T**, **rad/conv split** | Gray parallel-surface exchange with reradiating adiabatic side walls; vertical-enclosure Nu | Radiation: Modest / Incropera net-exchange; convection: MacGregor & Emery (1969) vertical cavity |

Air properties (ρ, c_p, μ, k, Pr) are evaluated with **CoolProp** (real-air, 1 atm) at the relevant
mean temperature; β = 1/T (ideal gas). A perimeter **fin conduction model** (thin 4.78 mm steel,
k≈50 W/m·K) resolves the front-face wall temperature from the perimeter-mean, because heat enters the
narrow 2-in front face but most internal convective area is the 10-in side faces.

**Geometry used (derived from `inputs/01`):** per-duct flow area 0.0101 m², hydraulic diameter
D_h = 0.0707 m, 12 ducts → total flow area 0.121 m²; internal convective area 47.4 m²; heated riser
length 6.91 m; heated-plate area 8.82 m² (scaling-line value; as-built ~10.18 m² — see §7); cavity
gap 0.707 m; effective stack height 19.6 m; chimney flow area 0.585 m².

**Heat delivered to the cavity.** Case 1 states 82 kWe electric input "corresponds to the scaled
1.5 MWt peak duty = 56.07 kWt." I take **Q_cavity ≈ 56 kW** as the heat actually crossing to the
risers, i.e. ~26 kW (≈32 %) is parasitic loss through the plate backing/insulated structure. This
split is the single most uncertain input (see §7); results are reported as a function of it.

---

## 2. Results — Case 1 baseline / accident-peak duty (Q_cavity = 56 kW; inlet air 20 °C, outdoor +2 °C)

| Quantity | Predicted | Where measured (per `inputs/03`) | Confidence |
|---|---|---|---|
| **System mass flow rate** | **0.55 kg/s = 33 kg/min** | inlet downcomer, whole loop | Moderate (±25 %) |
| **Riser air temperature rise ΔT** | **≈ 100 K** (T_in 20 °C → **T_out ≈ 121 °C**) | outlet − inlet gas TC | Moderate (±25 %, tracks ṁ) |
| **Riser wall T — front face, z = 3500 mm** | **≈ 170 °C** (perim. mean 138 °C; side 131 °C; rear 119 °C) | Riser 7 mid-plane, hot face | Moderate |
| **Heated-plate (mock-vessel) front T** | **≈ 375 °C** | plate front face | Good (±20–30 °C) |
| **Radiative fraction of heat removal** | **≈ 0.91** (radiation), ~0.09 cavity convection | Riser 7 four-face flux sensors | High (0.88–0.92) |
| Per-face radiative incidence (approx.) | front ~55 %, sides ~35 %, rear ~10 % | four-face sensors | Low–moderate |

**Diagnostics:** internal flow Re ≈ 15 500 (turbulent), riser air velocity ≈ 4.4 m/s, internal
h ≈ 18 W/m²·K; cavity Ra_L ≈ 6×10⁸, cavity h ≈ 2.3 W/m²·K; driving draft ≈ 50 Pa, balanced
predominantly by riser friction + entrance/exit form losses (the small-D_h ducts dominate the loop
resistance; chimney and downcomer losses are only a few Pa each).

### Normal-operation duty (Q_cavity = 26.16 kW), same ambient
mass flow **0.45 kg/s (27 kg/min)**, ΔT ≈ 58 K (T_out ≈ 78 °C), riser wall ≈ 86 °C, plate ≈ 262 °C,
radiative fraction ≈ 0.86.

---

## 3. Radiation vs. convection split

Across the cavity the hot plate transfers heat to the risers **~91 % by radiation, ~9 % by natural
convection** at the 56 kW duty (86 %/14 % at the lower 26 kW duty — radiation grows in share as plate
temperature rises, since q_rad ∝ T⁴). This is what the co-located matte-black (total) and reflective
(convection-only) heat-flux sensors on Riser 7 measure; their difference is the radiative flux.

- Radiation modeled as gray-surface exchange between plate (ε = 0.785, measured) and the riser plane
  (ε_r assumed 0.85 for oxidized steel — not reported in the source), with the adiabatic N/S/W cavity
  walls treated as reradiating. Net Q_rad = σA(T_p⁴ − T_r⁴)/(1/ε_p + 1/ε_r − 1).
- Cavity convection from MacGregor–Emery vertical-enclosure correlation (gap 0.707 m, H/L ≈ 9.5).

The radiative fraction is **robust to assumptions** (0.88–0.92 across ε_r = 0.6–0.9 and ε_p = 0.7–0.9),
so this is a high-confidence conclusion. The per-face breakdown (front dominant, rear smallest) is an
approximate geometric/solid-angle allocation and is the least certain sub-result.

---

## 4. Accident decay-heat transient (Case 2)

The supplied 10th-order polynomial (C₀…C₉, C₁₀ missing) peaks near 87 kW and turns negative after
~110 h, so it does **not** reproduce the stated shape; per the task's explicit alternative I imposed
the **normalized decay-heat curve: 26.16 kW → 56.07 kW peak at t = 84.85 h, then declining.**

**Time-scale check.** Lumped thermal capacitance of plate + risers C_th ≈ 1.8 MJ/K; effective passive
conductance dQ/dT_plate ≈ 250–350 W/K ⇒ thermal time constant τ ≈ 1.5–2 h ≪ the ~85 h ramp. The
system is therefore **quasi-steady**: at every instant the plate sits near its steady-state
equilibrium for the current power. A direct 1-minute-step lumped integration confirms this — plate
temperature tracks the quasi-steady curve and peaks at **≈ 375 °C at t ≈ 85 h**, then declines.

| Accident-peak quantity | Value |
|---|---|
| Peak plate (vessel) temperature | **≈ 375 °C** |
| Peak riser wall (front face) | ≈ 170 °C |
| Peak mass flow | ≈ 0.55 kg/s (33 kg/min) |
| Peak air ΔT | ≈ 100 K |

**Does it level off or run away? → It LEVELS OFF (self-limiting, stable).** The passive removal
capacity rises **monotonically and steeply** with plate temperature (radiation ∝ T⁴, and buoyant
mass flow also grows with the temperature rise), so for any bounded power there is a single stable
equilibrium plate temperature. The computed removal-vs-temperature curve (see `rccs_results.png`,
left panel) crosses the 56 kW accident duty at ≈ 375 °C with a finite positive slope — a stable fixed
point, not a runaway. Even at double the peak duty (≈112 kW) the plate would settle near ~507 °C.

**Safe-limit assessment.** The mock vessel is SAE 1020 / structural steel. A conservative structural
integrity limit is ~500 °C (steel retains substantial strength well below the ~600 °C range where
low-carbon steel degrades sharply). The predicted peak of ~375 °C sits **~125 °C below that limit**,
so **the vessel stays safely below the limit with margin**, and the passive system is self-stabilizing.
Confidence: **good** on the qualitative conclusion (level-off is a structural property of the T⁴
radiation law and is insensitive to modeling choices); moderate on the exact peak value (see §7).

---

## 5. Weather sensitivity (Case 3)

Same 56 kW duty, outdoor/inlet air varied −18 °C → +24 °C, wind 0 → 11 m/s.

| Outdoor/inlet T | ṁ (kg/min) | air ΔT (K) | riser wall (°C) | plate (°C) | rad frac |
|---|---|---|---|---|---|
| −18 °C | 38.3 | 87 | 87 | 361 | 0.89 |
| 0 °C | 35.6 | 94 | 111 | 368 | 0.90 |
| +2 °C (baseline) | 35.3 | 95 | 113 | 368 | 0.90 |
| +20 °C | 32.9 | 101 | 138 | 376 | 0.91 |
| +24 °C | 32.4 | 103 | 143 | 377 | 0.92 |

**Air temperature.** Colder outdoor air is **denser → larger buoyant driving head → more mass flow**
(≈ +18 % from +24 °C to −18 °C) and **lower riser-wall temperatures** (colder coolant, higher flow).
The **plate/vessel temperature is only weakly sensitive** (~±8 °C over the whole range) because it is
set by radiative balance against the riser surface, which changes little; this is a reassuring result
for the accident case (cold-weather performance is if anything slightly better for the vessel).

**Wind.** Wind chiefly acts on the chimney discharge (and exposed intake). Its dynamic pressure
0.5ρV² reaches **≈ 78 Pa at 11 m/s**, comparable to the ~50 Pa stack draft, so strong steady wind
could perturb the flow by an appreciable fraction — favorable (across-the-top suction at the stack
cap) enhancing draft, unfavorable (pressurizing the discharge or the intake) reducing it. In practice
the effect is **direction-dependent and largely buffered** by the flow conditioner and open butterfly
dampers, and gusty/multidirectional wind tends to average out. Net expected effect on the vessel
temperature is **small (a few °C)**; the mass flow is the more wind-sensitive quantity. Confidence:
qualitative direction high; magnitude low (no site-specific pressure-coefficient data used).

---

## 6. Confidence summary and most-uncertain assumption

| Result | Confidence | Basis |
|---|---|---|
| Radiative fraction ≈ 0.9 | **High** | Robust across ε and power |
| Plate/vessel peak temp ≈ 375 °C; levels off; safe | **Good** | T⁴ law guarantees self-limiting; value moves ±20–30 °C with inputs |
| Mass flow 0.55 kg/s; air ΔT ~100 K | **Moderate (±25 %)** | Sensitive to loop form-loss coefficients (assumed from handbook K's) |
| Riser wall front-face ~170 °C | **Moderate** | Depends on internal-h correlation and fin conduction model |
| Weather trends | **High (direction), Moderate (magnitude)** | Physics-based; wind pressure coeff. unquantified |
| Per-face radiation split | **Low–moderate** | Approximate view-factor allocation |

**Most uncertain assumption:** the **fraction of the 82 kWe electric input that actually reaches the
risers** (parasitic-loss / delivered-power split). Assuming Q_cavity = 56 kW (32 % parasitic); if the
true delivered power were 62–72 kW, the plate would run ~393–419 °C and ΔT ~109–123 K (still self-
limiting and below the safe limit). A close second is the **riser surface emissivity** (not reported;
assumed 0.85), which shifts the plate temperature by ±~20 °C, and the **loop form-loss coefficients**,
which set the mass-flow magnitude.

---

## 7. Key assumptions (consolidated)

1. **Q_cavity = 56 kW** delivered to risers at baseline/accident-peak; 26 kW parasitic (most uncertain).
2. Riser emissivity **ε_r = 0.85** (oxidized steel; not reported). Plate ε_p = 0.785 (measured).
3. Steel k ≈ 50 W/m·K, thin-wall near-isothermal-perimeter with fin correction for the front face.
4. Effective stack height 19.6 m; cold leg at inlet-air density; hot leg = riser-mean + chimney-outlet density.
5. Form-loss coefficients (entrances, exits, elbows, plena) from Idelchik/Crane handbook estimates.
6. Air treated as real gas at 1 atm (CoolProp); properties at local mean temperature.
7. Heated-plate area 8.82 m² (scaling-line); using the as-built 10.18 m² would lower fluxes ~13 % and
   plate temperature by ~15–20 °C — a known ~12 % reporting inconsistency in the source geometry.
8. Quasi-steady transient (justified: τ ≈ 1.5–2 h ≪ 85 h ramp).

*All correlations above are general-literature (Gnielinski, MacGregor–Emery, Haaland, Idelchik/Crane,
gray-surface radiation exchange); no facility-specific test report or model was used.*
