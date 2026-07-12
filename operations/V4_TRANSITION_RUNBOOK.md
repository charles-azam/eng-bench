# V4 stage-transition runbook

This is content-blind operator tooling. It may hash raw bytes and parse runner metadata, status, and
manifest records, but operators must not open event streams, predictions, or submitted workspaces
between stages. The operator stays outside the frozen `runner/` and `protocol/` trees and must never
be mounted into an agent sandbox.

The only legal order is:

```text
terminal stage
  -> verified atomic VPS archive
  -> verified local import and immutable cumulative snapshot
  -> fresh-key gate
  -> commit and push that gate alone
  -> generate the complete next schedule on the VPS
  -> verify, commit, and push that schedule alone
  -> launch the next stage
```

Generating a later schedule before its preceding gate is public is a protocol violation. If the
registered 60-hour provider-limit rule omits the extension, stop after the core gate; the frozen
stage-prefix checks do not permit launching the ablation while skipping the extension.

Run the blocks below in one local Bash session after `set -euo pipefail`. Keep that session open so
the local transition lock remains held. A stale lock after a host or shell failure is an incident to
inspect, not a directory to remove reflexively.

## 0. Select the closed stage and pin public code

Set exactly one literal before starting, for example `STAGE=core-n3`:

```bash
set -euo pipefail
umask 077

REPO=/Users/charlesazam/eng-bench
PRIVATE=/Users/charlesazam/eng-bench-v4-private
VPS=167.233.53.154
STAGE=${STAGE:?set STAGE to one registered stage}

case "$STAGE" in
  core-n3)
    SERVICE=eng-bench-core-n3-v4.service
    RETENTION_SERVICE=eng-bench-core-n3-v4-retention.service
    NEXT_STAGE=core-extend-n5
    ;;
  core-extend-n5)
    SERVICE=eng-bench-core-extend-n5-v4.service
    RETENTION_SERVICE=eng-bench-core-extend-n5-v4-retention.service
    NEXT_STAGE=nstf-duty-ablation-n3
    ;;
  nstf-duty-ablation-n3)
    SERVICE=eng-bench-nstf-duty-ablation-n3-v4.service
    RETENTION_SERVICE=eng-bench-nstf-duty-ablation-n3-v4-retention.service
    NEXT_STAGE=
    ;;
  *)
    printf 'unregistered stage: %s\n' "$STAGE" >&2
    exit 64
    ;;
esac

SCHEDULE_REMOTE="/root/bench-v2/schedules/$STAGE.tsv"
TRANSITION_LOCK="$PRIVATE/transition.lock"
TOOL_SHA256=779a8f401385664f2210c4b2d01f209828b8387598880a2a1dfe308744b4f024
TOOL_ROOT_REMOTE=/root/eng-bench-v4-operations
TOOL_REMOTE="$TOOL_ROOT_REMOTE/v4_stage_archive-$TOOL_SHA256.py"

test -d "$PRIVATE"
test ! -L "$PRIVATE"
test "$(stat -f '%Su:%Sg:%Lp' "$PRIVATE")" = "$(id -un):$(id -gn):700"
for private_directory in \
  "$PRIVATE/incoming" \
  "$PRIVATE/snapshots" \
  "$PRIVATE/gate-keys" \
  "$PRIVATE/schedule-transfer" \
  "$PRIVATE/public-worktrees" \
  "$PRIVATE/transition-envs" \
  "$PRIVATE/service-incidents" \
  "$PRIVATE/gate-logs"
do
  test ! -L "$private_directory"
  install -d -m 700 "$private_directory"
  test -d "$private_directory"
  test ! -L "$private_directory"
  test "$(stat -f '%Su:%Sg:%Lp' "$private_directory")" = \
    "$(id -un):$(id -gn):700"
done

mkdir -m 700 "$TRANSITION_LOCK"
trap 'rmdir -- "$TRANSITION_LOCK"' EXIT

cd "$REPO"
test "$(git branch --show-current)" = main
git fetch origin main
PUBLIC_BASE=$(git rev-parse origin/main)
test "$(git rev-parse HEAD)" = "$PUBLIC_BASE"
git diff --quiet
git diff --cached --quiet

public_tool_sha=$(git show "$PUBLIC_BASE:operations/v4_stage_archive.py" \
  | shasum -a 256 | cut -d ' ' -f1)
test "$public_tool_sha" = "$TOOL_SHA256"
test -f operations/v4_stage_archive.py
test ! -L operations/v4_stage_archive.py
test "$(shasum -a 256 operations/v4_stage_archive.py | cut -d ' ' -f1)" = \
  "$public_tool_sha"

PINNED="$PRIVATE/public-worktrees/$STAGE-$PUBLIC_BASE"
OPS_ENV="$PRIVATE/transition-envs/$STAGE-$PUBLIC_BASE-operations"
ROOT_ENV="$PRIVATE/transition-envs/$STAGE-$PUBLIC_BASE-analysis"
for fresh_path in "$PINNED" "$OPS_ENV" "$ROOT_ENV"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
git worktree add --detach "$PINNED" "$PUBLIC_BASE"
test "$(git -C "$PINNED" rev-parse HEAD)" = "$PUBLIC_BASE"
git -C "$PINNED" diff --quiet
git -C "$PINNED" diff --cached --quiet
test -z "$(git -C "$PINNED" status --porcelain --untracked-files=all)"
test "$(shasum -a 256 "$PINNED/operations/v4_stage_archive.py" | cut -d ' ' -f1)" = \
  "$public_tool_sha"
```

