# Calculation note — TRISO particle failure and fission-product release under accident heating

**Scope.** Five furnace accident-heating cases on irradiated LEU UO₂ TRISO fuel elements
(spheres HFR-K3/1, HFR-K3/3, HFR-K6/3; compacts HFR-P4/3-7, HFR-P4/1-12). For each case this note
predicts (1) the number of coated-particle failures and the phase/onset at which they occur,
(2) the final fractional release of Kr-85 and Cs-137 from the element, and (3) a ranking of the
cases with the temperature/burnup reasoning. All numbers are derived offline from
`inputs/01–03` only; no experimental results were consulted. Working script and raw output:
`output/triso_calc.py`, `output/calc_output.txt`.

---

## 1. Physical model and correlations used

### 1.1 What "failure" means and what drives it
Failure = through-thickness loss of the SiC layer, after which the particle behaves as a bare
kernel (§01, layer functions). Below ~2000 °C the SiC does not thermally decompose, so the
mechanistic failure driver available from the annex is **over-pressure of the SiC pressure
vessel**, resisted by (a) the SiC strength and (b) the compressive stress the IPyC/OPyC put on
the SiC during irradiation. I evaluate this explicitly and show it is not reached; the residual
failure risk therefore comes from time-and-temperature degradation processes that the annex does
not parameterize (discussed in §4).

### 1.2 Internal pressure (pressure-vessel loading)
- **Fissions per particle:** kernel U inventory `N_U = (ρ_k V_kernel / M_UO₂)·N_A` (kernel
  geometry/density from `01`, M_UO₂ = 269.8 g/mol), times burnup (%FIMA). HFR-K3/P4 kernel gives
  `N_U ≈ 1.55×10¹⁸`; HFR-K6 `≈1.64×10¹⁸`.
- **Fission-gas atoms:** `N_gas = Y_gas · N_fiss`, with stable+long-lived Xe+Kr yield
  `Y_gas ≈ 0.30 atoms/fission`. On heating the gas is released from the kernel into the buffer
  void; the released-to-void fraction is the kernel-diffusion release (§4/§6 of the annex,
  Xe/Kr stable coefficient D₀′ = 5×10⁻³ s⁻¹, Q = 155.4 kJ/mol) — 0.93–1.0 over these holds.
- **Void volume:** buffer pore volume `V_void = V_buffer·(1 − ρ_buffer/2.10)` (theoretical dense
  PyC 2.10 Mg/m³). ≈5.4×10⁻¹¹ m³ (K3/P4), 6.2×10⁻¹¹ m³ (K6).
- **Pressure:** ideal gas `P = n R T / V_void`.
- **CO:** the annex gives no CO-formation correlation, so the baseline is fission-gas only; a
  CO/oxygen sensitivity band of +30–50 % on pressure is carried (§4).

Resulting mean-geometry pressures at the peak hold: **A1 17 MPa, A2 24, B 25, C1 29, C2 23 MPa**.

### 1.3 SiC tangential stress
- **Pressure term, with elastic load sharing** across the bonded IPyC/SiC/OPyC membranes
  (Table 9.6 moduli): `σ_press,SiC = P·r_mid·E*_SiC / (2·Σ E*_i t_i)`, `E* = E/(1−ν)`. This gives
  ≈4.2·P (vs 5.6·P for SiC carrying the load alone). Peak-hold values: **A1 72, A2 102, B 110,
  C1 124, C2 99 MPa**.
- **Residual irradiation compression** in the SiC from IPyC/OPyC shrinkage, relaxed by
  irradiation creep. Integrated over fast fluence (E>0.18 MeV = E>0.1 / 1.10) with PyC swelling
  correlation **(e)** tangential (Eq 9.22) and the Table-9.14 scalar creep coefficient
  `K = 4.93×10⁻⁴ (MPa·10²⁵)⁻¹`, creep ν = 0.4, via a two-membrane (lumped PyC vs SiC)
  creep-relaxation ODE `dσ_s/dx = [ṡ − K·(1−ν_c)·(t_s/t_p)·σ_s] / [a + b·t_s/t_p]`.
  Result **−158 to −189 MPa (compression)**, near the steady-state asymptote
  `σ_ss = ṡ /[K(1−ν_c)(t_s/t_p)] ≈ −190 MPa`. Assumed **retained** during the (flux-free)
  furnace hold — thermal creep of dense PyC is slow.
