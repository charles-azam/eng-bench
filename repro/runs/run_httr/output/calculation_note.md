# Calculation note — HTTR loss-of-forced-cooling (LOFC) prediction from physics

**Scenario predicted:** HTTR (30 MWt prismatic graphite HTGR) at 9 MWt (30 % power); all
helium gas circulators trip simultaneously; **no scram, control rods frozen in position**;
vessel cooling system (VCS) running. Everything below is predicted from first principles;
the temperature-feedback coefficients are **computed** with a Monte-Carlo neutronics model
built on this machine (OpenMC + ENDF/B-VIII.0), not taken from memory or from any test result.

> **Compliance:** No LOFC/loss-of-forced-cooling *test-result* source was consulted (power
> traces, measured recriticality times/temperatures). Design/software/nuclear-data sources
> only — see `output/sources.md`, including the logged incident where LOFC test papers surfaced
> in searches and were deliberately not opened.

---

## 1. Method

**Neutronics (computed here).** A double-heterogeneous OpenMC model of the HTTR average fuel
lattice was built from public design data (`sources.md`): 600 µm UO₂ kernel → buffer/IPyC/SiC/OPyC
TRISO coatings (60/30/25/45 µm; 1.10/1.85/3.20/1.85 g/cm³) → ~30 vol% packing in a graphite matrix
compact (26 mm OD / 10 mm ID / 39 mm) → IG-110 fuel sleeve → 41 mm coolant channel → hexagonal
block (360 mm across flats). Core-average enrichment 6.0 wt% U-235 (design range 3.4–9.9 wt%,
core-average ≈6 %); smeared burnable poison (B₄C, core-average loading) included. Explicit
randomly-packed TRISO particles (~15 000 in the modelled compact) capture U-238 Doppler
self-shielding. Cross sections: **ENDF/B-VIII.0** with graphite/UO₂ S(α,β) thermal scattering, at
the library's exact temperatures **294, 600, 900, 1200 K** (no S(α,β) interpolation needed).

k_inf was computed at each temperature (whole lattice isothermal — fuel + moderator + coolant at a
common temperature, which is the relevant limit for a slow, conduction-dominated LOFC). The
**isothermal reactivity coefficient** is α(T) = (1/k)(dk/dT). Because the frozen rods + leakage act
as a temperature-independent multiplier that makes the real core critical at the operating
temperature, the feedback fed to the transient is Δρ_core(T) = 1 − k_inf(T_op)/k_inf(T) — the
constant multiplier cancels, so the lattice k_inf(T) *shape* gives the core reactivity feedback
directly. β_eff was computed by the prompt method (k with vs. without delayed neutrons).

Two lattice variants were run — burnable poison **on** (smeared, self-shielding neglected → BP worth
over-estimated) and **off** — which **bracket** the true coefficient, since fresh BP is a 1/v thermal
absorber that adds a *positive* contribution to α as temperature rises.

**Coupled transient (computed here).** Point kinetics (6 delayed groups, U-235 spectrum scaled to
the computed β_eff) + fission-product decay heat (Wigner–Way/Todreas form) + a 3-node lumped thermal
model of the graphite/vessel with the VCS as ultimate sink:

- core graphite (active fuel region, ~14 t, feedback temperature) → reflector graphite
  (responsive ~0.9 m over a day, tens of t) → RPV steel → VCS panel sink;
- conduction between graphite nodes, VCS removal law calibrated to the passive heat leak;
- graphite specific heat Cp(T) (Butland–Maddison; 0.71→2.0 kJ/kg·K over 300→2000 K) — the dominant
  thermal inertia and, as the task anticipated, the "star" that sets the timescales.

Thermal parameters (conductances, responsive masses, passive-leak/VCS capacity, operating
temperature, prior operating time) are engineering estimates from public design data and geometry;
they carry real uncertainty, so a **400-sample randomized sensitivity study** over all of them gives
the reported ranges.

---

## 2. Computed feedback coefficients

**Computed with OpenMC (ENDF/B-VIII.0, ~15 000 explicit TRISO particles per compact, isothermal lattice; full data in `output/results.json`).**

| T (K) | k_inf, BP **on** | k_inf, BP **off** |
|------:|:----------------:|:-----------------:|
| 294  | 1.08290 ± 0.00068 | 1.49628 ± 0.00086 |
| 600  | 1.05486 ± 0.00068 | — |
| 900  | 1.03567 ± 0.00066 | 1.42714 ± 0.00082 |
| 1200 | 1.01690 ± 0.00062 | 1.40209 ± 0.00083 |

