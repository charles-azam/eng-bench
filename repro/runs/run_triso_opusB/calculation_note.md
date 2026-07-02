# Calculation note — TRISO particle failure and fission-product release under accident heating

**Scope.** Predict, for the five accident-heating cases in `inputs/02_cases.md` (A1, A2, B, C1, C2):
(1) the number of coated particles that fail during heating and when; (2) the final fractional
release of Kr-85 and Cs-137 from the element; (3) a severity ranking with the temperature and
burnup reasoning behind it. Everything is derived offline from `inputs/` plus standard fission
physics. Correlations are cited to the annex (`inputs/03_material_properties.md`, "§n") and to
TECDOC-1674 equation numbers where the annex gives them. The working model is `output/model.py`.

---

## 1. Method and model chain

A coated particle fails, in the sense that matters for release, when its **SiC layer** loses
integrity — SiC is the gas pressure boundary and the diffusion barrier for metallic fission
products (§ Inputs-01). Two release channels then follow:

- **Kr-85 (fission gas).** Intact SiC is an essentially perfect gas barrier, so gas release is
  controlled by the *failed fraction*: each failed particle exposes a bare kernel that dumps
  almost all of its gas quickly at accident temperature (verified below). Hence
  **F(Kr-85) ≈ (failed fraction) × F_gas,bare-kernel ≈ failed fraction.**
- **Cs-137 (metallic).** Cs escapes a *failed* particle rapidly through the bare kernel, but it
  also leaks slowly out of *intact* particles by solid-state diffusion through the SiC (§5).
  Hence **F(Cs-137) = (failed frac)·1 + (intact frac)·F_Cs,SiC**, and for these cases the intact
  SiC-diffusion term dominates because the failed fraction is small.

The failure count is obtained from an internal-pressure / SiC-stress / Weibull chain:

1. **Fission inventory** per kernel = burnup(FIMA) × initial U atoms/kernel (geometry + kernel
   density, Inputs-01). Noble-gas atoms = 0.31 × fissions (standard cumulative Xe+Kr yield for
   LEU UO₂ — supplied as physics, not looked up for these tests).
2. **Free volume** = buffer pore volume, from buffer density vs. a 2.10 Mg/m³ dense-PyC basis
   (porosity ≈ 52 %). The buffer is the designed gas plenum (Inputs-01; §1 buffer convention).
3. **Internal pressure** P = nRT/V_free at the peak set-point (ideal gas; CO treated as a
   multiplier on the gas moles — see §5 of this note and the uncertainty discussion).
4. **SiC tangential stress** by the thin spherical-shell membrane formula
   σ_θ = P·r_m/(2·t_SiC), with r_m the mean SiC radius and t_SiC = 36 µm (Inputs-01). Taking the
   SiC to carry the full pressure load is conservative (the IPyC/OPyC share it when intact); it is
   the appropriate bound once IPyC has cracked under irradiation, which is expected at these
   fluences.
5. **Failure probability** from Weibull statistics (§3): P_f = 1 − exp[−(σ_θ/σ₀)^m], with
   m = 8.02 and characteristic strength σ₀ = 873 / Γ(1+1/m) = 925.8 MPa (converting the quoted
   *mean* strength 873 MPa). Expected failures = P_f × N_particles.

**Correlations used:** Weibull failure (§3); Cs-in-SiC diffusion Eq 10.9 (§5); kernel reduced
diffusion coefficients Table 7.1 (§4); equivalent-sphere release Eqs 10.7–10.8 (§6); one-particle
Kr-85 detection thresholds (§8). Elastic constants (§1) enter only through the load-sharing
argument in step 4.

### 1.1 Key intermediate quantities (from `model.py`)

| Case | Element | N_part | Burnup %FIMA | Peak T (°C) | t at peak (h) | fissions/kernel | free vol (m³) |
|---|---|---|---|---|---|---|---|
| A1 | K3/1 sphere | 16 400 | 7.7 | 1600 | 500 | 1.19×10¹⁷ | 5.45×10⁻¹¹ |
| A2 | K3/3 sphere | 16 400 | 10.2 | 1800 | 100 | 1.58×10¹⁷ | 5.45×10⁻¹¹ |
| B  | K6/3 sphere | 14 580 | 10.9 | 1800 | 400 (staged) | 1.79×10¹⁷ | 6.19×10⁻¹¹ |
| C1 | P4/3-7 compact | 1 631 | 13.9 | 1600 | 304 | 2.15×10¹⁷ | 5.45×10⁻¹¹ |
| C2 | P4/1-12 compact | 1 631 | 11.1 | 1600 | 304 | 1.72×10¹⁷ | 5.45×10⁻¹¹ |

Sanity check: 16 400 × 1.55×10¹⁸ U atoms/kernel ⇒ 10.0 g HM/sphere vs. 10.22 g quoted (Inputs-01) — ✓.

