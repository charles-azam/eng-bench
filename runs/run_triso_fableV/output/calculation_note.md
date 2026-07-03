# Calculation note — TRISO particle failure and fission-product release under accident heating

**Scope.** Blind, offline prediction of coated-particle failures and of Kr-85 / Cs-137 fractional
release for the five furnace-heating cases of `inputs/02_cases.md` (A1 = HFR-K3/1, A2 = HFR-K3/3,
B = HFR-K6/3, C1 = HFR-P4/3-7, C2 = HFR-P4/1-12), using only the geometry/irradiation data of
`inputs/01_particles_and_elements.md` and the property annex `inputs/03_material_properties.md`
plus basic physics (ideal gas law, fission yields, shell mechanics). No published test results
were consulted. Working file: `output/model.py`; raw output: `output/model_output.txt`.

**Date:** 2026-07-03.

---

## 1. Results summary

| Case | Element / schedule | Predicted failed particles (central) | P(≥1 fail) / upside | Failure onset (if any) | Kr-85 fractional release | Cs-137 fractional release (best est., range) | Confidence (fail / Kr / Cs) |
|---|---|---|---|---|---|---|---|
| **A1** | K3/1 sphere, 1600 °C·500 h | **0** (E[N] = 0.0006 of 16,400) | 0.06 % / 0–1 | during 1600 °C hold | **< 6×10⁻⁵** (E-value 4×10⁻⁸) | **≈ 3×10⁻²** (1×10⁻² – 1×10⁻¹) | High / High / Low |
| **A2** | K3/3 sphere, 1800 °C·100 h | **0** (E[N] = 0.010 of 16,400) | 1.0 % / 0–2 | 2nd 1800 °C hold (t ≈ 113–187 h) | **< 6×10⁻⁵** (E-value 6×10⁻⁷) | **≈ 4×10⁻⁴** (1×10⁻⁴ – 1.5×10⁻³) | Medium / Medium / Low |
| **B** | K6/3 sphere, staged 1600/1700/1800/1800 °C | **0** (E[N] = 0.015 of 14,580) | 1.5 % / 0–5 | phases 3–4 (1800 °C), most likely phase 4 | **< 7×10⁻⁵** (E-value 1×10⁻⁶) | **≈ 1.2×10⁻¹** (5×10⁻² – 3.5×10⁻¹) | Medium / Medium / Low–Medium |
| **C1** | P4/3-7 compact, 1600 °C·304 h | **0** (E[N] = 0.007 of 1,631) | 0.7 % / 0–1 | late in 1600 °C hold | **< 6×10⁻⁴** (E-value 4×10⁻⁶) | **≈ 1×10⁻²** (3×10⁻³ – 4×10⁻²) | High / High / Low |
| **C2** | P4/1-12 compact, 1600 °C·304 h | **0** (E[N] = 0.0009 of 1,631) | 0.09 % / 0 | (none expected) | **< 6×10⁻⁴** (E-value 6×10⁻⁷) | **≈ 2×10⁻³** (5×10⁻⁴ – 7×10⁻³) | High / High / Low |

Kr-85 entries use the one-particle detection thresholds of annex §8 (6×10⁻⁵ sphere, ≈7×10⁻⁵ for
the 14,580-particle K6 sphere, 6×10⁻⁴ compact): with zero predicted failures the whole-element
Kr-85 release should sit **below** the one-particle level in every case. Cs-137, by contrast, is
released from **intact** particles by solid-state diffusion through the SiC (Eq 10.9) and is
predicted to be orders of magnitude larger than Kr-85 everywhere.

**Ranking (most → least damaged): B ≫ C1 > A2 > A1 > C2** (§6).

**Most uncertain assumption:** the Cs source boundary condition at the SiC inner surface
(concentration continuity, no solubility partition) — it sets the absolute Cs-137 numbers to
within only 1–2 orders of magnitude and biases them high (§7).

---

## 2. Physical picture and model structure

A TRISO particle fails (for gas release) only if its SiC pressure vessel breaks. Two release
paths are modelled:

1. **Pressure-vessel failure → Kr-85 (and extra Cs).** Fission gas (Xe+Kr) plus CO accumulate in
   the buffer void; at furnace temperature the gas pressure loads the SiC shell in tension. The
   probability that a particle's SiC survives peak tangential stress σ is
   exp[−(σ/σ₀)^m] with σ₀ = 873 MPa, m = 8.02 (annex §3, Table 9.14). Expected failures
   = N·(1−exp[−(σ_max/σ₀)^m]), tracked phase-by-phase along each schedule. Kr-85 is retained by
   intact SiC (no noble-gas diffusivity in SiC is given — treated as impermeable), so the element
   Kr-85 release is (failed fraction) × (bare-kernel release, Eqs 10.7–10.8), the latter ≈ 1 at
   1600–1800 °C over these hold times.
