# Calculation note — TRISO particle failure under accident heating (cases A1, A2, B, C1, C2)

**Scope.** All numbers below are derived offline from the physics and correlations in
`inputs/03_material_properties.md` (TECDOC-1674 equation numbers, as cited) plus the
geometry/irradiation/heating data in `inputs/01_particles_and_elements.md` and
`inputs/02_cases.md`. No published results for HFR-K3, HFR-K6 or HFR-P4 were consulted. A
small number of **generic, non-benchmark-specific** nuclear-engineering constants (fission-product
yields, isotope half-lives, the ideal-gas law, standard thin-shell pressure-vessel and
composite-shell mismatch mechanics) were needed to close the model and are flagged **[GENERIC]**
throughout — these are textbook/general reactor-physics facts, not this benchmark's measured
outcomes. Working scripts: `calc.py` (constants & correlations), `cases.py` (case data
transcription), `main.py` (per-case model, produces all numbers quoted here — run
`python3 main.py` to reproduce).

## 1. Modelling approach — overview

Failure of a particle is taken to occur when the SiC layer's net tangential (hoop) stress
exceeds its strength in the Weibull sense (§3 of the annex). Three stress contributions are
computed and superposed:

1. **Internal-gas-pressure stress** — from fission-gas (Kr+Xe) accumulating in the buffer void
   and expanding as the particle heats, treated with the thin-wall spherical pressure-vessel
   formula σ_p = P·r/(2t) **[GENERIC mechanics]**, r = SiC mean radius, t = SiC thickness. The
   gas quantity that has left the kernel by any time is obtained from the **equivalent-sphere
   kernel-diffusion release model (Eqs 10.7/10.8)** using the "stable & long-lived" Xe/Kr
   coefficient (Table 7.1), integrated as a running Fourier number Fo = Σ D′(T)·Δt over the
   *entire* thermal history (irradiation, then every ramp/hold of the furnace schedule — ramps
   split into 20 sub-steps, holds into 40, for numerical resolution). Pressure P = n_released·R·T/V_free
   (ideal gas law **[GENERIC]**).
2. **Thermal-mismatch stress** — from the different coefficients of thermal expansion of PyC and
   SiC (Table 9.6) as the particle is heated above its irradiation temperature. Modelled with a
   3-layer (IPyC+SiC+OPyC) force-balance/compatibility composite-shell derivation (below), purely
   elastic — irradiation creep needs fluence, not time, and no flux exists during the furnace test.
3. **Irradiation-induced PyC/SiC "preload" stress** — the compressive stress the annex describes
   ("IPyC/OPyC shrink and put the SiC into compression", §1) is derived from the PyC dimensional-
   change correlation (e) (Eq 9.22) and the PyC creep coefficient (Eq 9.23/Table 9.14), using a
   creep-relaxed steady-state balance (derived below), evaluated at each case's fluence and
   irradiation temperature.

