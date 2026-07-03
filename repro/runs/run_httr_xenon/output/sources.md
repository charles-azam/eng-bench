# Sources consulted — Xe-135/I-135 addendum

Rule (unchanged): DESIGN DATA, SOFTWARE, and NUCLEAR DATA only. **No HTTR LOFC /
loss-of-forced-cooling test results** (power traces, measured recriticality times/temperatures,
post-test analyses). The only quantitative review feedback used is the qualitative "×7 timing
under-prediction"; the measured recriticality value itself was NOT looked up.

This addendum reused the neutronics results (k_inf(T), β_eff) already computed in the original
study — see `prior_output/sources.md` for the full OpenMC / ENDF/B-VIII.0 / HTTR design-data source
list. No new HTTR-specific sources were opened for the xenon work.

## Nuclear data for Xe-135 / I-135 (standard, from physics knowledge — no test data)
- I-135 half-life 6.57 h; Xe-135 half-life 9.14 h (standard decay data).
- I-135 cumulative fission yield ≈ 0.0629; Xe-135 direct (independent) yield ≈ 0.00237 (U-235
  thermal fission, standard yield data).
- Xe-135 thermal absorption cross section 2200 m/s value ≈ 2.65×10⁶ b; effective spectrum/temperature-
  averaged value taken as ~2.0×10⁶ b (band 1.5–2.7×10⁶) reflecting the elevated-temperature Maxwellian
  and the 0.084 eV resonance (non-1/v). Standard reactor-physics knowledge.
- ν (U-235 thermal) ≈ 2.43.
- These are textbook fission-product-poisoning data; no HTTR-specific or test-specific source used.

## Design data reused (not test data)
- HTTR average thermal flux at 9 MW (30 % power) estimated at ~3×10¹³ n/cm²/s from the design power
  density (2.5 MW/m³, JAEA outline) — a design-level estimate, carried with a wide sensitivity band.
  No measured flux map consulted.

## Incidents
- None new. As in the original study, LOFC test-result papers were not opened.
