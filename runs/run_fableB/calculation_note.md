# Calculation Note — Passive Reactor Cavity Cooling System (½-scale air-cooled test facility)

**Doc:** RCCS-CN-001 · **Rev:** A · **Method:** first-principles Python model (`model.py`), no CFD, no facility test data used
**Cases:** (1) baseline steady state 82 kWe · (2) accident decay-heat transient · (3) weather sensitivity

---

## 1. Purpose and system

Predict the passive performance of a ½-axial-scale air-cooled RCCS test facility: a 6.7 m tall
electrically heated steel plate (mock reactor vessel, 82 kWe) radiates and convects across a
0.707 m air cavity to a bank of **12 vertical rectangular steel riser ducts**
(10 in × 2 in × 0.188 in wall, narrow face toward the plate). Air inside the risers heats up,
becomes buoyant, and drives a natural-circulation loop: building air → 24-in downcomer → inlet
plenum → risers (7.49 m) → outlet plenum → two insulated 24-in chimney stacks discharging
outdoors ≈ 26 m above the riser inlets. No pumps.

Quantities predicted at the facility's instrument locations (per `inputs/03_instrumentation_map.md`):
total loop mass flow (downcomer meter), riser gas ΔT (inlet/outlet TCs), riser wall temperature
(Riser 7, z = 3500 mm, hot face), heated-plate front temperature, radiative/convective split
(four-face flux sensors at z = 3500 mm), accident peak temperatures, weather response.

## 2. Input data and derived geometry

| Item | Value | Source / derivation |
|---|---|---|
| Electric power, Case 1 | 82 kWe, uniform axial | `04_boundary…` |
| Riser internal section | 244.5 × 41.25 mm → A = 0.01008 m², D_h = 0.0706 m | derived from 10×2×0.188 in |
| Riser length / heated span | 7.49 m / 6.70 m in-cavity | `01_facility…` |
| Duct pitch / gap between ducts | 110.1 mm / 59.3 mm | 52 in ÷ 12 |
| Plate area (radiating envelope) | 6.70 × 1.321 m = 8.85 m² | matches 8.82 m² scaling value |
| Plate–riser spacing | 0.7066 m | baseline |
| Plate emissivity ε_p | 0.785 | measured (0.78–0.79) |
| Riser emissivity ε_r | **0.80 (assumed)** | not reported; oxidized steel 0.7–0.9 (Incropera Table A.11) |
| Downcomer / chimney | Ø0.610 m; L_dc = 4.69 m; L_ch,eq = 32.9 m per stack ×2 | `01_facility…` |
| Chimney discharge elevation | 26 m above riser inlet | facility total height 26 m |
| Ambient (Case 1) | inlet (building) 20 °C, outdoor 2 °C, calm | `04_boundary…` |
| Air properties | ρ = P/RT; μ, k, c_p from Incropera & DeWitt Table A.4 (1 atm) | cited |

## 3. Model

Three coupled sub-models, solved in `model.py` (pure Python, bisection/relaxation solvers).

### 3.1 Loop hydraulics + energy (mass flow, ΔT)

Momentum around the loop, steady incompressible-per-segment:

  Δp_buoyancy = g·[ρ_amb·H_exit − ρ̄_riser·H_riser − ρ_out·H_plenum − ρ_chimney·H_chimney] = Σ Δp_losses

- The balancing cold column is **outdoor air (2 °C)** over the full 26 m stack height; the
  building column (20 °C) up to the downcomer inlet cancels against the descending downcomer at
  the same temperature. Neutral building pressure plane assumed at riser-inlet elevation.
- Riser column density integrated over a linear gas-temperature rise; chimney gas taken as
  T_out − 12 K (lumped loss: uninsulated horizontal run + 3-in Enerwrap vertical stack).
- Losses: friction (Haaland smooth-tube), riser entrance K = 0.5, riser exit into plenum K = 1.0,
  flow acceleration G²(1/ρ_out − 1/ρ_in), downcomer flow-conditioner K = 2.0 + entrance 0.5 +
  elbow 0.3 + plenum expansion 1.0, chimney entrance 0.5 + open butterfly dampers 0.9 + exit 1.0
  (Idelchik, *Handbook of Hydraulic Resistance*). Riser friction and riser exit dominate (≈75 %
  of total loss).
