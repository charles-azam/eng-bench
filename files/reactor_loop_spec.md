# Autonomous Reactor Passive-Safety Loop — Stack Spec

The premise: one `/goal` runs an entire coupled neutronics + thermal simulation of a microreactor losing its heat sink, decides whether the core saves itself, and **cannot report a result it didn't earn** because deterministic gates block it from declaring success on loosened tolerances. This spec gives you the exact stack, the gate definitions, and the build order so you can size hardware before writing code.

---

## The decision that kills the CFD problem: pick a heat-pipe microreactor

The single most important scoping move is choosing a **solid-core, heat-pipe-cooled microreactor** as the test case rather than a coolant-bearing SMR. A heat-pipe reactor removes heat by conduction through a solid monolith into heat pipes — there is **no flowing coolant**, so there is **no CFD**, and the entire thermal side collapses to a heat-conduction problem that runs on CPU in minutes. The "loss-of-flow" transient becomes **loss of heat sink** (heat-pipe degradation), which is the physically equivalent passive-safety question and is exactly what national labs study for these designs.

This makes the whole project conduction + neutronics feedback, which is the cleanest possible version of the coupled story.

Anchor on a geometry with a **published reference k-eff** so you have a known-answer validation target — the heat-pipe microreactor used in Cardinal's own tutorials is the path of least resistance, since the coupling is already demonstrated for it. Verify whatever reference value you choose against its source; don't trust a remembered number.

---

## The stack (Path A — recommended, no GPU)

**Neutronics — OpenMC.** MIT-licensed, Python API the agent can drive cleanly, not export-controlled. Use the **ENDF/B-VIII.0 HDF5** library with **windowed multipole** data so you get on-the-fly Doppler broadening at arbitrary temperature — this matters because the entire feedback story depends on getting the fuel-temperature reactivity effect right, and you need continuous temperature dependence, not a few tabulated points. Include thermal-scattering S(α,β) data for your moderator (graphite/hydride).

**Thermal — MOOSE Heat Transfer (heat-conduction) module.** Solves the solid temperature field in the monolith. Heat pipes enter as a heat-sink boundary condition: a conductance to a sink temperature, degraded over time to drive the transient. No flow solver, no turbulence model, no CFD.

**Coupling — Cardinal (Argonne).** Wraps OpenMC and hands MOOSE the fission heat source, takes back the temperature field, iterates (Picard) to a coupled fixed point. This is the actual national-lab coupling code, open source, and the David-vs-Goliath credibility comes for free.

