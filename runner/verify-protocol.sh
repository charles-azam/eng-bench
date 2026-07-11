#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--protocol" || -z "${2:-}" || "${#}" -ne 2 ]]; then
  echo "usage: verify-protocol.sh --protocol DIRECTORY" >&2
  exit 64
fi

protocol=$(realpath "${2}")
manifest="${protocol}/manifest.sha256"
[[ -f "${manifest}" ]] || { echo "protocol manifest missing" >&2; exit 65; }

(
  cd "${protocol}"
  sha256sum --check --quiet manifest.sha256
  diff -u \
    <(awk '{print $2}' manifest.sha256 | LC_ALL=C sort) \
    <(find . -type f ! -name manifest.sha256 -printf './%P\n' | LC_ALL=C sort)
)
