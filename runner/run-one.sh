#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: run-one.sh --system codex|claude --task TASK --replicate N --stage STAGE [--attempt N]" >&2
}

system=""
task=""
replicate=""
stage=""
attempt=1
while (($#)); do
  case "$1" in
    --system) system="$2"; shift 2 ;;
    --task) task="$2"; shift 2 ;;
    --replicate) replicate="$2"; shift 2 ;;
    --stage) stage="$2"; shift 2 ;;
    --attempt) attempt="$2"; shift 2 ;;
    *) usage; exit 64 ;;
  esac
done

[[ "${system}" == codex || "${system}" == claude ]] || { usage; exit 64; }
[[ "${task}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { usage; exit 64; }
[[ "${replicate}" =~ ^[1-9][0-9]*$ ]] || { usage; exit 64; }
[[ "${attempt}" =~ ^[1-9][0-9]*$ ]] || { usage; exit 64; }
[[ "${stage}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { usage; exit 64; }

root=/root/bench-v2
protocol="${root}/protocol"
task_dir="${protocol}/tasks/${task}"
[[ -f "${protocol}/FROZEN" ]] || { echo "protocol is not frozen" >&2; exit 65; }
[[ -f "${protocol}/manifest.sha256" ]] || { echo "protocol manifest missing" >&2; exit 65; }
[[ -f "${protocol}/VERSION" ]] || { echo "protocol version missing" >&2; exit 65; }
[[ -f "${protocol}/environment.json" ]] || { echo "frozen environment manifest missing" >&2; exit 65; }
"${root}/runner/verify-protocol.sh" --protocol "${protocol}" || { echo "protocol file-set or hash validation failed" >&2; exit 65; }
[[ -f "${task_dir}/PROMPT.md" ]] || { echo "task prompt missing: ${task}" >&2; exit 66; }

run_id="${stage}-${task}-${system}-r$(printf '%02d' "${replicate}")-a$(printf '%02d' "${attempt}")"
run_dir="${root}/runs/${run_id}"
[[ ! -e "${run_dir}" ]] || { echo "run already exists: ${run_id}" >&2; exit 73; }
install -d -m 700 "${run_dir}/input" "${run_dir}/workspace" "${run_dir}/runtime"
python3 "${root}/runner/environment_manifest.py" > "${run_dir}/runtime/environment.json"
cmp --silent "${protocol}/environment.json" "${run_dir}/runtime/environment.json" || { echo "runtime environment differs from frozen manifest" >&2; exit 65; }
cp -a "${task_dir}/." "${run_dir}/input/"
cp -a "${task_dir}/." "${run_dir}/workspace/"
(cd "${run_dir}/input" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "${run_dir}/input.sha256"

start_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [[ "${system}" == codex ]]; then
  cli_version=$(codex --version)
  requested_model=gpt-5.6-sol
else
  cli_version=$(claude --version)
  requested_model=claude-fable-5
fi
prompt_hash=$(sha256sum "${run_dir}/input/PROMPT.md" | cut -d ' ' -f1)
protocol_hash=$(sha256sum "${protocol}/manifest.sha256" | cut -d ' ' -f1)
jq -n \
  --arg run_id "${run_id}" \
  --arg system "${system}" \
  --arg requested_model "${requested_model}" \
  --arg cli_version "${cli_version}" \
  --arg effort max \
  --arg stage "${stage}" \
  --arg task "${task}" \
  --argjson replicate "${replicate}" \
  --argjson attempt "${attempt}" \
  --arg start_time "${start_time}" \
  --arg prompt_sha256 "${prompt_hash}" \
  --arg protocol_manifest_sha256 "${protocol_hash}" \
  '{run_id: $run_id, system: $system, requested_model: $requested_model, cli_version: $cli_version, effort: $effort, stage: $stage, task: $task, replicate: $replicate, attempt: $attempt, start_time: $start_time, prompt_sha256: $prompt_sha256, protocol_manifest_sha256: $protocol_manifest_sha256}' \
  > "${run_dir}/metadata.json"

python3 "${root}/runner/connect_proxy.py" \
  --socket "${run_dir}/runtime/proxy.sock" \
  --allowlist "${root}/runner/allowlist.txt" \
  --log "${run_dir}/proxy.jsonl" \
  > "${run_dir}/runtime/proxy.stdout" \
  2> "${run_dir}/runtime/proxy.stderr" &
proxy_pid=$!
cleanup() {
  kill "${proxy_pid}" 2>/dev/null || true
  wait "${proxy_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
for _attempt in $(seq 1 100); do
  [[ -S "${run_dir}/runtime/proxy.sock" ]] && break
  sleep 0.05
done
[[ -S "${run_dir}/runtime/proxy.sock" ]] || { echo "provider proxy failed to start" >&2; exit 70; }

set +e
timeout --signal=INT --kill-after=900 3600 \
  "${root}/runner/isolate.sh" \
  --workspace "${run_dir}/workspace" \
  --runtime "${run_dir}/runtime" \
  -- /runner/invoke-system.sh --system "${system}" \
  > "${run_dir}/events.jsonl" \
  2> "${run_dir}/stderr.log"
exit_code=$?
set -e
end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)

"${root}/runner/validate-events.sh" \
  --system "${system}" \
  --events "${run_dir}/events.jsonl" \
  --exit-code "${exit_code}" \
  > "${run_dir}/status.json"
jq --arg end_time "${end_time}" '. + {end_time: $end_time}' "${run_dir}/metadata.json" > "${run_dir}/metadata.tmp"
mv "${run_dir}/metadata.tmp" "${run_dir}/metadata.json"
(cd "${run_dir}/workspace" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "${run_dir}/workspace.sha256"
"${root}/runner/finalize-run.sh" --run-dir "${run_dir}"
sha256sum "${run_dir}/metadata.json" "${run_dir}/events.jsonl" "${run_dir}/stderr.log" "${run_dir}/proxy.jsonl" "${run_dir}/status.json" "${run_dir}/manifest.jsonl" "${run_dir}/predictions.jsonl" > "${run_dir}/artifact.sha256"
chmod -R go-rwx "${run_dir}/runtime"
cat "${run_dir}/status.json"
