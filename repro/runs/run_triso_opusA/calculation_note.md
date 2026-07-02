# Calculation Note — TRISO particle failure and fission-product release under accident heating

**Scope.** Predict, for the five furnace-heating cases of `inputs/02_cases.md`
(A1 = HFR-K3/1, A2 = HFR-K3/3, B = HFR-K6/3, C1 = HFR-P4/3-7, C2 = HFR-P4/1-12):
(1) the number of coated particles that fail during heating and when; (2) the final fractional
release of Kr-85 and Cs-137 from the element; (3) a severity ranking with the temperature/burnup
reasoning. Every number is derived offline from first principles and the property annex
(`inputs/03_material_properties.md`, TECDOC-1674). No experimental results were consulted.

Working model and all numbers are reproducible from `output/triso_calc.py`.

---

## 1. Physical picture and strategy

A TRISO particle releases essentially nothing while its **SiC layer is intact**, with one crucial
exception: **caesium slowly diffuses through solid SiC**, whereas **fission gas (Kr) does not**.
This asymmetry organises the whole prediction:

- **Kr-85** (and all noble gas) escapes an element *only* through particles whose SiC has failed.
  A failed kernel then dumps nearly its entire gas inventory at accident temperature. Hence

  > **Kr-85 fractional release ≈ (failed fraction) × (gas released from a bared kernel) ≈ failed fraction.**

  The annex fixes the calibration: one failed particle ⇒ Kr-85 release ≈ 6.1×10⁻⁵ (sphere),
  ≈ 6.1×10⁻⁴ (compact) — the "one-particle detection threshold" (§8).

- **Cs-137** is released by **two parallel paths**: (i) solid-state diffusion through the *intact*
  SiC of every particle (Eq 10.9), and (ii) prompt release from any *failed* particle. Because
  path (i) operates on the whole population, **Cs-137 release is typically orders of magnitude
  larger than Kr-85 release** and is the governing dose/contamination term here.

So the calculation splits into: **(A) how many SiC layers fail** (a mechanics/Weibull problem),
and **(B) diffusive release** through intact SiC (Cs) and from any failed kernels (Kr + Cs).

---

## 2. Failure model (SiC as a pressure vessel)

At 1600–1800 °C there is **no temperature gradient** in a furnace, so gradient-driven mechanisms
(kernel migration/"amoeba") are inactive; SiC thermal decomposition needs >~2000 °C and is also
inactive at ≤1800 °C. The operative failure mode is **over-pressurisation of the SiC shell** by
fission gas + CO, judged against the SiC strength distribution.

**Gas inventory.** Fissions per particle N_f = (%FIMA)·N_HM, with N_HM = (HM_loading/N_particles)/238·N_A.
Free-gas source terms: stable+long-lived Xe+Kr yield **Y_gas = 0.31/fission**; CO from excess
oxygen **Y_CO = 0.15/fission** (order-of-magnitude; see §7). The gas fraction actually released
from the kernel into the buffer void is tracked by the equivalent-sphere solution (Eq 10.8) with
the "stable/long-lived gas" kernel coefficient (Table 7.1: D₀′=5×10⁻³ s⁻¹, Q=155.4 kJ/mol),
integrated over the schedule; at ≥1600 °C for tens–hundreds of hours it reaches ≈0.9–1.0.

**Void volume.** Buffer shell only, at its measured low density:
V_void = (1 − ρ_buffer/2.10)·(4/3)π(r_buffer³ − r_kernel³) ≈ **5.4×10⁻¹¹ m³** (spheres/compacts,
batch 2308), **6.2×10⁻¹¹ m³** (K6). Buffer porosity ≈ 0.52.

**Pressure & SiC stress.** Ideal gas P = nRT/V_void. Thin spherical shell membrane tension
(SiC carries the load; it is ~9× stiffer than PyC):

  σ_θ = P·r_m/(2·t_SiC),  r_m = mean SiC radius ≈ 4.0×10⁻⁴ m, t_SiC = 36 µm.

**Residual compression.** Under irradiation IPyC/OPyC shrinkage put the SiC into compression;
this is *subtracted* from σ_θ. It is modelled as growing with fluence (~σ ∝ Φ²) up to a few
hundred MPa and thermally annealing above 1500 °C — an engineering estimate, deliberately
conservative (small). Even setting it to zero does not change any conclusion (see §6).