---

## 2. Bare-kernel (failed-particle) release — why F(Kr)≈failed fraction and failed Cs≈1

Using the reduced kernel coefficients (§4) in the equivalent-sphere solution (§6):

| Condition | D′_gas·t | F_gas | D′_Cs·t | F_Cs |
|---|---|---|---|---|
| 1600 °C, 500 h | 0.41 | 0.99 | 2.4 | ~1.0 |
| 1800 °C, 100 h | — | 0.93 | 1.8 | ~1.0 |
| 1600 °C, 304 h | 0.25 | 0.95 | 1.5 | ~1.0 |

So a particle whose SiC has failed releases ≳93 % of its Kr-85 and essentially all its Cs-137
within the hold. This is why gas release is a near-direct count of failed particles, and why the
*failed-particle* Cs contribution equals the failed fraction.

---

## 3. Cs-137 release through *intact* SiC (the dominant Cs channel)

Cs leaks through intact SiC by solid-state diffusion (§5, Eq 10.9). The annex anchors
D_Cs,SiC(1600 °C) = 1.01×10⁻¹⁶ m²/s; the dominant (Q = 125 kJ/mol) term of Eq 10.9 gives the
temperature scaling:

| T (°C) | D_Cs,SiC (m²/s) | breakthrough lag L²/6D (h), L=36 µm |
|---|---|---|
| 1600 | 1.01×10⁻¹⁶ | 594 |
| 1700 | 1.52×10⁻¹⁶ | 396 |
| 1800 | 2.19×10⁻¹⁶ | 274 |

*(Note: substituting T directly into Eq 10.9 as printed gives ≈1.8×10⁻¹⁷ at 1600 °C; the annex's
recommended anchor 1.01×10⁻¹⁶ is ~5× higher. I use the explicitly stated anchor 1.01×10⁻¹⁶ and
scale it Arrhenius-wise — this is one of the noted uncertainties.)*

I model the intact particle as a well-mixed kernel reservoir (kernel diffusion is fast at
accident T, §2 above) behind the resistive SiC shell. A mass balance across the spherical shell
(inner radius r₁ = inner-SiC, outer r₂ = outer-SiC) gives first-order release with time constant
τ = V_kernel·(1/r₁ − 1/r₂)/(4π·D_Cs,SiC), so F_Cs,SiC = 1 − exp(−Σ tᵢ/τᵢ) summed over schedule
segments. Results (τ(1600 °C) ≈ 3150 h):

| Case | segments used | F_Cs,SiC (reservoir, upper estimate) |
|---|---|---|
| A1 | 1600/500 h | 0.147 |
| A2 | 1800/100 h | 0.067 |
| B  | 1600/100 + 1700/100 + 1800/400 h | 0.297 |
| C1 | 1600/304 h | 0.092 |
| C2 | 1600/304 h | 0.092 |

**Two robust physics results fall out of this, independent of the absolute magnitude:**

- **The long 1600 °C hold (A1, 500 h) leaks more Cs than the short 1800 °C hold (A2, 100 h).**
  Cumulative diffusion scales as D·t; A1's D·t (1.8×10⁻¹⁰) beats A2's (7.9×10⁻¹¹) by ~2.3× even
  though A2 is 200 °C hotter, because A2's hold is 5× shorter. Time wins here.
- **Only case B clearly passes the SiC breakthrough lag.** At 1800 °C the lag is 274 h; B holds
  400 h at 1800 °C (100 + 300), so ~130 h of established through-diffusion occurs. A1/A2/C1/C2 all
  hold *below* their breakthrough lag (500<594, 100<274, 304<594), so their true releases sit
  toward the *lower* end of the reservoir estimate (a few %), whereas B's is genuinely large.

I therefore report the reservoir value as an **upper estimate** and give a lag-aware **best
estimate** (roughly: below-breakthrough cases → a few %, B → ~20–30 %).

---

## 4. Internal pressure, SiC stress and failure count

Peak-condition results (best estimate uses CO ≈ noble gas, i.e. total gas moles = 2× fission
gas — see §5/uncertainty):

| Case | P (MPa) | σ_θ SiC (MPa) | P_f (per particle) | Expected failures |
|---|---|---|---|---|
| A1 | 35 | 196 | 3.8×10⁻⁶ | 0.06 |
| A2 | 52 | 287 | 8.3×10⁻⁵ | 1.4 |
| B  | 51 | 294 | 1.0×10⁻⁴ | 1.5 |
| C1 | 63 | 354 | 4.4×10⁻⁴ | 0.7 |
| C2 | 51 | 282 | 7.2×10⁻⁵ | 0.1 |

Bracketing on the CO assumption (the single biggest lever):

