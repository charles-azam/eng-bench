#!/usr/bin/env python3
"""Create and import content-blind, integrity-checked V4 stage archives."""

from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import fcntl
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


type StageName = Literal[
    "core-n3",
    "core-extend-n5",
    "nstf-duty-ablation-n3",
]
type SystemName = Literal["codex", "claude"]

SafeIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$"),
]
ServiceName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9_.-]*\.service$"),
]
PositiveInteger = Annotated[int, Field(ge=1, strict=True)]

CHECKSUM_LINE = re.compile(
    pattern=r"^(?P<digest>[0-9a-f]{64})  (?P<path>[^\r\n]+)$"
)
RUN_NAME = re.compile(
    pattern=(
        r"^(?P<stage>[a-z0-9][a-z0-9_-]*)-"
        r"(?P<task>[a-z0-9][a-z0-9_-]*)-"
        r"(?P<system>codex|claude)-r(?P<replicate>[0-9]{2})-"
        r"a(?P<attempt>01|02)$"
    )
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
FROZEN_FILE_SHA256: dict[str, str] = {
    "runner.sha256": "4866902c3c7c349e02e7870ede3d9d7a7c9912ce59230c1a167f85d261b9de7c",
    "protocol/manifest.sha256": "a055cf5b17b64861ba393dcda607e5f4b9908ad8e044bcc182ad6cf8df080520",
    "protocol/environment.json": "15559315a5072682de5ce4b0fc636c59ffdd101f5b048cac1137bd4c6f7e4bc7",
    "protocol/evaluation_ledger.json": "9962c3f87bee50f8a32b90b41c56954d0e89d545216d4bb02c2dede121824bd7",
    "protocol/matrix.tsv": "27c64e324236d2659747928e466770e466814eceae6e2a07c289a5f551538c43",
}
ARCHIVE_SUFFIXES: tuple[str, ...] = (
    "files0",
    "tree.sha256",
    "tar",
    "tar.sha256",
)
DARWIN_RENAME_EXCL: int = 0x00000004
LINUX_RENAME_NOREPLACE: int = 1


class StrictModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=False,
    )


class StageDefinition(StrictModel):
    stage: StageName
    expected_first_attempts: PositiveInteger
    service: ServiceName
    retention_service: ServiceName
    next_stage: StageName | None


class ServiceState(StrictModel):
    load_state: Literal["loaded"]
    active_state: Literal["inactive"]
    sub_state: Literal["dead"]
    result: Literal["success"]
    exec_main_status: Literal[0]
    main_pid: Literal[0]


class RetentionState(StrictModel):
    load_state: Literal["loaded"]
    active_state: Literal["active"]
    sub_state: Literal["running"]
    result: Literal["success"]
    exec_main_status: Literal[0]
    main_pid: PositiveInteger
    wants: frozenset[ServiceName]


class ScheduleRow(StrictModel):
    sequence: PositiveInteger
    task: SafeIdentifier
    system: SystemName
    replicate: PositiveInteger
    stage: StageName

    def run_id(self, *, attempt: int) -> str:
        return (
            f"{self.stage}-{self.task}-{self.system}"
            f"-r{self.replicate:02d}-a{attempt:02d}"
        )


class AttemptStatus(StrictModel):
    classification: Literal[
        "complete",
        "model_refusal",
        "model_contamination",
        "agent_failure",
        "timeout",
        "infrastructure_failure",
    ]
    detail: Annotated[str, StringConstraints(min_length=1)]
    exit_code: int
    canonical_status: Literal[
        "completed",
        "agent_failure",
        "refusal",
        "fallback_contaminated",
        "provider_failure",
        "runner_failure",
    ]
    prediction_normalization: Annotated[str, StringConstraints(min_length=1)]
    served_models: list[Annotated[str, StringConstraints(min_length=1)]]

    @model_validator(mode="after")
    def validate_classification_status(self) -> AttemptStatus:
        permitted = {
            "complete": {"completed", "agent_failure", "runner_failure"},
            "model_refusal": {"refusal", "runner_failure"},
            "model_contamination": {"fallback_contaminated", "runner_failure"},
            "agent_failure": {"agent_failure", "runner_failure"},
            "timeout": {"agent_failure", "runner_failure"},
            "infrastructure_failure": {"provider_failure", "runner_failure"},
        }
        if self.canonical_status not in permitted[self.classification]:
            raise ValueError("canonical status is incompatible with classification")
        return self


class ArchivePaths(StrictModel):
    directory: Path
    files0: Path
    tree_ledger: Path
    tar: Path
    tar_checksum: Path


STAGE_DEFINITIONS: dict[StageName, StageDefinition] = {
    "core-n3": StageDefinition(
        stage="core-n3",
        expected_first_attempts=12,
        service="eng-bench-core-n3-v4.service",
        retention_service="eng-bench-core-n3-v4-retention.service",
        next_stage="core-extend-n5",
    ),
    "core-extend-n5": StageDefinition(
        stage="core-extend-n5",
        expected_first_attempts=8,
        service="eng-bench-core-extend-n5-v4.service",
        retention_service="eng-bench-core-extend-n5-v4-retention.service",
        next_stage="nstf-duty-ablation-n3",
    ),
    "nstf-duty-ablation-n3": StageDefinition(
        stage="nstf-duty-ablation-n3",
        expected_first_attempts=6,
        service="eng-bench-nstf-duty-ablation-n3-v4.service",
        retention_service="eng-bench-nstf-duty-ablation-n3-v4-retention.service",
        next_stage=None,
    ),
}


