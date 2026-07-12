# V4 stage-transition runbook

This is content-blind operator tooling. It may hash raw bytes and parse runner metadata, status, and
manifest records, but operators must not open event streams, predictions, or submitted workspaces
between stages. The tooling is outside the frozen `runner/` and `protocol/` trees and must never be
mounted into an agent sandbox. Its VPS copy also stays outside `/root/bench-v2`, so deployment does
not alter the frozen campaign tree.

The legal order is:

```text
terminal stage
  -> verified atomic VPS archive
  -> verified local import and immutable cumulative snapshot
  -> fresh-key gate
  -> commit and push that gate alone
  -> generate the complete next schedule on the VPS
  -> verify, commit, and push the schedule
  -> launch the next stage
```

Generating a later schedule before its preceding gate commit is public is a protocol violation.
If the registered 60-hour provider-limit rule omits the extension, stop after the core result: the
frozen stage-prefix checks do not permit launching the ablation while skipping the extension.
Run every shell block from a session that has already executed `set -euo pipefail`; the snippets
assume fail-fast shell semantics.

## Fixed stage map

| Stage | Required `a01` | Terminal service | Next stage |
|---|---:|---|---|
| `core-n3` | 12 | `eng-bench-core-n3-v4.service` | `core-extend-n5` |
| `core-extend-n5` | 8 | `eng-bench-core-extend-n5-v4.service` | `nstf-duty-ablation-n3` |
| `nstf-duty-ablation-n3` | 6 | `eng-bench-nstf-duty-ablation-n3-v4.service` | final harvest |

`operations.v4_stage_archive` derives the service and count from this closed map; they are not
caller-controlled arguments.

## 1. Create the stage archive on the VPS

After the operator commit is public, copy the exact committed script to a private root-only path on
the VPS. Verify its digest against the public checkout before using it:

```bash
TOOL_ROOT=/root/eng-bench-v4-operations
TOOL="$TOOL_ROOT/v4_stage_archive.py"
install -d -m 700 "$TOOL_ROOT"
test ! -e "$TOOL"
# Copy operations/v4_stage_archive.py from the exact public commit to $TOOL.
chmod 500 "$TOOL"
test "$(sha256sum "$TOOL" | cut -d ' ' -f1)" = \
  e9613f92c7178e37cdeb3049d08078d1a58497ab3278179f502c4a67e5194110

/root/bench-v2/runner/.venv/bin/python "$TOOL" create \
  --stage <STAGE>
```

Immediately regenerate the environment manifest after installing the tool:

```bash
environment_probe=$(mktemp)
python3 /root/bench-v2/runner/environment_manifest.py > "$environment_probe"
cmp --silent /root/bench-v2/protocol/environment.json "$environment_probe"
rm -f -- "$environment_probe"
```

The comparison must remain equal; otherwise stop for explicit incident handling.

The command fails unless all of the following hold:

- the exact registered service is inactive/dead with `Result=success`, exit status zero, and no PID;
- `/root/bench-v2/runner.lock` is free;
- the frozen runner, protocol, environment, ledger, and matrix hashes match V4;
- `verify-protocol.sh` and a new exact environment capture pass;
- the next-stage schedule is absent;
- the full registered stage schedule and its checksum pass;
- both the primary and retry resume plans are empty;
- every exact `a01` exists, every `a02` is the registered retry of an infrastructure-failed `a01`,
  and no other stage attempt exists;
- no run-tree entry is a symlink or special file and every fixed artifact ledger verifies.

It atomically publishes one non-writable directory:

```text
/root/bench-v2/archives/v4-<STAGE>/
  v4-<STAGE>.files0
  v4-<STAGE>.tree.sha256
  v4-<STAGE>.tar
  v4-<STAGE>.tar.sha256
```

The tar is uncompressed and contains regular files only. Its member order and bytes are checked
against the tree ledger before publication.

## 2. Transfer and import without opening payloads

Use durable private storage outside the repository:

```bash
VPS=167.233.53.154
STAGE=<STAGE>
PRIVATE=<DURABLE_PRIVATE_ROOT>
INCOMING="$PRIVATE/incoming/v4-$STAGE"

install -d -m 700 "$INCOMING"
scp -pr "root@$VPS:/root/bench-v2/archives/v4-$STAGE/." "$INCOMING/"

cd /Users/charlesazam/eng-bench
uv run --frozen --project operations \
  python -m operations.v4_stage_archive import \
  --stage "$STAGE" \
  --archive-directory "$INCOMING" \
  --repository-root .
```

