# V4 finalization runbook

This runbook closes V4 without collapsing its inspection boundaries. It uses the public,
content-blind operators from a clean detached worktree and the immutable cumulative snapshot made
by `V4_TRANSITION_RUNBOOK.md`. It never changes `runner/`, `protocol/`, a frozen schedule, or a raw
attempt.

The three phases are exact:

```text
Phase 1 — sealed identities and sealed payloads
  terminal service -> final archive/import -> gate-key disclosure verification
  -> fresh harvest/evaluation -> public evaluation-byte commitment

Phase 2 — review unavailable after the public operator incident
  verify that no neutral bundle or mapping exists -> fixed public unavailability record

Phase 3 — verified, committed accounting
  recheck evaluation bytes -> campaign-accounting export -> privacy/size checks
  -> exact allowlist commit -> site handoff
```

The final terminal archive does **not** unlock an event stream, prediction, submitted workspace, or
automatic score. The public operator-incident record disables neutral-packet preparation entirely,
so no sealed mapping exists to open. Phase 3 may publish only the gate-selected deterministic
evaluation (an explicit empty selection on the actual incident path), campaign accounting, and the
fixed artifact-review unavailability record. A shared-workspace agent is never treated as blind.

Run the shell blocks in one local Bash session. Do not translate them to zsh. Keep that session and
the finalization lock alive through all three phases. A stale lock or staging path is an incident to
inspect, not permission to delete it.

## 0. Acquire the lock and pin clean public code

Select only the last stage that was actually launched. This is the sole manual campaign selector.

```bash
set -euo pipefail
umask 077

REPO=/Users/charlesazam/eng-bench
PRIVATE=/Users/charlesazam/eng-bench-v4-private
VPS=167.233.53.154
TERMINAL_STAGE=${TERMINAL_STAGE:?set TERMINAL_STAGE to the last launched registered stage}

case "$TERMINAL_STAGE" in
  core-n3|core-extend-n5|nstf-duty-ablation-n3) ;;
  *)
    printf 'unregistered terminal stage: %s\n' "$TERMINAL_STAGE" >&2
    exit 64
    ;;
esac

TRANSITION_LOCK="$PRIVATE/transition.lock"
FINAL_LOCK="$TRANSITION_LOCK"
FINAL_PRIVATE="$PRIVATE/finalization"
FINALIZATION_TOOL_SHA256=bf139e789afacb4e670e12a63c5de2a8b86a74f5fd2286ed098a22d4e201ef47

test -d "$PRIVATE"
test ! -L "$PRIVATE"
test "$(stat -f '%Su:%Sg:%Lp' "$PRIVATE")" = "$(id -un):$(id -gn):700"
case "${V4_FINALIZATION_LOCK_ALREADY_HELD:-0}" in
  0)
    test ! -e "$FINAL_LOCK"
    test ! -L "$FINAL_LOCK"
    mkdir -m 700 "$FINAL_LOCK"
    ;;
  1)
    test -d "$FINAL_LOCK"
    test ! -L "$FINAL_LOCK"
    test -z "$(find "$FINAL_LOCK" -mindepth 1 -print -quit)"
    unset V4_FINALIZATION_LOCK_ALREADY_HELD
    ;;
  *)
    printf 'invalid V4_FINALIZATION_LOCK_ALREADY_HELD value\n' >&2
    exit 64
    ;;
esac

for directory in \
  "$FINAL_PRIVATE" \
  "$PRIVATE/public-worktrees" \
  "$PRIVATE/finalization-envs" \
  "$PRIVATE/finalization-receipts" \
  "$PRIVATE/neutral-review" \
  "$PRIVATE/sealed-review" \
  "$PRIVATE/site-data-handoff"
do
  test ! -L "$directory"
  install -d -m 700 "$directory"
  test -d "$directory"
  test ! -L "$directory"
  test "$(stat -f '%Su:%Sg:%Lp' "$directory")" = \
    "$(id -un):$(id -gn):700"
done

EMPTY_GIT_HOOKS="$FINAL_PRIVATE/empty-git-hooks"
test ! -L "$EMPTY_GIT_HOOKS"
install -d -m 700 "$EMPTY_GIT_HOOKS"
test -z "$(find "$EMPTY_GIT_HOOKS" -mindepth 1 -print -quit)"
test -z "$(git -C "$REPO" ls-files \
  | awk -F/ '$NF == ".gitattributes" {print; exit}')"
INFO_ATTRIBUTES="$REPO/.git/info/attributes"
if test -e "$INFO_ATTRIBUTES" || test -L "$INFO_ATTRIBUTES"; then
  test -f "$INFO_ATTRIBUTES"
  test ! -L "$INFO_ATTRIBUTES"
  test ! -s "$INFO_ATTRIBUTES"
fi
FILTER_CONFIG="$FINAL_PRIVATE/git-filter-config.txt"
test ! -e "$FILTER_CONFIG"
test ! -L "$FILTER_CONFIG"
set +e
git -C "$REPO" config --show-origin --get-regexp '^filter\.' > "$FILTER_CONFIG"
filter_config_status=$?
set -e
test "$filter_config_status" = 1
test ! -s "$FILTER_CONFIG"
chmod 400 "$FILTER_CONFIG"
export GIT_CONFIG_COUNT=3
export GIT_CONFIG_KEY_0=core.hooksPath
export GIT_CONFIG_VALUE_0="$EMPTY_GIT_HOOKS"
export GIT_CONFIG_KEY_1=core.attributesFile
export GIT_CONFIG_VALUE_1=/dev/null
export GIT_CONFIG_KEY_2=commit.gpgSign
export GIT_CONFIG_VALUE_2=false

cd "$REPO"
test "$(git branch --show-current)" = main
git fetch origin main
PUBLIC_BASE=$(git rev-parse origin/main)
FINAL_PUBLIC_BASE="$PUBLIC_BASE"
test "$(git rev-parse HEAD)" = "$PUBLIC_BASE"
git diff --quiet
git diff --cached --quiet

INITIAL_UNTRACKED0="$FINAL_PRIVATE/initial-untracked-$PUBLIC_BASE.paths0"
BASELINE_IGNORED0="$FINAL_PRIVATE/baseline-ignored-$PUBLIC_BASE.paths0"
for fresh_path in "$INITIAL_UNTRACKED0" "$BASELINE_IGNORED0"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
git ls-files --others --exclude-standard -z \
  | LC_ALL=C sort -zu > "$INITIAL_UNTRACKED0"
while IFS= read -r -d '' relative; do
  case "$relative" in
    results/raw/*|results/raw-ledgers/*) ;;
    *)
      printf 'unexpected pre-finalization untracked path: %s\n' "$relative" >&2
      exit 65
      ;;
  esac
done < "$INITIAL_UNTRACKED0"
git ls-files --others --ignored --exclude-standard -z \
  | while IFS= read -r -d '' relative; do
      case "$relative" in
        results/raw/*) ;;
        *) printf '%s\0' "$relative" ;;
      esac
    done \
  | LC_ALL=C sort -zu > "$BASELINE_IGNORED0"
for imported_root in "$REPO/results/raw" "$REPO/results/raw-ledgers"; do
  if test -e "$imported_root" || test -L "$imported_root"; then
    test -d "$imported_root"
    test ! -L "$imported_root"
    test -z "$(find "$imported_root" -type l -print -quit)"
    test -z "$(find "$imported_root" ! -type d ! -type f -print -quit)"
  fi
done

FINAL_PINNED="$PRIVATE/public-worktrees/finalization-$PUBLIC_BASE"
FINAL_ENV="$PRIVATE/finalization-envs/$PUBLIC_BASE"
for fresh_path in "$FINAL_PINNED" "$FINAL_ENV"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
git worktree add --detach "$FINAL_PINNED" "$PUBLIC_BASE"
test "$(git -C "$FINAL_PINNED" rev-parse HEAD)" = "$PUBLIC_BASE"
git -C "$FINAL_PINNED" diff --quiet
git -C "$FINAL_PINNED" diff --cached --quiet
test -z "$(git -C "$FINAL_PINNED" status --porcelain --untracked-files=all)"
test "$(shasum -a 256 "$FINAL_PINNED/operations/v4_finalization.py" | cut -d ' ' -f1)" = \
  "$FINALIZATION_TOOL_SHA256"

env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
  uv run --frozen --directory "$FINAL_PINNED" \
  python -m operations.v4_finalization --help >/dev/null
```

Do not remove `FINAL_LOCK` on a failed path. Its presence forces the next operator to reconcile the
public base, staging directories, service receipt, and immutable snapshot before resuming.

## 1. Phase 1: close and import the terminal stage without inspecting it

First distinguish a fresh terminal stage from a stage already archived by an interstage transition.
The latter occurs when the registered time limit stops after a public gate. Never rerun an import
merely because finalization has started.

```bash
SNAP="$PRIVATE/snapshots/$TERMINAL_STAGE"
TERMINAL_LEDGER="$REPO/results/raw-ledgers/v4-$TERMINAL_STAGE.tree.sha256"
INCOMING="$PRIVATE/incoming/v4-$TERMINAL_STAGE"

terminal_state_count=0
for expected in "$SNAP" "$TERMINAL_LEDGER" "$INCOMING"; do
  if test -e "$expected" || test -L "$expected"; then
    terminal_state_count=$((terminal_state_count + 1))
  fi
done
case "$terminal_state_count" in
  0) TERMINAL_IMPORT_STATE=fresh ;;
  3) TERMINAL_IMPORT_STATE=already-imported ;;
  *)
    printf 'partial terminal import state; preserve it for incident review\n' >&2
    exit 65
    ;;
esac
```

When `TERMINAL_IMPORT_STATE=fresh`, keep `FINAL_LOCK` held and execute sections 0 through 3 of
`operations/V4_TRANSITION_RUNBOOK.md` with `STAGE="$TERMINAL_STAGE"`. Those sections are the sole
terminal-service/archive/import procedure. Do not execute its interstage sections 4 through 7. In
particular:

```bash
export V4_TRANSITION_LOCK_ALREADY_HELD=1
```

After transition section 0 has pinned its `PUBLIC_BASE` but before section 1 performs any service,
archive, or import action, run `test "$PUBLIC_BASE" = "$FINAL_PUBLIC_BASE"`. After section 3
returns, leave `V4_TRANSITION_LOCK_ALREADY_HELD` set; the resume block below verifies and unsets it
in the same shell.

- the exact mapped service and retention service must be loaded and terminal-successful;
- the archive operator must take the runner lock and verify all registered retries, schedules,
  ledgers, tree types, and pre/post environment evidence;
- transfer exactly the four archive files and use the public importer;
- create the non-writable cumulative snapshot; and
- stop the exact retention service only after the import and snapshot succeed.

An infrastructure-failed final scheduled replicate can still be terminally archived. It does not
become eligible merely because the archive succeeded. Do not open anything to diagnose eligibility.
When `TERMINAL_IMPORT_STATE=already-imported`, skip the transition sections entirely.

Resume this runbook only after the transition procedure has returned to the same local shell:

```bash
if test "$TERMINAL_IMPORT_STATE" = fresh; then
  test "${V4_TRANSITION_LOCK_ALREADY_HELD:-0}" = 1
  unset V4_TRANSITION_LOCK_ALREADY_HELD
fi
test "$PUBLIC_BASE" = "$FINAL_PUBLIC_BASE"
PUBLIC_BASE="$FINAL_PUBLIC_BASE"
SNAP="$PRIVATE/snapshots/$TERMINAL_STAGE"
test -d "$SNAP"
test ! -L "$SNAP"
test -d "$SNAP/raw"
test ! -L "$SNAP/raw"
test -d "$SNAP/schedules"
test ! -L "$SNAP/schedules"
test -z "$(find "$SNAP" -type l -print -quit)"
test -z "$(find "$SNAP" ! -type d ! -type f -print -quit)"
test -z "$(find "$SNAP" -type f -perm -222 -print -quit)"
case "$TERMINAL_STAGE" in
  core-n3) IMPORTED_STAGES=(core-n3) ;;
  core-extend-n5) IMPORTED_STAGES=(core-n3 core-extend-n5) ;;
  nstf-duty-ablation-n3)
    IMPORTED_STAGES=(core-n3 core-extend-n5 nstf-duty-ablation-n3)
    ;;
esac
for imported_stage in "${IMPORTED_STAGES[@]}"; do
  imported_ledger="$REPO/results/raw-ledgers/v4-$imported_stage.tree.sha256"
  imported_archive="$PRIVATE/incoming/v4-$imported_stage"
  test -f "$imported_ledger"
  test ! -L "$imported_ledger"
  test -d "$imported_archive"
  test ! -L "$imported_archive"
  IMPORT_VERIFY_STDOUT="$PRIVATE/finalization-receipts/import-verify-$imported_stage-$PUBLIC_BASE.stdout"
  IMPORT_VERIFY_STDERR="$PRIVATE/finalization-receipts/import-verify-$imported_stage-$PUBLIC_BASE.stderr"
  for fresh_path in "$IMPORT_VERIFY_STDOUT" "$IMPORT_VERIFY_STDERR"; do
    test ! -e "$fresh_path"
    test ! -L "$fresh_path"
  done
  (
    cd "$FINAL_PINNED"
    env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen --project operations \
      python -m operations.v4_stage_archive verify-import \
      --stage "$imported_stage" \
      --archive-directory "$imported_archive" \
      --repository-root "$REPO"
  ) > "$IMPORT_VERIFY_STDOUT" 2> "$IMPORT_VERIFY_STDERR"
  chmod 400 "$IMPORT_VERIFY_STDOUT" "$IMPORT_VERIFY_STDERR"
done

expected_raw_ledger_names=$(
  for imported_stage in "${IMPORTED_STAGES[@]}"; do
    printf 'v4-%s.tree.sha256\n' "$imported_stage"
  done | LC_ALL=C sort
)
actual_raw_ledger_names=$(find "$REPO/results/raw-ledgers" \
  -mindepth 1 -maxdepth 1 -print \
  | sed 's#^.*/##' | LC_ALL=C sort)
test "$actual_raw_ledger_names" = "$expected_raw_ledger_names"
for imported_stage in "${IMPORTED_STAGES[@]}"; do
  imported_ledger="$REPO/results/raw-ledgers/v4-$imported_stage.tree.sha256"
  test -f "$imported_ledger"
  test ! -L "$imported_ledger"
  test "$(stat -f '%Lp' "$imported_ledger")" = 444
done

SNAP_RAW_DIFF="$PRIVATE/finalization-receipts/snapshot-raw-$TERMINAL_STAGE-$PUBLIC_BASE.diff"
SNAP_SCHEDULE_DIFF="$PRIVATE/finalization-receipts/snapshot-schedules-$TERMINAL_STAGE-$PUBLIC_BASE.diff"
for fresh_path in "$SNAP_RAW_DIFF" "$SNAP_SCHEDULE_DIFF"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
diff -qr "$REPO/results/raw" "$SNAP/raw" > "$SNAP_RAW_DIFF" 2>&1
diff -qr "$REPO/results/schedules/v4" "$SNAP/schedules" \
  > "$SNAP_SCHEDULE_DIFF" 2>&1
chmod 400 "$SNAP_RAW_DIFF" "$SNAP_SCHEDULE_DIFF"

git fetch origin main
test "$(git rev-parse origin/main)" = "$PUBLIC_BASE"
test "$(git rev-parse HEAD)" = "$PUBLIC_BASE"
git diff --quiet
git diff --cached --quiet
test "$(git -C "$FINAL_PINNED" rev-parse HEAD)" = "$PUBLIC_BASE"
test -z "$(git -C "$FINAL_PINNED" status --porcelain --untracked-files=all)"
```

At this point the archive is evidence of bytes and lifecycle only. Payload inspection remains
forbidden.

## 2. Disclose any committed gates and run the independent full verifier

Gate disclosure is conditional. A campaign that stopped with no eligible core has no committed core
gate to disclose. A committed core gate with no extension gate uses explicit `--core-only`. A
committed extension gate uses its distinct extension key. Never disclose a key for an unattested or
failed gate attempt.

```bash
DISCLOSURE_REL=results/gates/disclosed-keys.json
DISCLOSURE="$REPO/$DISCLOSURE_REL"
CORE_GATE_REL=results/gates/core-n3.json
EXTENSION_GATE_REL=results/gates/core-extend-n5.json
CORE_GATE="$REPO/$CORE_GATE_REL"
EXTENSION_GATE="$REPO/$EXTENSION_GATE_REL"
CORE_KEY="$PRIVATE/gate-keys/core-n3.key"
EXTENSION_KEY="$PRIVATE/gate-keys/core-extend-n5.key"
GATE_VERIFY_RECEIPT="$PRIVATE/finalization-receipts/gate-disclosure-$PUBLIC_BASE.json"
GATE_CREATE_RECEIPT="$PRIVATE/finalization-receipts/gate-disclosure-create-$PUBLIC_BASE.json"

for fresh_path in "$DISCLOSURE" "$GATE_VERIFY_RECEIPT" "$GATE_CREATE_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done

DISCLOSURE_MODE=none
CORE_GATE_AT_HEAD=false
EXTENSION_GATE_AT_HEAD=false
if git cat-file -e "$PUBLIC_BASE:$CORE_GATE_REL" 2>/dev/null; then
  CORE_GATE_AT_HEAD=true
fi
if git cat-file -e "$PUBLIC_BASE:$EXTENSION_GATE_REL" 2>/dev/null; then
  EXTENSION_GATE_AT_HEAD=true
fi
if test "$EXTENSION_GATE_AT_HEAD" = true; then
  test -f "$CORE_GATE"
  test ! -L "$CORE_GATE"
  test -f "$CORE_KEY"
  test ! -L "$CORE_KEY"
  test -f "$EXTENSION_KEY"
  test ! -L "$EXTENSION_KEY"
  (
    cd "$FINAL_PINNED"
    env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen python -m operations.v4_finalization \
      create-gate-disclosure \
      --repository-root "$REPO" \
      --core-key "$CORE_KEY" \
      --extension-key "$EXTENSION_KEY" \
      --output "$DISCLOSURE"
  ) > "$GATE_CREATE_RECEIPT"
  DISCLOSURE_MODE=core-and-extension
elif test "$CORE_GATE_AT_HEAD" = true; then
  test ! -e "$EXTENSION_GATE"
  test ! -L "$EXTENSION_GATE"
  test -f "$CORE_KEY"
  test ! -L "$CORE_KEY"
  (
    cd "$FINAL_PINNED"
    env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen python -m operations.v4_finalization \
      create-gate-disclosure \
      --repository-root "$REPO" \
      --core-key "$CORE_KEY" \
      --core-only \
      --output "$DISCLOSURE"
  ) > "$GATE_CREATE_RECEIPT"
  DISCLOSURE_MODE=core-only
else
  test ! -e "$CORE_GATE"
  test ! -L "$CORE_GATE"
  test ! -e "$EXTENSION_GATE"
  test ! -L "$EXTENSION_GATE"
  test "$TERMINAL_STAGE" = core-n3
fi

case "$TERMINAL_STAGE:$DISCLOSURE_MODE" in
  core-n3:none|core-n3:core-only) ;;
  core-extend-n5:core-and-extension|nstf-duty-ablation-n3:core-and-extension) ;;
  *)
    printf 'terminal stage and disclosure mode are inconsistent\n' >&2
    exit 65
    ;;
esac

if test "$DISCLOSURE_MODE" != none; then
  test -f "$DISCLOSURE"
  test ! -L "$DISCLOSURE"
  test -s "$GATE_CREATE_RECEIPT"
  chmod 400 "$GATE_CREATE_RECEIPT"
  GATE_VERIFY_STDERR="$PRIVATE/finalization-receipts/gate-disclosure-$PUBLIC_BASE.stderr"
  test ! -e "$GATE_VERIFY_STDERR"
  test ! -L "$GATE_VERIFY_STDERR"
  (
    cd "$FINAL_PINNED"
    env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen python -m analysis.verify_gate_disclosure \
      --repository-root "$REPO" \
      --disclosure "$DISCLOSURE" \
      --runs-root "$SNAP/raw" \
      --matrix protocol/matrix.tsv \
      --ledger protocol/evaluation_ledger.json \
      --schedules-root "$SNAP/schedules" \
      --frozen-manifest protocol/frozen_manifest.sha256
  ) > "$GATE_VERIFY_RECEIPT" 2> "$GATE_VERIFY_STDERR"
  test -s "$GATE_VERIFY_RECEIPT"
  test ! -L "$GATE_VERIFY_RECEIPT"
  chmod 400 "$GATE_VERIFY_RECEIPT" "$GATE_VERIFY_STDERR"
fi
```

`create-gate-disclosure` verifies the exact committed gate bytes and key hashes. The separate
`verify_gate_disclosure` call reconstructs each stage-prefix snapshot from the final immutable raw
tree and recomputes the complete attestation. One is not a substitute for the other.

## 3. Fresh staged harvest and deterministic evaluation

The following commands mechanically parse payloads; the operator still must not open their inputs
or outputs. The selected datasets are derived only from the harvester's eligibility record. The
exact Python executable hash, Python version, OS/kernel/architecture, lockfile, evaluator manifest,
and public source commit are captured before evaluation and included in the public evaluation
commitment. The byte-for-byte recheck establishes repeatability in that recorded environment; it is
not a claim that platform `libm` produces identical last-bit JSON on every host.

- choose `n5` when eligible, otherwise `n3` when eligible;
- include `ablation` only when it is itself eligible and an eligible primary exists; and
- if no primary is eligible, evaluate nothing and create the explicit allow-empty commitment.

An infrastructure-ineligible extension may fall back to eligible `n3` and does not cancel an
already registered ablation. An eligible ablation with no eligible primary is a gate contradiction,
not a dataset to publish.

