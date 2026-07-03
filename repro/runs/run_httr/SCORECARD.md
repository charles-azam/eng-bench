# HTTR LOFC Scorecard — the long-computation experiment

**The run:** one Opus agent, ~340 turns total across main+finish sessions (~$20+3), given only
the scenario and public-design-data web access (LOFC test results forbidden; compliance verified
— every logged query/URL is design/software/nuclear-data; the agent logged and declined LOFC
papers that surfaced). It installed OpenMC 0.15.3, downloaded 3.4 GB of ENDF/B-VIII.0, built a
double-heterogeneous HTTR lattice (~15,000 explicit TRISO particles), and ran Monte Carlo
sweeps for ~3.5 h of background compute (its own nohup orchestrator finishing at 01:44) —
k_inf at 4 temperatures × 2 burnable-poison variants + β_eff by the prompt method + a 400-sample
thermal sensitivity study. This is the week's "very long run with long computations."

## Computed physics (from scratch — the point of the experiment)
- k_inf(T) monotonically falling; isothermal coefficient **α ≈ −7 pcm/K** (−6.85 BP-on /
  −7.04 BP-off — the two variants bracket to ±0.1), β_eff = 0.00728 ± 0.00093.
- (HTTR design references quote β_eff ≈ 0.0065 and strongly negative α — the computed values
  are in the physically right range; the agent's BP bracketing argument held.)

## Predictions vs measured (measured: 2010 9-MW VCS-on test; refs/measured_data.md)

| Quantity | Agent (computed) | Measured | Professional post-hoc (INL RELAP5-3D) | Verdict |
|---|---|---|---|---|
| Fission collapse | subcritical in ~1–3 min, power ↓ >5 orders | <1% within ~13 min; fast collapse | (matches) | ✓ mechanism & speed right |
| Recriticality occurs? | YES, spontaneous | YES (~the famous result) | YES | ✓ |
| **Recriticality time** | nominal 1.0 h; band 0.24–1.1 h | **~7–8 h** | 7 h | **✗ ~7× early** |
| **Stabilized/peak power** | **287 kW** nominal (band 0.3–0.8 MW) | **~0.3 MW** peak, low simmer | 0.65 MW (**2× high**) | **✓✓ beat the professional code** |
| Bounded? | bounded; core peak 583 °C (≪1600 limit); vessel ~280–336 °C | bounded; fuel ≪ limits; RPV <440 °C | bounded | ✓ |

## The reading (the week's thesis, third confirmation)
The agent's *neutronics* — computed from scratch on a rented box — was right where physics is
self-contained: feedback sign and magnitude, self-shutdown, the existence and mechanism of
recriticality, the stabilized power (**closer than the national lab's post-hoc code**). The one
big miss, timing (×7), lives exactly where the agent said its uncertainty lived: "the effective
core-to-sink conductance is not directly published... thermal, not neutronic." The professionals
had the plant's thermal data; the agent had to guess a conductance — and pre-registered that
dependency. Structured, self-flagged error; same signature as NSTF's ΔT and TRISO's 1800 °C.
Note its sensitivity band (0.24–1.1 h) did NOT contain the truth — honest calibration failure
to report alongside the wins.