The net driving stress σ_net = σ_p + σ_th + σ_preload (preload is negative/compressive) is tracked
through the whole furnace schedule; its **peak value** sets the Weibull failure probability per
particle, Pf = 1 − exp[−(σ_net/873)^8.02] (Table 9.14), and the **expected number of failed
particles** = N_particles × Pf. Once failed, a particle's further release is governed by kernel
diffusion alone (Eqs 10.7/10.8, per the annex's explicit instruction, §6) using the kernel
diffusion rows for Kr/Xe and Cs (Table 7.1). Intact particles retain Cs behind the SiC diffusion
barrier (Eq 10.9) and are assumed to retain essentially all Kr-85 (SiC/graphite offer no credible
noble-gas transport path; no such diffusion datum is given, consistent with real TRISO behaviour).

### 1.1 Composite-shell derivations used (not given verbatim in the annex; derived here)

For a thin spherical shell system of dense PyC (IPyC, thickness t_i, and OPyC, thickness t_o,
same modulus E_p) bonded to SiC (thickness t_s, modulus E_s), let ε be the common tangential
strain at the interface (compatibility) and ε0 the *unconstrained* strain the PyC alone would
adopt. Force balance over the composite cross-section (self-equilibrated, no external load):
σ_i·t_i + σ_s·t_s + σ_o·t_o = 0.

- **Thermal step (elastic, fast):** σ_i = E_p·(ε−ε0), σ_s = E_s·ε, with ε0 = (α_PyC−α_SiC)·ΔT.
  Solving the two equations:

      σ_s = E_s·(E_p·t_i + E_p·t_o)·ε0 / (E_p·t_i + E_s·t_s + E_p·t_o)

  This is the standard result that a compliant PyC layer cannot force its full free thermal
  strain onto the much stiffer SiC (E_SiC ≈ 9.3× E_PyC); ignoring PyC compliance (treating it as
  rigid) would overstate σ_th by roughly 6× for these geometries — this correction was checked
  numerically and applied throughout.
- **Irradiation swelling/creep step (steady state):** PyC creep is very fast relative to the
  fluence scale of these cases — the relaxation rate E_PyC·K(T) ≈ 20 per unit x (10²⁵ n/m²,
  E>0.18 MeV) for the given creep coefficient (Eq 9.23), i.e. a pure elastic shrink-fit stress
  would relax by e⁻²⁰ within Δx ≈ 0.05, far below any case's fluence (3.5–6.8). The system is
  therefore essentially always in creep-controlled steady state, where dσ_p/dx ≈ 0 and (from the
  PyC creep constitutive law dε/dx = dε0/dx + K·σ_p, with dε/dx ≈ 0 at steady state):

      σ_p = −(dε0/dx) / K(T_irr)              (per PyC layer, independent of SiC's stiffness)
      σ_preload = σ_s = (t_i + t_o)/t_s · (dε0/dx) / K(T_irr)   (force balance)

  using the *local slope* (not the accumulated strain) of the tangential swelling correlation (e)
  at the case's fluence. This predicts near-zero preload once the swelling curve saturates
  (x > 6.08, dε/dx → 0, correlation (e) constant branch) — physically sensible: once the driving
  swelling rate dies out, creep has had time to relax any transient stress.

## 2. Key generic assumptions (flagged, with confidence)

| # | Assumption | Value used | Basis | Confidence |
|---|---|---|---|---|
| 1 | Total stable+radioactive Kr+Xe fission-gas yield | 0.30 atoms/fission | [GENERIC] typical U-235 thermal-fission cumulative noble-gas yield | Medium |
| 2 | Kr-85 cumulative fission yield | 0.0133 atoms/fission | [GENERIC] standard fission-yield data | Medium-High |
| 3 | Cs-137 cumulative fission yield | 0.0619 atoms/fission | [GENERIC] standard fission-yield data | Medium-High |
| 4 | Kr-85 / Cs-137 half-lives | 10.76 y / 30.17 y | [GENERIC] nuclear data | High |
| 5 | Buffer free (void) volume | porosity = 1 − ρ_buffer/ρ_dense-PyC ≈ 0.47, applied to the as-fabricated buffer shell volume | Derived from the annex's own buffer/IPyC densities (§1 of inputs 01), **not corrected for kernel swelling encroaching into the buffer during irradiation** | Low-Medium (likely overestimates free volume → underestimates pressure) |
| 6 | CO (excess-oxygen) internal pressure | **0 in the base case**; sensitivity at 0.1 / 0.3 / 1.0 CO molecules per fission | Annex gives no CO yield formula; this is flagged as **the single most uncertain input** (§4) | **Low** |
| 7 | Average heavy-metal atomic mass | 238 − enrichment-weighted | [GENERIC] | High |
| 8 | Weibull failure driven by the *peak* stress reached (no sub-critical crack growth / no proof-test population depletion) | — | Simplification | Medium |
| 9 | Post-failure release fraction is independent of the exact failure time | — | Buffer + cracked SiC add negligible diffusive resistance compared with the kernel itself (kernel diffusion is explicitly stated to control, §6) | Medium-High |
| 10 | Intact-particle Cs-137 release via SiC | two variants computed: an explicit **upper bound** (spherical-release analogy applied to the SiC shell — over-estimates because it assumes a uniformly-distributed source rather than one-face permeation) and an **illustrative best estimate** (pre-breakthrough small-Fourier-number damping, exp[−1/(4·Fo_SiC)]) | Neither is a rigorous shell-permeation (Crank) solution; both are order-of-magnitude only | **Low** |
| 11 | Intact-particle Kr-85 release | ≈ 0 | SiC/graphite present no credible noble-gas diffusion path; no coefficient is given, consistent with known TRISO behaviour | Medium-High |

## 3. Per-case results

### 3.1 Geometry & fission-product inventory (per particle)

| Case | Batch | r_kernel (µm) | V_free,buffer (µm³) | Fissions/particle | Gas atoms (Kr+Xe)/particle | Kr-85 atoms (t=0, decay-corrected) | Cs-137 atoms (t=0) |
|---|---|---|---|---|---|---|---|
| A1 | EUO 2308 | 248.5 | 4.93×10⁷ | 1.22×10¹⁷ | 3.65×10¹⁶ | 1.57×10¹⁵ | 7.44×10¹⁵ |
| A2 | EUO 2308 | 248.5 | 4.93×10⁷ | 1.61×10¹⁷ | 4.83×10¹⁶ | 2.08×10¹⁵ | 9.86×10¹⁵ |
| B  | EUO 2358–65 | 254.0 | 5.64×10⁷ | 1.79×10¹⁷ | 5.36×10¹⁶ | 2.25×10¹⁵ | 1.08×10¹⁶ |
| C1 | EUO 2308 | 248.5 | 4.93×10⁷ | 2.20×10¹⁷ | 6.59×10¹⁶ | 2.84×10¹⁵ | 1.35×10¹⁶ |
| C2 | EUO 2308 | 248.5 | 4.93×10⁷ | 1.76×10¹⁷ | 5.27×10¹⁶ | 2.26×10¹⁵ | 1.08×10¹⁶ |

### 3.2 Failure prediction (fission-gas-only base case, no CO)

Onset is defined as the first time, *within the final hold at the case's designated peak
temperature* (the "case of interest" per `02_cases.md` — this excludes locking onto a transient
stress spike during an earlier intermediate excursion, e.g. A1's 1550 °C dwell before its
drop-and-reheat to 1600 °C), that the driving stress reaches 90% of its value at the end of that
hold.

| Case | Fluence x (10²⁵, E>0.18 MeV) | In-pile gas release fraction (end of irradiation) | Peak σ_p (MPa) | Peak σ_th (MPa) | σ_preload (MPa) | σ_net (MPa) | Pf (per particle) | **E[N failed]** | Onset (time, T) |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 3.55 | 0.935 | 107 | 21 | −6 | 122 | 1.4×10⁻⁷ | **0.002** | ~53.5 h — i.e. ~13 h into the final 1600 °C/500 h hold |
| A2 | 5.45 | 0.280 | 148 | 41 | −26 | 164 | 1.5×10⁻⁶ | **0.024** | ~133 h — ~20 h into the **2nd (final) 1800 °C segment** (the 74.5 h stage) |
| B  | 4.36 | 0.995 | 156 | 27 | −10 | 173 | 2.3×10⁻⁶ | **0.034** | ~406.5 h — ~7.5 h into the **4th stage**, the further 300 h hold at 1800 °C |
| C1 | 6.82 | 0.853 | 191 | 23 | 0* | 213 | 1.2×10⁻⁵ | **0.020** | ~52 h — ~23 h into the 1600 °C/304 h hold (fast — most gas already released in-pile) |
| C2 | 5.00 | 0.502 | 149 | 28 | −20 | 157 | 1.0×10⁻⁶ | **0.002** | ~158 h — ~129 h into the 1600 °C/304 h hold (slower — less gas pre-released in-pile) |

*C1's fluence (6.82) is past the correlation-(e) saturation break (6.08); the local swelling rate
there is ≈0 so the derived steady-state preload is ≈0.

**Interpretation: in the base (fission-gas-only) case, the model predicts effectively zero
SiC failures in all five tests** (expected counts 0.002–0.034 out of 14,580–16,400 sphere
particles or 1,631 compact particles) — consistent with the generally excellent accident
performance of good-quality TRISO fuel and with the annex's own framing (§8) that these tests are
interpreted at the granularity of single failed particles, not bulk failure. Confidence in this
absolute conclusion is **Low-Medium**: it is highly sensitive to assumption #6 (CO), see §4.

A physically notable, robust result: **onset timing tracks each case's *in-pile* gas-release
history, not just the furnace schedule.** C1 (highest burnup, hottest irradiation history, 85%
of its gas already released before the furnace test starts) reaches 90% of its final-hold stress
level within the first quarter of the 1600 °C/304 h hold; C2 (lower burnup/irradiation-T, only 50%
pre-released) needs nearly the whole 304 h hold to catch up, even on an *identical* furnace
schedule. For the staged case B, the driving stress is already close to its final value by a few
hours into the last (300 h) 1800 °C phase — most of the cumulative gas release has already
occurred during the preceding 1600 °C/1700 °C/1800 °C stages.

### 3.3 Final fractional release of Kr-85 and Cs-137 (base case)

Element-level release = (fraction of population failed) × (release fraction of a failed
particle) + (fraction intact) × (intact-particle release, ≈0 for Kr-85). Failed-particle release
fractions use Eqs 10.7/10.8 with the kernel D′ for Kr/Xe (stable/long-lived row) and for Cs
(Table 7.1) over the full thermal history — both come out to ≈0.95–1.00 (kernel diffusion is fast
enough, especially for Cs, that a failed particle releases nearly its whole current inventory
over these test durations).

| Case | Kr-85 release if failed | Cs-137 release if failed (kernel) | Intact-particle Cs-137 (illustrative best-est. / upper bound) | **Element Kr-85 release** | **Element Cs-137 release** | vs. 1-particle threshold (§8) |
|---|---|---|---|---|---|---|
| A1 | 0.999 | 1.000 | 2.4×10⁻⁵ / 0.463 | **1.4×10⁻⁷** | **2.4×10⁻⁵** | below (6×10⁻⁵ for spheres) |
| A2 | 0.947 | 1.000 | 4×10⁻¹⁰ / 0.337 | **1.4×10⁻⁶** | **1.5×10⁻⁶** | below |
| B  | 1.000 | 1.000 | 7.6×10⁻³ / 0.635 | **2.3×10⁻⁶** | **7.6×10⁻³** | Kr-85 below; **Cs-137 above** — driven by the intact-particle SiC-permeation term, not by failures |
| C1 | 0.989 | 1.000 | 3.6×10⁻⁸ / 0.375 | **1.2×10⁻⁵** | **1.2×10⁻⁵** | below (6×10⁻⁴ for compacts) |
| C2 | 0.965 | 1.000 | 3.6×10⁻⁸ / 0.375 | **1.0×10⁻⁶** | **1.1×10⁻⁶** | below |

Cross-check: dividing each element Kr-85 release by the §8 single-particle threshold
(6×10⁻⁵ for spheres, 6×10⁻⁴ for compacts) reproduces E[N failed] from §3.2 to within a few
percent in every case — an internal consistency check on the failed-particle release
calculation, independent of the stress model.

Note the one qualitative outlier: **case B's Cs-137 release is dominated by the intact-particle
SiC-permeation term** (its longest-and-hottest exposure — 1600→1700→1800 °C over ~700 h, then a
further 300 h at 1800 °C — pushes its accumulated SiC Fourier number the closest to the
breakthrough regime of any case), not by particle failures. This term carries **Low** confidence
(assumption #10) but the qualitative point — B is the case where the SiC diffusion barrier itself
is under the most sustained thermal challenge — is judged **Medium** confidence.

## 4. Sensitivity to the CO (excess-oxygen) pressure assumption — the most uncertain input

The annex gives no CO-generation formula, so the base case above carries **zero CO pressure**.
Because UO₂ fission produces excess oxygen (fission-product oxides average valence < 4) which can
react with the carbon buffer to form CO, and because CO pressure adds directly and linearly to
the same pressure-vessel stress term while the Weibull exponent (m = 8.02) makes Pf extremely
steep in stress, this single unquantified input dominates the uncertainty in the absolute failure
count:

| Case | N failed, Y_CO=0 (base) | Y_CO=0.1 CO/fission | Y_CO=0.3 CO/fission | Y_CO=1.0 CO/fission (extreme bound) |
|---|---|---|---|---|
| A1 | 0.002 | 0.018 | 0.35 | 129 |
| A2 | 0.024 | 0.22 | 5.3 | 2,194 |
| B  | 0.034 | 0.28 | 5.8 | 2,122 |
| C1 | 0.020 | 0.17 | 3.5 | 941 |
| C2 | 0.002 | 0.017 | 0.41 | 185 |

A factor-of-3 change in an unquantifiable input (0.1 → 0.3 CO/fission) swings the predicted
failure count by roughly 15–20×; the extreme bound (1 CO/fission, almost certainly unrealistic —
it assumes every fission's excess oxygen fully converts to free CO gas with no getter/retention
effect) would predict near-total failure. **This is explicitly the assumption I am least
confident in**, and the absolute failure counts and release fractions in §3.2–3.3 should be read
as a physically-grounded *floor* (fission gas + thermal mismatch only), not an upper bound.

## 5. Ranking and physical reasoning

**B ≳ A2 > C1 > A1 ≈ C2**, robust across every CO-sensitivity level computed (Table §4: B and A2
are the top two in all four scenarios; C1 is consistently third; A1 and C2 trade the bottom two
places depending on the CO level, since C2's higher irradiation temperature/burnup than A1's is
partly offset by A1's higher furnace peak temperature — but both are always well behind the top
three).

- **Temperature is the dominant driver.** The two 1800 °C cases (A2, B) rank above all three
  1600 °C cases despite C1 having *higher* burnup and fluence than either. Two mechanisms both
  scale strongly with peak temperature: (i) the kernel-diffusion release rate is Arrhenius in T,
  so a 1600→1800 °C step accelerates in-pile-remaining gas release sharply; (ii) the pressure
  itself is directly proportional to absolute temperature (ideal-gas law) for whatever gas is
  already resident in the buffer. Case B compounds this by holding at 1800 °C twice (100 h + a
  further 300 h) after already passing through 1600 °C and 1700 °C stages — the longest
  cumulative high-temperature exposure of any case, which is also why it is the only case where
  the intact-particle Cs-SiC permeation term becomes significant (§3.3).
- **Burnup/fluence is a secondary but consistent driver.** Comparing C1 vs C2 — the pair that, by
  design, isolates burnup at an *identical* furnace schedule and near-identical geometry — C1
  (13.9 %FIMA, 1075 °C irradiation) predicts roughly 2× C2's failure probability and Kr-85 release
  (11.1 %FIMA, 940 °C irradiation) at every CO-sensitivity level tested. Burnup increases both the
  fission-gas inventory (linearly) and, through the higher associated irradiation temperature,
  the fraction of that inventory already released in-pile — both push pressure and hence stress
  up, though the effect is smaller than a 200 °C accident-temperature step.
- A2 vs A1 (same sphere design, A2 at higher burnup **and** higher furnace temperature) shows the
  largest swing of any pair (∼10× in the base case), consistent with these two effects compounding
  rather than a single dominant variable.

## 6. Summary table — headline numbers (base case, no CO)

| Case | E[N failed] | Onset | Kr-85 fractional release | Cs-137 fractional release | Rank (worst→least, w/ CO sensitivity) | Confidence (count / release / rank) |
|---|---|---|---|---|---|---|
| A1 | 0.002 (≈0) | ~53.5 h, ~13 h into the 1600 °C/500 h hold | 1.4×10⁻⁷ | 2.4×10⁻⁵ | 4th–5th | Low / Low-Med / Medium |
| A2 | 0.024 (≈0) | ~133 h, ~20 h into the 2nd (final) 1800 °C segment | 1.4×10⁻⁶ | 1.5×10⁻⁶ | 2nd | Low / Low-Med / Medium-High |
| B  | 0.034 (≈0) | ~406.5 h, ~7.5 h into the final 300 h/1800 °C phase | 2.3×10⁻⁶ | **7.6×10⁻³** (intact-SiC term) | 1st | Low / Low(Cs)-Med(Kr) / Medium-High |
| C1 | 0.020 (≈0) | ~52 h, fast (high in-pile pre-release) | 1.2×10⁻⁵ | 1.2×10⁻⁵ | 3rd | Low / Low-Med / Medium |
| C2 | 0.002 (≈0) | ~158 h, slow (low in-pile pre-release) | 1.0×10⁻⁶ | 1.1×10⁻⁶ | 4th–5th | Low / Low-Med / Medium |

**Bottom line:** the physics-based model predicts that, from fission-gas pressure and
thermal-mismatch stress alone, essentially no particles fail in any of these five tests (all
Kr-85 releases fall below the annex's own one-particle detection threshold), with case B and A2
(the two 1800 °C tests) the most likely to show any measurable signal, and burnup a real but
secondary amplifier best isolated in the C1/C2 pair. **The one assumption most likely to change
this conclusion is the unquantified CO/excess-oxygen contribution to internal pressure (§4)** — if
CO generation is even a few tenths of a molecule per fission, failure counts move from
"negligible" to "a handful of particles," and the Weibull statistics (m = 8.02) mean this
transition is a steep, not gradual, function of that single number.
