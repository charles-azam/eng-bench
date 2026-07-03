# META — run_fableC_vps

- Model: Claude Fable 5
- Machine: VPS (Hetzner 8-core/30GB) — first-class evidence, full transcript
- Network: web tools allowed on allowlist but unused — 0 WebSearch/WebFetch (grep the transcript)
- Harness turns: 66 · API cost: $14.06 · Wall clock: 30.5 min
- Transcript: ../../transcripts/fableC_vps.run.log
- Note: rejected the supplied 82 kWe→56.07 kWt duty mapping for its own loss physics
  (~73 kW to air) — the same judgment call as Opus run repD. Flow −1.7%, plate +8.3%,
  ΔT +52% (self-consistent with that choice).
