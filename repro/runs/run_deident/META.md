# Run: de-identified pack, Opus
- Date: 2026-07-01 23:52 → 00:05 UTC (798 s wall-clock), 32 turns, $3.03 API cost
- Pack: identical physics inputs, facility name/report IDs scrubbed
- Machine: Hetzner 8-core/30GB VPS
- Method the agent chose: own air-property code (Sutherland laws), Haaland friction,
  Dittus-Boelter internal convection, two-gray-surface radiation network, 240-node
  circumferential riser-wall conduction model, first-principles parasitic-loss estimate (~11 kW)
- Score vs measured (Run011): flow +0.7%, ΔT +14%, riser wall +13%, plate −8%,
  radiative fraction 0.90 (measured: radiation-dominant ~0.8), accident bounded ✓ (peak −12%),
  weather sign ✓ (+15% flow cold-swing; measured ~25% incl. wind coupling)
