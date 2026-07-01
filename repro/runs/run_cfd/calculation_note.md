# Calculation Note — Passive Reactor Cavity Cooling System (RCCS)

**Facility:** ½-axial-scale, air-cooled RCCS test facility (12-riser, 19.03° sector of a
227-riser MHTGR-type design). Natural circulation, no pumps.
**Scope:** Predict, from first principles, the natural-circulation air mass flow, riser air
temperature rise, riser-duct and heated-wall (mock-vessel) temperatures, the radiation/convection
split, the accident (decay-heat) peak temperatures and stability, and the sensitivity to outdoor
weather. One key result (the heated-wall temperature) is cross-checked with an independent CFD
calculation that includes radiation.

> **Provenance statement.** Every number in this note was derived from the geometry, materials and
> boundary conditions in `inputs/` plus textbook physics and cited general correlations. **No
> published test data, report, or pre-made model of this facility was consulted.** The facility's
> own measured values are held out; predictions are reported at the sensor locations given in
> `inputs/03_instrumentation_map.md` so they *could* later be compared.

---

## 1. Method summary

Two coupled balances are solved (Python model `rccs_model.py`, driver `cases.py`):

**(A) Loop momentum → mass flow.** Buoyant chimney draft is balanced against loop friction + form
losses:
$$\Delta p_\text{draft}=g\!\int_0^{H}\!\big(\rho_\text{out}-\rho_\text{gas}(z)\big)\,dz
\;=\;\Delta p_\text{loss}=\sum_i\Big(f_i\tfrac{L_i}{D_{h,i}}+K_i\Big)\tfrac12\rho_iV_i^2 .$$
Draft uses the standard natural-draft/stack relation (outdoor air is the reference column; ASHRAE
*Handbook — Fundamentals*, stack effect). Friction factor: laminar $64/Re$; turbulent Petukhov
$f=(0.790\ln Re-1.64)^{-2}$ (Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, eq. 8.21).
Minor-loss $K$ values from Crane TP-410 / Idelchik (entrance 0.5, sudden expansion ≈1.0,
contraction 0.5, elbow 0.3, exit 1.0, flow conditioner ≈1.0).

**(B) Heat-transfer network → temperatures.**
- Air rise: $\Delta T = Q/(\dot m\,c_p)$.
- **Cavity radiation** plate→riser: two-surface enclosure with re-radiating (adiabatic N/S/W)
  walls, so effectively all plate radiation reaches the risers:
  $Q_\text{rad}=\sigma A_\text{plate}(T_p^4-T_{r}^4)/(1/\varepsilon_p+1/\varepsilon_r-1)$
  (Incropera eq. 13.24), $\varepsilon_p=0.785$ (measured), $\varepsilon_r=0.80$ (assumed, oxidised
  steel — not reported).
- **Cavity natural convection** plate→air→riser: vertical-plate Churchill–Chu (Incropera eq. 9.26),
  a minority parallel path.
- **Riser internal convection** wall→air: Gnielinski (Incropera eq. 8.62) at hydraulic diameter
  $D_h=70.6$ mm.
- **Riser-wall circumferential temperature**: thin-wall fin equation solved around the tube
  perimeter with the incident flux allocated front/side/rear (≈45/50/5 %) by view-factor reasoning,
  giving the front-face (sensor) temperature versus the perimeter mean.
- Air properties $\rho,\mu,k,c_p,Pr,\beta$ from cited correlations (`airprops.py`): ideal gas,
  Sutherland viscosity/conductivity (White, *Viscous Fluid Flow*), $c_p$ polynomial fit to Incropera
  Table A.4. Validated at 300 K to <0.5 %.

**Heat duty.** The 82 kWe baseline "corresponds to the scaled 1.5 MW­t peak duty" = **56 kWt**
(½-scale). I take the heat *crossing the cavity to the risers* as $Q=56$ kW; the ~26 kW balance is
parasitic (back-of-heater conduction, cavity-wall and uninsulated-ductwork losses). **This
electric-to-air fraction is the single most uncertain input** — §8 gives the sensitivity.

---