2. **Diffusion of Cs through intact SiC → Cs-137.** Cs leaves the kernel quickly at accident
   temperatures (kernel D′ from Table 7.1: Booth release fraction ≈ 1 within tens of hours at
   ≥1600 °C), so the intact SiC shell is the rate-limiting barrier (annex §5). I solve the 1-D
   spherical diffusion equation across the 36 µm SiC shell by explicit finite differences, with
   D_Cs,SiC anchored at the annex-recommended 1.011×10⁻¹⁶ m²/s at 1600 °C and scaled with the
   Arrhenius factor exp[−(125 kJ/mol)/R·(1/T−1/1873 K)] (Eq 10.9 with Γ = 2 as instructed);
   inner boundary = available (kernel-released, not yet escaped) Cs at concentration M/V_res;
   outer boundary = zero (buffer, IPyC, OPyC and matrix treated as non-retentive at these
   temperatures). The **irradiation phase is simulated first** (8,400–15,200 h at the mean
   irradiation temperature) so the SiC enters the furnace already partially loaded with Cs —
   important for B (15,216 h at 1140 °C) and A1.

The controlling group for Cs is the dimensionless diffusion time τ = ∫D dt / L² of the SiC shell
(L = 36 µm; breakthrough lag ≈ L²/6D). At 1600 °C the lag is ≈ 590 h, at 1800 °C ≈ 270 h
(D(1800 °C) = 2.2×10⁻¹⁶ m²/s). Hence: A2 (only 100 h at 1800 °C, τ/L² ≈ 0.07) barely breaks
through, while B (100 h + 100 h + 400 h at 1600/1700/1800 °C **plus** an in-pile preload
τ/L² ≈ 0.31) is fully broken through and releases massively. This lag structure, not the peak
temperature alone, orders the Cs results.

**In-reactor R/B (Eqs 7.5–7.6)** is not used: it diagnoses in-pile release of short-lived gases
and does not govern the furnace release of stable/long-lived species (annex §7 says as much).

## 3. Input-derived quantities (per particle)

Batch EUO 2308 (K3, P4): kernel r = 248.5 µm, buffer void volume = 57.8×10⁻¹² m³ (94 µm buffer at
1.00 g/cm³ against 2.25 g/cm³ theoretical → 55.6 % porosity); SiC mean radius 401.5 µm, thickness
36 µm → thin-shell factor σ/P = r/2t = 5.58. U atoms per particle 1.549×10¹⁸.
Batch EUO 2358–65 (K6): kernel r = 254 µm, void 65.8×10⁻¹² m³, σ/P = 5.74, 1.642×10¹⁸ U atoms.

Fissions per particle = burnup × U atoms; stable Xe+Kr = 0.30 atoms/fission (standard cumulative
U-235 thermal-fission noble-gas yield — physics input, not from the annex); CO = 0.05 oxygen
atoms/fission (assumption; sensitivity 0.01–0.10 carried through). Kernel gas release into the
buffer follows the equivalent-sphere model (Eqs 10.7–10.8) with the stable-gas coefficient of
Table 7.1 (D₀′ = 5×10⁻³ s⁻¹, Q = 155.4 kJ/mol) integrated over the actual T(t) history
(transformed time τ = ∫D′dt); it reaches 95–100 % during every furnace schedule, so the peak
pressures below are effectively full-inventory pressures.

| Case | Fissions/particle | Peak pressure (MPa) | Peak SiC hoop stress (MPa) | P_fail per particle | E[N_fail] |
|---|---|---|---|---|---|
| A1 | 1.19×10¹⁷ | 18.7 | 104 | 3.9×10⁻⁸ | 0.0006 |
| A2 | 1.58×10¹⁷ | 26.2 | 146 | 5.9×10⁻⁷ | 0.010 |
| B  | 1.79×10¹⁷ | 27.2 | 156 | 1.0×10⁻⁶ | 0.015 |
| C1 | 2.15×10¹⁷ | 33.4 | 186 | 4.2×10⁻⁶ | 0.007 |
| C2 | 1.72×10¹⁷ | 26.1 | 146 | 5.8×10⁻⁷ | 0.0009 |

