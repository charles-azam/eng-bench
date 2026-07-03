# TRISO Scorecard — predictions vs. furnace measurements

Measured values: KüFA/CCCTF accident-heating tests, IAEA TECDOC-1674 Table 8.2 / TECDOC-2090
Tables 19 & 21 (full provenance: `refs/measured_data.md`). All runs fully offline (0 web calls,
transcript-verified for VPS runs), property annex from the benchmark document itself.
Adversarially audited (`AUDIT.md`) — corrections applied throughout. Caveats: N=1 run per model
config; A2 burnup appears as both 10.2/10.6 %FIMA in the pack and runs differ in which they used;
the pack was manually curated and independently re-grepped clean (no automated gate).
Cases: A1 = HFR-K3/1 sphere 1600 °C/500 h · A2 = HFR-K3/3 sphere 1800 °C/100 h (sister spheres)
· B = HFR-K6/3 staged →1800 °C/300 h · C1/C2 = HFR-P4 compacts 1600 °C/304 h (13.9/11.1 %FIMA).

## Failed particles (the headline quantity)

| Case | **Measured** | Opus A | Opus B | Opus C | Fable 5 |
|---|---|---|---|---|---|
| A1 | **0** /16,400 | 0.002 ✓ | 0.06 ✓ | 0 ✓ | 0 ✓ |
| A2 | **~10–12** @50–97 h | 0.06 ✗(÷170) | 1.4 ✗(÷8) | 0–2 ✗ | 0–1 ✗(÷30) |
| B | **5**, all in final 1800 °C phase | 0.08 ✗ | 1.5 (÷3) | 0–5 (judgment band, low conf; model says 0) | 300 ✗(×60) |
| C1 | **3** @49/115/200 h | 0.004 ✗ | 0.7 (÷4) | 0 ✗ | 0.04 ✗ |
| C2 | **0** /1,631 | 0.002 ✓ | 0.1 ✓ | 0 ✓ | 0 ✓ |
| Onset/phase placement | (final phase for B) | "1800 °C phases" ✓ | peak-T concentrated ✓ | **"mostly final 300 h" ✓✓** | "~95% final phase" ✓✓, "2nd 1800 °C segment" for A2 ✓ |
| T-ranking (1800≫1600) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Burnup ordering C1>C2 | ✓ (3 vs 0) | ✓ (×2) | ✓ (×7) | — | ✓ (×13) |

## Kr-85 fractional release

| Case | **Measured** | Opus A | Opus C | Fable 5 |
|---|---|---|---|---|
| A1 | **1.8×10⁻⁶** | 1.2×10⁻⁷ | <6×10⁻⁵ ✓ | ~1×10⁻⁵ (×5) |
| A2 | **6.5×10⁻⁴** | 3.5×10⁻⁶ ✗ | 0.6–1×10⁻⁴ (÷7) | ~3×10⁻⁵ ✗ |
| C1 | **9.9×10⁻⁴** | 2.2×10⁻⁶ ✗ | <6×10⁻⁴ ~ | ~4×10⁻⁵ ✗ |
| C2 | **5.4×10⁻⁷** | 9.9×10⁻⁷ ✓ | <6×10⁻⁴ ✓ | ~1×10⁻⁵ (×18) |

## Cs-137 fractional release — the "inherited bias" finding

| Case | **Measured** | Opus A | Opus C | Fable 5 | vs measurement |
|---|---|---|---|---|---|
| A1 (1600 °C) | **1.1×10⁻⁴** | 0.11 | 0.11 | 0.01 | **×100–1000 high** |
| A2 (1800 °C) | **5.9×10⁻²** | 0.077 | 0.07 | 0.11 | **×1.2–1.9 — good** |
| B (→1800 °C) | **~4×10⁻²** | 0.16 | 0.13 | 0.5 | ×3–12 high |
| C1 (1600 °C) | **3.9×10⁻³** | 0.087 | 0.083 | 2×10⁻³ | Opus ×20 high; **Fable ÷2 ✓** |
| C2 (1600 °C) | **2.6×10⁻⁴** | 0.087 | 0.083 | 1.3×10⁻³ | Opus ×300; Fable ×5 |

TECDOC-1674 itself records that the participant codes "overpredict Cs on low-temperature tests
by an order of magnitude" and are "reasonable on high-release 1800 °C tests" — **the agents,
given the community's correlations, reproduced the community's systematic error almost
exactly.** (Sr was excluded from scoring a priori: all professional codes overpredict it >100×.)

## The honest synthesis

