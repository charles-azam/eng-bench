# Software Acquisition & Validation Runbook — Three Nuclear Benchmarks

You are setting up the toolchain for three independent nuclear-engineering benchmarks on a fresh Linux x86-64 machine. This file tells you **what** to install, **how to prove each tool works**, and **what to do when you hit trouble**. It does **not** give you copy-paste commands to run blindly — install procedures drift, so for every tool you **verify the current official documentation first**, then execute.

Your success on this phase is not "I ran some installers." It is: **every tool is installed, smoke-tested, validated against a known answer, and documented in a skill that a different agent could follow from scratch.**

---

## 0. Operating principles (read first, follow always)

### The acquisition protocol — apply to EVERY piece of software
A tool is not "ready" until all five steps are green, in order:

1. **Search** the current official docs/repo for the install method (do not trust your training data for exact commands — versions change).
2. **Install** it.
3. **Smoke-test**: run the most trivial possible thing and confirm it executes at all.
4. **Validate**: reproduce a *known answer* (analytic result or published benchmark value) within tolerance. A tool that runs but gives wrong physics is worse than no tool.
5. **Write a skill**: create `skills/<tool>.md` capturing the install command that actually worked, the environment gotchas, the smoke test, the validation snippet **with the expected number**, and the canonical invocation. Then have the skill be followed literally by a fresh-context check to confirm it's reproducible.

If any step fails, **do not paper over it**. Log the failure to the ledger, diagnose, fix, and amend the skill with the failure + resolution. The skill library is the permanent memory of this project — every landmine you hit once should never cost time again.

### Hard rules — do not violate
- **Do NOT attempt to obtain Serpent.** It is export-controlled and unavailable. OpenMC is its deliberate open-source replacement throughout. If any benchmark spec says "Serpent," you implement the equivalent in OpenMC.
- **Do NOT attempt to download BISON** unless a credentialed access path has been explicitly provided to you. It is license-gated (INL/NCRC). For the TRISO benchmark, default to the from-scratch Python implementation; treat BISON as an optional oracle only if access exists.
- **Do NOT fabricate validation targets.** Every expected number must come from a provided specification document or a first-principles analytic derivation you show your work for. If you cannot find the reference value, say so and flag it — never invent one.
- **Everything builds in a Docker container**, even on the remote host. Each tamed tool becomes a reproducible image; the matching skill points to the Dockerfile that works. This is how the final result becomes "clone the repo, run the container, reproduce the number."
- **Prefer OpenMP threads over MPI ranks** for OpenMC on a single machine: cross-section data is shared across threads but duplicated per MPI rank, which wastes RAM.

### What the human provides (you cannot fetch these)
- The **three benchmark specification documents** (MSFR coupling report; fuel-cycle/Am-transmutation paper; IAEA CRP-6 TRISO benchmark). These define your validation targets. If they are not in your working directory, **stop and request them** before validating anything downstream.
- Any **BISON access credentials**, if and only if that path is chosen.

---

## 1. Environment

- **OS**: Linux x86-64, Ubuntu LTS (22.04 or newer). Not macOS — several of these codes (e.g. Cycamore) ship Linux-x86-64 binaries only, and the heavyweight C++ codes fight Apple Silicon.
- **Base packages**: build toolchain (`build-essential`, `cmake`, `git`, `gfortran`), plus a Miniconda/Mambaforge install for environment management.
- **Python**: 3.11+ with NumPy, SciPy, pandas, matplotlib.
- **Suggested directory layout** (create it, and treat `gates/` and `refs/` as read-only to the build agents):

```
project/
├── skills/        # one <tool>.md per software, grown over time
├── gates/         # executable validation checks (agents may run, not edit)
├── refs/          # benchmark specs + reference values (read-only)
├── benchmarks/
│   ├── triso/
│   ├── fuelcycle/
│   └── msfr/
├── docker/        # one Dockerfile per environment
└── ledger.jsonl   # append-only log of every action + every gate result
```

Each layer below ends with the **skill you must write** and the **gate you must pass**. Do them in order — later layers depend on earlier validation.

---

## 2. Layer 0 — OpenMC + nuclear data  *(the shared pivot — needed by TRISO and MSFR)*

**What**: OpenMC, a Monte Carlo neutron/photon transport + depletion code (MIT-licensed, Python API, not export-controlled).

