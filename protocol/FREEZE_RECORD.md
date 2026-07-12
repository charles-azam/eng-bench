# Benchmark freeze record

- Protocol version: `2026-07-12-v4`
- Git tag: `benchmark-2026-07-12-v4`
- Frozen protocol manifest SHA-256: `a055cf5b17b64861ba393dcda607e5f4b9908ad8e044bcc182ad6cf8df080520`
- Runner source manifest SHA-256: `4866902c3c7c349e02e7870ede3d9d7a7c9912ce59230c1a167f85d261b9de7c`
- VPS environment snapshot SHA-256: `15559315a5072682de5ce4b0fc636c59ffdd101f5b048cac1137bd4c6f7e4bc7`
- Evaluator source manifest SHA-256: `9fafb9f4e87e354c77533736af0ad70f509638ca49882c2db428c4ce87dc98c2`
- V4 preflight ledger SHA-256: `4abe39afc922d238e44bd72e784354dd6a86aa4b4ccaa31bbdeb47701c96dad7`
- Canonical Debian package list SHA-256: `3589886847a7cbd95c7967bfbc4ae23fc9cf8fd3fb8697b5bf33a4b86aa3ac31`
- Schedule seed: `20260711` (intentionally retained from the preregistration)
- Frozen evaluator ledger: `protocol/evaluation_ledger.json`

The annotated tag references the complete v4 freeze commit and is pushed publicly before any v4
scored model output exists. Every stage schedule is generated from that deployed tag, committed,
and pushed before its first launch. The environment record is a hash-covered VPS and toolchain
snapshot, not an OCI image. The literal `/root/bench-v2` deployment path is retained for runner
compatibility and does not identify the protocol version.

## Excluded predecessors

Version 1 is excluded after its first scheduled process reached a defective finalizer. Version 2 is
excluded in full for the documented Claude sandbox-marker and locale-dependent ledger failures.
Their public records remain under `results/excluded/`; neither contributes to v4.

Version 3 is excluded in full after Ubuntu's unattended-upgrade transaction changed `curl`,
`libcurl4t64`, and `libcurl3t64-gnutls` from `8.18.0-1ubuntu2.2` to `.3` while schedule sequence 8
was still running against live read-only `/usr` and `/etc` bind mounts. Sequence 9 then failed its
environment comparison before task copying, metadata, events, or provider invocation. A completed
attempt cannot be replaced under the frozen retry rule, so the campaign was not resumed. Seven
completed statuses and one model-session timeout were known operationally; no v3 event content,
prediction, submitted workspace output, score, or artifact-review material was opened.

The private 1,823-record v3 preservation ledger hashes to
`89abfe08cbb243ef03493f9fab227ed627a0acbcec11df99cc531419f19501dd`.
The exact timeline, package proof, failed-directory boundary, and inspection declaration are in
`results/excluded/v3-environment-drift/EXCLUSION.md`. No v1, v2, or v3 attempt is reused in v4;
every registered cell restarts from replicate 1.

## V4 scientific and evaluator boundary

The v4 agent prompt, all three task packs, held-out measurement JSONL, evaluator source, evaluator
tests, and evaluator manifest are byte-identical to v3. The task-pack hashes remain:

- blind NSTF: `505e446c2aab398fa78bca00c400c7b85e849ba2a8b8b3cb7005cf7a7455bc37`;
- supplied-duty NSTF: `066da7206b38d3d3f43bfbd992226de0e72e072e64bd50886cc9c91e9515f65c`;
- TRISO: `b289430390cc2bdc6b2d176d3ac0d78a0281d634cd68211c5e83ac2ce54642e4`.

The prompt remains
`94bfff14534b9d741a472ee42b3ef9e54d5d72b65fb580a8df5a800788c02172`, and the frozen matrix
remains `27c64e324236d2659747928e466770e466814eceae6e2a07c289a5f551538c43`.
Only runner lifecycle integrity, the patched host snapshot, protocol version, and corresponding
metadata changed.