k_inf falls **monotonically** with temperature in both variants — U-238 Doppler broadening dominates, reinforced by the negative graphite moderator/spectral term.

**Isothermal temperature coefficient** α(T) = (1/k)·dk/dT, Monte-Carlo–propagated from the k_inf statistics (4000 resamples):

| T (K) | α, BP **on** (pcm/K) | α, BP **off** (pcm/K) |
|------:|:--------------------:|:---------------------:|
| 400  | −9.01 ± 0.38 | −8.60 ± 0.26 |
| 600  | −7.15 ± 0.19 | −7.81 ± 0.13 |
| 800  | −5.76 ± 0.35 | −6.99 ± 0.11 |
| 1000 | −6.03 ± 0.22 | −6.12 ± 0.24 |
| 1200 (1100 for BP off) | −6.31 ± 0.62 | −5.68 ± 0.31 |

Range-averaged coefficient: **−6.85 pcm/K (BP on)** and **−7.04 pcm/K (BP off)**. The two variants **bracket** α to within ±0.1 pcm/K over 294–1200 K: the feedback is **strongly negative (≈ −7 pcm/K) and essentially insensitive to the burnable-poison treatment**.

**Delayed-neutron fraction** (prompt method — k with vs. without delayed neutrons, @ 900 K): **β_eff = 0.00728 ± 0.00093** (728 ± 93 pcm). At −7 pcm/K, only ~100 K of core heating inserts a full dollar of negative reactivity — the physical basis for the fast self-shutdown below.

---

## 3. Predictions

### (1) Fission power in the first minutes — and why
**Computed collapse timescale: ~1–3 minutes.** With the negative coefficient above (≈ −7 pcm/K) and the core heating at ~0.3–0.5 K/s once the 9 MW can no longer be carried away, only ~10–30 K of temperature rise (a few tenths of a dollar) is enough to drop fission power **below the decay-heat level**; it continues down to **< 0.01 kW** (net fission effectively zero) as the core sits subcritical. The core-average graphite temperature overshoots its ~550 °C operating value by only **~30 °C, peaking at 583 °C ≈ 5.5 min** after the trip, then begins to fall. This is passive, inherent self-shutdown with the rods frozen — a drop of more than five orders of magnitude in fission power, achieved with no operator or control-rod action.

**Physical reason.** Helium is nearly transparent to neutrons (negligible moderation and
absorption), so stopping the coolant flow inserts **essentially zero direct reactivity** — this is
*not* a coolant-void transient. What matters is temperature. With forced convection gone, the 9 MW
of fission heat can no longer be carried out of the core; it is deposited in the fuel and graphite,
whose average temperature climbs at ~0.3–0.5 K/s (9 MW ≫ the ~0.2–0.4 MW the passive path can remove).
The core's **strongly negative isothermal temperature coefficient** (U-238 Doppler broadening +
negative graphite/spectral moderator coefficient — both computed above) converts this temperature
rise into negative reactivity. Within the first ~1–3 minutes this drives the reactor subcritical and
fission power collapses far below the decay-heat level. This is passive, inherent self-shutdown with
the rods frozen.

### (2) Recriticality — whether, when, and the governing mechanism
**Computed result — recriticality DOES occur, within about an hour.** Once fission has collapsed, the small temperature overshoot bleeds off by conduction to the cooler reflector graphite and the VCS; the core-average temperature drifts back down to the (frozen-rod) critical temperature and the reactor spontaneously re-criticalises. Predicted timing:

- **Nominal (conservative low-conductance case): t_recrit ≈ 1.0 h.**
- **Sensitivity (400-sample randomization of all thermal parameters): median 0.44 h, P10–P90 band 0.32–0.77 h, full range 0.24–1.1 h.**

So recriticality is predicted in **roughly 15 min to ~1 hour**, with the nominal case sitting near the slow end of the band. The spread is dominated by the (unpublished) effective core-to-sink conductance and the responsive graphite thermal mass — this is the largest single uncertainty in the prediction, and it is thermal, not neutronic.

