# Curation statement — TRISO accident-heating prediction pack

Curated 2026-07-03 from IAEA TECDOC-1674 (`triso/sources/TECDOC-1674_full.txt`) and
TECDOC-2090 (`triso/sources/TECDOC-2090_full.txt`), using the line-map in `triso/DILIGENCE.md`.

## Purpose and split

The pack is a **blind prediction benchmark**. The predicting agent receives only
`pack/TASK.md`, `pack/CLAUDE.md`, and `pack/inputs/*.md` — conditions plus a self-contained
material-property annex. All measured outcomes are held out in `refs/measured_data.md`. The agent
must predict, from physics alone, the heating-induced particle-failure counts, their timing, and
the final Kr-85 / Cs-137 fractional releases, then rank the cases.

## Cases included (5, + 1 optional)

- **A1 HFR-K3/1** and **A2 HFR-K3/3** — sister GLE-3 spheres, same particle batch (EUO 2308),
  chosen to isolate the 1600 °C→1800 °C temperature cliff at similar-ish burnup.
- **B HFR-K6/3** — staged 1600/1700/1800 °C sphere; tests whether the agent predicts failures
  concentrated in the hottest (final 1800 °C) phase.
- **C1 HFR-P4/3-7** vs **C2 HFR-P4/1-12** — compact pair at identical 1600 °C/304 h heating,
  isolating burnup effect (13.9 % vs 11.1 % FIMA).
- **NPR-1 A5** — recorded in refs as an *optional* very-high-burnup (79 % FIMA) stress case;
  not placed in `inputs/02_cases.md` to keep the core set homogeneous (LEU, similar geometry).

## Cases deliberately EXCLUDED

- **HFR-EU1bis** — "planned"/spec fuel where the benchmark specification differs from as-built
  reality; the DILIGENCE map flags spec≠reality. Excluded to avoid an ill-posed target.
- **HTR-PM** — planned-only, no conducted heating test / no measured data.
- **HRB-22 (cases 7a/7b)** — conducted, but omitted to keep the core set to the sphere pair,
  staged sphere, and compact pair; its rows remain visible in refs Table 8.2/19 context if needed.
- **Normal-operation postcalc cases 9–13** (SiC-stress benchmark) — excluded from prediction
  except that NPR-1 A5's single measured number is carried in refs as an optional case; the
  others are figure-only or ≈0 with no text-scoreable end state.
- **Strontium (Sr-90)** — excluded from scoring: ALL benchmark codes overpredict Sr by >100×
  (1674 line 24494). Sr values are retained in refs for context only.
- **Silver (Ag-110m)** — not a scored target (release is diffusion-erratic and often figure-only);
  values retained in refs for context.
- **Participant-code prediction tables/figures** — held out and flagged as *code output, not
  measurement*; not used as ground truth.

## Judgment calls

1. **Leakage stripping.** The postcalculation prose embeds the answers: it states failure counts,
   onset times, and the release levels used as boundary conditions. I extracted only conditions
   into `inputs/`. In particular, from `[2090] Table 21` I took ONLY the condition columns
   (burnup, fast fluence, irradiation temperature, heating temperature, duration) and dropped the
   four fractional-release columns (Kr-85, Sr-90, Cs-134, Cs-137). Heating *schedules* (set-point
   temperatures, ramp and hold times) from Table 10.11 are conditions, not outcomes, and were kept.

2. **Burnup value for A2 (HFR-K3/3).** Two figures appear: 10.2 % FIMA (Table 8.2 / end-of-life)
   and 10.6 % FIMA (Table 10.11 heating-phase inventory). Both are given in `inputs/02_cases.md`
   as conditions; neither reveals an outcome. Similarly the fluence is quoted as 6.0×10²⁵
   (Table 8.2, E>0.1) ≈ 5.9×10²⁵ (Table 10.11).

3. **K3/3 failure-count discrepancy.** Table 8.2 records "~12" heating failures; the prose onset
   list enumerates 10. Both are recorded in `refs/measured_data.md`; scoring should accept the
   10–12 range.

4. **Particle counts.** Table 10.1 gives 16,350 for the HFR-K3 sphere and 1631 for the HFR-P4
   compact; the benchmark elsewhere rounds the sphere to 16,400 (the value that underpins the
   ≈6×10⁻⁵ one-particle Kr threshold). `inputs/` uses 16,400 for spheres, 14,580 for HFR-K6,
   1631 for compacts, and states the interchangeability.

5. **One-particle detection thresholds** (Kr-85 ≈ 6×10⁻⁵ per particle in a sphere; ≈ 6×10⁻⁴ in a
   compact) are given in `inputs/03` as physics/normalization context. These are *thresholds*,
   not measured outcomes, so including them is not a leak; they let the agent map a predicted
   failure count to an expected Kr release and are essential to a well-posed task.

6. **Cs-in-SiC diffusivity (Eq 10.9).** The source equation is OCR-garbled. I reconstructed the
   two-term Arrhenius form and quoted the document's own evaluated value at 1600 °C
   (≈1.011×10⁻¹⁶ m²/s), plus the note that a code variant used 1.477×10⁻¹⁶ m²/s. This is an input
   (a correlation), not an outcome.

7. **Material annex completeness.** Per the task, the annex is deliberately complete: elastic/
   thermal properties, PyC swelling/creep correlations and coefficients, layer strengths and
   Weibull moduli, kernel diffusion coefficients, Cs-in-SiC diffusivity, the equivalent-sphere
   release model, the Booth R/B model, the buffer stiffness convention, and inventory/threshold
   scaling. The one acknowledged upstream gap (matrix/graphite sorption coefficients, referenced
   to TECDOC-978) is not needed for particle-level failure and release and is not included.

## Scoring guidance (in refs)

- Failure counts: integer, accept the recorded ranges (e.g. A2 = 10–12).
- Kr-85 / Cs-137 fractional release: log-scale comparison; Cs inter-code band is ×2–×10, so a
  factor-of-a-few miss on Cs is within the state of the art. Sr excluded.
- Ranking and onset-phase logic are qualitatively scoreable (which case worst; failures in the
  hottest phase; burnup ordering of the compact pair).
