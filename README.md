# eng-bench — Autonomous Engineering Benchmark: passive reactor cooling vs. real data

**The question:** can an AI agent, on a single modest box (no supercomputer), reproduce a
national lab's measured passive-cooling experiment — using engineering judgment rather than brute
force — and can an independent agent confirm it got the right answer honestly?

The benchmark is a **Reactor Cavity Cooling System (RCCS)** — the passive, pump-free system that
removes a high-temperature reactor's decay heat after shutdown. The validation anchor is the
**Argonne NSTF** ½-scale air-cooled RCCS, which has real measured temperatures and flow rates.
It maxes the four properties this benchmark is built around: **real measured data, complex
multi-software engineering, strong physical intuition, and low compute / smart small models.**

## How it works

1. A **builder** agent is given `rccs/TASK.md` + `rccs/inputs/` (geometry, materials, conditions —
   **no answers**) and asked, like any engineer, to produce a **calculation note** predicting the
   temperatures, flows, and heat split, with its working in `rccs/output/`. It chooses its own
   methods and tools. It must not look up the facility's published results.
2. A **separate, independent agent** (designed later) reads the builder's output, compares it to
   the **held-out measured data** in `rccs/refs/`, checks that the builder did not cheat, and
   reviews what it did — the problems it hit and how it solved them — to write up the result.

## Layout

```
eng-bench/
├── CLAUDE.md        # project constitution
├── README.md        # this file
├── rccs/            # THE BENCHMARK
│   ├── TASK.md      # the engineering ask handed to the builder  ← start here
│   ├── PROJECT_SEED.md  # rationale / north-star (why RCCS, the thesis)
│   ├── inputs/      # geometry, materials, conditions, measurement locations (NO answers)
│   ├── output/      # the builder writes its calculation note + working files here
│   ├── refs/        # ⛔ HELD-OUT measured data — for the independent checker only
│   └── sources/     # the source reports (PDF + text) + provenance — off-limits to the builder
└── archive/         # superseded earlier-benchmark research (TRISO, MSFR, fuel-cycle) — kept, unused
```

## Run target
A ~16-core / **32 GB** Linux box (e.g. a ~€40/mo Hetzner machine). The 32 GB of RAM is the spec
that matters (it removes out-of-memory risk on CFD builds, surface-to-surface radiation, and
meshes); core count only sets speed.

## Status
Problem settled, repo cleaned, data acquired and prepared (Argonne NSTF). The benchmark is ready
to hand to a builder agent. The independent checker agent and any additional builder instructions
are deliberately left for later.
