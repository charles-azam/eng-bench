#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--" ]]; then
  echo "usage: namespace-entry.sh -- COMMAND [ARG ...]" >&2
  exit 64
fi
shift

/usr/sbin/ip link set lo up
rm -f /runtime/bridge.ready
python3 /runner/unix_bridge.py \
  --socket /runtime/proxy.sock \
  --host 127.0.0.1 \
  --port 18080 \
  --ready-file /runtime/bridge.ready &
bridge_pid=$!

cleanup() {
  kill "${bridge_pid}" 2>/dev/null || true
  wait "${bridge_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _attempt in $(seq 1 100); do
  [[ -f /runtime/bridge.ready ]] && break
  sleep 0.05
done

if [[ ! -f /runtime/bridge.ready ]]; then
  echo "namespace proxy bridge failed to start" >&2
  exit 70
fi

set +e
"$@"
status=$?
set -e
exit "${status}"

