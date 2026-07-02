# Zero-Power Draft Correlation for the RCCS Air Loop

**Task:** predict the passive (heaters-off) natural-circulation mass flow ṁ as a function of
indoor–outdoor temperature difference ΔT and wind speed V, from first principles and the facility
geometry only. Working script: `output/draft_model.py`.

---

## 1. Functional form and physical justification

At zero power the loop still breathes because two independent pressure sources push cool outdoor
air through it, and a single turbulent resistance resists it. Balancing them gives the form.

### 1.1 Driving pressure — two additive terms

**(a) Stack (buoyancy) term — linear in ΔT.**
The loop is filled with building-temperature air (~20 °C) that rises up the risers and the two
insulated chimneys and discharges at height *H* into colder outdoor air. Writing the momentum
(pressure) balance around the *open* loop from the building intake (elevation z₁, building air at
ρ_in) to the chimney discharge (elevation z₂ = H, outdoor air at ρ_out):

  Δp_drive,fric = g·z₂·(ρ_out − ρ_in) − g·z₁·(ρ_in − ρ_in) = **g · H · (ρ_out − ρ_in)**

The intake elevation z₁ *cancels* because the air the loop draws in has the same density as the
air already inside it (both at indoor temperature) — so only the discharge height H matters. This
is the classical chimney-draft result. Using the ideal-gas law at common pressure P,

  ρ_out − ρ_in = (P/R_air)·(1/T_out − 1/T_in) ≈ ρ̄ · ΔT / T̄  ⟹  **Δp_stack ∝ ΔT.**

The buoyancy is set by a *density* difference, which for an ideal gas is linear in ΔT (for
ΔT ≪ T ≈ 290 K, the exact 1/T_out−1/T_in curves upward by only ~10 % at ΔT = 35 K — retained
exactly in the model, linearised for the technician formula).

**(b) Wind term — quadratic in V.**
Wind sweeping across the two open chimney tops produces a suction (negative gauge pressure) at the
outlet, set by Bernoulli: Δp_wind = C_w·½·ρ_out·V². This is a *dynamic pressure*, hence **∝ V²**.
The two sources act on the same series loop and drive flow in the same direction, so their
**pressures add**: Δp_drive = Δp_stack + Δp_wind.

### 1.2 Loss law — turbulent, so loss ∝ ṁ²

Every element (downcomer, risers, chimneys, plena entrances/exits) is in the fully-turbulent
regime (riser Re ≈ 5 000–21 000 across the whole map — see §3). In that regime both the Darcy
friction loss f·(L/D)·½ρv² and all minor losses K·½ρv² scale as velocity² and therefore as ṁ².
Summing them referenced to the total mass flow:

  Δp_loss = R · ṁ² ,  R = Σᵢ (fᵢ·Lᵢ/Dᵢ + Kᵢ) / (2·ρ·Aᵢ²)   [Pa·(kg/s)⁻²]

### 1.3 Resulting correlation

Setting drive = loss:

> **ṁ = √( [ g·H·(ρ_out − ρ_in) + C_w·½·ρ_out·V² ] / R )**

Limiting behaviour, both physically correct:
- Calm wind (V→0): ṁ ∝ **√ΔT** (turbulent buoyant loop).
- Isothermal (ΔT→0): ṁ ∝ **V** (√ of a V² driver).
- The square-root overall is the signature of a quadratic (turbulent) loss law; a laminar loop
  (loss ∝ ṁ) would instead give ṁ ∝ ΔT.

---

## 2. Numeric coefficients from the geometry

**Geometry used** (from `01_facility_geometry.md`):

| Element | Value used | Area A (m²) | Length (m) |
|---|---|---|---|
| Downcomer | 24 in dia | 0.292 | 4.69 (184.5 in equiv) |
| Risers (×12) | 9.624 × 1.624 in internal, D_h = 0.0706 m | 0.121 (total) | 7.49 (295 in) |
| Chimneys (×2) | 24 in dia | 0.584 (total) | 32.9 (826+470 in equiv) |
| Stack height H | chimney discharge, baseline | — | **19.6 m** |

**Loss build-up** (Darcy f from Colebrook; ε = 0.045 mm steel, 0.15 mm galvanized chimney; minor
K from standard tables — entrance 0.5, sudden-expansion exit 1.0, 90° elbow 0.5, flow conditioner
1.0, open dampers/elbows ~1.0):

| Element | f·L/D | ΣK | R-contribution (Pa·(kg/s)⁻²) |
|---|---|---|---|
| Downcomer | 0.15 | 2.0 | 10 |
| **Risers (×12)** | **3.3** | **1.5** | **131  ← dominant (small area, long, split 12 ways)** |
| Chimneys (×2) | 1.1 | 2.5 | 5 |
| **Total R** | | | **≈ 146** |

