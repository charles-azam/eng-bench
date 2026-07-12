# V4 inference-sandbox security record

Status: registered at 2026-07-12 12:15:39 UTC while the frozen `core-n3` campaign was
still in its registered retry phase, before terminal archival, prediction inspection,
automatic scoring, neutral-packet preparation, or artifact review.

## Finding

The frozen inference launcher in `runner/isolate.sh` starts Bubblewrap from the root-run
campaign service without an unprivileged user mapping. It also read-only binds broad host
`/etc` state and binds the live Codex or Claude credential file into the agent home. Read-only
mounting prevents mutation; it does not prevent the agent from reading or copying those bytes
into a submitted output or provider-visible tool result.

The runner's network proxy and immutable evidence ledgers remain meaningful controls, but this
filesystem design is not a hardened secret-isolation boundary. V4 therefore must not be cited as
evidence that the native agents could not access host configuration, password hashes, SSH host
keys, or provider credentials. This audit does not establish that a model actually copied a
secret; it establishes that the frozen sandbox made such access possible.

## V4 handling

- The running frozen campaign is not mutated or silently restarted.
- Complete raw attempts, including event streams, proxy logs, runtime state, and workspaces,
  remain private rather than entering the public results commit.
- Published scores and article tables are byte-reproduced internally against that private verified
  evidence and bound by public hashes. Because the public bundle omits the complete raw attempts,
  outsiders can verify commitments and derived-file consistency but cannot independently rerun the
  full scorer from public bytes alone.
- Identity-blind packet preparation scans every submitted-output path and byte stream for
  credential-like material before a reviewer receives it. A hit fails closed without printing,
  redacting, or publishing the matching material.
- The final article and committed reviewer disclosure must state this limitation. Numeric results
  measure the two native systems under the frozen V4 environment; they do not validate the
  sandbox's confidentiality.
- Provider-credential rotation and a VPS host review are post-closure security actions. They are
  not performed mid-campaign because doing so would alter the frozen invocation environment and
  invalidate remaining attempts.

At 12:48 UTC a separate operator action nevertheless installed a package during an active retry and
triggered exactly that fail-closed invalidation. `operations/V4_OPERATOR_ENVIRONMENT_INCIDENT.md`
records the cause, restoration, recovery boundary, and resulting no-score decision. It is an
operator-integrity incident, not evidence about either model's engineering performance.

## Requirement for a hardened rerun

A security-focused successor must use an unprivileged UID/user namespace, a minimal explicit
`/etc` projection, brokered credentials that are not agent-readable, a deny-by-default filesystem
view, and regression tests that attempt to read synthetic host and provider secrets. Such a rerun
is a new benchmark version, not an undocumented repair to V4.
