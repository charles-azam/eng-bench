from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from analysis.integrity import INFRASTRUCTURE_STATUSES
from analysis.models import (
    CellEligibility,
    DatasetEligibility,
    DatasetName,
    DatasetSpec,
    EligibilityReport,
    HarvestedAttempt,
    ScheduleReplicate,
)
from eng_bench.models import RunStatus


type ScheduledKey = tuple[str, str, str, int]
type CellKey = tuple[str, str]

DATASET_SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        dataset=DatasetName.N3,
        stages=("core-n3",),
        required_cells=4,
        required_replicates_per_cell=3,
    ),
    DatasetSpec(
        dataset=DatasetName.N5,
        stages=("core-n3", "core-extend-n5"),
        required_cells=4,
        required_replicates_per_cell=5,
    ),
    DatasetSpec(
        dataset=DatasetName.ABLATION,
        stages=("nstf-duty-ablation-n3",),
        required_cells=2,
        required_replicates_per_cell=3,
    ),
)


def load_matrix(*, matrix_path: Path) -> tuple[ScheduleReplicate, ...]:
    replicates: list[ScheduleReplicate] = []
    with matrix_path.open(mode="r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        expected_columns = [
            "stage",
            "task",
            "system",
            "first_replicate",
            "last_replicate",
        ]
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"matrix columns must be exactly {expected_columns!r}, "
                f"got {reader.fieldnames!r}"
            )
        for row in reader:
            first_replicate = int(row["first_replicate"])
            last_replicate = int(row["last_replicate"])
            if last_replicate < first_replicate:
                raise ValueError(f"invalid replicate range in matrix row: {row!r}")
            for replicate in range(first_replicate, last_replicate + 1):
                replicates.append(
                    ScheduleReplicate(
                        stage=row["stage"],
                        task=row["task"],
                        system=row["system"],
                        replicate=replicate,
                    )
                )
    keys = [replicate.key for replicate in replicates]
    if len(keys) != len(set(keys)):
        raise ValueError("matrix expands to duplicate scheduled replicates")
    if not replicates:
        raise ValueError("matrix does not contain scheduled replicates")
    return tuple(replicates)


def retry_identity(*, attempt: HarvestedAttempt) -> tuple[object, ...]:
    return (
        attempt.metadata.stage,
        attempt.metadata.task,
        attempt.metadata.system,
        attempt.metadata.replicate,
        attempt.metadata.requested_model,
        attempt.metadata.cli_version,
        attempt.metadata.effort,
        attempt.metadata.prompt_sha256,
        attempt.metadata.protocol_manifest_sha256,
        attempt.manifest.benchmark_version,
        attempt.manifest.pack_sha256,
        attempt.manifest.runner_image_sha256,
    )


def group_and_validate_attempts(
    *,
    attempts: tuple[HarvestedAttempt, ...],
    schedule: tuple[ScheduleReplicate, ...],
) -> dict[ScheduledKey, tuple[HarvestedAttempt, ...]]:
    scheduled_keys = {replicate.key for replicate in schedule}
    grouped: dict[ScheduledKey, list[HarvestedAttempt]] = defaultdict(list)
    for attempt in attempts:
        if attempt.scheduled_key not in scheduled_keys:
            raise ValueError(
                f"run is not registered in the frozen matrix: {attempt.metadata.run_id!r}"
            )
        grouped[attempt.scheduled_key].append(attempt)

    validated: dict[ScheduledKey, tuple[HarvestedAttempt, ...]] = {}
    for scheduled_key, physical_attempts in grouped.items():
        ordered = tuple(
            sorted(physical_attempts, key=lambda item: item.metadata.attempt)
        )
        attempt_numbers = [attempt.metadata.attempt for attempt in ordered]
        if attempt_numbers not in ([1], [1, 2]):
            raise ValueError(
                f"physical attempts must be exactly [1] or [1, 2] for "
                f"{scheduled_key!r}, got {attempt_numbers!r}"
            )
        first_attempt = ordered[0]
        first_is_infrastructure_failure = (
            first_attempt.manifest.status in INFRASTRUCTURE_STATUSES
        )
        if first_is_infrastructure_failure and len(ordered) != 2:
            raise ValueError(
                f"infrastructure failure was not retried exactly once: "
                f"{first_attempt.metadata.run_id!r}"
            )
        if not first_is_infrastructure_failure and len(ordered) == 2:
            raise ValueError(
                f"retry is forbidden after a non-infrastructure outcome: "
                f"{first_attempt.metadata.run_id!r}"
            )
        if len(ordered) == 2 and retry_identity(attempt=ordered[0]) != retry_identity(
            attempt=ordered[1]
        ):
            raise ValueError(
                f"retry changed frozen inputs or system configuration: {scheduled_key!r}"
            )
        if (
            len(ordered) == 2
            and ordered[1].metadata.start_time < ordered[0].metadata.end_time
        ):
            raise ValueError(
                f"retry started before the first attempt ended: {scheduled_key!r}"
            )
        validated[scheduled_key] = ordered
    return validated