```bash
HARVEST="$REPO/results/harvested"
HARVEST_STAGE="$REPO/results/.harvested-stage-$PUBLIC_BASE"
EVALUATION="$REPO/results/evaluation"
EVALUATION_STAGE="$REPO/results/.evaluation-stage-$PUBLIC_BASE"
HARVEST_STDOUT="$PRIVATE/finalization-receipts/harvest-$PUBLIC_BASE.stdout"
HARVEST_STDERR="$PRIVATE/finalization-receipts/harvest-$PUBLIC_BASE.stderr"
for fresh_path in "$HARVEST" "$HARVEST_STAGE" "$EVALUATION" "$EVALUATION_STAGE"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
for fresh_path in "$HARVEST_STDOUT" "$HARVEST_STDERR"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done

(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m analysis.harvest \
    --runs-root "$SNAP/raw" \
    --matrix protocol/matrix.tsv \
    --ledger protocol/evaluation_ledger.json \
    --schedules-root "$SNAP/schedules" \
    --output-dir "$HARVEST_STAGE"
) > "$HARVEST_STDOUT" 2> "$HARVEST_STDERR"
chmod 400 "$HARVEST_STDOUT" "$HARVEST_STDERR"

expected_harvest_paths=$(printf '%s\n' \
  ablation/manifests.jsonl \
  ablation/predictions.jsonl \
  attempts.csv \
  eligibility.csv \
  eligibility.json \
  integrity.jsonl \
  n3/manifests.jsonl \
  n3/predictions.jsonl \
  n5/manifests.jsonl \
  n5/predictions.jsonl \
  schedule_integrity.jsonl | LC_ALL=C sort)
actual_harvest_paths=$(find "$HARVEST_STAGE" -type f -print \
  | sed "s#^$HARVEST_STAGE/##" | LC_ALL=C sort)
test "$actual_harvest_paths" = "$expected_harvest_paths"
test -z "$(find "$HARVEST_STAGE" -type l -print -quit)"
test -z "$(find "$HARVEST_STAGE" ! -type d ! -type f -print -quit)"
mv -n "$HARVEST_STAGE" "$HARVEST"
test -d "$HARVEST"
test ! -e "$HARVEST_STAGE"

jq -e '[.datasets[].dataset] | sort == ["ablation","n3","n5"]' \
  "$HARVEST/eligibility.json" >/dev/null
N3_ELIGIBLE=$(jq -r \
  '[.datasets[] | select(.dataset == "n3") | .eligible]
   | if length == 1 and (.[0] | type) == "boolean" then .[0]
     else error("invalid n3 eligibility record") end' \
  "$HARVEST/eligibility.json")
N5_ELIGIBLE=$(jq -r \
  '[.datasets[] | select(.dataset == "n5") | .eligible]
   | if length == 1 and (.[0] | type) == "boolean" then .[0]
     else error("invalid n5 eligibility record") end' \
  "$HARVEST/eligibility.json")
ABLATION_ELIGIBLE=$(jq -r \
  '[.datasets[] | select(.dataset == "ablation") | .eligible]
   | if length == 1 and (.[0] | type) == "boolean" then .[0]
     else error("invalid ablation eligibility record") end' \
  "$HARVEST/eligibility.json")

PRIMARY_DATASET=
if test "$N5_ELIGIBLE" = true; then
  PRIMARY_DATASET=n5
elif test "$N3_ELIGIBLE" = true; then
  PRIMARY_DATASET=n3
fi

SELECTED_DATASETS=()
if test -n "$PRIMARY_DATASET"; then
  SELECTED_DATASETS+=("$PRIMARY_DATASET")
  if test "$ABLATION_ELIGIBLE" = true; then
    SELECTED_DATASETS+=(ablation)
  fi
elif test "$ABLATION_ELIGIBLE" = true; then
  printf 'eligible ablation without an eligible primary\n' >&2
  exit 65
fi

EVALUATION_ENVIRONMENT="$REPO/results/evaluation-environment.json"
EVALUATION_ENVIRONMENT_RECEIPT="$PRIVATE/finalization-receipts/evaluation-environment-$PUBLIC_BASE.json"
for fresh_path in "$EVALUATION_ENVIRONMENT" "$EVALUATION_ENVIRONMENT_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    capture-evaluation-environment \
    --repository-root "$FINAL_PINNED" \
    --output "$EVALUATION_ENVIRONMENT"
) > "$EVALUATION_ENVIRONMENT_RECEIPT"
chmod 400 "$EVALUATION_ENVIRONMENT_RECEIPT"

if test "$DISCLOSURE_MODE" = none; then
  test -z "$PRIMARY_DATASET"
elif test "$DISCLOSURE_MODE" = core-only; then
  test "$N3_ELIGIBLE" = true
  test "$PRIMARY_DATASET" = n3
else
  test "$DISCLOSURE_MODE" = core-and-extension
  test "$N3_ELIGIBLE" = true
  test "$(jq -er '.dataset' "$EXTENSION_GATE")" = "$PRIMARY_DATASET"
fi

install -d -m 700 "$EVALUATION_STAGE"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  for dataset in "${SELECTED_DATASETS[@]}"; do
    EVALUATE_STDOUT="$PRIVATE/finalization-receipts/evaluate-$dataset-$PUBLIC_BASE.stdout"
    EVALUATE_STDERR="$PRIVATE/finalization-receipts/evaluate-$dataset-$PUBLIC_BASE.stderr"
    for fresh_path in "$EVALUATE_STDOUT" "$EVALUATE_STDERR"; do
      test ! -e "$fresh_path"
      test ! -L "$fresh_path"
    done
    (
      cd "$FINAL_PINNED"
      env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
        uv run --frozen eng-bench evaluate \
        --manifests "$HARVEST/$dataset/manifests.jsonl" \
        --predictions "$HARVEST/$dataset/predictions.jsonl" \
        --measurements measurements/held_out.jsonl \
        --ledger protocol/evaluation_ledger.json \
        --evaluator-manifest protocol/evaluator_manifest.sha256 \
        --evaluator-root "$FINAL_PINNED" \
        --artifact-root "$SNAP/raw" \
        --output-dir "$EVALUATION_STAGE/$dataset"
    ) > "$EVALUATE_STDOUT" 2> "$EVALUATE_STDERR"
    chmod 400 "$EVALUATE_STDOUT" "$EVALUATE_STDERR"
  done
fi
actual_evaluation_entries=$(find "$EVALUATION_STAGE" -mindepth 1 -maxdepth 1 \
  -type d -exec basename {} \; | LC_ALL=C sort)
expected_evaluation_entries=
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  expected_evaluation_entries=$(printf '%s\n' "${SELECTED_DATASETS[@]}" \
    | LC_ALL=C sort)
fi
test "$actual_evaluation_entries" = "$expected_evaluation_entries"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  for dataset in "${SELECTED_DATASETS[@]}"; do
    test "$(find "$EVALUATION_STAGE/$dataset" -mindepth 1 -maxdepth 1 -type f \
      -exec basename {} \; | LC_ALL=C sort)" = $'scores.jsonl\nsummary.json'
  done
fi
test -z "$(find "$EVALUATION_STAGE" -type l -print -quit)"
test -z "$(find "$EVALUATION_STAGE" ! -type d ! -type f -print -quit)"
mv -n "$EVALUATION_STAGE" "$EVALUATION"
test -d "$EVALUATION"
test ! -e "$EVALUATION_STAGE"

EVALUATION_ENVIRONMENT_AFTER="$FINAL_PRIVATE/evaluation-environment-after-$PUBLIC_BASE.json"
EVALUATION_ENVIRONMENT_AFTER_RECEIPT="$PRIVATE/finalization-receipts/evaluation-environment-after-$PUBLIC_BASE.json"
for fresh_path in \
  "$EVALUATION_ENVIRONMENT_AFTER" "$EVALUATION_ENVIRONMENT_AFTER_RECEIPT"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    capture-evaluation-environment \
    --repository-root "$FINAL_PINNED" \
    --output "$EVALUATION_ENVIRONMENT_AFTER"
) > "$EVALUATION_ENVIRONMENT_AFTER_RECEIPT"
cmp --silent "$EVALUATION_ENVIRONMENT" "$EVALUATION_ENVIRONMENT_AFTER"
chmod 400 "$EVALUATION_ENVIRONMENT_AFTER" "$EVALUATION_ENVIRONMENT_AFTER_RECEIPT"
```

## 4. Commit the evaluation-byte commitment alone

The commitment hashes bytes without parsing scores. It binds the exact eligibility source and only
the selected evaluation directories. The zero-score terminal case must use
`--allow-empty-selection`; an implicit empty `--dataset` list is rejected.

```bash
COMMITMENTS="$REPO/results/commitments"
install -d -m 755 "$COMMITMENTS"
EVALUATION_FREEZE_REL=results/commitments/v4-evaluation-freeze.json
EVALUATION_FREEZE="$REPO/$EVALUATION_FREEZE_REL"
EVALUATION_FREEZE_RECEIPT="$PRIVATE/finalization-receipts/evaluation-freeze-$PUBLIC_BASE.json"
for fresh_path in "$EVALUATION_FREEZE" "$EVALUATION_FREEZE_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done

evaluation_freeze_arguments=(
  freeze-evaluation
  --repository-root "$REPO"
  --evaluation-root "$EVALUATION"
  --execution-environment "$EVALUATION_ENVIRONMENT"
  --selection-source "$HARVEST/eligibility.json"
  --output "$EVALUATION_FREEZE"
)
if test "${#SELECTED_DATASETS[@]}" -eq 0; then
  evaluation_freeze_arguments+=(--allow-empty-selection)
else
  for dataset in "${SELECTED_DATASETS[@]}"; do
    evaluation_freeze_arguments+=(--dataset "$dataset")
  done
fi
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    "${evaluation_freeze_arguments[@]}"
) > "$EVALUATION_FREEZE_RECEIPT"
test -s "$EVALUATION_FREEZE_RECEIPT"
chmod 400 "$EVALUATION_FREEZE_RECEIPT"

cd "$REPO"
git fetch origin main
test "$(git rev-parse origin/main)" = "$PUBLIC_BASE"
test "$(git rev-parse HEAD)" = "$PUBLIC_BASE"
git diff --quiet
git diff --cached --quiet
evaluation_freeze_sha=$(shasum -a 256 "$EVALUATION_FREEZE" | cut -d ' ' -f1)
evaluation_environment_sha=$(shasum -a 256 "$EVALUATION_ENVIRONMENT" | cut -d ' ' -f1)
git add -- "$EVALUATION_FREEZE_REL" results/evaluation-environment.json
expected_evaluation_commit_paths=$(printf '%s\n' \
  "$EVALUATION_FREEZE_REL" results/evaluation-environment.json | LC_ALL=C sort)
test "$(git diff --cached --name-only | LC_ALL=C sort)" = \
  "$expected_evaluation_commit_paths"
git diff --cached --check
git commit --no-gpg-sign -m "Commit V4 evaluation bytes and execution environment"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = 2
test "$(git rev-parse HEAD^)" = "$PUBLIC_BASE"
test "$(git diff-tree --no-commit-id --name-only -r HEAD | LC_ALL=C sort)" = \
  "$expected_evaluation_commit_paths"
test "$(git ls-tree HEAD -- "$EVALUATION_FREEZE_REL" | awk '{print $1,$2}')" = \
  "100644 blob"
test "$(git ls-tree HEAD -- results/evaluation-environment.json \
  | awk '{print $1,$2}')" = "100644 blob"
test "$(git show "HEAD:$EVALUATION_FREEZE_REL" | shasum -a 256 \
  | cut -d ' ' -f1)" = "$evaluation_freeze_sha"
test "$(git show HEAD:results/evaluation-environment.json | shasum -a 256 \
  | cut -d ' ' -f1)" = "$evaluation_environment_sha"
git push origin main
git fetch origin main
EVALUATION_COMMIT=$(git rev-parse HEAD)
test "$EVALUATION_COMMIT" = "$(git rev-parse origin/main)"
test "$(git rev-parse "$EVALUATION_COMMIT^")" = "$PUBLIC_BASE"
```

The public evaluation commitment is necessary but does not unlock score inspection. Proceed only
to neutral preparation.

## 5. Phase 2: record that artifact review is unavailable

The public operator-environment incident was registered before any result inspection and explicitly
forbids running the unproven isolated-review harness on V4. Therefore no neutral packet, sealed
mapping, review CSV, or private preparation diagnostic is created. The later review sections remain
as fail-closed continuity documentation but are not executable for this campaign.

```bash
REVIEW_PARENT="$PRIVATE/neutral-review/$PUBLIC_BASE"
REVIEW_BUNDLE="$REVIEW_PARENT/bundle"
SEALED_MAPPING="$PRIVATE/sealed-review/$PUBLIC_BASE-mapping.json"
PREPARE_STDOUT="$PRIVATE/finalization-receipts/blind-prepare-$PUBLIC_BASE.stdout"
PREPARE_STDERR="$PRIVATE/finalization-receipts/blind-prepare-$PUBLIC_BASE.stderr"
REVIEW_MODE=reviewer-isolation-unavailable
test "$(git ls-tree "$EVALUATION_COMMIT" -- \
  operations/V4_OPERATOR_ENVIRONMENT_INCIDENT.md | awk '{print $1,$2}')" = \
  "100644 blob"
for fresh_path in \
  "$REVIEW_PARENT" "$REVIEW_BUNDLE" "$SEALED_MAPPING" \
  "$PREPARE_STDOUT" "$PREPARE_STDERR"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
```

Skip sections 5a through 8, create the fixed public unavailability record in section 10, and make no
artifact-quality claim.

## 5a. Commit the opaque sealed-mapping hash before review

This section applies only when `REVIEW_MODE=available`. It hashes the mode-`0600` mapping as opaque
bytes without parsing or printing it. Publishing this commitment before review prevents a later
identity reassignment that would still fit otherwise identical neutral packets.

```bash
test "$REVIEW_MODE" = available
MAPPING_FREEZE_REL=results/commitments/v4-sealed-mapping-freeze.json
MAPPING_FREEZE="$REPO/$MAPPING_FREEZE_REL"
MAPPING_FREEZE_RECEIPT="$PRIVATE/finalization-receipts/mapping-freeze-$PUBLIC_BASE.json"
for fresh_path in "$MAPPING_FREEZE" "$MAPPING_FREEZE_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization freeze-mapping \
    --sealed-mapping "$SEALED_MAPPING" \
    --output "$MAPPING_FREEZE"
) > "$MAPPING_FREEZE_RECEIPT"
test -s "$MAPPING_FREEZE_RECEIPT"
chmod 400 "$MAPPING_FREEZE_RECEIPT"

cd "$REPO"
git fetch origin main
test "$(git rev-parse origin/main)" = "$EVALUATION_COMMIT"
test "$(git rev-parse HEAD)" = "$EVALUATION_COMMIT"
git diff --quiet
git diff --cached --quiet
mapping_freeze_sha=$(shasum -a 256 "$MAPPING_FREEZE" | cut -d ' ' -f1)
git add -- "$MAPPING_FREEZE_REL"
test "$(git diff --cached --name-only)" = "$MAPPING_FREEZE_REL"
git diff --cached --check
git commit --no-gpg-sign -m "Commit V4 sealed mapping before blind review"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = 2
test "$(git rev-parse HEAD^)" = "$EVALUATION_COMMIT"
test "$(git diff-tree --no-commit-id --name-only -r HEAD)" = \
  "$MAPPING_FREEZE_REL"
test "$(git ls-tree HEAD -- "$MAPPING_FREEZE_REL" | awk '{print $1,$2}')" = \
  "100644 blob"
test "$(git show "HEAD:$MAPPING_FREEZE_REL" | shasum -a 256 \
  | cut -d ' ' -f1)" = "$mapping_freeze_sha"
git push origin main
git fetch origin main
MAPPING_COMMIT=$(git rev-parse HEAD)
test "$MAPPING_COMMIT" = "$(git rev-parse origin/main)"
test "$(git rev-parse "$MAPPING_COMMIT^")" = "$EVALUATION_COMMIT"
```

## 6. Complete the review without executing submitted code

This section applies only when `REVIEW_MODE=available`. Give the reviewer only
`REVIEW_BUNDLE`. Do not provide `SEALED_MAPPING`, raw attempts, event streams, proxy logs, automatic
scores, result summaries, status tables, schedules annotated with outcomes, or the article draft.

