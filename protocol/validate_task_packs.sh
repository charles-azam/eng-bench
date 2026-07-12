#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
nstf_blind_input_root="inputs/nstf_common/inputs"
cd "$repo_root"

command -v rg >/dev/null

blind_files=(
  inputs/nstf_blind_derive_duty/TASK.md
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
  inputs/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv

echo "task-pack static validation passed"
