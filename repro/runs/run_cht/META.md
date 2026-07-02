# Run: CHT-style cross-check (temperatures SOLVED), Opus
- 2026-07-02 08:04 → 09:01 UTC (3447 s), 140 turns, $16.42
- Requirement: cross-check simulation must SOLVE wall temperatures (heat input prescribed,
  temperatures outputs) — the stronger check demanded by the adversarial audit.
- What it did: reduced model (Q_air=56 kW from its own parasitic estimate ±15%) + OpenFOAM
  buoyantSimpleFoam, k-ω SST, fvDOM radiation, uniform 5501 W/m² flux on plate, convective sink
  on riser plane; flux ramped in stages to converge. Temperatures were OUTPUTS.
- CFD outputs: plate 333–335 °C, riser mean 122–124 °C, radiative share 89% (reduced model: 372,
  131 mean/181 front, 91%). Self-disclosed ~20% energy-imbalance caveat (±20–30 °C).
- Vs measured: reduced plate 372 (−5%), riser front 181 (+11%); CFD plate 333 (−15%).
