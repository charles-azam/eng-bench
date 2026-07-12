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
    *) echo "usage: smoke-one.sh --system codex|claude --name SAFE_NAME [--kind ready|engineering|parity]" >&2; exit 64 ;;
  esac
done
[[ "${system}" == codex || "${system}" == claude ]] || exit 64
[[ "${name}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || exit 64
[[ "${kind}" == ready || "${kind}" == engineering || "${kind}" == parity ]] || exit 64

root=/root/bench-v2
if [[ "${system}" == codex ]]; then
  allowlist="${root}/runner/allowlist-codex.txt"
else
  allowlist="${root}/runner/allowlist-claude.txt"
fi
probe="${root}/preflight/${name}-${system}"
[[ ! -e "${probe}" ]] || { echo "probe already exists: ${probe}" >&2; exit 73; }
install -d -m 700 "${probe}/workspace" "${probe}/runtime"
if [[ "${kind}" == ready ]]; then
  printf '%s\n' 'Say READY.' > "${probe}/workspace/PROMPT.md"
elif [[ "${kind}" == engineering ]]; then
  printf '%s\n' 'A flat wall is 0.20 m thick, has thermal conductivity 2.0 W/(m K), area 3.0 m^2, and a steady temperature difference of 40 K. Compute the one-dimensional conductive heat rate using Q = k A deltaT/L. Return only JSON with key heat_rate_w and a numeric value.' > "${probe}/workspace/PROMPT.md"
else
  printf '%s\n' 'scored-invocation-parity-v1' > "${probe}/workspace/INPUT.txt"
  printf '%s\n' 'This is a neutral runner-parity probe, not a benchmark task. Use Read to inspect INPUT.txt. Use Bash to create the output directory and compute sha256sum INPUT.txt. Use Write to create output/parity.txt containing exactly the sha256sum output line, including the filename. Verify the file. Finish with a short confirmation that names output/parity.txt.' > "${probe}/workspace/PROMPT.md"
fi

invoke=/runner/smoke-invoke.sh
if [[ "${kind}" == parity ]]; then
  invoke=/runner/invoke-system.sh
fi

python3 "${root}/runner/connect_proxy.py" \
  --socket "${probe}/runtime/proxy.sock" \
  --allowlist "${allowlist}" \
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
  --system "${system}" \
  --workspace "${probe}/workspace" \
  --runtime "${probe}/runtime" \
  -- "${invoke}" --system "${system}" \
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

[[ "$(jq -r .classification "${probe}/status.json")" == complete ]] || exit 1
if [[ "${kind}" == parity ]]; then
  expected='a9f4f551c650380391f5a5f608c15b3b6fc4ddb988b0ed7150cc99526c0e8f4f  INPUT.txt'
  if [[ "${system}" == codex ]]; then
    jq -e 'select(.type == "turn.completed")' "${probe}/events.jsonl" >/dev/null || {
      printf '%s\n' 'Codex event stream lacks a completed turn' > "${probe}/parity-check.txt"
      exit 1
    }
  else
    jq -e '
      select(.type == "result" and .subtype == "success" and .is_error == false)
    ' "${probe}/events.jsonl" >/dev/null || {
      printf '%s\n' 'Claude event stream lacks a successful final result' > "${probe}/parity-check.txt"
      exit 1
    }
  fi
  [[ -f "${probe}/workspace/output/parity.txt" ]] || {
    printf '%s\n' 'missing output/parity.txt' > "${probe}/parity-check.txt"
    exit 1
  }
  [[ "$(cat "${probe}/workspace/output/parity.txt")" == "${expected}" ]] || {
    printf '%s\n' 'output/parity.txt did not match the independently computed checksum' > "${probe}/parity-check.txt"
    exit 1
  }
  printf '%s\n' passed > "${probe}/parity-check.txt"
fi