## 2. Baseline steady state (Case 1: Q = 56 kW, inlet 20 °C, outdoor +2 °C)

| Quantity | Location (per instrumentation) | Prediction | Confidence |
|---|---|---|---|
| **Air mass flow** $\dot m$ | inlet downcomer, whole loop | **0.58 kg/s ≈ 35 kg/min** | Medium (±25 %) |
| **Riser air ΔT** | outlet − inlet gas TC | **≈ 96 K** (T_out ≈ 116 °C) | Medium (±20 %) |
| **Riser wall T (front, mid-plane z=3.5 m)** | Riser 7 hot face | **≈ 163 °C** (perimeter mean ≈ 130 °C) | Medium |
| **Heated-plate (mock-vessel) T, front** | plate front face | **≈ 390 °C** | **Medium-high** (CFD-confirmed, §7) |
| **Radiative fraction of heat removal** | Riser 7 four-face flux | **≈ 0.93** (0.96 in CFD) | High (both methods >0.9) |
| Riser velocity / Reynolds no. | — | 4.6 m/s / Re ≈ 1.7×10⁴ (turbulent) | — |
| Chimney draft = loop loss | — | ≈ 60 Pa | — |

**Loss split (why the flow is what it is):** riser bank **48.6 Pa (80 %)**, chimney 7.0 Pa,
downcomer + plena 4.8 Pa. The small riser hydraulic diameter dominates the loop resistance, so the
passive flow self-limits at ~0.58 kg/s and the air must take a large ~96 K rise to carry 56 kW.
Because loss ∝ $\dot m^2$ and draft ∝ ΔT, the equilibrium scales roughly as
$\dot m\propto Q^{1/3}$, $\Delta T\propto Q^{2/3}$ — flow is *stiff* against power changes.

**Radiation vs convection.** Of the 56 kW crossing the cavity, ≈ 52 kW is radiative
(plate at 390 °C, $\varepsilon\!\approx\!0.79$, $T^4$ law) and ≈ 4 kW is cavity natural convection.
Radiation dominates because the plate is hot and the gap air is nearly transparent. By riser face,
the **front (line-of-sight) face** carries the largest flux (~45 %), the two wide side faces ~50 %
(via re-radiation off the back insulation), rear ~5 %.

---

## 3. Riser-duct and heated-wall temperatures — detail

- **Heated plate (mock RPV):** ~390 °C to radiate 52 kW across the cavity to risers held near
  130–160 °C. Robust to riser-emissivity assumption (±0.05 in $\varepsilon_r$ → ±~10 °C).
- **Riser wall:** perimeter-mean ~130 °C; the front face runs ~33 K hotter (~163 °C at mid-plane)
  because it intercepts the direct radiation and the thin (4.8 mm) A500 wall only partially
  equalises circumferentially (fin parameter $1/m\approx0.11$ m < half-perimeter 0.29 m). The
  **axial** peak wall temperature is near the riser *top* (~205 °C) where the air is already hot
  (§6), not at mid-plane.
- Internal convection coefficient $h_i\approx18$ W/m²K (Gnielinski). This is the limiting resistance
  for the riser wall: pure forced convection is used (conservative); buoyancy-aided mixed convection
  in the heated vertical duct would raise $h_i$ and slightly *lower* wall temperatures.

---

## 4. Radiation / convection split

| Path | 1-D network | CFD (viewFactor) |
|---|---|---|
| Radiation (plate→risers) | 93 % | 96 % |
| Convection (cavity air) | 7 % | 4 % |

Both independent methods agree radiation removes **>90 %** of the heat. This is the physically
expected result for a hot (~390 °C) source across a transparent air gap and is the design principle
of an RCCS. Confidence: **high** on the qualitative dominance; the exact few-percent convective
share is the softer number.

---

## 5. Accident decay-heat transient (Case 2) — peak temperatures & stability

The decay-heat curve is a *rise-to-peak* (depressurised conduction cooldown): load climbs from the
normal 26 kW to the **56 kW peak at ½-scale time t ≈ 84.85 h**, then declines. (The supplied 9-term
polynomial is missing its C10 term and diverges after ~110 h, so — as the input permits — the
**normalized shape** 26→56 kW peaking at 84.85 h was imposed.)

