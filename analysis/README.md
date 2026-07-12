# Results harvester

The harvester verifies copied raw run directories before producing any evaluator input. It checks
the fixed artifact ledger, exact input/workspace file sets and hashes, rejects symlinks, reconciles
the run ID across directory/metadata/manifest records, and enforces the preregistered one-retry rule.

Run it only on the clean v4 raw-results directory. The excluded v1, v2, and v3 campaigns must remain in
separate `excluded/` trees and are explicitly rejected as a harvest root or child.

For V4, this is an internal finalization workflow over private verified raw evidence. Complete raw
attempts are not released because the frozen sandbox could expose host and provider secrets. Public
Any selected results are byte-reproduced internally and commitment-backed, but the public bundle
alone is not sufficient for independent end-to-end harvesting or score recomputation. The actual
V4 operator-incident path selects no score dataset and publishes campaign accounting only.

```bash
uv run python -m analysis.harvest \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root results/schedules/v4 \
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

Before publishing the next registered schedule, create a content-free gate attestation. The gate
independently re-harvests the immutable raw tree, authenticates the v4 protocol and evaluation
ledger, and requires every present stage schedule to be closed. It fails unless the selected dataset
has every exact registered replicate, no missing final outcome, and no infrastructure-failed final
outcome. Completed versus non-completed system outcomes are deliberately omitted because completion
is not an infrastructure gate. The status-bearing harvester artifacts are committed with HMAC-SHA256
under a fresh 32-byte key so their low-entropy fields cannot be brute-forced between stages. Keep the
key private until every registered stage is closed, then publish it with the final results.
After a closed extension the gate selects n5 when it is eligible, and falls back to the still-valid
n3 primary dataset only if the extension has an infrastructure-ineligible final outcome; Stage 3 is
ordered after Stage 2 but is not conditionally cancelled by such an extension failure.

```bash
install -d -m 700 /private/gate-keys
openssl rand -out /private/gate-keys/core-n3.key 32
chmod 600 /private/gate-keys/core-n3.key

uv run python -m analysis.gate_eligibility \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root results/schedules/v4 \
  --frozen-manifest protocol/frozen_manifest.sha256 \
  --commitment-key /private/gate-keys/core-n3.key \
  --dataset n3 \
  --output results/gates/core-n3.json
```

### Verifying disclosed gate keys after the campaign

After every registered stage has closed, publish the previously private gate keys in one strict
JSON document. Each attestation path is a canonical POSIX path relative to the public repository
root; each key is exactly 32 bytes encoded as 64 lowercase hexadecimal characters. Unknown fields,
duplicate paths, absolute paths, traversal components, non-JSON attestation paths, uppercase hex,
and keys of any other length are rejected.

```json
{
  "schema_version": "1.0",
  "gates": [
    {
      "attestation_path": "results/gates/core-n3.json",
      "commitment_key_hex": "<replace with exactly 64 lowercase hex characters>"
    },
    {
      "attestation_path": "results/gates/core-extend-n5.json",
      "commitment_key_hex": "<replace with exactly 64 lowercase hex characters>"
    }
  ]
}
```

Verify the disclosure against the final public raw tree and final schedule directory:

```bash
uv run python -m analysis.verify_gate_disclosure \
  --repository-root . \
  --disclosure results/gates/disclosed-keys.json \
  --runs-root results/raw \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root results/schedules/v4 \
  --frozen-manifest protocol/frozen_manifest.sha256
```

For each disclosure entry, the verifier reads the committed attestation's `closed_stages`, checks
that they are a registered protocol prefix, and creates an isolated temporary snapshot containing
only those stages' raw attempts and frozen schedule artifacts. It then calls the same
`analysis.gate_eligibility.build_attestation` implementation used to make the commitment. Success
requires both the reconstructed Pydantic model and its canonical UTF-8 bytes (including the final
newline) to equal the committed file exactly. The JSON report printed to stdout contains hashes of
the verified attestation and disclosed key, but never prints the key itself.

### Commitments around the blinded review

The final campaign has two additional ordering commitments. After the gate-selected datasets have
been evaluated, hash the exact `scores.jsonl` and `summary.json` bytes and commit that checksum
ledger **before** preparing or opening the identity-blind review packets. Do not commit or inspect
the scores yet. This establishes that automatic scoring was frozen before substantive artifact
judgments.

After every neutral row in `review.csv` has been completed, hash and commit those exact CSV bytes
**before** opening the sealed label mapping or running `blind_review finalize`. The finalized public
bundle must contain a byte-identical `completed-review.csv`, so its public provenance can be checked
against the earlier pre-unsealing commitment. Preserve LF line endings throughout.

These checksum commits reveal neither automatic scores nor system identities. They establish an
auditable sequence:

```text
closed campaign -> frozen evaluator bytes -> blinded judgments -> unsealed mapping -> publication
```

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
  --schedules-root results/schedules/v4 \
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
  work contains no applicable scripts. Submitted scripts are not executed in this campaign. When a
  script is applicable, use `partial` or `fail` from the inert cited-artifact evidence and disclose
  that the script was not run.
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
  --schedules-root results/schedules/v4 \
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
