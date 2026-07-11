#!/usr/bin/env bash
set -euo pipefail

system=""
name=""
kind=ready
while (($#)); do
  case "$1" in
    --system) system="$2"; shift 2 ;;
    --name) name="$2"; shift 2 ;;
    --kind) kind="$2"; shift 2 ;;
    *) echo "usage: smoke-one.sh --system codex|claude --name SAFE_NAME [--kind ready|engineering]" >&2; exit 64 ;;
  esac
done
[[ "${system}" == codex || "${system}" == claude ]] || exit 64
[[ "${name}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || exit 64
[[ "${kind}" == ready || "${kind}" == engineering ]] || exit 64

root=/root/bench-v2
probe="${root}/preflight/${name}-${system}"
[[ ! -e "${probe}" ]] || { echo "probe already exists: ${probe}" >&2; exit 73; }
install -d -m 700 "${probe}/workspace" "${probe}/runtime"
if [[ "${kind}" == ready ]]; then
  printf '%s\n' 'Say READY.' > "${probe}/workspace/PROMPT.md"
else
  printf '%s\n' 'A flat wall is 0.20 m thick, has thermal conductivity 2.0 W/(m K), area 3.0 m^2, and a steady temperature difference of 40 K. Compute the one-dimensional conductive heat rate using Q = k A deltaT/L. Return only JSON with key heat_rate_w and a numeric value.' > "${probe}/workspace/PROMPT.md"
fi

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

set +e
timeout --signal=TERM --kill-after=10 180 \
  "${root}/runner/isolate.sh" \
  --workspace "${probe}/workspace" \
  --runtime "${probe}/runtime" \
  -- /runner/smoke-invoke.sh --system "${system}" \
  > "${probe}/events.jsonl" \
  2> "${probe}/stderr.log"
status=$?
set -e
printf '%s\n' "${status}" > "${probe}/exit-code.txt"
"${root}/runner/validate-events.sh" \
  --system "${system}" \
  --events "${probe}/events.jsonl" \
  --exit-code "${status}" \
  > "${probe}/status.json"
cat "${probe}/status.json"
