> **Archived (July 2026).** This is the preregistered v4 campaign protocol, kept verbatim as a
> historical record. The campaign it governed was never scored (see [HISTORY.md](HISTORY.md)).
> NSTF-Bench supersedes its runner/eligibility machinery with the Harbor tasks in `harbor/`;
> the scientific bytes (task packs, prompt, held-out records, scorer semantics) are unchanged.

# Preregistered native-agent engineering benchmark

Protocol version: `2026-07-12-v4`

Status: **frozen protocol**. No scored run may start until the freeze procedure in this document
has produced its manifest and tag. Changes after that tag require a new protocol version and make
earlier runs ineligible for the new comparison.

## 1. Research question and comparison unit

This experiment compares two native engineering-agent systems, not isolated model APIs:

- Codex with GPT-5.6 Sol;
- Claude Code with Claude Fable 5.

The question is whether either native system can produce a reproducible, uncertainty-aware
engineering prediction from the same curated offline evidence. The command harness, tool behavior,
and served model are part of the system being compared and must be reported as such.

No directional winner hypothesis is registered. The experiment will report task-level accuracy,
calibration, completion, runtime, and artifact quality. It will not collapse unlike tasks into one
leaderboard number.

## 2. Frozen tasks and experimental cells

Primary tasks:

1. `nstf_blind_derive_duty`: predict an air-cooled natural-circulation experiment from electrical
   heater input without being given the thermal duty delivered to the loop.
2. `triso_corrected_bounded_annex`: predict TRISO failure and release while explicitly judging
   whether the bounded annex supports each conclusion.

Registered ablation:

3. `nstf_supplied_duty`: the NSTF task with the scaled thermal-duty input supplied. This is an
   input-information ablation, not a second independent benchmark.

The blind NSTF pack consists only of `tasks/nstf_blind_derive_duty/TASK.md` and the files under
`tasks/nstf_common/inputs/`. The supplied-duty pack uses its own `TASK.md`, those same common files,
and `tasks/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv`. Human protocol and provenance
files are never mounted into an agent run.

### Sample sizes and ordering

- Stage 1: three runs in each primary system/task cell: 2 systems x 2 tasks x 3 = 12 launches.
- Stage 2: after all four cells have three infrastructure-valid launches, add attempts 4 and 5 to
  each cell: 8 launches, for `n=5` per primary cell.
- Stage 3: three supplied-duty NSTF runs per system: 6 launches.
- Target total: 26 launches, plus preserved infrastructure failures.

Run one launch at a time. Before a stage begins, generate its complete order by shuffling its cell
and attempt tuples with `random.Random(20260711).shuffle(...)`; save that schedule before launching
the first run. Do not reorder after seeing results.

`n=3` is the minimum publishable primary sample size. If a provider limit prevents Stage 2 by 60 h
after the first scored launch, report the equal `n=3` result and the omitted extension. A cell with
fewer than three infrastructure-valid launches prevents publication of the head-to-head result.

## 3. Run controls and native-system policy

For every launch:

- use the same VPS, hash-checked host/toolchain environment, preinstalled scientific packages, 60-minute model-working
  budget, and 75-minute hard process timeout;
- keep both automatic APT transaction timers and services masked and inactive for the complete
  campaign, and forbid package, CLI, runner-environment, or host reboot changes between freeze and
  final archive;
- use the highest reasoning setting advertised by each frozen CLI (`max` at protocol drafting);
- provide a plain task prompt, with no `/goal`, subagents, repository agent instructions, web tools,
  package installation, or task-specific coaching;
- create a hash-recorded host copy of the task pack using bytewise (`LC_ALL=C`) path collation,
  then give the agent a fresh
  writable working copy whose before/after file hashes are retained;
- keep measurements, evaluator code, protocol files, old runs, and source reports outside the
  agent-visible namespace;
- deny direct egress and permit only the provider/authentication endpoints required by the native
  CLI through a fail-closed proxy;
- capture the prompt, structured CLI event stream, shell/tool trace, created files, environment
  manifest, timestamps, exit status, usage, and served model identity.

