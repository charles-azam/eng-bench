from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import hashlib
import io
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from analysis.eligibility import (
    ScheduledKey,
    group_and_validate_attempts,
)
from analysis.harvest import discover_attempts
from analysis.integrity import (
    CHECKSUM_LINE,
    normalize_tree_ledger_path,
)
from analysis.models import (
    HarvestedAttempt,
    IntegrityRecord,
    ScheduleIntegrityRecord,
    ScheduleReplicate,
    ScheduledLaunch,
)
from analysis.schedules import (
    PROTOCOL_STAGE_ORDER,
    validate_first_attempt_order,
    validate_schedule_rows,
    validate_stage_chronology,
)
from eng_bench.models import FrozenLedger, RunStatus, Sha256


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
ShortRationale = Annotated[str, StringConstraints(min_length=1, max_length=500)]
NonNegativeInteger = Annotated[int, Field(ge=0)]

FROZEN_RUBRIC_DIGEST = (
    "a5b8bd328188607f6aa286e18328c0413a761ab192fe3621258bc4bb978f95c5"
)
FROZEN_RUBRIC_SHA256 = cast(Sha256, f"sha256:{FROZEN_RUBRIC_DIGEST}")


class StrictReviewModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class ReviewStatus(StrEnum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class PacketFileRole(StrEnum):
    TASK_CONTEXT = "task_context"
    SUBMITTED_OUTPUT = "submitted_output"


class RubricItem(StrictReviewModel):
    item_id: NonEmptyString
    criterion: NonEmptyString


RUBRIC_ITEMS: tuple[RubricItem, ...] = (
    RubricItem(
        item_id="required_note",
        criterion="the required calculation note exists and is readable",
    ),
    RubricItem(
        item_id="balances_and_boundaries",
        criterion=(
            "governing balances and boundary conditions are stated clearly enough to audit"
        ),
    ),
    RubricItem(
        item_id="assumption_provenance",
        criterion="supplied, inferred, and outside-annex assumptions are distinguished",
    ),
    RubricItem(
        item_id="uncertainty_traceability",
        criterion=(
            "uncertainty intervals are connected to named assumptions or sensitivities"
        ),
    ),
    RubricItem(
        item_id="independent_check",
        criterion=(
            "at least one independent energy/convergence check is shown where the task "
            "requests it"
        ),
    ),
    RubricItem(
        item_id="artifacts_and_offline_scripts",
        criterion=(
            "cited output artifacts exist and scripts run offline in the frozen environment "
            "when applicable"
        ),
    ),
    RubricItem(
        item_id="evidence_calibration",
        criterion=(
            "conclusions do not claim precision or identifiability beyond the supplied evidence"
        ),
    ),
    RubricItem(
        item_id="no_unavailable_access",
        criterion=(
            "no attempt is made to access unavailable measurements, reports, old runs, or "
            "arbitrary network"
        ),
    ),
)

REVIEW_FIELDNAMES: tuple[str, ...] = (
    "neutral_label",
    "packet_sha256",
    "task_variant",
    "item_id",
    "criterion",
    "status",
    "rationale",
)

REVIEW_INSTRUCTIONS = """# Blinded artifact-review instructions

Review only the task context and submitted output in each neutral packet. Do not open or publish
the sealed mapping until every row in `review.csv` is complete and its bytes have been frozen.

Use only `pass`, `partial`, `fail`, or `not_applicable`, with a short rationale for every item.

- Item 6: if no submitted script is applicable, a `pass` rationale must use
  `No applicable scripts: Cited artifacts verified: ...`. If a script is applicable, a `pass`
  requires actually running it with an offline sandbox command in an environment whose regenerated
  environment manifest matches the packet's `runner_image_sha256`; record
  `Offline command: ...; Runner manifest: sha256:...; Result: ...`. The packet generator does not
  execute submitted scripts.
- Item 8: raw traces and proxy logs are deliberately absent. Use `not_applicable` unless the
  submitted artifact itself records an access attempt. This item can never pass from artifact-only
  review. Use `partial` or `fail` with a rationale beginning `Submitted artifact evidence:` when
  such evidence exists. Report sandbox/proxy enforcement separately from this artifact judgment.

Exact identity strings are blocked during preparation, but prose, formatting, and tool conventions
can still suggest identity. This is a sole-reviewer assessment without independent adjudication.
"""


class RegularSnapshot(StrictReviewModel):
    path: Path
    data: bytes = Field(repr=False)
    sha256: Sha256
    size_bytes: NonNegativeInteger
    mode: NonNegativeInteger


class HashedSourceFile(StrictReviewModel):
    name: NonEmptyString
    sha256: Sha256


class ScheduleSource(StrictReviewModel):
    stage: NonEmptyString
    schedule_sha256: Sha256
    portable_checksum_sha256: Sha256
    vps_checksum_sha256: Sha256 | None = None
    integrity: ScheduleIntegrityRecord


class PacketFile(StrictReviewModel):
    role: PacketFileRole
    relative_path: NonEmptyString
    sha256: Sha256
    size_bytes: NonNegativeInteger


class PacketPayload(StrictReviewModel):
    schema_version: Literal["2.0"] = "2.0"
    neutral_label: NonEmptyString
    task_variant: NonEmptyString
    benchmark_version: NonEmptyString
    pack_sha256: Sha256
    runner_image_sha256: Sha256
    rubric_source_sha256: Sha256
    files: list[PacketFile]


class PacketManifest(PacketPayload):
    packet_sha256: Sha256


class BundlePacket(StrictReviewModel):
    neutral_label: NonEmptyString
    task_variant: NonEmptyString
    packet_sha256: Sha256


class ReviewBundleManifest(StrictReviewModel):
    schema_version: Literal["2.0"] = "2.0"
    ledger_sha256: Sha256
    matrix_sha256: Sha256
    rubric_source_sha256: Sha256
    schedule_files: list[HashedSourceFile]
    packets: list[BundlePacket]


class SnapshotFile(StrictReviewModel):
    role: PacketFileRole
    source_relative_path: NonEmptyString
    packet_relative_path: NonEmptyString
    data: bytes = Field(repr=False)
    sha256: Sha256
    size_bytes: NonNegativeInteger
    mode: NonNegativeInteger


class PacketBlueprint(StrictReviewModel):
    attempt: HarvestedAttempt
    files: list[SnapshotFile]


class CampaignSelection(StrictReviewModel):
    ledger_snapshot: RegularSnapshot
    matrix_snapshot: RegularSnapshot
    rubric_snapshot: RegularSnapshot
    schedule_files: list[HashedSourceFile]
    schedules: list[ScheduleSource]
    campaign_attempts: list[HarvestedAttempt]
    attempts: list[HarvestedAttempt]


class SealedFileMapping(StrictReviewModel):
    role: PacketFileRole
    packet_relative_path: NonEmptyString
    source_relative_path: NonEmptyString
    sha256: Sha256
    size_bytes: NonNegativeInteger


class SealedPacketMapping(StrictReviewModel):
    neutral_label: NonEmptyString
    packet_sha256: Sha256
    run_id: NonEmptyString
    system: NonEmptyString
    task_variant: NonEmptyString
    run_status: RunStatus
    benchmark_version: NonEmptyString
    pack_sha256: Sha256
    runner_image_sha256: Sha256
    integrity: IntegrityRecord
    files: list[SealedFileMapping]


class CampaignAttemptProvenance(StrictReviewModel):
    run_id: NonEmptyString
    run_status: RunStatus
    infrastructure_valid: bool
    included_in_review: bool
    integrity: IntegrityRecord


class SealedMapping(StrictReviewModel):
    schema_version: Literal["2.0"] = "2.0"
    generation_nonce: NonEmptyString
    ledger_sha256: Sha256
    matrix_sha256: Sha256
    rubric_source_sha256: Sha256
    schedule_files: list[HashedSourceFile]
    schedules: list[ScheduleSource]
    campaign_attempts: list[CampaignAttemptProvenance]
    packets: list[SealedPacketMapping]


class CompletedReviewRow(StrictReviewModel):
    neutral_label: NonEmptyString
    packet_sha256: Sha256
    task_variant: NonEmptyString
    item_id: NonEmptyString
    criterion: NonEmptyString
    status: ReviewStatus
    rationale: ShortRationale


class PublicReviewItem(StrictReviewModel):
    schema_version: Literal["2.0"] = "2.0"
    completed_review_sha256: Sha256
    run_id: NonEmptyString
    system: NonEmptyString
    task_variant: NonEmptyString
    run_status: RunStatus
    packet_sha256: Sha256
    item_id: NonEmptyString
    criterion: NonEmptyString
    status: ReviewStatus
    rationale: ShortRationale


class PublicRunMapping(StrictReviewModel):
    neutral_label: NonEmptyString
    packet_sha256: Sha256
    run_id: NonEmptyString
    system: NonEmptyString
    task_variant: NonEmptyString
    run_status: RunStatus
    benchmark_version: NonEmptyString
    pack_sha256: Sha256
    runner_image_sha256: Sha256
    integrity: IntegrityRecord
    files: list[SealedFileMapping]


class PublicFileHash(StrictReviewModel):
    name: NonEmptyString
    sha256: Sha256


class PublicProvenance(StrictReviewModel):
    schema_version: Literal["2.0"] = "2.0"
    completed_review_sha256: Sha256
    sealed_mapping_sha256: Sha256
    ledger_sha256: Sha256
    matrix_sha256: Sha256
    rubric_source_sha256: Sha256
    schedule_files: list[HashedSourceFile]
    schedules: list[ScheduleSource]
    campaign_attempts: list[CampaignAttemptProvenance]
    runs: list[PublicRunMapping]
    public_files: list[PublicFileHash]


def canonical_json(*, value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def serialize_model(*, model: BaseModel) -> str:
    return canonical_json(value=model.model_dump(mode="json"))


def sha256_bytes(*, value: bytes) -> Sha256:
    digest = hashlib.sha256(value).hexdigest()
    return cast(Sha256, f"sha256:{digest}")


def read_regular_snapshot(*, path: Path, label: str) -> RegularSnapshot:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, mode="rb", closefd=True) as stream:
        file_stat = os.fstat(stream.fileno())
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"{label} must remain a regular file while opened: {path}")
        data = stream.read()
    return RegularSnapshot(
        path=path,
        data=data,
        sha256=sha256_bytes(value=data),
        size_bytes=len(data),
        mode=stat.S_IMODE(file_stat.st_mode),
    )