def schedules_for_spec(
    *, schedule: tuple[ScheduleReplicate, ...], spec: DatasetSpec
) -> tuple[ScheduleReplicate, ...]:
    selected = tuple(item for item in schedule if item.stage in spec.stages)
    cells: dict[CellKey, list[ScheduleReplicate]] = defaultdict(list)
    for item in selected:
        cells[(item.task, item.system)].append(item)
    if len(cells) != spec.required_cells:
        raise ValueError(
            f"matrix dataset {spec.dataset.value!r} must have {spec.required_cells} cells, "
            f"got {len(cells)}"
        )
    for cell_key, cell_replicates in cells.items():
        replicate_numbers = sorted(item.replicate for item in cell_replicates)
        expected_numbers = list(range(1, spec.required_replicates_per_cell + 1))
        if replicate_numbers != expected_numbers:
            raise ValueError(
                f"matrix dataset {spec.dataset.value!r} cell {cell_key!r} must contain "
                f"replicates {expected_numbers!r}, got {replicate_numbers!r}"
            )
    return selected


def evaluate_dataset_eligibility(
    *,
    schedule: tuple[ScheduleReplicate, ...],
    grouped_attempts: dict[ScheduledKey, tuple[HarvestedAttempt, ...]],
    spec: DatasetSpec,
) -> DatasetEligibility:
    selected_schedule = schedules_for_spec(schedule=schedule, spec=spec)
    schedules_by_cell: dict[CellKey, list[ScheduleReplicate]] = defaultdict(list)
    for scheduled_replicate in selected_schedule:
        schedules_by_cell[(scheduled_replicate.task, scheduled_replicate.system)].append(
            scheduled_replicate
        )

    cells: list[CellEligibility] = []
    reasons: list[str] = []
    for (task, system), cell_schedule in sorted(schedules_by_cell.items()):
        ordered_schedule = sorted(cell_schedule, key=lambda item: item.replicate)
        expected_replicates = [item.replicate for item in ordered_schedule]
        valid_replicates: list[int] = []
        completed_replicates: list[int] = []
        missing_replicates: list[int] = []
        infrastructure_failed_replicates: list[int] = []
        physical_attempt_count = 0
        for scheduled_replicate in ordered_schedule:
            physical_attempts = grouped_attempts.get(scheduled_replicate.key, ())
            physical_attempt_count += len(physical_attempts)
            if not physical_attempts:
                missing_replicates.append(scheduled_replicate.replicate)
                continue
            final_attempt = physical_attempts[-1]
            if final_attempt.manifest.infrastructure_valid:
                valid_replicates.append(scheduled_replicate.replicate)
            else:
                infrastructure_failed_replicates.append(scheduled_replicate.replicate)
            if final_attempt.manifest.status is RunStatus.COMPLETED:
                completed_replicates.append(scheduled_replicate.replicate)

        cell_eligible = len(valid_replicates) == spec.required_replicates_per_cell
        if not cell_eligible:
            reasons.append(
                f"{system}/{task} has {len(valid_replicates)}/"
                f"{spec.required_replicates_per_cell} infrastructure-valid scheduled replicates"
            )
        cells.append(
            CellEligibility(
                task_variant=task,
                system=system,
                expected_replicates=expected_replicates,
                infrastructure_valid_replicates=valid_replicates,
                completed_replicates=completed_replicates,
                missing_replicates=missing_replicates,
                infrastructure_failed_replicates=infrastructure_failed_replicates,
                physical_attempts=physical_attempt_count,
                eligible=cell_eligible,
            )
        )

    return DatasetEligibility(
        dataset=spec.dataset,
        eligible=all(cell.eligible for cell in cells),
        required_cells=spec.required_cells,
        required_replicates_per_cell=spec.required_replicates_per_cell,
        cells=cells,
        reasons=reasons,
    )


def build_eligibility_report(
    *,
    schedule: tuple[ScheduleReplicate, ...],
    grouped_attempts: dict[ScheduledKey, tuple[HarvestedAttempt, ...]],
) -> EligibilityReport:
    datasets = [
        evaluate_dataset_eligibility(
            schedule=schedule,
            grouped_attempts=grouped_attempts,
            spec=spec,
        )
        for spec in DATASET_SPECS
    ]
    return EligibilityReport(datasets=datasets)


def dataset_schedule_keys(
    *, schedule: tuple[ScheduleReplicate, ...], spec: DatasetSpec
) -> frozenset[ScheduledKey]:
    return frozenset(
        item.key for item in schedules_for_spec(schedule=schedule, spec=spec)
    )
