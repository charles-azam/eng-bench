# TASK — Diagnostic addendum to your HTTR LOFC calculation note

You previously produced `prior_output/calculation_note.md` (with `results.json`), predicting the
HTTR loss-of-forced-cooling transient with a point-kinetics + 3-node thermal model
(`transient.py`, `analyze.py`, feedback coefficients in `model_httr.py` results). Your predicted
recriticality time was ~1.0 h nominal (band 0.24–1.1 h).

An independent adversarial review of that note identified a candidate missing mechanism:
**Xe-135 / I-135 fission-product poisoning dynamics**. Your model's only reactivity channel is
temperature; it contains no xenon. After a trip from steady power, iodine-135 (t½ ≈ 6.6 h)
continues decaying into xenon-135 (t½ ≈ 9.1 h), a strong thermal absorber, before the xenon
itself decays away — which can delay the return to criticality by hours.

## What we want (diagnostic, not a fresh prediction — say so in the note)

1. Extend your transient model to include I-135/Xe-135 dynamics: pre-trip equilibrium inventory
   at 9 MW (30% power, from your own flux/power estimates and standard yields and cross
   sections you may derive or estimate from physics and your existing lattice results), the
   post-trip build-up/decay, and the xenon reactivity worth fed into the same point-kinetics +
   thermal model.
2. Re-run the nominal case and your 400-sample sensitivity study.
3. Report, in `output/addendum_note.md`: the revised recriticality time (nominal + band), the
   revised stabilized power, what the xenon term changed, and an honest assessment of whether
   the review's diagnosis was quantitatively sufficient to explain your original ×7 timing
   under-prediction (measured value deliberately not given to you here).
4. State your assumptions for the xenon worth (flux level, σ_a, yields) with confidence levels.

## Rules (same as before)

- Do NOT look up (web or otherwise) any HTTR LOFC test results — power traces, measured
  recriticality times, or post-test analyses. You may use standard nuclear data knowledge and
  general literature for yields/cross-sections.
- Put everything in `output/`.
