# Full-scale RCCS performance — first-principles calculation note

**System:** Full-scale, air-cooled, passive Reactor Cavity Cooling System (RCCS) of an HTGR
(MHTGR-class), **227 vertical riser ducts** around the reactor pressure vessel (RPV).
**Task:** predict, from physics + the sanctioned inputs only, the natural-circulation air flow,
riser temperature rise, and peak vessel-wall temperature at the two design duties — **700 kWt**
(normal) and **1.5 MWt** (peak depressurized-conduction-cooldown decay heat) — at **20 °C ambient**,
and map the ½-scale facility model to full scale.

*All numbers below are produced by `rccs_model.py` / `sensitivity.py` in this directory; raw run
log in `results.txt`. No published performance of the real design was consulted.*

---

## 1. Headline results

| Quantity | **700 kWt (normal)** | **1.5 MWt (peak accident)** |
|---|---|---|
| Total natural-circulation air mass flow | **≈ 10.0 kg/s** (600 kg/min) | **≈ 12.1 kg/s** (725 kg/min) |
| Riser air temperature rise ΔT | **≈ 70 °C** (out ≈ 90 °C) | **≈ 123 °C** (out ≈ 143 °C) |
| Per-duct flow | ≈ 44 g/s | ≈ 53 g/s |
| Riser velocity / Reynolds no. | 4.0 m/s / Re ≈ 1.5×10⁴ | 5.3 m/s / Re ≈ 1.8×10⁴ |
| Peak riser wall temp (front face, top) | ≈ 122 °C | ≈ 201 °C |
| **Peak vessel-wall (RPV) temperature** | ≈ 266 °C | **≈ 378 °C** |
| Radiative fraction of cavity heat transfer | ≈ 0.82 | ≈ 0.90 |

**Safety call (item 3):** at the 1.5 MWt peak the vessel wall reaches **≈ 378 °C**, with a
plausible band of **≈ 360–395 °C** across all assumption sweeps. This is **below the safe
accident limit** for RPV low-alloy steel (≈ **427 °C / 800 °F**, ASME off-normal), with a margin
of ~50 °C, and far below the ~538 °C (1000 °F) metallurgical/short-term ceiling.
**Verdict: SAFE** — the passive RCCS keeps the vessel within limits at peak decay heat.
The estimate is deliberately **conservative** (see §4).

---

## 2. Model — what physics was solved

The RCCS is a single open natural-circulation air loop: cool outdoor/building air (20 °C) is drawn
down the downcomer, enters the bottom of the 227 riser ducts, is heated over the 13.86 m heated
length by radiation from the hot vessel across the cavity, becomes buoyant, rises through the
outlet plenum and chimney, and discharges high above. Three coupled balances are solved
self-consistently by iterating on total mass flow ṁ:

**(a) Loop momentum balance (drives the flow).** Buoyancy head = friction + form losses:

  ΔP_buoy = g·[(ρ_amb − ρ_riser,mean)·L_heated + (ρ_amb − ρ_out)·H_chimney]
  ΔP_loss = ½·ρ·V²·(f·L_riser/D_h + ΣK)

with f from the Colebrook correlation (steel roughness ε≈0.05 mm; turbulent, Re≈1.5–1.8×10⁴), and
form losses ΣK = 2.5 (0.5 duct-inlet contraction + 1.0 duct-exit expansion into plenum + 1.0 lumped
plena/bends/chimney/discharge kinetic-energy loss, referenced to riser velocity). The riser (small
D_h = 0.071 m) dominates the resistance; f·L/D_h ≈ 6 vs ΣK = 2.5.

**(b) Energy balance:** Q = ṁ·c_p·ΔT, c_p evaluated at the mean gas temperature.

**(c) Heat-transfer chain to the wall** (at the top / peak axial station, uniform axial flux):
- Internal convection, **Dittus–Boelter** Nu = 0.023 Re⁰·⁸Pr⁰·⁴ → h ≈ 18–21 W/m²K.
  Riser inner wall T_wall = T_air + q″_wet/h, using the perimeter-averaged internal flux
  q″_wet = Q/(N·P_wet·L_heated); front face taken 1.5× hotter (radiation lands on the narrow
  front face, thin high-k tube conducts circumferentially).
- **Two-surface radiation across the cavity** (plate ε=0.79, riser ε≈0.80 assumed):
  q″_plate = σ(T_p⁴ − T_riser⁴)/(1/ε_p + 1/ε_r − 1), with q″_plate = Q/A_heated (A_heated = 311.2 m²).
  Solved for T_p (the vessel/plate surface temperature).

**Air properties:** temperature-dependent, from CoolProp at 1 atm (ρ, μ, c_p, k, Pr, β), evaluated
at the mean gas temperature as the facility does.