**Weibull.** SiC characteristic (scale) strength from the mean and modulus (Table 9.14,
mean 873 MPa, m = 8.02): σ₀ = 873/Γ(1+1/8.02) = **927 MPa**. Per-particle failure probability
P_f = 1 − exp[−(σ_net/σ₀)^m]; expected failures = P_f × N_particles, evaluated at the most severe
schedule phase (onset = first phase reaching that stress).

### Computed stresses and failure probabilities

| Case | Peak T (°C) | Free gas F | P (MPa) | σ_θ net (MPa) | P_f / particle | **E[N_fail]** | onset |
|---|---|---|---|---|---|---|---|
| A1 | 1600 | 0.99 | 26 | 127 | 1.2×10⁻⁷ | **0.002** | — |
| A2 | 1800 | 0.94 | 39 | 195 | 3.7×10⁻⁶ | **0.06**  | 1800 °C phase |
| B  | 1800 | 1.00 | 38 | 204 | 5.3×10⁻⁶ | **0.08**  | 1800 °C phases |
| C1 | 1600 | 0.95 | 46 | 184 | 2.3×10⁻⁶ | **0.004** | — |
| C2 | 1600 | 0.95 | 37 | 166 | 1.0×10⁻⁶ | **0.002** | — |

**Key result:** net SiC stresses (127–204 MPa) sit at only ~14–22 % of the 927 MPa scale
strength. On the m = 8.02 Weibull curve this puts every case in the deep tail: **the expected
number of heating-induced SiC failures is below 0.1 particle in all five cases.** There is **no
coherent failure population** in any element. This is the robust, physically-correct outcome for
this well-fabricated LEU UO₂ TRISO fuel at ≤1800 °C — pressure alone cannot break these shells at
these burnups.

---

## 3. Fission-product release

**Cs through intact SiC.** Cs is fast in the kernel (Table 7.1: D′_Cs = 0.9·e^(−209000/RT),
giving D′t ≫ 0.15 — the kernel empties into the SiC), so the **SiC controls**. Using Eq 10.9
anchored to the annex reference value **D_Cs,SiC(1600 °C) = 1.011×10⁻¹⁶ m²/s** (Γ = 2), scaled by
its Arrhenius form (Q = 125 kJ/mol) to other temperatures, and the equivalent-sphere solution
(Eq 10.7/10.8) with reduced coefficient D_Cs,SiC/r_m², **integrated over the full staircase**
(τ = ∫D′dt), gives the intact-particle Cs release fraction.

**Gas / Cs from failed particles.** A bared kernel releases gas via the stable-gas coefficient
and Cs via the kernel Cs coefficient; both reach ≈0.95–1.0 over these holds.

**Element release** (ff = failed fraction ≈ E[N_fail]/N):
- Kr-85: F_Kr = ff · F_gas,failed ≈ ff.
- Cs-137: F_Cs = ff · F_Cs,failed + (1 − ff) · F_Cs,intact ≈ F_Cs,intact (since ff ≪ 1).

| Case | τ(Cs,SiC) | **F_Cs,intact** | **Kr-85 release** | **Cs-137 release** |
|---|---|---|---|---|
| A1 | 1.14×10⁻³ | 0.111 | 1.2×10⁻⁷ | **0.11** |
| A2 | 5.42×10⁻⁴ | 0.077 | 3.5×10⁻⁶ | **0.077** |
| B  | 2.39×10⁻³ | 0.158 | 5.3×10⁻⁶ | **0.16** |
| C1 | 6.99×10⁻⁴ | 0.087 | 2.2×10⁻⁶ | **0.087** |
| C2 | 6.99×10⁻⁴ | 0.087 | 9.9×10⁻⁷ | **0.087** |

- **Kr-85 is at or below the one-particle detection threshold in every case** (6.1×10⁻⁵ sphere,
  6.1×10⁻⁴ compact). Per the annex, such levels are "consistent with zero heating-induced
  failures." The numbers quoted are the *expectation* ff·F — i.e. the probability-weighted signal
  of a fractional chance of a single failure, not a resolved release.
- **Cs-137 release is 8–16 %**, set almost entirely by diffusion through intact SiC — larger for
  hotter and/or longer exposure. Note A1 (1600 °C but 500 h) exceeds A2 (1800 °C but only 100 h):
  the longer soak beats the higher temperature because √(Dt) rewards time. B is highest (1600 +
  1700 + 1800 °C, 400 h at 1800 °C).

