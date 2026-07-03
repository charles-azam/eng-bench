# META — run_fableD_vps

- Model: Claude Fable 5
- Machine: VPS (Hetzner 8-core/30GB) — first-class evidence, full transcript
- Network: web tools allowed on allowlist but unused — 0 WebSearch/WebFetch
- Harness turns: 54 · API cost: $12.44 · Wall clock: 22.0 min
- Transcript: ../../transcripts/fableD_vps.run.log
- Note: rejected the supplied duty (parasitic ≈ 17% from its own physics vs 32% implied by the
  design mapping — explicitly flagged as its dominant uncertainty). Flow −1.8%, plate +3.9%,
  ΔT +42%. Also caught and rejected the corrupt C10 decay polynomial.