- Energy: Q_air = ṁ·c̄_p·ΔT with Q_air = (1 − f_loss)·P_electric.

**Parasitic loss fraction f_loss = 0.30 (assumed)** — see §6; this is the most uncertain input.
Two independent facility statements support it: (i) Case 1 declares 82 kWe "corresponds to" the
scaled 1.5 MWt accident duty of 56.07 kW (ratio 0.68), and (ii) the accident polynomial gives
42 kWe at t = 0 and 82.8 kWe at its peak while the scaled thermal duty is 26.16 → 56.07 kW —
the same net/gross ratio 0.62–0.68 across the whole curve. A bottom-up insulation estimate
(2-in Duraboard + assumed 3-in SuperIsol behind heaters ≈ 3–10 kW; 6-in SuperIsol cavity walls
≈ 2–3 kW; edges/frame/plena ≈ 2–5 kW) gives 10–25 %, consistent at its upper end.

### 3.2 Cavity radiation + convection (plate and gas temperatures, rad/conv split)

Gray-diffuse network per axial segment (20 segments; air is non-participating over 0.7 m):

- Plate ↔ riser-bank plane, equal areas, view factor F₁₂ = 0.554 (aligned parallel rectangles,
  X = 1.87, Y = 9.48, Incropera Table 13.2). Insulated cavity walls treated as re-radiating →
  effective factor F̂ = (1 + F₁₂)/2 = 0.777.
- The bank plane is a composite surface: duct fronts (46 % of width, ε = 0.80) and gap mouths
  (54 %) which act as deep slot cavities (depth/width = 4.3) with apparent emissivity 0.97 →
  bank effective emissivity 0.89; overall exchange factor **𝔉 = 0.595**:
  q_rad = 𝔉·σ·(T_p⁴ − T_bank⁴).
- Convection: Churchill–Chu (1975) turbulent vertical-plate correlation (Ra_H ≈ 10¹¹–10¹²) from
  plate to a well-mixed cavity-gas node, and from the gas to all riser external faces (sides in
  the confined gaps derated ×0.7). Plate segments solve
  𝔉σ(T_p⁴ − T_bank⁴) + h_p(T_p − T_g) = q″_net = Q_air/A_plate (uniform heating, thin plate,
  weak axial conduction).

### 3.3 Riser duct wall (hot-face temperature at z = 3500 mm)

1-D circumferential conduction around the half-perimeter (48 nodes, symmetry), with per-node:

- external radiation: front face exchanges directly with the plate
  (R = (1/ε_p − 1) + 1/F̂ + (1/ε_r − 1)); side faces absorb the radiation streaming into the
  inter-duct gaps, distributed along depth by the 2-D parallel-strip penetration function
  F(x) = √(1+(x/w)²) − x/w (crossed strings); ~11 % leaks to the back region and re-radiates to
  rear faces via the adiabatic west wall;
- external convection from the cavity gas (Churchill–Chu, sides ×0.7);
- internal forced convection h = 20.1 W/m²K (Gnielinski, Re = 18 700, fully developed at
  z/D_h ≈ 50) to riser air at T_a(z = 3.5 m);
- internal radiation between duct inner faces (mean-radiant closure).

Buoyancy-aided mixed-convection impairment ("laminarization") was checked with Jackson's
buoyancy parameter Bo ≈ 0.02 « 1 → negligible at these conditions.

## 4. Results — Case 1, baseline steady state (82 kWe, inlet 20 °C, outdoor 2 °C, calm)

Net heat to air: **Q_air = 57.4 kW** (f_loss = 0.30). Driving head ≈ 78 Pa at balance.

| Quantity (measurement location) | Prediction | Confidence |
|---|---|---|
| **System mass flow** (downcomer meter) | **0.65 kg/s = 39 kg/min** | medium (±15 %) |
| **Riser gas ΔT** (outlet − inlet TC) | **88 °C** (20 → 108 °C) | medium (±20 %) |
| **Riser wall, Riser 7, z = 3500 mm, hot face** | **155 °C** (side faces 121 °C, rear 107 °C; local air 66 °C) | low–medium (±30 °C) |
| **Heated plate, front** | **386 °C** at z = 3.5 m (axial 375–395 °C; ≈ flat because T_p⁴ ≫ T_bank⁴) | medium (±40 °C) |
| **Radiative fraction of heat removal** | **0.83** (radiation 47.9 kW, cavity convection 9.5 kW) | medium (±0.07) |
| Cavity gas temperature (mixed) | 180 °C | low (stratification neglected) |
| Riser Reynolds number | 18 700 (turbulent) | — |

