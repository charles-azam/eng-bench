# Calculation Note — Passive Reactor Cavity Cooling System (½-scale air-cooled test facility)

**Prepared:** 2026-07-03
**Scope:** Predict the natural-circulation performance of the ½-axial-scale air-cooled RCCS
test facility described in `inputs/` for the operating cases in
`inputs/04_boundary_conditions_and_test_cases.md`.

**Provenance statement.** Every number in this note was derived from first-principles
physics (mass, momentum and energy balances; grey-body radiation exchange; cited standard
correlations) and the geometry, material properties and boundary conditions given in
`inputs/`. No published test report, measured result, or pre-made model of this facility
was consulted, searched for, or used. The only external material used was standard
textbook/handbook data (air properties, emissivity of oxidized steel, friction and
heat-transfer correlations), cited where used.

All working files are in this directory: `rccs_model.py` (steady-state model),
`run_cases.py` (case runner, transient, sensitivities), `results/` (JSON, CSV, figures).

---

## 1. System and modelling approach

Heat path: a 40-zone electric heater array drives a 25.4-mm SAE-1020 steel plate (the mock
reactor vessel, area 10.18 m², ε = 0.785 measured). The plate radiates and convects across
a 0.707-m air cavity to 12 vertical rectangular steel riser ducts (10 in × 2 in × 0.188 in
wall, heated over the 6.7-m cavity height). Air inside the risers heats up, becomes buoyant
and drives a natural-circulation loop: building air → 24-in downcomer → inlet plenum →
risers → outlet plenum → two insulated 24-in chimney stacks discharging outdoors at 19.6 m.

The model (`rccs_model.py`) is a coupled 1-D thermal–hydraulic network:

**Cavity heat transfer** — the heated height is split into 10 axial segments (matching the
heater zones). Each segment contains a five-surface grey-diffuse radiosity enclosure
(heated plate; riser front faces; riser side faces in the inter-duct gaps; riser rear
faces; insulated wall behind the risers). View factors come from 2-D crossed-strings
evaluations on the periodic 110-mm unit cell (duct front 50.8 mm, gap 59.3 mm, duct depth
254 mm), with reciprocity and row sums enforced. Because the cavity depth (707 mm) is much
larger than the duct pitch (110 mm), radiation arriving at the riser plane is taken as
uniformly distributed over it.

**Cavity natural convection** — plate → cavity air → duct faces / walls, using the
Churchill–Chu vertical-plate correlation (Incropera & DeWitt, *Fundamentals of Heat and
Mass Transfer*, 6th ed., Eq. 9.26) with the full cavity height as the characteristic
length; a single well-mixed cavity-air temperature is solved from the convective energy
balance. Convection on the shielded side/rear faces is derated by an assumed factor 0.7.

**Duct wall** — each segment carries three wall nodes (front, sides, rear) connected by
perimeter conduction through the 4.78-mm steel (fin links, k = 50 W/m·K), plus a grey
radiosity exchange between the duct's internal faces (the hot front face radiates to the
cool rear face inside the duct, flattening the perimeter temperature profile).

**In-duct forced convection** — Gnielinski's correlation (V. Gnielinski, *Int. Chem. Eng.*
16 (1976) 359) on the duct hydraulic diameter (Dh = 70.6 mm), with a thermal-entrance
enhancement of the form Nu(x)/Nu∞ = 1 + (x/Dh)^−0.9 (fitted to the turbulent entry-length
solutions in Kays, Crawford & Weigand, *Convective Heat and Mass Transfer*).

**Heater array and parasitics** — the heater surface is a separate node per segment: it
radiates to the plate back across the gap (two-surface grey exchange, ε_heater = 0.90
measured, ε_plate,back = 0.78) and loses heat backwards through the 2-in Duraboard to the
building (temperature-dependent k from the inputs). Losses through the 6-in SuperIsol
cavity walls are computed from the solved wall/cavity-air temperatures. An additional 5 %
of electric power is assumed lost through edges, frame and penetrations (assumption A6).

