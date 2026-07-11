#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--stage" || -z "${2:-}" || "${3:-}" != "--seed" || -z "${4:-}" ]]; then
  echo "usage: make-schedule.sh --stage STAGE --seed SEED" >&2
  exit 64
fi
stage=$2
seed=$4
[[ "${stage}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || exit 64
[[ "${seed}" =~ ^[0-9]+$ ]] || exit 64

root=/root/bench-v2
protocol="${root}/protocol"
matrix="${protocol}/matrix.tsv"
[[ -f "${protocol}/FROZEN" && -f "${matrix}" ]] || { echo "frozen protocol or matrix missing" >&2; exit 65; }
"${root}/runner/verify-protocol.sh" --protocol "${protocol}" || exit 65
install -d -m 700 "${root}/schedules"
output="${root}/schedules/${stage}.tsv"
[[ ! -e "${output}" ]] || { echo "schedule already exists: ${output}" >&2; exit 73; }
python3 "${root}/runner/make_schedule.py" \
  --matrix "${matrix}" \
  --stage "${stage}" \
  --seed "${seed}" \
  --output "${output}"
sha256sum "${output}" > "${output}.sha256"
cat "${output}"