The runner must compare a freshly generated environment manifest byte-for-byte with the frozen
manifest before allocating a canonical attempt directory and again immediately after inference.
A failed precondition creates no attempt. A failed post-inference comparison preserves the opaque
raw outputs, emits no normalized prediction, and finalizes as `runner_failure` for the registered
single retry.

Freeze exact CLI versions, model identifiers, reasoning settings, allowed tools, proxy allowlist,
environment-snapshot digest, task prompt, and task-pack hashes. Run a non-scored isolation preflight proving
that inference succeeds while arbitrary HTTP requests and reads of a hidden canary path fail.

Before freeze, also run each system through the exact scored CLI-command wrapper on a neutral
checksum task. The parity probe must use the frozen model, effort, permissions, tools, persistence,
configuration, MCP, sandbox, and event-output flags; it must produce the preregistered file hash,
finish with a provider-specific success event, and pass served-model/fallback validation. This proves
command parity, not the separate protocol-verification, environment-comparison, copying,
finalization, or timeout lifecycle, which has its own integration tests. A provider-specific
baseline prompt may be used because Fable can fail closed on content-free prompts; the registered
Fable readiness probe is an elementary slab-conduction calculation.

The VPS process retains effective UID 0 inside an external bubblewrap namespace. The namespace
truthfully sets `IS_SANDBOX=1`, the deliberate-sandbox marker recognized by the frozen Claude
executable, only after it has cleared the environment, restricted mounts, unshared the
network/PID/UTS/IPC namespaces, and installed the fail-closed egress bridge.

### Served-model rule

Attribute output only to the model that actually served it. For Claude Code, capture the assistant
message model, fallback system events, and final usage object from the event stream. The current CLI
emits `usage.iterations: []` for both the genuine-Fable smoke and a preserved Opus fallback, so that
field is retained but cannot be the identity oracle. Per-assistant model identity and explicit
fallback events therefore fail closed. A Fable 5 refusal is an agent-system completion failure even
if Claude Code automatically obtains an answer from Opus 4.8:

- preserve the refusal and fallback transcript;
- never attribute fallback text or numbers to Fable 5;
- exclude fallback numeric predictions from Fable quality metrics;
- if the primary task was served entirely by fallback, record no Fable prediction for that attempt.

Apply the same identity rule to any unexpected Codex model substitution. Do not rewrite a task or
prompt after observing a refusal.

### Failure and retry rule

- Provider authentication, rate-limit, transport, runner, or corrupt-trace failures are
  infrastructure failures. Retry once with identical inputs and preserve both attempts.
- Incorrect reasoning, missing outputs, schema-invalid output, tool misuse, timeout after a valid
  model session, and served-model refusal are system completion failures. Do not retry them.
- Never remove a failed attempt from completion-rate denominators.

A stopped stage may resume only from its original complete schedule. The resume verifier may skip
only a contiguous prefix of finalized, checksum-valid attempts whose metadata matches the frozen
schedule. It must reject incomplete or corrupt directories, gaps, altered identities, unregistered
attempt numbers, and retries for non-infrastructure outcomes. All first attempts still precede the
retry phase, and retries retain original schedule order.

## 4. Required output contract

Each task requires `output/calculation_note.md`, all working files, and
`output/predictions.json`. The JSON file must have this shape:

```json
{
  "schema_version": "1.0",
  "task_id": "task identifier from TASK.md",
  "predictions": [
    {
      "metric_id": "exact identifier from TASK.md",
      "point": 1.23,
      "p10": 0.9,
      "p50": 1.23,
      "p90": 1.8,
      "units": "exact unit from TASK.md",
      "confidence": 0.7,
      "qualitative": null,
      "category": null,
      "source_artifact": "output/calculation_note.md"
    }
  ],
  "annex_sufficiency": {
    "status": "sufficient|partially_sufficient|insufficient",
    "missing_physics": ["plain-language item"],
    "consequence": "effect on the predictions"
  },
  "most_uncertain_assumption": "plain-language statement"
}
```

This workspace file is the shared structured contract and is validated after execution. Neither
treatment uses a provider-specific CLI final-message schema flag.