The closed stage map is:

| Stage | Required `a01` | Terminal service | Retention service | Next stage |
|---|---:|---|---|---|
| `core-n3` | 12 | `eng-bench-core-n3-v4.service` | `eng-bench-core-n3-v4-retention.service` | `core-extend-n5` |
| `core-extend-n5` | 8 | `eng-bench-core-extend-n5-v4.service` | `eng-bench-core-extend-n5-v4-retention.service` | `nstf-duty-ablation-n3` |
| `nstf-duty-ablation-n3` | 6 | `eng-bench-nstf-duty-ablation-n3-v4.service` | `eng-bench-nstf-duty-ablation-n3-v4-retention.service` | final harvest |

`operations.v4_stage_archive` compiles the same map; service names and required counts are not
caller-controlled arguments. Every stage launch also creates its exact active `Wants=` retention
service. Successful transient services otherwise disappear immediately and a nonexistent unit can
report misleading inactive/dead success defaults. The retention process does not enter the agent
sandbox or frozen tree; it only keeps PID 1's exact terminal record loaded until archival. Future
launches create it in the main service's `ExecStartPre`, after PID 1 has loaded the main unit but
before the frozen schedule runner can start, eliminating the completion and SSH-gap race.

## 1. Install and verify the immutable VPS operator

Keep all variables in the local transition shell. Install the exact public script once at its
digest-qualified path. A later stage reuses that immutable path but repeats every check.

```bash
UPLOAD_REMOTE="$TOOL_REMOTE.upload-$PUBLIC_BASE"
if ssh -o BatchMode=yes "root@$VPS" \
  "test -e '$TOOL_REMOTE' || test -L '$TOOL_REMOTE'"
then
  :
else
  ssh -o BatchMode=yes "root@$VPS" \
    "test ! -L '$TOOL_ROOT_REMOTE' &&
     install -d -o root -g root -m 700 '$TOOL_ROOT_REMOTE' &&
     test ! -e '$UPLOAD_REMOTE' && test ! -L '$UPLOAD_REMOTE' &&
     test ! -e '$TOOL_REMOTE' && test ! -L '$TOOL_REMOTE'"
  scp "$PINNED/operations/v4_stage_archive.py" "root@$VPS:$UPLOAD_REMOTE"
  ssh -o BatchMode=yes "root@$VPS" \
    "test -f '$UPLOAD_REMOTE' && test ! -L '$UPLOAD_REMOTE' &&
     test \"\$(sha256sum '$UPLOAD_REMOTE' | cut -d ' ' -f1)\" = '$TOOL_SHA256' &&
     test ! -e '$TOOL_REMOTE' && test ! -L '$TOOL_REMOTE' &&
     install -o root -g root -m 500 '$UPLOAD_REMOTE' '$TOOL_REMOTE' &&
     rm -f -- '$UPLOAD_REMOTE'"
fi

ssh -o BatchMode=yes "root@$VPS" \
  "test -d '$TOOL_ROOT_REMOTE' && test ! -L '$TOOL_ROOT_REMOTE' &&
   test \"\$(stat -c '%U:%G:%a' '$TOOL_ROOT_REMOTE')\" = root:root:700 &&
   test -f '$TOOL_REMOTE' && test ! -L '$TOOL_REMOTE' &&
   test \"\$(stat -c '%U:%G:%a' '$TOOL_REMOTE')\" = root:root:500 &&
   test \"\$(sha256sum '$TOOL_REMOTE' | cut -d ' ' -f1)\" = '$TOOL_SHA256'"

vps_environment_digest=$(ssh -o BatchMode=yes "root@$VPS" \
  python3 /root/bench-v2/runner/environment_manifest.py \
  | shasum -a 256 | cut -d ' ' -f1)
test "$vps_environment_digest" = \
  15559315a5072682de5ce4b0fc636c59ffdd101f5b048cac1137bd4c6f7e4bc7
```

The following helper proves that both public checksum records and the current VPS schedule encode
the same bytes. It never opens a run payload.