The importer independently checks the archive file set and permissions, tar checksum, safe regular
tar members, exact NUL/tree-ledger path equality, every extracted hash, the public stage schedule,
exact run names/counts, registered retry set, and every fixed artifact ledger. It refuses an
existing run or stage ledger. Imported run trees and
`results/raw-ledgers/v4-<STAGE>.tree.sha256` are non-writable.

All validation precedes installation, but the flat `results/raw` layout requires one same-filesystem
rename per physical attempt. A host crash between those renames can leave a partial read-only import.
The importer deliberately refuses an automatic rerun in that state; preserve it and stop for explicit
incident handling rather than deleting or completing it manually.

Create a private cumulative prefix snapshot for the gate:

```bash
SNAP="$PRIVATE/snapshots/$STAGE"
test ! -e "$SNAP"
install -d -m 700 "$SNAP/raw" "$SNAP/schedules"
cp -a results/raw/. "$SNAP/raw/"
cp -a results/schedules/v4/. "$SNAP/schedules/"
chmod -R a-w "$SNAP"
```

At core closure the snapshot may contain only the core schedule. At extension closure it may
contain only core plus extension schedules. The gate also rejects any present but unclosed stage.

## 3. Create a fresh-key gate

For core:

```bash
umask 077
install -d -m 700 "$PRIVATE/gate-keys"
STAGE=core-n3
SNAP="$PRIVATE/snapshots/$STAGE"
KEY="$PRIVATE/gate-keys/core-n3.key"
GATE=results/gates/core-n3.json
SELECTED_DATASET=n3
test ! -e "$KEY" && test ! -e "$GATE"
openssl rand -out "$KEY" 32
chmod 600 "$KEY"
test "$(wc -c < "$KEY" | tr -d ' ')" = 32

uv run python -m analysis.gate_eligibility \
  --runs-root "$SNAP/raw" \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root "$SNAP/schedules" \
  --frozen-manifest protocol/frozen_manifest.sha256 \
  --commitment-key "$KEY" \
  --dataset n3 \
  --output "$GATE" \
  > "$PRIVATE/core-n3-gate.stdout"
```

For the closed extension, use a different fresh key and output
`results/gates/core-extend-n5.json`. Try the registered n5 selection first. If it fails, n3 may be
attempted with the same key and output path. The n3 call succeeds only when the extension is fully
closed, n5 is infrastructure-ineligible, and n3 remains eligible; any integrity failure still
fails closed.

```bash
STAGE=core-extend-n5
SNAP="$PRIVATE/snapshots/$STAGE"
KEY="$PRIVATE/gate-keys/core-extend-n5.key"
GATE=results/gates/core-extend-n5.json
test ! -e "$KEY" && test ! -e "$GATE"
openssl rand -out "$KEY" 32
chmod 600 "$KEY"
test "$(wc -c < "$KEY" | tr -d ' ')" = 32
! cmp --silent "$PRIVATE/gate-keys/core-n3.key" "$KEY"

if uv run python -m analysis.gate_eligibility \
  --runs-root "$SNAP/raw" \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root "$SNAP/schedules" \
  --frozen-manifest protocol/frozen_manifest.sha256 \
  --commitment-key "$KEY" \
  --dataset n5 \
  --output "$GATE" \
  > "$PRIVATE/extension-gate-n5.stdout" \
  2> "$PRIVATE/extension-gate-n5.stderr"
then
  SELECTED_DATASET=n5
else
  test ! -e "$GATE"
  uv run python -m analysis.gate_eligibility \
    --runs-root "$SNAP/raw" \
    --matrix protocol/matrix.tsv \
    --ledger protocol/evaluation_ledger.json \
    --schedules-root "$SNAP/schedules" \
    --frozen-manifest protocol/frozen_manifest.sha256 \
    --commitment-key "$KEY" \
    --dataset n3 \
    --output "$GATE" \
    > "$PRIVATE/extension-gate-n3.stdout" \
    2> "$PRIVATE/extension-gate-n3.stderr"
  SELECTED_DATASET=n3
fi
```

If both gate calls fail, stop. Do not generate the ablation schedule.

For either successfully selected gate, reproduce its canonical bytes before staging it:

```bash
RECHECK="$PRIVATE/$STAGE-gate-recheck.json"
test ! -e "$RECHECK"
uv run python -m analysis.gate_eligibility \
  --runs-root "$SNAP/raw" \
  --matrix protocol/matrix.tsv \
  --ledger protocol/evaluation_ledger.json \
  --schedules-root "$SNAP/schedules" \
  --frozen-manifest protocol/frozen_manifest.sha256 \
  --commitment-key "$KEY" \
  --dataset "$SELECTED_DATASET" \
  --output "$RECHECK" \
  > "$PRIVATE/$STAGE-gate-recheck.stdout"
cmp --silent "$GATE" "$RECHECK"
```