| Case | failures, no CO (gas only) | failures, CO = gas (best est.) |
|---|---|---|
| A1 | 0.00 | 0.06 |
| A2 | 0.01 | 1.4 |
| B  | 0.01 | 1.5 |
| C1 | 0.00 | 0.7 |
| C2 | 0.00 | 0.1 |

**Reading of the mechanics.** Peak SiC stress (196–354 MPa) stays well below the 873 MPa mean
strength in every case, so overpressure failure lives in the *lower Weibull tail*. The tail is
extremely sensitive: C1 (highest burnup, 13.9 %) has the highest per-particle P_f (4×10⁻⁴,
because burnup sets the gas inventory and hence the pressure), but the compact holds only 1631
particles, so its expected count (~0.7) is below the 16 400-particle spheres A2/B (~1.5) despite
their lower per-particle P_f. Burnup drives *per-particle* risk; population size drives *counts*.

**Onset / timing.** Failure risk tracks the instantaneous P·T product, so it is concentrated at
the hottest set-point and accumulates over the hold as any SiC thermal degradation proceeds:
- A1 — no failure expected; any single failure would be late in the 1600 °C/500 h hold.
- A2 — during the 1800 °C segments (first reached after the 12 h ramp; risk over the 100 h total).
- B — in the **1800 °C phases (phases 3 and 4)**, especially the 300 h fourth phase; negligible in the 1600/1700 °C phases.
- C1, C2 — during the 1600 °C/304 h hold (C1 earlier/more likely than C2 by burnup).

---

## 5. Final predictions per case

Kr-85 threshold reminder (§8): one failed particle ≈ **6×10⁻⁵** for a sphere, **6×10⁻⁴** for a
compact. Cs-137 release below is failed-fraction + intact-SiC diffusion (§3), best estimate with
the lag caveat; reservoir upper estimate in parentheses.

### Case A1 — K3/1 sphere, 1600 °C / 500 h, 7.7 % FIMA
- **Failures:** ~**0** (0.00–0.1 expected). No onset expected; the schedule is the mildest
  (lowest burnup, 1600 °C). *Confidence: high* that it is ≤1 particle.
- **Kr-85:** ≈ **4×10⁻⁶** — below the 6×10⁻⁵ one-particle threshold ⇒ consistent with zero
  heating-induced failures. *Confidence: high.*
- **Cs-137:** best estimate **~5–15 %** (reservoir 0.147); the 500 h hold sits right at the
  1600 °C breakthrough lag (594 h), so release is near onset of breakthrough. *Confidence:
  low–medium* on magnitude, medium that it exceeds A2.

### Case A2 — K3/3 sphere, 1800 °C / 100 h, 10.2 % FIMA
- **Failures:** ~**1** particle (0.0–1.4). Onset during the 1800 °C segments. The 1800 °C
  exposure adds a real SiC thermal-degradation risk not captured by the pressure model, so treat
  ~1 as a lower bound. *Confidence: medium.*
- **Kr-85:** ≈ **8×10⁻⁵** — just above the 6×10⁻⁵ threshold ⇒ ~1 detectable failed particle.
  *Confidence: medium.*
- **Cs-137:** best estimate **~1–3 %** (reservoir 0.067); held far below the 274 h breakthrough
  lag, so Cs is suppressed despite 1800 °C. *Confidence: low–medium.* This is the **lowest Cs
  release of the five** — the short hold beats the high temperature.

### Case B — K6/3 sphere, staged, 1800 °C total 400 h, 10.9 % FIMA  ← most severe
- **Failures:** ~**1–3** particles. Onset in **phases 3–4 (1800 °C)**, growing through the 300 h
  fourth phase. Pressure model gives ~1.5; the 400 h at 1800 °C adds the most cumulative
  thermal-degradation exposure of any case, so the upper end is credible. *Confidence: medium.*
- **Kr-85:** ≈ **1×10⁻⁴** (≈1.5 particles above the 6×10⁻⁵ threshold). *Confidence: medium.*
- **Cs-137:** best estimate **~20–30 %** (reservoir 0.297) — **the largest of the five**, and the
  only case that clearly passes the SiC breakthrough lag (400 h > 274 h at 1800 °C).
  *Confidence: medium* on ranking, low–medium on magnitude.

### Case C1 — P4/3-7 compact, 1600 °C / 304 h, 13.9 % FIMA
- **Failures:** ~**0–1** particle (0.7 expected). **Highest per-particle failure probability of
  all** (4×10⁻⁴) because it has the highest burnup ⇒ highest gas inventory ⇒ highest pressure;
  but only 1631 particles cap the count. Onset during the 1600 °C hold. *Confidence: medium.*
- **Kr-85:** ≈ **4×10⁻⁴** — below the compact 6×10⁻⁴ one-particle threshold ⇒ ~0–1 failed
  particle, marginal detectability. *Confidence: medium.*