```bash
verify_remote_schedule_binding() {
  local binding_stage="$1"
  local public_commit="$2"
  local relative="results/schedules/v4/$binding_stage.tsv"
  local remote="/root/bench-v2/schedules/$binding_stage.tsv"
  local digest
  local portable_hash
  local vps_record_hash

  git cat-file -e "$public_commit^{commit}"
  test "$(git ls-tree "$public_commit" -- "$relative" | awk '{print $1}')" = 100644
  test "$(git ls-tree "$public_commit" -- "$relative.sha256" | awk '{print $1}')" = 100644
  test "$(git ls-tree "$public_commit" -- "$relative.vps.sha256" | awk '{print $1}')" = \
    100644
  digest=$(git show "$public_commit:$relative" | shasum -a 256 | cut -d ' ' -f1)
  portable_hash=$(printf '%s  %s\n' "$digest" "$binding_stage.tsv" \
    | shasum -a 256 | cut -d ' ' -f1)
  vps_record_hash=$(printf '%s  %s\n' "$digest" "$remote" \
    | shasum -a 256 | cut -d ' ' -f1)
  test "$(git show "$public_commit:$relative.sha256" \
    | shasum -a 256 | cut -d ' ' -f1)" = "$portable_hash"
  test "$(git show "$public_commit:$relative.vps.sha256" \
    | shasum -a 256 | cut -d ' ' -f1)" = "$vps_record_hash"

  ssh -o BatchMode=yes "root@$VPS" \
    "set -euo pipefail
     test -f '$remote' && test ! -L '$remote'
     test -f '$remote.sha256' && test ! -L '$remote.sha256'
     test \"\$(sha256sum '$remote' | cut -d ' ' -f1)\" = '$digest'
     test \"\$(sha256sum '$remote.sha256' | cut -d ' ' -f1)\" = '$vps_record_hash'
     sha256sum --check --quiet '$remote.sha256'"
}

verify_retention_anchor() {
  local retained_service="$1"
  local retention_service="$2"

  case "$retained_service:$retention_service" in
    eng-bench-core-n3-v4.service:eng-bench-core-n3-v4-retention.service) ;;
    eng-bench-core-extend-n5-v4.service:eng-bench-core-extend-n5-v4-retention.service) ;;
    eng-bench-nstf-duty-ablation-n3-v4.service:eng-bench-nstf-duty-ablation-n3-v4-retention.service) ;;
    *) return 64 ;;
  esac

  ssh -o BatchMode=yes "root@$VPS" \
    "set -euo pipefail
     test \"\$(systemctl show --value -p LoadState '$retention_service')\" = loaded
     test \"\$(systemctl show --value -p ActiveState '$retention_service')\" = active
     test \"\$(systemctl show --value -p SubState '$retention_service')\" = running
     test \"\$(systemctl show --value -p Result '$retention_service')\" = success
     test \"\$(systemctl show --value -p ExecMainStatus '$retention_service')\" = 0
     test \"\$(systemctl show --value -p Wants '$retention_service')\" = '$retained_service'
     retention_pid=\$(systemctl show --value -p MainPID '$retention_service')
     test \"\$retention_pid\" -gt 0"
}

launch_exact_stage() {
  local launch_stage="$1"
  local launch_service="$2"
  local public_commit="$3"
  local relative="results/schedules/v4/$launch_stage.tsv"
  local remote="/root/bench-v2/schedules/$launch_stage.tsv"
  local digest
  local portable_hash
  local vps_record_hash
  local retention_service

  case "$launch_stage:$launch_service" in
    core-n3:eng-bench-core-n3-v4.service)
      retention_service=eng-bench-core-n3-v4-retention.service
      ;;
    core-extend-n5:eng-bench-core-extend-n5-v4.service)
      retention_service=eng-bench-core-extend-n5-v4-retention.service
      ;;
    nstf-duty-ablation-n3:eng-bench-nstf-duty-ablation-n3-v4.service)
      retention_service=eng-bench-nstf-duty-ablation-n3-v4-retention.service
      ;;
    *) return 64 ;;
  esac

  git fetch origin main
  test "$(git rev-parse origin/main)" = "$public_commit"
  test "$(git ls-tree "$public_commit" -- "$relative" | awk '{print $1}')" = 100644
  test "$(git ls-tree "$public_commit" -- "$relative.sha256" | awk '{print $1}')" = 100644
  test "$(git ls-tree "$public_commit" -- "$relative.vps.sha256" | awk '{print $1}')" = \
    100644
  digest=$(git show "$public_commit:$relative" | shasum -a 256 | cut -d ' ' -f1)
  portable_hash=$(printf '%s  %s\n' "$digest" "$launch_stage.tsv" \
    | shasum -a 256 | cut -d ' ' -f1)
  vps_record_hash=$(printf '%s  %s\n' "$digest" "$remote" \
    | shasum -a 256 | cut -d ' ' -f1)
  test "$(git show "$public_commit:$relative.sha256" \
    | shasum -a 256 | cut -d ' ' -f1)" = "$portable_hash"
  test "$(git show "$public_commit:$relative.vps.sha256" \
    | shasum -a 256 | cut -d ' ' -f1)" = "$vps_record_hash"

  ssh -o BatchMode=yes "root@$VPS" \
    "set -euo pipefail
     schedule='$remote'
     sidecar='$remote.sha256'
     lock=/root/bench-v2/runner.lock
     test -f \"\$schedule\" && test ! -L \"\$schedule\"
     test -f \"\$sidecar\" && test ! -L \"\$sidecar\"
     test \"\$(sha256sum \"\$schedule\" | cut -d ' ' -f1)\" = '$digest'
     test \"\$(sha256sum \"\$sidecar\" | cut -d ' ' -f1)\" = '$vps_record_hash'
     sha256sum --check --quiet \"\$sidecar\"
     environment_probe=\$(mktemp)
     trap 'rm -f -- \"\$environment_probe\"' EXIT
     python3 /root/bench-v2/runner/environment_manifest.py > \"\$environment_probe\"
     test \"\$(sha256sum \"\$environment_probe\" | cut -d ' ' -f1)\" = \
       15559315a5072682de5ce4b0fc636c59ffdd101f5b048cac1137bd4c6f7e4bc7
     test -f \"\$lock\" && test ! -L \"\$lock\"
     flock -n \"\$lock\" -c true
     test \"\$(systemctl show --value -p LoadState '$launch_service')\" = not-found
     test \"\$(systemctl show --value -p LoadState '$retention_service')\" = not-found
     systemd-run --unit='$launch_service' --service-type=exec --property=Restart=no \
       --property='ExecStartPre=/usr/bin/systemd-run --unit=$retention_service --service-type=exec --property=Restart=no --property=Wants=$launch_service /usr/bin/sleep infinity' \
       /root/bench-v2/runner/run-schedule.sh --schedule \"\$schedule\"
     test \"\$(systemctl show --value -p ActiveState '$retention_service')\" = active
     test \"\$(systemctl show --value -p SubState '$retention_service')\" = running
     test \"\$(systemctl show --value -p Wants '$retention_service')\" = '$launch_service'
     retention_pid=\$(systemctl show --value -p MainPID '$retention_service')
     test \"\$retention_pid\" -gt 0
     test \"\$(systemctl show --value -p LoadState '$launch_service')\" = loaded
     launch_active=\$(systemctl show --value -p ActiveState '$launch_service')
     launch_sub=\$(systemctl show --value -p SubState '$launch_service')
     case \"\$launch_active:\$launch_sub\" in
       active:running)
         launch_pid=\$(systemctl show --value -p MainPID '$launch_service')
         test \"\$launch_pid\" -gt 0
         ;;
       inactive:dead)
         test \"\$(systemctl show --value -p Result '$launch_service')\" = success
         test \"\$(systemctl show --value -p ExecMainStatus '$launch_service')\" = 0
         test \"\$(systemctl show --value -p MainPID '$launch_service')\" = 0
         ;;
       *) exit 65 ;;
     esac"
  verify_retention_anchor "$launch_service" "$retention_service"
}

verify_remote_schedule_binding "$STAGE" "$PUBLIC_BASE"
verify_retention_anchor "$SERVICE" "$RETENTION_SERVICE"
```

