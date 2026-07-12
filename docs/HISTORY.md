# How NSTF-Bench got here

This repository began as `eng-bench`, a July 2026 experiment comparing native coding agents
(Claude Code and Codex) on nuclear-engineering prediction tasks. That experiment published
results, retracted them after auditing its own inputs, rebuilt itself four times under a
preregistered protocol, and produced **no model comparison**. NSTF-Bench keeps the corrected
scientific assets and replaces the campaign machinery with a community-runnable harness. This
file is the honest record; every artifact referenced below is reachable at the pushed git tags.

## The original results and their retraction (tag `capstone-v1-2026-07-03`)

Twelve-plus autonomous agent runs predicted measured behavior of Argonne's NSTF passive cooling
facility, IAEA TRISO furnace tests, and the HTTR loss-of-forced-cooling test, and four articles
were published. A line-by-line source audit then found defects in the benchmark *inputs*
important enough to invalidate the headline claims:

- a caesium-in-SiC diffusion equation (IAEA-TECDOC-1674 Eq. 10.9) had been transcribed with
  three errors, one prefactor off by ~13 orders of magnitude — net diffusivity ~5.6× too low at
  the report's 1600 °C checksum ([TRISO_CORRECTIONS.md](TRISO_CORRECTIONS.md));
- the NSTF pack disclosed a design duty mapping (56.07 kWt) close to the held-out quantity
  agents were asked to infer (54.49 kWt at the tested endpoint), undercutting the blind-prediction
  framing;
- a peak-window average was described as a maximum; a whole-system radiation fraction and a
  post-peak cooldown were stated without support in the measured record;
- several TRISO counts, onset times, and Kr-85 releases were treated as independent evidence
  although the source derives them from one dependent inference chain.

The agents were not caught cheating; the benchmark was wrong. The articles were corrected in
place and the results withdrawn.

## Four rebuild campaigns, four independent failures

The rebuild froze corrected task bytes, preregistered a protocol, and attempted a scored
Claude-vs-Codex comparison. Each version failed before producing an eligible score, each for a
different reason (full records under `results/excluded/` at tag `benchmark-2026-07-12-v4`):

- **v1** died in run finalization (`v1-finalizer-bug`).
- **v2** completed its schedule but was excluded for two runner-integrity failures: the sandbox
  retained effective UID 0 so Claude's scored invocation exited before a model event, and
  locale-dependent ledger ordering disagreed with the frozen bytewise pack hashes
  (`v2-ineligible-campaign`).
- **v3** was excluded after Ubuntu's unattended-upgrade service replaced curl/libcurl *during* a
  scored attempt, changing the bind-mounted host filesystem mid-run (`v3-environment-drift`).
- **v4** hardened all of the above, then died by operator error: during a live retry, an
  operator-side agent installed a package on the frozen host; the post-run environment hash
  differed, the attempt failed its integrity check, and the preregistered eligibility gate —
  correctly — refused to score a partial comparison. A pre-results security review had also
  found the sandbox mounted broad host `/etc` state and left provider credentials readable, so
  raw attempt streams stay private.

Two lessons drove the redesign. First, solo-operated frozen-host metrology fails on its own
terms: the machinery meant to guarantee the comparison consumed the project. Second, the
scientific assets that survived every audit — the corrected packs, the held-out records with
evidence classes and dependency groups, the deterministic interval-aware scorer — were the
valuable part all along.

## What NSTF-Bench keeps, changes, and drops

**Keeps (byte-identical):** the corrected NSTF task packs (`tasks/`), the frozen agent prompt
(`protocol/PROMPT.md`), the NSTF held-out records, and the deterministic evaluator semantics.

**Changes:** the harness is now [Harbor](https://github.com/laude-institute/harbor) — anyone can
run any agent against the tasks with one command; the verifier (with the held-out answers)
reaches the container only after the agent finishes; network policy is an explicit allowlist;
scoring adds a fail-closed `score-task` path that needs no ledger.

**Drops:** the TRISO task (one problem, fully done — the corrected TRISO pack lives at tag
`benchmark-2026-07-12-v4`), the eligibility-gate/preregistration machinery, the VPS runner, and
the campaign accounting pipeline. Rigor now means: reproducible evaluation, published
transcripts, descriptive reporting — not clinical-trial gates a single operator cannot sustain.

## Tags

| Tag | What it preserves |
|---|---|
| `capstone-v1-2026-07-03` | The original campaign, articles, runs, and audits |
| `benchmark-2026-07-11-v1` / `-v2` | The first frozen rebuilds and the v2 exclusion record |
| `benchmark-2026-07-12-v3` | The v3 environment-drift exclusion |
| `benchmark-2026-07-12-v4` | The final frozen protocol, runner, TRISO task, and all exclusion records |