- **Cs-137:** best estimate **~2–9 %** (reservoir 0.092); below the 594 h breakthrough lag.
  *Confidence: low–medium.* Note the compact's absolute inventory is small (0.1 g U-235), so a
  given fraction is far less activity than from a sphere.

### Case C2 — P4/1-12 compact, 1600 °C / 304 h, 11.1 % FIMA
- **Failures:** ~**0** (0.0–0.1). Lower-burnup twin of C1; lower pressure ⇒ ~6× lower
  per-particle P_f. Onset unlikely. *Confidence: medium–high* that it is ≤1.
- **Kr-85:** ≈ **7×10⁻⁵** — well below the compact 6×10⁻⁴ threshold ⇒ zero detectable failures.
  *Confidence: medium.*
- **Cs-137:** best estimate **~2–9 %** (reservoir 0.092), essentially the same diffusion path as
  C1 (same T, t); slightly less activity by lower inventory. *Confidence: low–medium.*

**C1 vs C2 (the designed burnup isolation):** identical geometry and heating, so the intact-SiC
Cs *fraction* is the same; the burnup difference (13.9 vs 11.1 %) shows up as ~6× higher
per-particle failure probability and ~25 % more fission-product inventory (activity) in C1. This
is the clean demonstration that **burnup raises particle-failure risk through internal pressure**,
holding temperature fixed.

---

## 6. Ranking — which case suffers most, and why

Severity depends on the metric; the drivers are **temperature × time** (for the diffusive Cs
release and for SiC degradation) and **burnup** (for gas inventory → pressure → failure).

- **Particle failures / Kr-85 release:** **B ≳ A2 > C1 > C2 > A1.** The 1800 °C spheres (B, A2)
  top the count because high temperature maximises pressure *and* they hold 16 400/14 580
  particles; B edges A2 on longer 1800 °C time and higher burnup. C1 has the highest *per-particle*
  probability (highest burnup) but a small population.
- **Cs-137 fractional release:** **B ≫ A1 ≳ C1 ≈ C2 > A2.** Set by cumulative D·t through intact
  SiC: B is the only case past the breakthrough lag; A1's long 1600 °C hold beats the short, hot
  A2; the C pair sits in between.
- **Absolute released activity (Bq):** inventory scales with burnup × HM loading (§8). Spheres
  carry ~10× the HM of a compact, so **B** (high burnup sphere, large Cs fraction) releases the
  most Cs-137 activity; **A2** is next for Cs activity; the C compacts, despite high burnup, hold
  little total inventory.

**Overall most severe: Case B** — highest cumulative high-temperature dose (1800 °C for 400 h,
staged), high burnup (10.9 %), sphere population; it maximises *both* failures/Kr and Cs release.
**Least severe: Case A1** for failures/Kr (lowest burnup, 1600 °C), and **A2** for Cs fraction
(shortest hold). This is the temperature/burnup story in one line: **temperature (and time at it)
governs Cs and drives failures; burnup governs the gas inventory that pressurises the SiC and thus
the per-particle failure probability.**

---

## 7. Assumptions and the most uncertain one

Assumptions (each flagged in-text): SiC-only load-bearing thin shell (conservative on stress);
noble-gas yield 0.31/fission; buffer void from a 2.10 Mg/m³ dense-PyC basis; ideal gas; kernel as
a well-mixed reservoir behind the SiC for Cs; Weibull mean→characteristic conversion; Γ = 2 in
Eq 10.9; SiC thermal decomposition/kernel-migration/Pd-corrosion at 1800 °C discussed but **not
modelled** (no kinetics in the annex) — this makes the A2/B failure counts lower bounds.

**Most uncertain assumption: the CO (oxide) contribution to internal pressure.** The annex gives
no CO/oxygen-release correlation, yet CO from fissioned UO₂ can roughly double the gas moles at
high burnup. With no CO the pressure model predicts essentially **zero** failures in every case;
with CO ≈ the noble-gas amount it predicts ~1–1.5 in the hot/high-burnup cases. The absolute
failure count therefore swings by 1–2 orders of magnitude on this one input. The *rankings* above
are robust to it (they rest on temperature-time and burnup ordering), but the absolute failure
numbers carry **low confidence**. The second-largest uncertainty is the Cs-in-SiC release model
(reservoir upper bound vs. lag-limited lower bound → ~5× on the Cs fraction), compounded by the
noted ~5× inconsistency between Eq 10.9 as printed and its stated 1600 °C anchor.

---

### Appendix — reproducibility
All numbers are produced by `output/model.py` (pure-Python, no external data). Confidence tags:
*high* = robust to modelling choices; *medium* = correct ordering, magnitude uncertain within ~2–3×;
*low* = order-of-magnitude only. Fractional releases are per-element (whole fuel element) values.
