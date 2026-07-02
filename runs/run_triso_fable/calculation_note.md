# Calculation note — TRISO particle failure and fission-product release under accident heating

**Cases:** A1 (HFR-K3/1), A2 (HFR-K3/3), B (HFR-K6/3), C1 (HFR-P4/3-7), C2 (HFR-P4/1-12)
**Basis:** `inputs/01_particles_and_elements.md`, `inputs/02_cases.md`, `inputs/03_material_properties.md` (TECDOC-1674 correlation numbering) + first principles. Worked fully offline; no published test results consulted.
**Model code:** `triso_model.py` (stdlib Python). Machine-readable results: `results.json`. Run log: `model_run.log`.

---

## 1. Physical picture and model chain

A particle releases fission products in two ways:

1. **Through intact coatings** — noble gases (Kr-85) essentially do not penetrate intact SiC;
   Cs-137 does, slowly, by solid-state diffusion (annex §5, Eq 10.9). So an element with zero
   failures still shows a growing Cs release but a Kr release below the one-particle threshold
   (annex §8: 6×10⁻⁵ for spheres, 6×10⁻⁴ for compacts).
2. **By SiC failure** — the particle then behaves as a bare kernel: it instantly vents the gas
   stored in the buffer and thereafter releases gas and Cs by kernel diffusion
   (annex §6, Eqs 10.7–10.8 with Table 7.1 coefficients). At 1600–1800 °C a failed particle
   releases ≳90 % of its Kr and Cs inventory within ~100 h, so each failure ≈ one full
   particle inventory.

The model chain, per case, marched through the irradiation history and then the furnace
staircase in 30 s steps:

| Step | Model | Source |
|---|---|---|
| Fission inventory | atoms U × %FIMA; stable Xe+Kr yield 0.31/fission; Cs, Kr-85 treated fractionally | inputs 01; annex §8 |
| Gas release kernel→buffer | Booth equivalent sphere, Eqs 10.8a/b, D′ = 5×10⁻³·exp(−155.4 kJ/RT) s⁻¹ ("stable & long-lived gases"), ∫D′dt over irradiation + heating | annex §4, §6 |
| CO from free oxygen | Proksch-type estimate O/F = t²(efpd)·10^(−0.21−8500/T_irr), capped at 0.15 — **not in the annex**, carried as explicit assumption + "no-CO" sensitivity | first principles / HTGR practice |
| Internal pressure | ideal gas in buffer void: porosity = 1 − ρ_buf/2.25 ≈ 0.55, −10 % for kernel swelling → V_void ≈ 5.2×10⁻¹¹ m³ (K3/P4), 5.9×10⁻¹¹ m³ (K6) | inputs 01, annex §1 |
| SiC stress | thin shell σ = P·r_mid/(2·t_eff); PyC shrinkage-induced compression on SiC (order −10…−50 MPa, est. from ġ/K with Table 9.8 (e) and K = 4.93×10⁻⁴) **neglected → conservative** | annex §1–2 |
| SiC degradation (a) | thermal-decomposition thinning k = A·exp(−514 kJ/RT); A anchored so 36 µm is consumed in ~10 h at 2200 °C (the accepted TRISO destruction temperature; Si vapor-pressure argument). Gives 0.0012 µm/h at 1600 °C, 0.029 µm/h at 1800 °C | Q from annex Eq 10.9 second term; anchor = engineering judgment |
| SiC degradation (b) | Cs-corrosion penetration δ = √(∫D_Cs,SiC dt); Weibull scale strength knocked down ×(1 − 0.35·δ/t_SiC) | annex §5 + judgment (corroded SiC keeps ~2/3 strength) |
| Failure statistics | Pf = 1 − exp[−(σ/σ₀,eff)^m], σ₀ = 873 MPa, m = 8.02; expected failures = N·max-to-date Pf | annex §3, Table 9.14 |
| Kr-85 element release | Σ over failure increments [buffer fraction vented + post-failure Booth] + 1×10⁻⁵ baseline (matrix contamination/as-manufactured defects) | annex §6, §8 |
| Cs-137 element release | explicit transient PDE: spherical diffusion through the 36 µm SiC shell (D_Cs,SiC, Eq 10.9), inner boundary = well-mixed reservoir (everything inside SiC) fed by kernel Booth release (D′ = 0.90·exp(−209 kJ/RT)); outer boundary = zero sink (no matrix holdup credit); run through irradiation (pre-penetration) and heating; + failed particles at 90 % | annex §4, §5, §6 |

### A note on Eq 10.9 as printed

