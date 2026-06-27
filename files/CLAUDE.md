# Project Brief — Autonomous Multiphysics Nuclear Benchmarking

This file is the durable memory of the project. Any fresh Claude Code or Cowork session should read it first. It captures **what we're building, why, the decisions already made, and the rules** — so nothing has to be re-derived.

---

## The thesis (what this project is really about)

Two claims, of equal weight:

1. **Physics result**: with modest compute (a single Linux box, no supercomputer), an AI agent can reproduce coupled multiphysics nuclear benchmarks that are normally the work of national labs — by exercising *modeling judgment* (the right hypotheses, the right reduced models, justified simplifications) rather than brute force. Compute starvation is a feature: it forces the agent to think like a pre-1990s physicist who knew what to throw away.

2. **Harness result** (the deeper contribution): the real artifact is the **harness that lets an agent run autonomously, for a long time, on a complex task without drifting, forgetting, or fooling itself.** The reactor benchmarks are the proving ground. The blog's spine is "what made the agent durable and honest," not just "what number it got."

Both matter equally. Every design choice serves one or both.

---

## The three benchmarks (equal priority)

All three run on modest compute and were chosen because each stresses the harness differently.

### A. MSFR neutronics↔thermal-hydraulics coupling (LPSC benchmark, F. Acosta report)
- **What**: 2-D molten-salt cavity coupling Monte Carlo neutronics + CFD + 8-group delayed-neutron precursor transport. The *real* field-multiphysics one.
- **Why**: tight two-way coupling, a pre-built progressive milestone structure (Phase 0 single-physics → Phase 1 seven coupling steps → Phase 2 transient), reference values in the report, and an expert verifier on hand (Francisco, the author).
- **Money shot**: precursor drift — delayed-neutron precursors swept downstream by the flow, emitting in low-importance zones. Unique to liquid fuel.
- **Note**: original used Serpent → we replace with OpenMC. The report documents a bug (8 precursor equations shared one source term) — implementing it correctly is a potential finding.

### B. TRISO fuel performance (IAEA CRP-6)
- **What**: predict coated-particle failure fraction from irradiation conditions. Multi-layer: conduction + fission-gas release + pressure rise + SiC shell mechanics + Weibull failure.
- **Why**: purest "small models, physical reasoning" showcase; each layer validates against a closed-form solution; IAEA gives conditions but **not** models (anti-cheat is natural).
- **Approach**: Python-from-scratch primary; BISON only as optional oracle (and only if access is obtained — see rules).

### C. Fuel-cycle / Am transmutation (ISAC/ARAMIS-A benchmark)
- **What**: fleet-scale material-flow simulation over ~150 years; reproduce control trajectory, then attempt MSR Am-transmutation trajectory.
- **Why**: purest "modeling choices dominate the answer" story (the four reference codes agree in control, diverge in the MSR study purely from modeling assumptions); cheapest compute; David-vs-Goliath (free tools vs proprietary CEA/EDF/Framatome/Orano codes); reference codes' input decks are proprietary, so the agent can't find the answer.
- **Caution**: verification (code-vs-code), not validation (vs experiment) — the verdict is comparative, not absolute.

---

## Verified tooling decisions

| Need | Use | Notes |
|---|---|---|
| Neutronics (A, B-indirect, C-depletion) | **OpenMC** | MIT, Python API, **not** export-controlled. The shared pivot. ENDF/B-VIII.0 HDF5 + windowed multipole for on-the-fly Doppler. |
| Neutronics (do NOT use) | ~~Serpent~~ | Export-controlled, unavailable. OpenMC is its deliberate replacement everywhere. |
| CFD + precursor transport (A) | **OpenFOAM** (+ **GeN-Foam** as independent oracle) | Hardest install. GeN-Foam = open-source descendant of this exact LPSC work (EPFL). |
| Fuel-cycle scenario engine (C) | **Cyclus + Cycamore** | `conda install -c conda-forge cyclus cycamore`. **Linux-x86-64 only.** |
| Fuel-cycle depletion (C) | **OpenMCyclus** | Couples OpenMC depletion into Cyclus. |
| MSR online reprocessing (C) | SaltProc-style | SaltProc's original coupling is Serpent2 → confirm OpenMC path or implement the mass-handling in Python. |
| TRISO oracle (B, optional) | **BISON** | License-gated (INL/NCRC). Default to Python-from-scratch; only use if access provided. |