## 2. Recover only an exact failed service, if necessary

If an SSH call was ambiguous, inspect the exact mapped unit first. Active/running is already the
run; monitor it. Loaded inactive/dead success with the exact active retention service is already
complete and should be archived. Do not launch a second unit.

The helper below accepts only the closed stage map, records the pre-reset systemd metadata in
private durable storage, permits one recovery attempt, rechecks the public schedule contract, and
reuses the exact unit name with the original complete schedule. It rejects the usual successful
terminal state and accepts only systemd's exact `failed/failed` transient state. A valid active
retention service is stopped before reset; absence is accepted only on this failed path because an
`ExecStartPre` failure can prevent the anchor from being created, while systemd itself retains the
failed main unit.

```bash
recover_exact_failed_stage() {
  local recovery_stage="$1"
  local public_commit="$2"
  local recovery_service
  local recovery_retention
  local incident="$PRIVATE/service-incidents/$recovery_stage-$public_commit.txt"
  local incident_temp
  local active_state
  local sub_state
  local result
  local main_pid
  local load_state
  local retention_present

  case "$recovery_stage" in
    core-n3)
      recovery_service=eng-bench-core-n3-v4.service
      recovery_retention=eng-bench-core-n3-v4-retention.service
      ;;
    core-extend-n5)
      recovery_service=eng-bench-core-extend-n5-v4.service
      recovery_retention=eng-bench-core-extend-n5-v4-retention.service
      ;;
    nstf-duty-ablation-n3)
      recovery_service=eng-bench-nstf-duty-ablation-n3-v4.service
      recovery_retention=eng-bench-nstf-duty-ablation-n3-v4-retention.service
      ;;
    *) return 64 ;;
  esac

  git fetch origin main
  test "$(git rev-parse origin/main)" = "$public_commit"
  verify_remote_schedule_binding "$recovery_stage" "$public_commit"
  test ! -e "$incident"
  test ! -L "$incident"
  incident_temp=$(mktemp \
    "$PRIVATE/service-incidents/.$recovery_stage-$public_commit.XXXXXX")
  test -f "$incident_temp"
  test ! -L "$incident_temp"
  ssh -o BatchMode=yes "root@$VPS" \
    systemctl show "$recovery_service" \
    -p ActiveState -p SubState -p Result -p ExecMainStatus -p MainPID -p LoadState \
    > "$incident_temp"

  active_state=$(sed -n 's/^ActiveState=//p' "$incident_temp")
  sub_state=$(sed -n 's/^SubState=//p' "$incident_temp")
  result=$(sed -n 's/^Result=//p' "$incident_temp")
  main_pid=$(sed -n 's/^MainPID=//p' "$incident_temp")
  load_state=$(sed -n 's/^LoadState=//p' "$incident_temp")
  test "$active_state" = failed
  test "$sub_state" = failed
  test "$result" != success
  test "$main_pid" = 0
  test "$load_state" = loaded

  load_state=$(ssh -o BatchMode=yes "root@$VPS" \
    systemctl show --value -p LoadState "$recovery_retention")
  case "$load_state" in
    loaded)
      verify_retention_anchor "$recovery_service" "$recovery_retention"
      retention_present=yes
      ;;
    not-found)
      retention_present=no
      ;;
    *) return 65 ;;
  esac

  ssh -o BatchMode=yes "root@$VPS" \
    "test -f /root/bench-v2/runner.lock &&
     test ! -L /root/bench-v2/runner.lock &&
     flock -n /root/bench-v2/runner.lock -c true"
  chmod 400 "$incident_temp"
  test ! -e "$incident"
  test ! -L "$incident"
  mv -n "$incident_temp" "$incident"
  test ! -e "$incident_temp"
  test -f "$incident"
  test ! -L "$incident"
  if test "$retention_present" = yes; then
    ssh -o BatchMode=yes "root@$VPS" systemctl stop "$recovery_retention"
    for wait_attempt in 1 2 3 4 5 6 7 8 9 10; do
      load_state=$(ssh -o BatchMode=yes "root@$VPS" \
        systemctl show --value -p LoadState "$recovery_retention")
      if test "$load_state" = not-found; then
        break
      fi
      sleep 1
    done
    test "$load_state" = not-found
  fi
  ssh -o BatchMode=yes "root@$VPS" systemctl reset-failed "$recovery_service"
  for wait_attempt in 1 2 3 4 5 6 7 8 9 10; do
    load_state=$(ssh -o BatchMode=yes "root@$VPS" \
      systemctl show --value -p LoadState "$recovery_service")
    if test "$load_state" = not-found; then
      break
    fi
    sleep 1
  done
  test "$load_state" = not-found
  launch_exact_stage "$recovery_stage" "$recovery_service" "$public_commit"
}
```

