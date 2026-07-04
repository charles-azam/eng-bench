# Project constitution

**Maintainer note:** the full project memory (history, campaign records, infrastructure
runbook, roadmap) is kept **locally in `handoff/`**, which is git-ignored and deliberately not
published in this repo.

The objective is to showcase how an AI can — or cannot — do real engineering work.

The final objective is to generate an article that would work well on Hacker News and showcase
the ability of an engineering company to run simulations autonomously.

## The benchmark (settled)

A passive **Reactor Cavity Cooling System (RCCS)**, validated against real measured data from the
**Argonne NSTF** ½-scale air-cooled facility. Chosen because it maxes all four target properties:
real measured data, complex multi-software engineering, strong physical intuition, and low
compute / smart small models. Everything lives in `rccs/`. Rationale is in `rccs/PROJECT_SEED.md`.

## How it is set up

- **Builder** gets `rccs/TASK.md` + `rccs/inputs/` and produces a calculation note in
  `rccs/output/`. Treated like an engineer: it chooses its own methods. It must **not** read
  `rccs/refs/` or `rccs/sources/`, nor look up the facility's published results.
- **Independent checker** (designed later) reads the output, compares against the held-out
  measured data in `rccs/refs/`, verifies no cheating, and reviews the work to write the article.

## Working notes for any session

- Keep the separation of powers: inputs and the held-out answers must never mix.
- The run target is a ~16-core / 32 GB Linux box; the reduced model runs anywhere.
- Earlier pre-pivot research (TRISO, MSFR, fuel-cycle) is kept locally in `archive/`
  (git-ignored, not published).
- Deliberately minimal for now; additional builder/checker instructions come later.
