# V4 operator environment incident

Status: registered at 2026-07-12 12:53:41 UTC, after the terminal service exposed only its
content-free failure metadata and before any event stream, prediction, submitted workspace,
automatic score, neutral packet, or sealed mapping was inspected.

## What happened

While the frozen `core-n3` schedule was still running, a Codex subagent preparing a possible future
isolated artifact-review runtime executed:

```text
apt-get install -y --no-install-recommends bubblewrap
```

APT and dpkg record the install of `bubblewrap:amd64 0.11.1-1ubuntu0.1` from 12:48:43 through
12:48:47 UTC. This was an operator action, not an unattended update. The active Claude retry
`core-n3-nstf_blind_derive_duty-claude-r02-a02` had started at 12:15:35 UTC and finished inference
at 12:52:15 UTC. Its post-inference environment capture changed from the frozen SHA-256
`15559315a5072682de5ce4b0fc636c59ffdd101f5b048cac1137bd4c6f7e4bc7` to
`b243a8e57b36f77f665ff771b7c032da670cc9cd78cc57fd599ee9d52b9a9d08`. The schedule service then
failed closed at 12:52:18 UTC with exit status 65, before the last two registered retries started.

The current environment manifest has the same changed digest as the failed attempt. A simulated
purge reports that `bubblewrap` is the only package to remove. The installed package list is an
explicit field of the frozen environment manifest, so the cause of the mismatch is established
without opening either environment JSON or any model output.

The operator accepts responsibility for this intervention. The reviewer-isolation work should have
used the already vendor-pinned Bubblewrap binary or waited until campaign closure; installing a
package during an active attempt violated the frozen-host rule.

The same subagent also created the preserved public-package inspection directory
`/tmp/bwrap-help.RcBQYB/` and copied a mode-`0500` harness to
`/root/eng-bench-v4-operations/v4_isolated_review-41e2048a20abdf5c60d70145401d9b65ea64e00a275da46fc4f9fbaec0f6f164.py`.
Those paths are outside the frozen runner tree and are not fields of the environment manifest. Two
harness help attempts failed before dependency loading; no synthetic exchange, review output,
receipt, Codex inference, or benchmark payload access occurred. Both paths are preserved for
incident review and are not cleaned up mid-campaign.

## Registered handling

1. Preserve the failed main unit, its original invocation ID, and the active exact retention anchor
   until this record is public.
2. Purge only the accidentally installed `bubblewrap` package, then require a fresh content-blind
   environment capture to reproduce the frozen SHA-256 exactly.
3. Use only the already registered exact-service recovery path. The frozen planner may resume the
   two not-yet-started retries; it must not create an unregistered third attempt for the affected
   replicate or rewrite its `runner_failure` outcome.
4. Treat the affected final attempt as an infrastructure failure. Under the frozen eligibility
   rule, V4 `core-n3` cannot become an eligible scored comparison. Publish the complete campaign
   accounting and this incident; make no V4 head-to-head quality or winner claim.
5. Do not run the isolated-review harness on V4. Artifact review is unavailable, the sealed mapping
   remains unopened, and a normal shared-filesystem agent is not substituted as blind.

Any scientifically scored successor is a new benchmark version with a new preregistration. It must
run only after V4 is durably closed, must prevent package-management changes while attempts are
active, and must include this incident in its provenance rather than silently replacing V4.
