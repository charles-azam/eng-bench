from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from analysis.eligibility import (
    DATASET_SPECS,
    build_eligibility_report,
    dataset_schedule_keys,
    group_and_validate_attempts,
    load_matrix,
)
from analysis.harvest import discover_attempts, select_dataset_attempts
from analysis.models import (
    DatasetEligibility,
    DatasetName,
    DatasetSpec,
    EligibilityReport,
    HarvestedAttempt,
    ScheduleIntegrityRecord,
    ScheduleReplicate,
)
from analysis.publication_models import (
    AttemptRecord,
    CellClaim,
    CellStatusRow,
    ChartData,
    DatasetGateProvenance,
    HashRecord,
    IntervalCoverageClaim,
    PublicationBundleCounts,
    PublicationClaims,
    PublicationHashManifest,
    PublicationProvenance,
    ReplicateMetricRow,
    RunStatusRow,
    StageCompletionClaim,
    StatusCounts,
    StrictPublicationModel,
    TaskMetricSummaryRow,
)
from analysis.schedules import PROTOCOL_STAGE_ORDER, verify_schedules
from eng_bench.integrity import (
    parse_evaluator_manifest,
    sha256_bytes,
    validate_evaluator_manifest,
)
from eng_bench.models import (
    EvaluationSummary,
    FrozenLedger,
    Measurement,
    Prediction,
    RunManifest,
    RunStatus,
    Score,
)
from eng_bench.scoring import aggregate_task, evaluate, normalized_prediction
from eng_bench.units import can_convert_units


ModelT = TypeVar("ModelT", bound=BaseModel)
KeyT = TypeVar("KeyT")


ATTEMPT_COLUMNS: tuple[str, ...] = (
    "run_id",
    "stage",
    "task_variant",
    "system",
    "scheduled_replicate",
    "physical_attempt",
    "is_retry",
    "is_final_attempt_for_scheduled_replicate",
    "status",
    "infrastructure_valid",
    "included_n3",
    "included_n5",
    "included_ablation",
)


