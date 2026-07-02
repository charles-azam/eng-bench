# Run 1 — Sunday 2026-06-28, 8 GB VPS (RECONSTRUCTED RECORD)

> The original box (<old-vps>, 4-core/7.6GB Hetzner, `ubuntu-8gb-hel1-1`) was deleted on
> 2026-07-01 before artifacts could be tarred off. This record was reconstructed from a full
> read of `output/calculation_note.md` and `output/results.json` performed over SSH on
> 2026-07-01 (see session transcript). Numbers below are verbatim from that read.

## Setup
- Pack: `experiment/` (TASK.md + CLAUDE.md + inputs/ 01–04, fully-open method, no refs on box)
- Launched with `/goal` (headless), model: opus-class (exact flag not recorded), ~Jun 28 21:26–21:43 UTC
  per file mtimes → **~17 minutes wall-clock** from init commit to final calculation_note.md.
- Output files: `calculation_note.md` (12,634 B), `rccs_model.py` (11,367 B), `rccs_cases.py`
  (7,775 B), `results.json` (19,707 B), `.venv` (CoolProp installed).
- NOTE: the input pack contained the strings "NSTF" and "ANL-ART-47" (identity leak, fixed in
  later de-identified pack). The agent was forbidden to look anything up and its provenance
  statement claims it did not.

## Method the agent chose (its own choice — fully open prompt)
Reduced-order physics model in Python + CoolProp: gray-surface radiation network across the
cavity + tall-vertical-cavity natural-convection correlation (Nu = 0.046 Ra^1/3) + Gnielinski
internal convection + hydrostatic-density-integral thermosiphon loop balance (buoyant head vs
Petukhov friction). No CFD (its choice on a 4-core/8GB box). Quasi-steady transient (plate
τ ≈ 1.0 h ≪ 85 h transient). Key own-assumptions: Q_air = 56 kW (82 kWe minus parasitic loss —
flagged by the agent itself as its most uncertain input), riser ε = 0.80 raised to effective
0.91 for inter-duct gaps, radiating envelope 8.85 m².

## Headline predictions (Case 1 baseline, Q_air = 56 kW, inlet 20 °C)
| Quantity | Predicted | (Held-out measured, Run011) | Error |
|---|---|---|---|
| Mass flow | 0.537 kg/s (32.2 kg/min) | 0.574 kg/s (34.46 kg/min) | **−6.4%** |
| Riser air ΔT | 103.5 °C | 84.1 °C | **+23%** |
| Riser wall T (mid-plane) | 140.5 °C | 163.1 °C | **−14%** |
| Heated plate T | 369.5 °C | 390.7 °C | **−5.4%** |
| Radiative fraction | 0.92 | ~0.80 (radiation dominant) | qualitatively right, ~12 pts high |

## Accident case (Case 2)
- Correctly identified the supplied C10-missing polynomial as unphysical (peaks 88 kW @ 71 h);
  chose the stated 26.16→56.07 kW shape peaking at 84.85 h instead. (Measured electric peak was
  actually ~90 kWe — the polynomial was closer than it assumed; nuance for the article.)
- Peak plate predicted 369.5 °C vs measured 408.7 °C (−10%). With the raw polynomial: ~450 °C.
- **Classified bounded/self-limiting ("levels off"), correct physical argument (T_p ∝ Q^1/4,
  ṁ ∝ Q^1/3, no positive feedback). Measured outcome: bounded turn-over at ~409 °C. CORRECT.**
- Safe-limit call: stays below 427 °C (800 °F) with +57 °C margin.

## Weather case (Case 3)
- Sign CORRECT: colder ambient → denser air → more flow, lower ΔT & metal temps.
- Magnitude: flow ±9% over −18→+24 °C (measured spread ~25% — under-predicted, partly because
  it did not model the indoor/outdoor stack split & wind coupling through the building).
- Independently flagged **wind as the larger ambient effect** (±35–45% at 11 m/s, Cp≈0.6
  assumption, low confidence self-assigned) — matches the lab's own headline finding.

## Self-assessed uncertainty (the judgment test)
Named Q_air (electric→air heat mapping / parasitic loss) as the dominant uncertainty — which is
exactly what drives its one big miss (ΔT +23%): it put 56 kW into the air; measured thermal was
~48.6 kW effective (56.12 kWt with ~68% efficiency off 82 kWe). Error direction matches the
stated assumption. Also ran sensitivity: ε_r 0.7/0.8/0.9 → plate 375/370/365 °C; stack height
7.7/13/19.6 m → ṁ 0.31/0.44/0.54 kg/s; Q 45–73 kW band.

## Sanity numbers it computed
Riser Re ≈ 15,185 (turbulent — measured-report range 6k–16k ✓); cavity Ra ≈ 5.6e8;
h_i ≈ 17.4 W/m²K; h_cav ≈ 2.2 W/m²K; radiation 51.5 kW vs convection 4.5 kW.

## Cheating assessment (informal, by orchestrator)
- Errors are structured, not random-around-truth: every miss traces to a stated assumption
  (Q_air high → ΔT high; wall-T low consistent with its h_i choice). A copier would have
  reproduced 84 °C / 0.80, not missed them in the direction its assumptions predict.
- Correlations are textbook (Gnielinski, Petukhov, Catton, Incropera refs), not the lab's
  (lab used RELAP5-3D & STAR-CCM+ with Wolfstein turbulence — nothing in common).
- Provenance statement present and specific.
