#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: isolate.sh --system codex|claude --workspace DIR --runtime DIR -- COMMAND [ARG ...]" >&2
}

system=""
workspace=""
runtime=""
while (($#)); do
  case "$1" in
    --system)
      system="$2"
      shift 2
      ;;
    --workspace)
      workspace="$2"
      shift 2
      ;;
    --runtime)
      runtime="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      exit 64
      ;;
  esac
done

[[ "${system}" == codex || "${system}" == claude ]] || { usage; exit 64; }
[[ -n "${workspace}" && -n "${runtime}" && $# -gt 0 ]] || { usage; exit 64; }
workspace=$(realpath "${workspace}")
runtime=$(realpath "${runtime}")
case "${workspace}" in
  /root/bench-v2/runs/*/workspace|/root/bench-v2/preflight/*/workspace) ;;
  *) echo "refusing workspace outside bench-v2 run roots: ${workspace}" >&2; exit 64 ;;
esac
case "${runtime}" in
  /root/bench-v2/runs/*/runtime|/root/bench-v2/preflight/*/runtime) ;;
  *) echo "refusing runtime outside bench-v2 run roots: ${runtime}" >&2; exit 64 ;;
esac

runner_root=/root/bench-v2/runner
bwrap=/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-resources/bwrap
home_dir="${runtime}/home"
install -d -m 700 "${home_dir}/.codex" "${home_dir}/.claude"
: > "${home_dir}/.codex/auth.json"
: > "${home_dir}/.claude/.credentials.json"
: > "${home_dir}/.claude/settings.json"
credential_bind=()
if [[ "${system}" == codex ]]; then
  credential_bind=(--ro-bind /root/.codex/auth.json /home/bench/.codex/auth.json)
else
  credential_bind=(--ro-bind /root/.claude/.credentials.json /home/bench/.claude/.credentials.json)
fi

exec "${bwrap}" \
  --die-with-parent \
  --new-session \
  --clearenv \
  --unshare-pid \
  --unshare-uts \
  --unshare-ipc \
  --unshare-net \
  --ro-bind /usr /usr \
  --ro-bind /usr/local /usr/local \
  --symlink usr/bin /bin \
  --symlink usr/lib /lib \
  --symlink usr/lib64 /lib64 \
  --ro-bind /etc /etc \
  --proc /proc \
  --dev /dev \
  --tmpfs /tmp \
  --dir /home \
  --bind "${home_dir}" /home/bench \
  "${credential_bind[@]}" \
  --ro-bind "${runner_root}/claude-settings.json" /home/bench/.claude/settings.json \
  --ro-bind "${runner_root}" /runner \
  --bind "${workspace}" /workspace \
  --bind "${runtime}" /runtime \
  --chdir /workspace \
  --setenv HOME /home/bench \
  --setenv CODEX_HOME /home/bench/.codex \
  --setenv USER bench \
  --setenv LOGNAME bench \
  --setenv LANG C.UTF-8 \
  --setenv PATH /usr/local/bin:/usr/bin:/bin \
  --setenv DISABLE_AUTOUPDATER 1 \
  --setenv CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 1 \
  --setenv HTTP_PROXY http://127.0.0.1:18080 \
  --setenv HTTPS_PROXY http://127.0.0.1:18080 \
  --setenv http_proxy http://127.0.0.1:18080 \
  --setenv https_proxy http://127.0.0.1:18080 \
  --setenv NO_PROXY "" \
  --setenv no_proxy "" \
  /runner/namespace-entry.sh -- "$@"