- **Net SiC tangential stress = residual (−) + pressure (+):** compressive in every case:
  **A1 −87, A2 −81, B −49, C1 −66, C2 −77 MPa**.

### 1.4 Failure statistics
SiC failure by Weibull (Table 9.14: σ₀ = 873 MPa, m = 8.02):
`p_f = 1 − exp[−(σ_net/σ₀)^m]` for σ_net > 0. Particle-to-particle scatter in kernel size and
layer thicknesses (means ± SD from `01`) is Monte-Carlo sampled (2×10⁵ draws); each draw
contributes its analytic Weibull probability, so the failure count is resolved far below one
particle. **Even the 99.9th-percentile / worst tail of net stress is ≤ +70 MPa (case B)** — an
order of magnitude below σ₀ — so `p_f` is effectively zero (see §3).

### 1.5 Release model
- **Kr-85 (fission gas):** intact SiC retains gas essentially perfectly, so release comes only
  from failed particles. A failed kernel releases fraction `F_gas` of its gas by the
  equivalent-sphere solution (Eqs 10.7–10.8, reduced kernel gas coefficient §4): `F_gas ≈ 0.93–1.0`
  over these holds. Hence **Kr-85 fractional release ≈ (N_fail/N_tot)·F_gas**. One failed particle
  = 6.1×10⁻⁵ (spheres, 1/16400) or 6.1×10⁻⁴ (compacts, 1/1631) — the detection thresholds of §8.
- **Cs-137 (metallic, SiC-mobile):** two contributions —
  (i) *failed* particles release ≈100 % (kernel Cs diffusion, D₀′=0.90, Q=209 kJ/mol, is fast:
  `D′t ≫ 0.15`); (ii) *intact* particles leak Cs by slow diffusion **through the SiC**
  (Eq 10.9, anchored to the annex's stated `D_Cs,SiC(1600 °C)=1.011×10⁻¹⁶ m²/s`, scaled by the
  dominant 125 kJ/mol Arrhenius term to 1.52×10⁻¹⁶ at 1700 °C and 2.19×10⁻¹⁶ at 1800 °C).
  Intact-particle Cs release is estimated with the equivalent-sphere formula at the particle
  (SiC-outer) radius. **Cs-137 release ≈ (N_fail/N_tot)·1 + (1 − N_fail/N_tot)·F_Cs,SiC.**

> Note on Eq 10.9: evaluating the printed coefficients directly gives ~1.8×10⁻¹⁷ m²/s at
> 1600 °C, a factor ~5.6 below the annex's stated 1.011×10⁻¹⁶. I use the **stated** value as the
> anchor (as the annex instructs) and flag the discrepancy; it does not change the conclusions,
> only the absolute Cs magnitude.

---

## 2. Per-case results

Onset convention: diffusive Cs release accumulates continuously and is dominated by the
highest-temperature phase; any particle failure (see §3–4) would occur during that same peak phase.

| Case | Element | N | Burnup %FIMA | Peak T / time | Peak-hold P (MPa) | Net SiC σ (MPa) | **Failed particles (best estimate)** | Failure onset |
|---|---|---|---|---|---|---|---|---|
| A1 | HFR-K3/1 sphere | 16 400 | 7.7 | 1600 °C / 500 h | 17 | −87 | **0** (<10⁻³ expected) | — (no over-pressure failure) |
| A2 | HFR-K3/3 sphere | 16 400 | 10.6 | 1800 °C / 100 h | 24 | −81 | **0–2** (0 over-pressure; tail via 1800 °C degradation) | during 1800 °C exposure |
| B  | HFR-K6/3 sphere | 14 580 | 10.9 | 1800 °C / 100+300 h | 25 | −49 | **0–5** (0 over-pressure; degradation over 400 h) | 1800 °C stages, mostly the final 300 h |
| C1 | HFR-P4/3-7 compact | 1 631 | 13.9 | 1600 °C / 304 h | 29 | −66 | **0** (<10⁻³ expected) | — |
| C2 | HFR-P4/1-12 compact | 1 631 | 11.1 | 1600 °C / 304 h | 23 | −77 | **0** (<10⁻³ expected) | — |

### Fractional release predictions