Even the worst case (C1, 13.9 % FIMA) reaches barely a fifth of the SiC Weibull strength, and the
m = 8 exponent makes the failure probability per particle ≤ 4×10⁻⁶. **The pressure-vessel route
cannot produce even one statistically expected failure in any of these elements.** This is robust:
doubling the pressure (e.g. O/f = 0.10 everywhere plus full-yield gas) still leaves E[N] < 0.05
in every case (sensitivity block of `model_output.txt`).

A scoping check of residual stresses (annex §2, Eq 9.22/9.23, Table 9.8 correlations (e)+(d),
K = 4.93×10⁻⁴ (MPa·10²⁵ n/m²)⁻¹): PyC tangential shrinkage rates of 0.021–0.025 per 10²⁵ n/m² at
the case fluences (3.5–6.8×10²⁵, E > 0.18 MeV) balanced against irradiation creep give steady PyC
tensile stresses of ~40–50 MPa, i.e. the two ~40 µm PyC layers hold the 36 µm SiC in compression
of order −50…−100 MPa at end of irradiation. Neglecting this (as done above) is therefore
**conservative** for the failure prediction.

## 4. Case-by-case discussion

**A1 — HFR-K3/1, 7.7 % FIMA, 1600 °C for 500 h.** Lowest burnup → lowest pressure (19 MPa) and a
per-particle failure probability of 4×10⁻⁸: an unambiguous **zero-failure** prediction (high
confidence); Kr-85 stays below the one-particle level 6×10⁻⁵ (high confidence). Cs: 500 h at
1600 °C is comparable to the SiC lag time (≈590 h), and the 8,616 h irradiation at ~1120 °C mean
already contributes τ/L² ≈ 0.13, so the shell is past breakthrough by mid-hold. Model band
3.4×10⁻² (Cs redistributed through kernel+buffer+IPyC — more physical, since the kernel is
Cs-depleted at 1600 °C) to 1.0×10⁻¹ (kernel-concentration continuity — conservative). **Best
estimate ≈ 3×10⁻², range 10⁻²–10⁻¹, low confidence** (§7 bias discussion: the true value could be
one further order lower). Release grows continuously through the second half of the hold.

**A2 — HFR-K3/3, 10.2 % FIMA, 1800 °C for 100 h total.** Higher burnup and temperature → 26 MPa,
146 MPa peak stress, E[N] = 0.010; **central prediction 0 failures** (P(≥1) ≈ 1 %). If a failure
occurs it is most likely in the **second, 74.5 h 1800 °C hold** (E[N] contribution 0.008 vs 0.0013
in the first hold), i.e. after t ≈ 113 h of schedule. Because the annex contains no SiC
thermal-decomposition/fission-product-corrosion kinetics, and such degradation is strongly
activated above ~1700 °C, I carry an **upside allowance of 0–2 failures** (low confidence on the
upper end); each failure would add ≈ 6×10⁻⁵ to the Kr-85 fraction. Cs: only 100 h at 1800 °C —
τ/L² ≈ 0.07, well **inside** the diffusion lag (the cold irradiation, ~840 °C mean, preloads
nothing) → small transient release, **best estimate ≈ 4×10⁻⁴ (10⁻⁴–1.5×10⁻³), low confidence**.
Note the model consequence: A2 releases *less* Cs than A1 despite being 200 °C hotter, because it
is held ~5× shorter and enters with a colder-irradiation history; unmodelled SiC degradation is
the main risk to this conclusion.

**B — HFR-K6/3, 10.9 % FIMA, staged 1600/1700/1800 °C ×100 h + 1800 °C ×300 h.** Highest E[N]
(0.015) of the spheres; within the pressure model the risk accrues once the gas is fully released
(from the 1600 °C phase on, σ_max 140→156 MPa), but the physically most likely failure window is
the **1800 °C phases (3 and 4), especially the final 300 h**, where any strength degradation acts
longest. **Central prediction 0 failures, upside 0–5** (low confidence upper end; onset in phase
4). Kr-85: below 7×10⁻⁵ centrally; each real failure adds ≈ 6.9×10⁻⁵. Cs: worst of all cases —
the 15,216 h irradiation at 1140 °C alone drives the SiC shell to τ/L² ≈ 0.31 (past breakthrough
before the furnace ever heats), and the furnace adds ≈ 500 h ≥ 1600 °C of which 400 h at 1800 °C.
Predicted release **≈ 1.2×10⁻¹ (5×10⁻²–3.5×10⁻¹), low–medium confidence**, with the release rate
stepping up in each successive phase; by the fourth phase the SiC of the whole population is
essentially Cs-transparent. (Part of this, ≈ 0.1 in the conservative variant, crossed the SiC
already in-pile and sits in the matrix; it is assumed to leave the element early in the heating —
expect a large early Cs burst in this case.)

