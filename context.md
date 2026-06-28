# Project Seed — AI-Native Engineering, RCCS Anchor

## Goal
Two linked outputs: (1) a credible Hacker News article, (2) customer/partner messaging to start an **AI-native engineering company**. The article is the proof that makes the company credible — write it only after the technical proof exists.

## Thesis
Hard-tech engineering is **labor-bound, not physics-bound**. AI agents wrapped in a **trustworthiness harness** can do the labor with the rigor intact. The moat isn't the model — it's the harness (gates the agent can't edit + validation against real data + accumulating validated skill modules) that makes agent-driven engineering **verifiable**. We sell trustworthy analysis acceleration to insiders (advanced-reactor / energy / hard-tech builders), not "AI reactor for the regulator." Every output ships with an honest uncertainty budget.

## The one anchor proof (build this first; nothing else is real until it exists)
An AI agent, on a single Linux box, reproduces a **national lab's RCCS** (Reactor Cavity Cooling System — passive HTR decay-heat removal) experiment **two ways against the same measured data**:
- **Rung 1 — reduced-order 1-D model** (resistance network + buoyant loop; runs in ms). Showcases small-models-with-good-judgment: every simplification justified by a dimensionless number (Biot, Rayleigh, **radiation-vs-convection ratio** — radiation dominates when hot).
- **Rung 2 — full OpenFOAM CFD** (conjugate conduction + natural convection + **surface-to-surface radiation with view factors** — the install-hell / multi-code integration). Same data.
- Trust = reduced ↔ CFD ↔ measured data agree (or discrepancy explained). Validation is a gate, never an objective.

**Money shot:** peak temperature rising then **leveling off below the failure limit** — the reactor saving itself. **Surprise beat:** NSTF found passive performance shifted with the weather outside the building.

## Why RCCS (it maxes all four chosen criteria)
Real measured data ✓✓ (Argonne NSTF, NQA-1 licensing-grade; TAMU; UWM; KAERI) · complex software working together ✓✓ · physical intuition ✓✓ ("how does a reactor cool with no pumps?") · low compute / smart small models ✓✓.

## Hard precondition (HARD STOP)
The agent **cannot fetch the dataset** — the human provides it. Decide with Francisco (nuclear CTO, domain verifier) which to target first: **TAMU small rig** (gentler) or **a single accepted NSTF air-cooled test** (more impressive). Put geometry + boundary conditions + measured data in `refs/rccs/` before validating anything. Anti-cheat: build models from physics + provided conditions only; never copy a published input deck/results.

## Harness conventions
- **Acquisition protocol** per tool: search docs → install → smoke-test → validate vs known answer → write `skills/<tool>.md` → fresh-context agent rebuilds from the skill.
- **Substrates** (nothing lives only in chat): `skills/` (procedural), `ledger.jsonl` (every action + gate result + failure/recovery — this is the article's dataset), state files (milestone DAG).
- **Gates** = deterministic hooks, read-only to the builder; reference values in `refs/` the builder can't edit. Separation of powers.
- **Subagents** (fresh context for verifiers): orchestrator / installer / builder / verifier / skill-auditor.
- Everything builds in **Docker**. Run on **Linux x86-64** (a ~8–16 core / 64 GB Hetzner box), not macOS; pilot it from the Mac via Claude Code.

## Tooling
OpenMC (neutronics, MIT, **not Serpent** — export-controlled) · OpenFOAM (CFD + viewFactor radiation + chtMultiRegionFoam) · Python + CoolProp (reduced model) · gmsh/blockMesh · ParaView (headless). Launch autonomously via `claude -p "<goal>" --permission-mode auto --max-turns N` **inside a container**; gates as PreToolUse hooks.

## Sequence (do not skip)
1. Settle dataset with Francisco → populate `refs/rccs/`.
2. De-risk harness on a trivial milestone (e.g. OpenMC Godiva or a closed-form conduction check) — prove the machine (subagent + gate + skill + ledger + skill-audit) on something tiny.
3. **Rung 1** to a passing gate vs measured data.
4. **Rung 2** (CFD) vs the same data; triangulate.
5. Article from the spine + the real ledger (failures shown). Then the partner one-pager.

**The rule:** never write the article or pitch partners before step 4 exists. The validated-against-data result is the only unlock.

## Companion files (already generated)
`messaging_spine_rccs.md` (north star) · `rccs_anchor_buildspec.md` (full two-rung runbook) · `SETUP_benchmarks.md` + `CLAUDE.md` (harness/install detail — scope down to RCCS-only).