## Host and runner lifecycle qualification

V4 freezes the patched `.3` curl packages instead of rolling back a security update. The canonical
700-record package list is preserved as `protocol/debian_packages_v4.tsv`. Before the environment
snapshot, `apt-daily.service`, `apt-daily-upgrade.service`, `apt-daily.timer`, and
`apt-daily-upgrade.timer` were stopped and masked. Their exact masked/inactive states are part of
environment schema 1.1 and are rechecked on every capture. The separate
`unattended-upgrades.service` shutdown monitor remains enabled; reboot, manual package changes, CLI
updates, and runner-environment changes are forbidden until the final campaign archive closes.

Every physical attempt now has two independent environment captures:

1. before inference, a private temporary manifest must match before the canonical attempt
   directory can be allocated; and
2. immediately after inference, `runtime/environment-final.json` is retained in the fixed artifact
   ledger and must match again.

A post-inference mismatch or capture failure preserves the opaque raw event stream and workspace,
emits no normalized prediction, and finalizes as `runner_failure`. The public harvester independently
checks both environment artifacts and requires an exact digest-bearing failure disclosure before it
will accept such an attempt for the single registered retry.

The scheduler can resume only from the original full checksum-registered schedule. Its typed
planner hashes opaque artifacts without parsing model events or predictions, verifies strict
metadata/status/manifest agreement, requires contiguous first-attempt and eligible-retry prefixes,
and rejects corruption, identity drift, gaps, unregistered attempts, or a retry whose frozen fields
differ from its first attempt.

## Isolation and preflight evidence

The fresh v4 deployment contains a non-empty, non-symlink host canary at
`/root/bench-v2/hidden/held-out-canary.txt`. Both isolation probes first verified that the host
canary existed, then proved that the complete hidden path, host environment variables, opposite
credential, opposite provider, arbitrary proxied internet, and direct internet were absent inside
the scored bubblewrap boundary.

Codex completed a neutral readiness prompt. Fable 5 completed the registered elementary
slab-conduction readiness task. Both systems then completed the neutral checksum task through the
exact scored invocation wrapper and wrote the preregistered artifact. No probe used a benchmark
task or held-out measurement.

The first runner-suite invocation began before the Claude parity probe had written its terminal
`exit-code.txt`, so it failed one readiness assertion. That failed test log is retained in the
preflight ledger. After the neutral probe was terminal and its status/artifact were verified, the
unchanged locked runner suite passed all 19 tests. The 56-record credential-free v4 ledger commits
to the runner, duplicate byte-identical environment captures, protocol, package list, real-canary
hash, static/isolation evidence, readiness and parity artifacts, both test logs, and the two
preserved neutral classifier fixtures. Private runtime homes and credentials are excluded.

Claude events identify the actual assistant model and explicit fallbacks, so model contamination
fails closed. Current Codex JSONL records the requested model and session but does not expose an
equivalent per-message server-model identifier. Results therefore describe GPT-5.6 Sol as requested
and runner-assumed served, with exact CLI and native-binary hashes, rather than independently
verified service identity.

---

## Post-freeze restructure addendum (2026-07-12, NSTF-Bench v5)

The repository was restructured into NSTF-Bench after the v4 campaign terminated unscored. The
NSTF task-pack bytes, `protocol/PROMPT.md`, and the NSTF held-out records above are unchanged.
The TRISO task and the 28 TRISO held-out records were removed from HEAD (preserved at tag
`benchmark-2026-07-12-v4`), and the evaluator package was renamed `eng_bench` → `nstf_bench`,
so the evaluator manifest was regenerated; the current hash lives in
`protocol/evaluation_ledger.json` (`benchmark_version: 2026-07-nstf-bench-v5`) and is verified
by `tests/test_protocol_integrity.py`. Nothing in this addendum alters the frozen v4 record
above.