Follow `operations/V4_REVIEWER_PLAN.md` and the bundled instructions. Open every neutral packet,
verify cited files as inert bytes, and complete all eight rows per packet with concrete rationales.
The primary reviewer is OpenAI Codex under Charles Azam's authorization. A reviewer is eligible
only when the registered isolated-review probe has passed under the exact runtime used for V4: the
prompt is supplied on standard input, packet bytes are supplied through a canonical in-memory
payload, and no campaign, mapping, score, repository, shell, or host-filesystem path is mounted into
the reviewer. A normal Codex subagent shares this workspace and is **not** technically blind. If the
exact isolated runtime is unavailable or its synthetic adversarial probe fails, set
`REVIEW_MODE=reviewer-isolation-unavailable`, keep the mapping sealed, skip the remainder of this
section and sections 7–8, and create the fixed public record in section 10. Do not substitute a
shared-filesystem review.

Run the isolated primary pass once per neutral packet. After it has completed every row, snapshot
the exact primary `review.csv` before starting any second pass. The snapshot command validates the
whole neutral bundle, writes a fresh mode-`0400` file outside the bundle, and never prints review
content:

```bash
test "$REVIEW_MODE" = available
PRIMARY_REVIEW="$PRIVATE/neutral-review/$PUBLIC_BASE-primary-review.csv"
PRIMARY_REVIEW_RECEIPT="$PRIVATE/finalization-receipts/primary-review-$PUBLIC_BASE.json"
for fresh_path in "$PRIMARY_REVIEW" "$PRIMARY_REVIEW_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    snapshot-primary-review \
    --review-bundle "$REVIEW_BUNDLE" \
    --output "$PRIMARY_REVIEW"
) > "$PRIMARY_REVIEW_RECEIPT"
test "$(stat -f '%Lp' "$PRIMARY_REVIEW")" = 400
chmod 400 "$PRIMARY_REVIEW_RECEIPT"
```

If the registered isolated fresh-context consistency pass is available, run it only after this
snapshot and give it the same neutral per-packet material. The primary reviewer adjudicates any
proposed changes while both passes remain blind. Record whether the second pass and adjudication
actually occurred; the finalizer derives the changed-row count from the immutable primary snapshot
and final review bytes.

**No submitted script will be executed during this finalization.** The previously considered
offline runner is release-blocked and must not be used. For rubric item 6:

- `pass` is permitted only when no submitted script is applicable and the rationale begins exactly
  `No applicable scripts:` and includes `Cited artifacts verified:`;
- if a script is applicable, use `partial` or `fail` from the inert cited-artifact evidence and say
  explicitly that the script was not executed; and
- never claim an applicable-script pass, offline execution, runner-manifest execution proof, or
  equivalent substitute.

Item 8 can never pass from an artifact-only packet. Use `not_applicable` unless the submitted
artifact itself records an access attempt; any `partial` or `fail` rationale must begin exactly
`Submitted artifact evidence:`.

Do not continue until the primary and optional second pass are finished and the exact LF-only
`review.csv` is final. Do not open the sealed mapping to help resolve a judgment.

Before freezing the review, set the two literal booleans below from what actually occurred. The
typed generator binds this disclosure to the exact completed `review.csv`; it is later published
byte-for-byte. A planned pass is not an occurred pass.

```bash
SECOND_REVIEW_OCCURRED=${SECOND_REVIEW_OCCURRED:?set literal true or false}
ADJUDICATION_OCCURRED=${ADJUDICATION_OCCURRED:?set literal true or false}
case "$SECOND_REVIEW_OCCURRED:$ADJUDICATION_OCCURRED" in
  false:false|true:false|true:true) ;;
  *)
    printf 'invalid second-review/adjudication combination\n' >&2
    exit 64
    ;;
esac

REVIEW_DIFFERENCE="$PRIVATE/neutral-review/$PUBLIC_BASE-review-difference.json"
REVIEW_DIFFERENCE_RECEIPT="$PRIVATE/finalization-receipts/review-difference-$PUBLIC_BASE.json"
for fresh_path in "$REVIEW_DIFFERENCE" "$REVIEW_DIFFERENCE_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization compare-reviews \
    --review-bundle "$REVIEW_BUNDLE" \
    --primary-review "$PRIMARY_REVIEW" \
    --output "$REVIEW_DIFFERENCE"
) > "$REVIEW_DIFFERENCE_RECEIPT"
ROWS_CHANGED=$(jq -er \
  '.rows_changed | select(type == "number" and . >= 0 and floor == .)' \
  "$REVIEW_DIFFERENCE")
if test "$ROWS_CHANGED" -gt 0; then
  test "$SECOND_REVIEW_OCCURRED" = true
  test "$ADJUDICATION_OCCURRED" = true
else
  test "$ROWS_CHANGED" = 0
fi
chmod 400 "$REVIEW_DIFFERENCE" "$REVIEW_DIFFERENCE_RECEIPT"

REVIEW_DISCLOSURE_DRAFT="$PRIVATE/neutral-review/$PUBLIC_BASE-reviewer-disclosure-draft.json"
REVIEW_EDITORIAL_PRIVATE="$PRIVATE/neutral-review/$PUBLIC_BASE-artifact-review-editorial.json"
REVIEW_DISCLOSURE_RECEIPT="$PRIVATE/finalization-receipts/reviewer-disclosure-$PUBLIC_BASE.json"
for fresh_path in \
  "$REVIEW_DISCLOSURE_DRAFT" "$REVIEW_EDITORIAL_PRIVATE" \
  "$REVIEW_DISCLOSURE_RECEIPT"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
review_sha=$(shasum -a 256 "$REVIEW_BUNDLE/review.csv" | cut -d ' ' -f1)
frozen_at_raw=$(date +%Y-%m-%dT%H:%M:%S%z)
frozen_at="${frozen_at_raw:0:22}:${frozen_at_raw:22:2}"
jq -cS -n \
  --arg completed_review_sha256 "sha256:$review_sha" \
  --arg frozen_at "$frozen_at" \
  --argjson second_review_occurred "$SECOND_REVIEW_OCCURRED" \
  --argjson adjudication_occurred "$ADJUDICATION_OCCURRED" \
  --argjson rows_changed "$ROWS_CHANGED" \
  '{
    adjudication: (
      if $adjudication_occurred then {
        adjudicator: {affiliation: "OpenAI", display_name: "OpenAI Codex (primary reviewer)"},
        disclosure: "The primary reviewer resolved proposed consistency-pass changes while identities and automatic scores remained sealed; no independent human or independent model-family adjudicator participated.",
        method: "Reinspect the cited neutral-packet bytes and retain or revise each challenged row under the frozen rubric.",
        occurred: true,
        rows_changed: $rows_changed
      } else {
        disclosure: "No blind adjudication changed a row; no independent human or independent model-family adjudicator participated.",
        occurred: false,
        rows_changed: 0
      } end
    ),
    completed_review_sha256: $completed_review_sha256,
    frozen_at: $frozen_at,
    primary_reviewer: {
      affiliation: "OpenAI",
      display_name: "OpenAI Codex",
      prior_exposure: "The reviewer knew the preregistration and opaque campaign-status metadata but received no sealed mapping, model identity, automatic score, trace, or article draft during item judgments.",
      role: "Primary artifact reviewer under Charles Azam authorisation"
    },
    protocol_deviations: [
      {
        deviation_id: "submitted-scripts-not-executed",
        disclosure: "The proposed offline submitted-script runner was withdrawn before review after a security audit. No submitted script was executed; an applicable script therefore received partial or fail rather than the preregistered execution pass."
      },
      {
        deviation_id: "benchmark-sandbox-exposed-host-secrets",
        disclosure: "A pre-results audit found that the frozen inference sandbox ran as root, mounted broad host /etc state, and made live provider auth readable to the agent. Complete raw attempts remain private, submitted output is scanned before review, and this campaign does not establish hardened sandbox isolation."
      }
    ],
    schema_version: "1.0",
    second_review: (
      if $second_review_occurred then {
        disclosure: "A fresh-context Codex consistency pass challenged the completed judgments while blind; this was neither an independent human review nor an independent model-family review.",
        occurred: true,
        reviewer: {affiliation: "OpenAI", display_name: "OpenAI Codex (fresh-context pass)"},
        scope: "All eight registered rows for every neutral packet, using only the neutral review material."
      } else {
        disclosure: "No second artifact-review pass occurred; no independent human or independent model-family review participated.",
        occurred: false
      } end
    )
  }' > "$REVIEW_DISCLOSURE_DRAFT"
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    create-review-disclosure \
    --review-bundle "$REVIEW_BUNDLE" \
    --primary-review "$PRIMARY_REVIEW" \
    --input "$REVIEW_DISCLOSURE_DRAFT" \
    --output "$REVIEW_EDITORIAL_PRIVATE"
) > "$REVIEW_DISCLOSURE_RECEIPT"
chmod 400 \
  "$REVIEW_DISCLOSURE_DRAFT" "$REVIEW_EDITORIAL_PRIVATE" \
  "$REVIEW_DISCLOSURE_RECEIPT"
```

## 7. Commit the completed-review commitment alone

`freeze-review` validates the neutral bundle, exact packet trees, all eight canonical rows per
packet, and the item 6/item 8 semantics before hashing the exact review bytes.

```bash
test "$REVIEW_MODE" = available
REVIEW_FREEZE_REL=results/commitments/v4-review-freeze.json
REVIEW_FREEZE="$REPO/$REVIEW_FREEZE_REL"
REVIEW_FREEZE_RECEIPT="$PRIVATE/finalization-receipts/review-freeze-$PUBLIC_BASE.json"
for fresh_path in "$REVIEW_FREEZE" "$REVIEW_FREEZE_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization freeze-review \
    --review-bundle "$REVIEW_BUNDLE" \
    --primary-review "$PRIMARY_REVIEW" \
    --mapping-freeze "$MAPPING_FREEZE" \
    --editorial-metadata "$REVIEW_EDITORIAL_PRIVATE" \
    --output "$REVIEW_FREEZE"
) > "$REVIEW_FREEZE_RECEIPT"
test -s "$REVIEW_FREEZE_RECEIPT"
chmod 400 "$REVIEW_FREEZE_RECEIPT"

cd "$REPO"
git fetch origin main
test "$(git rev-parse origin/main)" = "$MAPPING_COMMIT"
test "$(git rev-parse HEAD)" = "$MAPPING_COMMIT"
git diff --quiet
git diff --cached --quiet
review_freeze_sha=$(shasum -a 256 "$REVIEW_FREEZE" | cut -d ' ' -f1)
git add -- "$REVIEW_FREEZE_REL"
test "$(git diff --cached --name-only)" = "$REVIEW_FREEZE_REL"
git diff --cached --check
git commit --no-gpg-sign -m "Commit V4 blind review before identity unsealing"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = 2
test "$(git rev-parse HEAD^)" = "$MAPPING_COMMIT"
test "$(git diff-tree --no-commit-id --name-only -r HEAD)" = \
  "$REVIEW_FREEZE_REL"
test "$(git ls-tree HEAD -- "$REVIEW_FREEZE_REL" | awk '{print $1,$2}')" = \
  "100644 blob"
test "$(git show "HEAD:$REVIEW_FREEZE_REL" | shasum -a 256 \
  | cut -d ' ' -f1)" = "$review_freeze_sha"
git push origin main
git fetch origin main
REVIEW_COMMIT=$(git rev-parse HEAD)
test "$REVIEW_COMMIT" = "$(git rev-parse origin/main)"
test "$(git rev-parse "$REVIEW_COMMIT^")" = "$MAPPING_COMMIT"
```

If this commit or push fails, keep the mapping sealed and stop. Never amend the completed review to
make publication easier.

## 8. Phase 3: finalize and verify the blinded review

This section applies only to `REVIEW_MODE=available`. Equality with the public review commit is the
unlock. Finalize into a new public directory, then independently verify byte identity from the
committed review through the unsealed mapping and public provenance.