def decode_utf8(*, snapshot: RegularSnapshot, label: str) -> str:
    return snapshot.data.decode(encoding="utf-8", errors="strict")


def validate_registered_rubric_items(*, snapshot: RegularSnapshot) -> None:
    lines = set(decode_utf8(snapshot=snapshot, label="registered rubric").splitlines())
    expected_lines = {
        f"{index}. {item.criterion}{';' if index < len(RUBRIC_ITEMS) else '.'}"
        for index, item in enumerate(RUBRIC_ITEMS, start=1)
    }
    if not expected_lines.issubset(lines):
        raise ValueError("hard-coded review items do not match the frozen rubric source")


def path_exists_including_symlink(*, path: Path) -> bool:
    return os.path.lexists(path)


def validate_ancestor_directories(*, path: Path) -> None:
    absolute_path = path.absolute()
    current = Path(absolute_path.anchor)
    for component in absolute_path.parts[1:-1]:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"destination ancestor must not be a symlink: {current}")
        if not current.is_dir():
            raise ValueError(f"destination parent directory does not exist: {current}")


def require_new_destination(*, path: Path, label: str) -> None:
    validate_ancestor_directories(path=path)
    if path_exists_including_symlink(path=path):
        raise ValueError(f"{label} destination must not already exist: {path}")


def require_outside_directory(*, path: Path, directory: Path, label: str) -> None:
    resolved_path = path.resolve(strict=False)
    resolved_directory = directory.resolve(strict=False)
    if resolved_path == resolved_directory or resolved_path.is_relative_to(resolved_directory):
        raise ValueError(f"{label} must be outside protected directory {directory}")


def require_mapping_separation(
    *, review_bundle: Path, sealed_mapping_path: Path
) -> None:
    require_outside_directory(
        path=sealed_mapping_path,
        directory=review_bundle.parent,
        label="sealed mapping",
    )