## 4. Commit and push the gate alone

`results/raw` is intentionally not staged at this point. Never use `git add -A`.

```bash
git add -- "$GATE"
test "$(git diff --cached --name-only)" = "$GATE"
git diff --cached --check
git commit -m "Publish V4 $STAGE eligibility gate"
test "$(git show --pretty= --name-only HEAD)" = "$GATE"
git push origin main
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

Only after the final equality check may the next schedule be generated.

## 5. Generate, verify, commit, and push the next schedule

On the VPS:

```bash
NEXT_STAGE=<core-extend-n5|nstf-duty-ablation-n3>
test ! -e "/root/bench-v2/schedules/$NEXT_STAGE.tsv"
/root/bench-v2/runner/make-schedule.sh --stage "$NEXT_STAGE" --seed 20260711
sha256sum --check --quiet "/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256"
```

Copy the schedule and its VPS checksum into private transfer storage. Install the schedule under
`results/schedules/v4/`, retain the VPS record as `*.tsv.vps.sha256`, and create a portable
`*.tsv.sha256` whose recorded path is only the schedule basename:

```bash
TRANSFER="$PRIVATE/schedule-transfer/$NEXT_STAGE"
LOCAL=results/schedules/v4
install -d -m 700 "$TRANSFER"
scp "root@$VPS:/root/bench-v2/schedules/$NEXT_STAGE.tsv" "$TRANSFER/"
scp "root@$VPS:/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256" \
  "$TRANSFER/$NEXT_STAGE.tsv.vps.sha256"

test ! -e "$LOCAL/$NEXT_STAGE.tsv"
test ! -e "$LOCAL/$NEXT_STAGE.tsv.sha256"
test ! -e "$LOCAL/$NEXT_STAGE.tsv.vps.sha256"
cp "$TRANSFER/$NEXT_STAGE.tsv" "$LOCAL/$NEXT_STAGE.tsv"
cp "$TRANSFER/$NEXT_STAGE.tsv.vps.sha256" "$LOCAL/$NEXT_STAGE.tsv.vps.sha256"

digest=$(sha256sum "$LOCAL/$NEXT_STAGE.tsv" | cut -d ' ' -f1)
printf '%s  %s\n' "$digest" "$NEXT_STAGE.tsv" > "$LOCAL/$NEXT_STAGE.tsv.sha256"

uv run python runner/make_schedule.py \
  --matrix protocol/matrix.tsv \
  --stage "$NEXT_STAGE" \
  --seed 20260711 \
  --output "$PRIVATE/$NEXT_STAGE.expected.tsv"
cmp --silent \
  "$LOCAL/$NEXT_STAGE.tsv" \
  "$PRIVATE/$NEXT_STAGE.expected.tsv"

(
  cd "$LOCAL"
  sha256sum --check --quiet "$NEXT_STAGE.tsv.sha256"
)
test "$(cat "$LOCAL/$NEXT_STAGE.tsv.vps.sha256")" = \
  "$digest  /root/bench-v2/schedules/$NEXT_STAGE.tsv"
```

Stage exactly the three schedule files, assert the staged name set, commit, push, fetch, and require
`HEAD == origin/main`:

```bash
git add -- \
  "$LOCAL/$NEXT_STAGE.tsv" \
  "$LOCAL/$NEXT_STAGE.tsv.sha256" \
  "$LOCAL/$NEXT_STAGE.tsv.vps.sha256"

git diff --cached --check
git diff --cached --name-only | LC_ALL=C sort > "$PRIVATE/schedule-index.actual"
printf '%s\n' \
  "$LOCAL/$NEXT_STAGE.tsv" \
  "$LOCAL/$NEXT_STAGE.tsv.sha256" \
  "$LOCAL/$NEXT_STAGE.tsv.vps.sha256" \
  | LC_ALL=C sort > "$PRIVATE/schedule-index.expected"
cmp --silent "$PRIVATE/schedule-index.actual" "$PRIVATE/schedule-index.expected"

git commit -m "Publish V4 $NEXT_STAGE schedule"
git push origin main
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

Only then launch the transient `Type=exec`, `Restart=no` service:

```bash
ssh root@167.233.53.154 \
  systemd-run \
  --unit="eng-bench-$NEXT_STAGE-v4.service" \
  --service-type=exec \
  --property=Restart=no \
  /root/bench-v2/runner/run-schedule.sh \
  --schedule "/root/bench-v2/schedules/$NEXT_STAGE.tsv"
```

Keep both gate keys private until the final ablation archive is closed and imported. There is no
third interstage gate because no later stage is unlocked; final harvesting determines ablation
eligibility.