The runner injects `run_id` into each prediction before evaluator ingestion; agents must not invent
it. All shown keys are required. Numeric metrics use JSON numbers, `point == p50`, ordered
`p10 <= p50 <= p90`, `confidence` from 0 to 1, and null `qualitative` and `category`.
Categorical metrics use null numeric fields, `units: "category"`, null `qualitative`, and an allowed
string in `category`. A prediction that cannot be made is omitted, counted as missing by the
evaluator, and explained in the calculation note. `source_artifact` is a normalized relative path to
an existing file under `output/`; fragments such as `#section` are forbidden.

## 5. Registered scoring dimensions

The evaluator is human-owned and frozen before scoring. It reports:

1. **Contract and completion:** required metrics present, units valid, artifacts executable or
   inspectable, and failures retained.
2. **Point accuracy:** absolute log error `abs(log(prediction / observation))` for ratio-scale
   positive quantities, with signed relative error shown for interpretation. Absolute plate
   temperatures use signed and absolute error in degrees Celsius; ratios of Celsius temperatures
   are meaningless because the zero is arbitrary.
3. **Uncertainty calibration:** weighted interval score from P10/P50/P90.
4. **Counts and zero events:** an interval-aware count score and `log10(count + 1)` error; never a
   relative error with a zero denominator.
5. **Qualitative gates:** allowed task-specific categories, including physical sufficiency and
   phase/ranking judgments.
6. **Process:** infrastructure-valid completion rate, wall time, and structural trace/artifact
   validity. Native token/usage fields remain in raw events and are tabulated without pretending the
   providers expose identical accounting. Substantive artifacts follow the blinded item-level review
   in `protocol/ARTIFACT_REVIEW.md`. Dollar cost is shown only if natively reported, never imputed
   from a subscription.

NSTF radiation is scored only against the experimentally supported categorical statement that
radiation dominates. The source does not provide a defensible whole-system numeric radiative
fraction: its matte/reflective gauges required recalibration and the reported face distribution is
not a radiation-versus-convection percentage. A model may estimate a fraction in its note, but that
number is not a registered metric. The supplied-duty ablation's duty value is an input and is excluded
from prediction-quality scoring. TRISO Kr-85 and Cs-137 are assessed on a log scale; Sr and Ag are
not scored. Their point errors and weighted interval scores are computed after the natural-log
transform, so multiplicative miss and calibration have the same geometry. Release predictions must
be strictly greater than zero and at most one. A model that
would otherwise report exact zero must state a positive numerical or detection floor and use it in
all four numeric fields; exact zero is schema-noncompliant because logarithmic error is undefined.

ANL-ART-47 Table 35's accident values are averages over its reported peak window, not instantaneous
maxima. The scorer uses those peak-window averages as comparators for the task's values at the
registered 84.85 h endpoint and labels that approximation explicitly. It does not call the Table 35
numbers maxima.

Table 32's `Riser duct wall` value is a generic/aggregate quantity, not an identified Riser 7
mid-plane hot-face point. The task may calculate that local temperature, but it is excluded from
registered point scoring rather than compared to a non-equivalent measurement.

The cold and warm baseline repeats in Tables 31-32 were not controlled zero-wind experiments;
outdoor temperature, wind, and the building pressure footprint covary. Numeric weather endpoints may
be plotted as contextual observations but are not registered point targets. Only the source-supported
direction that colder outdoor conditions increase natural-circulation flow is scored.

TRISO failure evidence is not statistically independent across every output column. For A2 and B,
the published failure counts and onset times are postcalculation assumptions inferred from Kr release;
the A1 and C2 zero-failure conclusions are likewise threshold-inferred from Kr. C1's count is
described as observed, but its exact onset times were imposed for postcalculation. Count, onset, and
Kr scores must be shown as one dependent evidence family, never described as three independent
confirmations.
For scorer interpretation, onset time is measured from the beginning of the selected onset phase:
A2's approximately 50 h cumulative 1800 C onset is about 24.5 h into its second/final 1800 C hold;
B's 119 h onset is relative to its final 300 h hold; and C1's 49 h onset is relative to its 1600 C
hold. These held-out interpretations are not mounted into agent runs.