`launch_exact_stage` performs the final schedule, sidecar, environment, lock, and service checks in
the same remote shell as `systemd-run`. If the current stage is failed, run:

```bash
recover_exact_failed_stage "$STAGE" "$PUBLIC_BASE"
```

Recovery always invokes `run-schedule.sh`, whose frozen content-blind planner resumes the complete
checksum-bound schedule. Never call `run-one.sh`, use a suffixed unit, or treat `reset-failed` as a
successful execution. If the recovered exact unit fails again, the existing incident record blocks
another automatic retry; stop for explicit incident handling.

## 3. Create, transfer, and import the terminal stage archive

Archive only after the exact service reaches inactive/dead `Result=success`, exit status zero, and
`MainPID=0`. The operator independently enforces that state and acquires the existing runner lock.

```bash
verify_remote_schedule_binding "$STAGE" "$PUBLIC_BASE"
verify_retention_anchor "$SERVICE" "$RETENTION_SERVICE"
ssh -o BatchMode=yes "root@$VPS" \
  /root/bench-v2/runner/.venv/bin/python "$TOOL_REMOTE" create \
  --stage "$STAGE"
```

The creator requires `LoadState=loaded` for the exact terminal service and the exact active retention
dependency; an unloaded or never-launched unit cannot pass as success. It also rechecks all frozen
hashes, protocol closure, the exact live environment, absence of the next schedule, both empty resume
phases, the registered retry set, safe run-tree types, every fixed artifact ledger, and source
stability. It atomically publishes one non-writable directory:

```text
/root/bench-v2/archives/v4-<STAGE>/
  v4-<STAGE>.files0
  v4-<STAGE>.tree.sha256
  v4-<STAGE>.tar
  v4-<STAGE>.tar.sha256
```

Transfer the four exact files explicitly, then execute the importer from the detached public
worktree while directing installation to the main repository:

```bash
INCOMING="$PRIVATE/incoming/v4-$STAGE"
test ! -e "$INCOMING"
test ! -L "$INCOMING"
install -d -m 700 "$INCOMING"
for archive_suffix in files0 tree.sha256 tar tar.sha256; do
  scp -p "root@$VPS:/root/bench-v2/archives/v4-$STAGE/v4-$STAGE.$archive_suffix" \
    "$INCOMING/"
done
for incoming_file in "$INCOMING"/*; do
  test -f "$incoming_file"
  test ! -L "$incoming_file"
  incoming_mode=$(stat -f '%Lp' "$incoming_file")
  test $((8#$incoming_mode & 8#222)) -eq 0
done

git fetch origin main
test "$(git rev-parse origin/main)" = "$PUBLIC_BASE"
test "$(git rev-parse HEAD)" = "$PUBLIC_BASE"
git diff --quiet
git diff --cached --quiet
test "$(git -C "$PINNED" rev-parse HEAD)" = "$PUBLIC_BASE"
git -C "$PINNED" diff --quiet
git -C "$PINNED" diff --cached --quiet
test -z "$(git -C "$PINNED" status --porcelain --untracked-files=all)"
(
  cd "$PINNED"
  env UV_PROJECT_ENVIRONMENT="$OPS_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen --project operations \
    python -m operations.v4_stage_archive import \
    --stage "$STAGE" \
    --archive-directory "$INCOMING" \
    --repository-root "$REPO"
)
```

The importer snapshots the verified tree-ledger bytes once, validates and extracts the matching tar,
rechecks the public schedule and registered retry set, then uses atomic no-replace renames for each
physical run. Imported run trees and `results/raw-ledgers/v4-<STAGE>.tree.sha256` become non-writable.
Because the repository uses a flat raw layout, a host failure between run-directory publications can
leave a partial read-only import. Preserve it and stop; do not delete or complete it manually.

Create a private cumulative prefix snapshot without opening any payload:

```bash
SNAP="$PRIVATE/snapshots/$STAGE"
test ! -e "$SNAP"
test ! -L "$SNAP"
install -d -m 700 "$SNAP/raw" "$SNAP/schedules"
cp -a "$REPO/results/raw/." "$SNAP/raw/"
cp -a "$REPO/results/schedules/v4/." "$SNAP/schedules/"
test -z "$(find "$SNAP" -type l -print -quit)"
test -z "$(find "$SNAP" ! -type d ! -type f -print -quit)"
chmod -R a-w "$SNAP"
test -d "$SNAP"
test ! -L "$SNAP"

ssh -o BatchMode=yes "root@$VPS" systemctl stop "$RETENTION_SERVICE"
```

