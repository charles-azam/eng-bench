# Can an AI do real engineering? Three nuclear problems, graded against measured data

This repo is the complete, auditable record of three experiments in AI-driven engineering
analysis. In each, autonomous Claude agents (running headless via Claude Code on a small VPS)
were given **only what a design engineer would receive** — geometry, materials, operating
conditions — and asked to produce a **calculation note** predicting quantities that a real
facility actually measured. The measured answers were held out for grading and never on the
machine.

| Campaign | The question | Ground truth | Where |
|---|---|---|---|
| **NSTF** — passive reactor-cavity cooling | Predict airflow, temperatures, radiation split, accident transient, weather sensitivity of Argonne's ½-scale natural-circulation rig | Argonne ANL-ART-47 measured campaign (33 months, NQA-1) | this directory: `inputs/`, `runs/`, `transcripts/`, `scoring/`, `AUDIT.md` |
| **TRISO** — fuel-particle failure statistics | Predict particle failures & fission-product release in 1600–1800 °C accident furnace tests (Weibull statistics of ~15,000-particle fuel elements) | IAEA TECDOC-1674 / TECDOC-2090 measured heating tests | `triso/` |
| **HTTR** — reactor loss-of-forced-cooling | Predict Japan's HTTR LOFC test — self-shutdown, spontaneous recriticality, stabilized power — *computing its own reactivity coefficients* (OpenMC Monte Carlo, 3.4 GB ENDF, overnight) | JAEA 2010 LOFC test (9 MW, VCS on) | `httr/` |

Companion articles: see the repository's website links (capstone + three deep-dives + an
interactive calculator).

## Integrity model (read this before objecting)

1. **The measured data is public** (Argonne / IAEA / JAEA reports). Secrecy is impossible and
   not claimed. The claim: the agents **derived** their numbers rather than retrieved them.
2. **Recall probes** (`probes/`): asked directly, the models decline to state the measured
   values from memory; forced-choice probes score at chance (NSTF: 6/16 n.s. with a disclosed
   design flaw; TRISO: 0/4 with the truth placed off-median). The models *recognize* the
   facilities; they cannot *recall* their data.
