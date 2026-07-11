#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--system" || -z "${2:-}" ]]; then
  echo "usage: invoke-system.sh --system codex|claude" >&2
  exit 64
fi
system=$2

case "${system}" in
  codex)
    exec codex \
      --dangerously-bypass-approvals-and-sandbox \
      exec \
      --model gpt-5.6-sol \
      --config 'model_reasoning_effort="max"' \
      --cd /workspace \
      --skip-git-repo-check \
      --ephemeral \
      --ignore-user-config \
      --ignore-rules \
      --output-schema /runner/final.schema.json \
      --output-last-message /runtime/final.json \
      --json \
      - < /workspace/PROMPT.md
    ;;
  claude)
    schema=$(jq -c . /runner/final.schema.json)
    exec claude \
      --print \
      --model claude-fable-5 \
      --effort max \
      --output-format stream-json \
      --verbose \
      --include-hook-events \
      --no-session-persistence \
      --safe-mode \
      --disable-slash-commands \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --settings /runner/claude-settings.json \
      --dangerously-skip-permissions \
      --no-chrome \
      --json-schema "${schema}" \
      --tools "Bash,Edit,Read,Write,Glob,Grep" \
      < /workspace/PROMPT.md
    ;;
  *)
    echo "unknown system: ${system}" >&2
    exit 64
    ;;
esac

