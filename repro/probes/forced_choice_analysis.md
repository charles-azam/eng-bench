# Forced-choice recall probes — analysis

Refusal-based probes (a model *declining* to recall) are weak evidence, so we also forced a
choice: 4 questions × 5 options each, models MUST answer even if guessing. Opus ×3 + Sonnet ×1
per question. Raw transcripts: `forced_choice_results.txt`; prompts: `fc1–fc4` (in results file).

## Results (correct answers: Q1=C, Q2=B, Q3=D, Q4=C)

| Question (measured quantity) | Opus (3 tries) | Sonnet | Hits |
|---|---|---|---|
| Q1 mass flow (34.5 kg/min) | A, A, D | B | 0/4 |
| Q2 plate temp (390 °C) | B, D, C | B | 2/4 |
| Q3 riser wall (163 °C) | D, D, D | D | 4/4 |
| Q4 riser ΔT (84 °C) | B, B, B | E | 0/4 |
| **Total** | | | **6/16 = 37.5%** vs 20% chance |

Binomial p(≥6 | n=16, p=0.2) ≈ 0.12 — **not significant**.

## Design flaw disclosed (cuts both ways)

The option sets were generated symmetrically around the true value, so **the correct answer sat
at the median of the sorted options in all four questions**. A model using a "pick the physically
mid-plausible value" heuristic scores above chance without any recall — and one Opus response
literally states "this is a guess near the mid-range." The Q2/Q3 hits are fully consistent with
that heuristic; on Q1/Q4 the models did *not* pick the median and were wrong.

## Conclusion

No reliable recall demonstrated: every single response self-labels as a guess ("essentially a
blind guess", "don't rely on it"; one Opus reply even challenged the premise as possibly
fabricated). Aggregate performance is statistically indistinguishable from informed guessing,
and the apparent hits are explained by the acknowledged design flaw. A cleaner future probe
would place the true value off-median and randomize option generation independently of the
truth. Combined with the refusal probes, the zero-web-access transcripts, and the consistent
self-explained prediction errors, the evidence continues to support derivation over retrieval —
with the honest caveat that latent-memory influence on assumption choices can never be fully
excluded.