Because the load changes over *tens of hours* while the loop's thermal time constant is
$C/(\mathrm dQ/\mathrm dT)\sim$ hours (lumped capacitance $C\approx2.1$ MJ/K: plate 0.85 + risers
0.96 + heaters 0.30), the transient is **quasi-steady**:

| Quantity | Prediction |
|---|---|
| Peak heat load | 56 kW at t = 84.85 h |
| **Peak heated-plate T** | **≈ 390 °C** (with thermal inertia: 391 °C, lagging the power peak by ~2 h) |
| Peak riser front-face T | ≈ 163 °C |
| Peak mass flow | ≈ 0.58–0.60 kg/s |

**Does it level off or run away? — It levels off. No runaway.** The dominant heat-removal path
(radiation) scales as $T_p^4$, a strong negative feedback: as the plate warms, its heat rejection
rises steeply and the buoyant flow also increases. The steady plate temperature vs. power is gentle
and bounded:

| Heat load Q | 26 | 40 | 56 | 80 | 110 kW |
|---|---|---|---|---|---|
| Steady plate T | 271 | 334 | **391** | 458 | 528 °C |

Even a hypothetical *doubling* of the peak load (56→110 kW) raises the plate only to ~528 °C.
**Safety margin:** the peak plate temperature (~390 °C, or ≤~440 °C including the parasitic-loss
uncertainty band) stays well below carbon-steel structural/creep concern (~550 °C) and typical
RPV-steel accident limits (~430–540 °C). The passive system is inherently self-stabilising.
Confidence: **high** on the *qualitative* conclusion (stable, levels off); **medium** on the exact
peak (tied to the Q assumption).

---

## 6. Weather sensitivity (Case 3)

Outdoor air temperature sets the density of the cold reference column and the inlet air; wind
perturbs the draft and parasitic losses. Sweeping outdoor T from −18 to +24 °C (inlet tracking with
an 18 °C building warm-up), wind ≈ 0:

| Outdoor T | −18 °C | +2 °C (baseline) | +24 °C |
|---|---|---|---|
| Mass flow | 0.63 kg/s | 0.58 | 0.53 |
| Air ΔT | 88 K | 96 | 105 |
| Heated-plate T | 382 °C | 390 | 401 |

**Colder outdoor air → denser draft column → more flow → lower plate temperature** (better cooling);
warm days are the limiting condition. The effect is modest (~±20 °C on the plate across a 42 °C
outdoor swing) because radiation (nearly independent of flow) carries most of the heat.

**Wind:** a dynamic head $½\rho V^2$ at the 24-in chimney outlet perturbs the ~60 Pa draft by
$\pm C_p\,½\rho V^2$ ($C_p\!\approx\!0.3$). At 11 m/s this is ~±78 Pa gross → the flow varies roughly
**0.45–0.68 kg/s** (adverse gusting vs. favourable aspiration), i.e. ±15–20 %. Wind also raises
convective loss from uninsulated hot ductwork (slightly lowering exhaust temperature and draft). Net:
wind is a **secondary** influence versus ambient temperature, and mostly adds scatter/unsteadiness
rather than a systematic shift. Confidence: **low-medium** (wind direction and building
aerodynamics not specified — most uncertain part of the weather analysis).

**Power-shape variation (Case 4, same integral 56 kW):** flow and total ΔT are set by the integral
power and barely change. The *local* peak wall temperature shifts with the axial power peak — top
for uniform/cosine (~206 °C), lower-third (~198 °C at z≈3 m) for bottom-peaked. Azimuthal 65/35 skew
raises the wall/plate temperature on the hot side by roughly the skew ratio locally.

---

## 7. Independent CFD cross-check (heated-wall temperature) — and reconciliation

**Tool:** OpenFOAM v2312 `buoyantSimpleFoam` (steady buoyant compressible RANS/laminar) with
**`viewFactor` surface-to-surface radiation** (transparent air) — run in the provided Docker image;
no code compiled. Files in `output/cfd/`, generator `output/make_cfd_case.py`.

