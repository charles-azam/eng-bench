# Version 2 schedules

Each stage schedule is generated and hashed before that stage's first launch. The portable
`*.sha256` files use local relative paths. The `*.vps.sha256` files preserve the runner's original
absolute-path checksum records byte for byte.

The order is an unblocked deterministic shuffle using Python's
`random.Random(20260711).shuffle(...)`. It is randomized, but it is not alternating or stratified;
same-system and same-task runs can cluster.