def fsync_directory(*, path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_exclusive_bytes(*, path: Path, data: bytes, mode: int = 0o644) -> os.stat_result:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    with os.fdopen(descriptor, mode="wb", closefd=True) as stream:
        stream.write(data)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fsync(stream.fileno())
        file_stat = os.fstat(stream.fileno())
    written_snapshot = read_regular_snapshot(path=path, label="newly written output")
    if written_snapshot.data != data or written_snapshot.mode != mode:
        raise ValueError(f"newly written output failed byte/mode verification: {path}")
    return file_stat


def write_exclusive_text(*, path: Path, text: str, mode: int = 0o644) -> os.stat_result:
    return write_exclusive_bytes(path=path, data=text.encode(encoding="utf-8"), mode=mode)


def remove_owned_file(*, path: Path, expected_stat: os.stat_result) -> None:
    if not path_exists_including_symlink(path=path) or path.is_symlink():
        return
    current_stat = path.stat(follow_symlinks=False)
    if (
        current_stat.st_dev == expected_stat.st_dev
        and current_stat.st_ino == expected_stat.st_ino
    ):
        path.unlink()


def rename_directory_exclusive(*, source: Path, destination: Path) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin":
        rename_function = library.renamex_np
        rename_function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename_function.restype = ctypes.c_int
        result = rename_function(source_bytes, destination_bytes, 0x00000004)
    elif sys.platform.startswith("linux"):
        rename_function = library.renameat2
        rename_function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename_function.restype = ctypes.c_int
        result = rename_function(-100, source_bytes, -100, destination_bytes, 1)
    else:
        raise RuntimeError(
            f"atomic no-replace directory publication is unsupported on {sys.platform!r}"
        )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(error_number, os.strerror(error_number), destination)
        raise OSError(error_number, os.strerror(error_number), destination)


def fsync_tree(*, root: Path) -> None:
    directories = [root]
    for directory, directory_names, _ in root.walk(top_down=True, follow_symlinks=False):
        directories.extend(directory / name for name in directory_names)
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        fsync_directory(path=directory)


def parse_tree_checksum_snapshot(
    *, snapshot: RegularSnapshot
) -> tuple[tuple[str, str], ...]:
    text = decode_utf8(snapshot=snapshot, label="tree checksum ledger")
    if not text or not text.endswith("\n"):
        raise ValueError(f"checksum ledger must be non-empty and newline-terminated: {snapshot.path}")
    entries: list[tuple[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = CHECKSUM_LINE.fullmatch(string=line)
        if match is None:
            raise ValueError(f"invalid checksum line {line_number} in {snapshot.path}")
        relative_path = normalize_tree_ledger_path(
            raw_path=match.group("path"),
            ledger_path=snapshot.path,
        )
        entries.append((relative_path, match.group("digest")))
    paths = [path for path, _ in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError(f"checksum ledger paths must be unique and sorted: {snapshot.path}")
    return tuple(entries)


def parse_single_checksum_snapshot(
    *, snapshot: RegularSnapshot
) -> tuple[str, str]:
    text = decode_utf8(snapshot=snapshot, label="schedule checksum ledger")
    lines = text.splitlines()
    if not text.endswith("\n") or len(lines) != 1:
        raise ValueError(f"schedule checksum ledger must contain exactly one line: {snapshot.path}")
    match = CHECKSUM_LINE.fullmatch(string=lines[0])
    if match is None:
        raise ValueError(f"invalid schedule checksum ledger: {snapshot.path}")
    return match.group("path"), match.group("digest")


def load_matrix_snapshot(*, snapshot: RegularSnapshot) -> tuple[ScheduleReplicate, ...]:
    replicates: list[ScheduleReplicate] = []
    stream = io.StringIO(decode_utf8(snapshot=snapshot, label="frozen matrix"), newline="")
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
            f"matrix columns must be exactly {expected_columns!r}, got {reader.fieldnames!r}"
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
    if not replicates or len(keys) != len(set(keys)):
        raise ValueError("matrix must expand to a non-empty unique replicate set")
    return tuple(replicates)


def load_schedule_snapshot(*, snapshot: RegularSnapshot) -> tuple[ScheduledLaunch, ...]:
    launches: list[ScheduledLaunch] = []
    stream = io.StringIO(decode_utf8(snapshot=snapshot, label="stage schedule"), newline="")
    reader = csv.DictReader(stream, delimiter="\t")
    expected_columns = ["sequence", "task", "system", "replicate", "stage"]
    if reader.fieldnames != expected_columns:
        raise ValueError(
            f"schedule columns must be exactly {expected_columns!r}, got {reader.fieldnames!r}"
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
    if sequences != list(range(1, len(launches) + 1)):
        raise ValueError(f"schedule sequence must be exactly 1..N: {snapshot.path}")
    keys = [launch.key for launch in launches]
    if len(keys) != len(set(keys)):
        raise ValueError(f"schedule contains duplicate rows: {snapshot.path}")
    return tuple(launches)


def snapshot_schedule_root(
    *, schedules_root: Path
) -> dict[str, RegularSnapshot]:
    if schedules_root.is_symlink() or not schedules_root.is_dir():
        raise ValueError(
            f"schedules root must be a regular non-symlink directory: {schedules_root}"
        )
    initial_names = tuple(sorted(entry.name for entry in schedules_root.iterdir()))
    snapshots: dict[str, RegularSnapshot] = {}
    for name in initial_names:
        path = schedules_root / name
        snapshots[name] = read_regular_snapshot(path=path, label="schedule provenance file")
    final_names = tuple(sorted(entry.name for entry in schedules_root.iterdir()))
    if final_names != initial_names:
        raise ValueError("schedules root changed while it was being snapshotted")
    return snapshots


def verify_campaign_schedules(
    *,
    schedules_root: Path,
    matrix_schedule: tuple[ScheduleReplicate, ...],
    grouped_attempts: dict[ScheduledKey, tuple[HarvestedAttempt, ...]],
) -> tuple[list[HashedSourceFile], list[ScheduleSource], tuple[str, ...]]:
    snapshots = snapshot_schedule_root(schedules_root=schedules_root)
    permitted_names = {"README.md"}
    schedule_stages = {
        name.removesuffix(".tsv")
        for name in snapshots
        if name.endswith(".tsv")
    }
    if not schedule_stages:
        raise ValueError("at least one completed stage schedule is required")
    present_stages = tuple(
        stage for stage in PROTOCOL_STAGE_ORDER if stage in schedule_stages
    )
    if set(present_stages) != schedule_stages:
        raise ValueError(f"unknown schedule stages: {sorted(schedule_stages)!r}")
    if present_stages != PROTOCOL_STAGE_ORDER[: len(present_stages)]:
        raise ValueError("present stage schedules must form a prefix of protocol stage order")
    sources: list[ScheduleSource] = []
    for stage in present_stages:
        schedule_name = f"{stage}.tsv"
        portable_name = f"{stage}.tsv.sha256"
        vps_name = f"{stage}.tsv.vps.sha256"
        if schedule_name not in snapshots or portable_name not in snapshots:
            raise ValueError(f"stage {stage!r} lacks its schedule or portable checksum")
        permitted_names.update({schedule_name, portable_name})
        schedule_snapshot = snapshots[schedule_name]
        portable_snapshot = snapshots[portable_name]
        recorded_path, recorded_digest = parse_single_checksum_snapshot(
            snapshot=portable_snapshot
        )
        if recorded_path not in {schedule_name, f"./{schedule_name}"}:
            raise ValueError(f"portable checksum has wrong path semantics for {stage!r}")
        if recorded_digest != schedule_snapshot.sha256.removeprefix("sha256:"):
            raise ValueError(f"portable schedule checksum mismatch for {stage!r}")
        vps_snapshot = snapshots.get(vps_name)
        if vps_snapshot is not None:
            permitted_names.add(vps_name)
            vps_path, vps_digest = parse_single_checksum_snapshot(snapshot=vps_snapshot)
            if vps_path != f"/root/bench-v2/schedules/{schedule_name}":
                raise ValueError(f"VPS checksum has wrong path semantics for {stage!r}")
            if vps_digest != schedule_snapshot.sha256.removeprefix("sha256:"):
                raise ValueError(f"VPS schedule checksum mismatch for {stage!r}")
        launches = load_schedule_snapshot(snapshot=schedule_snapshot)
        validate_schedule_rows(
            stage=stage,
            launches=launches,
            matrix_schedule=matrix_schedule,
        )
        integrity = validate_first_attempt_order(
            stage=stage,
            launches=launches,
            grouped_attempts=grouped_attempts,
            schedule_sha256=schedule_snapshot.sha256,
        )
        if not integrity.complete_launch_prefix:
            raise ValueError(
                f"stage {stage!r} schedule is present but its launch prefix is incomplete"
            )
        sources.append(
            ScheduleSource(
                stage=stage,
                schedule_sha256=schedule_snapshot.sha256,
                portable_checksum_sha256=portable_snapshot.sha256,
                vps_checksum_sha256=(
                    vps_snapshot.sha256 if vps_snapshot is not None else None
                ),
                integrity=integrity,
            )
        )
    unexpected_names = set(snapshots) - permitted_names
    if unexpected_names:
        raise ValueError(f"unexpected files in schedules root: {sorted(unexpected_names)!r}")
    attempted_stages = {stage for stage, _, _, _ in grouped_attempts}
    missing_schedules = attempted_stages - set(present_stages)
    if missing_schedules:
        raise ValueError(
            f"launched stages are missing schedules: {sorted(missing_schedules)!r}"
        )
    validate_stage_chronology(
        matrix_schedule=matrix_schedule,
        grouped_attempts=grouped_attempts,
    )
    hashed_files = [
        HashedSourceFile(name=name, sha256=snapshot.sha256)
        for name, snapshot in sorted(snapshots.items())
    ]
    return hashed_files, sources, present_stages


def select_campaign(
    *,
    runs_root: Path,
    matrix_path: Path,
    schedules_root: Path,
    ledger_path: Path,
    rubric_source_path: Path,
) -> CampaignSelection:
    ledger_snapshot = read_regular_snapshot(path=ledger_path, label="frozen ledger")
    ledger = FrozenLedger.model_validate_json(ledger_snapshot.data)
    matrix_snapshot = read_regular_snapshot(path=matrix_path, label="frozen matrix")
    matrix_schedule = load_matrix_snapshot(snapshot=matrix_snapshot)
    rubric_snapshot = read_regular_snapshot(
        path=rubric_source_path,
        label="registered artifact-review rubric",
    )
    if rubric_snapshot.sha256 != FROZEN_RUBRIC_SHA256:
        raise ValueError(
            "artifact-review rubric drifted from frozen SHA-256 "
            f"{FROZEN_RUBRIC_DIGEST}"
        )
    validate_registered_rubric_items(snapshot=rubric_snapshot)
    initial_raw_entries = tuple(sorted(entry.name for entry in runs_root.iterdir()))
    attempts = discover_attempts(runs_root=runs_root, ledger=ledger)
    final_raw_entries = tuple(sorted(entry.name for entry in runs_root.iterdir()))
    if final_raw_entries != initial_raw_entries:
        raise ValueError("raw runs root changed while the complete campaign was discovered")
    grouped_attempts = group_and_validate_attempts(
        attempts=attempts,
        schedule=matrix_schedule,
    )
    schedule_files, schedules, present_stages = verify_campaign_schedules(
        schedules_root=schedules_root,
        matrix_schedule=matrix_schedule,
        grouped_attempts=grouped_attempts,
    )
    selected_attempts = sorted(
        (
            attempt
            for attempt in attempts
            if attempt.metadata.stage in present_stages
            and attempt.manifest.infrastructure_valid
        ),
        key=lambda attempt: attempt.metadata.run_id,
    )
    if not selected_attempts:
        raise ValueError("completed campaign contains no infrastructure-valid attempts")
    return CampaignSelection(
        ledger_snapshot=ledger_snapshot,
        matrix_snapshot=matrix_snapshot,
        rubric_snapshot=rubric_snapshot,
        schedule_files=schedule_files,
        schedules=schedules,
        campaign_attempts=list(attempts),
        attempts=selected_attempts,
    )


def read_verified_file_snapshot(
    *, path: Path, expected_digest: str, label: str
) -> RegularSnapshot:
    snapshot = read_regular_snapshot(path=path, label=label)
    if snapshot.sha256.removeprefix("sha256:") != expected_digest:
        raise ValueError(f"{label} changed after immutable-run verification: {path}")
    return snapshot


def explicit_identity_tokens(*, attempt: HarvestedAttempt) -> tuple[bytes, ...]:
    raw_tokens = {
        attempt.metadata.run_id,
        attempt.metadata.system,
        attempt.metadata.requested_model,
        *attempt.manifest.served_models,
    }
    return tuple(
        sorted(
            {
                token.casefold().encode(encoding="utf-8")
                for token in raw_tokens
                if token.strip()
            }
        )
    )


def validate_no_explicit_identity_leak(
    *, attempt: HarvestedAttempt, relative_path: str, data: bytes
) -> None:
    tokens = explicit_identity_tokens(attempt=attempt)
    lowered_path = relative_path.casefold().encode(encoding="utf-8")
    lowered_data = data.lower()
    if any(token in lowered_path or token in lowered_data for token in tokens):
        raise ValueError(
            f"submitted output contains explicit run/system/model identity in "
            f"{attempt.metadata.run_id!r}"
        )


def snapshot_packet_files(*, attempt: HarvestedAttempt) -> list[SnapshotFile]:
    input_ledger_snapshot = read_regular_snapshot(
        path=attempt.run_directory / "input.sha256",
        label="verified input checksum ledger",
    )
    workspace_ledger_snapshot = read_regular_snapshot(
        path=attempt.run_directory / "workspace.sha256",
        label="verified workspace checksum ledger",
    )
    if input_ledger_snapshot.sha256 != attempt.integrity.input_ledger_sha256:
        raise ValueError(f"input ledger changed after verification: {attempt.metadata.run_id!r}")
    if workspace_ledger_snapshot.sha256 != attempt.integrity.workspace_ledger_sha256:
        raise ValueError(
            f"workspace ledger changed after verification: {attempt.metadata.run_id!r}"
        )
    input_entries = parse_tree_checksum_snapshot(snapshot=input_ledger_snapshot)
    workspace_entries = parse_tree_checksum_snapshot(snapshot=workspace_ledger_snapshot)
    files: list[SnapshotFile] = []
    for relative_path, expected_digest in input_entries:
        snapshot = read_verified_file_snapshot(
            path=attempt.run_directory / "input" / relative_path,
            expected_digest=expected_digest,
            label="task-context file",
        )
        files.append(
            SnapshotFile(
                role=PacketFileRole.TASK_CONTEXT,
                source_relative_path=f"input/{relative_path}",
                packet_relative_path=f"task-context/{relative_path}",
                data=snapshot.data,
                sha256=snapshot.sha256,
                size_bytes=snapshot.size_bytes,
                mode=snapshot.mode,
            )
        )
    for relative_path, expected_digest in workspace_entries:
        parsed = PurePosixPath(relative_path)
        if not parsed.is_relative_to(PurePosixPath("output")) or parsed == PurePosixPath(
            "output"
        ):
            continue
        output_relative = parsed.relative_to(PurePosixPath("output")).as_posix()
        snapshot = read_verified_file_snapshot(
            path=attempt.run_directory / "workspace" / relative_path,
            expected_digest=expected_digest,
            label="submitted-output file",
        )
        validate_no_explicit_identity_leak(
            attempt=attempt,
            relative_path=output_relative,
            data=snapshot.data,
        )
        files.append(
            SnapshotFile(
                role=PacketFileRole.SUBMITTED_OUTPUT,
                source_relative_path=f"workspace/{relative_path}",
                packet_relative_path=f"submitted-output/{output_relative}",
                data=snapshot.data,
                sha256=snapshot.sha256,
                size_bytes=snapshot.size_bytes,
                mode=snapshot.mode,
            )
        )
    packet_paths = [file.packet_relative_path for file in files]
    if len(packet_paths) != len(set(packet_paths)):
        raise ValueError(f"packet paths collide for {attempt.metadata.run_id!r}")
    return sorted(files, key=lambda file: file.packet_relative_path)


def build_blueprints(*, selection: CampaignSelection) -> list[PacketBlueprint]:
    return [
        PacketBlueprint(
            attempt=attempt,
            files=snapshot_packet_files(attempt=attempt),
        )
        for attempt in selection.attempts
    ]


def new_neutral_label(*, used_labels: set[str]) -> str:
    while True:
        candidate = f"case-{secrets.token_hex(8)}"
        if candidate not in used_labels:
            return candidate


def packet_payload_sha256(*, payload: PacketPayload) -> Sha256:
    return sha256_bytes(value=serialize_model(model=payload).encode(encoding="utf-8"))


def write_snapshot_into_packet(*, packet_root: Path, snapshot: SnapshotFile) -> None:
    destination = packet_root / snapshot.packet_relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_mode = 0o755 if snapshot.mode & 0o111 else 0o644
    write_exclusive_bytes(
        path=destination,
        data=snapshot.data,
        mode=destination_mode,
    )
    copied = read_regular_snapshot(path=destination, label="copied packet file")
    if copied.data != snapshot.data or copied.sha256 != snapshot.sha256:
        raise ValueError(f"copied packet bytes changed: {snapshot.packet_relative_path}")


def make_packet(
    *,
    blueprint: PacketBlueprint,
    neutral_label: str,
    packets_directory: Path,
    rubric_source_sha256: Sha256,
) -> SealedPacketMapping:
    packet_directory = packets_directory / neutral_label
    packet_directory.mkdir(mode=0o755)
    for snapshot in blueprint.files:
        write_snapshot_into_packet(packet_root=packet_directory, snapshot=snapshot)
    attempt = blueprint.attempt
    packet_files = [
        PacketFile(
            role=snapshot.role,
            relative_path=snapshot.packet_relative_path,
            sha256=snapshot.sha256,
            size_bytes=snapshot.size_bytes,
        )
        for snapshot in blueprint.files
    ]
    payload = PacketPayload(
        neutral_label=neutral_label,
        task_variant=attempt.metadata.task,
        benchmark_version=attempt.manifest.benchmark_version,
        pack_sha256=attempt.manifest.pack_sha256,
        runner_image_sha256=attempt.manifest.runner_image_sha256,
        rubric_source_sha256=rubric_source_sha256,
        files=packet_files,
    )
    packet_hash = packet_payload_sha256(payload=payload)
    manifest = PacketManifest(
        **payload.model_dump(mode="python"),
        packet_sha256=packet_hash,
    )
    write_exclusive_text(
        path=packet_directory / "packet.json",
        text=f"{serialize_model(model=manifest)}\n",
    )
    return SealedPacketMapping(
        neutral_label=neutral_label,
        packet_sha256=packet_hash,
        run_id=attempt.metadata.run_id,
        system=attempt.metadata.system,
        task_variant=attempt.metadata.task,
        run_status=attempt.manifest.status,
        benchmark_version=attempt.manifest.benchmark_version,
        pack_sha256=attempt.manifest.pack_sha256,
        runner_image_sha256=attempt.manifest.runner_image_sha256,
        integrity=attempt.integrity,
        files=[
            SealedFileMapping(
                role=snapshot.role,
                packet_relative_path=snapshot.packet_relative_path,
                source_relative_path=snapshot.source_relative_path,
                sha256=snapshot.sha256,
                size_bytes=snapshot.size_bytes,
            )
            for snapshot in blueprint.files
        ],
    )


def render_review_template(*, packets: Sequence[SealedPacketMapping]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=list(REVIEW_FIELDNAMES),
        lineterminator="\n",
    )
    writer.writeheader()
    for packet in packets:
        for item in RUBRIC_ITEMS:
            writer.writerow(
                {
                    "neutral_label": packet.neutral_label,
                    "packet_sha256": packet.packet_sha256,
                    "task_variant": packet.task_variant,
                    "item_id": item.item_id,
                    "criterion": item.criterion,
                    "status": "",
                    "rationale": "",
                }
            )
    return stream.getvalue().encode(encoding="utf-8")


def campaign_attempt_provenance(
    *, selection: CampaignSelection
) -> list[CampaignAttemptProvenance]:
    included_run_ids = {attempt.metadata.run_id for attempt in selection.attempts}
    return [
        CampaignAttemptProvenance(
            run_id=attempt.metadata.run_id,
            run_status=attempt.manifest.status,
            infrastructure_valid=attempt.manifest.infrastructure_valid,
            included_in_review=attempt.metadata.run_id in included_run_ids,
            integrity=attempt.integrity,
        )
        for attempt in sorted(
            selection.campaign_attempts,
            key=lambda attempt: attempt.metadata.run_id,
        )
    ]


def write_sealed_mapping(*, path: Path, mapping: SealedMapping) -> os.stat_result:
    data = f"{serialize_model(model=mapping)}\n".encode(encoding="utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    opened_stat = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, mode="wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), 0o600)
            os.fsync(stream.fileno())
        snapshot = read_regular_snapshot(path=path, label="new sealed mapping")
        if snapshot.data != data or snapshot.mode != 0o600:
            raise ValueError("sealed mapping failed byte/mode verification")
    except BaseException as error:
        try:
            remove_owned_file(path=path, expected_stat=opened_stat)
        except BaseException as cleanup_error:
            error.add_note(f"partial sealed-mapping cleanup also failed: {cleanup_error!r}")
        raise
    return opened_stat


def prepare_review_bundle(
    *,
    runs_root: Path,
    matrix_path: Path,
    schedules_root: Path,
    ledger_path: Path,
    rubric_source_path: Path,
    review_bundle: Path,
    sealed_mapping_path: Path,
) -> int:
    require_new_destination(path=review_bundle, label="review bundle")
    require_new_destination(path=sealed_mapping_path, label="sealed mapping")
    require_mapping_separation(
        review_bundle=review_bundle,
        sealed_mapping_path=sealed_mapping_path,
    )
    for output_path, label in (
        (review_bundle, "review bundle"),
        (sealed_mapping_path, "sealed mapping"),
    ):
        require_outside_directory(path=output_path, directory=runs_root, label=label)
    selection = select_campaign(
        runs_root=runs_root,
        matrix_path=matrix_path,
        schedules_root=schedules_root,
        ledger_path=ledger_path,
        rubric_source_path=rubric_source_path,
    )
    blueprints = build_blueprints(selection=selection)
    secrets.SystemRandom().shuffle(blueprints)

    staging_directory = Path(
        tempfile.mkdtemp(
            prefix=f".{review_bundle.name}.staging-",
            dir=review_bundle.parent,
        )
    )
    mapping_stat: os.stat_result | None = None
    bundle_published = False
    try:
        staging_directory.chmod(mode=0o755)
        packets_directory = staging_directory / "packets"
        packets_directory.mkdir(mode=0o755)
        used_labels: set[str] = set()
        packets: list[SealedPacketMapping] = []
        for blueprint in blueprints:
            neutral_label = new_neutral_label(used_labels=used_labels)
            used_labels.add(neutral_label)
            packets.append(
                make_packet(
                    blueprint=blueprint,
                    neutral_label=neutral_label,
                    packets_directory=packets_directory,
                    rubric_source_sha256=selection.rubric_snapshot.sha256,
                )
            )
        write_exclusive_bytes(
            path=staging_directory / "review.csv",
            data=render_review_template(packets=packets),
        )
        write_exclusive_bytes(
            path=staging_directory / "ARTIFACT_REVIEW.md",
            data=selection.rubric_snapshot.data,
        )
        write_exclusive_text(
            path=staging_directory / "REVIEW_INSTRUCTIONS.md",
            text=REVIEW_INSTRUCTIONS,
        )
        bundle_manifest = ReviewBundleManifest(
            ledger_sha256=selection.ledger_snapshot.sha256,
            matrix_sha256=selection.matrix_snapshot.sha256,
            rubric_source_sha256=selection.rubric_snapshot.sha256,
            schedule_files=selection.schedule_files,
            packets=[
                BundlePacket(
                    neutral_label=packet.neutral_label,
                    task_variant=packet.task_variant,
                    packet_sha256=packet.packet_sha256,
                )
                for packet in packets
            ],
        )
        write_exclusive_text(
            path=staging_directory / "bundle.json",
            text=f"{serialize_model(model=bundle_manifest)}\n",
        )
        fsync_tree(root=staging_directory)
        mapping = SealedMapping(
            generation_nonce=secrets.token_hex(32),
            ledger_sha256=selection.ledger_snapshot.sha256,
            matrix_sha256=selection.matrix_snapshot.sha256,
            rubric_source_sha256=selection.rubric_snapshot.sha256,
            schedule_files=selection.schedule_files,
            schedules=selection.schedules,
            campaign_attempts=campaign_attempt_provenance(selection=selection),
            packets=packets,
        )
        mapping_stat = write_sealed_mapping(path=sealed_mapping_path, mapping=mapping)
        fsync_directory(path=sealed_mapping_path.parent)
        rename_directory_exclusive(
            source=staging_directory,
            destination=review_bundle,
        )
        bundle_published = True
        fsync_directory(path=review_bundle.parent)
    except BaseException as error:
        try:
            if staging_directory.exists():
                shutil.rmtree(path=staging_directory)
        except BaseException as cleanup_error:
            error.add_note(f"staging cleanup also failed: {cleanup_error!r}")
        try:
            if not bundle_published and mapping_stat is not None:
                remove_owned_file(path=sealed_mapping_path, expected_stat=mapping_stat)
        except BaseException as cleanup_error:
            error.add_note(f"sealed-mapping cleanup also failed: {cleanup_error!r}")
        raise
    return len(blueprints)


def require_sealed_mapping_snapshot(
    *, path: Path
) -> tuple[SealedMapping, RegularSnapshot]:
    snapshot = read_regular_snapshot(path=path, label="sealed mapping")
    mode = snapshot.mode
    if mode != 0o600:
        raise ValueError(f"sealed mapping must have mode 0600, found {mode:04o}")
    mapping = SealedMapping.model_validate_json(snapshot.data)
    if snapshot.data != f"{serialize_model(model=mapping)}\n".encode(encoding="utf-8"):
        raise ValueError("sealed mapping is not canonical")
    return mapping, snapshot


def exact_tree_files(*, root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"expected a regular non-symlink directory: {root}")
    files: set[str] = set()
    for directory, directory_names, file_names in root.walk(
        top_down=True,
        follow_symlinks=False,
    ):
        for name in directory_names:
            candidate = directory / name
            if candidate.is_symlink() or not candidate.is_dir():
                raise ValueError(f"packet tree contains a non-directory entry: {candidate}")
        for name in file_names:
            candidate = directory / name
            if candidate.is_symlink() or not candidate.is_file():
                raise ValueError(f"packet tree contains a non-regular file: {candidate}")
            files.add(candidate.relative_to(root).as_posix())
    return files


def require_exact_tree(*, root: Path, expected_files: set[str], label: str) -> None:
    actual_files = exact_tree_files(root=root)
    expected_directories = {
        parent.as_posix()
        for relative_path in expected_files
        for parent in PurePosixPath(relative_path).parents
        if parent != PurePosixPath(".")
    }
    actual_directories = {
        (directory / name).relative_to(root).as_posix()
        for directory, directory_names, _ in root.walk(
            top_down=True,
            follow_symlinks=False,
        )
        for name in directory_names
    }
    if actual_files != expected_files or actual_directories != expected_directories:
        raise ValueError(f"{label} file or directory set changed")


def validate_packet_tree(
    *, review_bundle: Path, mapping: SealedMapping
) -> None:
    packets_directory = review_bundle / "packets"
    expected_labels = {packet.neutral_label for packet in mapping.packets}
    actual_labels = {entry.name for entry in packets_directory.iterdir()}
    if actual_labels != expected_labels:
        raise ValueError("review packet label set differs from sealed mapping")
    for sealed_packet in mapping.packets:
        packet_directory = packets_directory / sealed_packet.neutral_label
        expected_files = {
            "packet.json",
            *(file.packet_relative_path for file in sealed_packet.files),
        }
        require_exact_tree(
            root=packet_directory,
            expected_files=expected_files,
            label=f"packet {sealed_packet.neutral_label!r}",
        )
        manifest_snapshot = read_regular_snapshot(
            path=packet_directory / "packet.json",
            label="packet manifest",
        )
        manifest = PacketManifest.model_validate_json(manifest_snapshot.data)
        if manifest_snapshot.data != f"{serialize_model(model=manifest)}\n".encode(
            encoding="utf-8"
        ):
            raise ValueError("packet manifest is not canonical")
        payload = PacketPayload.model_validate(
            manifest.model_dump(mode="python", exclude={"packet_sha256"})
        )
        expected_packet_files = [
            PacketFile(
                role=file.role,
                relative_path=file.packet_relative_path,
                sha256=file.sha256,
                size_bytes=file.size_bytes,
            )
            for file in sealed_packet.files
        ]
        if (
            manifest.neutral_label != sealed_packet.neutral_label
            or manifest.task_variant != sealed_packet.task_variant
            or manifest.benchmark_version != sealed_packet.benchmark_version
            or manifest.pack_sha256 != sealed_packet.pack_sha256
            or manifest.runner_image_sha256 != sealed_packet.runner_image_sha256
            or manifest.rubric_source_sha256 != mapping.rubric_source_sha256
            or manifest.files != expected_packet_files
            or manifest.packet_sha256 != sealed_packet.packet_sha256
            or packet_payload_sha256(payload=payload) != sealed_packet.packet_sha256
        ):
            raise ValueError(f"packet provenance changed for {sealed_packet.neutral_label!r}")
        for file in sealed_packet.files:
            snapshot = read_regular_snapshot(
                path=packet_directory / file.packet_relative_path,
                label="packet file",
            )
            if snapshot.sha256 != file.sha256 or snapshot.size_bytes != file.size_bytes:
                raise ValueError(
                    f"packet file bytes changed: "
                    f"{sealed_packet.neutral_label}/{file.packet_relative_path}"
                )


def validate_review_bundle(
    *, review_bundle: Path, mapping: SealedMapping
) -> RegularSnapshot:
    expected_root_files = {
        "ARTIFACT_REVIEW.md",
        "REVIEW_INSTRUCTIONS.md",
        "bundle.json",
        "review.csv",
        *(
            f"packets/{packet.neutral_label}/{relative_path}"
            for packet in mapping.packets
            for relative_path in {
                "packet.json",
                *(file.packet_relative_path for file in packet.files),
            }
        ),
    }
    require_exact_tree(
        root=review_bundle,
        expected_files=expected_root_files,
        label="review bundle",
    )
    rubric_snapshot = read_regular_snapshot(
        path=review_bundle / "ARTIFACT_REVIEW.md",
        label="bundled rubric",
    )
    if rubric_snapshot.sha256 != mapping.rubric_source_sha256:
        raise ValueError("bundled rubric differs from sealed provenance")
    instruction_snapshot = read_regular_snapshot(
        path=review_bundle / "REVIEW_INSTRUCTIONS.md",
        label="review instructions",
    )
    if instruction_snapshot.data != REVIEW_INSTRUCTIONS.encode(encoding="utf-8"):
        raise ValueError("review instructions changed after preparation")
    bundle_snapshot = read_regular_snapshot(
        path=review_bundle / "bundle.json",
        label="review bundle manifest",
    )
    bundle = ReviewBundleManifest.model_validate_json(bundle_snapshot.data)
    if bundle_snapshot.data != f"{serialize_model(model=bundle)}\n".encode(
        encoding="utf-8"
    ):
        raise ValueError("review bundle manifest is not canonical")
    expected_bundle = ReviewBundleManifest(
        ledger_sha256=mapping.ledger_sha256,
        matrix_sha256=mapping.matrix_sha256,
        rubric_source_sha256=mapping.rubric_source_sha256,
        schedule_files=mapping.schedule_files,
        packets=[
            BundlePacket(
                neutral_label=packet.neutral_label,
                task_variant=packet.task_variant,
                packet_sha256=packet.packet_sha256,
            )
            for packet in mapping.packets
        ],
    )
    if bundle != expected_bundle:
        raise ValueError("review bundle manifest differs from sealed mapping")
    validate_packet_tree(review_bundle=review_bundle, mapping=mapping)
    return read_regular_snapshot(
        path=review_bundle / "review.csv",
        label="completed blinded review",
    )


def validate_mapping_against_campaign(
    *, mapping: SealedMapping, selection: CampaignSelection
) -> list[PacketBlueprint]:
    if (
        mapping.ledger_sha256 != selection.ledger_snapshot.sha256
        or mapping.matrix_sha256 != selection.matrix_snapshot.sha256
        or mapping.rubric_source_sha256 != selection.rubric_snapshot.sha256
        or mapping.schedule_files != selection.schedule_files
        or mapping.schedules != selection.schedules
        or mapping.campaign_attempts
        != campaign_attempt_provenance(selection=selection)
    ):
        raise ValueError("sealed campaign provenance differs from current frozen sources")
    blueprints = build_blueprints(selection=selection)
    blueprint_by_run = {
        blueprint.attempt.metadata.run_id: blueprint for blueprint in blueprints
    }
    mapped_run_ids = [packet.run_id for packet in mapping.packets]
    if len(mapped_run_ids) != len(set(mapped_run_ids)):
        raise ValueError("sealed mapping contains duplicate run IDs")
    if set(mapped_run_ids) != set(blueprint_by_run):
        raise ValueError("sealed mapping is not the complete infrastructure-valid campaign")
    labels = [packet.neutral_label for packet in mapping.packets]
    if len(labels) != len(set(labels)):
        raise ValueError("sealed mapping contains duplicate neutral labels")
    for packet in mapping.packets:
        blueprint = blueprint_by_run[packet.run_id]
        attempt = blueprint.attempt
        expected_files = [
            SealedFileMapping(
                role=file.role,
                packet_relative_path=file.packet_relative_path,
                source_relative_path=file.source_relative_path,
                sha256=file.sha256,
                size_bytes=file.size_bytes,
            )
            for file in blueprint.files
        ]
        if (
            packet.system != attempt.metadata.system
            or packet.task_variant != attempt.metadata.task
            or packet.run_status != attempt.manifest.status
            or packet.benchmark_version != attempt.manifest.benchmark_version
            or packet.pack_sha256 != attempt.manifest.pack_sha256
            or packet.runner_image_sha256 != attempt.manifest.runner_image_sha256
            or packet.integrity != attempt.integrity
            or packet.files != expected_files
        ):
            raise ValueError(f"sealed run provenance mismatch for {packet.run_id!r}")
    return blueprints


def parse_completed_review_snapshot(
    *, snapshot: RegularSnapshot, mapping: SealedMapping
) -> tuple[CompletedReviewRow, ...]:
    text = decode_utf8(snapshot=snapshot, label="completed blinded review")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != REVIEW_FIELDNAMES:
        raise ValueError(
            f"completed review columns must be exactly {list(REVIEW_FIELDNAMES)!r}"
        )
    rows = tuple(CompletedReviewRow.model_validate(row) for row in reader)
    expected_by_label = {packet.neutral_label: packet for packet in mapping.packets}
    expected_items = {item.item_id: item for item in RUBRIC_ITEMS}
    seen_keys: set[tuple[str, str]] = set()
    for row in rows:
        packet = expected_by_label.get(row.neutral_label)
        item = expected_items.get(row.item_id)
        if packet is None or item is None:
            raise ValueError("completed review contains an unknown packet or rubric item")
        if (
            row.packet_sha256 != packet.packet_sha256
            or row.task_variant != packet.task_variant
            or row.criterion != item.criterion
        ):
            raise ValueError("completed review row provenance differs from sealed mapping")
        key = (row.neutral_label, row.item_id)
        if key in seen_keys:
            raise ValueError(f"duplicate completed review judgment: {key!r}")
        seen_keys.add(key)
        if row.item_id == "no_unavailable_access":
            if row.status is ReviewStatus.PASS:
                raise ValueError("item 8 cannot pass in an artifact-only review")
            if row.status in {ReviewStatus.PARTIAL, ReviewStatus.FAIL} and not (
                row.rationale.casefold().startswith("submitted artifact evidence:")
            ):
                raise ValueError(
                    "item 8 partial/fail needs a rationale beginning "
                    "'Submitted artifact evidence:'"
                )
        if row.item_id == "artifacts_and_offline_scripts" and row.status is ReviewStatus.PASS:
            lowered = row.rationale.casefold()
            required_fragments = ("offline command:", "runner manifest:", "result:")
            offline_execution_recorded = all(
                fragment in lowered for fragment in required_fragments
            ) and f"runner manifest: {packet.runner_image_sha256.casefold()}" in lowered
            no_applicable_scripts_recorded = lowered.startswith(
                "no applicable scripts:"
            ) and "cited artifacts verified:" in lowered
            if not offline_execution_recorded and not no_applicable_scripts_recorded:
                raise ValueError(
                    "an item 6 pass must record either verified cited artifacts with no "
                    "applicable scripts or the offline command, exact packet runner manifest, "
                    "and result"
                )
    expected_keys = {
        (packet.neutral_label, item.item_id)
        for packet in mapping.packets
        for item in RUBRIC_ITEMS
    }
    if seen_keys != expected_keys:
        raise ValueError(
            "completed review must contain exactly eight registered judgments per packet"
        )
    return rows


def render_jsonl(*, models: Sequence[BaseModel]) -> bytes:
    return "".join(f"{serialize_model(model=model)}\n" for model in models).encode(
        encoding="utf-8"
    )


def public_run_mappings(*, mapping: SealedMapping) -> list[PublicRunMapping]:
    return [
        PublicRunMapping(
            neutral_label=packet.neutral_label,
            packet_sha256=packet.packet_sha256,
            run_id=packet.run_id,
            system=packet.system,
            task_variant=packet.task_variant,
            run_status=packet.run_status,
            benchmark_version=packet.benchmark_version,
            pack_sha256=packet.pack_sha256,
            runner_image_sha256=packet.runner_image_sha256,
            integrity=packet.integrity,
            files=packet.files,
        )
        for packet in sorted(mapping.packets, key=lambda packet: packet.run_id)
    ]


def build_public_items(
    *,
    rows: tuple[CompletedReviewRow, ...],
    mapping: SealedMapping,
    review_sha256: Sha256,
) -> list[PublicReviewItem]:
    packets = {packet.neutral_label: packet for packet in mapping.packets}
    return sorted(
        [
            PublicReviewItem(
                completed_review_sha256=review_sha256,
                run_id=packets[row.neutral_label].run_id,
                system=packets[row.neutral_label].system,
                task_variant=row.task_variant,
                run_status=packets[row.neutral_label].run_status,
                packet_sha256=row.packet_sha256,
                item_id=row.item_id,
                criterion=row.criterion,
                status=row.status,
                rationale=row.rationale,
            )
            for row in rows
        ],
        key=lambda item: (item.run_id, item.item_id),
    )


def finalize_review_bundle(
    *,
    runs_root: Path,
    matrix_path: Path,
    schedules_root: Path,
    ledger_path: Path,
    rubric_source_path: Path,
    review_bundle: Path,
    sealed_mapping_path: Path,
    public_bundle: Path,
) -> int:
    require_new_destination(path=public_bundle, label="public review bundle")
    require_mapping_separation(
        review_bundle=review_bundle,
        sealed_mapping_path=sealed_mapping_path,
    )
    require_outside_directory(
        path=public_bundle,
        directory=runs_root,
        label="public review bundle",
    )
    require_outside_directory(
        path=review_bundle,
        directory=runs_root,
        label="review bundle",
    )
    require_outside_directory(
        path=sealed_mapping_path,
        directory=runs_root,
        label="sealed mapping",
    )
    require_outside_directory(
        path=public_bundle,
        directory=review_bundle,
        label="public review bundle",
    )
    mapping, mapping_snapshot = require_sealed_mapping_snapshot(path=sealed_mapping_path)
    selection = select_campaign(
        runs_root=runs_root,
        matrix_path=matrix_path,
        schedules_root=schedules_root,
        ledger_path=ledger_path,
        rubric_source_path=rubric_source_path,
    )
    validate_mapping_against_campaign(mapping=mapping, selection=selection)
    completed_review_snapshot = validate_review_bundle(
        review_bundle=review_bundle,
        mapping=mapping,
    )
    rows = parse_completed_review_snapshot(
        snapshot=completed_review_snapshot,
        mapping=mapping,
    )
    public_items = build_public_items(
        rows=rows,
        mapping=mapping,
        review_sha256=completed_review_snapshot.sha256,
    )
    run_mappings = public_run_mappings(mapping=mapping)

    staging_directory = Path(
        tempfile.mkdtemp(
            prefix=f".{public_bundle.name}.staging-",
            dir=public_bundle.parent,
        )
    )
    try:
        staging_directory.chmod(mode=0o755)
        item_bytes = render_jsonl(models=public_items)
        mapping_bytes = render_jsonl(models=run_mappings)
        write_exclusive_bytes(
            path=staging_directory / "item-review.jsonl",
            data=item_bytes,
        )
        write_exclusive_bytes(
            path=staging_directory / "label-mapping.jsonl",
            data=mapping_bytes,
        )
        write_exclusive_bytes(
            path=staging_directory / "completed-review.csv",
            data=completed_review_snapshot.data,
        )
        write_exclusive_bytes(
            path=staging_directory / "ARTIFACT_REVIEW.md",
            data=selection.rubric_snapshot.data,
        )
        write_exclusive_text(
            path=staging_directory / "REVIEW_INSTRUCTIONS.md",
            text=REVIEW_INSTRUCTIONS,
        )
        public_files = [
            PublicFileHash(name="item-review.jsonl", sha256=sha256_bytes(value=item_bytes)),
            PublicFileHash(name="label-mapping.jsonl", sha256=sha256_bytes(value=mapping_bytes)),
            PublicFileHash(
                name="completed-review.csv",
                sha256=completed_review_snapshot.sha256,
            ),
            PublicFileHash(
                name="ARTIFACT_REVIEW.md",
                sha256=selection.rubric_snapshot.sha256,
            ),
            PublicFileHash(
                name="REVIEW_INSTRUCTIONS.md",
                sha256=sha256_bytes(value=REVIEW_INSTRUCTIONS.encode(encoding="utf-8")),
            ),
        ]
        provenance = PublicProvenance(
            completed_review_sha256=completed_review_snapshot.sha256,
            sealed_mapping_sha256=mapping_snapshot.sha256,
            ledger_sha256=selection.ledger_snapshot.sha256,
            matrix_sha256=selection.matrix_snapshot.sha256,
            rubric_source_sha256=selection.rubric_snapshot.sha256,
            schedule_files=selection.schedule_files,
            schedules=selection.schedules,
            campaign_attempts=mapping.campaign_attempts,
            runs=run_mappings,
            public_files=public_files,
        )
        write_exclusive_text(
            path=staging_directory / "provenance.json",
            text=f"{serialize_model(model=provenance)}\n",
        )
        fsync_tree(root=staging_directory)
        rename_directory_exclusive(
            source=staging_directory,
            destination=public_bundle,
        )
        fsync_directory(path=public_bundle.parent)
    except BaseException as error:
        try:
            if staging_directory.exists():
                shutil.rmtree(path=staging_directory)
        except BaseException as cleanup_error:
            error.add_note(f"public staging cleanup also failed: {cleanup_error!r}")
        raise
    return len(public_items)


def add_campaign_arguments(*, parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--schedules-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--rubric-source", type=Path, required=True)
    parser.add_argument("--review-bundle", type=Path, required=True)
    parser.add_argument("--sealed-mapping", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analysis.blind_review",
        description="Prepare and finalize identity-blind artifact-review bundles.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    add_campaign_arguments(parser=prepare_parser)
    finalize_parser = subparsers.add_parser("finalize")
    add_campaign_arguments(parser=finalize_parser)
    finalize_parser.add_argument("--public-bundle", type=Path, required=True)
    return parser


def main(*, arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(args=arguments)
    if parsed.command == "prepare":
        packet_count = prepare_review_bundle(
            runs_root=parsed.runs_root,
            matrix_path=parsed.matrix,
            schedules_root=parsed.schedules_root,
            ledger_path=parsed.ledger,
            rubric_source_path=parsed.rubric_source,
            review_bundle=parsed.review_bundle,
            sealed_mapping_path=parsed.sealed_mapping,
        )
        print(canonical_json(value={"packet_count": packet_count}))
        return 0
    published_item_count = finalize_review_bundle(
        runs_root=parsed.runs_root,
        matrix_path=parsed.matrix,
        schedules_root=parsed.schedules_root,
        ledger_path=parsed.ledger,
        rubric_source_path=parsed.rubric_source,
        review_bundle=parsed.review_bundle,
        sealed_mapping_path=parsed.sealed_mapping,
        public_bundle=parsed.public_bundle,
    )
    print(canonical_json(value={"published_item_count": published_item_count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
