#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--system" || ( "${2:-}" != codex && "${2:-}" != claude ) || "${#}" -ne 2 ]]; then
  echo "usage: probe-isolation.sh --system codex|claude" >&2
  exit 64
fi
system=$2

root=/root/bench-v2
probe="${root}/preflight/isolation-v3-${system}"
[[ ! -e "${probe}" ]] || { echo "probe already exists: ${probe}" >&2; exit 73; }
install -d -m 700 "${probe}/workspace" "${probe}/runtime"
python3 "${root}/runner/connect_proxy.py" \
  --socket "${probe}/runtime/proxy.sock" \
  --allowlist "${root}/runner/allowlist-${system}.txt" \
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
BENCH_HOST_SENTINEL=must-not-cross "${root}/runner/isolate.sh" \
  --system "${system}" \
  --workspace "${probe}/workspace" \
  --runtime "${probe}/runtime" \
  -- /runner/isolation-probe.sh --system "${system}" \
  | tee "${probe}/result.txt"