Per-face fluxes at the z = 3500 mm sensor station (matte-minus-gold decomposition):

| Face | Radiative (W/m²) | Convective (W/m²) | Rad share |
|---|---|---|---|
| Front (line-of-sight to plate) | 4 850 | ≈ +100 | ~98 % |
| Side (wide, mid-depth of gap) | 310 | 170 | ~65 % |
| Rear (faces insulated wall) | 480 | 300 | ~62 % |

The front face is almost purely radiative; the sides/rear pick up comparable radiation and gas
convection. Overall split ≈ 83 % radiation / 17 % convection.

**Sensitivity to the loss fraction** (dominant uncertainty): f_loss 0.15 → 0.35 gives
ṁ = 0.67 → 0.64 kg/s, ΔT = 103 → 83 °C, plate 422 → 372 °C, wall 180 → 147 °C, rad fraction
0.86 → 0.83. Riser emissivity 0.70 → 0.90 moves the plate only 391 → 381 °C (the deep-slot
cavity effect makes the bank nearly black regardless).

## 5. Results — Case 2, accident decay-heat transient

Electric power from the given 10th-order polynomial (×90): 42 kWe at t = 0, rising to
≈ 83–88 kWe near the stated peak (the digitized fit flat-tops over t ≈ 60–85 h), then collapsing.
Quasi-steady treatment is valid: the lumped plate time constant is
C_plate/(h_rad·A) ≈ 0.7 h ≪ 85 h.

| t (h) | P_elec (kW) | Q_air (kW) | ṁ (kg/s) | ΔT (K) | Plate (°C) | Riser wall (°C) |
|---|---|---|---|---|---|---|
| 0 | 42.0 | 29.4 | 0.57 | 52 | 277 | 97 |
| 24 | 63.5 | 44.5 | 0.62 | 71 | 341 | 129 |
| 48 | 80.7 | 56.5 | 0.65 | 87 | 383 | 154 |
| **72–85 (peak)** | **83–88** | **58–61** | **0.65–0.66** | **89–93** | **394–398** | **157–163** |
| 96 | 65.9 | 46.1 | 0.62 | 74 | 347 | 132 |

**Peak plate (mock-vessel) temperature ≈ 398 °C**, peak flow ≈ 0.66 kg/s.
**The temperature levels off — it does not run away.** Two negative feedbacks guarantee this:
radiative rejection grows as T_p⁴, and the loop flow itself strengthens with heat load
(ṁ ∝ Q^~1/3), so removal capacity always catches the slowly-varying decay input. Against the
ASME low-alloy vessel-steel accident limit of 538 °C (Level D basis used in HTGR licensing),
margin ≈ 140 °C: **bounded = yes**, even at the low-loss bound (f_loss = 0.15 → peak ≈ 425 °C).
Thermal inertia of the plate and structures (ignored) only lowers the true peak further —
the quasi-steady value is conservative.

## 6. Results — Case 3, weather sensitivity (fixed 82 kWe)

Stack physics: ṁ ≈ [Δρ·g·H / R_loop]^½, with the cold column at outdoor density and the inlet
fixed at 20 °C building air. Wind adds suction at the stack tip, modeled as
Δp = C_w·½ρU² with C_w = 0.4 (ASHRAE stack-effect/wind-pressure practice; sign is assisting
for a vertical open discharge).

| Outdoor T | Wind 0 | Wind 5 m/s | Wind 11 m/s |
|---|---|---|---|
| −18 °C | 0.74 kg/s (+14 %) | 0.77 (+18 %) | 0.86 (+32 %) |
| +2 °C (base) | 0.65 (—) | 0.67 (+4 %) | 0.76 (+17 %) |
| +24 °C | 0.56 (−14 %) | 0.58 (−10 %) | 0.67 (+3 %) |

