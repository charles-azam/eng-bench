#!/usr/bin/env python3
"""Select the next safe action from the original frozen schedule."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


type Phase = Literal["primary", "retry"]
type SystemName = Literal["codex", "claude"]
type CanonicalStatus = Literal[
    "completed",
    "agent_failure",
    "refusal",
    "fallback_contaminated",
    "provider_failure",
    "runner_failure",
]

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
SafeIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$"),
]
HexDigest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PrefixedHexDigest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$"),
]
PositiveInteger = Annotated[int, Field(ge=1, strict=True)]

CHECKSUM_LINE = re.compile(
    pattern=r"^(?P<digest>[0-9a-f]{64})  (?P<path>[^\r\n]+)$"
)
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
INFRASTRUCTURE_STATUSES: frozenset[CanonicalStatus] = frozenset(
    {"provider_failure", "runner_failure"}
)
CLASSIFICATION_STATUSES: dict[str, frozenset[CanonicalStatus]] = {
    "complete": frozenset({"completed", "agent_failure", "runner_failure"}),
    "model_refusal": frozenset({"refusal", "runner_failure"}),
    "model_contamination": frozenset(
        {"fallback_contaminated", "runner_failure"}
    ),
    "agent_failure": frozenset({"agent_failure", "runner_failure"}),
    "timeout": frozenset({"agent_failure", "runner_failure"}),
    "infrastructure_failure": frozenset(
        {"provider_failure", "runner_failure"}
    ),
}
SCHEDULE_COLUMNS = ("sequence", "task", "system", "replicate", "stage")


class StrictModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=False,
    )


class ScheduleRow(StrictModel):
    sequence: PositiveInteger
    task: SafeIdentifier
    system: SystemName
    replicate: PositiveInteger
    stage: SafeIdentifier

    @property
    def identity(self) -> tuple[str, str, SystemName, int]:
        return (self.stage, self.task, self.system, self.replicate)

    def run_id(self, *, attempt: int) -> str:
        return (
            f"{self.stage}-{self.task}-{self.system}"
            f"-r{self.replicate:02d}-a{attempt:02d}"
        )


class AttemptMetadata(StrictModel):
    run_id: NonEmptyString
    system: SystemName
    requested_model: NonEmptyString
    cli_version: NonEmptyString
    effort: NonEmptyString
    stage: SafeIdentifier
    task: SafeIdentifier
    replicate: PositiveInteger
    attempt: PositiveInteger
    start_time: datetime
    end_time: datetime
    prompt_sha256: HexDigest
    protocol_manifest_sha256: HexDigest

    @model_validator(mode="after")
    def validate_timestamps(self) -> AttemptMetadata:
        if self.end_time < self.start_time:
            raise ValueError("attempt end_time precedes start_time")
        return self


class AttemptStatus(StrictModel):
    classification: Literal[
        "complete",
        "model_refusal",
        "model_contamination",
        "agent_failure",
        "timeout",
        "infrastructure_failure",
    ]
    detail: NonEmptyString
    exit_code: int
    canonical_status: CanonicalStatus
    prediction_normalization: NonEmptyString
    served_models: list[NonEmptyString]

    @model_validator(mode="after")
    def validate_classification_status(self) -> AttemptStatus:
        permitted_statuses = CLASSIFICATION_STATUSES[self.classification]
        if self.canonical_status not in permitted_statuses:
            raise ValueError(
                "canonical status is incompatible with runner classification"
            )
        return self


class AttemptManifest(StrictModel):
    run_id: NonEmptyString
    benchmark_version: NonEmptyString
    task_variant: SafeIdentifier
    system: SystemName
    requested_model: NonEmptyString
    served_models: list[NonEmptyString]
    cli_version: NonEmptyString
    effort: NonEmptyString
    started_at: datetime
    ended_at: datetime
    attempt: PositiveInteger
    status: CanonicalStatus
    prompt_sha256: PrefixedHexDigest
    pack_sha256: PrefixedHexDigest
    runner_image_sha256: PrefixedHexDigest
    trace_path: NonEmptyString
    artifact_paths: list[NonEmptyString]


class FinalizedAttempt(StrictModel):
    metadata: AttemptMetadata
    status: AttemptStatus
    manifest: AttemptManifest


class PlannedAction(StrictModel):
    sequence: PositiveInteger
    task: SafeIdentifier
    system: SystemName
    replicate: PositiveInteger
    stage: SafeIdentifier
    attempt: PositiveInteger

    @classmethod
    def from_row(cls, *, row: ScheduleRow, attempt: int) -> PlannedAction:
        return cls(
            sequence=row.sequence,
            task=row.task,
            system=row.system,
            replicate=row.replicate,
            stage=row.stage,
            attempt=attempt,
        )

    def to_tsv(self) -> str:
        return "\t".join(
            (
                str(self.sequence),
                self.task,
                self.system,
                str(self.replicate),
                self.stage,
                str(self.attempt),
            )
        )


def parse_positive_integer(*, raw_value: str, label: str) -> int:
    if (
        not raw_value
        or not raw_value.isascii()
        or not raw_value.isdecimal()
        or (len(raw_value) > 1 and raw_value.startswith("0"))
    ):
        raise ValueError(f"{label} must be a canonical positive integer")
    value = int(raw_value)
    if value < 1:
        raise ValueError(f"{label} must be a canonical positive integer")
    return value


def load_schedule(*, schedule_path: Path) -> tuple[ScheduleRow, ...]:
    if schedule_path.is_symlink() or not schedule_path.is_file():
        raise ValueError("schedule must be a regular non-symlink file")
    rows: list[ScheduleRow] = []
    with schedule_path.open(mode="r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t", strict=True)
        header = next(reader, None)
        if tuple(header or ()) != SCHEDULE_COLUMNS:
            raise ValueError(f"schedule columns must be exactly {SCHEDULE_COLUMNS!r}")
        for line_number, record in enumerate(reader, start=2):
            if len(record) != len(SCHEDULE_COLUMNS):
                raise ValueError(
                    f"schedule line {line_number} must contain exactly five fields"
                )
            raw_sequence, task, system, raw_replicate, stage = record
            row = ScheduleRow.model_validate(
                obj={
                    "sequence": parse_positive_integer(
                        raw_value=raw_sequence,
                        label=f"schedule line {line_number} sequence",
                    ),
                    "task": task,
                    "system": system,
                    "replicate": parse_positive_integer(
                        raw_value=raw_replicate,
                        label=f"schedule line {line_number} replicate",
                    ),
                    "stage": stage,
                }
            )
            expected_sequence = len(rows) + 1
            if row.sequence != expected_sequence:
                raise ValueError(
                    "schedule sequence must be contiguous and ordered; "
                    f"expected {expected_sequence}, found {row.sequence}"
                )
            rows.append(row)
    if not rows:
        raise ValueError("schedule must contain at least one data row")
    identities = [row.identity for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("schedule contains duplicate run identities")
    stages = {row.stage for row in rows}
    if len(stages) != 1:
        raise ValueError("one schedule may contain exactly one stage")
    return tuple(rows)


def sha256_file(*, path: Path) -> str:
    digest = hashlib.sha256()
    with path.open(mode="rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def verify_schedule_checksum(*, schedule_path: Path, checksum_path: Path) -> None:
    if checksum_path.is_symlink() or not checksum_path.is_file():
        raise ValueError("schedule checksum must be a regular non-symlink file")
    checksum_text = checksum_path.read_text(encoding="utf-8")
    checksum_lines = checksum_text.splitlines()
    if not checksum_text.endswith("\n") or len(checksum_lines) != 1:
        raise ValueError("schedule checksum must contain exactly one record")
    match = CHECKSUM_LINE.fullmatch(string=checksum_lines[0])
    if match is None:
        raise ValueError("invalid schedule checksum record")
    if match.group("path") != str(schedule_path):
        raise ValueError("schedule checksum record does not name the selected schedule")
    if sha256_file(path=schedule_path) != match.group("digest"):
        raise ValueError("selected schedule does not match its registered checksum")


def require_regular_non_symlink(*, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def require_artifact_path(*, run_directory: Path, relative_path: str) -> Path:
    candidate = run_directory
    parts = Path(relative_path).parts
    for part in parts[:-1]:
        candidate = candidate / part
        if candidate.is_symlink() or not candidate.is_dir():
            raise ValueError(
                f"artifact parent must be a regular non-symlink directory: {candidate}"
            )
    artifact_path = run_directory / relative_path
    require_regular_non_symlink(path=artifact_path, label="checksummed artifact")
    return artifact_path


def verify_artifact_ledger(
    *, run_directory: Path, runs_root: Path, run_id: str
) -> None:
    ledger_path = run_directory / "artifact.sha256"
    require_regular_non_symlink(path=ledger_path, label="artifact checksum ledger")
    ledger_text = ledger_path.read_text(encoding="utf-8")
    if not ledger_text or not ledger_text.endswith("\n"):
        raise ValueError(
            f"artifact checksum ledger must be non-empty and newline-terminated: {run_id}"
        )
    entries: list[tuple[str, str]] = []
    for line_number, line in enumerate(ledger_text.splitlines(), start=1):
        match = CHECKSUM_LINE.fullmatch(string=line)
        if match is None:
            raise ValueError(
                f"invalid artifact checksum line {line_number} for {run_id}"
            )
        entries.append((match.group("path"), match.group("digest")))
    expected_paths = tuple(
        str(runs_root / run_id / relative_path)
        for relative_path in ARTIFACT_PATHS
    )
    recorded_paths = tuple(path for path, _ in entries)
    if recorded_paths != expected_paths:
        raise ValueError(f"artifact checksum ledger file-set mismatch for {run_id}")
    mismatches: list[str] = []
    for relative_path, (_, expected_digest) in zip(
        ARTIFACT_PATHS, entries, strict=True
    ):
        artifact_path = require_artifact_path(
            run_directory=run_directory,
            relative_path=relative_path,
        )
        if sha256_file(path=artifact_path) != expected_digest:
            mismatches.append(relative_path)
    if mismatches:
        raise ValueError(
            f"artifact checksum mismatch for {run_id}: {mismatches!r}"
        )


def validate_attempt_identity(
    *,
    metadata: AttemptMetadata,
    status: AttemptStatus,
    manifest: AttemptManifest,
    row: ScheduleRow,
    attempt: int,
) -> None:
    expected_run_id = row.run_id(attempt=attempt)
    observed_identity = (
        metadata.stage,
        metadata.task,
        metadata.system,
        metadata.replicate,
        metadata.attempt,
        metadata.run_id,
    )
    expected_identity = (
        row.stage,
        row.task,
        row.system,
        row.replicate,
        attempt,
        expected_run_id,
    )
    if observed_identity != expected_identity:
        raise ValueError(
            f"attempt metadata does not match schedule row {row.sequence}: "
            f"{expected_run_id}"
        )
    manifest_identity = (
        manifest.run_id,
        manifest.task_variant,
        manifest.system,
        manifest.requested_model,
        manifest.cli_version,
        manifest.effort,
        manifest.started_at,
        manifest.ended_at,
        manifest.attempt,
        manifest.status,
        manifest.prompt_sha256,
        manifest.trace_path,
        manifest.served_models,
    )
    expected_manifest_identity = (
        metadata.run_id,
        metadata.task,
        metadata.system,
        metadata.requested_model,
        metadata.cli_version,
        metadata.effort,
        metadata.start_time,
        metadata.end_time,
        metadata.attempt,
        status.canonical_status,
        f"sha256:{metadata.prompt_sha256}",
        f"{metadata.run_id}/events.jsonl",
        status.served_models,
    )
    if manifest_identity != expected_manifest_identity:
        raise ValueError(
            f"attempt manifest, metadata, and status disagree for {expected_run_id}"
        )
    expected_artifact_prefix = f"{expected_run_id}/workspace/"
    if (
        len(manifest.artifact_paths) != len(set(manifest.artifact_paths))
        or manifest.artifact_paths != sorted(manifest.artifact_paths)
        or any(
            not path.startswith(expected_artifact_prefix)
            for path in manifest.artifact_paths
        )
    ):
        raise ValueError(f"invalid manifest artifact paths for {expected_run_id}")


def load_finalized_attempt(
    *, row: ScheduleRow, attempt: int, runs_root: Path
) -> FinalizedAttempt | None:
    run_id = row.run_id(attempt=attempt)
    run_directory = runs_root / run_id
    if not run_directory.exists() and not run_directory.is_symlink():
        return None
    if run_directory.is_symlink() or not run_directory.is_dir():
        raise ValueError(
            f"attempt path must be a regular non-symlink directory: {run_id}"
        )
    verify_artifact_ledger(
        run_directory=run_directory,
        runs_root=runs_root,
        run_id=run_id,
    )
    metadata = AttemptMetadata.model_validate_json(
        json_data=(run_directory / "metadata.json").read_bytes(),
        strict=True,
    )
    status = AttemptStatus.model_validate_json(
        json_data=(run_directory / "status.json").read_bytes(),
        strict=True,
    )
    manifest = AttemptManifest.model_validate_json(
        json_data=(run_directory / "manifest.jsonl").read_bytes(),
        strict=True,
    )
    validate_attempt_identity(
        metadata=metadata,
        status=status,
        manifest=manifest,
        row=row,
        attempt=attempt,
    )
    return FinalizedAttempt(metadata=metadata, status=status, manifest=manifest)


def validate_retry_frozen_identity(
    *, primary: FinalizedAttempt, retry: FinalizedAttempt, row: ScheduleRow
) -> None:
    metadata_fields = (
        "system",
        "requested_model",
        "cli_version",
        "effort",
        "stage",
        "task",
        "replicate",
        "prompt_sha256",
        "protocol_manifest_sha256",
    )
    manifest_fields = (
        "benchmark_version",
        "task_variant",
        "system",
        "requested_model",
        "cli_version",
        "effort",
        "prompt_sha256",
        "pack_sha256",
        "runner_image_sha256",
    )
    mismatches = [
        f"metadata.{field}"
        for field in metadata_fields
        if getattr(primary.metadata, field) != getattr(retry.metadata, field)
    ]
    mismatches.extend(
        f"manifest.{field}"
        for field in manifest_fields
        if getattr(primary.manifest, field) != getattr(retry.manifest, field)
    )
    if mismatches:
        raise ValueError(
            "retry differs from its first attempt on frozen fields at "
            f"schedule row {row.sequence}: {mismatches!r}"
        )


def reject_unregistered_attempt_numbers(
    *, rows: tuple[ScheduleRow, ...], runs_root: Path
) -> None:
    run_bases = {
        row.run_id(attempt=1).removesuffix("-a01"): row.sequence for row in rows
    }
    for entry in runs_root.iterdir():
        base, separator, raw_attempt = entry.name.rpartition("-a")
        if separator != "-a" or base not in run_bases or not raw_attempt.isdecimal():
            continue
        if raw_attempt not in {"01", "02"}:
            raise ValueError(
                "only registered attempts a01 and a02 are permitted for "
                f"schedule row {run_bases[base]}: {entry.name}"
            )


def next_action(
    *, rows: tuple[ScheduleRow, ...], runs_root: Path, phase: Phase
) -> PlannedAction | None:
    if runs_root.is_symlink() or not runs_root.is_dir():
        raise ValueError("runs root must be a regular non-symlink directory")
    reject_unregistered_attempt_numbers(rows=rows, runs_root=runs_root)
    primary_statuses = tuple(
        load_finalized_attempt(row=row, attempt=1, runs_root=runs_root)
        for row in rows
    )
    first_missing_primary = next(
        (
            index
            for index, status in enumerate(primary_statuses)
            if status is None
        ),
        None,
    )
    if first_missing_primary is not None and any(
        status is not None for status in primary_statuses[first_missing_primary + 1 :]
    ):
        raise ValueError("first-attempt directories do not form a schedule prefix")

    retry_statuses = tuple(
        load_finalized_attempt(row=row, attempt=2, runs_root=runs_root)
        for row in rows
    )
    if first_missing_primary is not None:
        if any(status is not None for status in retry_statuses):
            raise ValueError("a retry exists before the first-attempt schedule closed")
        if phase == "retry":
            raise ValueError(
                "retry phase is unavailable until every first attempt is finalized"
            )
        return PlannedAction.from_row(
            row=rows[first_missing_primary],
            attempt=1,
        )

    eligible_indices = tuple(
        index
        for index, status in enumerate(primary_statuses)
        if status is not None
        and status.status.canonical_status in INFRASTRUCTURE_STATUSES
    )
    for index, retry_status in enumerate(retry_statuses):
        if retry_status is not None and index not in eligible_indices:
            raise ValueError(
                "retry exists for a non-infrastructure first attempt at "
                f"schedule row {rows[index].sequence}"
            )
        if retry_status is not None:
            primary_status = primary_statuses[index]
            if primary_status is None:
                raise ValueError("internal error: retry has no first attempt")
            validate_retry_frozen_identity(
                primary=primary_status,
                retry=retry_status,
                row=rows[index],
            )
    existing_eligible_retries = tuple(
        retry_statuses[index] is not None for index in eligible_indices
    )
    first_missing_retry = next(
        (
            index
            for index, exists in enumerate(existing_eligible_retries)
            if not exists
        ),
        None,
    )
    if first_missing_retry is not None and any(
        existing_eligible_retries[first_missing_retry + 1 :]
    ):
        raise ValueError("retry directories do not form the eligible schedule prefix")

    if phase == "primary" or first_missing_retry is None:
        return None
    schedule_index = eligible_indices[first_missing_retry]
    return PlannedAction.from_row(row=rows[schedule_index], attempt=2)


def parse_arguments(
    *, arguments: Sequence[str] | None = None
) -> tuple[Path, Path, Path, Phase]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", required=True, type=Path)
    parser.add_argument("--checksum", required=True, type=Path)
    parser.add_argument("--runs-root", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("primary", "retry"))
    parsed = parser.parse_args(args=arguments)
    return (
        Path(parsed.schedule),
        Path(parsed.checksum),
        Path(parsed.runs_root),
        parsed.phase,
    )


def main(*, arguments: Sequence[str] | None = None) -> int:
    schedule_path, checksum_path, runs_root, phase = parse_arguments(
        arguments=arguments
    )
    verify_schedule_checksum(
        schedule_path=schedule_path,
        checksum_path=checksum_path,
    )
    rows = load_schedule(schedule_path=schedule_path)
    action = next_action(rows=rows, runs_root=runs_root, phase=phase)
    if action is not None:
        sys.stdout.write(action.to_tsv() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