---

## 4. Per-case answers, assumptions, and confidence

**Case A1 — HFR-K3/1, 1600 °C / 500 h, 7.7 % FIMA.**
- Failures: **0 particles** (E ≈ 0.002; probability of even one failure ≈ 0.2 %). No onset.
- Kr-85: **≈1×10⁻⁷** (below threshold ⇒ effectively nil). *Confidence: high.*
- Cs-137: **≈0.11** (11 %). *Confidence: medium* (see §5). The lowest peak temperature but the
  longest hold ⇒ moderate Cs, negligible failure. *Assumption:* SiC-controlled Cs, full gas release.

**Case A2 — HFR-K3/3, 1800 °C / 100 h, 10.2–10.6 % FIMA.**
- Failures: **0 particles most likely**; highest-but-one failure probability (E ≈ 0.06 ⇒ ~6 %
  chance of a single failed particle, which would occur during the 1800 °C phase). *Confidence:
  medium-high on "≈0"; the ~6 % single-failure chance is order-of-magnitude.*
- Kr-85: **≈3×10⁻⁶** (≈0.06 particle-equivalent; below the 6.1×10⁻⁵ threshold). *Confidence: high.*
- Cs-137: **≈0.077** (7.7 %). *Confidence: medium.* Hotter than A1 but far shorter ⇒ slightly less Cs.

**Case B — HFR-K6/3, staged 1600/1700/1800/1800 °C, 400 h at 1800 °C, 10.9 % FIMA.**
- Failures: **0 particles most likely**; the **highest** failure probability of the set
  (E ≈ 0.08 ⇒ ~8 % chance of one failed particle), onset in the 1800 °C phases. *Confidence:
  medium-high on "≈0"; single-failure chance order-of-magnitude.*
- Kr-85: **≈5×10⁻⁶** (below the 6.9×10⁻⁵ threshold). *Confidence: high.*
- Cs-137: **≈0.16** (16 %) — **the largest release**, from the longest cumulative time at the
  highest temperatures. *Confidence: medium.* *Assumption:* Cs diffusion integrated over all four
  phases including 1600/1700 °C legs.

**Case C1 — HFR-P4/3-7 compact, 1600 °C / 304 h, 13.9 % FIMA (highest burnup).**
- Failures: **0 particles** (E ≈ 0.004). No onset. Highest burnup ⇒ highest gas inventory and
  pressure (46 MPa), but 1600 °C keeps stress (184 MPa) far below strength. *Confidence: high on "0".*
- Kr-85: **≈2×10⁻⁶** (well below the 6.1×10⁻⁴ compact threshold). *Confidence: high.*
- Cs-137: **≈0.087** (8.7 %). *Confidence: medium.*

**Case C2 — HFR-P4/1-12 compact, 1600 °C / 304 h, 11.1 % FIMA (lower burnup).**
- Failures: **0 particles** (E ≈ 0.002). Same schedule as C1, less gas ⇒ lower stress. *Confidence: high.*
- Kr-85: **≈1×10⁻⁶** (below threshold). *Confidence: high.*
- Cs-137: **≈0.087** (8.7 %). Cs source term is set by temperature/time (identical to C1), so the
  *fractional* Cs release matches C1; C1 releases more Cs-137 *in absolute activity* because its
  inventory is ~25 % larger (higher burnup — see §6). *Confidence: medium.*

---

## 5. Most uncertain assumption

**The effective diffusion length (model form) for Cs transport through the SiC shell.**
The failure conclusion ("≈0 particles fail; Kr below detection") is *robust* — stresses would have
to rise ~4–5× to matter, and even zeroing the residual compression or doubling the gas/CO source
leaves σ_θ ≲ 400 MPa, still deep in the Weibull tail. What is genuinely uncertain is the **Cs-137
magnitude**. I modelled the intact particle as an equivalent sphere with reduced coefficient
D_Cs,SiC/r_m². A thin-shell permeation treatment, or using the kernel radius instead of the mean
SiC radius, would shift F_Cs by roughly a factor of √2 either way. **The Cs-137 releases above
therefore carry a ~×0.5–2 band** (≈4–30 %). A secondary uncertainty is the anchoring of Eq 10.9:
the annex's stated 1.011×10⁻¹⁶ m²/s at 1600 °C is ~5–6× higher than a literal evaluation of the
written coefficients, so I used the stated reference value and its Arrhenius shape. The CO yield
(Y_CO) and the residual SiC stress are the least-constrained *inputs*, but they change only the
(already negligible) failure count, not the conclusions.