At core closure the gate accepts only the core schedule. At extension closure it accepts only core
plus extension. Any present but unclosed stage fails closed. For `nstf-duty-ablation-n3`, stop here:
there is no third interstage gate or later schedule. The archive/import does not unlock payload
inspection; continue with the three-phase procedure in `operations/V4_FINALIZATION_RUNBOOK.md`.

## 4. Create and reproduce a fresh-key gate

This section applies only to `core-n3` and `core-extend-n5`. Re-pin the public base and prove again
that no later schedule has appeared:

```bash
test "$STAGE" != nstf-duty-ablation-n3
git fetch origin main
GATE_BASE=$(git rev-parse origin/main)
test "$GATE_BASE" = "$PUBLIC_BASE"
test "$(git rev-parse HEAD)" = "$PUBLIC_BASE"
git diff --quiet
git diff --cached --quiet
test "$(git -C "$PINNED" rev-parse HEAD)" = "$PUBLIC_BASE"
ssh -o BatchMode=yes "root@$VPS" \
  "test ! -e '/root/bench-v2/schedules/$NEXT_STAGE.tsv' &&
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv' &&
   test ! -e '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256' &&
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'"

case "$STAGE" in
  core-n3)
    KEY="$PRIVATE/gate-keys/core-n3.key"
    GATE_REL=results/gates/core-n3.json
    ;;
  core-extend-n5)
    KEY="$PRIVATE/gate-keys/core-extend-n5.key"
    GATE_REL=results/gates/core-extend-n5.json
    ;;
  *) exit 64 ;;
esac
GATE="$REPO/$GATE_REL"
LOG_PREFIX="$PRIVATE/gate-logs/$STAGE-$PUBLIC_BASE"
for fresh_path in "$KEY" "$GATE" \
  "$LOG_PREFIX-primary.stdout" "$LOG_PREFIX-primary.stderr" \
  "$LOG_PREFIX-fallback.stdout" "$LOG_PREFIX-fallback.stderr" \
  "$LOG_PREFIX-recheck.stdout" "$LOG_PREFIX-recheck.stderr"
do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done

openssl rand -out "$KEY" 32
chmod 600 "$KEY"
test -f "$KEY"
test ! -L "$KEY"
test "$(stat -f '%Lp' "$KEY")" = 600
test "$(wc -c < "$KEY" | tr -d ' ')" = 32

run_gate() {
  local dataset="$1"
  local output="$2"
  local stdout_path="$3"
  local stderr_path="$4"
  (
    cd "$PINNED" &&
    test "$(git rev-parse HEAD)" = "$PUBLIC_BASE" &&
    git diff --quiet &&
    git diff --cached --quiet &&
    test -z "$(git status --porcelain --untracked-files=all)" &&
    env UV_PROJECT_ENVIRONMENT="$ROOT_ENV" PYTHONDONTWRITEBYTECODE=1 \
      uv run --frozen python -m analysis.gate_eligibility \
      --runs-root "$SNAP/raw" \
      --matrix protocol/matrix.tsv \
      --ledger protocol/evaluation_ledger.json \
      --schedules-root "$SNAP/schedules" \
      --frozen-manifest protocol/frozen_manifest.sha256 \
      --commitment-key "$KEY" \
      --dataset "$dataset" \
      --output "$output"
  ) > "$stdout_path" 2> "$stderr_path"
}
```

For core, select n3. For the closed extension, try the registered n5 selection first. If it fails,
the n3 call succeeds only when extension closure is valid, n5 is infrastructure-ineligible, and n3
remains eligible; it recomputes the full campaign rather than trusting the first error text.

```bash
if test "$STAGE" = core-n3; then
  SELECTED_DATASET=n3
  run_gate n3 "$GATE" \
    "$LOG_PREFIX-primary.stdout" "$LOG_PREFIX-primary.stderr"
else
  CORE_KEY="$PRIVATE/gate-keys/core-n3.key"
  test -f "$CORE_KEY"
  test ! -L "$CORE_KEY"
  if cmp --silent "$CORE_KEY" "$KEY"; then
    printf 'extension key equals core key\n' >&2
    exit 65
  else
    cmp_status=$?
    test "$cmp_status" = 1
  fi

  if run_gate n5 "$GATE" \
    "$LOG_PREFIX-primary.stdout" "$LOG_PREFIX-primary.stderr"
  then
    SELECTED_DATASET=n5
  else
    test ! -e "$GATE"
    test ! -L "$GATE"
    run_gate n3 "$GATE" \
      "$LOG_PREFIX-fallback.stdout" "$LOG_PREFIX-fallback.stderr"
    SELECTED_DATASET=n3
  fi
fi
test -f "$GATE"
test ! -L "$GATE"

RECHECK="$PRIVATE/$STAGE-$PUBLIC_BASE-gate-recheck.json"
test ! -e "$RECHECK"
test ! -L "$RECHECK"
run_gate "$SELECTED_DATASET" "$RECHECK" \
  "$LOG_PREFIX-recheck.stdout" "$LOG_PREFIX-recheck.stderr"
test -f "$RECHECK"
test ! -L "$RECHECK"
cmp --silent "$GATE" "$RECHECK"
```

If both extension calls fail, stop. Do not generate the ablation schedule.

