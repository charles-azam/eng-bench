# HTTR LOFC Scorecard — the long-computation experiment

**Adversarially audited (`AUDIT.md`, published unedited) — all corrections applied below.**

**The run:** one Opus agent across a main + a finish session (**$16.08 total, 144 harness
turns**; the transcript's two result events: $13.07/86 + $3.01/58), given only the scenario and
public-*design*-data web access (LOFC test results forbidden; compliance **verified by the
audit**: every one of the 23 logged web calls is design/software/nuclear-data, a regex sweep of
every tool result found zero measured LOFC numbers entering the context, and the agent logged
and declined the LOFC papers whose titles surfaced in searches). It installed OpenMC 0.15.3,
downloaded 3.4 GB of ENDF/B-VIII.0, built a double-heterogeneous HTTR lattice (15,235 explicit
TRISO particles), and ran Monte Carlo sweeps for ~3.3 h of background compute via its own nohup
orchestrator finishing at 01:44 — k_inf at 4 temperatures (BP-on; 3 for BP-off) + β_eff by the
prompt method + a 400-sample thermal sensitivity study. All numbers reproduce from the raw CSVs
(audit Finding 8).

**Framing disclosure (audit Finding 10):** the task pack itself presupposed the qualitative
outcome — GOAL.txt asked for "a predicted recriticality time in hours" and "the stabilized
power level afterwards" — and the 2010 test is famous enough to be in training data (the agent's
own search queries show recalled design values). The honest claim is that the agent was *barred
from retrieving the results* (verified), not that it predicted from ignorance. The genuinely
blind outputs are the quantitative ones: the recriticality clock and the power level.

## Computed physics (from scratch — the point of the experiment)
- k_inf(T) monotonically falling; isothermal coefficient **α ≈ −7 pcm/K** (−6.85 BP-on /
  −7.04 BP-off; the ±0.1 agreement is the *BP-treatment spread only* — single-enrichment,
  BOL-fuel, no-leakage, isothermal caveats are in the agent's note), β_eff = 0.00728 ± 0.00093.
- Design-literature anchors (β_eff ≈ 0.0065, strongly negative α) are consistent at <1σ, but
  the ±13% error bar makes that a weak-consistency check, not a validation — and the agent's
  own search queries show it held those target values in memory.

## Predictions vs measured (2010 9-MW VCS-on test; provenance per refs/measured_data.md)

| Quantity | Agent (computed) | Measured / best open source | Verdict |
|---|---|---|---|
| Fission collapse | subcritical in ~1–3 min; its own nominal trace reaches its 0.01 kW floor at ~29 min | 9→~0 MW without scram (exact collapse time for the 2010 test not openly published; the *2024, 30 MW* test analog: <1% within ~13 min) | ✓ mechanism; speed roughly consistent with the (proxy) data |
| Recriticality occurs? | YES, spontaneous | YES — though GOAL.txt presupposed it (see framing disclosure) | ✓ but partially given away |
| **Recriticality time** | nominal 1.0 h; 400-sample band 0.24–1.1 h (band internally inconsistent: nominal Gcr sits outside the sampled range) | **~7–8 h** | **✗ ~7× early; band excluded the truth** |
| **Stabilized/peak power** | **287 kW** nominal (its low-parameter corner; band median 575 kW, P10–P90 312–826 kW) | measured **recriticality peak** <0.5 MW, ≈0.3 MW inferred from INL's statement that its 0.65 MW was "about 0.35 MW higher" than measured; the measured *stabilized* level is not openly published | low-end nominal coincided with the measured peak; the **band median missed ~2× — statistically indistinguishable from INL's post-hoc 0.65 MW**. NOT "beat the professional code" (audit Finding 2: quantity mismatch, nominal-vs-median, and the 287 kW tracks its unverified 0.3 MW VCS-capacity assumption ~1:1) |
| Bounded? | bounded; core peak 583 °C (≪1600 limit); vessel nominal 280–336 °C, **worst-case tail 605 °C** (above the 440 °C RPV service limit — in the extreme low-conductance corner) | bounded; fuel ≪ limits; RPV <440 °C (30 MW-test data + design limit) | ✓ verdict; the tail case disclosed here |

## The reading (audit-corrected)

The agent's *neutronics* — computed from scratch on a rented box — was right where physics is
self-contained: feedback sign and magnitude, self-shutdown, bounded outcome. The famous
qualitative result (spontaneous recriticality) was partly presupposed by the task itself.

**The clock miss (×7) is only half the story the agent told about itself.** It pre-registered —
verifiably, in-run, before results existed — that the core-to-sink conductance was its dominant
uncertainty ("thermal, not neutronic"). The audit confirmed that pre-registration AND found the
un-flagged other half: the published analyses attribute the reactivity recovery largely to
**Xe-135 decay**, and xenon appears *zero times* in the agent's model, note, and transcript.
Score the mechanism as **half right**: thermal relaxation captured; xenon poisoning dynamics —
a first-order driver of the 6–8 h timing — absent and unflagged. Integrity-positive detail from
the transcript: mid-run the agent wrote that its physical picture suggested "recriticality in a
FEW HOURS," yet it published its computed 1.0 h anyway — evidence the model, not memory,
produced the timing.

**What survives at full strength:** verified test-result blindness; a real from-scratch Monte
Carlo physics computation whose every number reproduces from the raw outputs; every qualitative
safety call correct; and a quantitative miss whose causes are nameable (one pre-registered, one
found by the audit). What does not survive: "beat the professional code."

## The xenon addendum (diagnostic re-run, Jul 3 — `../runs/run_httr_xenon/`)

To test whether the audit's diagnosis was *quantitatively* sufficient, a follow-up agent run
($3.87, 37 turns, offline) extended the original model with I-135/Xe-135 dynamics — standard
nuclear data, no tuning. Framing: it knew the original was "×7 too short" (direction and size
of the miss) but not the measured value; this is a **mechanism-sufficiency test, not a fresh
prediction**, and the addendum note says so itself.

| Quantity | Original (T-only) | With xenon | Measured |
|---|---|---|---|
| Recriticality time | 1.0 h (band 0.24–1.1) | **12.5 h nominal, P10–P90 1.8–21 h** | ~7–8 h (inside the band) |
| Stabilized power | 287 kW nominal | ~480 kW nominal, median 0.93 MW | peak ≈0.3 MW (see Finding 2 caveats) |
| Bounded? | yes | yes (peak graphite ≤869 °C worst-case, ≪1600) | yes |

Post-trip xenon build-up adds ~−1270 pcm beyond equilibrium (peaking ≈8 h), forcing ~180 K of
overcooling before criticality can return — the clock is set by the xenon transient, not
graphite inertia alone. The mechanism **over-explains** the ×7 gap (×10–13 nominal, governed by
the assumed operating flux — the honest residual uncertainty). Note the correction moves the
stabilized power *toward* the professional code's 0.65 MW and away from the lucky 287 kW —
the audit's retraction of that trophy, independently reinforced. One missing term, named by an
audit, added by a $4 run, spans the week's biggest miss: structured errors are debuggable.
