# Run: zero-power correlation derivation, Opus — 14 turns, $1.37, 371 s
Task: derive, blind, a predictive formula for zero-power draft flow ṁ(ΔT, V) from geometry alone.
The lab's own fitted correlation (never shown): ṁ = (5.53·ΔT + 3.75·V²)^(1/1.8) kg/min.
Agent derived: ṁ = (20.5·ΔT + 6.25·V²)^(1/2) kg/min.
Verdict vs the lab fit:
- FORM: rediscovered exactly — stack term linear in ΔT, wind term quadratic in V, combined under
  a root set by the loop loss law. (Agent argued ṁ² losses → n=2; lab fitted n=1.8 ≈ Blasius.)
- WIND: at ΔT=0, V=10 m/s: agent 25.0 vs lab 26.9 kg/min (−7%).
- STACK: ~+45% high (ΔT=15: 17.2 vs 11.6 kg/min) — agent assumed the full indoor-outdoor ΔT
  drives the stack and itself flagged "intake air may cool → real drive lower" as the caveat.
- Self-stated uncertainty ±15–25% (+ C_w ±30%): the stack miss slightly exceeds its own band.
