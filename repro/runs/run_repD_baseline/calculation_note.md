# Calculation Note — Passive Reactor Cavity Cooling System (air-cooled, ½-scale)

**Author:** engineering analysis (first-principles)
**Date:** 2026-07-02
**Scope:** predict the natural-circulation performance of the ½-axial-scale, air-cooled RCCS
described in `inputs/` — mass flow, air temperature rise, wall/vessel temperatures, the
radiation/convection split, the accident decay-heat transient (peak temperatures and
stability), and the sensitivity to outdoor weather.

> **Provenance statement.** Every number below was derived from physics and the geometry,
> materials and boundary conditions given in `inputs/`. **No measured data, published test
> report, or pre-built model of this facility was consulted.** Empirical correlations used are
> generic (heat-transfer / fluid-mechanics textbook and standards) and are cited at each use.
> Air properties are from CoolProp (an open thermophysical library), not from any facility source.

---

## 1. Method overview

The facility is an open natural-circulation air loop: a hot mock-vessel plate radiates and
convects across an air cavity to a bank of **12 vertical steel riser ducts**; the air inside the
risers warms, rises by buoyancy, exits an upper plenum into two insulated chimneys, and is
replaced by cool inlet air down a downcomer.

I built a coupled steady-state model (`output/steady.py`) that simultaneously closes five
balances, iterated to convergence:

| Balance | Equation | Solves for |
|---|---|---|
| A. Loop momentum | buoyant draft ΔP_drive = friction ΔP_fric | loop mass flow ṁ |
| B. Coolant energy | Q_air = ṁ·c_p·ΔT | riser air rise ΔT |
| C. Cavity heat transfer | Q_air = Q_rad(T_p,T_s) + Q_conv(T_p,T_s) | plate temp T_p |
| D. Riser wall energy | Q_air = h_i·A_i·(T_wall−T_air) | riser wall temp T_s |
| E. Parasitic loss | Q_air = P_e − Q_loss(T_p,T_cav) | net heat to air Q_air |

The transient (`transient.py`) and weather sweep (`weather.py`) reuse this solver. All working
files, a machine-readable `results.json`, and `summary_figures.png` are in `output/`.

### Key physical inputs (all from `inputs/`)
- 12 risers, internal 9.624 in × 1.624 in → A = 100.8 cm²/duct, D_h = 70.6 mm (target 70.7 mm),
  heated length 6.909 m, total 7.493 m. Total internal flow area 0.121 m², internal wetted
  surface 47.4 m².
- Heated plate (mock RPV): A_plate = 10.18 m² (as-built), ε_plate = 0.78 (measured, mid-range).
- Cavity gap plate→riser front 0.7066 m; cavity cross-section (curtain) 1.32 m × 6.71 m = 8.86 m².
- Downcomer 0.61 m dia; dual chimney total 0.58 m²; discharge height 19.6 m.
- Insulation: SuperIsol 6 in (k ≈ 0.09 W/m·K) on N/S/W cavity walls; Duraboard 2 in
  (k ≈ 0.11 W/m·K) behind heaters.
- Steel k = 50 W/m·K, ρ = 7850, c_p = 480 (standard values, per `02_materials`).
- Site pressure 99.0 kPa (≈180 m elevation near Chicago).

### Correlations and their sources
- **Friction factor:** laminar 64/Re; turbulent **Haaland (1983)** smooth-duct formula.
- **Minor losses:** standard K-factors (entrance ≈0.5, sudden expansion ≈1.0, contraction ≈0.5,
  90° elbow ≈0.9, exit 1.0) — *Idelchik / Crane TP-410* class values.
- **Internal (riser) convection:** **Gnielinski (1976)** correlation for turbulent duct flow.
- **Cavity natural convection (plate↔riser gap):** high-Rayleigh vertical-cavity relation
  Nu_L = 0.046·Ra_L^(1/3) (*ASHRAE / Incropera, boundary-layer regime*).
