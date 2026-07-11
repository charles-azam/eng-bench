#!/usr/bin/env bash
set -euo pipefail

[[ ! -e /root/bench-v2/hidden ]]
[[ ! -e /root/bench ]]
[[ ! -e /root/eng-bench ]]

if curl --silent --show-error --fail --connect-timeout 3 https://example.com >/runtime/example.out 2>/runtime/example.err; then
  echo "arbitrary proxied internet unexpectedly succeeded" >&2
  exit 1
fi

if curl --silent --show-error --fail --noproxy '*' --connect-timeout 3 https://1.1.1.1 >/runtime/direct.out 2>/runtime/direct.err; then
  echo "direct internet unexpectedly succeeded" >&2
  exit 1
fi

printf '%s\n' 'filesystem-hidden=true' 'arbitrary-proxy-blocked=true' 'direct-network-blocked=true'

