#!/usr/bin/env bash
set -euo pipefail

root=/root/bench-v2
probe_root="${root}/preflight/fable-variants"
install -d -m 700 "${probe_root}"
printf '%s\n' '{"model":"claude-fable-5","switchModelsOnFlag":true}' > "${probe_root}/settings-switch-true.json"
chmod 600 "${probe_root}/settings-switch-true.json"

run_probe() {
  local name=$1
  local model=$2
  local effort=$3
  local safe_mode=$4
  local settings=$5
  local fallback_model=$6
  local prompt=$7
  local directory="${probe_root}/${name}"
  [[ ! -e "${directory}" ]] || { echo "probe exists: ${name}" >&2; return 73; }
  install -d -m 700 "${directory}"
  printf '%s\n' "${prompt}" > "${directory}/PROMPT.md"

  local -a command=(
    claude
    --print
    --model "${model}"
    --effort "${effort}"
    --output-format stream-json
    --verbose
    --no-session-persistence
    --disable-slash-commands
    --strict-mcp-config
    --mcp-config '{"mcpServers":{}}'
    --settings "${settings}"
    --no-chrome
  )
  if [[ "${safe_mode}" == yes ]]; then
    command+=(--safe-mode)
  fi
  if [[ -n "${fallback_model}" ]]; then
    command+=(--fallback-model "${fallback_model}")
  fi
  command+=(--tools "")

  jq -n \
    --arg name "${name}" \
    --arg model "${model}" \
    --arg effort "${effort}" \
    --arg safe_mode "${safe_mode}" \
    --arg settings "${settings}" \
    --arg fallback_model "${fallback_model}" \
    --arg prompt_sha256 "$(sha256sum "${directory}/PROMPT.md" | cut -d ' ' -f1)" \
    '{name: $name, model: $model, effort: $effort, safe_mode: $safe_mode, settings: $settings, fallback_model: $fallback_model, prompt_sha256: $prompt_sha256}' \
    > "${directory}/config.json"

  set +e
  HOME=/root/bench-v2/preflight/isolated-home \
    DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    timeout --signal=TERM --kill-after=10 180 \
    "${command[@]}" \
    < "${directory}/PROMPT.md" \
    > "${directory}/events.jsonl" \
    2> "${directory}/stderr.log"
  local status=$?
  set -e
  printf '%s\n' "${status}" > "${directory}/exit-code.txt"
  sha256sum "${directory}/config.json" "${directory}/PROMPT.md" "${directory}/events.jsonl" "${directory}/stderr.log" > "${directory}/artifacts.sha256"
}

ready='Say READY.'
engineering='A flat wall is 0.20 m thick, has thermal conductivity 2.0 W/(m K), area 3.0 m^2, and a steady temperature difference of 40 K. Compute the one-dimensional conductive heat rate using Q = k A deltaT/L. Return only JSON with key heat_rate_w and a numeric value.'
fail_closed_settings="${root}/runner/claude-settings.json"
switch_true_settings="${probe_root}/settings-switch-true.json"

run_probe exact-max-safe-failclosed claude-fable-5 max yes "${fail_closed_settings}" "" "${ready}"
run_probe exact-high-safe-failclosed claude-fable-5 high yes "${fail_closed_settings}" "" "${ready}"
run_probe alias-max-safe-failclosed fable max yes "${fail_closed_settings}" "" "${ready}"
run_probe exact-max-nosafe-failclosed claude-fable-5 max no "${fail_closed_settings}" "" "${ready}"
run_probe exact-max-safe-switchtrue-fallbacksame claude-fable-5 max yes "${switch_true_settings}" claude-fable-5 "${ready}"
run_probe engineering-max-safe-failclosed claude-fable-5 max yes "${fail_closed_settings}" "" "${engineering}"

for directory in "${probe_root}"/*/; do
  name=$(basename "${directory}")
  exit_code=$(cat "${directory}/exit-code.txt")
  fallback_count=$(jq -s '[.[] | select(.type == "system" and (.subtype == "model_refusal_fallback" or .subtype == "model_fallback" or .subtype == "model_consent_fallback"))] | length' "${directory}/events.jsonl")
  refusal_count=$(jq -s '[.[] | select(.type == "system" and .subtype == "model_refusal_no_fallback")] | length' "${directory}/events.jsonl")
  actual_models=$(jq -sr '[.[] | select(.type == "assistant") | .message.model] | unique | join(",")' "${directory}/events.jsonl")
  result=$(jq -sr '[.[] | select(.type == "result") | .result] | last // ""' "${directory}/events.jsonl")
  jq -n \
    --arg name "${name}" \
    --argjson exit_code "${exit_code}" \
    --argjson fallback_count "${fallback_count}" \
    --argjson refusal_count "${refusal_count}" \
    --arg actual_models "${actual_models}" \
    --arg result "${result}" \
    '{name: $name, exit_code: $exit_code, fallback_count: $fallback_count, refusal_count: $refusal_count, actual_models: $actual_models, result: $result}'
done
