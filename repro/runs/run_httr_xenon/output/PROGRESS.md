# PROGRESS — Xe-135/I-135 addendum to HTTR LOFC note

## Status: COMPLETE

## What was done
1. Reconstructed OpenMC k_inf(T) + β_eff from `prior_output/results.json` into `runs/main/keff.csv`
   (original neutronics runs directory was not retained) — reuses the exact validated core feedback.
2. `transient_xe.py`: extended the point-kinetics + 3-node thermal model with I-135/Xe-135 ODEs.
   Xenon reactivity = change from pre-trip equilibrium; burn-up rate scales with fission power.
   Governing knob ω_full = σ_aX·φ(9 MW). Verified xenon-off limit reproduces original ~1 h.
3. `analyze_xe.py`: nominal (with/without xenon, same marker) + 400-sample joint thermal+xenon
   sensitivity. Outputs `output/results_xe.json`, `output/lofc_xe.png`. Runtime ~5.6 min.
4. Wrote `output/addendum_note.md` (all four required items), `output/sources.md`.

## Key results
- Recriticality: 1.0 h → **12.5 h nominal**, band 1.8–21 h (P10–P90), ×10–13 shift.
- Stabilized power: 287 → ~480 kW nominal (median ~0.93 MW).
- Equilibrium xenon −1988 pcm; post-trip peak −1267 pcm at 7.8 h (nominal).
- Peak core temp ≤ 869 °C across all samples — bounded, no runaway.
- Verdict: xenon diagnosis is quantitatively **sufficient (indeed over-explains)** the ×7 gap;
  a ~7 h measured value sits inside the band. Central overshoot is driven by assumed 9-MW flux.

## Compliance
- No HTTR LOFC test result consulted. Only the qualitative "×7" review feedback used.