| Case | **Kr-85 fractional release** | **Cs-137 fractional release** (baseline) | Cs-137 range (diffusion-length sensitivity) |
|---|---|---|---|
| A1 | ≲ 6×10⁻⁵ (below 1-particle threshold) | **≈ 0.11** | 0.05 – 0.18 |
| A2 | ~ 6×10⁻⁵ – 1×10⁻⁴ (0–2 particles) | **≈ 0.07** | 0.04 – 0.12 |
| B  | ~ 6×10⁻⁵ – 3×10⁻⁴ (0–5 particles) | **≈ 0.13** | 0.07 – 0.22 |
| C1 | ≲ 6×10⁻⁴ (below 1-particle threshold) | **≈ 0.083** | 0.04 – 0.14 |
| C2 | ≲ 6×10⁻⁴ (below 1-particle threshold) | **≈ 0.083** | 0.04 – 0.14 |

**Reading the Kr-85 numbers:** with zero over-pressure failures, the whole-element Kr-85 release
sits *at or below the one-particle detection threshold* — i.e. consistent with zero heating-induced
failures — for all cases; only the 1800 °C cases (A2, B) can plausibly rise above it if the tail of
weak/degraded particles fails, B most of all because it spends 400 h at 1800 °C.

**Reading the Cs-137 numbers:** Cs escapes *intact* SiC by diffusion, so its release is
substantial (order 10 %) and, unlike Kr, does **not** require particle failure. It scales with the
Arrhenius `D_Cs,SiC` and with hold time — hence the ordering below. The absolute fraction is the
least certain number in this note (see §5); the *ordering* is robust.

---

## 3. Why over-pressure fails essentially no particles (the key quantitative finding)

At ≤1800 °C the fission-gas pressure (17–29 MPa) produces only 70–124 MPa of tangential stress in
the SiC after load-sharing, while the IPyC/OPyC leave the SiC in −160 to −190 MPa residual
**compression**. The net SiC stress is therefore compressive in every case, and even the extreme
Monte-Carlo tail (thin SiC + small buffer void + high burnup) reaches at most +70 MPa (B) —
`(70/873)^8 ≈ 10⁻⁸`. Stress-tail diagnostics (`calc_output.txt`):

```
A1 max net −3 MPa   frac(net>0)=0        B  max +70 MPa  frac(net>0)=1.5e-2 (all <<873)
A2 max +38 MPa      C1 max +60 MPa       C2 max +42 MPa
```

Sensitivity: adding +30 % CO pressure and stripping **half** the protective compression still
yields <2×10⁻⁴ failed particles in the worst case (B); only *fully* removing the compression
gives ~0.02 particles in B — still below one. **Conclusion: the pressure-vessel mechanism cannot
fail these particles at ≤1800 °C.** This is the physically correct result: these coatings are
strong and the driving pressures are modest.

---

## 4. What could still fail particles at 1800 °C (A2, B), and the small non-zero counts
The residual failure paths, all time-and-temperature driven and **not parameterized in the
annex**, are: (i) slow thermal annealing/creep relaxation of the protective PyC compression,
raising net SiC stress; (ii) fission-product corrosion of SiC (Pd, rare earths) that locally
thins the wall; (iii) SiC thermal degradation/decomposition, which becomes non-negligible only as
temperature approaches ~2000 °C. All three intensify with temperature and exposure time, so they
concentrate in the 1800 °C cases and scale with hold duration. On that basis I assign a small
non-zero **0–2** (A2) and **0–5** (B) failed-particle band — driven by B's 400 h at 1800 °C —
while the 1600 °C cases (A1, C1, C2) stay at 0. These bands are engineering judgement, low
confidence; the annex does not permit a rigorous number.

---

## 5. Ranking — which case suffers most, and the T/burnup sensitivities

**Overall severity (worst → least): B > A1 ≳ A2 > C1 > C2.**

Reasoning:
1. **Temperature is the dominant lever** (Arrhenius). Both the Cs-in-SiC diffusion coefficient and
   every degradation path rise steeply with T. The 1800 °C cases (A2, B) carry the highest
   *failure* risk.
2. **Time at temperature multiplies it.** Cs fractional release ∝ ~√(D·t). B holds 400 h at
   1800 °C → highest Cs fraction (≈0.13) **and** the largest degradation exposure → **B suffers
   most**. A2 is as hot but only 100 h, so its *fractional* Cs release (≈0.07) is actually the
   lowest of the five even though its failure risk is second-highest — a genuine T-vs-time
   trade-off. A1 is cooler (1600 °C) but held 500 h, giving the second-highest Cs fraction
   (≈0.11). So by **fractional Cs release** the order is **B > A1 > C1 = C2 > A2**, while by
   **failure/degradation risk** it is **B > A2 > (A1, C1, C2)**.
