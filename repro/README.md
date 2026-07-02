# Can an AI predict a nuclear-safety experiment from its blueprints?

This repo is the complete, auditable record of an experiment: an AI agent (Claude, running
autonomously via Claude Code on a small VPS) was given **only the geometry, materials, and
boundary conditions** of Argonne National Laboratory's NSTF — a ½-scale passive reactor-cavity
cooling experiment — and asked, like any engineer, to produce a **calculation note** predicting
what the lab measured. The measured data was never on the machine.

Companion article: [link]

## What's here

| Path | What it is |
|---|---|
| `TASK.md` | The engineering ask, exactly as the agent received it |
| `CLAUDE.md` | The agent's 4-line standing brief (incl. the no-lookup rule) |
| `GOAL.txt` | The frozen completion condition used to launch every run |
| `run.sh` | The launcher (headless Claude Code, `/goal`, tool whitelist) |
| `inputs/` | Everything the agent was given: facility geometry, materials, sensor locations, boundary conditions. **Facts only — no measured results.** |
| `runs/` | Each run's full output: the agent's calculation note, its Python models, results.json — plus per-run metadata (model, wall-clock, cost) |
| `scoring/` | Predicted-vs-measured tables. Measured values from the public Argonne reports (ANL-ART-47 and companions), with page/table citations |
| `probes/` | The training-data contamination probes (prompts + responses): can models *recall* the measured values? (No.) |
| `transcripts/` | The complete stream-json transcript of every surviving run — every command, every tool call. Grep them: `grep -c '"name":"WebSearch"' transcripts/*.log` → 0 everywhere |
| `packs/` | The de-identified input pack and blind-scenario file actually used |
| `AUDIT.md` | An independent adversarial AI audit of every claim in this repo, published unedited (verdict: supported with corrections — all applied) |

## Reproduce it

```bash
# on a Linux box with Claude Code installed and authenticated
git clone <this repo> && cd <repo>
bash run.sh          # launches the autonomous run; ~20–60 min
# then compare output/calculation_note.md to scoring/measured_values.md
```

The prompt is fully open — the agent chooses its own methods. Your run will differ in details;
that's the point. Score it against the measured values and see where it lands.

## Integrity model (read this before objecting)

1. **The measured data is public** (Argonne technical reports). Secrecy is impossible and not
   claimed. What we claim: the agent **derived** its numbers rather than retrieved them.
2. **Recall probes** (`probes/`): Opus, Sonnet, and Haiku, asked directly, all decline to state
   the measured values from memory ("any numbers I produced would be fabricated"). The models
   recognize the facility; they cannot recall its data.
3. **No lookups**: the agent's full transcripts log every command and web access; there is no
   fetch of any facility report. A de-identified rerun (facility name scrubbed) is included.
4. **Error structure**: the predictions miss in exactly the directions the agent's own stated
   assumptions push (e.g. its heat-loss assumption ⇒ its ΔT overshoot). Memorized answers
   don't produce self-consistent errors.

## Headline result (ensemble of 6 fully-archived Opus baseline runs)

| Quantity | Measured (Argonne, Run011) | Agent predictions (range) | Verdict |
|---|---|---|---|
| System mass flow | 0.574 kg/s | 0.55–0.65 kg/s | ±4% in 5 of 6; +13% in the run that overrode the given duty |
| Heated-plate temperature | 390.7 °C | 359–420 °C | −8…+7.5% |
| Riser wall (front, mid-plane) | 163.1 °C | 135–195 °C | −17…+20% |
| Riser air ΔT | 84.1 °C | 96–110 °C | **+14…+31% high, every run** (see scorecard for why) |
| Radiation dominant? | yes (~0.80) | yes (0.90–0.96) | right regime, **fraction over-predicted every run** |
| Accident: bounded turn-over below limit | yes, peak 408.7 °C | yes, peak 359–391 °C | correct call, every run |
| Weather: colder ⇒ more flow | yes (~25% swing) | yes (9–21% swing) | sign right, magnitude low |
| Blind argon ingress: stall + self-recovery | stall in ~90 s, gas peak 126 °C, recovery ~30 min | stall in s–tens of s, threshold 131 °C, recovery 5–15 min | mechanism + numbers ~right |
| Blind blockage (50% ducts): plate rise | +13 °C | +104 °C | **wrong ×8** — cause pre-flagged in the agent's own caveat |

Full per-run detail, disclosures, and the misses: `scoring/scorecard.md`. Independent adversarial
audit of all of it: `AUDIT.md`.

*Measured values © the cited public Argonne reports. Everything else: MIT license.*
