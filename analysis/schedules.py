from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

from analysis.eligibility import ScheduledKey
from analysis.integrity import (
    parse_checksum_lines,
    require_regular_non_symlink,
    sha256_file,
)
from analysis.models import (
    HarvestedAttempt,
    ScheduleIntegrityRecord,
    ScheduledLaunch,
    ScheduleReplicate,
)
from eng_bench.models import Sha256


SCHEDULE_SEED = 20260711
PROTOCOL_STAGE_ORDER: tuple[str, ...] = (
    "core-n3",
    "core-extend-n5",
    "nstf-duty-ablation-n3",
)


def expected_stage_launches(
    *, schedule: tuple[ScheduleReplicate, ...], stage: str
) -> tuple[ScheduleReplicate, ...]:
    launches = [item for item in schedule if item.stage == stage]
    random.Random(SCHEDULE_SEED).shuffle(launches)
    return tuple(launches)


def load_schedule_file(*, path: Path) -> tuple[ScheduledLaunch, ...]:
    require_regular_non_symlink(path=path, label="stage schedule")
    launches: list[ScheduledLaunch] = []
    with path.open(mode="r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        expected_columns = ["sequence", "task", "system", "replicate", "stage"]
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"schedule columns must be exactly {expected_columns!r}, "
                f"got {reader.fieldnames!r} in {path}"
            )
        for row in reader:
            launches.append(
                ScheduledLaunch(
                    sequence=int(row["sequence"]),
                    task=row["task"],
                    system=row["system"],
                    replicate=int(row["replicate"]),
                    stage=row["stage"],
                )
            )
    sequences = [launch.sequence for launch in launches]
    expected_sequences = list(range(1, len(launches) + 1))
    if sequences != expected_sequences:
        raise ValueError(
            f"schedule sequence must be unique and exactly 1..N in {path}: "
            f"got {sequences!r}"
        )
    keys = [launch.key for launch in launches]
    if len(keys) != len(set(keys)):
        raise ValueError(f"schedule contains duplicate launch rows: {path}")
    return tuple(launches)


def verify_schedule_checksum(
    *,
    schedule_path: Path,
    checksum_path: Path,
    permitted_recorded_paths: frozenset[str],
) -> Sha256:
    require_regular_non_symlink(path=checksum_path, label="schedule checksum ledger")
    entries = parse_checksum_lines(ledger_path=checksum_path)
    if len(entries) != 1:
        raise ValueError(f"schedule checksum ledger must contain one entry: {checksum_path}")
    recorded_path, recorded_digest = entries[0]
    if recorded_path not in permitted_recorded_paths:
        raise ValueError(
            f"schedule checksum path has the wrong sidecar semantics in {checksum_path}: "
            f"{recorded_path!r}"
        )
    actual_sha256 = sha256_file(path=schedule_path)
    if actual_sha256.removeprefix("sha256:") != recorded_digest:
        raise ValueError(f"schedule checksum mismatch: {schedule_path}")
    return actual_sha256


def discover_schedule_stages(*, schedules_root: Path) -> tuple[str, ...]:
    if schedules_root.is_symlink() or not schedules_root.is_dir():
        raise ValueError(
            f"schedules root must be a regular non-symlink directory: {schedules_root}"
        )
    schedule_stages: set[str] = set()
    portable_checksum_stages: set[str] = set()
    vps_checksum_stages: set[str] = set()
    for entry in sorted(schedules_root.iterdir(), key=lambda path: path.name):
        if entry.is_symlink() or not entry.is_file():
            raise ValueError(f"schedules root may contain only regular files: {entry}")
        if entry.name == "README.md":
            continue
        if entry.name.endswith(".tsv.vps.sha256"):
            vps_checksum_stages.add(entry.name.removesuffix(".tsv.vps.sha256"))
        elif entry.name.endswith(".tsv.sha256"):
            portable_checksum_stages.add(entry.name.removesuffix(".tsv.sha256"))
        elif entry.name.endswith(".tsv"):
            schedule_stages.add(entry.name.removesuffix(".tsv"))
        else:
            raise ValueError(f"unexpected file in schedules root: {entry.name!r}")
    if schedule_stages != portable_checksum_stages:
        raise ValueError(
            f"every stage schedule needs exactly one portable checksum ledger: "
            f"schedules={sorted(schedule_stages)!r}, "
            f"portable_checksums={sorted(portable_checksum_stages)!r}"
        )
    orphaned_vps_checksums = vps_checksum_stages - schedule_stages
    if orphaned_vps_checksums:
        raise ValueError(
            f"VPS checksum sidecars lack stage schedules: "
            f"{sorted(orphaned_vps_checksums)!r}"
        )
    unknown_stages = schedule_stages - set(PROTOCOL_STAGE_ORDER)
    if unknown_stages:
        raise ValueError(f"unknown scheduled stages: {sorted(unknown_stages)!r}")
    return tuple(stage for stage in PROTOCOL_STAGE_ORDER if stage in schedule_stages)


def validate_schedule_rows(
    *,
    stage: str,
    launches: tuple[ScheduledLaunch, ...],
    matrix_schedule: tuple[ScheduleReplicate, ...],
) -> None:
    if any(launch.stage != stage for launch in launches):
        raise ValueError(f"schedule {stage!r} contains a row for another stage")
    expected = expected_stage_launches(schedule=matrix_schedule, stage=stage)
    expected_keys = [item.key for item in expected]
    actual_keys = [item.key for item in launches]
    if actual_keys != expected_keys:
        raise ValueError(
            f"schedule {stage!r} rows/order do not match the frozen matrix and seed"
        )


