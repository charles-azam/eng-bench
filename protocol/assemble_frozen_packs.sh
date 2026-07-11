#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="${1:-}"
[[ -n "${output}" ]] || {
  echo "usage: assemble_frozen_packs.sh OUTPUT_DIRECTORY" >&2
  exit 64
}
[[ ! -e "${output}" ]] || {
  echo "refusing to overwrite existing output: ${output}" >&2
  exit 73
}

mkdir -p \
  "${output}/tasks/nstf_blind_derive_duty/inputs" \
  "${output}/tasks/nstf_supplied_duty/inputs" \
  "${output}/tasks/triso_corrected_bounded_annex/inputs"

cp "${repo_root}/protocol/PROMPT.md" "${output}/tasks/nstf_blind_derive_duty/PROMPT.md"
cp "${repo_root}/protocol/PROMPT.md" "${output}/tasks/nstf_supplied_duty/PROMPT.md"
cp "${repo_root}/protocol/PROMPT.md" "${output}/tasks/triso_corrected_bounded_annex/PROMPT.md"
cp "${repo_root}/tasks/nstf_blind_derive_duty/TASK.md" "${output}/tasks/nstf_blind_derive_duty/TASK.md"
cp "${repo_root}/tasks/nstf_supplied_duty/TASK.md" "${output}/tasks/nstf_supplied_duty/TASK.md"
cp "${repo_root}/tasks/triso_corrected_bounded_annex/TASK.md" "${output}/tasks/triso_corrected_bounded_annex/TASK.md"
cp "${repo_root}"/tasks/nstf_common/inputs/* "${output}/tasks/nstf_blind_derive_duty/inputs/"
cp "${repo_root}"/tasks/nstf_common/inputs/* "${output}/tasks/nstf_supplied_duty/inputs/"
cp "${repo_root}/tasks/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv" "${output}/tasks/nstf_supplied_duty/inputs/"
cp "${repo_root}"/tasks/triso_corrected_bounded_annex/inputs/* "${output}/tasks/triso_corrected_bounded_annex/inputs/"
cp "${repo_root}/protocol/matrix.tsv" "${output}/matrix.tsv"
cp "${repo_root}/protocol/validate_task_packs.sh" "${output}/validate_task_packs.sh"
cp "${repo_root}/protocol/VERSION" "${output}/VERSION"
cp "${repo_root}/protocol/environment.json" "${output}/environment.json"
printf 'protocol_version=%s\n' "$(cat "${repo_root}/protocol/VERSION")" > "${output}/FROZEN"

(
  cd "${output}"
  find . -type f ! -name manifest.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    > manifest.sha256
)
sha256sum "${output}/manifest.sha256"