3. **Burnup sets inventory and pressure, not the release fraction.** The C1/C2 pair (identical
   1600 °C / 304 h schedule and geometry) isolates burnup: the Cs *fraction* is identical (0.083),
   but C1 (13.9 %) carries ~25 % more Cs-137 inventory and a higher internal pressure
   (29 vs 23 MPa) than C2 (11.1 %). So **C1 releases more activity and is marginally more failure-
   prone than C2** — the expected burnup signature, though both remain at ~0 failures.
4. **Released activity (Bq), per element**, proxied by (Cs fraction × burnup × HM loading):
   B ≈ 13.8, A1 ≈ 8.3, A2 ≈ 7.6, C1 ≈ 1.2, C2 ≈ 0.9 (arbitrary units). Spheres dominate over
   compacts simply because they hold ~10× the heavy metal; **B is worst on both fractional and
   absolute Cs release.**

---

## 6. Assumptions and confidence

| # | Assumption | Confidence | Effect if wrong |
|---|---|---|---|
| 1 | Over-pressure + Weibull is the only quantifiable failure mode ≤1800 °C; net compressive SiC ⇒ ~0 failures | **High** | Central result; robust to CO and partial compression loss |
| 2 | Protective irradiation-induced SiC compression (−160 to −190 MPa) is retained through the hold | **Medium** | If it relaxes fully, still <1 failed particle (B) — see §3 |
| 3 | Gas fully released to buffer void, ideal-gas pressure, Y_gas = 0.30, no CO baseline | **Medium-high** | ±50 % pressure → negligible impact on failures (§3) |
| 4 | Kr-85 release = failed-fraction × ~1 (intact SiC retains gas perfectly) | **High** | Directly tied to failure count and §8 thresholds |
| 5 | Cs-137 leaks through intact SiC via Eq 10.9, equivalent-sphere at particle radius | **Low-medium** | Sets the *absolute* Cs fraction; see below |
| 6 | Small 1800 °C degradation-driven failure bands (A2 0–2, B 0–5) | **Low** | Judgement; not derivable from the annex |

**Most uncertain assumption:** the **Cs-137 release model through intact SiC** — specifically the
effective diffusion length. Using the particle radius gives ≈7–13 %; using the kernel radius gives
≈12–22 %; using the bare 36 µm SiC wall thickness gives ≈65–95 %. This one modelling choice spans
more than an order of magnitude in the headline Cs number, dwarfing every other uncertainty. The
compounding factor-~5.6 inconsistency in the printed Eq 10.9 coefficients vs its stated 1600 °C
value adds to it. Consequently the **Cs-137 absolute fractions are low confidence**, but the
**case ranking is high confidence** (temperature and time enter every candidate model the same way,
so B > A1 > C1 = C2 > A2 by fraction, and B worst overall, are preserved across the whole
sensitivity range). The Kr-85 / failure-count conclusion (≈0, at/below detection for 1600 °C
cases; small and B-highest at 1800 °C) is high confidence.

---

## 7. One-line summary per case
- **A1** (1600 °C/500 h, 7.7 %): 0 failures; Kr-85 ≲6×10⁻⁵ (below detection); Cs-137 ≈0.11.
- **A2** (1800 °C/100 h, 10.6 %): 0–2 failures during the 1800 °C exposure; Kr-85 ~6×10⁻⁵–1×10⁻⁴;
  Cs-137 ≈0.07.
- **B** (1800 °C staged, 400 h, 10.9 %): 0–5 failures, mostly in the final 300 h at 1800 °C;
  Kr-85 ~6×10⁻⁵–3×10⁻⁴ (highest); Cs-137 ≈0.13 (highest) — **worst case**.
- **C1** (1600 °C/304 h, 13.9 %): 0 failures; Kr-85 ≲6×10⁻⁴ (below compact detection);
  Cs-137 ≈0.083; highest *activity* of the pair.
- **C2** (1600 °C/304 h, 11.1 %): 0 failures; Kr-85 ≲6×10⁻⁴; Cs-137 ≈0.083; least severe overall.