## 5. Commit and push the gate alone

`results/raw` is deliberately not staged. Never use `git add -A`.

```bash
ssh -o BatchMode=yes "root@$VPS" \
  "test ! -e '/root/bench-v2/schedules/$NEXT_STAGE.tsv' &&
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv' &&
   test ! -e '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256' &&
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'"

cd "$REPO"
git fetch origin main
test "$(git rev-parse origin/main)" = "$GATE_BASE"
test "$(git rev-parse HEAD)" = "$GATE_BASE"
test "$(git branch --show-current)" = main
git diff --quiet
git diff --cached --quiet
gate_sha=$(shasum -a 256 "$GATE" | cut -d ' ' -f1)
git add -- "$GATE_REL"
test "$(git diff --cached --name-only)" = "$GATE_REL"
git diff --cached --check
git commit -m "Publish V4 $STAGE eligibility gate"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = 2
test "$(git rev-parse HEAD^)" = "$GATE_BASE"
test "$(git diff-tree --no-commit-id --name-only -r HEAD)" = "$GATE_REL"
test "$(git ls-tree HEAD -- "$GATE_REL" | awk '{print $1}')" = 100644
test "$(git show "HEAD:$GATE_REL" | shasum -a 256 | cut -d ' ' -f1)" = "$gate_sha"
git push origin main
git fetch origin main
GATE_COMMIT=$(git rev-parse HEAD)
test "$GATE_COMMIT" = "$(git rev-parse origin/main)"
test "$(git rev-parse "$GATE_COMMIT^")" = "$PUBLIC_BASE"
```

Only this equality unlocks generation of the next schedule.

## 6. Generate, copy, and reproduce the next schedule

Generate on the VPS only after the gate commit is public:

```bash
ssh -o BatchMode=yes "root@$VPS" \
  "set -euo pipefail
   test ! -e '/root/bench-v2/schedules/$NEXT_STAGE.tsv'
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv'
   test ! -e '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'
   /root/bench-v2/runner/make-schedule.sh --stage '$NEXT_STAGE' --seed 20260711 >/dev/null
   test -f '/root/bench-v2/schedules/$NEXT_STAGE.tsv'
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv'
   test -f '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'
   test ! -L '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'
   sha256sum --check --quiet '/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256'"

TRANSFER="$PRIVATE/schedule-transfer/$NEXT_STAGE-$GATE_COMMIT"
LOCAL_REL=results/schedules/v4
LOCAL="$REPO/$LOCAL_REL"
test -d "$LOCAL"
test ! -L "$LOCAL"
test ! -e "$TRANSFER"
test ! -L "$TRANSFER"
install -d -m 700 "$TRANSFER"
scp "root@$VPS:/root/bench-v2/schedules/$NEXT_STAGE.tsv" "$TRANSFER/"
scp "root@$VPS:/root/bench-v2/schedules/$NEXT_STAGE.tsv.sha256" \
  "$TRANSFER/$NEXT_STAGE.tsv.vps.sha256"

for local_path in \
  "$LOCAL/$NEXT_STAGE.tsv" \
  "$LOCAL/$NEXT_STAGE.tsv.sha256" \
  "$LOCAL/$NEXT_STAGE.tsv.vps.sha256"
do
  test ! -e "$local_path"
  test ! -L "$local_path"
done
cp "$TRANSFER/$NEXT_STAGE.tsv" "$LOCAL/$NEXT_STAGE.tsv"
cp "$TRANSFER/$NEXT_STAGE.tsv.vps.sha256" "$LOCAL/$NEXT_STAGE.tsv.vps.sha256"
digest=$(shasum -a 256 "$LOCAL/$NEXT_STAGE.tsv" | cut -d ' ' -f1)
printf '%s  %s\n' "$digest" "$NEXT_STAGE.tsv" > "$LOCAL/$NEXT_STAGE.tsv.sha256"

PINNED_GATE="$PRIVATE/public-worktrees/$STAGE-gate-$GATE_COMMIT"
SCHEDULE_ENV="$PRIVATE/transition-envs/$STAGE-$GATE_COMMIT-schedule"
EXPECTED="$PRIVATE/$NEXT_STAGE-$GATE_COMMIT.expected.tsv"
for fresh_path in "$PINNED_GATE" "$SCHEDULE_ENV" "$EXPECTED"; do
  test ! -e "$fresh_path"
  test ! -L "$fresh_path"
done
git worktree add --detach "$PINNED_GATE" "$GATE_COMMIT"
test "$(git -C "$PINNED_GATE" rev-parse HEAD)" = "$GATE_COMMIT"
git -C "$PINNED_GATE" diff --quiet
git -C "$PINNED_GATE" diff --cached --quiet
test -z "$(git -C "$PINNED_GATE" status --porcelain --untracked-files=all)"
(
  cd "$PINNED_GATE"
  test "$(git rev-parse HEAD)" = "$GATE_COMMIT"
  git diff --quiet
  git diff --cached --quiet
  test -z "$(git status --porcelain --untracked-files=all)"
  env UV_PROJECT_ENVIRONMENT="$SCHEDULE_ENV" PYTHONDONTWRITEBYTECODE=1 \
    uv run --frozen python runner/make_schedule.py \
    --matrix protocol/matrix.tsv \
    --stage "$NEXT_STAGE" \
    --seed 20260711 \
    --output "$EXPECTED"
)
cmp --silent "$LOCAL/$NEXT_STAGE.tsv" "$EXPECTED"

(
  cd "$LOCAL"
  sha256sum --check --quiet "$NEXT_STAGE.tsv.sha256"
)
expected_vps_record_hash=$(printf '%s  %s\n' "$digest" \
  "/root/bench-v2/schedules/$NEXT_STAGE.tsv" | shasum -a 256 | cut -d ' ' -f1)
test "$(shasum -a 256 "$LOCAL/$NEXT_STAGE.tsv.vps.sha256" | cut -d ' ' -f1)" = \
  "$expected_vps_record_hash"
for local_path in \
  "$LOCAL/$NEXT_STAGE.tsv" \
  "$LOCAL/$NEXT_STAGE.tsv.sha256" \
  "$LOCAL/$NEXT_STAGE.tsv.vps.sha256"
do
  test -f "$local_path"
  test ! -L "$local_path"
done
```