**Install (verify against current docs at docs.openmc.org)**: via conda-forge —
`conda config --add channels conda-forge && conda config --set channel_priority strict && conda create -n openmc-env openmc && conda activate openmc-env`

**Nuclear data**: download the official **ENDF/B-VIII.0 HDF5 library, with windowed multipole data**, from `openmc.org/data` (windowed multipole gives on-the-fly Doppler broadening at arbitrary temperature — you will need it for any temperature-feedback work). Set the `OPENMC_CROSS_SECTIONS` environment variable to the resulting `cross_sections.xml`. To keep the data footprint small you may instead use the `openmc_data_downloader` package to fetch only the nuclides your materials use. **Ensure thermal-scattering S(α,β) tables are present** for any moderator you model (e.g. graphite, H in ZrH, Be).

**Smoke test**: build a single fuel pin cell, run a k-eigenvalue calculation, confirm it returns a k-effective with a standard deviation at all.

**Validation gate (Gate 0)**: reproduce a known-answer criticality benchmark — **Godiva** (bare HEU sphere) or **Jezebel** (bare Pu sphere), both keff ≈ 1.0 by construction and present in OpenMC's own examples/regression suite. Require agreement within combined statistical uncertainty. Nothing downstream is trusted until this is green.

**Skill to write**: `skills/openmc.md` — working install, the `OPENMC_CROSS_SECTIONS` setup, the threads-not-MPI memory rule, the S(α,β) gotcha, and the Godiva validation snippet with the expected keff.

---

## 3. Benchmark A — TRISO fuel performance  *(Python-first, lightest tooling)*

**Goal**: from the IAEA CRP-6 irradiation conditions (provided in `refs/`), predict particle failure fraction. The physics models are written by you in Python; validate each layer against a closed-form solution before coupling.

**What to install**: just the scientific Python stack (already present) plus, optionally, a stochastic/Weibull stats helper. **Optional oracle**: BISON — only if access was provided; otherwise skip and note it.

**Smoke test**: solve 1-D spherical heat conduction with a uniform volumetric source in a single sphere; confirm it runs and produces a temperature profile.

**Validation gates (analytic, per layer)**:
- **Conduction**: steady 1-D spherical conduction with uniform source has a closed-form parabolic temperature profile — match it.
- **Pressure rise**: fission-gas production → internal pressure via an ideal-gas + mass-balance model — check against the hand-calculated value for a fixed burnup.
- **Mechanics/failure**: SiC shell stress + Weibull failure statistics — sanity-check limiting cases.
- **End-to-end**: predict failure fraction, then compare to the IAEA CRP-6 *measured* values (held out in `refs/` — reveal only at scoring). Any empirical correlation you use **must cite its source** and be checked against the data point it came from.

**Skill to write**: `skills/triso_models.md` — each sub-model, its analytic check, and its expected value.

---

## 4. Benchmark B — Fuel-cycle / Am-transmutation  *(Cyclus stack, cheap compute)*

**Goal**: reproduce the control trajectory (solid-fuel fleet) of the provided fuel-cycle paper as a validation gate, then attempt the MSR/Am-transmutation trajectory and compare your modeling choice to the spread of the four (proprietary) reference codes.

**What to install (verify against fuelcycle.org)**:
- **Cyclus + Cycamore** (scenario engine + facility archetypes): `conda install -c conda-forge cyclus cycamore`. **Linux-x86-64 only.** Cycamore must be installed in the same location as Cyclus.
- **OpenMCyclus** (couples OpenMC depletion into Cyclus as a depletable reactor archetype): install from its GitHub repo per its README.
- **Online-reprocessing logic**: a **SaltProc**-style approach for the liquid MSR fuel. ⚠️ SaltProc's original coupling targets Serpent2 — since Serpent is unavailable, either find/confirm an OpenMC-coupled path or implement the online-reprocessing mass-handling yourself in Python. Decide and document which.

**Smoke test**: run the Cyclus "once-through" tutorial input from fuelcycle.org and confirm it produces the expected `.sqlite` output; run the Cyclus + Cycamore unit tests and confirm they pass.

**Validation gate**: reproduce the tutorial once-through reference output (provided by the Cyclus project) bit-for-bit/within tolerance; then reproduce the paper's **control-trajectory equilibrium values** (where the four reference codes agree → a defensible target band) before attempting the MSR trajectory.

**Skill to write**: `skills/cyclus.md` (install, the dependency list — Boost, libxml++, HDF5, Coin-Cbc — the unit-test command, the once-through validation) and `skills/openmcyclus.md`.

