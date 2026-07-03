# PROGRESS — HTTR LOFC prediction

Started: 2026-07-02 22:08 UTC

## Plan
1. [DONE] Install OpenMC (0.15.3, conda-forge, MPI) in env `omc`.
2. [DONE] Download ENDF/B-VIII.0 HDF5 nuclear data -> /root/xs/. T=294/600/900/1200/2500 K + graphite S(a,b).
3. [DONE] Collect HTTR public DESIGN data (geometry, enrichment zoning, materials, thermal props). Logged in sources.md.
4. [DONE] Build OpenMC model: TRISO pin-in-block WS cell, explicit ~15k TRISO, smeared BP, reflective BC.
5. [DONE] Compute k_inf at isothermal T = 294/600/900/1200 K, BP on (main) and BP off (nobp). sigma_k ~6-8e-4.
6. [DONE] Derive isothermal temperature coefficient alpha(T) [pcm/K] with statistical uncertainties, both BP variants.
7. [DONE] Build coupled transient model: point kinetics + ANS decay heat + 3-node graphite/vessel thermal + VCS.
8. [DONE] Run LOFC transient: circulator trip at 9 MWt, no scram, rods frozen, VCS on + 400-sample sensitivity.
9. [DONE] Extract 4 predictions + confidence levels. calculation_note.md filled from real data.

## COMPLETE — 2026-07-03
All four goal criteria met. analyze.py (extended to emit BOTH BP variants) run on the real completed
OpenMC sweep -> output/results.json + output/lofc_transient.png. calculation_note.md has every NUMBERS
placeholder replaced with computed values. Headline computed results:
- k_inf(T): BP on 1.0829(294K)->1.0169(1200K); BP off 1.4963->1.4021. Monotonic decrease (Doppler-dominated).
- alpha(T): range-avg -6.85 pcm/K (BP on) / -7.04 pcm/K (BP off); variants bracket to +/-0.1 pcm/K. Strongly negative.
- beta_eff = 0.00728 +/- 0.00093 (prompt method @900K).
- Power collapse: fission power < decay heat in ~1-3 min, down to <0.01 kW (self-shutdown, rods frozen).
- Recriticality: nominal ~1.0 h; sensitivity median 0.44 h, band 0.24-1.1 h (thermal time constant, not neutronic).
- Stabilized power: nominal 287 kW (~3%); sensitivity ~0.3-0.8 MW (set by passive/VCS removal).
- Peak temps: core graphite 521-651 C (peak ~583 C, +33 C overshoot); vessel median 336 C, worst 605 C. BOUNDED, no runaway.
All from own computed neutronics + transient; NO LOFC test-result source consulted (see sources.md).

## Status log
- 22:08 OpenMC installed & verified. XS download launched.
- 22:11 ENDF/B-VIII.0 downloaded (3.4 GB) + extracted to /root/xs/endfb-viii.0-hdf5/. Confirmed T=294/600/900/1200/2500 K and c_Graphite / c_Graphite_30p / c_U_in_UO2 / c_O_in_UO2 S(a,b). Steps 1-2 DONE.
- 22:12 Design-data research agent running. Next: build TRISO pin-cell model.
- Modeling decision: compute k_inf(T) of the HTTR average fuel lattice (pin-in-block cell, explicit TRISO double heterogeneity, reflective BC) at 294/600/900/1200 K -> isothermal temperature coefficient alpha(T). Absolute criticality is set by frozen control rods in reality, so the transient needs the SHAPE alpha(T), which the reflected lattice captures robustly. Will note leakage/reflector caveat.
- 22:2x Design data agent returned full report (geometry/enrichment/BP/graphite/VCS/kinetics), sources.md populated, LOFC incident logged.
- Built model_httr.py (TRISO pin-in-block WS cell, smeared burnable poison, --prompt-only for beta_eff) and transient.py (point kinetics + ANS decay heat + 2-node graphite thermal + VCS). Pipeline validated on synthetic k(T): power collapses in ~6-18 min, core overshoots then cools, recriticality when core returns to Top, self-regulates at low power, temps bounded.
- Geometry cross-check: HM ~930 kg (matches HTTR ~900 kg U), active-core graphite 13.7 t, reflector ~90 t (~0.9 m responds over 24 h). Responsive graphite thermal mass ~50-70 t.
- [RUNNING] OpenMC main sweep (BP on, 12000 p x 170 batches) T=294/600/900/1200 K (~20-23 min/temp, sigma_k~6e-4). Orchestrator (run_followups.sh) will auto-run beta_eff pair (@900K full+prompt-only) and no-BP sensitivity after.
- Refined transient.py: 3-node thermal chain core->reflector->vessel->VCS (reports vessel temp). CORRECTED reactivity mapping: Drho_core(T)=1-k_inf(Top)/k_inf(T) and alpha=(1/k)dk/dT (was erroneously /k^2, ~1.5x too small). Fixed decay-heat t->0 divergence (clamp to ~6.3% at 1s). Validated Cp(T) fit (713@300K) and decay curve.
- Physical picture forming: (1) power collapses in ~1-3 min via negative T-feedback (He voiding worth ~0, so it's pure temperature/Doppler+moderator feedback as 9MW>>passive removal heats the core ~0.3-0.5 K/s); (2) recriticality in a FEW HOURS when core cools back to Top (governed by graphite heat capacity + conduction to the ~100C-cooler reflector/VCS; decay heat drops below passive removal within minutes); (3) stabilizes at the power passive cooling removes at Top ~ few hundred kW (~L0, VCS capacity); (4) temps BOUNDED (peak core overshoot small ~20-50C, vessel VCS-held, no runaway).
- analyze.py ready: computes k(T), alpha(T)+/-sigma (MC over k), beta_eff (prompt method), nominal transient + 400-sample randomized thermal sensitivity, plot + results.json. Awaiting real k(T).