1. **Zero-failure cases called correctly by every run** (A1, C2 — 8/8 verdicts ✓).
2. **Absolute failure counts under-predicted across the board at 1800 °C** (÷8…÷450 on A2):
   the annex supplies pressure-vessel mechanics only, and at these stresses (14–38% of Weibull
   strength) pressure alone bursts nothing — *which is the historically correct pressure-vessel
   answer*; the real 1800 °C killer (SiC thermal decomposition/corrosion) was not in the
   provided property set. Responses to the gap differed by model (audit-corrected wording):
   **Fable coded an ad-hoc decomposition mechanism** (anchored to the ~2200 °C destruction
   point — domain knowledge beyond the annex, disclosed) and overshot Case B ×60 while nailing
   the phase placement; **Opus C added a self-described low-confidence 0–5 judgment band** (its
   model says ~0) whose upper edge coincides with the measured 5 but which missed A2 and C1;
   the other three runs reported the pressure-vessel answer as-is. Judgment under incomplete
   physics — visible in all three flavors (code it, band it, or decline).
   **Circularity disclosure:** the original benchmark codes never predicted these failure
   counts — the counts were imposed as boundary conditions in their postcalculations. The
   agents attempted a strictly harder task than the reference codes performed.
3. **The sister-sphere cliff (A2 vs A1) was predicted in direction by all runs but not in
   magnitude by any.** The measured A2(10–12 @100 h) > B(5 @400 h) inversion is *consistent
   with* a fuel-batch difference (K3 vs K6 production) that identical-particle physics cannot
   express — a hypothesis, not an established cause. Either way: real engineering data carries
   information the spec sheet doesn't.
4. **Cs-137: accuracy tends to track temperature the way the professional codes' did** —
   ×1.2–1.9 on the pure 1800 °C sphere (A2); ×3–12 on the staged case B (the codes also
   overpredicted B specifically); orders high at 1600 °C for four of five runs — with one
   counter-example (Sonnet UNDER-predicted A1: 2.4×10⁻⁵ vs 1.1×10⁻⁴). A tendency, not a law.
   Opus B (omitted from the table above, now noted): A1 Cs ≈0.147 (×1300 high), same pattern
   as the other Opus runs. Inherited correlations ⇒ inherited biases, mostly.
5. Costs: Opus $1.7–2.1 / 11–14 turns / ~10 min per run; Fable ~96k tokens; all offline.

## Fable 5 — VPS rerun with full transcript (added Jul 3; 14 turns, $5.44, 14 min, 0 web calls)

Launched to close the evidence gap on the original local-subagent Fable run (`run_triso_fable`,
no transcript). Same frozen pack, first-class evidence (`../transcripts/triso_fableV.run.log`).

| Case | **Measured** | Fable 5 (VPS) |
|---|---|---|
| A1 failures | **0** | 0 (E[N]=0.0006) ✓ |
| A2 failures | **~10–12** | central 0, upside 0–2 ✗ |
| B failures | **5**, all final phase | central 0, **upside 0–5, "most likely phase 4"** — band edge + phase ✓✓, model says 0 |
| C1 failures | **3** | 0, upside 0–1 ✗ |
| C2 failures | **0** | 0 ✓ |
| Kr-85 A2 | **6.5×10⁻⁴** | <6×10⁻⁵ ✗ |
| Cs-137 A1 (1600 °C) | **1.1×10⁻⁴** | 3×10⁻² — ×270 high (the inherited bias again) |
| Cs-137 A2 (1800 °C) | **5.9×10⁻²** | 4×10⁻⁴ — **÷150 UNDER: a second counter-example** to "accurate at 1800 °C" |
| Cs-137 B | **~4×10⁻²** | 1.2×10⁻¹ — ×3 |
| Cs-137 C1/C2 | 3.9×10⁻³ / 2.6×10⁻⁴ | 1×10⁻² (×2.6) / 2×10⁻³ (×7.7) |

**The temperament finding this run adds:** the original (local) Fable run *coded* an ad-hoc SiC
degradation mechanism and overshot B ×60; this VPS Fable run — same model, same pack — chose the
Opus-C-style path instead: pure pressure-vessel physics plus explicit low-confidence judgment
bands (and, like Opus C, its B band's upper edge landed on the measured 5 with the right phase).
"Code it / band it / decline" is a **sampled behavior, not a fixed model property** — N=1
temperament claims per model are not supported. Both Fable runs also ranked B as most-damaged
(measured: A2 had more failures), inverting the sister-sphere cliff — consistent with the
batch-difference hypothesis being invisible to physics.

## Sonnet ladder row (52 turns, $4.74, 22 min — ~2.5× Opus cost)
Failures: A1 0.002 ✓ · A2 0.024 ✗(÷450) · B 0.034 ✗(÷150) · C1 0.020 ✗ · C2 0.002 ✓.
Meticulous inventory bookkeeping (tracked fuel batches, decay-corrected Kr-85 atoms), correct
zero-failure calls and phase placements — but purely the given pressure-vessel physics, no
invented mechanism. The ladder pattern repeats: the weaker model executes the supplied physics;
the frontier models are the ones that notice what's missing. (Probes: 0/4 off-median
forced-choice, both models refuse recall — `../probes/triso_probes_results.txt`; audit:
`AUDIT.md`, corrections applied above.)
