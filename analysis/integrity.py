from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import TypeVar, cast

from pydantic import BaseModel

from analysis.models import (
    HarvestedAttempt,
    IntegrityRecord,
    RunMetadata,
    RunnerClassification,
    RunStatusRecord,
)
from eng_bench.models import FrozenLedger, Prediction, RunManifest, RunStatus, Sha256


ModelT = TypeVar("ModelT", bound=BaseModel)

CHECKSUM_LINE = re.compile(pattern=r"^(?P<digest>[0-9a-f]{64})  (?P<path>[^\r\n]+)$")
ARTIFACT_PATHS: tuple[str, ...] = (
    "metadata.json",
    "events.jsonl",
    "stderr.log",
    "proxy.jsonl",
    "status.json",
    "manifest.jsonl",
    "predictions.jsonl",
    "input.sha256",
    "workspace.sha256",
    "normalization.stderr",
    "runtime/environment.json",
    "runtime/environment-final.json",
)
POST_INFERENCE_ENVIRONMENT_MARKERS: dict[str, str] = {
    "mismatched": "post_inference_environment_mismatched",
    "capture_failed": "post_inference_environment_capture_failed",
}
INFRASTRUCTURE_STATUSES: frozenset[RunStatus] = frozenset(
    {RunStatus.PROVIDER_FAILURE, RunStatus.RUNNER_FAILURE}
)
CLASSIFICATION_STATUSES: dict[RunnerClassification, frozenset[RunStatus]] = {
    RunnerClassification.COMPLETE: frozenset(
        {RunStatus.COMPLETED, RunStatus.AGENT_FAILURE, RunStatus.RUNNER_FAILURE}
    ),
    RunnerClassification.MODEL_REFUSAL: frozenset(
        {RunStatus.REFUSAL, RunStatus.RUNNER_FAILURE}
    ),
    RunnerClassification.MODEL_CONTAMINATION: frozenset(
        {RunStatus.FALLBACK_CONTAMINATED, RunStatus.RUNNER_FAILURE}
    ),
    RunnerClassification.AGENT_FAILURE: frozenset(
        {RunStatus.AGENT_FAILURE, RunStatus.RUNNER_FAILURE}
    ),
    RunnerClassification.TIMEOUT: frozenset(
        {RunStatus.AGENT_FAILURE, RunStatus.RUNNER_FAILURE}
    ),
    RunnerClassification.INFRASTRUCTURE_FAILURE: frozenset(
        {RunStatus.PROVIDER_FAILURE, RunStatus.RUNNER_FAILURE}
    ),
}