- **Radiation:** two-surface gray enclosure (plate ↔ riser curtain) with **reradiating adiabatic
  side/back walls**, network resistance form (*Incropera & DeWitt, "Fundamentals of Heat and Mass
  Transfer"*), effective view factor F̄→1 for opposing faces joined by reradiating walls.
- **Air properties:** CoolProp (Bell et al., 2014), evaluated at local T and 99 kPa.

---

## 2. Case 1 — baseline steady state (P_e ≈ 82 kW_e, inlet air 20 °C, outdoor +2 °C)

Converged result:

| Quantity (where measured) | Prediction | Confidence |
|---|---|---|
| **(1) Loop mass flow** ṁ (inlet downcomer, whole loop) | **0.65 kg/s ≈ 39 kg/min** | Medium-high |
| **(2) Riser air ΔT** (outlet − inlet TC) | **≈ 110 °C** (T_out ≈ 130 °C) | Medium-high |
| **(3a) Riser wall T** (Riser 7, z=3500 mm, front face) | **≈ 195 °C** (perimeter-mean ≈ 150 °C) | Medium |
| **(3b) Heated-plate front T** | **≈ 420 °C** | Medium |
| **(4) Radiative fraction** of heat removal | **≈ 0.92–0.94** (Q_rad ≈ 67 kW, Q_conv ≈ 4 kW) | Medium |
| Net heat to air Q_air / parasitic loss | 71 kW / ≈ 11 kW (13 %) | Low-medium |
| Draft = friction (self-consistent) | ≈ 70 Pa each | Medium |

**Reasoning.**
- *Flow & ΔT (A,B).* The buoyant draft is the weight deficit of the hot internal column relative
  to an outdoor cold column, ΔP = g∫(ρ_o−ρ_int)dz over the 19.6 m stack (risers heating
  20→130 °C, then chimney at ~130 °C). Balancing against friction — dominated by the 12 risers
  (D_h = 71 mm, Re ≈ 1.8×10⁴, turbulent) plus chimney and minor losses — closes at
  ṁ ≈ 0.65 kg/s. With Q_air ≈ 71 kW this gives ΔT = Q_air/(ṁ c_p) ≈ 110 °C. Riser velocity ≈ 5.4 m/s.
- *Radiation/convection split (C,4).* Because the plate runs at ~420 °C, radiation dominates:
  σ·Ā·(T_p⁴−T_s⁴) with Ā = 6.49 m² (gray reradiating enclosure) carries ≈ 67 kW, while
  sealed-cavity natural convection across the 0.71 m gap (h ≈ 2.1 W/m²·K, Ra ≈ 3.7×10⁸) carries
  only ≈ 4 kW → **radiation ≈ 93 %**. This matches the expected physics of a high-temperature RCCS
  (the matte-vs-reflective heat-flux sensors are placed exactly to capture this split).
- *Wall/plate temperatures (D,3).* Riser internal convection (Gnielinski, h_i ≈ 20 W/m²·K over
  47.4 m²) sets a mean wall-to-air film rise of ~75 °C → perimeter-mean wall ≈ 150 °C. The **front
  face** at mid-plane runs hotter because the incident radiation is concentrated there; a
  flux-concentration factor of ~1.6 on the local film rise gives **≈ 195 °C** at the sensor
  location. The plate temperature then follows from balancing 71 kW of radiation+convection at
  T_p ≈ 420 °C — i.e. a net wall flux ≈ 7 kW/m², consistent with the facility's scaled peak design
  flux of 6.82 kW/m².

---

## 3. Case 2 — accident decay-heat transient

The scaled decay curve rises from the normal load (26.2 kW_t at ½-scale) to a peak of
**56.1 kW_t** (at ½-scale time ≈ 84.85 h), then declines. Because the load ramps over ~85 h while
the plate's thermal time constant is short, the loop is **quasi-steady** — verified below — so the
transient is the steady solver evaluated along P(t) (`transient.py`).

**Time-constant check.** Plate steel mass ≈ 2030 kg → C_plate ≈ 0.97 MJ/K. The radiative
conductance at the peak is dQ/dT_p = 4σĀT_p³ ≈ 360 W/K, giving τ ≈ 0.75 h ≪ 85 h ramp. The plate
lag is therefore negligible; peak temperatures coincide with peak power.

| Peak-of-transient quantity | Prediction | Confidence |
|---|---|---|
| **Peak decay power** (½-scale) | 56.1 kW_t | High (given) |
| **Peak plate temperature** | **≈ 350 °C** | Medium |
| **Peak riser front-wall temperature** | **≈ 145 °C** | Medium |
| **Peak mass flow** | **≈ 0.60 kg/s (36 kg/min)** | Medium-high |
| Peak riser ΔT | ≈ 78 °C | Medium-high |

**Does it level off or run away? — It LEVELS OFF; the vessel stays safe.**

The system is intrinsically self-stabilizing:
1. Higher plate temperature → radiative removal grows as **T⁴** (very steep);
2. Higher air temperature → larger buoyant draft → more flow → more convective removal.

Both restoring effects strengthen faster than the load, so a stable equilibrium always exists.
The steady removal-capacity sweep confirms a **monotonic, single-valued** T_p(P) with no bifurcation
or thermal runaway:

| Power [kW] | 26 | 40 | 56 | 82 | 120 | 160 | 220 (facility max) |
|---|---|---|---|---|---|---|---|
| Plate T [°C] | 228 | 291 | 347 | 420 | 504 | 578 | 676 |
| Radiative fraction | 0.86 | 0.89 | 0.92 | 0.94 | 0.96 | 0.97 | 0.98 |

At the accident peak (56 kW) the plate settles near **350 °C** — comfortably below a conservative
structural safe limit for the low-carbon steel mock vessel (**~550 °C**, where SAE 1020 strength
degrades markedly). The plate would only approach that limit near ~150 kW, roughly **2.7× the peak
decay load** — a large passive margin. **Conclusion: the passive RCCS removes the decay heat and
the vessel temperature levels off well below the safe limit; it does not run away.**

---

## 4. Case 3 — weather sensitivity (baseline load, outdoor T and wind varied)

**Outdoor temperature** sets the density of the cold reference column, so it directly modulates
the draft (ΔP_drive ∝ ρ_o − ρ_hot):

| Outdoor T [°C] | −18 | −10 | 0 | +2 | +10 | +24 |
|---|---|---|---|---|---|---|
| Mass flow [kg/min] | 44.4 | 42.1 | 39.3 | 38.7 | 36.6 | 33.2 |
| Riser ΔT [°C] | 95 | 101 | 108 | 110 | 116 | 128 |
| Riser front-wall T [°C] | 176 | 183 | 193 | 195 | 203 | 219 |
| Plate T [°C] | 413 | 416 | 419 | 420 | 423 | 429 |
| Draft [Pa] | 88 | 81 | 72 | 70 | 64 | 54 |

- **Colder outdoor air → stronger draft → more flow → smaller ΔT and cooler risers.** Over the full
  −18 → +24 °C range the flow varies by ≈ ±15 % about the +2 °C baseline.
- **The plate (vessel) temperature is nearly insensitive to weather** (413→429 °C across 42 °C of
  ambient). This is an important and robust result: the vessel temperature is fixed by the **radiative
  heat-rejection balance** (a weak function of flow), while flow and ΔT absorb the weather variation.
  Passive cooling of the vessel is therefore weather-robust.

**Wind** changes the pressure at the chimney discharge. A cross-wind over/around a vertical stack
top typically produces suction (C_p ≈ −0.3…−0.6) that **aids** the draft; a wind stagnating into
the discharge (C_p > 0) **opposes** it. Bounding both with ΔP_wind = −C_p·½ρU²:

| Wind U [m/s] | 0 | 4 | 8 | 11 |
|---|---|---|---|---|
| Flow, assisting (C_p=−0.4) [kg/s] | 0.65 | 0.66 | 0.71 | 0.77 |
| Flow, adverse (C_p=+0.4) [kg/s] | 0.65 | 0.63 | 0.58 | 0.52 |

At the facility's ~11 m/s upper wind, the draft term is ±30 Pa (comparable to the 70 Pa thermal
draft), swinging flow by roughly ±20 %. Wind is thus a **second-order but non-negligible**
influence; its sign depends on wind direction relative to the stacks.