### Hardware verdict
- **Run on Linux x86-64, not macOS.** Several codes ship Linux-x86-64 binaries only (e.g. Cycamore) and the heavyweight C++ codes fight Apple Silicon.
- **A dedicated Hetzner box (~8–16 cores, 64 GB RAM, Ubuntu LTS, ~30–45 €/mo) is the recommended compute brain.** Avoid the cheapest instances — OpenFOAM/Cyclus builds need RAM. The MacBook is the *pilot seat* (run Claude Code from it, drive the remote box); local Docker only for prototyping the two light benchmarks.
- **Everything builds in Docker**, so each tamed tool = a reproducible image, and the skill points to the Dockerfile.

---

## The harness architecture (the actual product)

### Core principle
Make physical truth part of the agent's **environment**, not its **instructions**. Encode every notion of correctness as a script the worker agents can *run but not edit*. Autonomy is safe because the floor is concrete.

### Three durable substrates (nothing important lives only in the chat context)
- **Skills** (`skills/<tool>.md`) — procedural knowledge: how to install/drive each tool. Grown on every issue hit.
- **Ledger** (`ledger.jsonl`, append-only) — episodic knowledge: every action, every gate result with numbers, every reasoning trace. This is also the blog dataset.
- **State files** — task knowledge: the milestone DAG and which nodes are green.
- **Litmus test**: a cold-restart agent should resume from `skills/` + ledger + state files alone.

### The acquisition protocol (mandatory, every tool)
search current docs → install → smoke-test → **validate against a known answer** → write the skill → have a fresh-context agent reproduce from the skill. Not "ready" until all green. Fixing an issue isn't done until the skill is amended.

### Subagent roles (context isolation is the point)
- **Orchestrator** — owns the DAG + ledger, spawns others, does no physics itself.
- **Installer/Acquirer** — runs the acquisition protocol, writes skills.
- **Builder** — writes models/solvers/coupling; **no write access to `gates/` or `refs/`.**
- **Verifier(s)** — spawned fresh per milestone, sees only artifacts + gate output, never the builder's reasoning; charter is adversarial ("find why this is wrong").
- **Skill-auditor** — follows a fresh skill literally to confirm it's reproducible.
- **Diagnostician** — only on gate failure; one hypothesis, one fix, bounded.
- **Scribe** — mines the ledger into the writeup.

### Gates (deterministic, hook-enforced, read-only to workers)
General: statistical convergence; coupling/Picard fixed-point (log oscillations); **energy balance closes** (catches most coupling bugs); physicality bounds; mesh convergence; **feedback sign** (negative temp coefficient; a positive one is a *finding*, surfaced not buried); known-answer validation before trusting anything downstream. Validation is a **gate, never an objective** (don't optimize toward matching the reference — pass once, then freeze settings).

### Long-run durability practices (the findings section)
Context hygiene (orchestrator delegates heavy work to fresh subagents so its own context stays thin); frequent checkpointing; bounded effort + honest escalation ("stuck: tried X/Y/Z, here's the state"); idempotent milestones; **separation of powers** (gates + reference values in a directory workers can't write).

---

## Hard rules
- Never attempt to obtain **Serpent** (export-controlled) or **BISON** without provided credentials (license-gated).
- Never **fabricate a validation target** — every expected number comes from a provided spec or a shown analytic derivation. If you can't find it, flag it.
- The **human provides the three benchmark spec PDFs** (MSFR report, fuel-cycle paper, IAEA CRP-6). The agent cannot fetch these. Stop and request them if absent from `refs/`.
- Prefer **OpenMP threads over MPI** for OpenMC on one machine (shared cross-section data → less RAM).
- Build the physics **manually to a passing gate first, then wrap in autonomy.** The fatal failure mode is debugging the harness on top of a simulation that doesn't yet work.

---

## How to use this brief
- **Claude Code** (build & run the harness): keep this as `CLAUDE.md` at repo root — it's read automatically each session. Put subagents in `.claude/agents/`, slash commands in `.claude/commands/`, blocking checks as hooks. This is where the orchestrator/verifier/gate architecture actually runs.
- **Cowork** (research & writeup): attach this brief + the three spec PDFs at the start of the session. Use it to digest the benchmarks, reason across them, and draft the blog.
- Rough split: **Cowork to think and write, Claude Code to build and run** — both bootstrapped from this same file.

## Companion files
- `SETUP_benchmarks.md` — the install/validation runbook (current).
- `reactor_loop_spec.md` — gate architecture from an earlier heat-pipe passive-safety framing; **partially stale** (we moved to the three benchmarks above). Mine it for the gate/skill patterns, not the reactor choice.
