# V4 core systemd-retention intervention

Status: content-blind operations record written while the frozen core schedule was still running,
before the terminal archive, eligibility gate, prediction inspection, scoring, or artifact review.

## Why the intervention was necessary

An adversarial audit found that a successful transient systemd service with
`CollectMode=inactive` is garbage-collected when it becomes unreferenced. On this host,
`systemctl show` for a nonexistent service still emits misleading default values equivalent to
inactive/dead success unless `LoadState` is also checked. The original archive operator therefore
had both an evidence hole and a race: an absent unit could appear successful, while a real successful
unit could disappear before archival.

The audited correction requires `LoadState=loaded` and an exact active retention dependency. A
separate transient sleep service holds a `Wants=` reference to the campaign service until the stage
archive and private import are complete. It does not enter the frozen runner tree, agent sandbox, or
task workspace.

## Live core intervention

The anchor was installed at `2026-07-12 09:21:34 UTC`, while core schedule sequence 9 was still
active. The exact command was:

```text
systemd-run --unit=eng-bench-core-n3-v4-retention.service --service-type=exec --property=Restart=no --property=Wants=eng-bench-core-n3-v4.service /usr/bin/sleep infinity
```

The content-blind identifiers and evidence are:

| Field | Value |
|---|---|
| Core unit | `eng-bench-core-n3-v4.service` |
| Core invocation | `26b6c592a5414db78a5c0f1055916ca9` |
| Core main PID at intervention | `236107` |
| Retention unit | `eng-bench-core-n3-v4-retention.service` |
| Retention invocation | `b9a4fb9f4d934de3a0e5ba848b058649` |
| Retention main PID | `269890` |
| Retention relation | `Wants=eng-bench-core-n3-v4.service` |
| Private receipt | `/root/eng-bench-v4-operations/core-n3-v4-retention.receipt` |
| Receipt SHA-256 | `a846a7bc1bd3b3d0bd1e078886e20f636ae97a5c79af1f46829b8eea98335027` |
| Receipt metadata | root:root, mode `0600`, 1,238 bytes, mtime `2026-07-12 09:21:35.919480021 UTC` |

The core invocation ID and main PID were unchanged across the intervention. A fresh environment
capture remained byte-identical to the frozen environment SHA-256
`15559315a5072682de5ce4b0fc636c59ffdd101f5b048cac1137bd4c6f7e4bc7`.

## Prospective fix for later stages

Corrective commit `3add27c2396bd3a21903706387d94c48c28f3525` publishes the hardened operator and
runbook. The content-addressed VPS operator is root-owned, mode `0500`, outside `/root/bench-v2`,
and hashes to `039e3b149b4181fdb498f112fd558a73d560dc7a56c11a3a639a990f8191f697`.

Later launches create the exact retention service from the main service's `ExecStartPre`. PID 1 has
therefore loaded the main unit, and the anchor is active, before the frozen schedule runner can
begin. Isolated scratch services verified the retention behavior, fast-success behavior, and final
cleanup; the scratch units were removed.

No event stream, prediction, submitted workspace, score, or artifact-review material was inspected
while diagnosing or applying this intervention. No frozen runner, protocol, schedule, environment,
or run payload byte was modified.