```bash
test "$REVIEW_MODE" = available
git fetch origin main
test "$(git rev-parse origin/main)" = "$REVIEW_COMMIT"
test "$(git rev-parse HEAD)" = "$REVIEW_COMMIT"
git diff --quiet
git diff --cached --quiet
test "$(git show "$REVIEW_COMMIT:$REVIEW_FREEZE_REL" | shasum -a 256 \
  | cut -d ' ' -f1)" = "$review_freeze_sha"
test "$(shasum -a 256 "$REVIEW_FREEZE" | cut -d ' ' -f1)" = \
  "$review_freeze_sha"
test "$(git show "$MAPPING_COMMIT:$MAPPING_FREEZE_REL" | shasum -a 256 \
  | cut -d ' ' -f1)" = "$mapping_freeze_sha"
test "$(shasum -a 256 "$MAPPING_FREEZE" | cut -d ' ' -f1)" = \
  "$mapping_freeze_sha"

MAPPING_FREEZE_RECHECK="$FINAL_PRIVATE/mapping-freeze-recheck-$REVIEW_COMMIT.json"
MAPPING_RECHECK_RECEIPT="$PRIVATE/finalization-receipts/mapping-freeze-recheck-$PUBLIC_BASE.json"
for fresh_path in "$MAPPING_FREEZE_RECHECK" "$MAPPING_RECHECK_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization freeze-mapping \
    --sealed-mapping "$SEALED_MAPPING" \
    --output "$MAPPING_FREEZE_RECHECK"
) > "$MAPPING_RECHECK_RECEIPT"
cmp --silent "$MAPPING_FREEZE" "$MAPPING_FREEZE_RECHECK"
test -s "$MAPPING_RECHECK_RECEIPT"
chmod 400 "$MAPPING_FREEZE_RECHECK" "$MAPPING_RECHECK_RECEIPT"

REVIEW_FREEZE_RECHECK="$FINAL_PRIVATE/review-freeze-recheck-$REVIEW_COMMIT.json"
REVIEW_RECHECK_RECEIPT="$PRIVATE/finalization-receipts/review-freeze-recheck-$PUBLIC_BASE.json"
for fresh_path in "$REVIEW_FREEZE_RECHECK" "$REVIEW_RECHECK_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization freeze-review \
    --review-bundle "$REVIEW_BUNDLE" \
    --primary-review "$PRIMARY_REVIEW" \
    --mapping-freeze "$MAPPING_FREEZE" \
    --editorial-metadata "$REVIEW_EDITORIAL_PRIVATE" \
    --output "$REVIEW_FREEZE_RECHECK"
) > "$REVIEW_RECHECK_RECEIPT"
cmp --silent "$REVIEW_FREEZE" "$REVIEW_FREEZE_RECHECK"
test -s "$REVIEW_RECHECK_RECEIPT"
chmod 400 "$REVIEW_FREEZE_RECHECK" "$REVIEW_RECHECK_RECEIPT"

BLIND_REVIEW_ROOT="$REPO/results/blind-review"
PUBLIC_REVIEW="$BLIND_REVIEW_ROOT/public"
REVIEW_VERIFICATION_REL=results/commitments/v4-finalized-review-verification.json
REVIEW_VERIFICATION="$REPO/$REVIEW_VERIFICATION_REL"
FINALIZED_REVIEW_RECEIPT="$PRIVATE/finalization-receipts/finalized-review-$PUBLIC_BASE.json"
test ! -e "$BLIND_REVIEW_ROOT"
test ! -L "$BLIND_REVIEW_ROOT"
install -d -m 755 "$BLIND_REVIEW_ROOT"
for fresh_path in "$PUBLIC_REVIEW" "$REVIEW_VERIFICATION" "$FINALIZED_REVIEW_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done

(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m analysis.blind_review finalize \
    --runs-root "$SNAP/raw" \
    --matrix protocol/matrix.tsv \
    --schedules-root "$SNAP/schedules" \
    --ledger protocol/evaluation_ledger.json \
    --rubric-source protocol/ARTIFACT_REVIEW.md \
    --review-bundle "$REVIEW_BUNDLE" \
    --sealed-mapping "$SEALED_MAPPING" \
    --public-bundle "$PUBLIC_REVIEW"
)
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    verify-finalized-review \
    --review-freeze "$REVIEW_FREEZE" \
    --mapping-freeze "$MAPPING_FREEZE" \
    --sealed-mapping "$SEALED_MAPPING" \
    --primary-review "$PRIMARY_REVIEW" \
    --editorial-metadata "$REVIEW_EDITORIAL_PRIVATE" \
    --review-bundle "$REVIEW_BUNDLE" \
    --public-bundle "$PUBLIC_REVIEW" \
    --output "$REVIEW_VERIFICATION"
) > "$FINALIZED_REVIEW_RECEIPT"
test -s "$FINALIZED_REVIEW_RECEIPT"
chmod 400 "$FINALIZED_REVIEW_RECEIPT"
```

If `finalize` fails after reading the mapping, blinding cannot be recreated. The public review
commit remains immutable. Preserve every path and stop; retry only the same command after a purely
operational diagnosis, never after changing `review.csv`. If verification fails, publish nothing.

## 9. Recheck the evaluation commitment from the immutable snapshot

This re-harvest and re-evaluation are fresh private computations. They must reproduce the original
harvest and every committed score/summary byte before article exports are generated. No file is
opened manually.

```bash
PUBLIC_TERMINAL_COMMIT="$EVALUATION_COMMIT"
if test "$REVIEW_MODE" = available; then
  PUBLIC_TERMINAL_COMMIT="$REVIEW_COMMIT"
fi
git fetch origin main
test "$(git rev-parse origin/main)" = "$PUBLIC_TERMINAL_COMMIT"
test "$(git rev-parse HEAD)" = "$PUBLIC_TERMINAL_COMMIT"
test "$(git show "$EVALUATION_COMMIT:$EVALUATION_FREEZE_REL" | shasum -a 256 \
  | cut -d ' ' -f1)" = "$evaluation_freeze_sha"
test "$(shasum -a 256 "$EVALUATION_FREEZE" | cut -d ' ' -f1)" = \
  "$evaluation_freeze_sha"

test "$(jq -r '.evaluation_root' "$EVALUATION_FREEZE")" = results/evaluation
test "$(jq -r '.selection_source.path' "$EVALUATION_FREEZE")" = \
  results/harvested/eligibility.json
test "$(jq -r '.execution_environment.path' "$EVALUATION_FREEZE")" = \
  results/evaluation-environment.json
test "$(jq -r '.execution_environment.sha256' "$EVALUATION_FREEZE")" = \
  "$(shasum -a 256 "$EVALUATION_ENVIRONMENT" | cut -d ' ' -f1)"
committed_datasets=$(jq -r '.datasets | join(" ")' "$EVALUATION_FREEZE")
if test "${#SELECTED_DATASETS[@]}" -eq 0; then
  test -z "$committed_datasets"
else
  test "$committed_datasets" = "${SELECTED_DATASETS[*]}"
fi
test "$(jq -r '.selection_source.sha256' "$EVALUATION_FREEZE")" = \
  "$(shasum -a 256 "$HARVEST/eligibility.json" | cut -d ' ' -f1)"
test "$(jq -r '.selection_source.size_bytes' "$EVALUATION_FREEZE")" = \
  "$(stat -f '%z' "$HARVEST/eligibility.json")"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  for dataset in "${SELECTED_DATASETS[@]}"; do
    for filename in scores.jsonl summary.json; do
      relative="results/evaluation/$dataset/$filename"
      test "$(jq -r --arg path "$relative" \
        '[.files[] | select(.path == $path)] | length' "$EVALUATION_FREEZE")" = 1
      test "$(jq -r --arg path "$relative" \
        '.files[] | select(.path == $path) | .sha256' "$EVALUATION_FREEZE")" = \
        "$(shasum -a 256 "$REPO/$relative" | cut -d ' ' -f1)"
      test "$(jq -r --arg path "$relative" \
        '.files[] | select(.path == $path) | .size_bytes' "$EVALUATION_FREEZE")" = \
        "$(stat -f '%z' "$REPO/$relative")"
    done
  done
fi

RECHECK_HARVEST="$FINAL_PRIVATE/recheck-harvest-$PUBLIC_TERMINAL_COMMIT"
RECHECK_EVALUATION="$FINAL_PRIVATE/recheck-evaluation-$PUBLIC_TERMINAL_COMMIT"
RECHECK_HARVEST_STDOUT="$PRIVATE/finalization-receipts/recheck-harvest-$PUBLIC_TERMINAL_COMMIT.stdout"
RECHECK_HARVEST_STDERR="$PRIVATE/finalization-receipts/recheck-harvest-$PUBLIC_TERMINAL_COMMIT.stderr"
for fresh_path in \
  "$RECHECK_HARVEST" "$RECHECK_EVALUATION" \
  "$RECHECK_HARVEST_STDOUT" "$RECHECK_HARVEST_STDERR"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m analysis.harvest \
    --runs-root "$SNAP/raw" \
    --matrix protocol/matrix.tsv \
    --ledger protocol/evaluation_ledger.json \
    --schedules-root "$SNAP/schedules" \
    --output-dir "$RECHECK_HARVEST"
) > "$RECHECK_HARVEST_STDOUT" 2> "$RECHECK_HARVEST_STDERR"
chmod 400 "$RECHECK_HARVEST_STDOUT" "$RECHECK_HARVEST_STDERR"
diff -qr "$HARVEST" "$RECHECK_HARVEST" >/dev/null
install -d -m 700 "$RECHECK_EVALUATION"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  for dataset in "${SELECTED_DATASETS[@]}"; do
    (
      cd "$FINAL_PINNED"
      env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
        uv run --frozen eng-bench evaluate \
        --manifests "$RECHECK_HARVEST/$dataset/manifests.jsonl" \
        --predictions "$RECHECK_HARVEST/$dataset/predictions.jsonl" \
        --measurements measurements/held_out.jsonl \
        --ledger protocol/evaluation_ledger.json \
        --evaluator-manifest protocol/evaluator_manifest.sha256 \
        --evaluator-root "$FINAL_PINNED" \
        --artifact-root "$SNAP/raw" \
        --output-dir "$RECHECK_EVALUATION/$dataset"
    )
  done
fi
diff -qr "$EVALUATION" "$RECHECK_EVALUATION" >/dev/null
RECHECK_ENVIRONMENT="$FINAL_PRIVATE/recheck-environment-$PUBLIC_TERMINAL_COMMIT.json"
RECHECK_ENVIRONMENT_RECEIPT="$PRIVATE/finalization-receipts/recheck-environment-$PUBLIC_TERMINAL_COMMIT.json"
for fresh_path in "$RECHECK_ENVIRONMENT" "$RECHECK_ENVIRONMENT_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    capture-evaluation-environment \
    --repository-root "$FINAL_PINNED" \
    --output "$RECHECK_ENVIRONMENT"
) > "$RECHECK_ENVIRONMENT_RECEIPT"
cmp --silent "$EVALUATION_ENVIRONMENT" "$RECHECK_ENVIRONMENT"
chmod 400 "$RECHECK_ENVIRONMENT" "$RECHECK_ENVIRONMENT_RECEIPT"
chmod -R a-w "$RECHECK_HARVEST" "$RECHECK_EVALUATION"
```

## 10. Generate publication exports and the reviewer disclosure

Run the independent publication export once for each selected dataset. The current implementation
emits eleven exact files per dataset, including the three campaign-accounting files in addition to
the files summarized in `analysis/PUBLICATION.md`.

```bash
PUBLICATION="$REPO/results/publication"
test ! -e "$PUBLICATION"
test ! -L "$PUBLICATION"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  install -d -m 755 "$PUBLICATION"
fi
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  for dataset in "${SELECTED_DATASETS[@]}"; do
    (
      cd "$FINAL_PINNED"
      env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
        uv run --frozen python -m analysis.publication \
        --dataset "$dataset" \
        --manifests "$HARVEST/$dataset/manifests.jsonl" \
        --predictions "$HARVEST/$dataset/predictions.jsonl" \
        --measurements measurements/held_out.jsonl \
        --scores "$EVALUATION/$dataset/scores.jsonl" \
        --summary "$EVALUATION/$dataset/summary.json" \
        --attempts "$HARVEST/attempts.csv" \
        --schedule-integrity "$HARVEST/schedule_integrity.jsonl" \
        --eligibility "$HARVEST/eligibility.json" \
        --matrix protocol/matrix.tsv \
        --schedules-root "$SNAP/schedules" \
        --runs-root "$SNAP/raw" \
        --artifact-root "$SNAP/raw" \
        --ledger protocol/evaluation_ledger.json \
        --evaluator-manifest protocol/evaluator_manifest.sha256 \
        --evaluator-root "$FINAL_PINNED" \
        --output-dir "$PUBLICATION/$dataset"
    )
    expected_publication_paths=$(printf '%s\n' \
      campaign_attempts.csv campaign_eligibility.json campaign_run_status.csv \
      cell_status.csv chart_data.json claims.json provenance.json \
      replicate_metrics.csv run_status.csv sha256_manifest.json \
      task_metric_summary.csv | LC_ALL=C sort)
    actual_publication_paths=$(find "$PUBLICATION/$dataset" -type f -print \
      | sed "s#^$PUBLICATION/$dataset/##" | LC_ALL=C sort)
    test "$actual_publication_paths" = "$expected_publication_paths"
    test -z "$(find "$PUBLICATION/$dataset" -type l -print -quit)"
  done
fi
```

When review succeeded, publish the already typed and review-committed disclosure byte-for-byte:

```bash
if test "$REVIEW_MODE" = available; then
  REVIEW_EDITORIAL="$REPO/results/blind-review/artifact-review-editorial.json"
  test ! -e "$REVIEW_EDITORIAL"
  test ! -L "$REVIEW_EDITORIAL"
  cp "$REVIEW_EDITORIAL_PRIVATE" "$REVIEW_EDITORIAL"
  chmod 644 "$REVIEW_EDITORIAL"
  cmp --silent "$REVIEW_EDITORIAL_PRIVATE" "$REVIEW_EDITORIAL"
  test "$(jq -r '.completed_review_sha256' "$REVIEW_EDITORIAL")" = \
    "$(jq -r '.completed_review_sha256' "$PUBLIC_REVIEW/provenance.json")"
fi
```

For any unavailable review mode, create instead the corresponding fixed public record and do not
create an editorial JSON or public review directory:

```bash
if test "$REVIEW_MODE" != available; then
  REVIEW_UNAVAILABLE="$REPO/results/blind-review/REVIEW_UNAVAILABLE.md"
  test ! -e "$REVIEW_UNAVAILABLE"
  test ! -L "$REVIEW_UNAVAILABLE"
  install -d -m 755 "$REPO/results/blind-review"
  if test "$REVIEW_MODE" = identity-leak-unavailable; then
    unavailable_reason='Identity-blind packet preparation failed closed because a submitted artifact contained an explicit run, system, or model identity token. No artifact was redacted or rewritten, the sealed mapping was not opened, and no substantive artifact-review result is reported.'
  elif test "$REVIEW_MODE" = no-reviewable-artifacts; then
    unavailable_reason='Identity-blind packet preparation found no infrastructure-valid physical attempt to review. No neutral packet or sealed mapping was created, and no substantive artifact-review result is reported.'
  elif test "$REVIEW_MODE" = credential-scan-unavailable; then
    unavailable_reason='Identity-blind packet preparation failed closed when an automated no-match-output scan found credential-like material. No packet or sealed mapping was published, no reviewer received the candidate bytes, and no substantive artifact-review result is reported. The matching material remains private and is not printed or redacted.'
  else
    test "$REVIEW_MODE" = reviewer-isolation-unavailable
    unavailable_reason='The registered technically isolated reviewer runtime never completed its exact synthetic adversarial probe, and the public operator-environment incident disabled artifact review for V4. A normal agent in the shared workspace was not treated as blind, no sealed mapping was created, and no substantive artifact-review result is reported.'
  fi
  printf '%s\n' \
    '# V4 artifact review unavailable' \
    '' \
    "$unavailable_reason Deterministic evaluation may be released only if the later whole-candidate privacy scan also passes; otherwise its earlier byte commitment remains public without result bytes." \
    > "$REVIEW_UNAVAILABLE"
fi
```

## 10a. Re-run semantic proofs immediately before release scanning

These checks close the interval between the earlier commitments and final staging. Every output is
new and private; byte comparisons must succeed before candidate files are made read-only.

```bash
PRESTAGE_EVALUATION_FREEZE="$FINAL_PRIVATE/prestage-evaluation-freeze-$PUBLIC_TERMINAL_COMMIT.json"
PRESTAGE_EVALUATION_RECEIPT="$PRIVATE/finalization-receipts/prestage-evaluation-freeze-$PUBLIC_TERMINAL_COMMIT.json"
for fresh_path in "$PRESTAGE_EVALUATION_FREEZE" "$PRESTAGE_EVALUATION_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
prestage_evaluation_arguments=(
  freeze-evaluation
  --repository-root "$REPO"
  --evaluation-root "$EVALUATION"
  --execution-environment "$EVALUATION_ENVIRONMENT"
  --selection-source "$HARVEST/eligibility.json"
  --output "$PRESTAGE_EVALUATION_FREEZE"
)
if test "${#SELECTED_DATASETS[@]}" -eq 0; then
  prestage_evaluation_arguments+=(--allow-empty-selection)
else
  for dataset in "${SELECTED_DATASETS[@]}"; do
    prestage_evaluation_arguments+=(--dataset "$dataset")
  done
fi
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    "${prestage_evaluation_arguments[@]}"
) > "$PRESTAGE_EVALUATION_RECEIPT"
chmod 400 "$PRESTAGE_EVALUATION_RECEIPT"
cmp --silent "$EVALUATION_FREEZE" "$PRESTAGE_EVALUATION_FREEZE"

PRESTAGE_HARVEST="$FINAL_PRIVATE/prestage-harvest-$PUBLIC_TERMINAL_COMMIT"
PRESTAGE_HARVEST_STDOUT="$PRIVATE/finalization-receipts/prestage-harvest-$PUBLIC_TERMINAL_COMMIT.stdout"
PRESTAGE_HARVEST_STDERR="$PRIVATE/finalization-receipts/prestage-harvest-$PUBLIC_TERMINAL_COMMIT.stderr"
for fresh_path in \
  "$PRESTAGE_HARVEST" "$PRESTAGE_HARVEST_STDOUT" "$PRESTAGE_HARVEST_STDERR"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m analysis.harvest \
    --runs-root "$SNAP/raw" \
    --matrix protocol/matrix.tsv \
    --ledger protocol/evaluation_ledger.json \
    --schedules-root "$SNAP/schedules" \
    --output-dir "$PRESTAGE_HARVEST"
) > "$PRESTAGE_HARVEST_STDOUT" 2> "$PRESTAGE_HARVEST_STDERR"
chmod 400 "$PRESTAGE_HARVEST_STDOUT" "$PRESTAGE_HARVEST_STDERR"
diff -qr "$HARVEST" "$PRESTAGE_HARVEST" >/dev/null

if test "$DISCLOSURE_MODE" != none; then
  PRESTAGE_GATE_STDOUT="$PRIVATE/finalization-receipts/prestage-gate-$PUBLIC_TERMINAL_COMMIT.stdout"
  PRESTAGE_GATE_STDERR="$PRIVATE/finalization-receipts/prestage-gate-$PUBLIC_TERMINAL_COMMIT.stderr"
  for fresh_path in "$PRESTAGE_GATE_STDOUT" "$PRESTAGE_GATE_STDERR"; do
    test ! -e "$fresh_path"
    test ! -L "$fresh_path"
  done
  (
    cd "$FINAL_PINNED"
    env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen python -m analysis.verify_gate_disclosure \
      --repository-root "$REPO" \
      --disclosure "$DISCLOSURE" \
      --runs-root "$SNAP/raw" \
      --matrix protocol/matrix.tsv \
      --ledger protocol/evaluation_ledger.json \
      --schedules-root "$SNAP/schedules" \
      --frozen-manifest protocol/frozen_manifest.sha256
  ) > "$PRESTAGE_GATE_STDOUT" 2> "$PRESTAGE_GATE_STDERR"
  cmp --silent "$GATE_VERIFY_RECEIPT" "$PRESTAGE_GATE_STDOUT"
  cmp --silent "$GATE_VERIFY_STDERR" "$PRESTAGE_GATE_STDERR"
  test -s "$PRESTAGE_GATE_STDOUT"
  chmod 400 "$PRESTAGE_GATE_STDOUT" "$PRESTAGE_GATE_STDERR"
fi

if test "$REVIEW_MODE" = available; then
  PRESTAGE_REVIEW_VERIFICATION="$FINAL_PRIVATE/prestage-finalized-review-$PUBLIC_TERMINAL_COMMIT.json"
  PRESTAGE_REVIEW_RECEIPT="$PRIVATE/finalization-receipts/prestage-finalized-review-$PUBLIC_TERMINAL_COMMIT.json"
  for fresh_path in "$PRESTAGE_REVIEW_VERIFICATION" "$PRESTAGE_REVIEW_RECEIPT"; do
    test ! -e "$fresh_path"
    test ! -L "$fresh_path"
  done
  (
    cd "$FINAL_PINNED"
    env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen python -m operations.v4_finalization \
      verify-finalized-review \
      --review-freeze "$REVIEW_FREEZE" \
      --mapping-freeze "$MAPPING_FREEZE" \
      --sealed-mapping "$SEALED_MAPPING" \
      --primary-review "$PRIMARY_REVIEW" \
      --editorial-metadata "$REVIEW_EDITORIAL_PRIVATE" \
      --review-bundle "$REVIEW_BUNDLE" \
      --public-bundle "$PUBLIC_REVIEW" \
      --output "$PRESTAGE_REVIEW_VERIFICATION"
  ) > "$PRESTAGE_REVIEW_RECEIPT"
  chmod 400 "$PRESTAGE_REVIEW_RECEIPT"
  cmp --silent "$REVIEW_VERIFICATION" "$PRESTAGE_REVIEW_VERIFICATION"
  cmp --silent "$REVIEW_EDITORIAL_PRIVATE" "$REVIEW_EDITORIAL"
fi

PRESTAGE_PUBLICATION="$FINAL_PRIVATE/prestage-publication-$PUBLIC_TERMINAL_COMMIT"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  test ! -e "$PRESTAGE_PUBLICATION"
  test ! -L "$PRESTAGE_PUBLICATION"
  install -d -m 700 "$PRESTAGE_PUBLICATION"
  for dataset in "${SELECTED_DATASETS[@]}"; do
    (
      cd "$FINAL_PINNED"
      env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
        uv run --frozen python -m analysis.publication \
        --dataset "$dataset" \
        --manifests "$HARVEST/$dataset/manifests.jsonl" \
        --predictions "$HARVEST/$dataset/predictions.jsonl" \
        --measurements measurements/held_out.jsonl \
        --scores "$EVALUATION/$dataset/scores.jsonl" \
        --summary "$EVALUATION/$dataset/summary.json" \
        --attempts "$HARVEST/attempts.csv" \
        --schedule-integrity "$HARVEST/schedule_integrity.jsonl" \
        --eligibility "$HARVEST/eligibility.json" \
        --matrix protocol/matrix.tsv \
        --schedules-root "$SNAP/schedules" \
        --runs-root "$SNAP/raw" \
        --artifact-root "$SNAP/raw" \
        --ledger protocol/evaluation_ledger.json \
        --evaluator-manifest protocol/evaluator_manifest.sha256 \
        --evaluator-root "$FINAL_PINNED" \
        --output-dir "$PRESTAGE_PUBLICATION/$dataset"
    )
  done
  diff -qr "$PUBLICATION" "$PRESTAGE_PUBLICATION" >/dev/null
fi

PRESTAGE_ENVIRONMENT="$FINAL_PRIVATE/prestage-environment-$PUBLIC_TERMINAL_COMMIT.json"
PRESTAGE_ENVIRONMENT_RECEIPT="$PRIVATE/finalization-receipts/prestage-environment-$PUBLIC_TERMINAL_COMMIT.json"
for fresh_path in "$PRESTAGE_ENVIRONMENT" "$PRESTAGE_ENVIRONMENT_RECEIPT"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    capture-evaluation-environment \
    --repository-root "$FINAL_PINNED" \
    --output "$PRESTAGE_ENVIRONMENT"
) > "$PRESTAGE_ENVIRONMENT_RECEIPT"
cmp --silent "$EVALUATION_ENVIRONMENT" "$PRESTAGE_ENVIRONMENT"
chmod 400 "$PRESTAGE_ENVIRONMENT" "$PRESTAGE_ENVIRONMENT_RECEIPT"

for protected_tree in "$HARVEST" "$EVALUATION" "$PRESTAGE_HARVEST"; do
  chmod -R a-w "$protected_tree"
done
chmod a-w "$EVALUATION_ENVIRONMENT"
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  chmod -R a-w "$PUBLICATION" "$PRESTAGE_PUBLICATION"
fi
if test "$REVIEW_MODE" = available; then
  chmod -R a-w "$PUBLIC_REVIEW"
  chmod a-w "$REVIEW_VERIFICATION" "$REVIEW_EDITORIAL"
else
  chmod a-w "$REVIEW_UNAVAILABLE"
fi
if test "$DISCLOSURE_MODE" != none; then
  chmod a-w "$DISCLOSURE"
fi
```

Only now may the editor inspect released material. When a dataset was selected, that includes its
verified publication exports and committed scores; the article must say those numbers were
byte-reproduced internally against private verified raw evidence but are not independently
recomputable from the public bundle. When review succeeded, it must identify the reviewer,
second-pass/adjudication facts, changed-row count, and lack of independent human review.

On this fixed incident path, neither condition holds. The editor may inspect only campaign
accounting, eligibility, integrity records, the empty evaluation commitment, and the two public
incident/security records. The article must state that no numeric/head-to-head dataset was eligible,
no review occurred, and no neutral bundle or sealed mapping existed. It must not discuss withheld
predictions, infer a partial winner, or imply that scripts or artifacts were reviewed.

## 11. Build the exact final allowlist and stop on privacy or size risk

The final results commit may include only:

- immutable `results/raw-ledgers/` imported by the archive procedure, while complete raw attempts
  remain private because they contain event streams, provider plumbing, and full workspaces;