---

## 5. Confidence and the most-uncertain assumptions

**Overall confidence: medium.** The flow, ΔT and stability conclusions are the most robust; the
absolute wall/plate temperatures and the exact radiative fraction carry more uncertainty.

Ranked most-uncertain assumptions (biggest lever first):
1. **Riser surface emissivity (ε_riser = 0.80, assumed).** Not reported in the source. It directly
   scales the dominant radiative path. Range 0.7–0.9 would shift the radiative conductance Ā by
   ~±8 % and the plate temperature by ~±15 °C. *Most uncertain single input.*
2. **Front-face flux-concentration factor (×1.6).** Sets how much hotter the instrumented front
   face runs above the perimeter-mean wall. A proper 2-D/CFD riser conduction solve would sharpen
   this; the perimeter-mean wall (~150 °C) is more reliable than the ~195 °C front-face value.
3. **Parasitic heat-loss fraction (~13 %).** The source states the measured loss fraction is not
   provided; I estimated it from insulation conduction. It maps almost 1:1 onto the net Q_air and
   hence ΔT.
4. **Radiation view factor F̄→1** (reradiating-enclosure idealization) and treating the riser bank
   as a full-cross-section "curtain." Real gaps between ducts and partial reradiation make this
   slightly optimistic; effect is modest because losses net out on adiabatic walls.
5. **Buoyancy reference / building-vs-outdoor inlet air.** The draft integral uses outdoor density
   as the external reference; the building-air inlet detail is a small correction.

**Suggested next step to tighten the numbers:** a lumped-network or CFD riser cross-section model
to replace the front-face concentration factor, and a sensitivity study on ε_riser and the loss
fraction.

---

## 6. Files in `output/`
- `air_props.py` — air properties (CoolProp wrapper).
- `geometry.py` — facility geometry derived from `inputs/`.
- `steady.py` — coupled steady-state solver (balances A–E).
- `transient.py` — Case 2 decay-heat transient + passive-stability sweep.
- `weather.py` — Case 3 outdoor-temperature and wind sensitivity.
- `run_all.py` — runs everything; writes `results.json` and `summary_figures.png`.
- `results.json` — machine-readable summary of all cases.
- `summary_figures.png` — transient, stability, and weather-sensitivity plots.
