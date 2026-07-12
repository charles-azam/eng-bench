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
schedule_sha256=$(sha256sum "${schedule}" | cut -d ' ' -f1)

exec 9>/root/bench-v2/runner.lock
flock -n 9 || { echo "another schedule is running" >&2; exit 75; }
plan_file=$(mktemp /root/bench-v2/runs/.schedule-plan.XXXXXX)
cleanup() {
  rm -f -- "${plan_file}"
}
trap cleanup EXIT INT TERM

run_phase() {
  local phase=$1
  while true; do
    observed_schedule_sha256=$(sha256sum "${schedule}" | cut -d ' ' -f1)
    [[ "${observed_schedule_sha256}" == "${schedule_sha256}" ]] || {
      echo "schedule changed after checksum validation" >&2
      exit 65
    }
    /root/bench-v2/runner/.venv/bin/python \
      /root/bench-v2/runner/resume_schedule.py \
      --schedule "${schedule}" \
      --checksum "${schedule}.sha256" \
      --runs-root /root/bench-v2/runs \
      --phase "${phase}" \
      > "${plan_file}"
    [[ -s "${plan_file}" ]] || break
    IFS=$'\t' read -r sequence task system replicate stage attempt < "${plan_file}"
    if [[ "${phase}" == primary ]]; then
      printf 'starting sequence=%s task=%s system=%s replicate=%s stage=%s attempt=%s\n' \
        "${sequence}" "${task}" "${system}" "${replicate}" "${stage}" "${attempt}"
    else
      printf 'retrying infrastructure failure sequence=%s task=%s system=%s replicate=%s stage=%s attempt=%s\n' \
        "${sequence}" "${task}" "${system}" "${replicate}" "${stage}" "${attempt}"
    fi
    /root/bench-v2/runner/run-one.sh \
      --system "${system}" \
      --task "${task}" \
      --replicate "${replicate}" \
      --stage "${stage}" \
      --attempt "${attempt}"
  done
}

run_phase primary
run_phase retry
