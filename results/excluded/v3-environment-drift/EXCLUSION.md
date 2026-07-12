# v3 campaign exclusion

Protocol version `2026-07-12-v3`, tag `benchmark-2026-07-12-v3`, is ineligible for
every model-quality and artifact-quality comparison. It is not scored, and none
of its attempts may be merged with or reused by a later protocol version.

The randomized `core-n3` schedule began sequentially on July 12, 2026. Its first
eight rows reached terminal runner records: seven completed and one ended in the
registered model-session-timeout class (`agent_failure`). While sequence 8,
`core-n3-triso_corrected_bounded_annex-codex-r02-a01`, was running, the host's
automatic package-upgrade service changed the frozen execution environment.

## Exact environment drift

Sequence 8 started at `2026-07-12T06:15:26Z` and ended at
`2026-07-12T06:33:02Z`. `apt-daily-upgrade.service` ran from `06:30:00Z` through
`06:30:10Z`; its package transaction ran from `06:30:03Z` through `06:30:07Z`.
It upgraded exactly these packages:

| Package | Frozen version | Installed version | Preserved frozen `.deb` SHA-256 |
|---|---|---|---|
| `curl` | `8.18.0-1ubuntu2.2` | `8.18.0-1ubuntu2.3` | `2659501a249544faa8ac1f0db91ce3aceeae6cf1b5f7424f4108641a87b8221d` |
| `libcurl4t64` | `8.18.0-1ubuntu2.2` | `8.18.0-1ubuntu2.3` | `075bd743ecb05ddfbbaa192f8cd6eebc4ae9c1e0f37d419b29c9d373d0969df4` |
| `libcurl3t64-gnutls` | `8.18.0-1ubuntu2.2` | `8.18.0-1ubuntu2.3` | `eb0044f7dac5db7863868b5dcea9d1bbbc4aaf4e0fd4ec15f75826117aa480e9` |

The observed Debian package ledger hashes to
`3589886847a7cbd95c7967bfbc4ae23fc9cf8fd3fb8697b5bf33a4b86aa3ac31`.
Replacing only those three version records with their frozen versions
reconstructs the frozen package-ledger hash exactly:
`f87d5523c4008fe36df80bf80e67f642e63384c2e926e9db40cafe00a76244eb`.
No other environment-manifest field changed.

The runner compared the environment before each inference, but sequence 8 had
already passed that check when the upgrade began. The scored sandbox read-only
bind-mounted the host's live `/usr` and `/etc`, so its filesystem environment
changed during the attempt. This record does not claim that sequence 8 used a
particular changed library; it says the frozen environment cannot be certified
for the attempt's full duration.

## Fail-closed sequence 9

At `06:33:02Z`, the scheduler invoked sequence 9,
`core-n3-nstf_blind_derive_duty-codex-r02-a01`. The frozen `run-one.sh` created
the run directory and regenerated its environment manifest. At `06:33:03Z`, the
byte comparison against the frozen manifest failed and the service exited with
status `65/DATAERR`.

The sequence-9 directory contains empty `input/` and `workspace/` directories;
`runtime/` contains only `environment.json`. The observed environment file
hashes to
`1912406609c0b8985aaacd80e2edd7acd4f2ce2ed0491ad62aa6f83408d58ded`;
the frozen environment file hashes to
`d8f61e4a46f44e4bddd4ead99a60aae1fc3090d98d5d0a6569ad87161f2da32a`.
The failure occurred before task copying, metadata creation, proxy startup,
event-stream creation, or model invocation. It is therefore preserved as a
pre-attempt runner incident, not represented as a completed physical model
attempt. Schedule rows 10 through 12 never started.

## Why the campaign was not resumed or salvaged

The frozen scheduler retries only a finalized `provider_failure` or
`runner_failure`, after all first attempts finish. Sequence 9 has no
`status.json`, and the fail-closed exit stopped the first-pass loop before the
retry phase. Its existing scaffold also prevents reuse of the same attempt ID.

Deleting or moving that scaffold, assigning an ad hoc attempt number, manually
executing the remaining rows, or adding resume logic would change the frozen
execution procedure after campaign outcomes already existed. More importantly,
none of those actions could retrospectively certify sequence 8's environment.
Rerunning sequence 8 would be a post-outcome replacement of a completed attempt,
which the reporting plan expressly prohibits. Downgrading the three packages was
therefore rejected as a salvage path: the preserved packages establish the
diagnosis, but a downgrade cannot repair the overlapping attempt and would roll
back security updates.

The only non-conditional resolution is to exclude v3 in full and restart every
registered cell from replicate 1. No v3 attempt is eligible for the replacement
campaign. Version 4 adds four operational controls:

1. freeze a new environment on the patched `8.18.0-1ubuntu2.3` packages;
2. mask `apt-daily.service`, `apt-daily-upgrade.service`, `apt-daily.timer`, and
   `apt-daily-upgrade.timer` for the campaign's full duration;
3. require an environment comparison both immediately before and immediately
   after every physical attempt; and
4. perform the pre-attempt protocol and environment checks before allocating a
   run directory, so a rejected invocation cannot consume an attempt ID or leave
   a run scaffold.

## Inspection and preservation boundary

Before the exclusion decision was frozen, inspection was limited to systemd
service state and journals; run IDs, timestamps, terminal status fields,
directory trees, file counts and sizes; apt, dpkg, and unattended-upgrade logs;
environment-manifest field comparison; package-ledger reconstruction; and
SHA-256 records. No model event content, prediction, submitted workspace output,
numeric benchmark result, score, or artifact-review material was opened.

The private raw campaign and operational evidence are preserved at
`/root/bench-v3-excluded-20260712-v3`. The private 1,823-record preservation
ledger has SHA-256
`89abfe08cbb243ef03493f9fab227ed627a0acbcec11df99cc531419f19501dd`.
Only that commitment is public now; the ledger and raw payload remain separately
preserved and will be published only after the replacement campaign's
prospective boundary no longer depends on their artifact filenames.

Relevant frozen and observed anchors are:

| Record | SHA-256 |
|---|---|
| Frozen protocol manifest | `29429843b248aa75c45cd47befa9029d2d94024144e6fcb02cc0ffe7f8bab5c3` |
| Frozen runner source manifest | `a88dada96286a036cab8407e6a43e22aa49b25530580881b6b62eb27baf946fe` |
| Frozen matrix | `27c64e324236d2659747928e466770e466814eceae6e2a07c289a5f551538c43` |
| Frozen `core-n3` schedule | `0a171af993f319992fe91a720b2d5554b4ae6751e4de7f6da402e377591fa03d` |
| Schedule checksum record | `f98499619be417a405ce661ed5e975fc802b6b50b28e32ba544dacea04df7089` |
| Frozen environment JSON | `d8f61e4a46f44e4bddd4ead99a60aae1fc3090d98d5d0a6569ad87161f2da32a` |
| Sequence-9 observed environment JSON | `1912406609c0b8985aaacd80e2edd7acd4f2ce2ed0491ad62aa6f83408d58ded` |
| Private preservation ledger | `89abfe08cbb243ef03493f9fab227ed627a0acbcec11df99cc531419f19501dd` |
