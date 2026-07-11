#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "${script_dir}/tasks/nstf_blind_derive_duty" ]]; then
  repo_root="${script_dir}"
  nstf_blind_input_root="tasks/nstf_blind_derive_duty/inputs"
else
  repo_root="$(cd "${script_dir}/.." && pwd)"
  nstf_blind_input_root="tasks/nstf_common/inputs"
fi
cd "$repo_root"

command -v rg >/dev/null

blind_files=(
  tasks/nstf_blind_derive_duty/TASK.md
  "${nstf_blind_input_root}/01_geometry.md"
  "${nstf_blind_input_root}/02_materials.md"
  "${nstf_blind_input_root}/03_measurement_locations.md"
  "${nstf_blind_input_root}/04_electrical_cases.md"
  "${nstf_blind_input_root}/accident_electric_power.csv"
)

for path in "${blind_files[@]}"; do
  test -f "$path"
done

numeric_leaks='(?<![0-9.])(?:26\.16|56\.07|56\.12|54\.49|51\.7|48\.6)(?![0-9])'
text_leaks='65% efficiency|68% efficiency'

if rg --line-number --pcre2 "$numeric_leaks|$text_leaks" "${blind_files[@]}"; then
  echo "blind NSTF pack contains a held-out thermal-duty or response token" >&2
  exit 1
fi

awk -F, '
  BEGIN {
    coefficient[0] = 466.531039994
    coefficient[1] = 0.078631095079
    coefficient[2] = 0.000170562320568
    coefficient[3] = -1.28449427566e-7
    coefficient[4] = 5.09424812301e-11
    coefficient[5] = -1.27606140005e-14
    coefficient[6] = 2.04789514471e-18
    coefficient[7] = -2.08318254453e-22
    coefficient[8] = 1.29530038954e-26
    coefficient[9] = -4.48601180685e-31
    coefficient[10] = 6.462156403603905e-36
  }
  FNR > 1 {
    minutes = $1 * 60.0
    polynomial = coefficient[10]
    for (power = 9; power >= 0; power--) {
      polynomial = polynomial * minutes + coefficient[power]
    }
    expected = polynomial * 90.0 / 1000.0
    difference = $2 - expected
    if (difference < 0) {
      difference = -difference
    }
    if (difference > 0.000002) {
      printf "reconstructed electric curve mismatch at t=%s h: table=%s expected=%.9f\n", $1, $2, expected > "/dev/stderr"
      failed = 1
    }
  }
  END {
    exit failed
  }
' "${nstf_blind_input_root}/accident_electric_power.csv"

awk -F, '
  NR == FNR {
    if (FNR > 1) {
      electrical[$1] = $2
    }
    next
  }
  FNR > 1 && $1 == "accident" {
    expected = $3 / 56.07 * 90.0
    difference = electrical[$2] - expected
    if (difference < 0) {
      difference = -difference
    }
    if (difference > 0.000002) {
      printf "curve mismatch at t=%s h: electric=%s expected=%.6f\n", $2, electrical[$2], expected > "/dev/stderr"
      failed = 1
    }
  }
  END {
    exit failed
  }
' "${nstf_blind_input_root}/accident_electric_power.csv" \
  tasks/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv

triso_files=(
  tasks/triso_corrected_bounded_annex/TASK.md
  tasks/triso_corrected_bounded_annex/inputs/01_particles_and_elements.md
  tasks/triso_corrected_bounded_annex/inputs/02_cases.md
  tasks/triso_corrected_bounded_annex/inputs/03_bounded_material_annex.md
)

for path in "${triso_files[@]}"; do
  test -f "$path"
done

triso_result_leaks='1\.8e-6|1\.1e-4|6\.5e-4|5\.9e-2|9\.9e-4|3\.9e-3|5\.4e-7|2\.6e-4|4\.0e-2'
if rg --line-number --pcre2 "$triso_result_leaks" "${triso_files[@]}"; then
  echo "TRISO pack contains a held-out release token" >&2
  exit 1
fi

rg --quiet --fixed-strings '5.5e-14 * exp(Gamma / 5)' \
  tasks/triso_corrected_bounded_annex/inputs/03_bounded_material_annex.md
rg --quiet --fixed-strings '1.6e-2 * exp(-514000 / (R*T))' \
  tasks/triso_corrected_bounded_annex/inputs/03_bounded_material_annex.md
rg --quiet --fixed-strings '926.892 MPa' \
  tasks/triso_corrected_bounded_annex/inputs/03_bounded_material_annex.md

if rg --line-number --fixed-strings '1.6e-15' "${triso_files[@]}"; then
  echo "TRISO pack contains the superseded second Arrhenius prefactor" >&2
  exit 1
fi

echo "task-pack static validation passed"