def validate_first_attempt_order(
    *,
    stage: str,
    launches: tuple[ScheduledLaunch, ...],
    grouped_attempts: dict[ScheduledKey, tuple[HarvestedAttempt, ...]],
    schedule_sha256: Sha256,
) -> ScheduleIntegrityRecord:
    first_attempts = [
        grouped_attempts[launch.key][0] if launch.key in grouped_attempts else None
        for launch in launches
    ]
    present_count = sum(attempt is not None for attempt in first_attempts)
    if any(
        attempt is not None
        for attempt in first_attempts[present_count:]
    ):
        raise ValueError(
            f"first attempts for stage {stage!r} are not a prefix of the frozen schedule"
        )
    launched = tuple(
        attempt for attempt in first_attempts[:present_count] if attempt is not None
    )
    for previous, current in zip(launched, launched[1:], strict=False):
        if current.metadata.start_time < previous.metadata.end_time:
            raise ValueError(
                f"first-attempt chronology violates schedule order in stage {stage!r}: "
                f"{current.metadata.run_id!r} started before {previous.metadata.run_id!r} ended"
            )
    return ScheduleIntegrityRecord(
        stage=stage,
        schedule_sha256=schedule_sha256,
        scheduled_replicates=len(launches),
        launched_first_attempts=len(launched),
        complete_launch_prefix=len(launched) == len(launches),
        first_started_at=launched[0].metadata.start_time if launched else None,
        last_first_attempt_ended_at=(
            launched[-1].metadata.end_time if launched else None
        ),
    )


def validate_stage_chronology(
    *,
    matrix_schedule: tuple[ScheduleReplicate, ...],
    grouped_attempts: dict[ScheduledKey, tuple[HarvestedAttempt, ...]],
) -> None:
    schedules_by_stage: dict[str, list[ScheduleReplicate]] = defaultdict(list)
    for scheduled_replicate in matrix_schedule:
        schedules_by_stage[scheduled_replicate.stage].append(scheduled_replicate)
    for prior_stage, later_stage in zip(
        PROTOCOL_STAGE_ORDER,
        PROTOCOL_STAGE_ORDER[1:],
        strict=False,
    ):
        later_first_attempts = [
            grouped_attempts[item.key][0]
            for item in schedules_by_stage[later_stage]
            if item.key in grouped_attempts
        ]
        if not later_first_attempts:
            continue
        missing_prior = [
            item.key
            for item in schedules_by_stage[prior_stage]
            if item.key not in grouped_attempts
        ]
        if missing_prior:
            raise ValueError(
                f"stage {later_stage!r} launched before all {prior_stage!r} "
                f"scheduled replicates had final attempts: missing={missing_prior!r}"
            )
        prior_final_attempts = [
            grouped_attempts[item.key][-1] for item in schedules_by_stage[prior_stage]
        ]
        last_prior_end = max(
            attempt.metadata.end_time for attempt in prior_final_attempts
        )
        first_later_start = min(
            attempt.metadata.start_time for attempt in later_first_attempts
        )
        if first_later_start < last_prior_end:
            raise ValueError(
                f"stage {later_stage!r} started before {prior_stage!r} final attempts ended"
            )


def verify_schedules(
    *,
    schedules_root: Path,
    matrix_schedule: tuple[ScheduleReplicate, ...],
    grouped_attempts: dict[ScheduledKey, tuple[HarvestedAttempt, ...]],
) -> tuple[ScheduleIntegrityRecord, ...]:
    present_stages = discover_schedule_stages(schedules_root=schedules_root)
    attempted_stages = {
        stage for stage, _, _, _ in grouped_attempts
    }
    missing_schedules = attempted_stages - set(present_stages)
    if missing_schedules:
        raise ValueError(
            f"launched stages are missing frozen schedules: {sorted(missing_schedules)!r}"
        )

    records: list[ScheduleIntegrityRecord] = []
    for stage in present_stages:
        schedule_path = schedules_root / f"{stage}.tsv"
        checksum_path = schedules_root / f"{stage}.tsv.sha256"
        schedule_sha256 = verify_schedule_checksum(
            schedule_path=schedule_path,
            checksum_path=checksum_path,
            permitted_recorded_paths=frozenset(
                {schedule_path.name, f"./{schedule_path.name}"}
            ),
        )
        vps_checksum_path = schedules_root / f"{stage}.tsv.vps.sha256"
        if vps_checksum_path.exists() or vps_checksum_path.is_symlink():
            vps_schedule_sha256 = verify_schedule_checksum(
                schedule_path=schedule_path,
                checksum_path=vps_checksum_path,
                permitted_recorded_paths=frozenset(
                    {f"/root/bench-v2/schedules/{schedule_path.name}"}
                ),
            )
            if vps_schedule_sha256 != schedule_sha256:
                raise ValueError(
                    f"portable and VPS schedule checksums disagree for {stage!r}"
                )
        launches = load_schedule_file(path=schedule_path)
        validate_schedule_rows(
            stage=stage,
            launches=launches,
            matrix_schedule=matrix_schedule,
        )
        record = validate_first_attempt_order(
            stage=stage,
            launches=launches,
            grouped_attempts=grouped_attempts,
            schedule_sha256=schedule_sha256,
        )
        records.append(record)
    validate_stage_chronology(
        matrix_schedule=matrix_schedule,
        grouped_attempts=grouped_attempts,
    )
    return tuple(records)