---

## 6. Ranking — which case suffers most, and why

Two different metrics matter, so both rankings are given.

**By barrier integrity / gas release (SiC failure probability):**
> **B > A2 > C1 > C2 > A1**

Driven by **peak temperature**: the two 1800 °C cases (B, A2) top the list because pressure
∝ T and the SiC stress with it. Among the 1600 °C cases, **burnup** orders them (C1 13.9 % >
C2 11.1 % > A1 7.7 %) through the gas inventory. B edges out A2 by having both the highest cumulative
time at 1800 °C (400 h vs 100 h) and near-complete gas release.

**By Cs-137 release (the governing source term):**
> **B (0.16) > A1 (0.11) > C1 ≈ C2 (0.087) > A2 (0.077)**

Driven by the **time–temperature integral √(∫D dt)** of Cs in SiC: B wins on the longest hot soak;
A1's long 500 h/1600 °C beats A2's short 100 h/1800 °C.

**Overall "suffers most": Case B (HFR-K6/3).** It is worst on *both* metrics — highest failure
probability and highest Cs-137 release — because it combines the highest peak temperature (1800 °C),
the longest cumulative time at high temperature (400 h), and high burnup (10.9 % FIMA).

**Absolute activity vs fraction.** Fractional releases equalise the burnup effect. In *absolute*
released activity, higher-burnup elements are worse for the same fraction (inventory ∝ %FIMA ×
HM-loading, §8): among the compacts C1 (13.9 %) releases ~25 % more Cs-137 activity than C2 (11.1 %)
at equal fraction — the intended C1/C2 burnup-isolation comparison. The spheres carry ~10× the
heavy-metal loading of the compacts, so even at similar fractions a sphere releases far more total
activity than a compact.

**Least severe: A1** on integrity (coolest peak, lowest burnup) though not on Cs fraction (its long
soak keeps Cs moderate). The compacts are the most benign in *absolute* terms simply because they
contain ~1/10 the fuel.

---

## 7. Assumptions and correlations used (summary)

| Item | Value / source | Confidence |
|---|---|---|
| SiC failure mode | Pressure-vessel + Weibull (Table 9.14: 873 MPa, m=8.02) | high |
| SiC membrane stress | thin-shell σ=Pr/2t, SiC load-bearing | high |
| Gas yield Y_gas | 0.31 Xe+Kr / fission | medium-high |
| CO yield Y_CO | 0.15 / fission (order-of-mag) | low (but non-critical) |
| Void volume | buffer porosity (1−ρ/2.10) | medium-high |
| Residual SiC compression | ~tens–200 MPa, annealed >1500 °C | low (non-critical) |
| Gas release from kernel | Eq 10.8, D₀′=5×10⁻³, Q=155.4 kJ/mol | medium-high |
| Cs in SiC | Eq 10.9 anchored to 1.011×10⁻¹⁶ m²/s @1600 °C | medium |
| Cs through intact SiC | equiv-sphere Eq 10.7/10.8, D/r_m², schedule-integrated | **medium-low (dominant output uncertainty)** |
| Failed-kernel release | equiv-sphere, Table 7.1 kernel D | high |
| One-particle thresholds | 6.1×10⁻⁵ (sphere), 6.1×10⁻⁴ (compact) | high (given) |

**Bottom line.** All five elements are predicted to retain their particle populations essentially
intact under these accident-heating schedules: **0 heating-induced SiC failures expected in each
case** (with the 1800 °C cases B and A2 carrying a few-percent chance of a *single* failed particle,
onset in their 1800 °C phases), **Kr-85 release at or below the one-particle detection threshold**,
and **Cs-137 release of ≈8–16 %** governed by diffusion through intact SiC. **Case B is the most
severe** (highest temperature × time and burnup); **A1 the most benign for integrity**; the
compact pair C1/C2 isolates the burnup effect (equal Cs *fraction*, ~25 % more Cs *activity* from
the higher-burnup C1).
