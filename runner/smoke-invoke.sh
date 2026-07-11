#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--system" || -z "${2:-}" ]]; then
  echo "usage: smoke-invoke.sh --system codex|claude" >&2
  exit 64
fi

case "$2" in
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
      --json \
      - < /workspace/PROMPT.md
    ;;
  claude)
    exec claude \
      --print \
      --model claude-fable-5 \
      --effort max \
      --output-format stream-json \
      --verbose \
      --no-session-persistence \
      --safe-mode \
      --disable-slash-commands \
      --strict-mcp-config \
      --mcp-config '{"mcpServers":{}}' \
      --settings /runner/claude-settings.json \
      --no-chrome \
      --tools "" \
      < /workspace/PROMPT.md
    ;;
  *)
    echo "unknown system: $2" >&2
    exit 64
    ;;
esac