With the printed second-term prefactor 1.6×10⁻¹⁵ m²/s, D_Cs,SiC(1600 °C) evaluates to
1.8×10⁻¹⁷ m²/s — inconsistent with the annex's own stated value of **1.011×10⁻¹⁶ m²/s**.
The stated value (and the "participant" value 1.477×10⁻¹⁶ with Γ = 2) is reproduced if the
prefactor is ~1.6×10⁻² m²/s. I therefore kept both activation energies (125 and 514 kJ/mol)
and recalibrated the second-term prefactor to hit exactly 1.011×10⁻¹⁶ m²/s at 1600 °C
(effective D₀,₂ = 1.79×10⁻² m²/s). Consequences: D_Cs,SiC = 1.01×10⁻¹⁶ (1600 °C),
4.7×10⁻¹⁶ (1700 °C), 2.05×10⁻¹⁵ m²/s (1800 °C) — i.e. **1800 °C is ~20× worse than 1600 °C
for Cs transport and, by the same activation energy, for SiC chemical degradation.** This
steep temperature sensitivity is the backbone of the ranking.

### Deliberate conservatisms (state of bias)

- Booth with the given kernel D′ puts 95–100 % of the stable gas in the buffer by end of
  heating (high vs typical design values) → pressure biased high.
- PyC-induced SiC compression neglected → stress biased high.
- No Cs solubility partition at the SiC inner surface, no matrix/graphite holdup → Cs release
  biased high (possibly ×3–10 for the 1600 °C cases).
- In the closed furnace, Si vapor saturation should slow SiC decomposition → case B failure
  count biased high.

---

## 2. Derived quantities (nominal model, at end of test)

| Case | P_peak (MPa) | Gas in buffer | O/F (CO) | σ_SiC end (MPa) | t_SiC,eff end (µm) | Cs corrosion δ/t | E[failures] |
|---|---|---|---|---|---|---|---|
| A1 | 22 | 1.00 | 0.062 | 125 | 35.4 | 0.41 | 0.010 |
| A2 | 27 | 0.95 | 0.002 | 162 | 33.0 | 0.77 | 0.28 |
| B  | 40 | 1.00 | 0.15 (capped) | 348 | 23.6 | 1.00 | 283 |
| C1 | 37 | 0.99 | 0.038 | 208 | 35.6 | 0.32 | 0.042 |
| C2 | 26 | 0.97 | 0.008 | 148 | 35.6 | 0.30 | 0.003 |

Even at 40 MPa internal pressure the pristine-SiC stress (≈350 MPa at the thinned end-state,
≈150–250 MPa un-thinned) sits well below the 873 MPa Weibull scale strength; with m = 8.02 the
pressure-vessel failure probability of undamaged SiC is ≤10⁻⁵ per particle everywhere. **All
predicted failures are therefore driven by high-temperature SiC degradation (thinning +
corrosion strength loss), which only bites at 1800 °C.**

---

## 3. Per-case predictions

### Case A1 — HFR-K3/1, 1600 °C / 500 h (7.7 %FIMA, sphere, 16,400 particles)

Lowest burnup → lowest pressure (22 MPa at 1873 K); σ ≈ 125 MPa; decomposition removes only
0.6 µm in 500 h; Cs corrosion reaches 41 % of the wall. Pf stays ~6×10⁻⁷ per particle.
- **Failures: 0** (expected value 0.01) — *confidence: high.*
- **Onset: none.** — *confidence: high.*
- **Kr-85: < 6×10⁻⁵ (one-particle threshold); expect ~1×10⁻⁵** (baseline contamination only)
  — *confidence: high.*
- **Cs-137: ~1×10⁻²** (band 3×10⁻³–3×10⁻²). Diffusion through intact SiC; the hot irradiation
  (centre 1216 °C) pre-penetrates ~6 µm of the wall and the 500 h at 1600 °C is comparable to
  the shell breakthrough lag (t_SiC²/6D ≈ 590 h), so release is in the steep early-rise phase.
  *Confidence: low-medium (model is deliberately conservative-high).*

### Case A2 — HFR-K3/3, 1800 °C / 100 h in two segments (10.6 %FIMA inventory, sphere)

Cold irradiation (700–983 °C) means little CO and only 28 % of gas in the buffer at start of
heating — but the 1800 °C exposure drives buffer gas to 95 % and Cs corrosion to 77 % of the
wall; thinning 3 µm. Pf climbs to 1.7×10⁻⁵ per particle, almost all of it accumulated in the
second 1800 °C segment.
- **Failures: 0–1** (expected value 0.28; P(≥1) ≈ 24 %; sensitivity band 0.09–1.4)
  — *confidence: medium-low.*