- the exact harvested, selected evaluation, publication, and finalized public-review trees;
- the gate-key disclosure when one exists;
- the finalized-review verification when review succeeded; and
- either the reviewer editorial JSON or the applicable review-unavailability record.

The already public evaluation/review commitments are not recommitted. Private gate keys, archive
tars, cumulative snapshots, neutral packets, sealed mapping, review preparation diagnostics, and
recheck trees are never candidates.

```bash
ALLOWLIST0="$FINAL_PRIVATE/final-allowlist-$PUBLIC_TERMINAL_COMMIT.paths0"
ACTUAL0="$FINAL_PRIVATE/final-staged-$PUBLIC_TERMINAL_COMMIT.paths0"
COMMIT_ACTUAL0="$FINAL_PRIVATE/final-commit-$PUBLIC_TERMINAL_COMMIT.paths0"
PRESTAGE0="$FINAL_PRIVATE/final-prestage-$PUBLIC_TERMINAL_COMMIT.paths0"
PRIVATE_RAW0="$FINAL_PRIVATE/private-raw-$PUBLIC_TERMINAL_COMMIT.paths0"
STAGED_UNTRACKED0="$FINAL_PRIVATE/staged-untracked-$PUBLIC_TERMINAL_COMMIT.paths0"
STAGED_IGNORED0="$FINAL_PRIVATE/staged-ignored-$PUBLIC_TERMINAL_COMMIT.paths0"
STAGED_RAW_DIFF="$FINAL_PRIVATE/staged-raw-$PUBLIC_TERMINAL_COMMIT.diff"
COMMITTED_UNTRACKED0="$FINAL_PRIVATE/committed-untracked-$PUBLIC_TERMINAL_COMMIT.paths0"
COMMITTED_IGNORED0="$FINAL_PRIVATE/committed-ignored-$PUBLIC_TERMINAL_COMMIT.paths0"
COMMITTED_RAW_DIFF="$FINAL_PRIVATE/committed-raw-$PUBLIC_TERMINAL_COMMIT.diff"
WORKTREE_SCAN="$FINAL_PRIVATE/public-candidate-worktree-$PUBLIC_TERMINAL_COMMIT.json"
WORKTREE_SCAN_RECEIPT="$PRIVATE/finalization-receipts/public-candidate-worktree-$PUBLIC_TERMINAL_COMMIT.json"
COMMIT_SCAN="$FINAL_PRIVATE/public-candidate-commit-$PUBLIC_TERMINAL_COMMIT.json"
COMMIT_SCAN_RECEIPT="$PRIVATE/finalization-receipts/public-candidate-commit-$PUBLIC_TERMINAL_COMMIT.json"
for fresh_path in \
  "$ALLOWLIST0" "$ACTUAL0" "$COMMIT_ACTUAL0" "$PRESTAGE0" "$PRIVATE_RAW0" \
  "$STAGED_UNTRACKED0" "$STAGED_IGNORED0" "$STAGED_RAW_DIFF" \
  "$COMMITTED_UNTRACKED0" "$COMMITTED_IGNORED0" "$COMMITTED_RAW_DIFF" \
  "$WORKTREE_SCAN" "$WORKTREE_SCAN_RECEIPT" \
  "$COMMIT_SCAN" "$COMMIT_SCAN_RECEIPT"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done

candidate_roots=(
  "$REPO/results/harvested"
  "$REPO/results/evaluation"
)
if test "${#SELECTED_DATASETS[@]}" -gt 0; then
  candidate_roots+=("$REPO/results/publication")
fi
if test "$REVIEW_MODE" = available; then
  candidate_roots+=("$REPO/results/blind-review/public")
fi

fixed_candidates=()
for imported_stage in "${IMPORTED_STAGES[@]}"; do
  fixed_candidates+=(
    "$REPO/results/raw-ledgers/v4-$imported_stage.tree.sha256"
  )
done
if test "$DISCLOSURE_MODE" != none; then
  fixed_candidates+=("$DISCLOSURE")
fi
if test "$REVIEW_MODE" = available; then
  fixed_candidates+=("$REVIEW_VERIFICATION")
  fixed_candidates+=("$REPO/results/blind-review/artifact-review-editorial.json")
else
  fixed_candidates+=("$REPO/results/blind-review/REVIEW_UNAVAILABLE.md")
fi

for root in "${candidate_roots[@]}"; do
  test -d "$root"
  test ! -L "$root"
  test -z "$(find "$root" -type l -print -quit)"
  test -z "$(find "$root" ! -type d ! -type f -print -quit)"
done
test -d "$REPO/results/raw"
test ! -L "$REPO/results/raw"
test -z "$(find "$REPO/results/raw" -type l -print -quit)"
test -z "$(find "$REPO/results/raw" ! -type d ! -type f -print -quit)"
find "$REPO/results/raw" -type f -print0 \
  | while IFS= read -r -d '' absolute; do
      relative=${absolute#"$REPO/"}
      test "$relative" != "$absolute"
      printf '%s\0' "$relative"
    done \
  | LC_ALL=C sort -zu > "$PRIVATE_RAW0"
test -s "$PRIVATE_RAW0"

verify_private_raw_is_only_worktree_residue() {
  local untracked_output="$1"
  local ignored_output="$2"
  local raw_diff_output="$3"
  git ls-files --others --exclude-standard -z \
    | LC_ALL=C sort -zu > "$untracked_output"
  while IFS= read -r -d '' relative; do
    case "$relative" in
      results/raw/*) ;;
      *)
        printf 'unexpected untracked path after result staging: %s\n' "$relative" >&2
        exit 65
        ;;
    esac
  done < "$untracked_output"
  git ls-files --others --ignored --exclude-standard -z \
    | while IFS= read -r -d '' relative; do
        case "$relative" in
          results/raw/*) ;;
          *) printf '%s\0' "$relative" ;;
        esac
      done \
    | LC_ALL=C sort -zu > "$ignored_output"
  cmp --silent "$BASELINE_IGNORED0" "$ignored_output"
  diff -qr "$REPO/results/raw" "$SNAP/raw" > "$raw_diff_output" 2>&1
}
for file in "${fixed_candidates[@]}"; do
  test -f "$file"
  test ! -L "$file"
done

{
  for root in "${candidate_roots[@]}"; do
    find "$root" -type f -print0
  done
  for file in "${fixed_candidates[@]}"; do
    printf '%s\0' "$file"
  done
} | while IFS= read -r -d '' absolute; do
  relative=${absolute#"$REPO/"}
  test "$relative" != "$absolute"
  case "$relative" in
    *$'\n'*|*$'\r'*|*$'\t'*)
      printf 'unsafe Git path in final candidate set\n' >&2
      exit 65
      ;;
  esac
  printf '%s\0' "$relative"
done | LC_ALL=C sort -zu > "$ALLOWLIST0"
test -s "$ALLOWLIST0"

while IFS= read -r -d '' relative; do
  absolute="$REPO/$relative"
  test -f "$absolute"
  test ! -L "$absolute"
  if git -C "$REPO" check-ignore -q -- "$relative"; then
    printf 'final candidate is ignored: %s\n' "$relative" >&2
    exit 65
  fi
  if git -C "$REPO" ls-files --error-unmatch -- "$relative" >/dev/null 2>&1; then
    printf 'final candidate was already tracked: %s\n' "$relative" >&2
    exit 65
  fi
done < "$ALLOWLIST0"

(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    scan-public-candidates \
    --repository-root "$REPO" \
    --paths0 "$ALLOWLIST0" \
    --output "$WORKTREE_SCAN"
) > "$WORKTREE_SCAN_RECEIPT"
chmod 400 "$WORKTREE_SCAN_RECEIPT"
```

Any credential-like hit or file above 95 MiB is a release stop. Do not display the matching line,
redact an immutable raw artifact, omit it silently, use Git LFS, or move it to another host during
this procedure. Preserve the candidate set and request an explicit publication decision.

## 12. Commit and push exactly the allowlist

```bash
cd "$REPO"
git fetch origin main
test "$(git rev-parse origin/main)" = "$PUBLIC_TERMINAL_COMMIT"
test "$(git rev-parse HEAD)" = "$PUBLIC_TERMINAL_COMMIT"
test "$(git branch --show-current)" = main
git diff --quiet
git diff --cached --quiet

{
  for root in "${candidate_roots[@]}"; do
    find "$root" -type f -print0
  done
  for file in "${fixed_candidates[@]}"; do
    printf '%s\0' "$file"
  done
} | while IFS= read -r -d '' absolute; do
  relative=${absolute#"$REPO/"}
  test "$relative" != "$absolute"
  case "$relative" in
    *$'\n'*|*$'\r'*|*$'\t'*)
      printf 'unsafe Git path in final candidate set\n' >&2
      exit 65
      ;;
  esac
  printf '%s\0' "$relative"
done | LC_ALL=C sort -zu > "$PRESTAGE0"
cmp --silent "$ALLOWLIST0" "$PRESTAGE0"

git --literal-pathspecs add \
  --pathspec-from-file="$ALLOWLIST0" \
  --pathspec-file-nul
git diff --cached --name-only -z | LC_ALL=C sort -zu > "$ACTUAL0"
cmp --silent "$ALLOWLIST0" "$ACTUAL0"
git diff --quiet
verify_private_raw_is_only_worktree_residue \
  "$STAGED_UNTRACKED0" "$STAGED_IGNORED0" "$STAGED_RAW_DIFF"
while IFS= read -r -d '' relative; do
  index_entry=$(git ls-files --stage -- "$relative")
  mode=${index_entry%% *}
  case "$mode" in
    100644) ;;
    *)
      printf 'non-blob or unsafe Git mode for %s: %s\n' "$relative" "$mode" >&2
      exit 65
      ;;
  esac
done < "$ALLOWLIST0"

git commit --no-gpg-sign -m "Publish verified V4 benchmark results"
FINAL_COMMIT=$(git rev-parse HEAD)
test "$(git rev-list --parents -n 1 "$FINAL_COMMIT" | awk '{print NF}')" = 2
test "$(git rev-parse "$FINAL_COMMIT^")" = "$PUBLIC_TERMINAL_COMMIT"
git diff-tree --no-commit-id --name-only -z -r "$FINAL_COMMIT" \
  | LC_ALL=C sort -zu > "$COMMIT_ACTUAL0"
cmp --silent "$ALLOWLIST0" "$COMMIT_ACTUAL0"
git diff --quiet
git diff --cached --quiet
verify_private_raw_is_only_worktree_residue \
  "$COMMITTED_UNTRACKED0" "$COMMITTED_IGNORED0" "$COMMITTED_RAW_DIFF"
while IFS= read -r -d '' relative; do
  test "$(git ls-tree "$FINAL_COMMIT" -- "$relative" | awk '{print $2}')" = blob
  working_sha=$(shasum -a 256 "$REPO/$relative" | cut -d ' ' -f1)
  committed_sha=$(git cat-file blob "$FINAL_COMMIT:$relative" \
    | shasum -a 256 | cut -d ' ' -f1)
  test "$working_sha" = "$committed_sha"
done < "$ALLOWLIST0"
(
  cd "$FINAL_PINNED"
  env UV_PROJECT_ENVIRONMENT="$FINAL_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python -m operations.v4_finalization \
    scan-public-candidates \
    --repository-root "$REPO" \
    --paths0 "$ALLOWLIST0" \
    --commit "$FINAL_COMMIT" \
    --output "$COMMIT_SCAN"
) > "$COMMIT_SCAN_RECEIPT"
test "$(jq -r '.aggregate_sha256' "$WORKTREE_SCAN")" = \
  "$(jq -r '.aggregate_sha256' "$COMMIT_SCAN")"
test "$(jq -r '.path_count' "$WORKTREE_SCAN")" = \
  "$(jq -r '.path_count' "$COMMIT_SCAN")"
chmod 400 "$COMMIT_SCAN_RECEIPT"
git push origin main
git fetch origin main
test "$FINAL_COMMIT" = "$(git rev-parse origin/main)"
```

## 13. Create the immutable site-data handoff

The handoff is made only from files proven equal to the final public commit. It does not write the
actual website. `primary/` is the selected `n5` or `n3` publication bundle; `ablation/` is present
only when selected; and artifact-review files are present only after successful finalize/verify.

