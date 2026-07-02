# Calculation Note — Passive Reactor Cavity Cooling System (½-scale, air-cooled)

**Subject:** First-principles prediction of natural-circulation performance of the ½-axial-scale
air-cooled RCCS test facility (12 riser ducts, 19.03° sector of the GA-MHTGR RCCS).
**Method:** hand-built physics model (pure Python, no external packages), no facility test data
consulted.
**Files:** `rccs_model.py` (model), `results.json` (machine-readable results),
`model_run_log.txt` (full run output).

---

## 1. Summary of predictions

| Quantity (at the instrumented location) | Prediction | Confidence |
|---|---|---|
| Loop air mass flow (Sierra meter, inlet downcomer) | **0.55 kg/s (33 kg/min)** | Medium-high (±15%) |
| Riser air temperature rise (outlet − inlet TC) | **≈ 101 °C** (20 → 121 °C) | Medium (±20%) |
| Riser wall, Riser 7, z = 3500 mm, hot (front) face | **≈ 160 °C** | Medium-low (±30 °C) |
| Heated plate (mock RPV) front, representative | **≈ 386 °C** | Medium-low (±40 °C) |
| Radiative fraction of riser heat removal | **≈ 0.87** (0.80–0.90) | Medium (±0.07) |
| Accident (Case 2) peak plate temperature | **≈ 321 °C at t ≈ 88 h** | Medium |
| Accident bounded? | **Yes — levels off, no runaway** | High |
| Weather | colder → more flow; wind ≈ ±12–17% at 11 m/s | Medium |

**Most uncertain assumption:** the **parasitic heat-loss fraction** — how much of the 82 kWe
electric input actually crosses the cavity into the riser air. The inputs state that 82 kWe
"corresponds to" the scaled 56.07 kWt duty, which implies **f_loss ≈ 0.32**; my bottom-up
insulation-conductance estimate supports only ≥ 0.10. Sweeping f_loss = 0.15 → 0.40 moves ΔT from
121 → 90 °C and plate temperature from 427 → 363 °C (mass flow barely moves: 0.57 → 0.54 kg/s,
because ṁ ∝ Q^⅓ in a friction-dominated chimney loop).

---

## 2. Inputs and derived geometry

From `inputs/01–04` (all SI):

| Item | Value |
|---|---|
| Riser duct (each) | 10 × 2 in outer, 0.188 in wall → internal 244.5 × 41.3 mm |
| Flow area | 0.01008 m²/duct → **0.1210 m² total** (12 ducts) |
| Hydraulic diameter | **D_h = 4A/P = 0.0706 m** (matches the quoted 0.0707 m) |
| Riser length | 7.49 m total, **6.82 m heated** (scaling value) |
| Duct pitch / gap | 52 in / 12 = 110.1 mm; opening between ducts 59.3 mm |
| Cavity | plate→riser gap 0.7066 m, width 1.321 m, height 6.7 m |
| Plate radiating area | 1.321 × 6.82 = **9.0 m²** (envelope; as-built quote 10.18, scaling table 8.82 — a stated ±12% inconsistency I carry as uncertainty) |
| Downcomer | Ø 0.61 m (A = 0.292 m²), L_eq = 4.69 m |
| Chimney | 2 × Ø 0.61 m (A = 0.584 m²), L_eq = 32.9 m/stack, discharge at **19.6 m** |
| Emissivities | plate 0.785 (measured); riser **0.79 assumed** (oxidized steel, not reported) |
| Air | 1 atm, properties from Incropera & DeWitt Table A.4, evaluated at mean gas T |

**Energy bookkeeping (key assumption A1).** Case 1 runs 82 kWe, and the inputs say this
corresponds to the scaled 1.5 MWt peak duty = 56.07 kWt removed by the RCCS. I therefore take
**Q_air = (1 − 0.316) × 82 = 56.1 kW** picked up by the riser air, the remaining ~26 kW being
parasitic (heater back-losses through the Duraboard/SuperIsol stack, structural bridges, cavity
walls, plena). This is the dominant uncertainty (see §1 and §8).

---

## 3. Loop model — natural-circulation flow rate

One-dimensional steady momentum balance around the open loop
(building at 20 °C → downcomer → inlet plenum → 12 risers → outlet plenum → chimneys →
outdoors at 19.6 m):

  g·[ρ_amb·z_disch − ρ_in·z₁ − ρ̄_riser·(z₂−z₁) − ρ_chim·(z_disch−z₂)] + Δp_wind = ΣΔp_loss