def sha256_file(*, path: Path) -> Sha256:
    digest = hashlib.sha256()
    with path.open(mode="rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return cast(Sha256, f"sha256:{digest.hexdigest()}")


def require_regular_non_symlink(*, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def validate_no_symlinks(*, root: Path) -> None:
    if root.is_symlink():
        raise ValueError(f"symlink is forbidden: {root}")
    if not root.is_dir():
        raise ValueError(f"expected directory: {root}")
    for directory, directory_names, file_names in root.walk(
        top_down=True,
        follow_symlinks=False,
    ):
        for name in directory_names + file_names:
            candidate = directory / name
            if candidate.is_symlink():
                raise ValueError(f"symlink is forbidden: {candidate}")


def regular_tree_files(*, root: Path) -> tuple[str, ...]:
    validate_no_symlinks(root=root)
    relative_paths: list[str] = []
    for directory, _, file_names in root.walk(top_down=True, follow_symlinks=False):
        for name in file_names:
            candidate = directory / name
            relative_path = candidate.relative_to(root).as_posix()
            if not candidate.is_file():
                raise ValueError(f"tree entry is not a regular file: {relative_path!r}")
            relative_paths.append(relative_path)
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError(f"tree discovery produced duplicate files under {root}")
    return tuple(sorted(relative_paths))


def parse_checksum_lines(*, ledger_path: Path) -> tuple[tuple[str, str], ...]:
    require_regular_non_symlink(path=ledger_path, label="checksum ledger")
    text = ledger_path.read_text(encoding="utf-8")
    if not text or not text.endswith("\n"):
        raise ValueError(f"checksum ledger must be non-empty and newline-terminated: {ledger_path}")
    entries: list[tuple[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = CHECKSUM_LINE.fullmatch(string=line)
        if match is None:
            raise ValueError(f"invalid checksum line {line_number} in {ledger_path}")
        entries.append((match.group("path"), match.group("digest")))
    paths = [path for path, _ in entries]
    if len(paths) != len(set(paths)):
        raise ValueError(f"duplicate path in checksum ledger: {ledger_path}")
    return tuple(entries)


def normalize_tree_ledger_path(*, raw_path: str, ledger_path: Path) -> str:
    if not raw_path.startswith("./"):
        raise ValueError(f"tree checksum path must start with './' in {ledger_path}: {raw_path!r}")
    relative_path = raw_path.removeprefix("./")
    parsed = PurePosixPath(relative_path)
    if (
        not relative_path
        or parsed.is_absolute()
        or parsed.as_posix() != relative_path
        or ".." in parsed.parts
        or "\\" in relative_path
    ):
        raise ValueError(f"invalid relative checksum path in {ledger_path}: {raw_path!r}")
    return relative_path


def verify_tree_ledger(*, tree_root: Path, ledger_path: Path) -> tuple[str, ...]:
    entries = parse_checksum_lines(ledger_path=ledger_path)
    normalized = tuple(
        normalize_tree_ledger_path(raw_path=raw_path, ledger_path=ledger_path)
        for raw_path, _ in entries
    )
    actual_paths = regular_tree_files(root=tree_root)
    if tuple(sorted(normalized)) != actual_paths:
        missing = sorted(set(actual_paths) - set(normalized))
        unexpected = sorted(set(normalized) - set(actual_paths))
        raise ValueError(
            f"checksum ledger file-set mismatch for {tree_root}: "
            f"unrecorded_files={missing!r}, missing_files={unexpected!r}"
        )
    mismatches = [
        relative_path
        for relative_path, (_, digest) in zip(normalized, entries, strict=True)
        if sha256_file(path=tree_root / relative_path).removeprefix("sha256:") != digest
    ]
    if mismatches:
        raise ValueError(f"checksum mismatch under {tree_root}: {mismatches!r}")
    return actual_paths


def verify_artifact_ledger(*, run_directory: Path, run_id: str) -> None:
    ledger_path = run_directory / "artifact.sha256"
    require_regular_non_symlink(path=ledger_path, label="artifact checksum ledger")
    entries = parse_checksum_lines(ledger_path=ledger_path)
    expected_vps_paths = tuple(
        f"/root/bench-v2/runs/{run_id}/{relative_path}" for relative_path in ARTIFACT_PATHS
    )
    recorded_paths = tuple(path for path, _ in entries)
    if recorded_paths != expected_vps_paths:
        missing = sorted(set(expected_vps_paths) - set(recorded_paths))
        unexpected = sorted(set(recorded_paths) - set(expected_vps_paths))
        raise ValueError(
            f"artifact checksum ledger file-set mismatch for {run_id!r}: "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )
    mismatches: list[str] = []
    for relative_path, (_, digest) in zip(ARTIFACT_PATHS, entries, strict=True):
        artifact_path = run_directory / relative_path
        require_regular_non_symlink(path=artifact_path, label="checksummed artifact")
        if sha256_file(path=artifact_path).removeprefix("sha256:") != digest:
            mismatches.append(relative_path)
    if mismatches:
        raise ValueError(f"artifact checksum mismatch for {run_id!r}: {mismatches!r}")


def load_single_jsonl(*, path: Path, model_type: type[ModelT]) -> ModelT:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError(f"expected exactly one JSONL record in {path}, found {len(lines)}")
    return model_type.model_validate_json(lines[0])


def load_jsonl(*, path: Path, model_type: type[ModelT]) -> list[ModelT]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [model_type.model_validate_json(line) for line in lines]


def expected_run_id(*, metadata: RunMetadata) -> str:
    return (
        f"{metadata.stage}-{metadata.task}-{metadata.system}"
        f"-r{metadata.replicate:02d}-a{metadata.attempt:02d}"
    )


def validate_frozen_fields(
    *, metadata: RunMetadata, manifest: RunManifest, ledger: FrozenLedger
) -> None:
    issues: list[str] = []
    if manifest.benchmark_version != ledger.benchmark_version:
        issues.append("benchmark_version")
    if manifest.prompt_sha256 != ledger.prompt_sha256:
        issues.append("prompt_sha256")
    if manifest.runner_image_sha256 != ledger.runner_image_sha256:
        issues.append("runner_image_sha256")
    expected_pack = ledger.task_pack_sha256.get(metadata.task)
    if expected_pack is None or manifest.pack_sha256 != expected_pack:
        issues.append("pack_sha256")
    expected_system = ledger.systems.get(metadata.system)
    if expected_system is None:
        issues.append("system")
    else:
        if metadata.requested_model != expected_system.requested_model:
            issues.append("requested_model")
        if metadata.cli_version != expected_system.cli_version:
            issues.append("cli_version")
        if metadata.effort != expected_system.effort:
            issues.append("effort")
    if issues:
        raise ValueError(f"run {metadata.run_id!r} violates frozen fields: {sorted(issues)!r}")


def validate_runtime_environments(
    *,
    run_directory: Path,
    metadata: RunMetadata,
    status: RunStatusRecord,
    manifest: RunManifest,
    predictions: list[Prediction],
) -> None:
    initial_environment_path = run_directory / "runtime" / "environment.json"
    final_environment_path = run_directory / "runtime" / "environment-final.json"
    initial_environment_sha256 = sha256_file(path=initial_environment_path)
    final_environment_sha256 = sha256_file(path=final_environment_path)
    if manifest.runner_image_sha256 != initial_environment_sha256:
        raise ValueError(f"runtime environment hash mismatch: {metadata.run_id!r}")

    initial_environment = initial_environment_path.read_bytes()
    final_environment = final_environment_path.read_bytes()
    environments_match = initial_environment == final_environment
    marker = status.prediction_normalization
    failure_kind = next(
        (
            kind
            for kind, expected_marker in POST_INFERENCE_ENVIRONMENT_MARKERS.items()
            if marker == expected_marker
        ),
        None,
    )
    if marker.startswith("post_inference_environment_") and failure_kind is None:
        raise ValueError(
            f"unknown post-inference environment marker for {metadata.run_id!r}: "
            f"{marker!r}"
        )

    if failure_kind is None:
        if (
            not environments_match
            or final_environment_sha256 != manifest.runner_image_sha256
        ):
            raise ValueError(
                "post-inference runtime environment differs without a canonical "
                f"failure disclosure: {metadata.run_id!r}"
            )
        return

    if manifest.status is not RunStatus.RUNNER_FAILURE:
        raise ValueError(
            "post-inference environment failure must be canonical runner_failure: "
            f"{metadata.run_id!r}"
        )
    if predictions:
        raise ValueError(
            "post-inference environment failure contains normalized predictions: "
            f"{metadata.run_id!r}"
        )
    if failure_kind == "mismatched" and environments_match:
        raise ValueError(
            "post-inference environment mismatch marker contradicts identical "
            f"captures: {metadata.run_id!r}"
        )

    expected_disclosure = (
        f"post-inference environment verification={failure_kind}; "
        f"frozen_sha256={initial_environment_sha256.removeprefix('sha256:')}; "
        f"observed_sha256={final_environment_sha256.removeprefix('sha256:')}; "
        "raw inference artifacts preserved; predictions not normalized\n"
    )
    actual_disclosure = run_directory.joinpath("normalization.stderr").read_text(
        encoding="utf-8"
    )
    if actual_disclosure != expected_disclosure:
        raise ValueError(
            "post-inference environment disclosure does not match the captured "
            f"artifacts: {metadata.run_id!r}"
        )


def validate_run_consistency(
    *,
    run_directory: Path,
    metadata: RunMetadata,
    status: RunStatusRecord,
    manifest: RunManifest,
    predictions: list[Prediction],
    input_paths: tuple[str, ...],
    workspace_paths: tuple[str, ...],
    ledger: FrozenLedger,
) -> None:
    calculated_run_id = expected_run_id(metadata=metadata)
    if run_directory.name != calculated_run_id or metadata.run_id != calculated_run_id:
        raise ValueError(
            f"run-id mismatch: directory={run_directory.name!r}, "
            f"metadata={metadata.run_id!r}, expected={calculated_run_id!r}"
        )
    if metadata.attempt > 2:
        raise ValueError(f"only one infrastructure retry is permitted: {metadata.run_id!r}")

    field_pairs: tuple[tuple[str, object, object], ...] = (
        ("run_id", manifest.run_id, metadata.run_id),
        ("task_variant", manifest.task_variant, metadata.task),
        ("system", manifest.system, metadata.system),
        ("requested_model", manifest.requested_model, metadata.requested_model),
        ("cli_version", manifest.cli_version, metadata.cli_version),
        ("effort", manifest.effort, metadata.effort),
        ("attempt", manifest.attempt, metadata.attempt),
        ("started_at", manifest.started_at, metadata.start_time),
        ("ended_at", manifest.ended_at, metadata.end_time),
        ("status", manifest.status, status.canonical_status),
        ("served_models", manifest.served_models, status.served_models),
    )
    mismatched_fields = [
        name
        for name, manifest_value, metadata_value in field_pairs
        if manifest_value != metadata_value
    ]
    if mismatched_fields:
        raise ValueError(
            f"metadata/manifest/status mismatch for {metadata.run_id!r}: "
            f"{mismatched_fields!r}"
        )
    if manifest.status not in CLASSIFICATION_STATUSES[status.classification]:
        raise ValueError(
            f"raw classification {status.classification.value!r} cannot produce "
            f"status {manifest.status.value!r} for {metadata.run_id!r}"
        )
    if metadata.end_time < metadata.start_time:
        raise ValueError(f"negative run duration: {metadata.run_id!r}")

    prompt_path = run_directory / "input" / "PROMPT.md"
    if "PROMPT.md" not in input_paths:
        raise ValueError(f"input pack lacks PROMPT.md: {metadata.run_id!r}")
    actual_prompt = sha256_file(path=prompt_path).removeprefix("sha256:")
    if metadata.prompt_sha256 != actual_prompt:
        raise ValueError(f"metadata prompt hash mismatch: {metadata.run_id!r}")
    input_ledger_hash = sha256_file(path=run_directory / "input.sha256")
    if manifest.pack_sha256 != input_ledger_hash:
        raise ValueError(f"manifest pack hash mismatch: {metadata.run_id!r}")
    validate_runtime_environments(
        run_directory=run_directory,
        metadata=metadata,
        status=status,
        manifest=manifest,
        predictions=predictions,
    )

    expected_trace = f"{metadata.run_id}/events.jsonl"
    if manifest.trace_path != expected_trace:
        raise ValueError(f"trace path mismatch: {metadata.run_id!r}")
    expected_artifact_paths = [
        f"{metadata.run_id}/workspace/{relative_path}" for relative_path in workspace_paths
    ]
    if manifest.artifact_paths != expected_artifact_paths:
        raise ValueError(f"workspace artifact path coverage mismatch: {metadata.run_id!r}")

    prediction_keys = [(prediction.run_id, prediction.metric_id) for prediction in predictions]
    if len(prediction_keys) != len(set(prediction_keys)):
        raise ValueError(f"duplicate normalized prediction: {metadata.run_id!r}")
    if any(prediction.run_id != metadata.run_id for prediction in predictions):
        raise ValueError(f"prediction run-id mismatch: {metadata.run_id!r}")
    if any(prediction.source_artifact not in manifest.artifact_paths for prediction in predictions):
        raise ValueError(f"prediction references an unlisted artifact: {metadata.run_id!r}")
    if manifest.status is not RunStatus.COMPLETED and predictions:
        raise ValueError(f"non-completed run contains normalized predictions: {metadata.run_id!r}")

    validate_frozen_fields(metadata=metadata, manifest=manifest, ledger=ledger)


def load_and_verify_attempt(*, run_directory: Path, ledger: FrozenLedger) -> HarvestedAttempt:
    if run_directory.is_symlink() or not run_directory.is_dir():
        raise ValueError(f"run directory must be a regular non-symlink directory: {run_directory}")
    run_id = run_directory.name
    verify_artifact_ledger(run_directory=run_directory, run_id=run_id)
    input_paths = verify_tree_ledger(
        tree_root=run_directory / "input",
        ledger_path=run_directory / "input.sha256",
    )
    workspace_paths = verify_tree_ledger(
        tree_root=run_directory / "workspace",
        ledger_path=run_directory / "workspace.sha256",
    )
    metadata = RunMetadata.model_validate_json(
        run_directory.joinpath("metadata.json").read_text(encoding="utf-8")
    )
    status = RunStatusRecord.model_validate_json(
        run_directory.joinpath("status.json").read_text(encoding="utf-8")
    )
    manifest = load_single_jsonl(
        path=run_directory / "manifest.jsonl",
        model_type=RunManifest,
    )
    predictions = load_jsonl(
        path=run_directory / "predictions.jsonl",
        model_type=Prediction,
    )
    validate_run_consistency(
        run_directory=run_directory,
        metadata=metadata,
        status=status,
        manifest=manifest,
        predictions=predictions,
        input_paths=input_paths,
        workspace_paths=workspace_paths,
        ledger=ledger,
    )
    integrity = IntegrityRecord(
        run_id=run_id,
        stage=metadata.stage,
        task_variant=metadata.task,
        system=metadata.system,
        replicate=metadata.replicate,
        physical_attempt=metadata.attempt,
        status=manifest.status,
        infrastructure_valid=manifest.infrastructure_valid,
        artifact_ledger_sha256=sha256_file(path=run_directory / "artifact.sha256"),
        metadata_sha256=sha256_file(path=run_directory / "metadata.json"),
        manifest_sha256=sha256_file(path=run_directory / "manifest.jsonl"),
        predictions_sha256=sha256_file(path=run_directory / "predictions.jsonl"),
        input_ledger_sha256=sha256_file(path=run_directory / "input.sha256"),
        workspace_ledger_sha256=sha256_file(path=run_directory / "workspace.sha256"),
        input_file_count=len(input_paths),
        workspace_file_count=len(workspace_paths),
        artifact_file_count=len(ARTIFACT_PATHS),
    )
    return HarvestedAttempt(
        run_directory=run_directory,
        metadata=metadata,
        status=status,
        manifest=manifest,
        predictions=predictions,
        integrity=integrity,
    )