3. **Transcripts** (`transcripts/`): the complete stream-json log of every surviving run —
   every command, every tool call. `grep -c '"name":"WebSearch"' transcripts/*.log` → 0 for
   every NSTF and TRISO run (the cht run issued a single `curl -sI hub.docker.com`
   connectivity check before pulling the OpenFOAM Docker image — it's in the log).
   `httr.run.log` has web hits **by design**: that campaign allowed public *design* data and
   forbade test results; the adversarial audit swept every tool result and found zero measured
   LOFC numbers entering the context (`httr/AUDIT.md`, Finding 1).
4. **Independent curation + adversarial audits.** The NSTF inputs were re-derived by a separate
   curator agent from the raw report under a written no-outcomes protocol (`packs/`). Every
   campaign was then audited by a fresh-context adversarial AI agent with the charter "prove
   this wrong." All three audits are published **unedited** — `AUDIT.md`, `triso/AUDIT.md`,
   `httr/AUDIT.md` — and all corrections were applied. The HTTR audit retracted a headline
   claim; the retraction is in the article and scorecard.
5. **Error structure.** The misses are systematic, self-flagged, and physically traceable
   (a supplied duty input, a missing degradation mechanism, an absent xenon term) — the
   signature of derivation, not retrieval. Memorized answers don't produce self-consistent,
   explainable mistakes.

## What's here (NSTF, this directory)

| Path | What it is |
|---|---|
| `TASK.md` / `CLAUDE.md` / `GOAL.txt` / `run.sh` | The engineering ask, the 4-line standing brief (incl. the no-lookup rule), the frozen completion condition, and the launcher — exactly as the agents received them |
| `inputs/` | Everything the agent was given: geometry, materials, sensor locations, boundary conditions. **Facts only — no measured results** |
| `runs/` | Each run's full output: calculation note, Python models, results, figures, plus `META.md` (model, machine, cost, wall-clock, evidence grade) |
| `scoring/` | Predicted-vs-measured tables; measured values cited to report page/table |
| `probes/` | Contamination probes: prompts + responses, forced-choice analysis |
| `transcripts/` | Full transcripts of every surviving run (21 logs across the three campaigns) |
| `packs/` | The de-identified pack, the independent-curator protocol and pack, blind-scenario file |
| `AUDIT.md` | The NSTF adversarial audit, unedited |
| `triso/`, `httr/` | The other two campaigns: pack, held-out refs, scorecard, audit each |

## Reproduce it

```bash
# on a Linux box with Claude Code installed and authenticated
git clone https://github.com/charles-azam/eng-bench && cd eng-bench
bash run.sh          # NSTF baseline; ~10–30 min, ~$2–6 of API
# or: cd triso/pack && bash run.sh        (TRISO, fully offline)
# then compare output/calculation_note.md to scoring/measured_values.md (or triso/refs/)
```

`run.sh` uses Claude Code's `/goal` command (built in since v2.x) to loop until the deliverable
exists; on a setup without it, pass the contents of `GOAL.txt` as the prompt directly. The
prompts are fully open — the agent picks its own methods. Your run will differ in its choices;
that's the point. Score it against the held-out values and see where it lands.

## Headline results

**NSTF (ensemble of 7 fully-archived Opus baseline runs):**

| Quantity | Measured (Argonne, Run011) | Agent predictions (range) | Verdict |
|---|---|---|---|
| System mass flow | 0.574 kg/s | 0.55–0.65 kg/s | within ~4% in 6 of 7 (median +1%); +13% in the run that overrode the given duty |
| Heated-plate temperature | 390.7 °C | 359–420 °C | −8…+7.5% (median −4%) |
| Riser wall (front, mid-plane) | 163.1 °C | 110–195 °C | −32…+20% (widest spread — hotspot-modeling-sensitive) |
| Riser air ΔT | 84.1 °C | 96–110 °C | **+14…+31% high, every run** (see scorecard for why) |
| Radiation dominant? | yes (~0.80) | yes (0.87–0.93) | right regime, **fraction over-predicted every run** |
| Accident: bounded turn-over below limit | yes, peak 408.7 °C | yes, peak 359–391 °C (Opus); 321–497 °C across all models | correct call, every run of every model |
| Blind argon ingress | stall ~90 s, gas peak 126 °C, self-recovery ~30 min | stall s–tens s, threshold 131 °C, recovery 5–15 min | mechanism + threshold ✓; recovery time ~2–6× fast |
| Blind blockage (50% ducts): plate rise | +13 °C | +104 °C | **wrong ×8** — cause pre-flagged in the agent's own caveat |

**TRISO:** every zero-failure case called correctly (10/10 verdicts across 5 runs); the
1800 °C sister sphere under-predicted ÷8…÷450 (the annex contains pressure-vessel physics
only — the real killer, SiC thermal degradation, wasn't in it); the community's own Cs-137
prediction biases reproduced from the community's own correlations. → `triso/SCORECARD.md`

**HTTR:** feedback coefficients computed from scratch (α ≈ −7 pcm/K, β_eff = 0.0073 ± 0.0009,
audit-reproduced from the raw Monte Carlo outputs); self-shutdown and bounded outcome correct;
recriticality clock missed ×7 for causes now fully named (half pre-registered by the agent,
half — xenon — found by the audit), and a $3.87 diagnostic rerun adding the xenon term moved
the clock from 1.0 h to 12.5 h (band 1.8–21 h; measured 7–8 h inside it) — structured errors
are debuggable. → `httr/SCORECARD.md`, `httr/AUDIT.md`, `runs/run_httr_xenon/`

Full per-run detail, disclosures, and the misses: `scoring/scorecard.md`, `triso/SCORECARD.md`,
`httr/SCORECARD.md`. The audits: `AUDIT.md`, `triso/AUDIT.md`, `httr/AUDIT.md`.

## Costs

NSTF: ~$61 (12 runs incl. 2 CFD-bearing + curator + probes + audit) + $26.50 for the two Fable 5
VPS runs. TRISO: $15.8 across the five metered runs (of 6 total — one ran as an unmetered local
subagent). HTTR: $16.08 (+ ~3.3 h background Monte Carlo on the
box) + $3.87 for the xenon addendum. Total ≈ $125. VPS: €30/month Hetzner, ~€2 of actual usage.
Everything ran on an 8-core / 30 GB box.

*Measured values © the cited public reports (ANL, IAEA, JAEA, INL). Everything else: MIT
(see LICENSE).*