- **Onset: if a failure occurs, in the second 1800 °C segment** (≈60–100 h cumulative at
  1800 °C) — *confidence: medium.*
- **Kr-85: ~3×10⁻⁵, ≤1×10⁻⁴** (i.e. at or below the one-particle level) — *confidence: medium.*
- **Cs-137: ~0.11** (band 0.05–0.2). At 1800 °C the SiC breakthrough lag is only ~29 h, so even
  intact particles leak Cs at a quasi-steady rate; 100 h at 1800 °C ⇒ ~11 % of inventory.
  *Confidence: medium.*

### Case B — HFR-K6/3, staged 1600/1700/1800 °C + 1800 °C × 300 h (10.9 %FIMA, sphere, 14,580 particles)

Worst case by design: long hot irradiation (634 efpd at 1140 °C → all gas in the buffer,
significant CO, Cs pre-penetration ~8 µm), then 400 h total at 1800 °C. Decomposition removes
~12 µm of SiC (36→24 µm), Cs corrosion penetrates the full wall (δ/t = 1 at ~50 h into the
final phase), pressure reaches ~40 MPa ⇒ end-state σ ≈ 350 MPa against a corroded strength of
~570 MPa; with m = 8, Pf ≈ 2 %.
- **Failures: ~300 of 14,580 (~2 %)**; credible band 25–2000 — *confidence: low (order of
  magnitude); this number is the most model-sensitive of the set.*
- **Onset: first failure expected near the end of the 1700 °C / 100 h hold** (E[n] crosses 1 at
  ~253 h into the schedule); ~15 failures by the end of the first 1800 °C hold; **~95 % of all
  failures during the final 1800 °C / 300 h phase** — *confidence: medium.*
- **Kr-85: ~2×10⁻²** (band 1×10⁻³–1.5×10⁻¹) — *confidence: low.*
- **Cs-137: ~0.5** (band 0.3–0.7): ~0.47 leaks through (fully corrosion-penetrated) intact SiC
  over 400 h at 1800 °C + the failed-particle contribution — *confidence: medium.*

### Case C1 — HFR-P4/3-7, 1600 °C / 304 h (13.9 %FIMA, compact, 1631 particles)

Highest burnup and fluence of the set → highest 1600 °C pressure (37 MPa) and σ ≈ 208 MPa, but
degradation at 1600 °C is mild (0.4 µm thinning; δ/t = 0.32). Pf ≈ 2.6×10⁻⁵ per particle.
- **Failures: 0** (expected value 0.04; P(≥1) ≈ 4 %; if one occurs, late in the hold)
  — *confidence: medium-high.*
- **Onset: none expected** — *confidence: high.*
- **Kr-85: < 6×10⁻⁴ (compact one-particle threshold); expect ~4×10⁻⁵** — *confidence: high
  (threshold statement), the point value is indicative only.*
- **Cs-137: ~2×10⁻³** (band 2×10⁻³–8×10⁻³, judged possible down to ~1×10⁻³) — *confidence:
  low-medium.* Note the *fractional* intact-particle Cs release is nearly burnup-independent;
  C1's higher burnup shows up in pressure margin and in absolute becquerels (annex §8), plus a
  slightly deeper irradiation pre-penetration (hotter irradiation).

### Case C2 — HFR-P4/1-12, 1600 °C / 304 h (11.1 %FIMA, compact)

Burnup twin of C1 at 11.1 %FIMA, cooler irradiation (940 °C): P = 26 MPa, σ ≈ 148 MPa,
Pf ≈ 1.6×10⁻⁶.
- **Failures: 0** (expected value 0.003) — *confidence: high.*
- **Onset: none** — *confidence: high.*
- **Kr-85: < 6×10⁻⁴; expect ~1×10⁻⁵** — *confidence: high.*
- **Cs-137: ~1.3×10⁻³** (band 1×10⁻³–5×10⁻³) — *confidence: low-medium.*
- **C1 vs C2 (burnup effect at fixed 1600 °C/304 h):** the pair differ mainly in pressure
  (37 vs 26 MPa) and failure expectation (0.04 vs 0.003, i.e. ×13) — a strong burnup
  sensitivity in *margin*, but both remain at zero failures because 1600 °C degradation is too
  mild to close the strength gap.

---

## 4. Sensitivity study (expected failures / Kr-85 / Cs-137)

