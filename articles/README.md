# Articles — review guide (everything is in THIS repo)

**For review (Francisco / anyone): read the four files below, in this order.** They are the
canonical articles; they render fully on GitHub (figures included).

| # | File | What it is | ~Words |
|---|---|---|---|
| 1 | `article3_capstone.md` | **The lead post**: "I ran an AI engineering department for a week" — all three campaigns, the retraction, the xenon fix | 2,400 |
| 2 | `article1_final.md` | NSTF deep-dive: "I gave an AI the blueprints of a nuclear-safety experiment…" | 2,500 |
| 3 | `article2_final.md` | Physics explainer: "The nuclear reactor that cools itself" (+ interactive calculator) | 1,100 |
| 4 | `article4_triso.md` | TRISO: "A billion tiny pressure vessels" | 1,500 |

Support material:

- `figures/` — all article figures. `fig_ensemble.png` = every archived run vs. measured, no
  cherry-picking. `rccs_schematic.svg` = the system diagram.
- `rccs_calculator.html` — the interactive model (open directly in a browser; fully offline).
- `hn_faq.md` — prepared answers for the HN comment section, including the hard ones
  (the retracted HTTR claim, the xenon-rerun objection, Fable's duty rejection).
- `reviewer_brief_francisco.md` — **start here if you are Francisco**: the three specific
  things being asked of you, ~45 min.

Evidence trail behind every claim (also in this repo):

- `../repro/scoring/scorecard.md` — NSTF predicted-vs-measured, all runs, audited.
- `../triso/SCORECARD.md` + `../triso/AUDIT.md` — TRISO results + unedited adversarial audit.
- `../httr/SCORECARD.md` + `../httr/AUDIT.md` — HTTR results + the audit that forced the
  retraction of "beat the professional code".
- `../runs/run_httr_xenon/output/addendum_note.md` — the $3.87 xenon diagnostic
  (recriticality 1 h → 12.5 h, band contains the measured 7–8 h).
- `../repro/transcripts/` — full tool-call logs of every run (21 files).
- `../repro/` — the complete pack that becomes the public repo
  (`github.com/charles-azam/eng-bench`, staged at `~/eng-bench-public`).

## What `blog_ready/` is

`blog_ready/*.md` are byte-exact copies of the deployment versions that live on branch
`cazam/eng-bench-articles` of `charles-azam.github.io` (Astro blog). Same text as the
canonical articles above, plus blog frontmatter (EN+FR titles/descriptions, slugs), the
"Original repository" line, an in-page `<iframe>` of the calculator in the explainer, and
site-relative image paths (which only resolve when deployed — on GitHub, read the canonical
files instead). If the canonical articles change, regenerate/re-sync the blog copies before
deploying.
