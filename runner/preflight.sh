#!/usr/bin/env bash
set -euo pipefail

root=/root/bench-v2
bwrap=/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-resources/bwrap

printf 'timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'hostname=%s\n' "$(hostname)"
printf 'cpus=%s\n' "$(nproc)"
printf 'codex_version=%s\n' "$(codex --version)"
printf 'claude_version=%s\n' "$(claude --version)"
printf 'python_version=%s\n' "$(python3 --version 2>&1)"
printf 'docker_version=%s\n' "$(docker --version)"
[[ -x "${bwrap}" ]]
[[ -f /root/.codex/auth.json ]]
[[ -f /root/.claude/.credentials.json ]]
[[ -f "${root}/runner/claude-settings.json" ]]
jq -e '.switchModelsOnFlag == false' "${root}/runner/claude-settings.json" >/dev/null
codex login status
claude auth status | jq '{loggedIn, authMethod, apiProvider, subscriptionType}'
df -h /root
free -h
printf '%s\n' 'preflight_static=passed'