**Geometry (full-scale, from inputs §2/§5):** N = 227 ducts; duct internal 9.624″×1.624″ →
A_duct = 0.01008 m², P_wet = 0.571 m, D_h = 0.0706 m; L_heated = 13.86 m; total flow area 2.29 m².
Riser friction length scaled from the facility's total/heated ratio → 15.2 m.

**Key assumption — chimney/discharge height (not given for the real plant, item "where not
given").** The buoyancy column height above the riser inlet was set to **H = 40 m**, obtained by
scaling the facility's 19.6 m baseline discharge by the total-height ratio 55.2/26 (≈ 2.12) — i.e.
19.6 × 2.12 ≈ 41.6 m, rounded to 40 m. Sensitivity H = 30–50 m is reported in §5.

---

## 3. Why the numbers look the way they do (physical checks)

- **Flow barely increases while power doubles.** ṁ rises only 10.0 → 12.1 kg/s (+21%) as Q goes
  700 → 1500 kWt (+114%). This is the natural-circulation signature ṁ ∝ Q^(1/3): buoyancy ∝ ΔT ∝
  Q/ṁ over height H, loss ∝ ṁ² ⇒ ṁ³ ∝ Q·H. Check: (1500/700)^⅓ = 1.29 → 10.0×1.29 = 12.9 kg/s,
  matching the 12.1 kg/s solved (the small shortfall is the higher ΔT lowering hot-column density
  non-linearly). Consequently **ΔT more than doubles** (70 → 123 °C).
- **The cavity is radiation-dominated.** At 1.5 MWt the plate must push 4.82 kW/m² across the gap;
  radiation carries ~90% of it (natural convection in the tall sealed cavity adds only ~0.5 kW/m²).
  This is why the vessel runs hot (378 °C) even though the air only reaches 143 °C — the ~177 °C
  plate-to-riser radiative ΔT is set by the T⁴ law at that flux, essentially independent of the
  flow loop.
- **Self-consistent radiation:** σ(651⁴ − 474⁴)/1.516 = 4.82 kW/m² = Q/A_heated. ✓

---

## 4. Assumptions & confidence per number

| # | Result | Confidence | Basis / dominant uncertainty |
|---|---|---|---|
| 1 | **Mass flow 10 / 12 kg/s** | **Medium–High (±20%)** | Set by ṁ∝(Q·H)^⅓, so **cube-root-insensitive** to loss-coefficient and height errors: a ±50% error in ΣK or H moves ṁ by only ~±15% (see §5). Both loads are firmly turbulent, so Dittus–Boelter / Colebrook apply. Main lever is the assumed 40 m chimney height. |
| 2 | **ΔT 70 / 123 °C** | **Medium–High (±20%)** | Follows directly from ṁ via the exact energy balance; inherits the flow uncertainty (inversely). |
| 3 | **Peak vessel wall 266 / 378 °C** | **High on the SAFE call; Medium on the exact value (±25 °C)** | Radiation-dominated ⇒ almost independent of the flow loop; ±50 °C air-temp error → only ~±15 °C wall. Conservative: (a) neglects the parallel cavity-convection path that would *lower* T_p; (b) neglects vessel heat loss to insulated side/back walls; (c) uses the hot top station and a 1.5× front-face peaking factor. Sensitive to riser emissivity (367–391 °C for ε 0.7–0.9) and the safe-limit choice. |
| 4 | **Radiative fraction 0.82 / 0.90** | **Medium** | Cavity natural-convection Nu correlation for a tall enclosure is approximate; the split is a secondary reported quantity. |
| — | **20 °C ambient; Q split evenly over ducts; uniform axial flux; 1 atm** | assumptions stated in TASK/inputs | Azimuthal/axial power shaping (input Case 4) would raise local peak wall ~10–15% where peaked. |

**Safe-limit assumption:** HTGR RPVs are low-alloy steel (SA-508/SA-533 class, or 2¼Cr–1Mo in
higher-temperature designs). Taking the conservative ASME off-normal/accident service limit ≈
**427 °C (800 °F)**, with normal-duty limit ≈ 371 °C (700 °F) and a short-term metallurgical
ceiling ≈ 538 °C (1000 °F). The 378 °C peak clears the 427 °C accident limit by ~50 °C; the 266 °C
normal-duty result is well under 371 °C. (These are generic steel service temperatures, not the
plant's published design limits.)

---

## 5. Sensitivity (bounding the answers)

**Discharge/buoyancy height H (the largest single assumption):**

| H | ṁ (700/1500 kW) | ΔT (700/1500) | T_plate (700/1500) |
|---|---|---|---|
| 30 m | 8.7 / 10.5 kg/s | 80 / 142 °C | 272 / **389 °C** |
| **40 m (baseline)** | 10.0 / 12.1 kg/s | 70 / 123 °C | 266 / **378 °C** |
| 50 m | 11.0 / 13.4 kg/s | 63 / 111 °C | 263 / **372 °C** |

Even the pessimistic 30 m case gives 389 °C < 427 °C → **the SAFE verdict is robust to this
assumption.** Riser emissivity 0.7/0.8/0.9 → T_plate 391/378/367 °C at 1.5 MWt. Ambient −18→+24 °C
→ T_plate 358→380 °C (colder air = denser, more flow, cooler wall). All variants stay < 427 °C.

---

## 6. Scaling argument — ½-scale facility → full scale (item 4)

The facility is a **top-down (reduced-height) ½-axial-scale, 12-duct/19.03° sector** model. The
same solver run on the facility geometry (N=12, L_heated=6.82 m, H=19.6 m, scaled powers) predicts:

| Facility duty | ṁ | ΔT | V (riser) | Re |
|---|---|---|---|---|
| 26.16 kWt (norm) | 0.43 kg/s | 60 °C | 3.3 m/s | 1.3×10⁴ |
| 56.07 kWt (peak) | 0.53 kg/s | 105 °C | 4.3 m/s | 1.5×10⁴ |

**Dimensionless groups — what is preserved and what is not:**

- **Preserved by design:**
  - *Geometric similarity of the flow channel* — duct cross-section, wall thickness and D_h are
    **kept 1:1**. Same hydraulic diameter ⇒ same near-wall flow character.
  - *Prandtl number* — same working fluid (atmospheric air), so Pr ≈ 0.71 identically; convective
    correlations transfer directly.
  - *Richardson / Froude number (buoyancy ↔ inertia)* — the top-down rules force velocity ∝ √l_R
    (0.707) and heights ∝ l_R (0.5), which holds the ratio (gβΔT·H)/V² ≈ constant. My independent
    solve gives facility/full **velocity ratio ≈ 0.81** and **Re ratio ≈ 0.83** — close to the
    intended 0.707, confirming the buoyancy–inertia balance is approximately reproduced (the small
    excess comes from the deliberate ×1.414 heat-flux boost, which raises facility ΔT and thus its
    buoyancy relative to a pure geometric scale).
  - *Radiation–conduction coupling* — wall heat flux is intentionally scaled ×l_R^−0.5 = 1.414 so
    the T⁴ radiation cavity behaves similarly; both facility and full-scale sit in the same
    radiation-dominated regime (radiative fraction 0.8–0.9 in both).

- **NOT preserved:**
  - *Reynolds number* — scales as √l_R ≈ 0.707, so the facility runs at ~0.7–0.8× full-scale Re.
    **Both remain firmly turbulent (Re > 10⁴)**, so the same f and Nu correlations apply to each;
    the friction factor is only modestly higher and Nu modestly lower at the facility's lower Re.
    This is the main similarity distortion, and it is small.
  - *Absolute buoyancy head / power / area* — sector + reduced height, so absolute magnitudes are
    not similar (handled by the flux boost, above).
  - *Transient time scale* — the accident transient is scaled separately (facility peak at 84.85 h
    vs full-scale 120 h); steady-state predictions here are unaffected.
  - *Parasitic heat-loss fraction* — surface-to-volume ratio is larger in the small facility, so
    its relative structural losses differ from full scale (not quantified in inputs).

**Effect on confidence.** Because (i) the flow channel is a true 1:1 slice, (ii) the fluid and
hence Pr are identical, and (iii) *both* scales are turbulent so the *same* correlations govern
each, the extrapolation of **mass flow and ΔT is trustworthy to ~±20%**. The one broken group
(Reynolds) is a mild distortion within a single flow regime, not a regime change. The **peak
vessel-wall temperature is the most confident output**: it is set by the radiative cavity balance
at a fixed heat flux, which is nearly independent of the loop flow and is faithfully reproduced by
the ×1.414 flux-scaling of the facility. Hence the **SAFE margin (~50 °C below the 427 °C accident
limit) is robust** across every assumption swept here.

---

## 7. Bottom line

At full scale the 227-duct passive RCCS moves **≈ 10 kg/s** of air at the 700 kWt normal duty
(ΔT ≈ 70 °C) and **≈ 12 kg/s** at the 1.5 MWt peak-accident decay-heat duty (ΔT ≈ 123 °C), purely
by natural circulation. The peak vessel wall reaches **≈ 378 °C**, comfortably below the ~427 °C
accident service limit for RPV steel. **The system is predicted to keep the vessel safe at peak
decay heat, with margin, and the conclusion is robust to the stated modelling assumptions.**