**C1 — HFR-P4/3-7, 13.9 % FIMA, 1600 °C for 304 h.** Highest burnup of the set → highest pressure
(33 MPa) and the highest per-particle failure probability (4.2×10⁻⁶ ≈ 7× C2), but only 1,631
particles → E[N] = 0.007: **0 failures** (high confidence), Kr-85 below the compact one-particle
level 6×10⁻⁴ (high confidence — note the compact threshold is 10× coarser than the spheres').
Any failure would come late in the 1600 °C hold (stress still rising 165→186 MPa as the last
kernel gas is released). Cs: 304 h at 1600 °C plus a warm irradiation (1075 °C, τ/L² ≈ 0.10
preload) → just past lag; **best estimate ≈ 1×10⁻² (3×10⁻³–4×10⁻²), low confidence**.

**C2 — HFR-P4/1-12, 11.1 % FIMA, identical schedule to C1.** The burnup-effect twin: 20 % less
burnup → 26 MPa, 146 MPa, per-particle failure probability 7× lower than C1, E[N] = 0.0009 →
**0 failures** (high confidence), Kr-85 < 6×10⁻⁴. The colder irradiation (940 °C) contributes
almost no SiC preload, so the shell stays essentially within its lag time: **Cs ≈ 2×10⁻³
(5×10⁻⁴–7×10⁻³), low confidence** — about 5× less than C1.

## 5. Failure-onset summary

Within the pressure-vessel model the failure probability is a function of the running maximum
stress, so risk concentrates where pressure (∝ n·T) first peaks: the final approach to, and first
tens of hours at, each case's peak-temperature hold, with a slow further rise as the last kernel
gas is released. Explicitly: A1/C1/C2 — the 1600 °C hold; A2 — the 1800 °C holds (second one
dominant); B — from the 1600 °C phase onward with maximum likelihood in the 1800 °C phases 3–4.
Any degradation-driven failures (not modelled) would instead cluster late in the hottest, longest
exposures: the end of A2's second 1800 °C hold and B's final 300 h phase.

## 6. Ranking and sensitivities

**B ≫ C1 > A2 > A1 > C2.**

- **B suffers most, by far**: highest combined metric on every axis — E[N_fail] = 0.015 (highest),
  Cs-137 ≈ 12 % (highest by ×4), and the longest time at ≥1600 °C (≈500 h, of which 400 h at
  1800 °C) compounding a 15,216 h/1140 °C irradiation that had already breached the SiC's Cs lag.
  If any case shows real (degradation-driven) particle failures, it is this one, in phase 4.
- **C1 second**: burnup, not temperature, is its driver — 13.9 % FIMA gives the highest internal
  pressure and per-particle failure probability of the whole set, plus a 1 % Cs release.
- **A2 third**: hottest schedule but short; within the diffusion model its Cs release is the
  *smallest* (100 h ≪ lag at 1800 °C, cold irradiation), so its risk is concentrated in the
  (unmodelled, temperature-steep) SiC degradation channel and in gas-pressure failures
  (E[N] = 0.010, second highest).
- **A1 fourth**: benign on failures (lowest stress of all) but its 500 h at 1600 °C produces the
  second-largest Cs release (~3 %). Time at temperature, not peak temperature, is what hurts it.
- **C2 least**: modest burnup, cold irradiation, 1600 °C only — lowest numbers on both axes.

**Temperature sensitivity.** Pressure grows only linearly in T, but (i) D_Cs,SiC grows
Arrhenius-like — ×2.2 per 200 °C (Q = 125 kJ/mol) — and, more importantly, (ii) the *lag time*
L²/6D crosses the experiment duration between 1600 and 1800 °C: a 100 h hold releases almost no
Cs at 1600 °C but a 400 h hold at 1800 °C releases tens of percent. Failure risk at 1800 °C is
understated by the pressure model alone because SiC strength-degradation kinetics (much steeper
in T) are absent from the annex.

**Burnup sensitivity.** Gas and CO inventories scale linearly with burnup, so σ ∝ Bu and the
Weibull exponent turns this into P_fail ∝ Bu^8: the C1/C2 pair (13.9 vs 11.1 % FIMA, identical
heating) shows exactly this — (13.9/11.1)^8.02 ≈ 6, model ratio ≈ 7 (CO and release-fraction
differences make up the rest). Burnup also scales the *absolute* activity released (annex §8):
at equal fractional release C1 emits ≈ 25 % more becquerels per particle than C2.

## 7. Assumptions, confidence, and the dominant uncertainty

| # | Assumption | Basis | Effect / confidence |
|---|---|---|---|
| 1 | Xe+Kr yield 0.30/fission | U-235 thermal fission physics | ±10 % on P; high |
| 2 | CO from O/f = 0.05 (range 0.01–0.10) | UO₂ oxygen balance, no annex correlation | ±20 % on P, ×3–5 on E[N]; medium |
| 3 | All released gas + CO in buffer pores (porosity vs 2.25 g/cm³ PyC), no credit for kernel/crack porosity, no void loss to kernel swelling | annex buffer convention (§1) | conservative on P; medium |
| 4 | Thin-shell stress σ = P·r/2t, residual PyC-induced compression (−50…−100 MPa, §3) neglected; Weibull "mean" 873 MPa used as characteristic strength, per-particle form of annex §3, no stressed-volume factor | Table 9.14 | conservative; medium |
| 5 | Intact SiC fully retains Kr | no noble-gas D in SiC given; physical | high |
| 6 | **Cs inner boundary: concentration continuity with the kernel-released inventory (no solubility partition at the SiC interface); reservoir volume kernel…kernel+buffer+IPyC** | standard multilayer-code practice; annex gives no partition data | **sets absolute F_Cs within 1–2 orders, biases HIGH; low** |
| 7 | Buffer/IPyC/OPyC/matrix non-retentive for Cs at ≥1600 °C; all Cs that ever crossed the SiC (incl. in-pile) leaves the element during the test | weak sorption at accident T | biases F_Cs high, esp. B; medium |
| 8 | Mean irradiation temperatures (A1 1120, A2 840, B 1140, C1 1075, C2 940 °C) for the in-pile preload | inputs give surface/centre ranges | ×2–3 on preload term; medium |
| 9 | No SiC thermal-decomposition / fission-product-corrosion failure channel | not in annex | biases failure count LOW at 1800 °C (A2, B); low |
| 10 | No as-manufactured defective particles or matrix uranium contamination | not in inputs | Kr-85 floor could sit at ~10⁻⁶–10⁻⁵ regardless of failures |

**Most uncertain assumption: #6, the Cs–SiC source boundary condition.** The Cs-137 release is in
the breakthrough-transient regime in four of five cases, where the release scales directly with
the assumed interface concentration; real Cs solubility in SiC is far below that in the
kernel/carbon, so the tabulated Cs numbers are best read as upper-half estimates with a genuine
uncertainty of one, possibly two, orders of magnitude downward. It does not affect the *ranking*
(medium confidence), which is set by the τ/L² ordering. For the failure counts the critical
assumption is instead #9: it is the only mechanism that could realistically turn the 1800 °C
predictions (A2, B) from 0 into a handful of failures, which is why those upside ranges are
carried.

## 8. Correlations used (citations)

- Elastic/thermal data, buffer convention — annex §1, Table 9.6.
- PyC swelling/creep scoping — annex §2, Eq 9.22/9.23, Table 9.8 corr. (e) and (d), creep
  coefficient 4.93×10⁻⁴ (MPa·10²⁵ n/m²)⁻¹ (Table 9.14).
- SiC/PyC Weibull statistics — annex §3, Table 9.14 (σ₀ = 873 MPa, m = 8.02).
- Kernel diffusion coefficients (Cs; stable Xe/Kr 5×10⁻³ s⁻¹ / 155.4 kJ/mol) — annex §4, Table 7.1.
- Cs diffusion in SiC — annex §5, Eq 10.9 anchored at 1.011×10⁻¹⁶ m²/s @1600 °C, Γ = 2.
- Equivalent-sphere release — annex §6, Eqs 10.7–10.8 (Booth approximations).
- Booth R/B (not used, in-pile diagnostic only) — annex §7, Eqs 7.5–7.6.
- Inventory scaling and one-particle detection thresholds — annex §8.
- Geometry, densities, particle counts, irradiation histories, schedules — inputs 01 and 02.