- Riser column density uses the exact integral for a linear T(z):
  ρ̄ = (P/RΔT)·ln(T_out/T_in).
- Elevations: heated riser 1.1 → 8.0 m, discharge 19.6 m above grade. Chimney gas at
  T_out − 3 °C (small insulated-duct loss, assumed).
- Losses (dynamic-head coefficients from Idelchik / Crane TP-410; friction from Petukhov
  f = (0.79 ln Re − 1.64)⁻², smooth): downcomer entrance+conditioner+elbow K = 2.8; Borda
  expansion into inlet plenum K = 1; riser sharp entry + turn K = 0.7, friction over L/D_h = 106,
  exit K = 1, plus flow acceleration G²(1/ρ_out − 1/ρ_in); chimney contraction 0.5 + dampers 0.9
  + friction + discharge KE (K = 1).
- Q_air = ṁ·c_p·ΔT closes the system; solved by bisection.

**Case 1 result:** draft ≈ 61 Pa, dominated by riser losses (53 Pa of 61 — the riser bank *is*
the loop's throttle); **ṁ = 0.551 kg/s**, riser velocity 4.4 m/s, Re = 15 700 (turbulent),
**ΔT = 101 °C** (20 → 121 °C at the outlet TC). The 4.4 m/s velocity is consistent with the
facility's own scaling statement (velocity ~ √½ × full scale). Because losses scale ~ṁ² while
buoyancy scales ~ΔT ~ Q/ṁ, ṁ ∝ Q^⅓ — the flow prediction is robust; ΔT inherits the Q
uncertainty almost linearly.

## 4. Cavity model — plate and riser wall temperatures

Gray-diffuse radiosity enclosure at the cavity cross-section (2-D, per metre height), surfaces:
**P** plate (ε 0.785) | **F** riser front faces (ε 0.79) | **O** slot openings between ducts
(treated as a near-black pseudo-surface, ε_eff ≈ 0.97 by the cavity formula, at the slot-wall
temperature) | **W** insulated side walls (adiabatic, re-radiating). View factors by crossed
strings (Modest, *Radiative Heat Transfer*): F(P→riser plane) = 0.599, split 0.46/0.54 between
fronts and openings by area (gap ≫ pitch → uniform irradiation).

Radiation absorbed through the openings is deposited on the duct side faces. The duct wall is
resolved as a **1-D circumferential fin** (k = 50 W/m·K, t = 4.78 mm, 81 nodes over the
half-perimeter, symmetric): radiative loads on front/side faces + natural convection from cavity
air outside (Churchill & Chu 1975, tall-plate; ×0.7 in the confined slots — assumption), internal
forced-convection sink h_i = 17.8 W/m²K from **Gnielinski** (Incropera & DeWitt Ch. 8) at the
mean gas temperature. Cavity air temperature from its own energy balance (plate convection in;
riser faces + insulated-wall losses out, U_wall = 0.46 W/m²K over 21.7 m²). The plate temperature
is then iterated until the risers pick up exactly Q_air. Energy closure check: plate output
58.1 kW vs riser pickup + wall loss 57.8 kW (0.5%).

**Case 1 results (at z = 3500 mm, local air 71 °C):**

| Node | Prediction |
|---|---|
| Plate front (mock RPV) | **386 °C** |
| Riser 7 hot/front face | **160 °C** |
| Riser side faces (mean) | 133 °C |
| Riser rear face | 120 °C |
| Cavity air | ≈ 188 °C |

Front-face flux received ≈ 4.6 kW/m² radiative; the fin conduction spreads it into the sides
(fin parameter mL ≈ 3.6, so spreading is partial — hence the ~40 °C front-to-side gradient the
four-face sensors should see).

## 5. Radiation / convection split

At the plate: 49.0 kW radiative vs 9.1 kW convective (84% radiative). At the risers (what the
matte/gold sensor pairs measure): radiation absorbed 49.0 kW — **19.3 kW on the front faces,
29.7 kW entering the inter-duct slots onto the side faces** — vs 7.1 kW convected from cavity
air: **radiative fraction ≈ 0.87**. Confidence: medium; it is sensitive to the assumed riser
emissivity (0.79) and to the ×0.7 slot-convection factor. Expected range 0.80–0.90. This
radiation dominance is the design's point: removal capability rises ~T⁴.

## 6. Case 2 — accident decay-heat transient

The supplied 10th-order polynomial (missing its C10 term) fails sanity checks — it starts at
42 kW (not 26), peaks near 60 h, and goes negative at 120 h — so per the inputs' stated
alternative I imposed the described shape: 26.16 → 56.07 kW, peaking at t = 84.85 h, then a slow
decay (gamma-like, P = 26.16 + 29.91·(t/t_p)²·e^{2(1−t/t_p)} kW).

Quasi-steady removal map R(T_plate) (from the full steady model at 10 power levels) + lumped
structural heat capacity C ≈ 3.0 MJ/K (plate 0.85 + risers 0.99 + heater stack/near-surface
structure ~1.2 — assumption). System time constant ≈ 2–3 h ≪ 85 h, so the transient is
quasi-steady with a small lag.

**Result: the temperature levels off — no runaway.** Removal grows ~T_plate⁴ while input is
bounded, so an equilibrium always exists and is stable.

- Peak plate: **≈ 321 °C at t ≈ 88.5 h** (≈ 3.7 h after the power peak)
- At the peak: ṁ ≈ 0.52 kg/s, ΔT ≈ 73 °C, riser hot-face ≈ 120 °C
- Margin: ~100 °C below the Case-1 steady value (Case 1 deliberately over-drives at 82 kWe),
  ~105 °C below a 425 °C continuous-service limit for the SAE 1020 plate, and far below the
  ~538 °C accident limit used for SA508-class reactor vessels. **accident_bounded = true.**

## 7. Case 3 — weather sensitivity (82 kWe held)

| Outdoor T | Wind | Δp_wind | ṁ (kg/s) | Δṁ | ΔT (°C) | Plate (°C) |
|---|---|---|---|---|---|---|
| −18 °C | 0 | — | 0.629 | +14% | 88 | 381 |
| +2 °C (base) | 0 | — | 0.551 | — | 101 | 386 |
| +24 °C | 0 | — | 0.476 | −14% | 117 | 392 |
| +2 °C | 11 m/s, tip suction Cp −0.3 | +23 Pa | 0.645 | +17% | 86 | 381 |
| +2 °C | 11 m/s, adverse Cp +0.2 | −16 Pa | 0.488 | −12% | 114 | 391 |
| +24 °C | 11 m/s adverse | −14 Pa | 0.417 | −24% | 133 | 398 |

**Sign and physics:** colder outdoor air → denser ambient column → stronger draft → more flow,
lower ΔT and metal temperatures. Wind matters because its dynamic pressure at 11 m/s (~75 Pa) is
comparable to the entire buoyant head (~60 Pa): crossflow suction at the stack tips aids flow;
stack pressurization (unfavorable geometry/gusting) opposes it and is the credible degraded mode
(risk of oscillation between the two stacks). The key safety observation: across the whole
−18…+24 °C, 0–11 m/s envelope the plate moves only about **−5/+12 °C**, because T⁴ radiation, not
the air loop, sets the vessel temperature.

## 8. Assumptions, correlations, confidence

Correlations (all textbook, cited): Gnielinski forced convection and air property table —
Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, 6th ed.; Churchill & Chu (1975)
natural convection; Petukhov friction factor; Idelchik *Handbook of Hydraulic Resistance* /
Crane TP-410 form-loss coefficients; crossed-strings view factors — Modest, *Radiative Heat
Transfer*.

Ranked uncertainties:
1. **Parasitic loss fraction f_loss = 0.316 (A1) — the most uncertain assumption.** Drives ΔT
   (±20%) and plate T (±40 °C); flow only ±4%.
2. Riser surface emissivity 0.79 (not reported) — moves the rad fraction ±0.05 and plate T ∓15 °C.
3. Form-loss set (conditioner K = 2, riser entry/exit) — ±30% on ΣK is ∓10% on ṁ.
4. Chimney discharge elevation read as 19.6 m above grade (ṁ ∝ H^⅓ approximately).
5. Slot natural-convection factor (0.7) and one-side-heated duct Nusselt (uniform h_i assumed);
   buoyancy-aided mixed convection could impair h_i locally — affects riser wall T (±20 °C), not
   the loop.
6. Uniform flow among the 12 risers assumed (the ΔP instrumentation exists precisely because
   maldistribution is possible; edge ducts will run slightly cooler).