def sha256_file(*, path: Path) -> str:
    digest = hashlib.sha256()
    with path.open(mode="rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def require_regular_file(*, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def require_regular_directory(*, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} must be a regular non-symlink directory: {path}")


def run_command(
    *, arguments: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        args=arguments,
        cwd=cwd,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(encoding="utf-8", errors="replace").strip()
        raise RuntimeError(
            f"command failed with exit {result.returncode}: {arguments!r}; "
            f"stderr={stderr!r}"
        )
    return result


def parse_single_checksum(
    *, path: Path, permitted_paths: frozenset[str]
) -> tuple[str, str]:
    require_regular_file(path=path, label="checksum ledger")
    contents = path.read_text(encoding="utf-8")
    lines = contents.splitlines()
    if not contents.endswith("\n") or len(lines) != 1:
        raise ValueError(f"checksum ledger must contain one terminated record: {path}")
    match = CHECKSUM_LINE.fullmatch(string=lines[0])
    if match is None:
        raise ValueError(f"malformed checksum ledger: {path}")
    recorded_path = match.group("path")
    if recorded_path not in permitted_paths:
        raise ValueError(
            f"checksum ledger has wrong path semantics: {recorded_path!r}"
        )
    return match.group("digest"), recorded_path


def parse_tree_ledger_contents(*, contents: bytes) -> tuple[tuple[str, str], ...]:
    text = contents.decode(encoding="utf-8")
    if not text or not text.endswith("\n"):
        raise ValueError("tree checksum ledger must be non-empty and terminated")
    records: list[tuple[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = CHECKSUM_LINE.fullmatch(string=line)
        if match is None:
            raise ValueError(f"malformed tree checksum line {line_number}")
        relative_path = match.group("path")
        validate_archive_relative_path(relative_path=relative_path)
        records.append((relative_path, match.group("digest")))
    paths = [relative_path for relative_path, _ in records]
    if len(paths) != len(set(paths)):
        raise ValueError("tree checksum ledger contains duplicate paths")
    if paths != sorted(paths, key=lambda value: os.fsencode(value)):
        raise ValueError("tree checksum ledger paths are not bytewise sorted")
    return tuple(records)


def rename_directory_exclusive(*, source: Path, destination: Path) -> None:
    if source.name in {"", ".", ".."} or destination.name in {"", ".", ".."}:
        raise ValueError("exclusive rename requires named directory entries")
    directory_flags: int = (
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    result: int
    error_number: int
    source_parent_descriptor: int = os.open(source.parent, directory_flags)
    try:
        destination_parent_descriptor: int = os.open(
            destination.parent,
            directory_flags,
        )
        try:
            library = ctypes.CDLL(name=None, use_errno=True)
            source_name = os.fsencode(source.name)
            destination_name = os.fsencode(destination.name)
            ctypes.set_errno(0)
            if sys.platform == "darwin":
                rename_function = library.renameatx_np
                rename_function.argtypes = [
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_uint,
                ]
                rename_function.restype = ctypes.c_int
                result = rename_function(
                    source_parent_descriptor,
                    source_name,
                    destination_parent_descriptor,
                    destination_name,
                    DARWIN_RENAME_EXCL,
                )
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
                result = rename_function(
                    source_parent_descriptor,
                    source_name,
                    destination_parent_descriptor,
                    destination_name,
                    LINUX_RENAME_NOREPLACE,
                )
            else:
                raise RuntimeError(
                    "atomic no-replace directory rename is unsupported on "
                    f"{sys.platform!r}"
                )
            error_number = ctypes.get_errno()
        finally:
            os.close(destination_parent_descriptor)
    finally:
        os.close(source_parent_descriptor)
    if result == 0:
        return
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(error_number, os.strerror(error_number), destination)
    raise OSError(error_number, os.strerror(error_number), destination)


def validate_archive_relative_path(*, relative_path: str) -> None:
    if not relative_path.startswith("./"):
        raise ValueError(f"archive path must start with './': {relative_path!r}")
    stripped = relative_path.removeprefix("./")
    parsed = PurePosixPath(stripped)
    if (
        not stripped
        or parsed.is_absolute()
        or parsed.as_posix() != stripped
        or ".." in parsed.parts
        or "." in parsed.parts
        or "\\" in stripped
        or "\x00" in stripped
        or "\n" in stripped
        or "\r" in stripped
    ):
        raise ValueError(f"unsafe archive path: {relative_path!r}")


def load_schedule(*, path: Path, stage: StageDefinition) -> tuple[ScheduleRow, ...]:
    require_regular_file(path=path, label="stage schedule")
    rows: list[ScheduleRow] = []
    with path.open(mode="r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        expected_columns = ["sequence", "task", "system", "replicate", "stage"]
        if reader.fieldnames != expected_columns:
            raise ValueError("stage schedule has unexpected columns")
        for raw_row in reader:
            row = ScheduleRow.model_validate(
                obj={
                    "sequence": int(raw_row["sequence"]),
                    "task": raw_row["task"],
                    "system": raw_row["system"],
                    "replicate": int(raw_row["replicate"]),
                    "stage": raw_row["stage"],
                },
                strict=True,
            )
            expected_sequence = len(rows) + 1
            if row.sequence != expected_sequence:
                raise ValueError("schedule sequence is not contiguous and ordered")
            if row.stage != stage.stage:
                raise ValueError("schedule contains a row for another stage")
            rows.append(row)
    if len(rows) != stage.expected_first_attempts:
        raise ValueError(
            f"{stage.stage} requires {stage.expected_first_attempts} schedule rows"
        )
    identities = [(row.task, row.system, row.replicate) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("schedule contains duplicate run identities")
    return tuple(rows)


def artifact_path(*, run_directory: Path, relative_path: str) -> Path:
    candidate = run_directory
    for part in PurePosixPath(relative_path).parts[:-1]:
        candidate = candidate / part
        require_regular_directory(path=candidate, label="artifact parent")
    path = run_directory / relative_path
    require_regular_file(path=path, label="checksummed artifact")
    return path


def verify_artifact_ledger(
    *, run_directory: Path, recorded_runs_root: Path
) -> None:
    run_id = run_directory.name
    ledger_path = run_directory / "artifact.sha256"
    require_regular_file(path=ledger_path, label="artifact checksum ledger")
    contents = ledger_path.read_text(encoding="utf-8")
    if not contents or not contents.endswith("\n"):
        raise ValueError(f"artifact ledger is not terminated: {run_id}")
    records: list[tuple[str, str]] = []
    for line_number, line in enumerate(contents.splitlines(), start=1):
        match = CHECKSUM_LINE.fullmatch(string=line)
        if match is None:
            raise ValueError(
                f"malformed artifact checksum line {line_number}: {run_id}"
            )
        records.append((match.group("path"), match.group("digest")))
    expected_paths = tuple(
        str(recorded_runs_root / run_id / relative_path)
        for relative_path in ARTIFACT_PATHS
    )
    if tuple(path for path, _ in records) != expected_paths:
        raise ValueError(f"fixed artifact ledger has wrong file set: {run_id}")
    mismatches = [
        relative_path
        for relative_path, (_, expected_digest) in zip(
            ARTIFACT_PATHS,
            records,
            strict=True,
        )
        if sha256_file(
            path=artifact_path(
                run_directory=run_directory,
                relative_path=relative_path,
            )
        )
        != expected_digest
    ]
    if mismatches:
        raise ValueError(f"artifact checksum mismatch for {run_id}: {mismatches!r}")


def stage_run_directories(
    *, runs_root: Path, rows: tuple[ScheduleRow, ...], stage: StageDefinition
) -> tuple[Path, ...]:
    require_regular_directory(path=runs_root, label="runs root")
    allowed_names = {
        row.run_id(attempt=attempt)
        for row in rows
        for attempt in (1, 2)
    }
    stage_entries = sorted(
        (
            entry
            for entry in runs_root.iterdir()
            if entry.name.startswith(f"{stage.stage}-")
        ),
        key=lambda entry: os.fsencode(entry.name),
    )
    for entry in stage_entries:
        require_regular_directory(path=entry, label="stage run directory")
        if entry.name not in allowed_names or RUN_NAME.fullmatch(string=entry.name) is None:
            raise ValueError(f"unregistered stage attempt directory: {entry.name}")
    first_attempt_names = {
        entry.name for entry in stage_entries if entry.name.endswith("-a01")
    }
    expected_first_attempt_names = {row.run_id(attempt=1) for row in rows}
    if first_attempt_names != expected_first_attempt_names:
        raise ValueError("stage does not contain every exact registered first attempt")
    return tuple(stage_entries)


def require_registered_retry_set(
    *, run_directories: tuple[Path, ...], rows: tuple[ScheduleRow, ...]
) -> None:
    by_name = {run_directory.name: run_directory for run_directory in run_directories}
    required_retries: set[str] = set()
    for row in rows:
        primary_name = row.run_id(attempt=1)
        primary_status = AttemptStatus.model_validate_json(
            json_data=(by_name[primary_name] / "status.json").read_bytes(),
            strict=True,
        )
        if primary_status.canonical_status in {"provider_failure", "runner_failure"}:
            required_retries.add(row.run_id(attempt=2))
    observed_retries = {
        run_directory.name
        for run_directory in run_directories
        if run_directory.name.endswith("-a02")
    }
    if observed_retries != required_retries:
        raise ValueError(
            "stage retries do not exactly match infrastructure-failed first attempts"
        )


def reject_symlinks_and_non_regular_entries(*, root: Path) -> None:
    require_regular_directory(path=root, label="run directory")
    for directory, directory_names, file_names in root.walk(
        top_down=True,
        follow_symlinks=False,
    ):
        for name in directory_names:
            candidate = directory / name
            require_regular_directory(path=candidate, label="run tree directory")
        for name in file_names:
            candidate = directory / name
            relative_path = candidate.relative_to(root).as_posix()
            candidate_stat = os.lstat(candidate)
            # The frozen runner kills and waits for the proxy but leaves this stale
            # socket inode behind. It is registered runtime plumbing, not evidence.
            if relative_path == "runtime/proxy.sock" and stat.S_ISSOCK(
                candidate_stat.st_mode
            ):
                continue
            require_regular_file(path=candidate, label="run tree file")


def tree_records(*, runs_root: Path, run_directories: tuple[Path, ...]) -> tuple[tuple[str, str], ...]:
    files: list[Path] = []
    for run_directory in run_directories:
        reject_symlinks_and_non_regular_entries(root=run_directory)
        files.extend(
            path
            for path in run_directory.rglob(pattern="*")
            if path.is_file() and not path.is_symlink()
        )
    ordered_files = sorted(
        files,
        key=lambda path: os.fsencode(path.relative_to(runs_root).as_posix()),
    )
    records: list[tuple[str, str]] = []
    for path in ordered_files:
        relative_path = f"./{path.relative_to(runs_root).as_posix()}"
        validate_archive_relative_path(relative_path=relative_path)
        records.append((relative_path, sha256_file(path=path)))
    if not records:
        raise ValueError("stage archive cannot be empty")
    return tuple(records)


def render_tree_ledger(*, records: tuple[tuple[str, str], ...]) -> bytes:
    return "".join(
        f"{digest}  {relative_path}\n"
        for relative_path, digest in records
    ).encode(encoding="utf-8")


def render_files0(*, records: tuple[tuple[str, str], ...]) -> bytes:
    return b"".join(
        relative_path.encode(encoding="utf-8") + b"\x00"
        for relative_path, _ in records
    )


def write_tar(
    *, tar_path: Path, runs_root: Path, records: tuple[tuple[str, str], ...]
) -> None:
    with tarfile.open(
        name=tar_path,
        mode="x",
        format=tarfile.PAX_FORMAT,
    ) as archive:
        for relative_path, _ in records:
            source_path = runs_root / relative_path.removeprefix("./")
            source_stat = source_path.stat(follow_symlinks=False)
            member = tarfile.TarInfo(name=relative_path.removeprefix("./"))
            member.size = source_stat.st_size
            member.mode = stat.S_IMODE(source_stat.st_mode)
            member.mtime = 0
            member.uid = 0
            member.gid = 0
            member.uname = ""
            member.gname = ""
            with source_path.open(mode="rb") as stream:
                archive.addfile(tarinfo=member, fileobj=stream)


def tar_member_paths(*, archive: tarfile.TarFile) -> tuple[tarfile.TarInfo, ...]:
    members = tuple(archive.getmembers())
    names: list[str] = []
    for member in members:
        if not member.isfile():
            raise ValueError(f"tar contains a non-regular member: {member.name!r}")
        relative_path = f"./{member.name}"
        validate_archive_relative_path(relative_path=relative_path)
        names.append(relative_path)
    if len(names) != len(set(names)):
        raise ValueError("tar contains duplicate members")
    return members


def verify_tar(
    *, tar_path: Path, records: tuple[tuple[str, str], ...]
) -> None:
    expected = {relative_path: digest for relative_path, digest in records}
    with tarfile.open(name=tar_path, mode="r:") as archive:
        members = tar_member_paths(archive=archive)
        observed_paths = tuple(f"./{member.name}" for member in members)
        if observed_paths != tuple(expected):
            raise ValueError("tar member paths differ from the tree checksum ledger")
        for member in members:
            stream = archive.extractfile(member=member)
            if stream is None:
                raise ValueError(f"tar member cannot be read: {member.name!r}")
            digest = hashlib.sha256()
            while block := stream.read(1024 * 1024):
                digest.update(block)
            if digest.hexdigest() != expected[f"./{member.name}"]:
                raise ValueError(f"tar member checksum mismatch: {member.name!r}")


def archive_paths(*, directory: Path, stage: StageDefinition) -> ArchivePaths:
    prefix = f"v4-{stage.stage}"
    return ArchivePaths(
        directory=directory,
        files0=directory / f"{prefix}.files0",
        tree_ledger=directory / f"{prefix}.tree.sha256",
        tar=directory / f"{prefix}.tar",
        tar_checksum=directory / f"{prefix}.tar.sha256",
    )


def verify_schedule_closed(
    *,
    schedule_path: Path,
    schedule_checksum_path: Path,
    runs_root: Path,
    planner_script: Path,
    planner_python: Path,
) -> None:
    for phase in ("primary", "retry"):
        result = run_command(
            arguments=[
                str(planner_python),
                str(planner_script),
                "--schedule",
                str(schedule_path),
                "--checksum",
                str(schedule_checksum_path),
                "--runs-root",
                str(runs_root),
                "--phase",
                phase,
            ]
        )
        if result.stdout:
            raise ValueError(f"stage still has a pending {phase} action")


def create_stage_archive(
    *,
    stage: StageDefinition,
    runs_root: Path,
    schedule_path: Path,
    schedule_checksum_path: Path,
    planner_script: Path,
    planner_python: Path,
    archive_root: Path,
    recorded_runs_root: Path,
) -> Path:
    rows = load_schedule(path=schedule_path, stage=stage)
    run_directories = stage_run_directories(
        runs_root=runs_root,
        rows=rows,
        stage=stage,
    )
    for run_directory in run_directories:
        reject_symlinks_and_non_regular_entries(root=run_directory)
        verify_artifact_ledger(
            run_directory=run_directory,
            recorded_runs_root=recorded_runs_root,
        )
    require_registered_retry_set(run_directories=run_directories, rows=rows)
    verify_schedule_closed(
        schedule_path=schedule_path,
        schedule_checksum_path=schedule_checksum_path,
        runs_root=runs_root,
        planner_script=planner_script,
        planner_python=planner_python,
    )
    records = tree_records(
        runs_root=runs_root,
        run_directories=run_directories,
    )

    archive_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    require_regular_directory(path=archive_root, label="archive root")
    final_directory = archive_root / f"v4-{stage.stage}"
    if final_directory.exists() or final_directory.is_symlink():
        raise FileExistsError(f"stage archive already exists: {final_directory}")
    temporary_directory = Path(
        tempfile.mkdtemp(prefix=f".v4-{stage.stage}.", dir=archive_root)
    )
    published = False
    try:
        paths = archive_paths(directory=temporary_directory, stage=stage)
        paths.files0.write_bytes(render_files0(records=records))
        paths.tree_ledger.write_bytes(render_tree_ledger(records=records))
        write_tar(tar_path=paths.tar, runs_root=runs_root, records=records)
        verify_tar(tar_path=paths.tar, records=records)
        if tree_records(
            runs_root=runs_root,
            run_directories=run_directories,
        ) != records:
            raise ValueError("stage source tree changed while it was archived")
        verify_schedule_closed(
            schedule_path=schedule_path,
            schedule_checksum_path=schedule_checksum_path,
            runs_root=runs_root,
            planner_script=planner_script,
            planner_python=planner_python,
        )
        require_registered_retry_set(run_directories=run_directories, rows=rows)
        tar_digest = sha256_file(path=paths.tar)
        paths.tar_checksum.write_text(
            f"{tar_digest}  {paths.tar.name}\n",
            encoding="utf-8",
        )
        for path in (
            paths.files0,
            paths.tree_ledger,
            paths.tar,
            paths.tar_checksum,
        ):
            path.chmod(mode=stat.S_IMODE(path.stat().st_mode) & ~0o222)
        temporary_directory.chmod(mode=0o500)
        rename_directory_exclusive(
            source=temporary_directory,
            destination=final_directory,
        )
        published = True
    finally:
        if not published and temporary_directory.exists():
            temporary_directory.chmod(mode=0o700)
            shutil.rmtree(path=temporary_directory)
    return final_directory


def parse_systemctl_properties(
    *, output: bytes, expected: frozenset[str]
) -> dict[str, str]:
    properties: dict[str, str] = {}
    for line in output.decode(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator != "=" or name not in expected or not value or name in properties:
            raise ValueError(f"malformed systemd service state: {line!r}")
        properties[name] = value
    if properties.keys() != expected:
        raise ValueError("systemd service state omits required properties")
    return properties


def parse_systemctl_state(*, output: bytes) -> ServiceState:
    properties = parse_systemctl_properties(
        output=output,
        expected=frozenset(
            {
                "LoadState",
                "ActiveState",
                "SubState",
                "Result",
                "ExecMainStatus",
                "MainPID",
            }
        ),
    )
    return ServiceState.model_validate(
        obj={
            "load_state": properties["LoadState"],
            "active_state": properties["ActiveState"],
            "sub_state": properties["SubState"],
            "result": properties["Result"],
            "exec_main_status": int(properties["ExecMainStatus"]),
            "main_pid": int(properties["MainPID"]),
        },
        strict=True,
    )


def parse_retention_state(
    *, output: bytes, expected_service: ServiceName
) -> RetentionState:
    properties = parse_systemctl_properties(
        output=output,
        expected=frozenset(
            {
                "LoadState",
                "ActiveState",
                "SubState",
                "Result",
                "ExecMainStatus",
                "MainPID",
                "Wants",
            }
        ),
    )
    state = RetentionState.model_validate(
        obj={
            "load_state": properties["LoadState"],
            "active_state": properties["ActiveState"],
            "sub_state": properties["SubState"],
            "result": properties["Result"],
            "exec_main_status": int(properties["ExecMainStatus"]),
            "main_pid": int(properties["MainPID"]),
            "wants": frozenset(properties["Wants"].split()),
        },
        strict=True,
    )
    if state.wants != frozenset({expected_service}):
        raise ValueError("retention service has the wrong Wants dependency")
    return state


def verify_host_closure(*, bench_root: Path, stage: StageDefinition) -> None:
    retention = run_command(
        arguments=[
            "systemctl",
            "show",
            stage.retention_service,
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=Result",
            "--property=ExecMainStatus",
            "--property=MainPID",
            "--property=Wants",
            "--no-pager",
        ]
    )
    parse_retention_state(
        output=retention.stdout,
        expected_service=stage.service,
    )
    systemctl = run_command(
        arguments=[
            "systemctl",
            "show",
            stage.service,
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=Result",
            "--property=ExecMainStatus",
            "--property=MainPID",
            "--no-pager",
        ]
    )
    parse_systemctl_state(output=systemctl.stdout)
    for relative_path, expected_digest in FROZEN_FILE_SHA256.items():
        path = bench_root / relative_path
        require_regular_file(path=path, label="frozen campaign file")
        if sha256_file(path=path) != expected_digest:
            raise ValueError(f"frozen campaign file drifted: {relative_path}")
    run_command(
        arguments=[
            str(bench_root / "runner" / "verify-protocol.sh"),
            "--protocol",
            str(bench_root / "protocol"),
        ]
    )
    environment = run_command(
        arguments=[
            "python3",
            str(bench_root / "runner" / "environment_manifest.py"),
        ]
    )
    if environment.stdout != (bench_root / "protocol" / "environment.json").read_bytes():
        raise ValueError("current environment differs from the frozen V4 environment")
    if stage.next_stage is not None:
        for suffix in (".tsv", ".tsv.sha256"):
            next_path = bench_root / "schedules" / f"{stage.next_stage}{suffix}"
            if next_path.exists() or next_path.is_symlink():
                raise ValueError("next-stage schedule exists before the current gate")


def create_vps_archive(*, stage: StageDefinition) -> Path:
    bench_root = Path("/root/bench-v2")
    lock_path = bench_root / "runner.lock"
    require_regular_file(path=lock_path, label="runner lock")
    with lock_path.open(mode="r+b") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_host_closure(bench_root=bench_root, stage=stage)
        schedule_path = bench_root / "schedules" / f"{stage.stage}.tsv"
        schedule_checksum_path = schedule_path.with_suffix(".tsv.sha256")
        digest, _ = parse_single_checksum(
            path=schedule_checksum_path,
            permitted_paths=frozenset({str(schedule_path)}),
        )
        if sha256_file(path=schedule_path) != digest:
            raise ValueError("VPS stage schedule checksum mismatch")
        return create_stage_archive(
            stage=stage,
            runs_root=bench_root / "runs",
            schedule_path=schedule_path,
            schedule_checksum_path=schedule_checksum_path,
            planner_script=bench_root / "runner" / "resume_schedule.py",
            planner_python=bench_root / "runner" / ".venv" / "bin" / "python",
            archive_root=bench_root / "archives",
            recorded_runs_root=bench_root / "runs",
        )


def archive_file_set(*, directory: Path, stage: StageDefinition) -> ArchivePaths:
    require_regular_directory(path=directory, label="stage archive directory")
    expected_names = {f"v4-{stage.stage}.{suffix}" for suffix in ARCHIVE_SUFFIXES}
    entries = tuple(directory.iterdir())
    if {entry.name for entry in entries} != expected_names:
        raise ValueError("stage archive directory has an unexpected file set")
    paths = archive_paths(directory=directory, stage=stage)
    for path in (paths.files0, paths.tree_ledger, paths.tar, paths.tar_checksum):
        require_regular_file(path=path, label="stage archive file")
        if stat.S_IMODE(path.stat().st_mode) & 0o222:
            raise ValueError(f"stage archive file is writable: {path.name}")
    return paths


def parse_files0(*, path: Path) -> tuple[str, ...]:
    require_regular_file(path=path, label="NUL path ledger")
    contents = path.read_bytes()
    if not contents or not contents.endswith(b"\x00"):
        raise ValueError("NUL path ledger must be non-empty and terminated")
    raw_paths = contents.split(b"\x00")[:-1]
    paths = tuple(raw_path.decode(encoding="utf-8") for raw_path in raw_paths)
    for relative_path in paths:
        validate_archive_relative_path(relative_path=relative_path)
    if len(paths) != len(set(paths)):
        raise ValueError("NUL path ledger contains duplicate paths")
    if list(paths) != sorted(paths, key=lambda value: os.fsencode(value)):
        raise ValueError("NUL path ledger paths are not bytewise sorted")
    return paths


def extract_verified_tar(
    *,
    tar_path: Path,
    records: tuple[tuple[str, str], ...],
    destination: Path,
) -> None:
    expected_paths = tuple(relative_path for relative_path, _ in records)
    with tarfile.open(name=tar_path, mode="r:") as archive:
        members = tar_member_paths(archive=archive)
        observed_paths = tuple(f"./{member.name}" for member in members)
        if observed_paths != expected_paths:
            raise ValueError("tar members differ from the verified tree ledger")
        for member in members:
            target = destination / member.name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            stream = archive.extractfile(member=member)
            if stream is None:
                raise ValueError(f"tar member cannot be read: {member.name!r}")
            with target.open(mode="xb") as output:
                shutil.copyfileobj(fsrc=stream, fdst=output)
            target.chmod(mode=member.mode & 0o777)
    for relative_path, expected_digest in records:
        path = destination / relative_path.removeprefix("./")
        require_regular_file(path=path, label="extracted stage file")
        if sha256_file(path=path) != expected_digest:
            raise ValueError(f"extracted checksum mismatch: {relative_path}")
    actual_paths = sorted(
        (
            f"./{path.relative_to(destination).as_posix()}"
            for path in destination.rglob(pattern="*")
            if path.is_file() and not path.is_symlink()
        ),
        key=lambda value: os.fsencode(value),
    )
    if tuple(actual_paths) != expected_paths:
        raise ValueError("extracted tree has an unexpected path set")


def make_tree_read_only(*, root: Path) -> None:
    paths = sorted(
        root.rglob(pattern="*"),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for path in paths:
        mode = stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)
        path.chmod(mode=mode & ~0o222, follow_symlinks=False)
    root_mode = stat.S_IMODE(root.stat().st_mode)
    root.chmod(mode=root_mode & ~0o222)


def import_stage_archive(
    *,
    stage: StageDefinition,
    archive_directory: Path,
    repository_root: Path,
    recorded_runs_root: Path,
) -> tuple[Path, ...]:
    paths = archive_file_set(directory=archive_directory, stage=stage)
    tar_digest, _ = parse_single_checksum(
        path=paths.tar_checksum,
        permitted_paths=frozenset({paths.tar.name}),
    )
    if sha256_file(path=paths.tar) != tar_digest:
        raise ValueError("stage tar checksum mismatch")
    tree_ledger_contents = paths.tree_ledger.read_bytes()
    records = parse_tree_ledger_contents(contents=tree_ledger_contents)
    files0_paths = parse_files0(path=paths.files0)
    if files0_paths != tuple(relative_path for relative_path, _ in records):
        raise ValueError("NUL path ledger and tree checksum ledger disagree")
    verify_tar(tar_path=paths.tar, records=records)

    schedule_path = repository_root / "results" / "schedules" / "v4" / f"{stage.stage}.tsv"
    portable_checksum = schedule_path.with_suffix(".tsv.sha256")
    schedule_digest, _ = parse_single_checksum(
        path=portable_checksum,
        permitted_paths=frozenset(
            {schedule_path.name, f"./{schedule_path.name}"}
        ),
    )
    if sha256_file(path=schedule_path) != schedule_digest:
        raise ValueError("portable stage schedule checksum mismatch")
    rows = load_schedule(path=schedule_path, stage=stage)

    results_root = repository_root / "results"
    raw_root = results_root / "raw"
    ledger_root = results_root / "raw-ledgers"
    require_regular_directory(path=results_root, label="results root")
    if raw_root.exists() or raw_root.is_symlink():
        require_regular_directory(path=raw_root, label="raw results root")
    if ledger_root.exists() or ledger_root.is_symlink():
        require_regular_directory(path=ledger_root, label="raw ledger root")
    ledger_destination = ledger_root / f"v4-{stage.stage}.tree.sha256"
    if ledger_destination.exists() or ledger_destination.is_symlink():
        raise FileExistsError(f"raw stage ledger already exists: {ledger_destination}")

    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".v4-import-{stage.stage}.", dir=results_root)
    )
    installed: list[Path] = []
    try:
        extraction_root = temporary_root / "extracted"
        extraction_root.mkdir(mode=0o700)
        extract_verified_tar(
            tar_path=paths.tar,
            records=records,
            destination=extraction_root,
        )
        run_directories = stage_run_directories(
            runs_root=extraction_root,
            rows=rows,
            stage=stage,
        )
        require_registered_retry_set(run_directories=run_directories, rows=rows)
        for run_directory in run_directories:
            verify_artifact_ledger(
                run_directory=run_directory,
                recorded_runs_root=recorded_runs_root,
            )
        destinations = tuple(raw_root / run_directory.name for run_directory in run_directories)
        existing = [path for path in destinations if path.exists() or path.is_symlink()]
        if existing:
            raise FileExistsError(f"raw stage destinations already exist: {existing!r}")
        raw_root.mkdir(mode=0o755, exist_ok=True)
        ledger_root.mkdir(mode=0o755, exist_ok=True)
        require_regular_directory(path=raw_root, label="raw results root")
        require_regular_directory(path=ledger_root, label="raw ledger root")
        for run_directory, destination in zip(
            run_directories,
            destinations,
            strict=True,
        ):
            rename_directory_exclusive(
                source=run_directory,
                destination=destination,
            )
            make_tree_read_only(root=destination)
            installed.append(destination)
        with ledger_destination.open(mode="xb") as output:
            output.write(tree_ledger_contents)
        ledger_destination.chmod(mode=0o444)
        for relative_path, expected_digest in records:
            installed_path = raw_root / relative_path.removeprefix("./")
            if sha256_file(path=installed_path) != expected_digest:
                raise ValueError(f"installed checksum mismatch: {relative_path}")
    finally:
        if temporary_root.exists():
            shutil.rmtree(path=temporary_root)
    return tuple(installed)


def verify_imported_stage(
    *,
    stage: StageDefinition,
    archive_directory: Path,
    repository_root: Path,
    recorded_runs_root: Path,
) -> tuple[Path, ...]:
    paths = archive_file_set(directory=archive_directory, stage=stage)
    tar_digest, _ = parse_single_checksum(
        path=paths.tar_checksum,
        permitted_paths=frozenset({paths.tar.name}),
    )
    if sha256_file(path=paths.tar) != tar_digest:
        raise ValueError("stage tar checksum mismatch")
    tree_ledger_contents = paths.tree_ledger.read_bytes()
    records = parse_tree_ledger_contents(contents=tree_ledger_contents)
    files0_paths = parse_files0(path=paths.files0)
    if files0_paths != tuple(relative_path for relative_path, _ in records):
        raise ValueError("NUL path ledger and tree checksum ledger disagree")
    verify_tar(tar_path=paths.tar, records=records)

    schedule_path = (
        repository_root
        / "results"
        / "schedules"
        / "v4"
        / f"{stage.stage}.tsv"
    )
    portable_checksum = schedule_path.with_suffix(".tsv.sha256")
    schedule_digest, _ = parse_single_checksum(
        path=portable_checksum,
        permitted_paths=frozenset({schedule_path.name, f"./{schedule_path.name}"}),
    )
    if sha256_file(path=schedule_path) != schedule_digest:
        raise ValueError("portable stage schedule checksum mismatch")
    rows = load_schedule(path=schedule_path, stage=stage)

    raw_root = repository_root / "results" / "raw"
    ledger_destination = (
        repository_root
        / "results"
        / "raw-ledgers"
        / f"v4-{stage.stage}.tree.sha256"
    )
    require_regular_file(path=ledger_destination, label="imported raw stage ledger")
    if ledger_destination.read_bytes() != tree_ledger_contents:
        raise ValueError("imported raw stage ledger differs from verified archive")
    if stat.S_IMODE(ledger_destination.stat().st_mode) & 0o222:
        raise ValueError("imported raw stage ledger must be read-only")

    run_directories = stage_run_directories(
        runs_root=raw_root,
        rows=rows,
        stage=stage,
    )
    require_registered_retry_set(run_directories=run_directories, rows=rows)
    for run_directory in run_directories:
        reject_symlinks_and_non_regular_entries(root=run_directory)
        verify_artifact_ledger(
            run_directory=run_directory,
            recorded_runs_root=recorded_runs_root,
        )
        for path in (run_directory, *run_directory.rglob(pattern="*")):
            if stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) & 0o222:
                raise ValueError(f"imported stage path is writable: {path}")

    actual_paths = tuple(
        sorted(
            (
                f"./{path.relative_to(raw_root).as_posix()}"
                for run_directory in run_directories
                for path in run_directory.rglob(pattern="*")
                if path.is_file() and not path.is_symlink()
            ),
            key=os.fsencode,
        )
    )
    expected_paths = tuple(relative_path for relative_path, _ in records)
    if actual_paths != expected_paths:
        raise ValueError("imported stage path set differs from verified archive")
    for relative_path, expected_digest in records:
        imported_path = raw_root / relative_path.removeprefix("./")
        require_regular_file(path=imported_path, label="imported stage file")
        if sha256_file(path=imported_path) != expected_digest:
            raise ValueError(f"imported stage checksum mismatch: {relative_path}")
    return run_directories


def parse_arguments(
    *, arguments: Sequence[str] | None = None
) -> tuple[
    Literal["create", "import", "verify-import"],
    StageDefinition,
    Path | None,
    Path | None,
]:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--stage", choices=tuple(STAGE_DEFINITIONS), required=True)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--stage", choices=tuple(STAGE_DEFINITIONS), required=True)
    import_parser.add_argument("--archive-directory", type=Path, required=True)
    import_parser.add_argument("--repository-root", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify-import")
    verify_parser.add_argument("--stage", choices=tuple(STAGE_DEFINITIONS), required=True)
    verify_parser.add_argument("--archive-directory", type=Path, required=True)
    verify_parser.add_argument("--repository-root", type=Path, required=True)
    parsed = parser.parse_args(args=arguments)
    stage_name: StageName = parsed.stage
    return (
        parsed.command,
        STAGE_DEFINITIONS[stage_name],
        getattr(parsed, "archive_directory", None),
        getattr(parsed, "repository_root", None),
    )


def main(*, arguments: Sequence[str] | None = None) -> int:
    command, stage, archive_directory, repository_root = parse_arguments(
        arguments=arguments
    )
    if command == "create":
        output = create_vps_archive(stage=stage)
        print(output)
        return 0
    if archive_directory is None or repository_root is None:
        raise ValueError("import requires archive and repository paths")
    if command == "import":
        imported = import_stage_archive(
            stage=stage,
            archive_directory=archive_directory,
            repository_root=repository_root,
            recorded_runs_root=Path("/root/bench-v2/runs"),
        )
        print(f"imported_stage={stage.stage} physical_attempts={len(imported)}")
        return 0
    verified = verify_imported_stage(
        stage=stage,
        archive_directory=archive_directory,
        repository_root=repository_root,
        recorded_runs_root=Path("/root/bench-v2/runs"),
    )
    print(f"verified_stage={stage.stage} physical_attempts={len(verified)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