**Loop momentum balance** — the driving head is the closed-loop integral of ρg dz against
the outdoor-air column (ideal-gas densities at 101 325 Pa), including the gas temperature
profile in the risers, the outlet plenum, and the chimney (with a small computed heat loss
through the Enerwrap insulation). Friction uses the Churchill (1977) all-regime friction
factor with commercial/galvanized steel roughness (0.15 mm) plus form-loss coefficients
from Idelchik, *Handbook of Hydraulic Resistance* (entrance 0.5, flow conditioner 2.0,
elbow 0.3, duct inlet contraction 0.4, duct exit expansion 1.0, chimney port 0.5, five
open butterfly dampers 1.0 total, stack exit 1.0), plus the acceleration term. Wind enters
as a pressure at the stack discharge, Δp = −Cp·½ρU², with the pressure coefficient Cp an
assumption (see §6). The solver finds the mass flow at which buoyancy balances losses
(Brent's method); the whole-model energy audit closes to < 0.1 %.

**Air properties** — Incropera & DeWitt Table A.4, interpolated; ideal-gas density.

### Key assumptions (referenced throughout)

| # | Assumption | Value used | Basis / uncertainty |
|---|---|---|---|
| A1 | Riser duct & rear-wall emissivity (not reported in inputs) | ε_duct = 0.80, ε_wall = 0.85 | Oxidized structural steel ≈ 0.79 (Incropera Table A.11); varied 0.70–0.90 |
| A2 | Inlet air = building air at 20 °C (Case 1) | 20 °C | Stated in inputs; downcomer is indoors and uninsulated |
| A3 | Flow-conditioner + damper loss coefficients | K = 2.0, 1.0 | Idelchik typical values; varied 0.5–4.0 |
| A4 | Building neutral-pressure plane at the downcomer intake (z ≈ 3.5 m) | — | Varied 0.5–7 m; small effect |
| A5 | Cavity convection: well-mixed cavity air, Churchill–Chu h, 0.7 derating on shielded faces | — | Radiation dominates, so modest impact |
| A6 | Edge/frame/penetration parasitic loss | 5 % of P_elec | Engineering allowance; varied 2–10 % |
| A7 | Heated-plate area 10.18 m² (as-built) with uniform flux per zone | — | Inputs flag a 12 % reporting inconsistency vs 8.82 m² |
| A8 | Case-2 power shape imposed from the inputs' fallback description | 26.16 → 56.07 kW peak at 84.85 h, then ∝ t^−0.28 | The 10th-order polynomial as given (C10 missing) starts at 42 kW and diverges after ~110 h, so it was rejected; peak power and timing are as specified |
| A9 | Wind pressure coefficient at the stack discharge | Cp ∈ [−0.5, +0.2] | Vertical stack termination: suction typical; downwash possible |

---

## 2. Case 1 — Baseline steady state (82 kWe, outdoor +2 °C, inlet/building 20 °C, low wind)

Converged solution: buoyancy head 69 Pa balances loop losses; riser Reynolds number
≈ 15 000–16 000 (fully turbulent); whole-model energy audit closes to < 0.1 %.

| Quantity (at the measurement location) | Prediction | Range (assumption sweep) | Confidence |
|---|---|---|---|
| **System mass flow** (inlet downcomer, whole loop) | **0.56 kg/s = 34 kg/min** | 0.54 – 0.58 kg/s | Medium-high (±10 %) |
| **Riser gas ΔT** (outlet − inlet TC) | **120 K** (20 → 140 °C) | 100 – 125 K | Medium (±15 %) |
| **Riser 7 wall T, hot/front face, z = 3.5 m** | **210 °C** | 180 – 225 °C | Medium (±20 K) |
| Riser 7 side faces / rear face, z = 3.5 m | 160 °C / 158 °C | ±20 K | Medium |
| **Heated-plate front temperature** | **406 °C** mean (417 °C max, near top) | 370 – 420 °C | Medium (±25 K) |
| Cavity air temperature | 212 °C | ±25 K | Medium-low |
| Heater-array surface | ≈ 510 °C | ±40 K | Low-medium |
| **Heat to riser air** | **68 kW of 82 kWe** (parasitic ≈ 14 kW, 17 %) | 57 – 72 kW | Medium |
| **Radiative fraction of duct heat removal** | **0.89** | 0.85 – 0.91 | High |

**Radiation / convection split.** Of the 68 kW removed by the risers, ≈ 61 kW arrives as
thermal radiation from the plate (direct and via the re-radiating back wall) and ≈ 7 kW as
natural convection from the cavity air — radiative fraction **0.89**. Per face at the
Riser-7 mid-plane sensors (total flux / radiative share):

| Face | Total flux | Radiative | Convective | Radiative fraction |
|---|---|---|---|---|
| Hot/front (line-of-sight to plate) | 5.7 kW/m² | 5.7 kW/m² | ≈ 0 | ≈ 1.00 |
| Side (wide, in gap) | 1.0 kW/m² | 0.85 kW/m² | 0.14 kW/m² | 0.86 |
| Cold/rear | 0.85 kW/m² | 0.70 kW/m² | 0.14 kW/m² | 0.83 |

The front face runs essentially at the cavity-air temperature, so its gold-foil
(convection) sensor should read near zero; the shielded faces receive most of their heat
by multi-bounce radiation through the inter-duct gaps plus mild convection. About half of
the total duct heat absorption occurs on the side faces (large area), even though the
front-face *flux* is ~6× higher.

**Why the mass flow is so insensitive (±10 % across all hydraulic assumptions):** the loop
self-regulates — added resistance lowers flow, which raises the gas temperature and the
buoyancy head as compensation. ṁ ∝ (ρΔρ g H / R)^(1/3) at fixed power, so a factor-2 error
in a loss coefficient moves the flow only ~25 %, and the dominant losses (riser friction,
entrance/exit) are well characterized. This cube-root forgiveness is the fundamental
passive-safety feature of the design.

**Most uncertain assumption for this case: the parasitic-loss fraction.** My
physics-based estimate (heater backside conduction through the Duraboard ≈ 8.4 kW, edge
allowance ≈ 4 kW, insulated cavity walls ≈ 1.4 kW) gives 17 % loss. However, the inputs'
own scaling table maps 82 kWe to a 56.07-kW removal duty, implying the designers expected
≈ 32 % loss. A bounding run at 30 % total parasitic loss gives ṁ = 0.55 kg/s (barely
changed), ΔT = 103 K, plate 372 °C, front-face wall 183 °C, radiative fraction 0.88. The
mass flow and radiative fraction are robust to this; the gas ΔT and absolute temperatures
carry it as their dominant uncertainty — hence the asymmetric ranges above.

Axial profiles: `results/case1_profiles.png`. The plate is nearly isothermal (406 ± 11 °C)
because radiation to the T⁴-flattened duct bank dominates; wall and gas temperatures climb
roughly linearly with elevation.

---

## 3. Case 2 — Accident decay-heat transient

Power history per assumption A8: 26.16 kW normal load rising along the specified curve to
the 56.07-kW peak at 84.85 h, then declining. The loop is quasi-steady on this timescale
(plate thermal time constant ≈ 1 h ≪ 85-h ramp), so peak temperatures depend almost only
on the peak power — which is specified — not on the curve shape or the assumed thermal
masses (varying the heater-array thermal mass 200 → 800 kJ/K moved the peak plate
temperature 0.1 K).

| Quantity | Prediction | Confidence |
|---|---|---|
| Initial (26.16 kW) plate temperature | 219 °C | Medium |
| **Peak plate temperature** | **334 °C at t ≈ 85.1 h** (~0.3 h after the power peak) | Medium (±30 K) |
| Peak heater-array temperature | 433 °C | Low-medium |
| Peak riser front-face wall (z = 3.5 m) | 155 °C | Medium |
| Peak mass flow | 0.53 kg/s | Medium-high |
| Peak riser gas ΔT | 85 K | Medium |

**Verdict: the vessel temperature levels off — it does not run away.** The plate tracks
the decay power quasi-statically, peaks at **≈ 334 °C** essentially coincident with the
84.85-h power peak, and declines with the decay curve thereafter
(`results/case2_transient.png`, `case2_transient.csv`). Physically this is guaranteed
stable here: heat removal grows steeply with plate temperature (radiation ∝ T⁴ and the
natural-circulation flow also strengthens with load — the precomputed removal
characteristic rises from 2.8 kW at 67 °C to 94 kW at 467 °C), while the decay input is
bounded and falling. Against a 538 °C (1000 °F) accident limit typical of RPV steels
(ASME Level-C/D style criterion for SA-533/SA-508 vessels; the mock plate is SAE 1020),
the margin is **> 200 K** — the conclusion is insensitive to every assumption in this
note (even taking parasitic losses to zero raises the peak by only a few tens of K).
Confidence in the *verdict*: **high**.

---

## 4. Case 3 — Weather sensitivity (baseline power, outdoor −18 to +24 °C, wind 0–11 m/s)

Inlet air is building air, held at 20 °C (assumption A2); outdoor temperature acts on the
loop through the ambient-column density (draft) and chimney heat loss. Wind acts through
the stack-discharge pressure, Δp = −Cp·½ρU² (A9): a vertical stack termination in a cross
wind typically sees suction (Cp ≈ −0.5 … −0.25, aiding draft); Cp = +0.2 bounds an adverse
downwash case.

No wind:

| Outdoor T | ṁ [kg/s] | Riser ΔT [K] | Gas out [°C] | Plate mean [°C] | Front wall @3.5 m [°C] |
|---|---|---|---|---|---|
| −18 °C | 0.62 | 109 | 129 | 402 | 199 |
| −10 °C | 0.60 | 113 | 133 | 403 | 203 |
| 0 °C | 0.57 | 118 | 138 | 405 | 209 |
| +2 °C (baseline) | 0.56 | 120 | 140 | 406 | 210 |
| +10 °C | 0.54 | 124 | 144 | 407 | 215 |
| +24 °C | 0.51 | 132 | 152 | 410 | 223 |

Wind at outdoor +2 °C:

| Wind | Cp = −0.5 (suction) | Cp = −0.25 | Cp = +0.2 (downwash) |
|---|---|---|---|
| 5 m/s | 0.59 kg/s | 0.58 | 0.55 |
| 8 m/s | 0.64 kg/s | 0.60 | 0.53 |
| 11 m/s | 0.70 kg/s | 0.63 | 0.51 |

**Findings** (`results/case3_weather.png`): a 42 K colder outdoors strengthens the draft
by ≈ +10 % flow; the hottest ambient (+24 °C) costs ≈ −10 %. Strong wind spans roughly
−10 % to +25 % flow depending on the stack pressure coefficient. In every case the *heat
removed is unchanged* (it is set by the power input); the loop simply trades flow against
ΔT, and the **vessel temperature moves by only ≈ ±7 K across the entire weather
envelope** — weather affects how the system breathes, not whether it cools. Confidence:
medium-high for the ambient-temperature trend (pure hydrostatics), low-medium for the wind
magnitude (Cp is a geometry-specific assumption; the sign of the suction benefit is
reliable, its size is not).

---

## 5. Case 4 (optional) — Axial power-shape variations

Same integral power, redistributed per the given zone peaking factors:

| Profile | ṁ [kg/s] | Riser ΔT [K] | Plate max [°C] (location) |
|---|---|---|---|
| Uniform (baseline) | 0.563 | 120 | 417 (top) |
| Mid-plane cosine | 0.563 | 120 | **455** (zone 7, z ≈ 4.4 m — shifted above the power peak by the rising gas temperature) |
| Bottom-peaked | 0.566 | 119 | **467** (zone 3, z ≈ 1.7 m) |

Integral quantities (flow, ΔT, split) are essentially shape-independent; only the local
plate peak moves, rising ≈ 40–60 K where the local flux peaks at ~1.3–1.4× average.
Confidence: medium.

---

## 6. Confidence summary and dominant uncertainties

| # | Deliverable | Value (Case 1) | Confidence |
|---|---|---|---|
| 1 | Mass flow | 0.56 kg/s (34 kg/min) | **Medium-high** — self-regulating loop, ±10 % |
| 2 | Riser ΔT | 120 K (100–125 K) | **Medium** — carries the parasitic-loss uncertainty |
| 3 | Riser front wall @ z=3.5 m / plate front | 210 °C / 406 °C | **Medium** — emissivities + parasitic, ±20–25 K |
| 4 | Radiative fraction | 0.89 (front face ≈ 1.0) | **High** — a T⁴ vs h·ΔT ratio, robust |
| 5 | Accident peak / verdict | 334 °C, levels off, > 200 K margin | **Medium on the number, high on the verdict** |
| 6 | Weather | flow ±10 % (T), −10…+25 % (wind); vessel ±7 K | **Medium-high** (T), **low-medium** (wind size) |

Ranked uncertainties:
1. **Parasitic-loss fraction (A6/A8)** — 17 % from physics vs 32 % implied by the design
   duty mapping; dominates ΔT and absolute temperatures. It is the assumption I would
   test first against the facility's power-balance data.
2. **Riser/wall emissivities (A1)** — not reported; ±0.1 moves the plate ± ~10 K and the
   radiative fraction ±0.005.
3. **Wind pressure coefficient (A9)** — sets the size (not sign) of the wind effect.
4. **Cavity-convection model (A5)** — well-mixed air + flat-plate correlations; only ~11 %
   of the heat rides on it, so even ±50 % error moves the split by only ±0.04.
5. **Form-loss coefficients (A3)** — cube-root-suppressed by the loop self-regulation.

---

## 7. File index

| File | Contents |
|---|---|
| `rccs_model.py` | Steady-state coupled model (radiation enclosure, cavity convection, duct conduction, loop hydraulics) |
| `run_cases.py` | All cases, sensitivity sweeps, transient integrator, figure generation |
| `results/results.json` | Machine-readable results for every run in this note |
| `results/case1_profiles.png` | Baseline axial temperature profiles |
| `results/case2_transient.png` / `.csv` | Accident transient histories |
| `results/case3_weather.png` | Weather-sensitivity curves |

**Correlations cited:** Gnielinski, *Int. Chem. Eng.* 16 (1976) 359 (duct convection);
Churchill & Chu via Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, 6th ed.,
Eq. 9.26 (natural convection) and Table A.4 (air properties) and Table A.11 (oxidized-steel
emissivity); Churchill, *Chem. Eng.* 84 (1977) 91 (friction factor); Idelchik, *Handbook of
Hydraulic Resistance* (form losses); Kays, Crawford & Weigand, *Convective Heat and Mass
Transfer* (turbulent entry-length behaviour).

**Provenance (restated):** all predictions above were computed from the `inputs/` files and
first-principles models with the cited textbook correlations; no measured data, published
report, or existing model of this facility was consulted.