## 7. Commit the schedule and bind its public bytes to launch

Stage exactly three files and prove the commit has one parent, one exact path set, regular Git modes,
and the locally verified blobs:

```bash
cd "$REPO"
git fetch origin main
SCHEDULE_BASE=$(git rev-parse origin/main)
test "$SCHEDULE_BASE" = "$GATE_COMMIT"
test "$(git rev-parse HEAD)" = "$GATE_COMMIT"
test "$(git branch --show-current)" = main
git diff --quiet
git diff --cached --quiet

SCHEDULE_REL="$LOCAL_REL/$NEXT_STAGE.tsv"
PORTABLE_REL="$SCHEDULE_REL.sha256"
VPS_SIDECAR_REL="$SCHEDULE_REL.vps.sha256"
schedule_sha=$(shasum -a 256 "$REPO/$SCHEDULE_REL" | cut -d ' ' -f1)
portable_sha=$(shasum -a 256 "$REPO/$PORTABLE_REL" | cut -d ' ' -f1)
vps_sidecar_sha=$(shasum -a 256 "$REPO/$VPS_SIDECAR_REL" | cut -d ' ' -f1)
git add -- "$SCHEDULE_REL" "$PORTABLE_REL" "$VPS_SIDECAR_REL"
git diff --cached --check
actual_paths=$(git diff --cached --name-only | LC_ALL=C sort)
expected_paths=$(printf '%s\n' "$SCHEDULE_REL" "$PORTABLE_REL" "$VPS_SIDECAR_REL" \
  | LC_ALL=C sort)
test "$actual_paths" = "$expected_paths"

git commit -m "Publish V4 $NEXT_STAGE schedule"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = 2
test "$(git rev-parse HEAD^)" = "$SCHEDULE_BASE"
test "$(git diff-tree --no-commit-id --name-only -r HEAD | LC_ALL=C sort)" = \
  "$expected_paths"
for committed_path in "$SCHEDULE_REL" "$PORTABLE_REL" "$VPS_SIDECAR_REL"; do
  test "$(git ls-tree HEAD -- "$committed_path" | awk '{print $1}')" = 100644
done
test "$(git show "HEAD:$SCHEDULE_REL" | shasum -a 256 | cut -d ' ' -f1)" = \
  "$schedule_sha"
test "$(git show "HEAD:$PORTABLE_REL" | shasum -a 256 | cut -d ' ' -f1)" = \
  "$portable_sha"
test "$(git show "HEAD:$VPS_SIDECAR_REL" | shasum -a 256 | cut -d ' ' -f1)" = \
  "$vps_sidecar_sha"
git push origin main
git fetch origin main
SCHEDULE_COMMIT=$(git rev-parse HEAD)
test "$SCHEDULE_COMMIT" = "$(git rev-parse origin/main)"
test "$(git rev-parse "$SCHEDULE_COMMIT^")" = "$GATE_COMMIT"
```

The exact launch helper defined in section 1 validates public blobs locally, then binds them to the
remote launch in one fail-fast shell:

```bash
case "$NEXT_STAGE" in
  core-extend-n5) NEXT_SERVICE=eng-bench-core-extend-n5-v4.service ;;
  nstf-duty-ablation-n3) NEXT_SERVICE=eng-bench-nstf-duty-ablation-n3-v4.service ;;
  *) exit 64 ;;
esac
launch_exact_stage "$NEXT_STAGE" "$NEXT_SERVICE" "$SCHEDULE_COMMIT"
ssh -o BatchMode=yes "root@$VPS" \
  systemctl show "$NEXT_SERVICE" \
  -p ActiveState -p SubState -p Result -p ExecMainStatus -p MainPID -p LoadState
```

If the launch SSH result is ambiguous, inspect that exact `NEXT_SERVICE`. An active unit is the
launch; monitor it. Loaded inactive/dead success with the exact active retention service is already
a completed launch and proceeds to archival. If it is exactly failed/failed, call
`recover_exact_failed_stage "$NEXT_STAGE" "$SCHEDULE_COMMIT"`. The recovery helper remaps the new
stage internally, so it cannot reuse the just-closed stage's service or schedule by mistake.

Keep both gate keys private until the final ablation archive is closed and imported. Final
content-blind harvesting determines ablation eligibility, but neither harvesting nor archival
unlocks payload inspection. Follow `operations/V4_FINALIZATION_RUNBOOK.md`: publish the evaluation-
byte commitment before neutral packet preparation, and publish the completed-review commitment
before unsealing identities or inspecting results.
