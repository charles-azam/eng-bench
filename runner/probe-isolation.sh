#!/usr/bin/env bash
set -euo pipefail

root=/root/bench-v2
probe="${root}/preflight/isolation"
[[ ! -e "${probe}" ]] || { echo "probe already exists: ${probe}" >&2; exit 73; }
install -d -m 700 "${probe}/workspace" "${probe}/runtime"
python3 "${root}/runner/connect_proxy.py" \
  --socket "${probe}/runtime/proxy.sock" \
  --allowlist "${root}/runner/allowlist.txt" \
  --log "${probe}/proxy.jsonl" &
proxy_pid=$!
cleanup() {
  kill "${proxy_pid}" 2>/dev/null || true
  wait "${proxy_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
for _attempt in $(seq 1 100); do
  [[ -S "${probe}/runtime/proxy.sock" ]] && break
  sleep 0.05
done
[[ -S "${probe}/runtime/proxy.sock" ]] || exit 70
"${root}/runner/isolate.sh" \
  --workspace "${probe}/workspace" \
  --runtime "${probe}/runtime" \
  -- /runner/isolation-probe.sh \
  | tee "${probe}/result.txt"