**Transient — point kinetics with OpenMC-computed coefficients.** Do **not** run Monte Carlo at every timestep (that's a supercomputer job). Instead: OpenMC computes Doppler and thermal-expansion reactivity coefficients via perturbation runs at steady state; those feed a 6-delayed-group point-kinetics model coupled to a lumped/1-D thermal model. The transient then runs in seconds.

**Skip depletion entirely.** A passive-safety transient needs fresh fuel (or one representative burned state). Depletion was the most expensive thing on the table and buys you nothing here.

**Optional stretch rung — MOOSE Solid Mechanics** for explicit thermal-expansion-driven geometry change feeding back into reactivity. For week one, fold expansion into a coefficient instead; add full mechanics only if days remain.

## The stack (Path B — only if you must have the convection money-shot)

If you decide the visual payoff requires a buoyancy plume (pump dies, natural convection takes over), switch the test case to a coolant-bearing SMR, run the **loop** on a cheap 1-D coolant model (MOOSE **Thermal Hydraulics Module**, THM), and spin up **one** NekRS natural-convection **snapshot** on a single GPU purely for the animation. This is the *only* place a GPU appears, it's late, and it's brief — see sizing below. Everything else is identical to Path A.

---

## The gates — deterministic, hook-enforced, outside the agent's control

These run as post-run hooks that parse solver output and **hard-block** the loop from advancing. The agent cannot edit them mid-run or argue past them. This is the spine of the trustworthiness claim: when an HN skeptic asks "how do you know it didn't hallucinate a safe answer," you link these.

- **Gate 0 — Known-answer validation.** Bare OpenMC model must reproduce the benchmark's published k-eff within statistical agreement (their σ + yours). Nothing downstream is trusted until this passes.
- **Gate A — Statistical convergence.** k-eff standard deviation below threshold (e.g. < 50 pcm); power-tally relative error below threshold (e.g. < 5%) in every mesh element holding meaningful power; **Shannon entropy** confirms the fission source converged before active batches began. Block otherwise.
- **Gate B — Coupling fixed point.** Max temperature change AND k-eff change between successive Picard iterations below threshold (e.g. ΔT_max < 1 K, Δk < 10 pcm). Block if oscillating or not converged within N iterations — and log the oscillation, because a divergence-and-recovery is exactly the content that proves the loop is real.
- **Gate C — Energy balance.** Total fission power from OpenMC must equal total heat removed through the heat-pipe/coolant BC within tolerance (e.g. 1%). This single gate catches a huge class of silent coupling bugs.
- **Gate D — Physicality.** Every temperature within [sink temp, limiting-material melting point]; no negative temperatures; k-eff in a sane band. A temperature *exceeding* a safety limit is **flagged, not suppressed** — it may be the actual answer.
- **Gate E — Mesh convergence.** Peak temperature and k-eff change less than threshold between the two finest meshes (e.g. < 1% / < 50 pcm). No downstream result is trusted on an unconverged mesh.
- **Gate F — Feedback sign.** Doppler coefficient must be negative; total temperature coefficient must be negative for the passive-safety claim to hold. A **positive** coefficient is the Chernobyl failure mode — the harness must surface it loudly as a finding, never bury it.
- **Gate G — Transient classification.** Transient must conserve energy globally and be classified as either *bounded asymptote* (safe) or *material-limit breach* (unsafe). Both are valid, publishable outcomes; the harness reports peak temperature and time-to-peak either way.

### Verifier subagent (fresh context)
A separate agent that sees only the artifacts and gate results — never the generating context — does the judgment checks the gates can't encode: is the flux shape physically sane (peaked in core, depressed at reflector), does the temperature peak coincide with the power peak, does the transient trajectory match what the feedback coefficients predict. A fresh context is much harder to fool than an agent reviewing its own reasoning.

---

## Build order (so you can size before building)

1. **OpenMC standalone** -> reproduce benchmark k-eff. *(Gate 0)*
2. **Add power tally** -> first money-shot: high-resolution flux/power map. *(Gate A)*
3. **Cardinal steady-state coupling** OpenMC <-> MOOSE conduction -> converged operating temperatures. *(Gates B, C, E)*
4. **Perturbation runs** -> Doppler + expansion coefficients. *(Gate F)*
5. **Transient** (point-kinetics + thermal) -> safe/unsafe classification + second money-shot: temperature field animation as power self-regulates. *(Gate G)*
6. *(Path B only)* **One NekRS GPU snapshot** for the convection visual.
7. **Wrap in the `/goal` loop + verifier subagent.**

Crucially: get steps 1–5 working **manually** with real gates by mid-week. *Then* close the loop. The fatal failure mode is debugging the autonomy harness on top of a simulation that doesn't yet work. The headline "one command ran a validated reactor safety case overnight" survives descoping steps 6–7; it does not survive having no working simulation.

---

## Hardware sizing

**Path A:** A single **32–64 vCPU node, 64 GB RAM, ~10 GB disk** for the ENDF/B-VIII HDF5 + multipole data. Each coupled steady state is tens of minutes; the full loop with mesh studies and retries is an overnight job. Runs on a workstation you own ($0) or a modest cloud CPU instance (~$30–150 for the week, less on spot). **No GPU.**

**Path B adds:** one **A100 80GB** instance for the single NekRS snapshot, needed ~2–6 hours total. Current on-demand is roughly **$1–1.8/hr** (neoclouds/marketplace), **~$0.60–0.75/hr spot** — so **~$5–15** of GPU time, on top of the Path A CPU node. Verify live rates at deployment; they move.

**Agent cost:** meter your Claude API usage across the week — a long autonomous loop that fails and re-reasons many times is a real (though modest) line item, and a credible all-in figure (compute + tokens) is exactly the concrete detail the writeup needs.

**Realistic all-in for Path A: under $200, plausibly near zero if you run local.**
