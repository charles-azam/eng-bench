# Version 4 schedules

Each stage schedule is generated and hashed only after the public
`benchmark-2026-07-12-v4` tag, and is committed and pushed before that stage's first launch. The
portable `*.sha256` files use local relative paths. The `*.vps.sha256` files preserve the runner's
original absolute-path checksum records byte for byte.

The order is an unblocked deterministic shuffle using Python's
`random.Random(20260711).shuffle(...)`. It is randomized, but it is not alternating or stratified;
same-system and same-task runs can cluster. The v4 `core-n3` order matches v2 and v3 because the
matrix, seed, and shuffle implementation are unchanged. Every registered cell nevertheless
restarts from replicate 1 under the v4 environment; no predecessor attempt is reused.