def canonical_json(*, value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def require_input_file(*, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def snapshot_file(*, path: Path, label: str) -> bytes:
    require_input_file(path=path, label=label)
    return path.read_bytes()


def require_snapshot_unchanged(*, path: Path, contents: bytes, label: str) -> None:
    current = snapshot_file(path=path, label=label)
    if current != contents:
        raise ValueError(f"{label} changed while publication data was assembled: {path}")


def load_jsonl_bytes(
    *, contents: bytes, model_type: type[ModelT], label: str
) -> tuple[ModelT, ...]:
    lines = [line for line in contents.decode("utf-8").splitlines() if line.strip()]
    return tuple(model_type.model_validate_json(line) for line in lines)


def index_unique(
    *, values: Iterable[ModelT], key: Callable[[ModelT], KeyT], label: str
) -> dict[KeyT, ModelT]:
    indexed: dict[KeyT, ModelT] = {}
    for value in values:
        item_key = key(value)
        if item_key in indexed:
            raise ValueError(f"duplicate {label}: {item_key!r}")
        indexed[item_key] = value
    return indexed


def parse_boolean(*, value: str, field_name: str) -> bool:
    if value not in {"true", "false"}:
        raise ValueError(
            f"attempts CSV field {field_name!r} must be 'true' or 'false', got {value!r}"
        )
    return value == "true"


def load_attempts_bytes(*, contents: bytes) -> tuple[AttemptRecord, ...]:
    attempts: list[AttemptRecord] = []
    with io.StringIO(contents.decode("utf-8"), newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(ATTEMPT_COLUMNS):
            raise ValueError(
                f"attempts CSV columns must be exactly {list(ATTEMPT_COLUMNS)!r}, "
                f"got {reader.fieldnames!r}"
            )
        for row in reader:
            attempts.append(
                AttemptRecord(
                    run_id=row["run_id"],
                    stage=row["stage"],
                    task_variant=row["task_variant"],
                    system=row["system"],
                    scheduled_replicate=int(row["scheduled_replicate"]),
                    physical_attempt=int(row["physical_attempt"]),
                    is_retry=parse_boolean(
                        value=row["is_retry"], field_name="is_retry"
                    ),
                    is_final_attempt_for_scheduled_replicate=parse_boolean(
                        value=row["is_final_attempt_for_scheduled_replicate"],
                        field_name="is_final_attempt_for_scheduled_replicate",
                    ),
                    status=RunStatus(row["status"]),
                    infrastructure_valid=parse_boolean(
                        value=row["infrastructure_valid"],
                        field_name="infrastructure_valid",
                    ),
                    included_n3=parse_boolean(
                        value=row["included_n3"], field_name="included_n3"
                    ),
                    included_n5=parse_boolean(
                        value=row["included_n5"], field_name="included_n5"
                    ),
                    included_ablation=parse_boolean(
                        value=row["included_ablation"],
                        field_name="included_ablation",
                    ),
                )
            )
    index_unique(values=attempts, key=lambda item: item.run_id, label="attempt run_id")
    return tuple(attempts)


def load_summary_bytes(*, contents: bytes) -> EvaluationSummary:
    return EvaluationSummary.model_validate_json(contents)


def load_schedule_integrity_bytes(
    *, contents: bytes
) -> tuple[ScheduleIntegrityRecord, ...]:
    records = load_jsonl_bytes(
        contents=contents,
        model_type=ScheduleIntegrityRecord,
        label="schedule integrity JSONL",
    )
    index_unique(values=records, key=lambda item: item.stage, label="schedule stage")
    return records


def status_counts(*, statuses: Iterable[RunStatus]) -> StatusCounts:
    materialized = tuple(statuses)
    return StatusCounts(
        completed=sum(status is RunStatus.COMPLETED for status in materialized),
        agent_failure=sum(status is RunStatus.AGENT_FAILURE for status in materialized),
        refusal=sum(status is RunStatus.REFUSAL for status in materialized),
        fallback_contaminated=sum(
            status is RunStatus.FALLBACK_CONTAMINATED for status in materialized
        ),
        provider_failure=sum(
            status is RunStatus.PROVIDER_FAILURE for status in materialized
        ),
        runner_failure=sum(
            status is RunStatus.RUNNER_FAILURE for status in materialized
        ),
    )


def dataset_spec(*, dataset: DatasetName) -> DatasetSpec:
    return next(spec for spec in DATASET_SPECS if spec.dataset is dataset)


def dataset_eligibility(
    *, report: EligibilityReport, dataset: DatasetName
) -> DatasetEligibility:
    return next(item for item in report.datasets if item.dataset is dataset)


def expected_attempt_records(
    *,
    raw_attempts: tuple[HarvestedAttempt, ...],
    eligibility: EligibilityReport,
    matrix_schedule: tuple[ScheduleReplicate, ...],
) -> tuple[AttemptRecord, ...]:
    eligibility_by_dataset = {
        item.dataset: item.eligible for item in eligibility.datasets
    }
    dataset_keys = {
        spec.dataset: dataset_schedule_keys(schedule=matrix_schedule, spec=spec)
        for spec in DATASET_SPECS
    }
    final_attempt_numbers = {
        scheduled_key: max(
            attempt.metadata.attempt
            for attempt in raw_attempts
            if attempt.scheduled_key == scheduled_key
        )
        for scheduled_key in {attempt.scheduled_key for attempt in raw_attempts}
    }
    return tuple(
        AttemptRecord(
            run_id=attempt.metadata.run_id,
            stage=attempt.metadata.stage,
            task_variant=attempt.metadata.task,
            system=attempt.metadata.system,
            scheduled_replicate=attempt.metadata.replicate,
            physical_attempt=attempt.metadata.attempt,
            is_retry=attempt.metadata.attempt == 2,
            is_final_attempt_for_scheduled_replicate=(
                attempt.metadata.attempt
                == final_attempt_numbers[attempt.scheduled_key]
            ),
            status=attempt.manifest.status,
            infrastructure_valid=attempt.manifest.infrastructure_valid,
            included_n3=(
                eligibility_by_dataset[DatasetName.N3]
                and attempt.scheduled_key in dataset_keys[DatasetName.N3]
            ),
            included_n5=(
                eligibility_by_dataset[DatasetName.N5]
                and attempt.scheduled_key in dataset_keys[DatasetName.N5]
            ),
            included_ablation=(
                eligibility_by_dataset[DatasetName.ABLATION]
                and attempt.scheduled_key in dataset_keys[DatasetName.ABLATION]
            ),
        )
        for attempt in sorted(raw_attempts, key=lambda item: item.metadata.run_id)
    )


def canonical_models_jsonl(*, models: Iterable[BaseModel]) -> bytes:
    return "".join(
        f"{canonical_json(value=model.model_dump(mode='json'))}\n" for model in models
    ).encode("utf-8")


def snapshot_schedule_directory(*, schedules_root: Path) -> dict[str, bytes]:
    if schedules_root.is_symlink() or not schedules_root.is_dir():
        raise ValueError(
            f"schedules root must be a regular non-symlink directory: {schedules_root}"
        )
    snapshots: dict[str, bytes] = {}
    for entry in sorted(schedules_root.iterdir(), key=lambda path: path.name):
        if entry.is_symlink() or not entry.is_file():
            raise ValueError(f"schedules root may contain only regular files: {entry}")
        snapshots[entry.name] = entry.read_bytes()
    return snapshots


def require_schedule_snapshots_unchanged(
    *, schedules_root: Path, snapshots: dict[str, bytes]
) -> None:
    current = snapshot_schedule_directory(schedules_root=schedules_root)
    if current != snapshots:
        raise ValueError("schedule files changed while publication data was assembled")


def make_hash_record(
    *, role: str, path: str, contents: bytes, record_count: int | None = None
) -> HashRecord:
    return HashRecord(
        role=role,
        path=path,
        sha256=sha256_bytes(value=contents),
        byte_count=len(contents),
        record_count=record_count,
    )


def logical_source_paths(*, dataset: DatasetName) -> dict[str, str]:
    dataset_name = dataset.value
    return {
        "ledger": "protocol/evaluation_ledger.json",
        "evaluator_manifest": "protocol/evaluator_manifest.sha256",
        "matrix": "protocol/matrix.tsv",
        "eligibility": "harvested/eligibility.json",
        "attempts": "harvested/attempts.csv",
        "manifests": f"harvested/{dataset_name}/manifests.jsonl",
        "predictions": f"harvested/{dataset_name}/predictions.jsonl",
        "measurements": "measurements/held_out.jsonl",
        "scores": f"evaluation/{dataset_name}/scores.jsonl",
        "summary": f"evaluation/{dataset_name}/summary.json",
        "schedule_integrity": "harvested/schedule_integrity.jsonl",
    }


def select_and_validate_attempts(
    *,
    dataset: DatasetName,
    attempts: tuple[AttemptRecord, ...],
    manifests: tuple[RunManifest, ...],
) -> tuple[AttemptRecord, ...]:
    manifest_by_run = index_unique(
        values=manifests,
        key=lambda item: item.run_id,
        label="manifest run_id",
    )
    selected = tuple(
        attempt for attempt in attempts if attempt.included_in(dataset=dataset)
    )
    selected_by_run = index_unique(
        values=selected,
        key=lambda item: item.run_id,
        label="selected attempt run_id",
    )
    if set(selected_by_run) != set(manifest_by_run):
        raise ValueError(
            "selected attempts and harvested manifests have different run IDs: "
            f"attempt_only={sorted(set(selected_by_run) - set(manifest_by_run))!r}, "
            f"manifest_only={sorted(set(manifest_by_run) - set(selected_by_run))!r}"
        )
    if not selected:
        raise ValueError(f"dataset {dataset.value!r} has no selected attempts")

    grouped: dict[tuple[str, str, str, int], list[AttemptRecord]] = defaultdict(list)
    for attempt in selected:
        manifest = manifest_by_run[attempt.run_id]
        mismatches: list[str] = []
        if manifest.task_variant != attempt.task_variant:
            mismatches.append("task_variant")
        if manifest.system != attempt.system:
            mismatches.append("system")
        if manifest.attempt != attempt.physical_attempt:
            mismatches.append("physical_attempt")
        if manifest.status is not attempt.status:
            mismatches.append("status")
        if manifest.infrastructure_valid != attempt.infrastructure_valid:
            mismatches.append("infrastructure_valid")
        if mismatches:
            raise ValueError(
                f"attempt/manifest mismatch for {attempt.run_id!r}: {mismatches!r}"
            )
        grouped[attempt.scheduled_key].append(attempt)

    for scheduled_key, physical_attempts in grouped.items():
        ordered = sorted(physical_attempts, key=lambda item: item.physical_attempt)
        numbers = [attempt.physical_attempt for attempt in ordered]
        if numbers not in ([1], [1, 2]):
            raise ValueError(
                f"publication attempts must be [1] or [1, 2] for {scheduled_key!r}, "
                f"got {numbers!r}"
            )
        expected_retry_flags = [number > 1 for number in numbers]
        if [attempt.is_retry for attempt in ordered] != expected_retry_flags:
            raise ValueError(f"retry flags disagree for {scheduled_key!r}")
        expected_final_flags = [False] * (len(ordered) - 1) + [True]
        if [
            attempt.is_final_attempt_for_scheduled_replicate for attempt in ordered
        ] != expected_final_flags:
            raise ValueError(f"final-attempt flags disagree for {scheduled_key!r}")
        if len(ordered) == 2 and ordered[0].status not in {
            RunStatus.PROVIDER_FAILURE,
            RunStatus.RUNNER_FAILURE,
        }:
            raise ValueError(
                f"retry follows a non-infrastructure outcome for {scheduled_key!r}"
            )

    return tuple(
        sorted(
            selected,
            key=lambda item: (
                item.task_variant,
                item.system,
                item.scheduled_replicate,
                item.physical_attempt,
                item.run_id,
            ),
        )
    )


def validate_score_identity(
    *,
    score: Score,
    manifest: RunManifest,
    measurement: Measurement,
    prediction: Prediction | None,
) -> None:
    mismatches: list[str] = []
    if score.benchmark_version != manifest.benchmark_version:
        mismatches.append("benchmark_version")
    if score.task_variant != manifest.task_variant:
        mismatches.append("task_variant")
    if score.system != manifest.system:
        mismatches.append("system")
    if score.requested_model != manifest.requested_model:
        mismatches.append("requested_model")
    if score.served_models != manifest.served_models:
        mismatches.append("served_models")
    if score.run_status is not manifest.status:
        mismatches.append("run_status")
    if score.infrastructure_valid != manifest.infrastructure_valid:
        mismatches.append("infrastructure_valid")
    if score.measurement_kind is not measurement.kind:
        mismatches.append("measurement_kind")
    if score.evidence_class is not measurement.evidence_class:
        mismatches.append("evidence_class")
    if score.dependency_group != measurement.dependency_group:
        mismatches.append("dependency_group")
    expected_completion_passed = (
        manifest.status is RunStatus.COMPLETED and prediction is not None
    )
    if score.completion_passed != expected_completion_passed:
        mismatches.append("completion_passed")
    if score.scorable and not (
        score.completion_passed and score.compliance_passed and score.artifact_valid
    ):
        mismatches.append("scorable")
    if mismatches:
        raise ValueError(
            f"score identity mismatch for {(score.run_id, score.metric_id)!r}: "
            f"{mismatches!r}"
        )

    has_missing_issue = "missing_prediction" in score.issues
    if (prediction is None) != has_missing_issue:
        raise ValueError(
            f"score missing-prediction issue disagrees for "
            f"{(score.run_id, score.metric_id)!r}"
        )
    expected_normalized: tuple[float | None, float | None, float | None, float | None]
    if prediction is not None and can_convert_units(
        from_units=prediction.units, to_units=measurement.units
    ):
        expected_normalized = normalized_prediction(
            prediction=prediction,
            measurement=measurement,
        )
    else:
        expected_normalized = (None, None, None, None)
    actual_normalized = (
        score.normalized_point,
        score.normalized_p10,
        score.normalized_p50,
        score.normalized_p90,
    )
    if actual_normalized != expected_normalized:
        raise ValueError(
            f"score normalized prediction disagrees for "
            f"{(score.run_id, score.metric_id)!r}"
        )


def validate_evaluator_inputs(
    *,
    manifests: tuple[RunManifest, ...],
    predictions: tuple[Prediction, ...],
    measurements: tuple[Measurement, ...],
    scores: tuple[Score, ...],
    summary: EvaluationSummary,
) -> tuple[
    dict[str, RunManifest],
    dict[tuple[str, str], Prediction],
    dict[tuple[str, str], Measurement],
    dict[tuple[str, str], Score],
]:
    manifest_by_run = index_unique(
        values=manifests,
        key=lambda item: item.run_id,
        label="manifest run_id",
    )
    prediction_by_key = index_unique(
        values=predictions,
        key=lambda item: (item.run_id, item.metric_id),
        label="prediction run/metric",
    )
    measurement_by_key = index_unique(
        values=measurements,
        key=lambda item: (item.task_variant, item.metric_id),
        label="measurement task/metric",
    )
    score_by_key = index_unique(
        values=scores,
        key=lambda item: (item.run_id, item.metric_id),
        label="score run/metric",
    )

    for prediction in predictions:
        manifest = manifest_by_run.get(prediction.run_id)
        if manifest is None:
            raise ValueError(
                f"prediction references unknown run: {prediction.run_id!r}"
            )
        if (manifest.task_variant, prediction.metric_id) not in measurement_by_key:
            raise ValueError(
                f"prediction references unknown task/metric: "
                f"{(manifest.task_variant, prediction.metric_id)!r}"
            )

    expected_score_keys = {
        (manifest.run_id, measurement.metric_id)
        for manifest in manifests
        for measurement in measurements
        if measurement.task_variant == manifest.task_variant and measurement.required
    }
    if set(score_by_key) != expected_score_keys:
        raise ValueError(
            "scores do not exactly cover every run/required-metric pair: "
            f"score_only={sorted(set(score_by_key) - expected_score_keys)!r}, "
            f"missing={sorted(expected_score_keys - set(score_by_key))!r}"
        )
    if not expected_score_keys:
        raise ValueError("publication dataset has no required metric scores")

    for score_key, score in score_by_key.items():
        manifest = manifest_by_run[score.run_id]
        measurement = measurement_by_key[(manifest.task_variant, score.metric_id)]
        prediction = prediction_by_key.get(score_key)
        validate_score_identity(
            score=score,
            manifest=manifest,
            measurement=measurement,
            prediction=prediction,
        )

    task_manifests: dict[tuple[str, str], list[RunManifest]] = defaultdict(list)
    task_scores: dict[tuple[str, str], list[Score]] = defaultdict(list)
    for manifest in manifests:
        task_manifests[(manifest.system, manifest.task_variant)].append(manifest)
    for score in scores:
        task_scores[(score.system, score.task_variant)].append(score)
    recomputed = EvaluationSummary(
        benchmark_versions=sorted(
            {manifest.benchmark_version for manifest in manifests}
        ),
        total_attempts=len(manifests),
        task_results=[
            aggregate_task(
                system=system,
                task_variant=task_variant,
                manifests=task_manifests[(system, task_variant)],
                scores=task_scores[(system, task_variant)],
            )
            for system, task_variant in sorted(task_manifests)
        ],
    )
    if summary != recomputed:
        raise ValueError("evaluator summary does not match manifests and scores")
    return manifest_by_run, prediction_by_key, measurement_by_key, score_by_key


def validate_schedule_records(
    *,
    selected_attempts: tuple[AttemptRecord, ...],
    schedule_integrity: tuple[ScheduleIntegrityRecord, ...],
) -> tuple[ScheduleIntegrityRecord, ...]:
    records_by_stage = index_unique(
        values=schedule_integrity,
        key=lambda item: item.stage,
        label="schedule integrity stage",
    )
    scheduled_keys_by_stage: dict[str, set[tuple[str, str, str, int]]] = defaultdict(
        set
    )
    for attempt in selected_attempts:
        scheduled_keys_by_stage[attempt.stage].add(attempt.scheduled_key)
    missing_stages = set(scheduled_keys_by_stage) - set(records_by_stage)
    if missing_stages:
        raise ValueError(
            f"selected attempts lack schedule integrity records: {sorted(missing_stages)!r}"
        )
    selected_records: list[ScheduleIntegrityRecord] = []
    selected_stage_order = tuple(
        stage for stage in PROTOCOL_STAGE_ORDER if stage in scheduled_keys_by_stage
    )
    if set(selected_stage_order) != set(scheduled_keys_by_stage):
        raise ValueError(
            "selected attempts contain a stage outside the frozen protocol order"
        )
    for stage in selected_stage_order:
        record = records_by_stage[stage]
        actual_replicates = len(scheduled_keys_by_stage[stage])
        if record.scheduled_replicates != actual_replicates:
            raise ValueError(
                f"schedule count mismatch for {stage!r}: "
                f"integrity={record.scheduled_replicates}, dataset={actual_replicates}"
            )
        if record.launched_first_attempts != actual_replicates:
            raise ValueError(
                f"schedule launch count mismatch for {stage!r}: "
                f"integrity={record.launched_first_attempts}, dataset={actual_replicates}"
            )
        if not record.complete_launch_prefix:
            raise ValueError(f"selected publication stage is incomplete: {stage!r}")
        selected_records.append(record)
    return tuple(selected_records)


def build_run_status_rows(
    *,
    dataset: DatasetName,
    selected_attempts: tuple[AttemptRecord, ...],
    manifest_by_run: dict[str, RunManifest],
) -> tuple[RunStatusRow, ...]:
    return tuple(
        RunStatusRow(
            dataset=dataset,
            run_id=attempt.run_id,
            benchmark_version=manifest_by_run[attempt.run_id].benchmark_version,
            stage=attempt.stage,
            task_variant=attempt.task_variant,
            system=attempt.system,
            scheduled_replicate=attempt.scheduled_replicate,
            physical_attempt=attempt.physical_attempt,
            is_retry=attempt.is_retry,
            is_final_attempt_for_scheduled_replicate=(
                attempt.is_final_attempt_for_scheduled_replicate
            ),
            requested_model=manifest_by_run[attempt.run_id].requested_model,
            served_models=manifest_by_run[attempt.run_id].served_models,
            status=attempt.status,
            infrastructure_valid=attempt.infrastructure_valid,
            started_at=manifest_by_run[attempt.run_id].started_at,
            ended_at=manifest_by_run[attempt.run_id].ended_at,
            wall_time_seconds=(
                manifest_by_run[attempt.run_id].ended_at
                - manifest_by_run[attempt.run_id].started_at
            ).total_seconds(),
        )
        for attempt in selected_attempts
    )


def group_attempts_by_cell(
    *, attempts: tuple[AttemptRecord, ...]
) -> dict[tuple[str, str], tuple[AttemptRecord, ...]]:
    grouped: dict[tuple[str, str], list[AttemptRecord]] = defaultdict(list)
    for attempt in attempts:
        grouped[(attempt.task_variant, attempt.system)].append(attempt)
    return {
        key: tuple(
            sorted(
                values,
                key=lambda item: (
                    item.scheduled_replicate,
                    item.physical_attempt,
                    item.run_id,
                ),
            )
        )
        for key, values in sorted(grouped.items())
    }


def final_attempts(
    *, attempts: tuple[AttemptRecord, ...]
) -> tuple[AttemptRecord, ...]:
    return tuple(
        attempt
        for attempt in attempts
        if attempt.is_final_attempt_for_scheduled_replicate
    )


def build_cell_status_rows(
    *, dataset: DatasetName, selected_attempts: tuple[AttemptRecord, ...]
) -> tuple[CellStatusRow, ...]:
    rows: list[CellStatusRow] = []
    for (task_variant, system), attempts in group_attempts_by_cell(
        attempts=selected_attempts
    ).items():
        final = final_attempts(attempts=attempts)
        counts = status_counts(statuses=(attempt.status for attempt in attempts))
        rows.append(
            CellStatusRow(
                dataset=dataset,
                task_variant=task_variant,
                system=system,
                scheduled_replicates=len(final),
                eligible_replicates=sum(
                    attempt.infrastructure_valid for attempt in final
                ),
                completed_final_replicates=sum(
                    attempt.status is RunStatus.COMPLETED for attempt in final
                ),
                non_completed_final_replicates=sum(
                    attempt.status is not RunStatus.COMPLETED for attempt in final
                ),
                physical_attempts=len(attempts),
                retries=sum(attempt.is_retry for attempt in attempts),
                non_completed_physical_attempts=sum(
                    attempt.status is not RunStatus.COMPLETED for attempt in attempts
                ),
                infrastructure_failed_physical_attempts=sum(
                    attempt.status
                    in {RunStatus.PROVIDER_FAILURE, RunStatus.RUNNER_FAILURE}
                    for attempt in attempts
                ),
                completed_attempts=counts.completed,
                agent_failure_attempts=counts.agent_failure,
                refusal_attempts=counts.refusal,
                fallback_contaminated_attempts=counts.fallback_contaminated,
                provider_failure_attempts=counts.provider_failure,
                runner_failure_attempts=counts.runner_failure,
            )
        )
    return tuple(rows)


def build_replicate_metric_rows(
    *,
    dataset: DatasetName,
    selected_attempts: tuple[AttemptRecord, ...],
    manifest_by_run: dict[str, RunManifest],
    prediction_by_key: dict[tuple[str, str], Prediction],
    measurement_by_key: dict[tuple[str, str], Measurement],
    score_by_key: dict[tuple[str, str], Score],
) -> tuple[ReplicateMetricRow, ...]:
    attempts_by_run = {attempt.run_id: attempt for attempt in selected_attempts}
    rows: list[ReplicateMetricRow] = []
    publication_keys = sorted(
        (
            manifest.run_id,
            measurement.metric_id,
        )
        for manifest in manifest_by_run.values()
        for measurement in measurement_by_key.values()
        if measurement.task_variant == manifest.task_variant
    )
    for publication_key in publication_keys:
        run_id, metric_id = publication_key
        manifest = manifest_by_run[run_id]
        attempt = attempts_by_run[run_id]
        measurement = measurement_by_key[(manifest.task_variant, metric_id)]
        prediction = prediction_by_key.get(publication_key)
        score = score_by_key.get(publication_key)
        if measurement.required != (score is not None):
            raise ValueError(
                f"evaluator row presence disagrees with required flag for "
                f"{publication_key!r}"
            )
        rows.append(
            ReplicateMetricRow(
                dataset=dataset,
                run_id=manifest.run_id,
                benchmark_version=manifest.benchmark_version,
                stage=attempt.stage,
                task_variant=manifest.task_variant,
                system=attempt.system,
                scheduled_replicate=attempt.scheduled_replicate,
                physical_attempt=attempt.physical_attempt,
                is_retry=attempt.is_retry,
                is_final_attempt_for_scheduled_replicate=(
                    attempt.is_final_attempt_for_scheduled_replicate
                ),
                run_status=manifest.status,
                infrastructure_valid=manifest.infrastructure_valid,
                metric_id=measurement.metric_id,
                measurement_kind=measurement.kind,
                measurement_required=measurement.required,
                evaluator_row_present=score is not None,
                evidence_class=measurement.evidence_class,
                dependency_group=measurement.dependency_group,
                units=measurement.units,
                observed_value=measurement.value,
                accepted_lower=measurement.lower,
                accepted_upper=measurement.upper,
                expected_qualitative=measurement.expected_qualitative,
                expected_category=measurement.expected_category,
                allowed_categories=measurement.allowed_categories,
                measurement_provenance=measurement.provenance,
                prediction_present=prediction is not None,
                prediction_units=prediction.units if prediction is not None else None,
                prediction_confidence=(
                    prediction.confidence if prediction is not None else None
                ),
                source_artifact=(
                    prediction.source_artifact if prediction is not None else None
                ),
                raw_point=prediction.point if prediction is not None else None,
                raw_p10=prediction.p10 if prediction is not None else None,
                raw_p50=prediction.p50 if prediction is not None else None,
                raw_p90=prediction.p90 if prediction is not None else None,
                predicted_qualitative=(
                    prediction.qualitative if prediction is not None else None
                ),
                predicted_category=(
                    prediction.category if prediction is not None else None
                ),
                point=score.normalized_point if score is not None else None,
                p10=score.normalized_p10 if score is not None else None,
                p50=score.normalized_p50 if score is not None else None,
                p90=score.normalized_p90 if score is not None else None,
                completion_passed=(
                    score.completion_passed if score is not None else None
                ),
                compliance_passed=(
                    score.compliance_passed if score is not None else None
                ),
                artifact_valid=score.artifact_valid if score is not None else None,
                scorable=score.scorable if score is not None else None,
                absolute_error=score.absolute_error if score is not None else None,
                signed_error=score.signed_error if score is not None else None,
                absolute_log_error=(
                    score.absolute_log_error if score is not None else None
                ),
                signed_relative_error=(
                    score.signed_relative_error if score is not None else None
                ),
                weighted_interval_score=(
                    score.weighted_interval_score if score is not None else None
                ),
                count_log_error=(
                    score.count_log_error if score is not None else None
                ),
                interval_log_error=(
                    score.interval_log_error if score is not None else None
                ),
                prediction_interval_covered=(
                    score.prediction_interval_covered if score is not None else None
                ),
                point_in_measurement_interval=(
                    score.point_in_measurement_interval
                    if score is not None
                    else None
                ),
                qualitative_passed=(
                    score.qualitative_passed if score is not None else None
                ),
                categorical_passed=(
                    score.categorical_passed if score is not None else None
                ),
                issues=score.issues if score is not None else [],
                publication_notes=(
                    [] if score is not None else ["not_evaluated_required_false"]
                ),
            )
        )
    return tuple(rows)


def count_present(*, values: Iterable[object | None]) -> int:
    return sum(value is not None for value in values)


def count_true(*, values: Iterable[bool | None]) -> int:
    return sum(value is True for value in values)


def build_task_metric_summary_rows(
    *,
    dataset: DatasetName,
    summary: EvaluationSummary,
    manifests: tuple[RunManifest, ...],
    scores: tuple[Score, ...],
    measurement_by_key: dict[tuple[str, str], Measurement],
) -> tuple[TaskMetricSummaryRow, ...]:
    manifests_by_task: dict[tuple[str, str], list[RunManifest]] = defaultdict(list)
    scores_by_task_metric: dict[tuple[str, str, str], list[Score]] = defaultdict(list)
    for manifest in manifests:
        manifests_by_task[(manifest.system, manifest.task_variant)].append(manifest)
    for score in scores:
        scores_by_task_metric[
            (score.system, score.task_variant, score.metric_id)
        ].append(score)

    rows: list[TaskMetricSummaryRow] = []
    for task in summary.task_results:
        task_key = (task.system, task.task_variant)
        task_manifests = manifests_by_task[task_key]
        for metric in task.metrics:
            measurement = measurement_by_key[(task.task_variant, metric.metric_id)]
            metric_scores = scores_by_task_metric[
                (task.system, task.task_variant, metric.metric_id)
            ]
            infrastructure_scores = [
                score for score in metric_scores if score.infrastructure_valid
            ]
            completed_scores = [
                score for score in infrastructure_scores if score.completion_passed
            ]
            scorable_scores = [
                score for score in infrastructure_scores if score.scorable
            ]
            rows.append(
                TaskMetricSummaryRow(
                    dataset=dataset,
                    system=task.system,
                    task_variant=task.task_variant,
                    task_attempts=task.attempts,
                    task_infrastructure_valid_attempts=(
                        task.infrastructure_valid_attempts
                    ),
                    task_completed_attempts=task.completed_attempts,
                    task_agent_failures=task.agent_failures,
                    task_refusals=task.refusals,
                    task_fallback_contaminated_attempts=(
                        task.fallback_contaminated_attempts
                    ),
                    task_provider_failures=task.provider_failures,
                    task_runner_failures=task.runner_failures,
                    task_run_completion_rate=task.run_completion_rate,
                    task_run_completion_numerator=task.completed_attempts,
                    task_run_completion_denominator=(
                        task.infrastructure_valid_attempts
                    ),
                    task_mean_wall_time_seconds=task.mean_wall_time_seconds,
                    task_mean_wall_time_denominator=len(task_manifests),
                    task_expected_metric_predictions=(
                        task.expected_metric_predictions
                    ),
                    task_completed_metric_predictions=(
                        task.completed_metric_predictions
                    ),
                    task_metric_completion_rate=task.metric_completion_rate,
                    task_metric_completion_numerator=(
                        task.completed_metric_predictions
                    ),
                    task_metric_completion_denominator=(
                        task.expected_metric_predictions
                    ),
                    metric_id=metric.metric_id,
                    measurement_kind=metric.measurement_kind,
                    measurement_required=measurement.required,
                    evidence_class=measurement.evidence_class,
                    dependency_group=measurement.dependency_group,
                    units=measurement.units,
                    measurement_provenance=measurement.provenance,
                    expected_predictions=metric.expected_predictions,
                    completed_predictions=metric.completed_predictions,
                    scorable_predictions=metric.scorable_predictions,
                    completion_rate=metric.completion_rate,
                    completion_numerator=metric.completed_predictions,
                    completion_denominator=metric.expected_predictions,
                    artifact_validity_rate=metric.artifact_validity_rate,
                    artifact_validity_numerator=sum(
                        score.artifact_valid for score in completed_scores
                    ),
                    artifact_validity_denominator=len(completed_scores),
                    mean_absolute_error=metric.mean_absolute_error,
                    mean_absolute_error_denominator=count_present(
                        values=(score.absolute_error for score in scorable_scores)
                    ),
                    mean_signed_error=metric.mean_signed_error,
                    mean_signed_error_denominator=count_present(
                        values=(score.signed_error for score in scorable_scores)
                    ),
                    mean_absolute_log_error=metric.mean_absolute_log_error,
                    mean_absolute_log_error_denominator=count_present(
                        values=(
                            score.absolute_log_error for score in scorable_scores
                        )
                    ),
                    mean_signed_relative_error=metric.mean_signed_relative_error,
                    mean_signed_relative_error_denominator=count_present(
                        values=(
                            score.signed_relative_error for score in scorable_scores
                        )
                    ),
                    mean_weighted_interval_score=(
                        metric.mean_weighted_interval_score
                    ),
                    mean_weighted_interval_score_denominator=count_present(
                        values=(
                            score.weighted_interval_score for score in scorable_scores
                        )
                    ),
                    mean_count_log_error=metric.mean_count_log_error,
                    mean_count_log_error_denominator=count_present(
                        values=(score.count_log_error for score in scorable_scores)
                    ),
                    mean_interval_log_error=metric.mean_interval_log_error,
                    mean_interval_log_error_denominator=count_present(
                        values=(score.interval_log_error for score in scorable_scores)
                    ),
                    prediction_interval_coverage_rate=(
                        metric.prediction_interval_coverage_rate
                    ),
                    prediction_interval_coverage_numerator=count_true(
                        values=(
                            score.prediction_interval_covered
                            for score in scorable_scores
                        )
                    ),
                    prediction_interval_coverage_denominator=count_present(
                        values=(
                            score.prediction_interval_covered
                            for score in scorable_scores
                        )
                    ),
                    point_interval_pass_rate=metric.point_interval_pass_rate,
                    point_interval_pass_numerator=count_true(
                        values=(
                            score.point_in_measurement_interval
                            for score in scorable_scores
                        )
                    ),
                    point_interval_pass_denominator=count_present(
                        values=(
                            score.point_in_measurement_interval
                            for score in scorable_scores
                        )
                    ),
                    qualitative_pass_rate=metric.qualitative_pass_rate,
                    qualitative_pass_numerator=count_true(
                        values=(score.qualitative_passed for score in scorable_scores)
                    ),
                    qualitative_pass_denominator=count_present(
                        values=(score.qualitative_passed for score in scorable_scores)
                    ),
                    categorical_pass_rate=metric.categorical_pass_rate,
                    categorical_pass_numerator=count_true(
                        values=(score.categorical_passed for score in scorable_scores)
                    ),
                    categorical_pass_denominator=count_present(
                        values=(score.categorical_passed for score in scorable_scores)
                    ),
                )
            )
    return tuple(rows)


def build_claims(
    *,
    dataset: DatasetName,
    selected_attempts: tuple[AttemptRecord, ...],
    schedule_records: tuple[ScheduleIntegrityRecord, ...],
    scores: tuple[Score, ...],
) -> PublicationClaims:
    cell_claims: list[CellClaim] = []
    for (task_variant, system), attempts in group_attempts_by_cell(
        attempts=selected_attempts
    ).items():
        final = final_attempts(attempts=attempts)
        cell_claims.append(
            CellClaim(
                task_variant=task_variant,
                system=system,
                eligible_replicates=sum(
                    attempt.infrastructure_valid for attempt in final
                ),
                scheduled_replicates=len(final),
                physical_attempts=len(attempts),
                retries=sum(attempt.is_retry for attempt in attempts),
                non_completed_physical_attempts=sum(
                    attempt.status is not RunStatus.COMPLETED for attempt in attempts
                ),
                infrastructure_failed_physical_attempts=sum(
                    attempt.status
                    in {RunStatus.PROVIDER_FAILURE, RunStatus.RUNNER_FAILURE}
                    for attempt in attempts
                ),
                status_counts=status_counts(
                    statuses=(attempt.status for attempt in attempts)
                ),
            )
        )

    scores_by_metric: dict[tuple[str, str, str], list[Score]] = defaultdict(list)
    for score in scores:
        scores_by_metric[(score.task_variant, score.system, score.metric_id)].append(
            score
        )
    interval_claims: list[IntervalCoverageClaim] = []
    for (task_variant, system, metric_id), metric_scores in sorted(
        scores_by_metric.items()
    ):
        scorable_scores = [score for score in metric_scores if score.scorable]
        interval_claims.append(
            IntervalCoverageClaim(
                task_variant=task_variant,
                system=system,
                metric_id=metric_id,
                prediction_interval_covered_numerator=count_true(
                    values=(
                        score.prediction_interval_covered for score in scorable_scores
                    )
                ),
                prediction_interval_covered_denominator=count_present(
                    values=(
                        score.prediction_interval_covered for score in scorable_scores
                    )
                ),
                point_in_measurement_interval_numerator=count_true(
                    values=(
                        score.point_in_measurement_interval for score in scorable_scores
                    )
                ),
                point_in_measurement_interval_denominator=count_present(
                    values=(
                        score.point_in_measurement_interval for score in scorable_scores
                    )
                ),
            )
        )
    final = final_attempts(attempts=selected_attempts)
    return PublicationClaims(
        dataset=dataset,
        scheduled_replicates=len(final),
        eligible_replicates=sum(attempt.infrastructure_valid for attempt in final),
        physical_attempts=len(selected_attempts),
        retries=sum(attempt.is_retry for attempt in selected_attempts),
        non_completed_physical_attempts=sum(
            attempt.status is not RunStatus.COMPLETED
            for attempt in selected_attempts
        ),
        infrastructure_failed_physical_attempts=sum(
            attempt.status
            in {RunStatus.PROVIDER_FAILURE, RunStatus.RUNNER_FAILURE}
            for attempt in selected_attempts
        ),
        status_counts=status_counts(
            statuses=(attempt.status for attempt in selected_attempts)
        ),
        cells=cell_claims,
        schedule_stages=[
            StageCompletionClaim(
                stage=record.stage,
                scheduled_replicates=record.scheduled_replicates,
                launched_first_attempts=record.launched_first_attempts,
                complete_launch_prefix=record.complete_launch_prefix,
                schedule_sha256=record.schedule_sha256,
            )
            for record in schedule_records
        ],
        interval_coverage=interval_claims,
    )


def csv_value(*, value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (list, dict, tuple)):
        return canonical_json(value=value)
    return str(value)


def render_csv(
    *,
    model_type: type[StrictPublicationModel],
    rows: Sequence[StrictPublicationModel],
) -> bytes:
    fieldnames = list(model_type.model_fields)
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            dumped = row.model_dump(mode="python")
            writer.writerow(
                {
                    field_name: csv_value(value=dumped[field_name])
                    for field_name in fieldnames
                }
            )
        return stream.getvalue().encode("utf-8")


def render_model_json(*, model: BaseModel) -> bytes:
    return (
        f"{canonical_json(value=model.model_dump(mode='json'))}\n"
    ).encode("utf-8")


def publish_atomic_bundle(
    *, output_directory: Path, files: dict[str, bytes]
) -> None:
    if output_directory.exists() or output_directory.is_symlink():
        raise ValueError(
            f"publication output already exists or is a symlink: {output_directory}"
        )
    parent = output_directory.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError(
            f"publication output parent must be a regular directory: {parent}"
        )
    staging_directory = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.staging-", dir=parent)
    )
    try:
        for relative_path, contents in sorted(files.items()):
            (staging_directory / relative_path).write_bytes(contents)
        if output_directory.exists() or output_directory.is_symlink():
            raise ValueError(
                f"publication output appeared during assembly: {output_directory}"
            )
        os.rename(src=staging_directory, dst=output_directory)
    finally:
        if staging_directory.exists():
            shutil.rmtree(staging_directory)


def generate_publication_tables(
    *,
    dataset: DatasetName,
    manifests_path: Path,
    predictions_path: Path,
    measurements_path: Path,
    scores_path: Path,
    summary_path: Path,
    attempts_path: Path,
    schedule_integrity_path: Path,
    eligibility_path: Path,
    matrix_path: Path,
    schedules_root: Path,
    runs_root: Path,
    artifact_root: Path,
    ledger_path: Path,
    evaluator_manifest_path: Path,
    evaluator_root: Path,
    output_directory: Path,
) -> None:
    if output_directory.exists() or output_directory.is_symlink():
        raise ValueError(
            f"publication output already exists or is a symlink: {output_directory}"
        )
    if evaluator_root.is_symlink() or not evaluator_root.is_dir():
        raise ValueError(
            f"evaluator root must be a regular non-symlink directory: {evaluator_root}"
        )
    loaded_scoring_path = Path(evaluate.__code__.co_filename).resolve()
    expected_scoring_path = (evaluator_root / "src/eng_bench/scoring.py").resolve()
    if loaded_scoring_path != expected_scoring_path:
        raise ValueError(
            "loaded evaluator code is not the evaluator-root source: "
            f"loaded={loaded_scoring_path}, expected={expected_scoring_path}"
        )
    if artifact_root.resolve() != runs_root.resolve():
        raise ValueError("artifact root must resolve to the verified raw runs root")
    for protected_root, label in (
        (runs_root, "raw runs root"),
        (schedules_root, "schedules root"),
    ):
        resolved_output = output_directory.resolve()
        resolved_protected = protected_root.resolve()
        if resolved_output == resolved_protected or resolved_output.is_relative_to(
            resolved_protected
        ):
            raise ValueError(f"publication output must be outside the {label}")

    input_paths: dict[str, Path] = {
        "ledger": ledger_path,
        "evaluator_manifest": evaluator_manifest_path,
        "matrix": matrix_path,
        "eligibility": eligibility_path,
        "attempts": attempts_path,
        "manifests": manifests_path,
        "predictions": predictions_path,
        "measurements": measurements_path,
        "scores": scores_path,
        "summary": summary_path,
        "schedule_integrity": schedule_integrity_path,
    }
    input_snapshots = {
        role: snapshot_file(path=path, label=f"publication source {role}")
        for role, path in input_paths.items()
    }
    schedule_snapshots = snapshot_schedule_directory(
        schedules_root=schedules_root
    )

    ledger = FrozenLedger.model_validate_json(input_snapshots["ledger"])
    validate_evaluator_manifest(
        root=evaluator_root,
        manifest_path=evaluator_manifest_path,
        expected_manifest_sha256=ledger.evaluator_manifest_sha256,
    )
    frozen_measurements_path = evaluator_root / "measurements/held_out.jsonl"
    if measurements_path.resolve() != frozen_measurements_path.resolve():
        raise ValueError(
            "measurements path must resolve to evaluator-root/measurements/held_out.jsonl"
        )
    manifest_entries = parse_evaluator_manifest(
        manifest_text=input_snapshots["evaluator_manifest"].decode("utf-8")
    )
    expected_measurement_sha256 = manifest_entries.get(
        "measurements/held_out.jsonl"
    )
    actual_measurement_sha256 = sha256_bytes(
        value=input_snapshots["measurements"]
    )
    if expected_measurement_sha256 != actual_measurement_sha256:
        raise ValueError(
            "held-out measurement hash does not match the evaluator manifest"
        )

    matrix_schedule = load_matrix(matrix_path=matrix_path)
    raw_attempts = discover_attempts(runs_root=runs_root, ledger=ledger)
    grouped_raw_attempts = group_and_validate_attempts(
        attempts=raw_attempts,
        schedule=matrix_schedule,
    )
    recomputed_schedule_integrity = verify_schedules(
        schedules_root=schedules_root,
        matrix_schedule=matrix_schedule,
        grouped_attempts=grouped_raw_attempts,
    )
    recomputed_eligibility = build_eligibility_report(
        schedule=matrix_schedule,
        grouped_attempts=grouped_raw_attempts,
    )
    loaded_eligibility = EligibilityReport.model_validate_json(
        input_snapshots["eligibility"]
    )
    if loaded_eligibility != recomputed_eligibility:
        raise ValueError(
            "provided eligibility report does not match verified raw attempts"
        )
    chosen_eligibility = dataset_eligibility(
        report=recomputed_eligibility,
        dataset=dataset,
    )
    if not chosen_eligibility.eligible:
        raise ValueError(f"chosen dataset gate is ineligible: {dataset.value!r}")
    chosen_spec = dataset_spec(dataset=dataset)
    chosen_schedule_keys = dataset_schedule_keys(
        schedule=matrix_schedule,
        spec=chosen_spec,
    )

    schedule_integrity = load_schedule_integrity_bytes(
        contents=input_snapshots["schedule_integrity"]
    )
    if schedule_integrity != recomputed_schedule_integrity:
        raise ValueError(
            "provided schedule integrity does not match verified schedules/raw chronology"
        )
    attempts = load_attempts_bytes(contents=input_snapshots["attempts"])
    recomputed_attempt_records = expected_attempt_records(
        raw_attempts=raw_attempts,
        eligibility=recomputed_eligibility,
        matrix_schedule=matrix_schedule,
    )
    if attempts != recomputed_attempt_records:
        raise ValueError(
            "provided attempts CSV does not exactly match verified raw attempts/gates"
        )

    chosen_raw_attempts = select_dataset_attempts(
        attempts=raw_attempts,
        eligibility=chosen_eligibility,
        scheduled_keys=chosen_schedule_keys,
    )
    expected_manifests = tuple(attempt.manifest for attempt in chosen_raw_attempts)
    expected_predictions = tuple(
        sorted(
            (
                prediction
                for attempt in chosen_raw_attempts
                for prediction in attempt.predictions
            ),
            key=lambda item: (item.run_id, item.metric_id),
        )
    )
    manifests = load_jsonl_bytes(
        contents=input_snapshots["manifests"],
        model_type=RunManifest,
        label="harvested manifests",
    )
    predictions = load_jsonl_bytes(
        contents=input_snapshots["predictions"],
        model_type=Prediction,
        label="harvested predictions",
    )
    if manifests != expected_manifests:
        raise ValueError(
            "provided manifests are not the exact gated raw-attempt selection"
        )
    if predictions != expected_predictions:
        raise ValueError(
            "provided predictions are not the exact gated raw-attempt selection"
        )

    measurements = load_jsonl_bytes(
        contents=input_snapshots["measurements"],
        model_type=Measurement,
        label="held-out measurements",
    )
    scores = load_jsonl_bytes(
        contents=input_snapshots["scores"],
        model_type=Score,
        label="evaluator scores",
    )
    summary = load_summary_bytes(contents=input_snapshots["summary"])
    recomputed_evaluation = evaluate(
        manifests=list(manifests),
        predictions=list(predictions),
        measurements=list(measurements),
        artifact_root=artifact_root,
        ledger=ledger,
    )
    if scores != tuple(recomputed_evaluation.scores):
        raise ValueError(
            "provided evaluator scores do not match independent exact recomputation"
        )
    if summary != recomputed_evaluation.summary:
        raise ValueError(
            "provided evaluator summary does not match independent exact recomputation"
        )

    selected_attempts = select_and_validate_attempts(
        dataset=dataset,
        attempts=attempts,
        manifests=manifests,
    )
    (
        manifest_by_run,
        prediction_by_key,
        measurement_by_key,
        score_by_key,
    ) = validate_evaluator_inputs(
        manifests=manifests,
        predictions=predictions,
        measurements=measurements,
        scores=scores,
        summary=summary,
    )
    schedule_records = validate_schedule_records(
        selected_attempts=selected_attempts,
        schedule_integrity=schedule_integrity,
    )

    run_rows = build_run_status_rows(
        dataset=dataset,
        selected_attempts=selected_attempts,
        manifest_by_run=manifest_by_run,
    )
    cell_rows = build_cell_status_rows(
        dataset=dataset,
        selected_attempts=selected_attempts,
    )
    replicate_rows = build_replicate_metric_rows(
        dataset=dataset,
        selected_attempts=selected_attempts,
        manifest_by_run=manifest_by_run,
        prediction_by_key=prediction_by_key,
        measurement_by_key=measurement_by_key,
        score_by_key=score_by_key,
    )
    summary_rows = build_task_metric_summary_rows(
        dataset=dataset,
        summary=summary,
        manifests=manifests,
        scores=scores,
        measurement_by_key=measurement_by_key,
    )
    claims = build_claims(
        dataset=dataset,
        selected_attempts=selected_attempts,
        schedule_records=schedule_records,
        scores=scores,
    )
    chart_data = ChartData(dataset=dataset, records=list(replicate_rows))

    raw_integrity_contents = canonical_models_jsonl(
        models=(
            attempt.integrity
            for attempt in sorted(
                raw_attempts, key=lambda item: item.metadata.run_id
            )
        )
    )
    for role, path in input_paths.items():
        require_snapshot_unchanged(
            path=path,
            contents=input_snapshots[role],
            label=f"publication source {role}",
        )
    require_schedule_snapshots_unchanged(
        schedules_root=schedules_root,
        snapshots=schedule_snapshots,
    )
    validate_evaluator_manifest(
        root=evaluator_root,
        manifest_path=evaluator_manifest_path,
        expected_manifest_sha256=ledger.evaluator_manifest_sha256,
    )
    final_raw_attempts = discover_attempts(runs_root=runs_root, ledger=ledger)
    final_raw_integrity_contents = canonical_models_jsonl(
        models=(
            attempt.integrity
            for attempt in sorted(
                final_raw_attempts, key=lambda item: item.metadata.run_id
            )
        )
    )
    if final_raw_attempts != raw_attempts or (
        final_raw_integrity_contents != raw_integrity_contents
    ):
        raise ValueError("verified raw runs changed while publication data was assembled")

    record_counts: dict[str, int | None] = {
        "ledger": 1,
        "evaluator_manifest": len(
            input_snapshots["evaluator_manifest"].decode("utf-8").splitlines()
        ),
        "matrix": len(matrix_schedule),
        "eligibility": 1,
        "attempts": len(attempts),
        "manifests": len(manifests),
        "predictions": len(predictions),
        "measurements": len(measurements),
        "scores": len(scores),
        "summary": 1,
        "schedule_integrity": len(schedule_integrity),
    }
    logical_paths = logical_source_paths(dataset=dataset)
    source_hashes = [
        make_hash_record(
            role=role,
            path=logical_paths[role],
            contents=input_snapshots[role],
            record_count=record_counts[role],
        )
        for role in input_paths
    ]
    source_hashes.extend(
        make_hash_record(
            role=f"schedule_file:{relative_path}",
            path=f"schedules/{relative_path}",
            contents=contents,
        )
        for relative_path, contents in sorted(schedule_snapshots.items())
    )
    source_hashes.append(
        make_hash_record(
            role="raw_integrity_snapshot",
            path="raw/<verified-integrity-snapshot>",
            contents=raw_integrity_contents,
            record_count=len(raw_attempts),
        )
    )

    data_files: dict[str, bytes] = {}
    data_files["run_status.csv"] = render_csv(
        model_type=RunStatusRow,
        rows=run_rows,
    )
    data_files["cell_status.csv"] = render_csv(
        model_type=CellStatusRow,
        rows=cell_rows,
    )
    data_files["replicate_metrics.csv"] = render_csv(
        model_type=ReplicateMetricRow,
        rows=replicate_rows,
    )
    data_files["task_metric_summary.csv"] = render_csv(
        model_type=TaskMetricSummaryRow,
        rows=summary_rows,
    )
    data_files["claims.json"] = render_model_json(model=claims)
    data_files["chart_data.json"] = render_model_json(model=chart_data)
    data_output_hashes = [
        make_hash_record(
            role=f"data_output:{relative_path}",
            path=relative_path,
            contents=contents,
        )
        for relative_path, contents in sorted(data_files.items())
    ]
    gate_provenance = DatasetGateProvenance(
        dataset=dataset,
        eligible=True,
        stages=list(chosen_spec.stages),
        required_cells=chosen_spec.required_cells,
        required_replicates_per_cell=(
            chosen_spec.required_replicates_per_cell
        ),
        actual_cells=len(chosen_eligibility.cells),
        actual_scheduled_replicates=len(chosen_schedule_keys),
    )
    provenance = PublicationProvenance(
        benchmark_version=ledger.benchmark_version,
        dataset_gate=gate_provenance,
        counts=PublicationBundleCounts(
            raw_physical_attempts=len(raw_attempts),
            selected_physical_attempts=len(manifests),
            selected_scheduled_replicates=len(chosen_schedule_keys),
            selected_predictions=len(predictions),
            held_out_measurements=len(measurements),
            evaluator_scores=len(scores),
            run_status_rows=len(run_rows),
            cell_status_rows=len(cell_rows),
            replicate_metric_rows=len(replicate_rows),
            task_metric_summary_rows=len(summary_rows),
        ),
        source_hashes=source_hashes,
        data_output_hashes=data_output_hashes,
    )
    provenance_contents = render_model_json(model=provenance)
    files_with_provenance = {
        **data_files,
        "provenance.json": provenance_contents,
    }
    output_hashes = [
        make_hash_record(
            role=f"output:{relative_path}",
            path=relative_path,
            contents=contents,
        )
        for relative_path, contents in sorted(files_with_provenance.items())
    ]
    hash_manifest = PublicationHashManifest(
        dataset=dataset,
        source_hashes=source_hashes,
        output_hashes=output_hashes,
    )
    complete_files = {
        **files_with_provenance,
        "sha256_manifest.json": render_model_json(model=hash_manifest),
    }
    publish_atomic_bundle(
        output_directory=output_directory,
        files=complete_files,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analysis.publication",
        description=(
            "Validate harvested/evaluator joins and emit deterministic publication tables."
        ),
    )
    parser.add_argument(
        "--dataset",
        choices=[dataset.value for dataset in DatasetName],
        required=True,
    )
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, required=True)
    parser.add_argument("--schedule-integrity", type=Path, required=True)
    parser.add_argument("--eligibility", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--schedules-root", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--evaluator-manifest", type=Path, required=True)
    parser.add_argument("--evaluator-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(*, arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(args=arguments)
    generate_publication_tables(
        dataset=DatasetName(parsed.dataset),
        manifests_path=parsed.manifests,
        predictions_path=parsed.predictions,
        measurements_path=parsed.measurements,
        scores_path=parsed.scores,
        summary_path=parsed.summary,
        attempts_path=parsed.attempts,
        schedule_integrity_path=parsed.schedule_integrity,
        eligibility_path=parsed.eligibility,
        matrix_path=parsed.matrix,
        schedules_root=parsed.schedules_root,
        runs_root=parsed.runs_root,
        artifact_root=parsed.artifact_root,
        ledger_path=parsed.ledger,
        evaluator_manifest_path=parsed.evaluator_manifest,
        evaluator_root=parsed.evaluator_root,
        output_directory=parsed.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
