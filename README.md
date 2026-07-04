# eng-bench — can an AI do real engineering? Three nuclear campaigns vs. measured data

**The question:** can autonomous AI agents, on a €30/month box, do verification-grade
engineering analysis — predict what real facilities actually *measured*, from only what a
design engineer would receive — and can the result be trusted through published transcripts,
held-out answers, and adversarial audits?

Three campaigns ran the same pipeline (curate inputs → freeze prompts → autonomous runs →
contamination probes → adversarial audit → score against held-out measurements):

| Campaign | Facility / ground truth | Headline | Where |
|---|---|---|---|
| **NSTF** | Argonne ½-scale passive reactor-cavity cooling (33 months of measurements) | flow within ~4% in 6/7 runs; accident transient called correctly by every run; systematic ΔT miss traced to one supplied input | `repro/` |
| **TRISO** | IAEA CRP-6 accident furnace tests (particle-failure statistics) | all zero-failure cases called (10/10); 1800 °C counts under-predicted for a nameable reason; industry's own Cs biases reproduced | `triso/` |
| **HTTR** | Japan's 30 MW reactor, 2010 loss-of-forced-cooling test | agent computed its own reactivity coefficients (OpenMC, 3.4 GB ENDF, overnight); recriticality clock missed ×7, then explained by an audit-diagnosed xenon term ($3.87 rerun: 1 h → 12.5 h, measured 7–8 h in band) | `httr/` |

Total: ~$125 of API. Every claim was adversarially audited by fresh-context agents; all three
audits are published unedited (one forced a full retraction — see `httr/AUDIT.md`).

## Reviewing this repo — start here

1. **`articles/README.md`** — the four publication-ready articles + review guide.
   (Francisco: `articles/reviewer_brief_francisco.md` first.)
2. **The scorecards** (predicted vs. measured, with the misses front and center):
   `repro/scoring/scorecard.md` · `triso/SCORECARD.md` · `httr/SCORECARD.md`
3. **The audits** (unedited): `repro/AUDIT.md` · `triso/AUDIT.md` · `httr/AUDIT.md`
4. **The evidence**: `repro/transcripts/` (21 full tool-call logs), `repro/runs/` (every
   run's calculation note, models, META), `repro/probes/` (contamination probes).

## Layout

```
eng-bench/
├── articles/        # the four articles + figures + interactive calculator + HN FAQ  ← REVIEW
├── repro/           # the publishable pack (all 3 campaigns): inputs, runs, transcripts,
│                    # scoring, probes, audits — mirrors the public repo eng-bench
├── triso/, httr/    # campaign working dirs: pack, held-out refs, scorecard, audit
├── rccs/            # original NSTF benchmark curation (TASK, inputs, held-out refs, sources)
├── runs/            # raw harvested run outputs (incl. the new Fable-VPS and xenon runs)
├── packs/, experiment/  # frozen run packs (gitignored bulk on disk)
├── handoff/         # complete project memory — read handoff/00_INDEX.md in any fresh session
└── archive/         # pre-pivot research
```

## Separation of powers (the integrity model)

Builders see `inputs/` only — facts, no outcomes; held-out answers live in `refs/`/`scoring/`
and were never on the run machine. Runs are headless and autonomous; their full transcripts
are published (NSTF/TRISO: zero web calls; HTTR: design-data web access only, audited).
Inputs were independently re-curated by a separate agent from the raw report; probes show the
models cannot recall the measured values; fresh-context adversarial audits reviewed every
claim, and every correction — including one retraction — was applied and disclosed.

*Public artifact repo (same content as `repro/`): `github.com/charles-azam/eng-bench` —
staged locally at `~/eng-bench-public`, published by the repo owner.*