**Driving coefficients** (P = 101 325 Pa, T_in = 293 K, evaluated at ΔT = 15 K reference):
- Stack: a = g·H·(ρ_out−ρ_in)/ΔT ≈ **0.83 Pa/K**
- Wind: b = C_w·½·ρ_out ≈ **0.25 Pa/(m/s)²**  (with C_w = 0.4)

Folding R in and converting to kg/min (×60), the **technician-ready formula** is:

> ### ṁ [kg/min] ≈ √( 20.5·ΔT + 6.25·V² )
> ΔT = T_indoor − T_outdoor [K], V = wind speed [m/s].
>
> (Equivalent long form: ṁ = 60·√[(0.83·ΔT + 0.25·V²)/146].)

Reproduces the full iterated-property model (which re-evaluates ρ and f at every point) to within
~10 % over the whole map.

---

## 3. Validity limits and confidence

**Validity range:** ΔT ≈ 2–35 K, V ≈ 0–12 m/s, baseline configuration (dual chimneys open, dampers
open, discharge 19.6 m, heaters off, indoor ≈ 20 °C). Do **not** use for ΔT ≈ 0 with V ≈ 0 (flow →
0, model degenerate) or if a chimney/damper is closed (R changes) or discharge height is lowered
(H scales the stack term directly).

**Turbulence check:** riser Re spans ≈ 4 950 (ΔT = 5, V = 0) to 20 600 (ΔT = 30, V = 10) — the
ṁ² loss law holds throughout; only the single calmest point is mildly transitional, where the true
flow may be a few % below the prediction.

**Confidence by coefficient:**

| Quantity | Confidence | Basis / caveat |
|---|---|---|
| Stack term (a, exponent 1 in ΔT) | **High** | Pure ideal-gas buoyancy + geometry; H = 19.6 m is a stated baseline dimension. Downcomer/inlet-plenum are uninsulated, so intake air may cool slightly below 20 °C → real stack drive marginally lower (conservative to assume full ΔT). |
| Loss coefficient R (exponent ½) | **Medium-high** | Riser friction (the 90 % contributor) is well-constrained by geometry; f iterated via Colebrook. Minor-K values (±30 %) move R by only ~±8 % since risers dominate. R itself varies 131→172 (±13 %) with flow because f falls with Re — the fixed-R formula carries this as its ~10 % spread. |
| Wind term (b, C_w, exponent 2 in V) | **Low** | The V² scaling is firm (dynamic pressure). The magnitude C_w = 0.4 is an *effective net* suction coefficient: two stacks on opposite (N/S) walls mean one is windward (stagnation, opposes) and one leeward (suction, aids), so the pair partially self-cancels. Plausible range C_w ≈ 0.2–0.7 → wind-driven flow uncertain by roughly ±30 %. This is the weakest link; wind direction relative to the stack pair is not modelled. |
| Absolute ṁ | **±15–25 %** | Compounded from the above plus ~2 % from local barometric pressure (facility at ~180 m: P ≈ 99 kPa vs 101 kPa assumed → ṁ ~2 % lower). |

**Sanity:** predicted zero-power flows (9–38 kg/min) sit sensibly *below* the powered-loop scale
(a scaled ~82 kW duty with a ~150 K riser rise implies ṁ ≈ Q/(c_p·ΔT_rise) ≈ 33 kg/min), as a
passive draft should.

---

## 4. Predicted mass flow ṁ [kg/min]

Full model (properties and friction re-evaluated at each point):

| ΔT \ V | 0 m/s | 5 m/s | 10 m/s |
|---:|---:|---:|---:|
| **5 K**  |  9.2 | 15.2 | 26.7 |
| **15 K** | 17.2 | 21.5 | 31.3 |
| **30 K** | 26.2 | 29.6 | 38.2 |

(Closed-form √(20.5·ΔT + 6.25·V²) gives 10.1 / 16.1 / 27.0 · 17.5 / 21.5 / 30.5 · 24.8 / 27.8 /
35.2 — within ~10 % of the above.)

**Reading the table:** at calm wind the flow grows as √ΔT (5→30 K nearly triples the driver but
only ~2.8× the flow); wind alone (ΔT small) drives flow linearly in V and dominates by V = 10 m/s;
the two effects combine as the √ of their summed pressures, so they are strongly sub-additive
(e.g. ΔT = 15, V = 10 gives 31 kg/min, not 17 + 27).

---

### Correlations cited
- Ideal-gas buoyancy / chimney-draft relation Δp = g·H·(ρ_out−ρ_in) (standard stack effect).
- Bernoulli wind dynamic pressure Δp = C_p·½ρV² (ASHRAE wind-pressure convention).
- Darcy–Weisbach friction with the Colebrook–White f(Re, ε/D); minor-loss K values from standard
  handbook tables (entrance, exit/expansion, elbow).
- Rectangular-duct hydraulic diameter D_h = 4A/P.
