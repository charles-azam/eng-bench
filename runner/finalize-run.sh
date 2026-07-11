#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--run-dir" || -z "${2:-}" ]]; then
  echo "usage: finalize-run.sh --run-dir DIR" >&2
  exit 64
fi
run_dir=$(realpath "$2")
case "${run_dir}" in
  /root/bench-v2/runs/*) ;;
  *) echo "run directory must be under /root/bench-v2/runs" >&2; exit 64 ;;
esac

root=/root/bench-v2
metadata="${run_dir}/metadata.json"
events="${run_dir}/events.jsonl"
raw_status="${run_dir}/status.json"
workspace="${run_dir}/workspace"
run_id=$(jq -r .run_id "${metadata}")
system=$(jq -r .system "${metadata}")
requested_model=$(jq -r .requested_model "${metadata}")
task=$(jq -r .task "${metadata}")
task_definition="${root}/protocol/tasks/${task}/TASK.md"
classification=$(jq -r .classification "${raw_status}")
normalized="${run_dir}/predictions.jsonl"
: > "${normalized}"
: > "${run_dir}/normalization.stderr"

served_models='[]'
if [[ "${system}" == claude ]]; then
  if parsed_models=$(jq -sc '[.[] | select(.type == "assistant" and .message.model != null and .message.model != "<synthetic>") | .message.model] | unique' "${events}" 2>/dev/null); then
    served_models="${parsed_models}"
  fi
  if [[ "${served_models}" == "[]" ]] && jq -e 'select(.type == "system" and .subtype == "model_refusal_no_fallback")' "${events}" >/dev/null; then
    served_models=$(jq -cn --arg model "${requested_model}" '[ $model ]')
  fi
else
  if jq -e 'select(.type == "thread.started")' "${events}" >/dev/null 2>&1; then
    served_models=$(jq -cn --arg model "${requested_model}" '[ $model ]')
  else
    served_models='[]'
  fi
fi

canonical_status=runner_failure
normalization=not_attempted
case "${classification}" in
  complete)
    if [[ -f "${workspace}/output/predictions.json" ]]; then
      set +e
      "${root}/runner/.venv/bin/python" "${root}/runner/normalize_predictions.py" \
        --input "${workspace}/output/predictions.json" \
        --output "${normalized}" \
        --workspace "${workspace}" \
        --run-id "${run_id}" \
        --task-id "${task}" \
        --task-file "${task_definition}" \
        2> "${run_dir}/normalization.stderr"
      normalize_exit=$?
      set -e
      if [[ "${normalize_exit}" -eq 0 ]]; then
        canonical_status=completed
        normalization=passed
      else
        canonical_status=agent_failure
        normalization=failed
      fi
    else
      canonical_status=agent_failure
      normalization=missing_predictions_file
      printf '%s\n' 'workspace/output/predictions.json is missing' > "${run_dir}/normalization.stderr"
    fi
    ;;
  model_refusal)
    canonical_status=refusal
    ;;
  model_contamination)
    canonical_status=fallback_contaminated
    ;;
  agent_failure)
    canonical_status=agent_failure
    ;;
  timeout)
    if [[ "${served_models}" == "[]" ]]; then
      canonical_status=runner_failure
    else
      canonical_status=agent_failure
    fi
    ;;
  infrastructure_failure)
    if grep -Eiq 'authentication|rate.?limit|429|529|overload|transport|connection (lost|failed)|api error' "${events}" "${run_dir}/stderr.log"; then
      canonical_status=provider_failure
    else
      canonical_status=runner_failure
    fi
    ;;
  *)
    echo "unknown runner classification: ${classification}" >&2
    exit 65
    ;;
esac

if [[ "${served_models}" == "[]" && ( "${canonical_status}" == completed || "${canonical_status}" == agent_failure || "${canonical_status}" == fallback_contaminated ) ]]; then
  canonical_status=runner_failure
  normalization=no_served_model
fi

artifact_paths=$(find "${workspace}" -type f -printf '%P\n' | LC_ALL=C sort | jq -Rsc --arg run_id "${run_id}" 'split("\n")[:-1] | map($run_id + "/workspace/" + .)')
benchmark_version=$(tr -d '\n' < "${root}/protocol/VERSION")
prompt_hash=$(jq -r .prompt_sha256 "${metadata}")
pack_hash=$(sha256sum "${run_dir}/input.sha256" | cut -d ' ' -f1)
environment_hash=$(sha256sum "${root}/protocol/environment.json" | cut -d ' ' -f1)
started_at=$(jq -r .start_time "${metadata}")
ended_at=$(jq -r .end_time "${metadata}")
attempt=$(jq -r .attempt "${metadata}")
cli_version=$(jq -r .cli_version "${metadata}")
effort=$(jq -r .effort "${metadata}")

jq -cn \
  --arg run_id "${run_id}" \
  --arg benchmark_version "${benchmark_version}" \
  --arg task_variant "${task}" \
  --arg system "${system}" \
  --arg requested_model "${requested_model}" \
  --argjson served_models "${served_models}" \
  --arg cli_version "${cli_version}" \
  --arg effort "${effort}" \
  --arg started_at "${started_at}" \
  --arg ended_at "${ended_at}" \
  --argjson attempt "${attempt}" \
  --arg status "${canonical_status}" \
  --arg prompt_sha256 "sha256:${prompt_hash}" \
  --arg pack_sha256 "sha256:${pack_hash}" \
  --arg runner_image_sha256 "sha256:${environment_hash}" \
  --arg trace_path "${run_id}/events.jsonl" \
  --argjson artifact_paths "${artifact_paths}" \
  '{run_id: $run_id, benchmark_version: $benchmark_version, task_variant: $task_variant, system: $system, requested_model: $requested_model, served_models: $served_models, cli_version: $cli_version, effort: $effort, started_at: $started_at, ended_at: $ended_at, attempt: $attempt, status: $status, prompt_sha256: $prompt_sha256, pack_sha256: $pack_sha256, runner_image_sha256: $runner_image_sha256, trace_path: $trace_path, artifact_paths: $artifact_paths}' \
  > "${run_dir}/manifest.jsonl"

jq \
  --arg canonical_status "${canonical_status}" \
  --arg normalization "${normalization}" \
  --argjson served_models "${served_models}" \
  '. + {canonical_status: $canonical_status, prediction_normalization: $normalization, served_models: $served_models}' \
  "${raw_status}" > "${run_dir}/status.tmp"
mv "${run_dir}/status.tmp" "${raw_status}"