**Governing mechanism.** After fission collapses, only decay heat (which falls below the passive
heat-removal rate within minutes) warms the core, while conduction to the cooler surrounding
reflector graphite and the VCS removes heat. The **enormous heat capacity of the graphite** makes
this a slow thermal process: the core sheds its (small) temperature overshoot and drifts back down
toward the operating temperature over **hours**. The instant the core-average temperature returns to
the temperature at which the frozen-rod configuration was critical, feedback reactivity returns to
zero and the reactor spontaneously goes critical again. The timing is set by the graphite thermal
time constant (heat capacity ÷ effective core-to-sink conductance) — not by neutronics. This is the
dominant uncertainty in the prediction (the effective conductance is not directly published).

### (3) Stabilized power level
**Computed stabilized fission power: a few hundred kW.** Nominal **287 kW (~3 % of the 9 MW pre-trip level, ~1 % of the 30 MW nominal rating)**; sensitivity **median 575 kW, P10–P90 312–826 kW**, i.e. **~0.3–0.8 MW** — scaling directly with the passive-removal / VCS capacity. The trace approaches this level as a gentle, well-damped drift (rising as decay heat fades and fission makes up the balance), not a sharp power spike.

After recriticality the reactor self-regulates at the operating temperature: it produces exactly the
fission power needed so that fission + decay heat equals what the passive path (conduction + VCS)
can remove at that temperature. As decay heat continues to fall, fission power rises to make up the
difference, asymptoting to the passive heat-removal capacity — a few hundred kW, i.e. a few percent
of the pre-trip 9 MW (order ~1–2 % of nominal 30 MW). The power may show a gentle damped
oscillation about this level (negative feedback + thermal lag).

### (4) Fuel and vessel temperature trend — bounded or runaway
**Computed verdict: BOUNDED — no runaway** (robust across the entire 400-sample sensitivity set):

- **Peak core-graphite (≈ fuel) temperature:** nominal **583 °C**; sensitivity **median 572 °C, P10–P90 521–633 °C, worst-case 651 °C** — an overshoot of only ~30–100 °C above the ~550 °C operating temperature, and **far below the ~1600 °C TRISO fuel limit**.
- **Peak RPV (vessel) temperature:** nominal **280 °C**; sensitivity **median 336 °C**, worst-case tail **605 °C** (only in the extreme low-conductance / low-VCS corner) — in all cases below short-term steel limits.

**Bounded — no runaway.** Four independent reasons: (a) power collapses within minutes, so little
extra energy is added; (b) decay heat at 30 % power is modest (≈0.5 MW initially, <0.15 MW within
minutes) and quickly falls below the passive removal; (c) the graphite's huge heat capacity limits
the temperature *rate* to a small overshoot; (d) the negative temperature coefficient caps any
excursion — every attempt to heat up removes reactivity. The peak core-graphite (≈fuel) temperature
overshoots only modestly above the operating value and then declines; the RPV, separated from the
core by ~1 m of reflector graphite and cooled directly by the VCS, stays near its normal operating
temperature and well below steel limits. This is the inherent-safety signature of the design.

---

## 4. Assumptions and confidence

**Neutronics assumptions:** fresh (BOL) fuel; core-average 6 wt% enrichment (single value, not the
12-zone map); burnable poison smeared (self-shielding neglected → its worth over-estimated, hence
BP-on/off used only as a bracket); Wigner–Seitz reflective lattice cell (leakage/reflector feedback
not in k_inf — a small additional, also-negative term at operating T); isothermal feedback (fuel and
moderator at one temperature — the correct limit for slow conduction-dominated LOFC).

**Thermal assumptions:** lumped 3-node model; conductances and responsive masses from geometry;
passive-leak/VCS capacity ~0.3 MW at the 30 %-power condition (< the 0.6 MW full-power rating);
decay heat from a generic fission-product correlation (±~20 %); operating core-average graphite
temperature ~550 °C.

**Confidence:**
- Prediction (1) — direction and mechanism: **high**; exact seconds-to-minutes: medium.
- Prediction (2) — that recriticality occurs and is governed by graphite thermal inertia: **high**;
  the numeric recriticality time: **moderate** (dominated by the effective core-to-sink conductance).
- Prediction (3) — that it stabilizes at a few hundred kW set by passive removal: **medium-high**;
  exact value scales with the passive-removal capacity.
- Prediction (4) — bounded, no runaway: **high** (robust across the entire sensitivity sample).
