# Results harvester

The harvester verifies copied raw run directories before producing any evaluator input. It checks
the fixed artifact ledger, exact input/workspace file sets and hashes, rejects symlinks, reconciles
the run ID across directory/metadata/manifest records, and enforces the preregistered one-retry rule.

Run it only on the clean v2 raw-results directory. The excluded v1 partial attempt must remain in a
separate `excluded/` tree and is explicitly rejected as a harvest root or child.

```bash
uv run python -m analysis.harvest \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root results/schedules/v2 \
  --output-dir results/harvested
```

The command verifies each present stage schedule and checksum against the frozen matrix, shuffle
seed, launch order, and run chronology. A missing schedule for an unlaunched later stage is allowed;
a launched stage without its schedule is not. Each stage requires a portable `*.tsv.sha256`;
an archived `*.tsv.vps.sha256` sidecar is also verified against the exact frozen VPS pathname when
present. A regular `README.md` may accompany the schedules as provenance. The command writes
`attempts.csv`, `eligibility.json`,
`eligibility.csv`, `integrity.jsonl`, `schedule_integrity.jsonl`, and gated `manifests.jsonl` /
`predictions.jsonl` pairs under `n3/`, `n5/`, and `ablation/`. An
ineligible dataset is represented by empty JSONL files so a partial comparison cannot be scored by
accident. Physical infrastructure failures and their retry remain visible in the eligible dataset;
eligibility counts the final outcome once per scheduled replicate.

## Identity-blind artifact review

After automatic scoring has been frozen, prepare the preregistered qualitative review directly from
the complete immutable raw campaign. The tool does not trust caller-selected or gated manifest
files. It verifies every raw attempt, the retry rules, frozen matrix, every present schedule and
checksum, launch order, chronology, and a complete launch prefix for each present stage. Thus the
same command supports a completed n3-only campaign, n3 plus n5, or all three registered stages.

```bash
uv run python -m analysis.blind_review prepare \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --schedules-root results/schedules/v2 \
  --ledger protocol/evaluation_ledger.json \
  --rubric-source protocol/ARTIFACT_REVIEW.md \
  --review-bundle /public-review-area/review-bundle \
  --sealed-mapping /separate-private-area/review-mapping.json
```

Every infrastructure-valid physical attempt is included: completions, agent failures, refusals,
and fallback-contaminated attempts. Provider and runner failures are excluded. Each neutral packet
contains two explicitly separated byte-identical trees: verified frozen inputs under
`task-context/` and submitted files under `submitted-output/`. A submitted
`output/predictions.json` is legitimate work product and remains visible; held-out measurements,
automatic evaluator scores, raw traces, proxy logs, run status, identity, and timestamps do not.
`packet.json` binds the task variant, benchmark version, task-pack hash, runner-environment hash,
frozen rubric hash, and every copied file hash.

Packet labels and review order use the operating system's cryptographic random source. Before any
destination is created, output paths and the exact source-byte snapshots that will be copied are
scanned for the run ID, system name, requested model, and served-model identifiers. A match fails
closed; the tool never redacts or mutates an artifact. Copied bytes and hashes are rechecked.

Preparation atomically publishes one new review-bundle directory containing `packets/`, the blank
`review.csv`, the exact frozen rubric, reviewer instructions, and an identity-neutral bundle
manifest. The sealed mode-`0600` mapping must be outside the entire parent directory of the review
bundle—not merely outside `packets/`. Existing or symlink destinations are refused. Keep that
mapping unopened and unpublished until all blinded judgments have been completed and frozen.

Fill every row with `pass`, `partial`, `fail`, or `not_applicable` and a short rationale. Two rubric
items need especially careful semantics:

- Item 6 can pass with `No applicable scripts: Cited artifacts verified: ...` when the submitted
  work contains no applicable scripts. When a script is applicable, a pass requires the reviewer
  to actually run it with an offline sandbox command in an environment whose regenerated manifest
  matches that packet's `runner_image_sha256`, recording the command, that exact manifest hash, and
  result. The packet tool does not execute scripts.
- Item 8 must be `not_applicable` because traces are absent unless the submitted artifact itself
  records an access attempt. Artifact-only review can never pass this item. When such evidence
  exists, use `partial` or `fail` with a `Submitted artifact evidence:` rationale. Sandbox and proxy
  enforcement are reported separately; they are not silently converted into an artifact-review
  pass.

Finalize only after the review is complete:

```bash
uv run python -m analysis.blind_review finalize \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --schedules-root results/schedules/v2 \
  --ledger protocol/evaluation_ledger.json \
  --rubric-source protocol/ARTIFACT_REVIEW.md \
  --review-bundle /public-review-area/review-bundle \
  --sealed-mapping /separate-private-area/review-mapping.json \
  --public-bundle results/blind-review/public
```

`finalize` snapshots and hashes the same completed CSV bytes it parses, re-verifies the entire raw
campaign and packet file set, and then atomically publishes a new public bundle. That bundle includes
the completed CSV, exact frozen rubric, deterministic item-level judgments, the now-unsealed
label-to-run mapping, and public provenance binding the completed-review hash, sealed-mapping hash,
ledger, matrix, every schedule/checksum, rubric, packet, runner-environment hash, and per-run
integrity record. The provenance lists every physical campaign attempt, including excluded
infrastructure failures and whether each attempt entered the review, so selection can be audited.
The rubric is never reduced to an overall leaderboard score.

This is not a claim of perfect reviewer blinding. Exact identifier strings are blocked, but the
submitted artifacts are otherwise copied byte-for-byte, so prose style, formatting, tool
conventions, or coding style can still reveal or suggest which system produced them. A sole
reviewer also provides no independent adjudication.
