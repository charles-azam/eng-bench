# V4 blinded artifact-review plan

Status: registered at 2026-07-12 10:36:07 UTC while the frozen `core-n3` schedule was still
running, before terminal archival, gate selection, prediction inspection, automatic scoring, review
packet preparation, or mapping access.

Isolation amendment: registered at 2026-07-12 12:49:15 UTC while the same `core-n3` retry was still
running and before terminal archival or any result inspection. It rejected a normal
shared-workspace subagent as technically blind and required an exact prompt-only runtime probe.
That probe never ran. The later public `V4_OPERATOR_ENVIRONMENT_INCIDENT.md` supersedes the planned
review path: V4 artifact review is unavailable, no neutral bundle or sealed mapping will be created,
and no substantive blinded-review claim will be published.

## Reviewer and independence disclosure

The planned primary item-level artifact reviewer was OpenAI Codex, acting under Charles Azam's
request to execute the overnight benchmark plan. No eligible isolated runtime was established
before the operator incident. A normal Codex subagent shares the benchmark filesystem and is not
treated as technically blind, so the planned review will not occur for V4.

No primary pass, second pass, or adjudication will be reported. The fixed public unavailability
record will identify the technical reason and will not imply human or model review.

The final public results will include a fixed review-unavailability disclosure recording:

- that no primary or second review occurred;
- that no mapping was created or opened;
- that no independent human reviewer participated.

## Judgment rules

Every infrastructure-valid physical attempt prepared by `analysis.blind_review` receives all eight
registered item judgments. The reviewer uses only `pass`, `partial`, `fail`, or `not_applicable`,
with a concrete rationale.

Item 6 passes only when cited files were verified and no submitted script is applicable. An
adversarial pre-results audit found that the proposed offline runner exposed too much host state and
lacked adequate resource and receipt isolation, so it was withdrawn before review. No submitted
script will be executed in this campaign. A packet with an applicable script therefore receives
`partial` or `fail`, with the rationale stating that cited files were inspected but the script was
not run; code that merely looks plausible is not an execution pass.

Item 8 is `not_applicable` when the submitted artifact contains no access-attempt evidence. It can
never pass from an artifact-only packet. Any `partial` or `fail` rationale begins with
`Submitted artifact evidence:` as required by the frozen review tool.

## Withdrawn script runner

Before any review packet existed, I built and tested a digest-addressed prototype for offline script
execution using synthetic input only. An independent adversarial audit found that its root-UID
Bubblewrap process could read host secrets such as `/etc/ssh/ssh_host_ed25519_key` through an overly
broad read-only `/etc` bind. It also lacked sufficiently strong resource limits and receipt
continuity for arbitrary submitted code. The prototype was never committed, never received a V4
artifact, and was removed from the VPS at 2026-07-12 11:18:25 UTC. The conservative item 6 policy
above replaces it.

A later pre-results audit found the same class of root-UID and broad-host-mount weakness in the
already frozen inference sandbox itself. `operations/V4_SANDBOX_SECURITY_RECORD.md` records that
separate campaign limitation and the mandatory submitted-output credential scan. It does not alter
item judgments except that a credential-like hit prevents any packet from reaching the reviewer.

## Failed-blinding contingency

Packet preparation deliberately fails if a submitted artifact contains an explicit identity token
or credential-like material. Credential detection takes priority when both are present. If either
occurs, no file will be redacted or rewritten and no unblinded substitute rubric will be invented.
A public failure record will identify the class of preparation check and artifact review will be
reported as unavailable without printing the match. Eligible deterministic numeric evaluation may
still be published, but no substantive artifact-review conclusion will be claimed.

The same fail-closed rule applies because the exact isolated runtime and synthetic probe were
unavailable. No sealed mapping is created, a shared-filesystem reviewer is not substituted, and the
fixed `reviewer-isolation-unavailable` record accompanies the campaign accounting.
