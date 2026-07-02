# Run: independently-curated pack, Opus — 27 turns, $3.12, 625 s
- Inputs curated by a SEPARATE agent directly from the raw report text under a written
  no-measured-outcomes protocol (repro/packs/CURATOR_TASK.md); pack gate-checked leak-free
  before the builder saw it. Closes the audit's "curator held the answers" caveat.
- Score vs measured (Run011): flow 0.576 kg/s (+0.3% — best of campaign), ΔT 96.3 (+14%),
  vessel/plate 385.8 °C (−1.3% — best), riser wall 110.3 °C (−32% — worst; didn't model the
  front-face hotspot the location detail of which the curated pack under-specified),
  radiative fraction 0.87 (closest to measured 0.80). Accident: bounded, ~390 °C peak.
- Notable: pack legitimately contained the DESIGN-INTENT flow (0.456 kg/s, Table 5); the builder
  explicitly rejected it in favor of its own momentum balance (0.576) — which matched the
  measurement. Anti-anchoring on record. Also derived heater efficiency η≈0.64 independently
  (actual ~0.68) instead of using the duty pairing.