- **Colder ambient → stronger flow** (≈ −0.7 %/°C of outdoor warming); ΔT moves inversely
  (Q fixed): 77 K at −18 °C vs 102 K at +24 °C.
- **Wind assists** on average (+17 % at 11 m/s at baseline); gusts would appear as flow
  oscillations, and an adverse cap geometry could locally reverse the sign — C_w is uncertain
  (0–0.8).
- Plate temperature barely moves (±5–10 K over the whole map) because removal is
  radiation-dominated: **weather changes the flow split, not the safety margin.** Worst case
  for flow is a hot, still summer day; the system remains bounded there.

## 7. Assumptions, uncertainty, confidence

| # | Assumption | Basis | Impact |
|---|---|---|---|
| 1 | **Parasitic loss fraction f_loss = 0.30** | facility's own 82 kWe ↔ 56 kW duty mapping + decay-curve scaling; insulation estimate 10–25 % | **Most uncertain.** Directly scales ΔT and all temperatures (§4 sensitivity) |
| 2 | Riser emissivity 0.80 | oxidized steel, not reported | weak (slot cavity effect) |
| 3 | Chimney exit 26 m above riser inlet; neutral plane at inlet | facility height 26 m | ±1 m → ±2 % on ṁ |
| 4 | Minor-loss K set (conditioner 2.0, exits 1.0, dampers 0.9) | Idelchik typical values | ±50 % on K → ∓8 % on ṁ |
| 5 | Well-mixed cavity gas (no stratification) | simplification | shifts conv/rad split locally; midplane values less affected |
| 6 | Uniform flow among the 12 risers; Riser 7 = periodic center duct | symmetric plenum feed | edge risers a few % different |
| 7 | Smooth-tube friction; Gnielinski fully-developed; no laminarization (Bo ≈ 0.02) | Re ≈ 19 000 | ±10 % on h_i → ±10 K on wall |
| 8 | Quasi-steady accident sweep | τ_plate ≈ 0.7 h ≪ 85 h | conservative on peak |

**The single most uncertain assumption is #1, the parasitic heat-loss fraction** (net heat
delivered to the riser air). It cannot be derived precisely because the heater-side insulation
stack-up is not specified; the plausible range 0.15–0.35 moves the mass flow by ±3 %, the riser
ΔT by ±18 %, and the plate by ±25 °C. All safety conclusions are unchanged across that range.

**Confidence summary:** ṁ 0.65 kg/s (medium, ±15 %) · ΔT 88 °C (medium, ±20 %) · riser hot-face
155 °C (low–medium, ±30 °C) · plate 386 °C (medium, ±40 °C) · rad fraction 0.83 (medium, ±0.07)
· accident bounded (high confidence — feedback argument is structural, not parametric).

## 8. References

1. Incropera, DeWitt, Bergman, Lavine, *Fundamentals of Heat and Mass Transfer*, 6th ed. —
   air properties (Table A.4), Churchill–Chu Eq. 9.26, view factors (Table 13.2), gray-enclosure
   networks (Ch. 13), emissivities (Table A.11).
2. Gnielinski, V., "New equations for heat and mass transfer in turbulent pipe and channel
   flow," *Int. Chem. Eng.* 16 (1976).
3. Churchill, S.W., Chu, H.H.S., "Correlating equations for laminar and turbulent free
   convection from a vertical plate," *IJHMT* 18 (1975).
4. Haaland, S.E., "Simple and explicit formulas for the friction factor in turbulent pipe flow,"
   *J. Fluids Eng.* 105 (1983).
5. Idelchik, I.E., *Handbook of Hydraulic Resistance*, 3rd ed. — minor-loss coefficients.
6. Jackson, J.D., Cotton, M.A., Axcell, B.P., "Studies of mixed convection in vertical tubes,"
   *Int. J. Heat Fluid Flow* 10 (1989) — buoyancy-impairment criterion.
7. ASHRAE *Handbook — Fundamentals*, Ch. 16 (stack effect and wind pressure).
8. ASME B&PV Code Sec. III / NRC HTGR licensing practice — 538 °C (1000 °F) short-term accident
   limit for low-alloy vessel steel.

## 9. Files

- `model.py` — full model (pure Python, stdlib only); run `python3 model.py`.
- `results.json` — headline results and all case tables.