```bash
HANDOFF_STAGE="$PRIVATE/site-data-handoff/.stage-$FINAL_COMMIT"
HANDOFF="$PRIVATE/site-data-handoff/$FINAL_COMMIT"
HANDOFF_SOURCE="$PRIVATE/public-worktrees/site-handoff-$FINAL_COMMIT"
for fresh_path in "$HANDOFF_STAGE" "$HANDOFF" "$HANDOFF_SOURCE"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
git worktree add --detach "$HANDOFF_SOURCE" "$FINAL_COMMIT"
test "$(git -C "$HANDOFF_SOURCE" rev-parse HEAD)" = "$FINAL_COMMIT"
git -C "$HANDOFF_SOURCE" diff --quiet
git -C "$HANDOFF_SOURCE" diff --cached --quiet
test -z "$(git -C "$HANDOFF_SOURCE" status --porcelain --untracked-files=all)"
install -d -m 700 "$HANDOFF_STAGE"
cp "$HANDOFF_SOURCE/operations/V4_SANDBOX_SECURITY_RECORD.md" \
  "$HANDOFF_STAGE/V4_SANDBOX_SECURITY_RECORD.md"
cp "$HANDOFF_SOURCE/operations/V4_OPERATOR_ENVIRONMENT_INCIDENT.md" \
  "$HANDOFF_STAGE/V4_OPERATOR_ENVIRONMENT_INCIDENT.md"
cp "$HANDOFF_SOURCE/results/evaluation-environment.json" \
  "$HANDOFF_STAGE/evaluation-environment.json"
install -d -m 700 "$HANDOFF_STAGE/campaign"
for campaign_file in \
  attempts.csv eligibility.csv eligibility.json integrity.jsonl schedule_integrity.jsonl
do
  cp "$HANDOFF_SOURCE/results/harvested/$campaign_file" \
    "$HANDOFF_STAGE/campaign/$campaign_file"
done
(
  cd "$HANDOFF_STAGE/campaign"
  find . -type f ! -name MANIFEST.sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 shasum -a 256 > MANIFEST.sha256
  shasum -a 256 --check MANIFEST.sha256
)

if test -n "$PRIMARY_DATASET"; then
  cp -a "$HANDOFF_SOURCE/results/publication/$PRIMARY_DATASET" \
    "$HANDOFF_STAGE/primary"
fi
if test "$ABLATION_ELIGIBLE" = true && test -n "$PRIMARY_DATASET"; then
  cp -a "$HANDOFF_SOURCE/results/publication/ablation" \
    "$HANDOFF_STAGE/ablation"
fi
if test "$REVIEW_MODE" = available; then
  cp -a "$HANDOFF_SOURCE/results/blind-review/public" \
    "$HANDOFF_STAGE/artifact-review"
  cp "$HANDOFF_SOURCE/results/blind-review/artifact-review-editorial.json" \
    "$HANDOFF_STAGE/artifact-review-editorial.json"
else
  cp "$HANDOFF_SOURCE/results/blind-review/REVIEW_UNAVAILABLE.md" \
    "$HANDOFF_STAGE/REVIEW_UNAVAILABLE.md"
fi

campaign_manifest_sha256=$(shasum -a 256 \
  "$HANDOFF_STAGE/campaign/MANIFEST.sha256" | cut -d ' ' -f1)
campaign_manifest_sha256="sha256:$campaign_manifest_sha256"
sandbox_security_record_sha256=$(shasum -a 256 \
  "$HANDOFF_STAGE/V4_SANDBOX_SECURITY_RECORD.md" | cut -d ' ' -f1)
sandbox_security_record_sha256="sha256:$sandbox_security_record_sha256"
operator_environment_incident_sha256=$(shasum -a 256 \
  "$HANDOFF_STAGE/V4_OPERATOR_ENVIRONMENT_INCIDENT.md" | cut -d ' ' -f1)
operator_environment_incident_sha256="sha256:$operator_environment_incident_sha256"
evaluation_environment_sha256=$(shasum -a 256 \
  "$HANDOFF_STAGE/evaluation-environment.json" | cut -d ' ' -f1)
evaluation_environment_sha256="sha256:$evaluation_environment_sha256"
primary_manifest_sha256=null
if test -n "$PRIMARY_DATASET"; then
  primary_manifest_sha256=$(shasum -a 256 \
    "$HANDOFF_STAGE/primary/sha256_manifest.json" | cut -d ' ' -f1)
  primary_manifest_sha256="sha256:$primary_manifest_sha256"
fi
ablation_manifest_sha256=null
if test "$ABLATION_ELIGIBLE" = true && test -n "$PRIMARY_DATASET"; then
  ablation_manifest_sha256=$(shasum -a 256 \
    "$HANDOFF_STAGE/ablation/sha256_manifest.json" | cut -d ' ' -f1)
  ablation_manifest_sha256="sha256:$ablation_manifest_sha256"
fi
review_provenance_sha256=null
editorial_sha256=null
review_unavailable_sha256=null
if test "$REVIEW_MODE" = available; then
  review_provenance_sha256=$(shasum -a 256 \
    "$HANDOFF_STAGE/artifact-review/provenance.json" | cut -d ' ' -f1)
  review_provenance_sha256="sha256:$review_provenance_sha256"
  editorial_sha256=$(shasum -a 256 \
    "$HANDOFF_STAGE/artifact-review-editorial.json" | cut -d ' ' -f1)
  editorial_sha256="sha256:$editorial_sha256"
else
  review_unavailable_sha256=$(shasum -a 256 \
    "$HANDOFF_STAGE/REVIEW_UNAVAILABLE.md" | cut -d ' ' -f1)
  review_unavailable_sha256="sha256:$review_unavailable_sha256"
fi

jq -cS -n \
  --arg source_commit "$FINAL_COMMIT" \
  --arg terminal_stage "$TERMINAL_STAGE" \
  --arg campaign_manifest_sha256 "$campaign_manifest_sha256" \
  --arg sandbox_security_record_sha256 "$sandbox_security_record_sha256" \
  --arg operator_environment_incident_sha256 "$operator_environment_incident_sha256" \
  --arg evaluation_environment_sha256 "$evaluation_environment_sha256" \
  --arg primary_dataset "$PRIMARY_DATASET" \
  --arg ablation_manifest_sha256 "$ablation_manifest_sha256" \
  --arg review_mode "$REVIEW_MODE" \
  --arg primary_manifest_sha256 "$primary_manifest_sha256" \
  --arg review_provenance_sha256 "$review_provenance_sha256" \
  --arg editorial_sha256 "$editorial_sha256" \
  --arg review_unavailable_sha256 "$review_unavailable_sha256" \
  --argjson ablation_included \
    "$(test "$ABLATION_ELIGIBLE" = true && test -n "$PRIMARY_DATASET" \
      && printf true || printf false)" \
  '{
    ablation_included: $ablation_included,
    ablation_manifest_sha256: (if $ablation_manifest_sha256 == "null" then null else $ablation_manifest_sha256 end),
    campaign_manifest_sha256: $campaign_manifest_sha256,
    editorial_sha256: (if $editorial_sha256 == "null" then null else $editorial_sha256 end),
    evaluation_environment_sha256: $evaluation_environment_sha256,
    operator_environment_incident_sha256: $operator_environment_incident_sha256,
    primary_dataset: (if $primary_dataset == "" then null else $primary_dataset end),
    primary_manifest_sha256: (if $primary_manifest_sha256 == "null" then null else $primary_manifest_sha256 end),
    review_mode: $review_mode,
    review_provenance_sha256: (if $review_provenance_sha256 == "null" then null else $review_provenance_sha256 end),
    review_unavailable_sha256: (if $review_unavailable_sha256 == "null" then null else $review_unavailable_sha256 end),
    sandbox_security_record_sha256: $sandbox_security_record_sha256,
    schema_version: "1.0",
    source_commit: $source_commit,
    terminal_stage: $terminal_stage
  }' > "$HANDOFF_STAGE/SOURCE.json"

test "$(jq -r '.source_commit' "$HANDOFF_STAGE/SOURCE.json")" = "$FINAL_COMMIT"
test "$(jq -r '.campaign_manifest_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
  "sha256:$(shasum -a 256 "$HANDOFF_STAGE/campaign/MANIFEST.sha256" | cut -d ' ' -f1)"
test "$(jq -r '.sandbox_security_record_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
  "sha256:$(shasum -a 256 "$HANDOFF_STAGE/V4_SANDBOX_SECURITY_RECORD.md" | cut -d ' ' -f1)"
test "$(jq -r '.operator_environment_incident_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
  "sha256:$(shasum -a 256 "$HANDOFF_STAGE/V4_OPERATOR_ENVIRONMENT_INCIDENT.md" | cut -d ' ' -f1)"
test "$(jq -r '.evaluation_environment_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
  "sha256:$(shasum -a 256 "$HANDOFF_STAGE/evaluation-environment.json" | cut -d ' ' -f1)"
if test -n "$PRIMARY_DATASET"; then
  test "$(jq -r '.primary_manifest_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
    "sha256:$(shasum -a 256 "$HANDOFF_STAGE/primary/sha256_manifest.json" | cut -d ' ' -f1)"
else
  test "$(jq -r '.primary_manifest_sha256' "$HANDOFF_STAGE/SOURCE.json")" = null
fi
if test "$ABLATION_ELIGIBLE" = true && test -n "$PRIMARY_DATASET"; then
  test "$(jq -r '.ablation_manifest_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
    "sha256:$(shasum -a 256 "$HANDOFF_STAGE/ablation/sha256_manifest.json" | cut -d ' ' -f1)"
else
  test "$(jq -r '.ablation_manifest_sha256' "$HANDOFF_STAGE/SOURCE.json")" = null
fi
if test "$REVIEW_MODE" = available; then
  test "$(jq -r '.review_provenance_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
    "sha256:$(shasum -a 256 "$HANDOFF_STAGE/artifact-review/provenance.json" | cut -d ' ' -f1)"
  test "$(jq -r '.editorial_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
    "sha256:$(shasum -a 256 "$HANDOFF_STAGE/artifact-review-editorial.json" | cut -d ' ' -f1)"
else
  test "$(jq -r '.review_unavailable_sha256' "$HANDOFF_STAGE/SOURCE.json")" = \
    "sha256:$(shasum -a 256 "$HANDOFF_STAGE/REVIEW_UNAVAILABLE.md" | cut -d ' ' -f1)"
fi

test -z "$(find "$HANDOFF_STAGE" -type l -print -quit)"
test -z "$(find "$HANDOFF_STAGE" ! -type d ! -type f -print -quit)"
(
  cd "$HANDOFF_STAGE"
  find . -type f ! -path './MANIFEST.sha256' -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 shasum -a 256 > MANIFEST.sha256
  shasum -a 256 --check MANIFEST.sha256
)
mv -n "$HANDOFF_STAGE" "$HANDOFF"
test -d "$HANDOFF"
test ! -e "$HANDOFF_STAGE"
chmod -R a-w "$HANDOFF"
```

Copy only this handoff into the staging site's `public/data/benchmark-v4/` layout. Pin every
non-null digest from `SOURCE.json` in the article component props, run the site's schema tests, ESLint, and
production build, and inspect the rendered article before copying to the real site or deploying.
If there is no eligible primary, do not instantiate result components that require `primary/`;
report the campaign accounting and no-head-to-head outcome directly.

## Failure summary

- **Terminal service/archive/import failure:** keep all payload sealed; recover only through the
  exact-service procedure in `V4_TRANSITION_RUNBOOK.md`.
- **No committed core gate:** allow only a terminal `core-n3` campaign, skip disclosure, and require
  the harvester to select no primary before using the allow-empty commitment.
- **Extension ineligible:** select eligible `n3`; do not cancel an eligible registered ablation.
- **No eligible primary:** select no ablation or score files, publish the allow-empty commitment,
  and make no head-to-head quality claim.
- **Gate/disclosure/harvest/evaluation mismatch:** stop without opening payload; never infer around a
  failed verifier.
- **Identity leak during blind prepare:** do not redact or retry; publish numeric results only with
  the fixed unavailability record.
- **No infrastructure-valid review packet:** publish the fixed unavailability record; do not invent
  an artifact-quality judgment.
- **Credential-like submitted output:** keep the candidate bytes private. If any required ledger or
  derived result candidate also contains credential-like material, publish no result commit; retain
  only already public commitments/incident records and treat credential rotation/host review as a
  separate incident.
- **Isolated reviewer or exact synthetic probe unavailable:** keep the mapping sealed, do not use a
  shared-filesystem agent as a blind reviewer, and publish the fixed unavailability record.
- **Applicable submitted script:** do not execute it; item 6 cannot pass.
- **Review commitment not public:** keep mapping sealed.
- **Finalize or continuity verification failure:** keep the final allowlist unstaged and publish
  nothing.
- **Evaluation recheck or publication recomputation mismatch:** preserve both trees and stop.
- **Credential-like content, unsafe type/path, or file above 95 MiB:** stop before staging; do not
  print the match or mutate the evidence.
- **Site schema/build/render failure:** keep the handoff private and do not update or deploy the
  website.

After the final commit, site handoff, and site verification all succeed, release the lock:

```bash
test -d "$FINAL_LOCK"
test -z "$(find "$FINAL_LOCK" -mindepth 1 -print -quit)"
rmdir "$FINAL_LOCK"
```