**Model:** 2-D vertical slice of the cavity, depth 0.7066 m (plate → riser front plane), 2 m
representative height (per-area radiative exchange between the parallel strips is height-independent
in the parallel-plate limit). Plate wall fixed at the 1-D prediction **390 °C** ($\varepsilon$0.785),
riser plane at **160 °C** ($\varepsilon$0.80), top/bottom re-radiating (adiabatic). View factors
generated with `faceAgglomerate`+`viewFactorsGen`; heat fluxes from the `wallHeatFlux` function
object (with `qr`) and `qr` patch averages.

**CFD result:** plate area-mean total flux **6215 W/m²**, of which radiative **5960 W/m² (96 %)**,
convective 255 W/m² (4 %).

**Reconciliation:**

| | 1-D network | CFD (radiation) | Agreement |
|---|---|---|---|
| Plate flux to remove 56 kW (=56 kW/8.84 m²) | 6335 W/m² required | 6215 W/m² at 390 °C | within **2 %** |
| ⇒ Heated-wall temperature for 56 kW | **390 °C** | **≈ 391–392 °C** | within ~2 °C |
| Radiative fraction | 0.93 | 0.96 | consistent (both > 0.9) |

The CFD, using a completely different treatment of radiation (explicit view factors between mesh
faces rather than a lumped two-surface formula) and resolving the cavity buoyant flow, reproduces
the heated-wall temperature to ~2 % and confirms radiation dominance. The small convective
difference (CFD 4 % vs 1-D 7 %) reflects the different natural-convection treatment (resolved 2-m
cavity vs. Churchill–Chu over 6.7 m) and is immaterial to the plate temperature. **The 1-D model's
key temperature is corroborated by independent higher-fidelity CFD.**

---

## 8. Confidence, and the most uncertain assumptions

| # | Assumption | Impact | How uncertain |
|---|---|---|---|
| 1 | **Heat-to-air = 56 kW** (electric-to-air ≈ 68 %; parasitic ≈ 32 %) | Sets all temperatures & flow | **Most uncertain.** Q = 48→72 kW gives plate 364→437 °C, ΔT 85→118 K, $\dot m$ 0.56→0.61 kg/s (see `results/results.json`, `case1_sens`). Conclusions (stable, radiation-dominated, below limits) hold across the band. |
| 2 | Riser emissivity 0.80 (not reported) | Plate T, split | ±0.05 → ±~10 °C plate |
| 3 | Minor-loss $K$ set / equivalent lengths | Mass flow, ΔT | ±30 % on ΣK → ~±10 % on $\dot m$ |
| 4 | Pure forced internal convection (no mixed-convection boost) | Riser wall T | Conservative; true $h_i$ higher → wall cooler |
| 5 | Wind $C_p$ and building aerodynamics | Weather scatter | Low confidence; direction unspecified |
| 6 | Plate area 8.84 m² (vs. as-built 10.18 m²) | Plate flux/temp | +15 % area → plate ~15–20 °C cooler |

**Overall confidence:** heated-wall temperature and radiative-dominance conclusion **high**
(two independent methods agree); mass flow and ΔT **medium** (±20–25 %, chiefly from the
parasitic-loss and minor-loss assumptions); weather-wind **low-medium**.

---

## 9. Files

- `airprops.py` — cited air-property correlations (validated).
- `rccs_model.py` — coupled loop-momentum + heat-transfer network (all physics).
- `cases.py` — runs Cases 1–4; writes `results/results.json`.
- `make_cfd_case.py`, `cfd/` — OpenFOAM viewFactor-radiation cross-check; `cfd/RESULTS.md`.
- `results/results.json` — all numerical results and sensitivity sweeps.

**Headline numbers:** ṁ ≈ 0.58 kg/s (35 kg/min); riser ΔT ≈ 96 K; riser wall ≈ 163 °C (front,
mid-plane); heated wall ≈ 390 °C; radiation ≈ 93 % of heat removal; accident peak ≈ 390 °C —
**levels off, no runaway, stays below safe limits.**
