# META — run_httr_xenon (diagnostic addendum, NOT a blind prediction)

- Model: Claude Opus
- Machine: VPS · Network: fully offline (no web tools on allowlist) — 0 web calls
- Harness turns: 37 · API cost: $3.87 · Wall clock: 15.4 min
- Transcript: ../../transcripts/httr_xenon.run.log
- Charter: the HTTR adversarial audit (../../httr/AUDIT.md, Finding 3) identified xenon
  poisoning as missing physics. This run extends the original agent's own model with
  I-135/Xe-135 dynamics. It was told the original prediction was "×7 too short" (direction and
  size of the miss) but NOT the measured value. Result: nominal 1.0 h → 12.5 h, band 1.8–21 h;
  it is a mechanism-sufficiency test, not a fresh prediction — see TASK.md and the addendum's
  own framing.
