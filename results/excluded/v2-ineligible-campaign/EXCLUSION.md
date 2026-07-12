# v2 campaign exclusion

Protocol version `2026-07-11-v2`, tag `benchmark-2026-07-11-v2`, is ineligible for every
model-quality comparison. It is not scored and none of its attempts may be merged with a later
protocol version.

The complete randomized `core-n3` schedule ran sequentially on July 11–12, 2026. It produced 18
physical attempts: six completed Codex first attempts, six Claude first attempts, and the six
identical retries required by the frozen infrastructure-failure rule. Every Claude attempt exited
before a model event with the same 93-byte diagnostic:

```text
--dangerously-skip-permissions cannot be used with root/sudo privileges for security reasons
```

The preflight smoke had not exercised the scored invocation: it omitted
`--dangerously-skip-permissions`, enabled tools, hook events, and the JSON-schema output contract.
The scored sandbox changed `USER` and `LOGNAME` to `bench` but retained effective UID 0. This is a
runner/preflight defect, not a Claude Fable 5 engineering result.

Independent raw-integrity verification then found a second exclusion. The frozen evaluation ledger
retained task-pack hashes generated with bytewise path ordering, while the v2 systemd process
generated `input.sha256` and `workspace.sha256` under the host locale because `run-one.sh` did not
set `LC_ALL` for `sort`. The task bytes are identical to the frozen protocol, but the ledger-byte
hashes differ:

| Task | Frozen pack hash | v2 physical-attempt pack hash |
|---|---|---|
| `nstf_blind_derive_duty` | `505e446c2aab398fa78bca00c400c7b85e849ba2a8b8b3cb7005cf7a7455bc37` | `43e87b07bcde86ae4832ac3ec936638fc762b6bd5e8962cdc489d2e3bbe9a815` |
| `triso_corrected_bounded_annex` | `b289430390cc2bdc6b2d176d3ac0d78a0281d634cd68211c5e83ac2ce54642e4` | `1166835be175f8a495ebf68624e3583c443066c42f100ad8f9a66126461b3bd8` |

The harvester therefore failed closed at the frozen-field boundary. Relaxing or rewriting the v2
ledger would be a post-outcome protocol change, so v2 remains excluded.

Before this exclusion was frozen, the following were inspected: systemd status and journal output;
run IDs; artifact, schedule, and whole-campaign hashes; file sizes; task-pack ledger path order; the
Claude status/metadata/environment records; one representative Claude stderr and proxy log; and
byte-equality of Claude inputs to the frozen protocol. No Codex event content, prediction, submitted
workspace output, score, or artifact-review material was opened.

The 1,316-file private preservation ledger is published as
`results/excluded/v2-ineligible-campaign.sha256`. Its SHA-256 is
`103663ec098bf4c93adc3431d275aab02766162ebbe8a09e42e9b388d37d2188`.
The raw payload remains separately preserved and will be published only after the replacement
campaign's prospective boundary no longer depends on it.

A replacement protocol must:

1. rerun all four primary cells from replicate 1;
2. set deterministic bytewise collation for every pack/workspace ledger;
3. exercise the exact scored invocation in a neutral preflight for both systems; and
4. freeze and publish a new protocol, environment manifest, tag, and randomized schedule before the
   first replacement launch.
