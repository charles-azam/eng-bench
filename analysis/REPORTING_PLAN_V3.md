# V3 article reporting plan

Status: public post-freeze reporting plan, written while the sequential `core-n3` campaign was in
progress and before any eligible prediction, workspace output, score, or artifact-review material
was opened.

This file does not change the frozen tasks, prompts, measurements, eligibility rules, evaluator,
runner, or schedules. Those remain fixed by tag `benchmark-2026-07-12-v3` and the separately
published schedule commits. This plan only constrains how mechanically exported results will be
presented in the article.

## Dataset and campaign accounting

The article will use the primary dataset selected by the frozen gate:

- `n5` if all four primary cells have five infrastructure-valid scheduled replicates;
- otherwise `n3` if all four cells retain three infrastructure-valid scheduled replicates and the
  registered extension is closed or omitted under the 60-hour provider-limit rule;
- no head-to-head quality result if `n3` is ineligible.

The first result table will report, for every task/system cell:

- scheduled and eligible replicates;
- physical attempts and retries;
- completed, agent-failure, refusal, fallback-contaminated, provider-failure, and runner-failure
  counts;
- whether Stage 2 and the supplied-duty ablation ran and passed their eligibility gates.

Physical attempts will never be collapsed into scheduled replicates when reporting infrastructure
failures or retries.

## Figures and exact table fallbacks

Every figure will be generated from `claims.json`, `chart_data.json`, or the CSV tables emitted by
`analysis.publication`. Every plotted value will also appear in an accessible table. Figures will
show individual physical attempts; means may be annotated but will not replace replicate data.

1. **Run-order strip.** Show every physical attempt in actual sequential order, including retries,
   with task, system, scheduled replicate, and terminal status. This exposes provider drift and run
   clustering rather than implying balanced alternation.
2. **NSTF numeric intervals.** Show each P10-P90 interval and P50 against the held-out comparator.
   Positive quantities will use `log2(prediction / observation)` so equal multiplicative misses are
   symmetric around zero. Absolute temperatures will use signed error in degrees Celsius. Blind and
   supplied-duty results will be separate panels.
3. **TRISO numeric intervals.** Failure counts will use
   `log10(prediction + 1) - log10(observation + 1)`. Positive point targets will use signed
   log-ratio error; accepted measurement intervals will remain visible as intervals rather than be
   replaced by their midpoint. Count, onset, and Kr-85 records that share a dependency group will be
   labeled as one evidence family, not counted as independent confirmations.
4. **Categorical outcomes.** Show every submitted category beside the expected category for each
   replicate. Missing predictions, refusals, fallbacks, and invalid outputs remain visible.
5. **Artifact review.** Report the eight registered item judgments separately from numeric results,
   identify the reviewer, and state whether a second review or adjudication occurred.

Evidence class, dependency group, units, measurement provenance, required/optional status, and
numerators/denominators will remain available in the tables.

## Claims the article will not make

The article will not:

- compute an overall score or count metric wins;
- call interval coverage from three or five replicates proof of general calibration;
- compare native token totals or impute subscription dollar cost across providers;
- call the comparison a bare-model benchmark;
- attribute Codex output to a server model that its event stream did not independently identify;
- treat the supplied-duty ablation as an independent benchmark;
- treat dependent TRISO records as independent evidence;
- add post-outcome replacement runs beyond the registered retry rule;
- add decorative 3D graphics or mean-only bar charts.

A narrative overall winner is permitted only under the strict frozen rule: the same system must be
better on registered accuracy, interval score/coverage, completion, and artifact quality without a
material counterexample. Otherwise the conclusion is task-level and mixed.
