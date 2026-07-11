#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--system" || ( "${2:-}" != codex && "${2:-}" != claude ) || "${#}" -ne 2 ]]; then
  echo "usage: isolation-probe.sh --system codex|claude" >&2
  exit 64
fi
system=$2

if [[ -n "${BENCH_HOST_SENTINEL:-}" ]]; then
  echo "host environment crossed isolation boundary" >&2
  exit 1
fi
echo "host-environment-cleared=true"

[[ ! -e /root/bench-v2/hidden ]]
[[ ! -e /root/bench ]]
[[ ! -e /root/eng-bench ]]

if [[ "${system}" == codex ]]; then
  [[ -s /home/bench/.codex/auth.json ]]
  [[ ! -s /home/bench/.claude/.credentials.json ]]
  opposite_provider=https://api.anthropic.com
else
  [[ -s /home/bench/.claude/.credentials.json ]]
  [[ ! -s /home/bench/.codex/auth.json ]]
  opposite_provider=https://chatgpt.com
fi

if curl --silent --show-error --fail --connect-timeout 3 "${opposite_provider}" >/runtime/opposite-provider.out 2>/runtime/opposite-provider.err; then
  echo "opposite provider unexpectedly passed the allowlist" >&2
  exit 1
fi

if curl --silent --show-error --fail --connect-timeout 3 https://example.com >/runtime/example.out 2>/runtime/example.err; then
  echo "arbitrary proxied internet unexpectedly succeeded" >&2
  exit 1
fi

if curl --silent --show-error --fail --noproxy '*' --connect-timeout 3 https://1.1.1.1 >/runtime/direct.out 2>/runtime/direct.err; then
  echo "direct internet unexpectedly succeeded" >&2
  exit 1
fi

printf '%s\n' \
  'filesystem-hidden=true' \
  'selected-credential-mounted=true' \
  'other-credential-empty=true' \
  'opposite-provider-blocked=true' \
  'arbitrary-proxy-blocked=true' \
  'direct-network-blocked=true'
