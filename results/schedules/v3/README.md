# Version 3 schedules

Each stage schedule is generated and hashed only after the public
`benchmark-2026-07-12-v3` tag, and is committed and pushed before that stage's first launch. The
portable `*.sha256` files use local relative paths. The `*.vps.sha256` files preserve the runner's
original absolute-path checksum records byte for byte.

The order is an unblocked deterministic shuffle using Python's
`random.Random(20260711).shuffle(...)`. It is randomized, but it is not alternating or stratified;
same-system and same-task runs can cluster. The v3 `core-n3` order matches v2 because the matrix,
seed, and shuffle implementation are unchanged. All executions nevertheless restart from replicate
1 under v3; no v2 attempt is reused.
