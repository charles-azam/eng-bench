# Run: CFD cross-check, Opus
- 2026-07-01 21:52 → 22:19 UTC (1644 s), 71 turns, $8.71
- Pack: baseline + one added requirement: "cross-check one key result with an independent
  higher-fidelity simulation set up and run on this machine"
- What it did: 1-D network (Gnielinski/Petukhov/Churchill-Chu/gray-enclosure + circumferential
  fin model for the front face) THEN installed OpenFOAM v2312 via Docker, generated a 2-D cavity
  case with viewFactor S2S radiation, ran buoyantSimpleFoam, reconciled within 2%.
- Score vs measured: flow +1%, ΔT +14%, riser front face 163 vs 163.1 °C, plate 390 vs 390.7 °C,
  rad fraction 0.93/0.96, accident bounded ✓ peak −4%.
