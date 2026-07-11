#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--schedule" || -z "${2:-}" ]]; then
  echo "usage: run-schedule.sh --schedule FILE" >&2
  exit 64
fi
schedule=$(realpath "$2")
case "${schedule}" in
  /root/bench-v2/schedules/*.tsv) ;;
  *) echo "schedule must be under /root/bench-v2/schedules" >&2; exit 64 ;;
esac
sha256sum --check --quiet "${schedule}.sha256" || exit 65

exec 9>/root/bench-v2/runner.lock
flock -n 9 || { echo "another schedule is running" >&2; exit 75; }
declare -a retry_rows=()
while IFS=$'\t' read -r sequence task system replicate stage; do
  [[ "${sequence}" == sequence ]] && continue
  printf 'starting sequence=%s task=%s system=%s replicate=%s stage=%s\n' "${sequence}" "${task}" "${system}" "${replicate}" "${stage}"
  /root/bench-v2/runner/run-one.sh \
    --system "${system}" \
    --task "${task}" \
    --replicate "${replicate}" \
    --stage "${stage}" \
    --attempt 1
  status_file="/root/bench-v2/runs/${stage}-${task}-${system}-r$(printf '%02d' "${replicate}")-a01/status.json"
  classification=$(jq -r .classification "${status_file}")
  if [[ "${classification}" == infrastructure_failure ]]; then
    retry_rows+=("${sequence}"$'\t'"${task}"$'\t'"${system}"$'\t'"${replicate}"$'\t'"${stage}")
  fi
done < "${schedule}"

for row in "${retry_rows[@]}"; do
  IFS=$'\t' read -r sequence task system replicate stage <<< "${row}"
  printf 'retrying infrastructure failure sequence=%s task=%s system=%s replicate=%s stage=%s\n' "${sequence}" "${task}" "${system}" "${replicate}" "${stage}"
  /root/bench-v2/runner/run-one.sh \
    --system "${system}" \
    --task "${task}" \
    --replicate "${replicate}" \
    --stage "${stage}" \
    --attempt 2
done