Variants: Cs-corrosion strength knock-down 0.20/0.35/0.50; CO on/off; decomposition rate ×3, ÷3;
D_Cs,SiC ×1.46 (the "participant" calibration).

| Case | E[failures] min…max | Kr-85 min…max | Cs-137 min…max |
|---|---|---|---|
| A1 | 0.002…0.02 | 1.0…1.1×10⁻⁵ | 1.1…2.6×10⁻² |
| A2 | 0.09…1.4 | 1.5…9.1×10⁻⁵ | 0.11…0.17 |
| B  | 12…2170 (runaway to all-fail at dec ×3) | 8×10⁻⁴…(1) | 0.47…0.90 |
| C1 | 0.017…0.067 | 2.0…5.1×10⁻⁵ | 2.3…7.8×10⁻³ |
| C2 | 0.002…0.004 | 1.1…1.2×10⁻⁵ | 1.3…5.0×10⁻³ |

The 1600 °C zero-failure conclusions and the ranking are robust across the envelope; the
absolute counts for B (and to a lesser degree A2) are not — see §6.

---

## 5. Ranking and why

**B > A2 > C1 > A1 > C2.**

1. **Temperature is the first-order variable.** Every degradation channel in the model
   (Cs-in-SiC transport, SiC decomposition) carries an activation energy of ~500 kJ/mol at
   these temperatures ⇒ a 200 °C step from 1600 to 1800 °C multiplies the damage rate by ~20.
   That is why the two 1800 °C cases (B, A2) dominate, and within them time-at-1800 °C sets the
   order: B (400 h) ≫ A2 (100 h). At 1600 °C, even 500 h (A1) or 304 h at 13.9 %FIMA (C1)
   cannot close the gap between ~150–210 MPa stress and ~800 MPa corroded strength.
2. **Burnup is the second-order variable.** It scales the gas + CO inventory and hence pressure
   (roughly linearly) and the absolute activity at stake. It orders the 1600 °C trio
   (C1 > A1 ≈ C2 in failure expectation; ×13 between the burnup twins C1/C2) and compounds
   case B (10.9 %FIMA over 634 efpd, the largest CO term). But with m = 8 Weibull statistics,
   pressure alone never reaches the failure threshold in these tests — only the
   temperature-driven strength/thickness degradation does.
3. Fast fluence enters only weakly here (the annex fixes Γ = 2 in Eq 10.9 for all cases; PyC
   shrinkage effects are a compressive benefit that was conservatively neglected).

---

## 6. Most uncertain assumption

**The high-temperature SiC degradation kinetics** — specifically (i) the thermal-decomposition
thinning rate, for which the annex provides no correlation and which I anchored by a single
engineering point (full 36 µm layer consumed in ~10 h at 2200 °C) with the annex's own
514 kJ/mol activation energy, and (ii) the assumed 35 % strength knock-down at full Cs-corrosion
penetration. Because failure probability goes as (σ/σ₀)^8, modest changes in either assumption
move the 1800 °C failure counts by an order of magnitude (case B: 25→2000). The 1600 °C
"zero failures, Kr below one-particle threshold" conclusions, the failure onset locations, and
the case ranking survive the whole sensitivity envelope; the absolute failure count of case B
does not. Second most uncertain: the CO estimate (not annex-covered; switching it off cuts
case B's expected failures ~20×) and the no-partition Cs boundary condition (Cs releases are
upper-leaning, plausibly high by ×3–10 at 1600 °C).

---

## 7. Results summary

| Case | Failures (of N) | Onset | Kr-85 release | Cs-137 release |
|---|---|---|---|---|
| A1 | 0 / 16,400 | none | < 6×10⁻⁵ (≈1×10⁻⁵) | ~1×10⁻² |
| A2 | 0–1 / 16,400 (E=0.3) | if any: 2nd 1800 °C segment | ≤1×10⁻⁴ (≈3×10⁻⁵) | ~0.11 |
| B | ~300 / 14,580 (25–2000) | end of 1700 °C hold; bulk in final 1800 °C/300 h | ~2×10⁻² | ~0.5 |
| C1 | 0 / 1631 (E=0.04) | none expected | < 6×10⁻⁴ (≈4×10⁻⁵) | ~2×10⁻³ |
| C2 | 0 / 1631 | none | < 6×10⁻⁴ (≈1×10⁻⁵) | ~1.3×10⁻³ |

Files: `triso_model.py` (model), `results.json` (machine-readable predictions incl. ranges and
confidence), `model_run.log` (full nominal + sensitivity output).