The 873 MPa / `m = 8.02` SiC strength pair is an imposed benchmark prior based on German standard
calculations, directly analogous to the K3/P4 benchmark cases. HFR-K6 is not one of Table 9.14's
cases 9-13. Applying that pair to K6 is an explicit extrapolation and must increase the uncertainty
assigned to Case B rather than being presented as K6 characterization data.

Results remain task-level. A narrative overall winner is permitted only if the same system is
better on the preregistered accuracy, calibration, completion, and artifact dimensions without a
material counterexample. Otherwise the registered conclusion is mixed.

## 6. Blinding, exclusions, and freeze procedure

### Blindness checks

The primary NSTF pack must not contain a scaled thermal-duty mapping or held-out measurement. The
pack builder must fail if any assembled blind file contains these deny-list patterns as complete
numeric tokens (so, for example, `51.7` does not match the unrelated dimension `51.75`): `26.16`,
`56.07`, `56.12`, `54.49`, `51.7`, `48.6`, `65% efficiency`, or `68% efficiency`. It must also
fail if paths named
`refs`, `sources`, `protocol`, `measurement`, `score`, or `runs` are mounted.

The TRISO pack must not contain measured failure counts, measured release fractions, or the held-out
results file. The only one-particle values permitted are mathematical population fractions derived
from the supplied particle counts; they must not be described as observations.

### Exclusions

- Protocol v1 is excluded because its first scheduled process reached a defective finalizer. Its
  partial attempt is preserved and no v1 output contributes to a score.
- Protocol v2 is excluded in full. Its scored Claude command retained effective UID 0 but omitted
  the truthful sandbox marker, so all Claude first attempts and registered retries exited before a
  model event. Independently, its task/workspace ledger sort inherited the host locale, producing
  ledger-byte hashes that disagreed with the bytewise frozen pack hashes even though the task file
  bytes were identical. These are runner-integrity failures, not model results. No v2 attempt is
  scored, reviewed, or merged with v4.
- Protocol v3 is excluded in full after an unattended package upgrade changed the frozen host
  environment during sequence 8. Sequence 9 then failed closed before metadata creation or model
  invocation. Because the completed sequence-8 attempt cannot be certified for its full duration
  or replaced under the frozen retry rule, no v3 attempt is scored, reviewed, or merged with v4.
  The exact timeline, hashes, and inspection boundary are preserved in
  `results/excluded/v3-environment-drift/EXCLUSION.md`.
- HTTR is excluded from the leaderboard because its earlier prompt prescribed much of the method
  and leaked the expected qualitative trajectory. Existing artifacts may appear only in a labeled
  post-hoc audit sidebar.
- Old runs against the incorrect TRISO equation are evidence of the benchmark audit, not model
  scores.
- No new score is computed from the old NSTF comparison between a measured outlet temperature and
  an analytically predicted buoyancy-neutral threshold; those are different quantities.
- Run014 observed the rise through peak power but was concluded after the peak condition. The new
  task therefore asks about bounded response **through peak**, not a supposedly observed post-peak
  cooldown.

Version 4 preserves the v3 scientific task, prompt, held-out measurement, and evaluator bytes. It
changes only runner lifecycle integrity and protocol metadata, freezes the patched host with
automatic package transactions disabled, adds pre/post environment proof plus safe schedule
resumption, and restarts all four primary cells from replicate 1 under a new tag and schedule.

### Freeze

After all preflight tests pass and before the first scored run:

1. assemble each agent-visible pack exactly as specified above;
2. run `protocol/validate_task_packs.sh` plus the runner's hidden-canary tests;
3. compute SHA-256 for every pack file, the task prompt, evaluator files, CLI binaries/version
   output, proxy policy, and run-image digest;
4. write every manifest with deterministic bytewise path collation and without timestamps in
   hash-covered content;
5. commit and tag `benchmark-2026-07-12-v4`;
6. record the commit, tag, manifest hash, schedule, and preflight artifacts in the run ledger.

Any scientific, scoring, prompt, or runner-policy change after the tag requires a new protocol version and a complete
rerun of affected cells. Editorial changes that do not affect evidence may be made later and must be
identified separately.