---

## 5. Benchmark C — MSFR neutronics↔thermal-hydraulics coupling  *(heaviest; the real multiphysics)*

**Goal**: reproduce the LPSC MSFR benchmark (provided report) — a 2-D molten-salt cavity coupling Monte Carlo neutronics, CFD, and 8-group delayed-neutron precursor transport. The original uses Serpent + OpenFOAM; you replace Serpent with **OpenMC**.

**What to install**:
- **OpenFOAM** (CFD + the precursor advection-diffusion-decay equations). Note the original used a `foam-extend` lineage; confirm which OpenFOAM distribution your chosen coupling/GeN-Foam version requires, and install that one. This is your hardest install — budget for it and write a thorough skill.
- **GeN-Foam** (open-source multiphysics descendant of this exact LPSC line of work; EPFL): build it against the matching OpenFOAM version per its current instructions. Use it as your **independent oracle**.
- Your **OpenMC ↔ OpenFOAM coupling harness**: OpenMC supplies the fission-rate/power field on the CFD mesh; OpenFOAM solves temperature, velocity (Boussinesq buoyancy), and the 8 precursor families; the resulting delayed-neutron source is fed back into OpenMC. You build and own this Picard loop.

**Smoke tests**: OpenFOAM — run the classic lid-driven cavity tutorial. GeN-Foam — run one of its shipped tutorial cases. OpenMC — already validated in Layer 0.

**Validation gates (from the provided report — staged, easiest first)**:
- **Phase 0.1** (velocity only): lid-driven cavity, max velocity = 1 m/s at the moving wall. Match the streamlines.
- **Phase 0.2** (static neutronics): reproduce the reference **keff = 1.0022 (ρ = 219.5 pcm)**; β_eff via IFP ≈ **654.6 pcm** (treat β_eff as a stretch target — IFP in circulating fuel is subtle).
- **Phase 1.1** (circulating fuel): precursor drift reduces reactivity by ≈ **71.7 pcm** and β_eff to ≈ 0.96× static.
- **Phase 1.3 / 1.5** (power & buoyancy coupling): reactivity ≈ **−3925 / −3938 pcm**.
- **Cross-check** every result three ways: your OpenMC+OpenFOAM loop ↔ GeN-Foam ↔ the report's numbers.
- **Physical-consistency gates** (always on): energy balance closes (fission power in = heat removed); reactivity falls as power rises (negative feedback); precursor drift reduces β_eff.

**Note for the writeup**: the report documents a known bug in the original code (the 8 precursor equations shared one source term instead of 8 distinct ones — its precursor *distributions* are therefore not a numerical reference). Implement the source terms correctly from the equations; if your corrected distributions look right, flag this as a finding.

**Skills to write**: `skills/openfoam.md`, `skills/genfoam.md`, `skills/openmc_openfoam_coupling.md`.

---

## 6. Skill template (use for every `skills/<tool>.md`)

```
# <tool> — skill
## Install (verified working on <date>, <OS/arch>)
<exact commands that worked>
## Environment / gotchas
<env vars, version pins, the traps that cost time>
## Smoke test
<trivial command + expected sign of life>
## Validation
<command + EXPECTED reference value + tolerance + source of that value>
## Canonical invocation
<how downstream steps should call this tool>
## Failure log
<every issue hit + its resolution — append over time>
```

---

## 7. Definition of done for this phase

This setup phase is complete only when:
- [ ] OpenMC installed, Godiva reproduced, `skills/openmc.md` written and re-verified from scratch.
- [ ] TRISO Python models pass their analytic gates; `skills/triso_models.md` written.
- [ ] Cyclus + Cycamore + OpenMCyclus installed, unit tests pass, once-through reproduced; skills written.
- [ ] OpenFOAM + GeN-Foam installed, tutorials run; skills written.
- [ ] OpenMC↔OpenFOAM coupling harness reproduces MSFR Phase 0.1 and 0.2 within tolerance.
- [ ] Every tool has a Dockerfile in `docker/` and a reproducible skill.
- [ ] The ledger records every install, every smoke test, and every gate result with its numbers.
- [ ] A fresh-context agent could rebuild the entire environment from `skills/` + `docker/` alone — test this and report whether it holds.

Work the layers in order. Validate before you trust. When something breaks, the fix isn't done until the skill is updated.
