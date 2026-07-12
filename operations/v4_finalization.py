#!/usr/bin/env python3
"""Freeze and verify V4 finalization boundaries without exposing sealed identities."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import re
import secrets
import stat
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from analysis.blind_review import (
    CREDENTIAL_LIKE_PATH_FRAGMENTS,
    CREDENTIAL_LIKE_PATTERNS,
    FROZEN_RUBRIC_SHA256,
    REVIEW_FIELDNAMES,
    REVIEW_INSTRUCTIONS,
    RUBRIC_ITEMS,
    BundlePacket,
    CompletedReviewRow,
    HashedSourceFile,
    PacketFile,
    PacketFileRole,
    PacketManifest,
    PacketPayload,
    PublicProvenance,
    PublicReviewItem,
    PublicRunMapping,
    ReviewBundleManifest,
    ReviewStatus,
    packet_payload_sha256,
)
from analysis.gate_eligibility import GateAttestation, canonical_json as gate_json
from analysis.verify_gate_disclosure import DisclosedGateKey, GateKeyDisclosure


type DatasetName = Literal["n3", "n5", "ablation"]

HexDigest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PrefixedHexDigest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$"),
]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
NonNegativeInteger = Annotated[int, Field(ge=0, strict=True)]

DATASET_ORDER: dict[DatasetName, int] = {"n3": 0, "n5": 1, "ablation": 2}
EVALUATION_FILENAMES: frozenset[str] = frozenset({"scores.jsonl", "summary.json"})
PUBLIC_BUNDLE_FILENAMES: frozenset[str] = frozenset(
    {
        "ARTIFACT_REVIEW.md",
        "REVIEW_INSTRUCTIONS.md",
        "completed-review.csv",
        "item-review.jsonl",
        "label-mapping.jsonl",
        "provenance.json",
    }
)
PUBLIC_HASHED_FILENAMES: frozenset[str] = PUBLIC_BUNDLE_FILENAMES - {
    "provenance.json"
}
CORE_ATTESTATION_PATH = "results/gates/core-n3.json"
EXTENSION_ATTESTATION_PATH = "results/gates/core-extend-n5.json"
NEUTRAL_LABEL = re.compile(pattern=r"^case-[0-9a-f]{16}$")
MAX_PUBLIC_CANDIDATE_BYTES = 95 * 1024 * 1024
PUBLIC_CREDENTIAL_PATH_FRAGMENTS: tuple[bytes, ...] = (
    *CREDENTIAL_LIKE_PATH_FRAGMENTS,
    b"credential",
    b"secret",
)
EMPTY_FILE_SHA256 = hashlib.sha256(b"").hexdigest()
SAFE_EMPTY_RUNTIME_CREDENTIAL_PATH = re.compile(
    pattern=(
        r"^\./[a-z0-9][a-z0-9_-]*/runtime/home/"
        r"(?:\.codex/auth\.json|\.claude/\.credentials\.json)$"
    )
)


class StrictModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=False,
    )


class RegularSnapshot(StrictModel):
    path: Path
    data: bytes = Field(repr=False)
    sha256: HexDigest
    size_bytes: NonNegativeInteger
    mode: NonNegativeInteger


class FileCommitment(StrictModel):
    path: NonEmptyString
    size_bytes: NonNegativeInteger
    sha256: HexDigest

    @field_validator("path")
    @classmethod
    def require_canonical_relative_path(cls, value: str) -> str:
        require_safe_relative_path(value=value, label="committed file path")
        return value


class EvaluationFreezeCommitment(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-evaluation-freeze"] = "v4-evaluation-freeze"
    evaluation_root: NonEmptyString
    selection_mode: Literal["eligible-datasets", "no-eligible-primary"]
    datasets: list[DatasetName]
    execution_environment: FileCommitment
    selection_source: FileCommitment
    files: list[FileCommitment]

    @field_validator("evaluation_root")
    @classmethod
    def require_safe_evaluation_root(cls, value: str) -> str:
        require_safe_relative_path(value=value, label="evaluation root")
        return value

    @model_validator(mode="after")
    def require_complete_sorted_selection(self) -> EvaluationFreezeCommitment:
        ordered = (
            []
            if not self.datasets
            else validate_dataset_selection(
                datasets=self.datasets,
                allow_empty_selection=False,
            )
        )
        if self.datasets != ordered:
            raise ValueError("evaluation commitment datasets are not canonically ordered")
        expected_mode = "eligible-datasets" if self.datasets else "no-eligible-primary"
        if self.selection_mode != expected_mode:
            raise ValueError("evaluation selection mode does not match its dataset set")
        expected_files = [
            f"{self.evaluation_root}/{dataset}/{filename}"
            for dataset in self.datasets
            for filename in sorted(EVALUATION_FILENAMES)
        ]
        if [record.path for record in self.files] != expected_files:
            raise ValueError("evaluation commitment file set or order is invalid")
        return self


class EvaluationExecutionEnvironment(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-evaluation-execution-environment"] = (
        "v4-evaluation-execution-environment"
    )
    repository_commit: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
    python_implementation: NonEmptyString
    python_version: NonEmptyString
    python_executable: NonEmptyString
    python_executable_sha256: HexDigest
    platform_system: NonEmptyString
    platform_release: NonEmptyString
    platform_machine: NonEmptyString
    byteorder: Literal["little", "big"]
    uv_lock_sha256: HexDigest
    evaluator_manifest_sha256: HexDigest


class FrozenPacket(StrictModel):
    neutral_label: NonEmptyString
    task_variant: NonEmptyString
    packet_sha256: PrefixedHexDigest
    runner_image_sha256: PrefixedHexDigest
    packet_manifest: FileCommitment


class ReviewerIdentity(StrictModel):
    display_name: NonEmptyString
    affiliation: NonEmptyString | None


class PrimaryReviewer(ReviewerIdentity):
    role: NonEmptyString
    prior_exposure: NonEmptyString


class NoSecondReview(StrictModel):
    occurred: Literal[False]
    disclosure: NonEmptyString


class CompletedSecondReview(StrictModel):
    occurred: Literal[True]
    reviewer: ReviewerIdentity
    scope: NonEmptyString
    disclosure: NonEmptyString


class NoAdjudication(StrictModel):
    occurred: Literal[False]
    rows_changed: Literal[0]
    disclosure: NonEmptyString


class CompletedAdjudication(StrictModel):
    occurred: Literal[True]
    rows_changed: NonNegativeInteger
    adjudicator: ReviewerIdentity
    method: NonEmptyString
    disclosure: NonEmptyString


class ProtocolDeviation(StrictModel):
    deviation_id: Literal[
        "submitted-scripts-not-executed",
        "benchmark-sandbox-exposed-host-secrets",
    ]
    disclosure: NonEmptyString


class ArtifactReviewEditorialMetadata(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    completed_review_sha256: PrefixedHexDigest
    frozen_at: NonEmptyString
    primary_reviewer: PrimaryReviewer
    second_review: NoSecondReview | CompletedSecondReview = Field(
        discriminator="occurred"
    )
    adjudication: NoAdjudication | CompletedAdjudication = Field(
        discriminator="occurred"
    )
    protocol_deviations: list[ProtocolDeviation]

    @field_validator("frozen_at")
    @classmethod
    def require_aware_datetime(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("review disclosure frozen_at must include a UTC offset")
        return value

    @model_validator(mode="after")
    def require_registered_protocol_deviation(
        self,
    ) -> ArtifactReviewEditorialMetadata:
        deviation_ids = {
            deviation.deviation_id for deviation in self.protocol_deviations
        }
        if deviation_ids != {
            "submitted-scripts-not-executed",
            "benchmark-sandbox-exposed-host-secrets",
        } or len(self.protocol_deviations) != 2:
            raise ValueError("review disclosure must record both registered deviations")
        if self.adjudication.occurred and not self.second_review.occurred:
            raise ValueError("blind adjudication requires an occurred second review")
        return self


class SealedMappingFreezeCommitment(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-sealed-mapping-freeze"] = "v4-sealed-mapping-freeze"
    mapping: FileCommitment

    @model_validator(mode="after")
    def require_fixed_mapping_path(self) -> SealedMappingFreezeCommitment:
        if self.mapping.path != "sealed-mapping.json":
            raise ValueError("sealed mapping commitment must use its fixed opaque path")
        if self.mapping.size_bytes == 0:
            raise ValueError("sealed mapping commitment cannot bind an empty file")
        return self


class ReviewFreezeCommitment(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-review-freeze"] = "v4-review-freeze"
    bundle: FileCommitment
    primary_review: FileCommitment
    review: FileCommitment
    ledger_sha256: PrefixedHexDigest
    matrix_sha256: PrefixedHexDigest
    rubric_source_sha256: PrefixedHexDigest
    schedule_files: list[HashedSourceFile]
    packets: list[FrozenPacket]
    editorial_metadata: FileCommitment
    sealed_mapping: FileCommitment
    sealed_mapping_freeze_sha256: HexDigest

    @model_validator(mode="after")
    def require_fixed_paths_and_unique_packets(self) -> ReviewFreezeCommitment:
        if (
            self.bundle.path != "bundle.json"
            or self.primary_review.path != "primary-review.csv"
            or self.review.path != "review.csv"
        ):
            raise ValueError("review commitment must bind bundle.json and review.csv")
        if self.editorial_metadata.path != "artifact-review-editorial.json":
            raise ValueError("review commitment must bind reviewer editorial metadata")
        labels = [packet.neutral_label for packet in self.packets]
        hashes = [packet.packet_sha256 for packet in self.packets]
        if not labels or len(labels) != len(set(labels)) or len(hashes) != len(set(hashes)):
            raise ValueError("review commitment packet set must be non-empty and unique")
        return self


class ReviewDifferenceReceipt(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-review-difference"] = "v4-review-difference"
    primary_review_sha256: PrefixedHexDigest
    completed_review_sha256: PrefixedHexDigest
    rows_changed: NonNegativeInteger


class PublicCandidateScanReceipt(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-public-candidate-scan"] = "v4-public-candidate-scan"
    source: Literal["working-tree", "git-commit"]
    repository_commit: Annotated[
        str, StringConstraints(pattern=r"^[0-9a-f]{40}$")
    ] | None
    path_count: NonNegativeInteger
    aggregate_sha256: HexDigest


class FinalizedReviewVerification(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["v4-finalized-review-verification"] = (
        "v4-finalized-review-verification"
    )
    review_commitment_sha256: HexDigest
    completed_review_sha256: HexDigest
    completed_review_size_bytes: NonNegativeInteger
    provenance_sha256: HexDigest
    editorial_metadata_sha256: HexDigest
    sealed_mapping_freeze_sha256: HexDigest
    sealed_mapping_sha256: HexDigest
    packet_count: NonNegativeInteger
    verified: Literal[True] = True


def canonical_json(*, value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_model_bytes(*, model: BaseModel) -> bytes:
    return f"{canonical_json(value=model.model_dump(mode='json'))}\n".encode(
        encoding="utf-8"
    )


def sha256_bytes(*, data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prefixed_sha256_bytes(*, data: bytes) -> str:
    return f"sha256:{sha256_bytes(data=data)}"


def absolute_path(*, path: Path) -> Path:
    if ".." in path.parts:
        raise ValueError(f"paths must not contain '..' components: {path}")
    return path if path.is_absolute() else Path.cwd() / path


def path_exists_including_symlink(*, path: Path) -> bool:
    return os.path.lexists(path)


def validate_path_components(
    *, path: Path, final_kind: Literal["file", "directory", "parent"]
) -> Path:
    absolute = absolute_path(path=path)
    parts = absolute.parts
    current = Path(parts[0])
    final_index = len(parts) - 1 if final_kind != "parent" else len(parts) - 2
    for index, component in enumerate(parts[1 : final_index + 1], start=1):
        current = current / component
        file_stat = os.lstat(current)
        if stat.S_ISLNK(file_stat.st_mode):
            raise ValueError(f"path must not traverse a symlink: {current}")
        is_final = index == final_index
        if not is_final or final_kind in {"directory", "parent"}:
            if not stat.S_ISDIR(file_stat.st_mode):
                raise ValueError(f"path component must be a directory: {current}")
        elif final_kind == "file" and not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"path must be a regular file: {current}")
    return absolute


def require_regular_directory(*, path: Path, label: str) -> Path:
    absolute = validate_path_components(path=path, final_kind="directory")
    file_stat = os.lstat(absolute)
    if not stat.S_ISDIR(file_stat.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink directory: {absolute}")
    return absolute


def read_regular_snapshot(
    *, path: Path, label: str, max_size_bytes: int | None = None
) -> RegularSnapshot:
    absolute = validate_path_components(path=path, final_kind="file")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(absolute, flags)
    with os.fdopen(descriptor, mode="rb", closefd=True) as stream:
        file_stat = os.fstat(stream.fileno())
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"{label} changed type while opened: {absolute}")
        if max_size_bytes is not None and file_stat.st_size > max_size_bytes:
            raise ValueError(f"{label} exceeds {max_size_bytes} bytes: {absolute}")
        data = stream.read()
    validate_path_components(path=absolute, final_kind="file")
    return RegularSnapshot(
        path=absolute,
        data=data,
        sha256=sha256_bytes(data=data),
        size_bytes=len(data),
        mode=stat.S_IMODE(file_stat.st_mode),
    )


def require_new_output(*, path: Path) -> Path:
    absolute = absolute_path(path=path)
    validate_path_components(path=absolute, final_kind="parent")
    if path_exists_including_symlink(path=absolute):
        raise ValueError(f"output must not already exist: {absolute}")
    return absolute


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


def write_atomic_exclusive(*, path: Path, data: bytes, mode: int = 0o644) -> None:
    output = require_new_output(path=path)
    temporary = output.parent / f".{output.name}.tmp-{secrets.token_hex(16)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, mode)
    try:
        with os.fdopen(descriptor, mode="wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.link(temporary, output, follow_symlinks=False)
        fsync_directory(path=output.parent)
        written = read_regular_snapshot(path=output, label="published output")
        if written.data != data or written.mode != mode:
            raise ValueError(f"published output failed byte/mode verification: {output}")
    finally:
        if path_exists_including_symlink(path=temporary):
            temporary.unlink()
            fsync_directory(path=output.parent)


def require_safe_relative_path(*, value: str, label: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or relative.is_absolute()
        or relative.as_posix() != value
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"{label} must be a canonical relative POSIX path: {value!r}")
    return relative


def read_canonical_paths0(*, path: Path) -> tuple[str, ...]:
    snapshot = read_regular_snapshot(path=path, label="public candidate path list")
    if not snapshot.data or not snapshot.data.endswith(b"\0"):
        raise ValueError("public candidate path list must be non-empty and NUL-terminated")
    raw_paths = snapshot.data[:-1].split(b"\0")
    paths = tuple(raw_path.decode(encoding="utf-8", errors="strict") for raw_path in raw_paths)
    for relative_path in paths:
        if any(character in relative_path for character in ("\n", "\r", "\t")):
            raise ValueError("public candidate paths must not contain control separators")
        require_safe_relative_path(
            value=relative_path,
            label="public candidate path",
        )
    if paths != tuple(sorted(set(paths))):
        raise ValueError("public candidate paths must be unique and bytewise sorted")
    return paths


def read_committed_candidate(
    *, repository_root: Path, commit: str, relative_path: str
) -> bytes:
    tree_record = run_git(
        repository_root=repository_root,
        arguments=["--literal-pathspecs", "ls-tree", "-z", commit, "--", relative_path],
    )
    if not tree_record.endswith(b"\0") or tree_record.count(b"\0") != 1:
        raise ValueError(f"committed candidate is missing or ambiguous: {relative_path}")
    metadata, recorded_path = tree_record[:-1].split(b"\t", maxsplit=1)
    if recorded_path.decode(encoding="utf-8", errors="strict") != relative_path:
        raise ValueError(f"committed candidate path differs: {relative_path}")
    mode, object_type, _ = metadata.split(b" ", maxsplit=2)
    if mode != b"100644" or object_type != b"blob":
        raise ValueError(f"committed candidate is not a 100644 blob: {relative_path}")
    size_bytes = int(
        run_git(
            repository_root=repository_root,
            arguments=["cat-file", "-s", f"{commit}:{relative_path}"],
        )
    )
    if size_bytes > MAX_PUBLIC_CANDIDATE_BYTES:
        raise ValueError(f"public candidate exceeds 95 MiB: {relative_path}")
    return run_git(
        repository_root=repository_root,
        arguments=["cat-file", "blob", f"{commit}:{relative_path}"],
    )


def validate_public_candidate(*, relative_path: str, data: bytes) -> None:
    lowered_path = relative_path.casefold().encode(encoding="utf-8")
    lowered_data = data.lower()
    if any(fragment in lowered_path for fragment in PUBLIC_CREDENTIAL_PATH_FRAGMENTS):
        raise ValueError(f"credential-like public candidate path: {relative_path}")
    validate_embedded_credential_paths(relative_path=relative_path, data=data)
    if any(pattern.search(data) is not None for pattern in CREDENTIAL_LIKE_PATTERNS):
        raise ValueError(f"credential-like content in public candidate: {relative_path}")
    if len(data) > MAX_PUBLIC_CANDIDATE_BYTES:
        raise ValueError(f"public candidate exceeds 95 MiB: {relative_path}")


def validate_embedded_credential_paths(*, relative_path: str, data: bytes) -> None:
    lowered_data = data.lower()
    if not any(fragment in lowered_data for fragment in CREDENTIAL_LIKE_PATH_FRAGMENTS):
        return
    if not (
        relative_path.startswith("results/raw-ledgers/v4-")
        and relative_path.endswith(".tree.sha256")
    ):
        raise ValueError(f"credential-like embedded path in public candidate: {relative_path}")
    text = data.decode(encoding="ascii", errors="strict")
    for line in text.splitlines():
        lowered_line = line.casefold().encode(encoding="ascii")
        if not any(
            fragment in lowered_line for fragment in CREDENTIAL_LIKE_PATH_FRAGMENTS
        ):
            continue
        digest, separator, embedded_path = line.partition("  ")
        if (
            separator != "  "
            or digest != EMPTY_FILE_SHA256
            or SAFE_EMPTY_RUNTIME_CREDENTIAL_PATH.fullmatch(string=embedded_path) is None
        ):
            raise ValueError(
                f"credential-like embedded path in public candidate: {relative_path}"
            )


def scan_public_candidates(
    *,
    repository_root: Path,
    paths0: Path,
    output: Path,
    commit: str | None,
) -> PublicCandidateScanReceipt:
    root = require_regular_directory(path=repository_root, label="repository root")
    require_outside_directory(
        path=output,
        directory=root,
        label="public candidate scan receipt",
    )
    paths = read_canonical_paths0(path=paths0)
    resolved_commit: str | None = None
    if commit is not None:
        if re.fullmatch(pattern=r"[0-9a-f]{40}", string=commit) is None:
            raise ValueError("candidate scan commit must be a full lowercase Git object ID")
        resolved_commit = run_git(
            repository_root=root,
            arguments=["rev-parse", "--verify", f"{commit}^{{commit}}"],
        ).decode(encoding="ascii", errors="strict").strip()
        if resolved_commit != commit:
            raise ValueError("candidate scan commit does not resolve to itself")
    aggregate = hashlib.sha256()
    for relative_path in paths:
        data = (
            read_regular_snapshot(
                path=root / relative_path,
                label="working-tree public candidate",
                max_size_bytes=MAX_PUBLIC_CANDIDATE_BYTES,
            ).data
            if resolved_commit is None
            else read_committed_candidate(
                repository_root=root,
                commit=resolved_commit,
                relative_path=relative_path,
            )
        )
        validate_public_candidate(relative_path=relative_path, data=data)
        aggregate.update(relative_path.encode(encoding="utf-8"))
        aggregate.update(b"\0")
        aggregate.update(data)
        aggregate.update(b"\0")
    receipt = PublicCandidateScanReceipt(
        source="working-tree" if resolved_commit is None else "git-commit",
        repository_commit=resolved_commit,
        path_count=len(paths),
        aggregate_sha256=aggregate.hexdigest(),
    )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=receipt), mode=0o400)
    return receipt


def repository_relative_path(*, path: Path, repository_root: Path, label: str) -> str:
    if not path.is_relative_to(repository_root):
        raise ValueError(f"{label} must be within repository root")
    relative = path.relative_to(repository_root)
    value = relative.as_posix()
    require_safe_relative_path(value=value, label=label)
    return value


def require_outside_directory(*, path: Path, directory: Path, label: str) -> None:
    absolute_path_value = absolute_path(path=path)
    absolute_directory = absolute_path(path=directory)
    if absolute_path_value == absolute_directory or absolute_path_value.is_relative_to(
        absolute_directory
    ):
        raise ValueError(f"{label} must be outside {absolute_directory}")


def require_exact_directory_entries(
    *, directory: Path, expected_names: frozenset[str], label: str
) -> None:
    actual_names = frozenset(entry.name for entry in os.scandir(directory))
    if actual_names != expected_names:
        raise ValueError(
            f"{label} entries differ: expected {sorted(expected_names)!r}, "
            f"found {sorted(actual_names)!r}"
        )


def exact_tree(*, root: Path) -> tuple[set[str], set[str]]:
    require_regular_directory(path=root, label="tree root")
    files: set[str] = set()
    directories: set[str] = set()
    for directory, directory_names, file_names in root.walk(
        top_down=True,
        follow_symlinks=False,
    ):
        for name in directory_names:
            candidate = directory / name
            file_stat = os.lstat(candidate)
            if not stat.S_ISDIR(file_stat.st_mode):
                raise ValueError(f"tree contains a non-directory entry: {candidate}")
            directories.add(candidate.relative_to(root).as_posix())
        for name in file_names:
            candidate = directory / name
            file_stat = os.lstat(candidate)
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError(f"tree contains a non-regular file: {candidate}")
            files.add(candidate.relative_to(root).as_posix())
    return files, directories


def require_exact_tree(*, root: Path, expected_files: set[str], label: str) -> None:
    expected_directories = {
        parent.as_posix()
        for relative_path in expected_files
        for parent in PurePosixPath(relative_path).parents
        if parent != PurePosixPath(".")
    }
    actual_files, actual_directories = exact_tree(root=root)
    if actual_files != expected_files or actual_directories != expected_directories:
        raise ValueError(f"{label} file or directory set changed")


def file_commitment(*, snapshot: RegularSnapshot, path: str) -> FileCommitment:
    return FileCommitment(
        path=path,
        size_bytes=snapshot.size_bytes,
        sha256=snapshot.sha256,
    )


def validate_dataset_selection(
    *, datasets: Sequence[DatasetName], allow_empty_selection: bool
) -> list[DatasetName]:
    selected = list(datasets)
    if not selected:
        if allow_empty_selection:
            return []
        raise ValueError(
            "at least one evaluation dataset must be selected unless "
            "--allow-empty-selection is explicit"
        )
    if allow_empty_selection:
        raise ValueError("--allow-empty-selection requires no --dataset arguments")
    if len(selected) != len(set(selected)):
        raise ValueError("evaluation datasets must be unique")
    primary = set(selected) & {"n3", "n5"}
    if len(primary) != 1:
        raise ValueError("a non-empty selection must contain exactly one of n3 or n5")
    ordered = sorted(selected, key=lambda dataset: DATASET_ORDER[dataset])
    return ordered


def freeze_evaluation(
    *,
    repository_root: Path,
    datasets: Sequence[DatasetName],
    evaluation_root: Path,
    execution_environment: Path,
    selection_source: Path,
    output: Path,
    allow_empty_selection: bool = False,
) -> EvaluationFreezeCommitment:
    repository = require_regular_directory(
        path=repository_root,
        label="repository root",
    )
    evaluation = require_regular_directory(
        path=evaluation_root,
        label="fresh evaluation root",
    )
    repository_relative_path(
        path=evaluation,
        repository_root=repository,
        label="evaluation root",
    )
    selected = validate_dataset_selection(
        datasets=datasets,
        allow_empty_selection=allow_empty_selection,
    )
    require_exact_directory_entries(
        directory=evaluation,
        expected_names=frozenset(selected),
        label="evaluation root",
    )
    records: list[FileCommitment] = []
    for dataset in selected:
        dataset_root = require_regular_directory(
            path=evaluation / dataset,
            label=f"{dataset} evaluation directory",
        )
        require_exact_directory_entries(
            directory=dataset_root,
            expected_names=EVALUATION_FILENAMES,
            label=f"{dataset} evaluation directory",
        )
        for filename in sorted(EVALUATION_FILENAMES):
            snapshot = read_regular_snapshot(
                path=dataset_root / filename,
                label=f"{dataset} {filename}",
            )
            relative_path = repository_relative_path(
                path=snapshot.path,
                repository_root=repository,
                label="evaluation file",
            )
            records.append(file_commitment(snapshot=snapshot, path=relative_path))
    source_snapshot = read_regular_snapshot(
        path=selection_source,
        label="selection or eligibility source",
    )
    source_relative_path = repository_relative_path(
        path=source_snapshot.path,
        repository_root=repository,
        label="selection or eligibility source",
    )
    require_outside_directory(
        path=output,
        directory=evaluation,
        label="evaluation commitment output",
    )
    evaluation_relative = repository_relative_path(
        path=evaluation,
        repository_root=repository,
        label="evaluation root",
    )
    environment_snapshot = read_regular_snapshot(
        path=execution_environment,
        label="evaluation execution environment",
    )
    require_canonical_model_snapshot(
        snapshot=environment_snapshot,
        model_type=EvaluationExecutionEnvironment,
        label="evaluation execution environment",
    )
    environment_relative_path = repository_relative_path(
        path=environment_snapshot.path,
        repository_root=repository,
        label="evaluation execution environment",
    )
    commitment = EvaluationFreezeCommitment(
        evaluation_root=evaluation_relative,
        selection_mode=("eligible-datasets" if selected else "no-eligible-primary"),
        datasets=selected,
        execution_environment=file_commitment(
            snapshot=environment_snapshot,
            path=environment_relative_path,
        ),
        selection_source=file_commitment(
            snapshot=source_snapshot,
            path=source_relative_path,
        ),
        files=records,
    )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=commitment))
    return commitment


def capture_evaluation_environment(
    *, repository_root: Path, output: Path
) -> EvaluationExecutionEnvironment:
    repository = require_regular_directory(
        path=repository_root,
        label="evaluation source repository",
    )
    executable = Path(sys.executable).resolve(strict=True)
    executable_snapshot = read_regular_snapshot(
        path=executable,
        label="evaluation Python executable",
    )
    uv_lock = read_regular_snapshot(
        path=repository / "uv.lock",
        label="evaluation uv lock",
    )
    evaluator_manifest = read_regular_snapshot(
        path=repository / "protocol" / "evaluator_manifest.sha256",
        label="evaluator manifest",
    )
    repository_commit = run_git(
        repository_root=repository,
        arguments=["rev-parse", "HEAD"],
    ).decode(encoding="ascii", errors="strict").strip()
    environment = EvaluationExecutionEnvironment(
        repository_commit=repository_commit,
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        python_executable=str(executable),
        python_executable_sha256=executable_snapshot.sha256,
        platform_system=platform.system(),
        platform_release=platform.release(),
        platform_machine=platform.machine(),
        byteorder=cast(Literal["little", "big"], sys.byteorder),
        uv_lock_sha256=uv_lock.sha256,
        evaluator_manifest_sha256=evaluator_manifest.sha256,
    )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=environment))
    return environment


def require_canonical_model_snapshot(
    *, snapshot: RegularSnapshot, model_type: type[BaseModel], label: str
) -> BaseModel:
    model = model_type.model_validate_json(snapshot.data)
    if snapshot.data != canonical_model_bytes(model=model):
        raise ValueError(f"{label} must be canonical LF-terminated JSON")
    return model


def validate_neutral_label(*, value: str) -> None:
    if NEUTRAL_LABEL.fullmatch(string=value) is None:
        raise ValueError(f"unsafe neutral packet label: {value!r}")


def validate_packet_relative_paths(*, files: Sequence[PacketFile]) -> list[str]:
    relative_paths = [file.relative_path for file in files]
    roles = {file.role for file in files}
    if PacketFileRole.TASK_CONTEXT not in roles:
        raise ValueError("packet manifest must contain task context")
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("packet manifest contains duplicate file paths")
    for packet_file in files:
        relative_path = packet_file.relative_path
        require_safe_relative_path(value=relative_path, label="packet file path")
        if relative_path == "packet.json":
            raise ValueError("packet file path collides with packet.json")
        required_prefix = (
            "task-context/"
            if packet_file.role is PacketFileRole.TASK_CONTEXT
            else "submitted-output/"
        )
        if not relative_path.startswith(required_prefix):
            raise ValueError("packet file role does not match its registered path prefix")
    for left in relative_paths:
        for right in relative_paths:
            if left != right and PurePosixPath(right).is_relative_to(PurePosixPath(left)):
                raise ValueError("packet file paths contain a file/directory collision")
    return relative_paths


def validate_packet_manifest(
    *,
    review_bundle: Path,
    bundle_packet: BundlePacket,
    rubric_source_sha256: str,
) -> tuple[PacketManifest, RegularSnapshot, set[str]]:
    validate_neutral_label(value=bundle_packet.neutral_label)
    packet_root = require_regular_directory(
        path=review_bundle / "packets" / bundle_packet.neutral_label,
        label="neutral packet directory",
    )
    manifest_snapshot = read_regular_snapshot(
        path=packet_root / "packet.json",
        label="neutral packet manifest",
    )
    parsed = require_canonical_model_snapshot(
        snapshot=manifest_snapshot,
        model_type=PacketManifest,
        label="neutral packet manifest",
    )
    manifest = cast(PacketManifest, parsed)
    payload = PacketPayload.model_validate(
        manifest.model_dump(mode="python", exclude={"packet_sha256"})
    )
    relative_paths = validate_packet_relative_paths(files=manifest.files)
    if (
        manifest.neutral_label != bundle_packet.neutral_label
        or manifest.task_variant != bundle_packet.task_variant
        or manifest.packet_sha256 != bundle_packet.packet_sha256
        or manifest.rubric_source_sha256 != rubric_source_sha256
        or packet_payload_sha256(payload=payload) != bundle_packet.packet_sha256
    ):
        raise ValueError(
            f"neutral packet provenance mismatch: {bundle_packet.neutral_label!r}"
        )
    expected_files = {"packet.json", *relative_paths}
    require_exact_tree(
        root=packet_root,
        expected_files=expected_files,
        label=f"neutral packet {bundle_packet.neutral_label!r}",
    )
    for packet_file in manifest.files:
        snapshot = read_regular_snapshot(
            path=packet_root / packet_file.relative_path,
            label="neutral packet file",
        )
        if (
            prefixed_sha256_bytes(data=snapshot.data) != packet_file.sha256
            or snapshot.size_bytes != packet_file.size_bytes
        ):
            raise ValueError(
                "neutral packet file bytes differ from packet.json: "
                f"{bundle_packet.neutral_label}/{packet_file.relative_path}"
            )
    return manifest, manifest_snapshot, {
        f"packets/{bundle_packet.neutral_label}/{relative_path}"
        for relative_path in expected_files
    }


def render_completed_review_csv(*, rows: Sequence[CompletedReviewRow]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=list(REVIEW_FIELDNAMES),
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row.model_dump(mode="json"))
    return stream.getvalue().encode(encoding="utf-8")


def validate_completed_review(
    *,
    snapshot: RegularSnapshot,
    bundle: ReviewBundleManifest,
) -> tuple[CompletedReviewRow, ...]:
    if not snapshot.data or b"\r" in snapshot.data or not snapshot.data.endswith(b"\n"):
        raise ValueError("completed review must use non-empty LF-terminated CSV")
    text = snapshot.data.decode(encoding="utf-8", errors="strict")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != REVIEW_FIELDNAMES:
        raise ValueError(
            f"completed review columns must be exactly {list(REVIEW_FIELDNAMES)!r}"
        )
    rows = tuple(CompletedReviewRow.model_validate(row) for row in reader)
    expected_rows = [
        (packet, item)
        for packet in bundle.packets
        for item in RUBRIC_ITEMS
    ]
    if len(rows) != len(expected_rows):
        raise ValueError("completed review must contain exactly eight rows per packet")
    for row, (packet, item) in zip(rows, expected_rows, strict=True):
        if (
            row.neutral_label != packet.neutral_label
            or row.packet_sha256 != packet.packet_sha256
            or row.task_variant != packet.task_variant
            or row.item_id != item.item_id
            or row.criterion != item.criterion
        ):
            raise ValueError("completed review row order or provenance is invalid")
        if row.item_id == "no_unavailable_access":
            if row.status is ReviewStatus.PASS:
                raise ValueError("item 8 cannot pass in an artifact-only review")
            if row.status in {ReviewStatus.PARTIAL, ReviewStatus.FAIL} and not (
                row.rationale.casefold().startswith("submitted artifact evidence:")
            ):
                raise ValueError(
                    "item 8 partial/fail rationale must begin "
                    "'Submitted artifact evidence:'"
                )
        if row.item_id == "artifacts_and_offline_scripts":
            lowered = row.rationale.casefold()
            if row.status is ReviewStatus.NOT_APPLICABLE:
                raise ValueError("item 6 cannot be not_applicable")
            if row.status is ReviewStatus.PASS and not (
                lowered.startswith("no applicable scripts:")
                and "cited artifacts verified:" in lowered
            ):
                raise ValueError(
                    "item 6 pass requires verified cited artifacts and no applicable "
                    "submitted script"
                )
            if row.status in {ReviewStatus.PARTIAL, ReviewStatus.FAIL} and not (
                "not executed" in lowered or "not run" in lowered
            ):
                raise ValueError("item 6 partial/fail must disclose non-execution")
    if snapshot.data != render_completed_review_csv(rows=rows):
        raise ValueError("completed review CSV is not canonical")
    return rows


def validate_neutral_review_bundle(
    *, review_bundle: Path
) -> tuple[
    ReviewBundleManifest,
    RegularSnapshot,
    RegularSnapshot,
    dict[str, tuple[PacketManifest, RegularSnapshot]],
]:
    root = require_regular_directory(path=review_bundle, label="neutral review bundle")
    bundle_snapshot = read_regular_snapshot(
        path=root / "bundle.json",
        label="neutral review bundle manifest",
    )
    parsed = require_canonical_model_snapshot(
        snapshot=bundle_snapshot,
        model_type=ReviewBundleManifest,
        label="neutral review bundle manifest",
    )
    bundle = cast(ReviewBundleManifest, parsed)
    if not bundle.packets:
        raise ValueError("neutral review bundle must contain at least one packet")
    labels = [packet.neutral_label for packet in bundle.packets]
    hashes = [packet.packet_sha256 for packet in bundle.packets]
    if len(labels) != len(set(labels)) or len(hashes) != len(set(hashes)):
        raise ValueError("neutral review bundle packet labels and hashes must be unique")
    packets_root = require_regular_directory(
        path=root / "packets",
        label="neutral packets directory",
    )
    require_exact_directory_entries(
        directory=packets_root,
        expected_names=frozenset(labels),
        label="neutral packets directory",
    )
    expected_root_files: set[str] = {
        "ARTIFACT_REVIEW.md",
        "REVIEW_INSTRUCTIONS.md",
        "bundle.json",
        "review.csv",
    }
    packet_records: dict[str, tuple[PacketManifest, RegularSnapshot]] = {}
    for packet in bundle.packets:
        manifest, manifest_snapshot, packet_files = validate_packet_manifest(
            review_bundle=root,
            bundle_packet=packet,
            rubric_source_sha256=bundle.rubric_source_sha256,
        )
        packet_records[packet.neutral_label] = (manifest, manifest_snapshot)
        expected_root_files.update(packet_files)
    require_exact_tree(
        root=root,
        expected_files=expected_root_files,
        label="neutral review bundle",
    )
    rubric_snapshot = read_regular_snapshot(
        path=root / "ARTIFACT_REVIEW.md",
        label="bundled artifact-review rubric",
    )
    if prefixed_sha256_bytes(data=rubric_snapshot.data) != bundle.rubric_source_sha256:
        raise ValueError("bundled artifact-review rubric differs from bundle.json")
    if bundle.rubric_source_sha256 != FROZEN_RUBRIC_SHA256:
        raise ValueError("neutral review bundle does not use the registered frozen rubric")
    instructions = read_regular_snapshot(
        path=root / "REVIEW_INSTRUCTIONS.md",
        label="bundled review instructions",
    )
    if instructions.data != REVIEW_INSTRUCTIONS.encode(encoding="utf-8"):
        raise ValueError("bundled review instructions differ from registered instructions")
    review_snapshot = read_regular_snapshot(
        path=root / "review.csv",
        label="completed neutral review",
    )
    validate_completed_review(
        snapshot=review_snapshot,
        bundle=bundle,
    )
    return bundle, bundle_snapshot, review_snapshot, packet_records


def read_sealed_mapping_snapshot(*, path: Path) -> RegularSnapshot:
    snapshot = read_regular_snapshot(path=path, label="sealed identity mapping")
    if snapshot.mode != 0o600:
        raise ValueError("sealed identity mapping must have exact mode 0600")
    if snapshot.size_bytes == 0:
        raise ValueError("sealed identity mapping must not be empty")
    return snapshot


def load_editorial_metadata(
    *, path: Path, completed_review_sha256: str
) -> tuple[ArtifactReviewEditorialMetadata, RegularSnapshot]:
    snapshot = read_regular_snapshot(path=path, label="artifact-review editorial metadata")
    parsed = require_canonical_model_snapshot(
        snapshot=snapshot,
        model_type=ArtifactReviewEditorialMetadata,
        label="artifact-review editorial metadata",
    )
    metadata = cast(ArtifactReviewEditorialMetadata, parsed)
    if metadata.completed_review_sha256 != completed_review_sha256:
        raise ValueError("reviewer editorial metadata binds a different completed review")
    return metadata, snapshot


def read_primary_review_snapshot(
    *, path: Path, review_root: Path, bundle: ReviewBundleManifest
) -> tuple[RegularSnapshot, tuple[CompletedReviewRow, ...]]:
    require_outside_directory(
        path=path,
        directory=review_root,
        label="primary review snapshot",
    )
    snapshot = read_regular_snapshot(path=path, label="primary completed review")
    if snapshot.mode != 0o400:
        raise ValueError("primary review snapshot must have exact mode 0400")
    rows = validate_completed_review(snapshot=snapshot, bundle=bundle)
    return snapshot, rows


def calculate_review_difference(
    *, review_bundle: Path, primary_review: Path
) -> ReviewDifferenceReceipt:
    root = require_regular_directory(path=review_bundle, label="neutral review bundle")
    bundle, _, completed_snapshot, _ = validate_neutral_review_bundle(
        review_bundle=root
    )
    primary_snapshot, primary_rows = read_primary_review_snapshot(
        path=primary_review,
        review_root=root,
        bundle=bundle,
    )
    completed_rows = validate_completed_review(
        snapshot=completed_snapshot,
        bundle=bundle,
    )
    return ReviewDifferenceReceipt(
        primary_review_sha256=prefixed_sha256_bytes(data=primary_snapshot.data),
        completed_review_sha256=prefixed_sha256_bytes(data=completed_snapshot.data),
        rows_changed=sum(
            primary_row != completed_row
            for primary_row, completed_row in zip(
                primary_rows,
                completed_rows,
                strict=True,
            )
        ),
    )


def write_review_difference(
    *, review_bundle: Path, primary_review: Path, output: Path
) -> ReviewDifferenceReceipt:
    difference = calculate_review_difference(
        review_bundle=review_bundle,
        primary_review=primary_review,
    )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=difference))
    return difference


def create_review_disclosure(
    *, review_bundle: Path, primary_review: Path, input_path: Path, output: Path
) -> ArtifactReviewEditorialMetadata:
    root = require_regular_directory(path=review_bundle, label="neutral review bundle")
    bundle, _, completed_snapshot, packet_records = validate_neutral_review_bundle(
        review_bundle=root
    )
    primary_snapshot, _ = read_primary_review_snapshot(
        path=primary_review,
        review_root=root,
        bundle=bundle,
    )
    if set(packet_records) != {packet.neutral_label for packet in bundle.packets}:
        raise ValueError("primary review packet set differs from neutral bundle")
    difference = calculate_review_difference(
        review_bundle=root,
        primary_review=primary_review,
    )
    metadata, snapshot = load_editorial_metadata(
        path=input_path,
        completed_review_sha256=prefixed_sha256_bytes(data=completed_snapshot.data),
    )
    if metadata.adjudication.rows_changed != difference.rows_changed:
        raise ValueError("review disclosure changed-row count differs from primary/final review")
    if not metadata.second_review.occurred and primary_snapshot.data != completed_snapshot.data:
        raise ValueError("review changed without an occurred second review")
    if difference.rows_changed > 0 and not metadata.adjudication.occurred:
        raise ValueError("changed review rows require occurred blind adjudication")
    write_atomic_exclusive(path=output, data=snapshot.data)
    return metadata


def snapshot_primary_review(*, review_bundle: Path, output: Path) -> FileCommitment:
    root = require_regular_directory(path=review_bundle, label="neutral review bundle")
    require_outside_directory(
        path=output,
        directory=root,
        label="primary review snapshot",
    )
    _, _, review_snapshot, _ = validate_neutral_review_bundle(review_bundle=root)
    write_atomic_exclusive(path=output, data=review_snapshot.data, mode=0o400)
    written = read_regular_snapshot(path=output, label="primary review snapshot")
    return file_commitment(snapshot=written, path="primary-review.csv")


def freeze_sealed_mapping(
    *, sealed_mapping: Path, output: Path
) -> SealedMappingFreezeCommitment:
    snapshot = read_sealed_mapping_snapshot(path=sealed_mapping)
    commitment = SealedMappingFreezeCommitment(
        mapping=file_commitment(snapshot=snapshot, path="sealed-mapping.json"),
    )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=commitment))
    return commitment


def load_canonical_mapping_commitment(
    *, path: Path
) -> tuple[SealedMappingFreezeCommitment, RegularSnapshot]:
    snapshot = read_regular_snapshot(path=path, label="sealed mapping freeze commitment")
    parsed = require_canonical_model_snapshot(
        snapshot=snapshot,
        model_type=SealedMappingFreezeCommitment,
        label="sealed mapping freeze commitment",
    )
    return cast(SealedMappingFreezeCommitment, parsed), snapshot


def freeze_review(
    *,
    review_bundle: Path,
    primary_review: Path,
    mapping_freeze: Path,
    editorial_metadata: Path,
    output: Path,
) -> ReviewFreezeCommitment:
    root = require_regular_directory(path=review_bundle, label="neutral review bundle")
    require_outside_directory(
        path=output,
        directory=root,
        label="review commitment output",
    )
    bundle, bundle_snapshot, review_snapshot, packet_records = (
        validate_neutral_review_bundle(review_bundle=root)
    )
    mapping_commitment, mapping_commitment_snapshot = (
        load_canonical_mapping_commitment(path=mapping_freeze)
    )
    primary_snapshot, _ = read_primary_review_snapshot(
        path=primary_review,
        review_root=root,
        bundle=bundle,
    )
    _, editorial_snapshot = load_editorial_metadata(
        path=editorial_metadata,
        completed_review_sha256=prefixed_sha256_bytes(data=review_snapshot.data),
    )
    commitment = ReviewFreezeCommitment(
        bundle=file_commitment(snapshot=bundle_snapshot, path="bundle.json"),
        primary_review=file_commitment(
            snapshot=primary_snapshot,
            path="primary-review.csv",
        ),
        review=file_commitment(snapshot=review_snapshot, path="review.csv"),
        ledger_sha256=bundle.ledger_sha256,
        matrix_sha256=bundle.matrix_sha256,
        rubric_source_sha256=bundle.rubric_source_sha256,
        schedule_files=bundle.schedule_files,
        packets=[
            FrozenPacket(
                neutral_label=packet.neutral_label,
                task_variant=packet.task_variant,
                packet_sha256=packet.packet_sha256,
                runner_image_sha256=packet_records[packet.neutral_label][
                    0
                ].runner_image_sha256,
                packet_manifest=file_commitment(
                    snapshot=packet_records[packet.neutral_label][1],
                    path=f"packets/{packet.neutral_label}/packet.json",
                ),
            )
            for packet in bundle.packets
        ],
        editorial_metadata=file_commitment(
            snapshot=editorial_snapshot,
            path="artifact-review-editorial.json",
        ),
        sealed_mapping=mapping_commitment.mapping,
        sealed_mapping_freeze_sha256=mapping_commitment_snapshot.sha256,
    )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=commitment))
    return commitment


def load_canonical_review_commitment(
    *, path: Path
) -> tuple[ReviewFreezeCommitment, RegularSnapshot]:
    snapshot = read_regular_snapshot(path=path, label="review freeze commitment")
    parsed = require_canonical_model_snapshot(
        snapshot=snapshot,
        model_type=ReviewFreezeCommitment,
        label="review freeze commitment",
    )
    return cast(ReviewFreezeCommitment, parsed), snapshot


def verify_public_file_hashes(
    *, public_bundle: Path, provenance: PublicProvenance
) -> dict[str, RegularSnapshot]:
    names = [record.name for record in provenance.public_files]
    if len(names) != len(set(names)) or frozenset(names) != PUBLIC_HASHED_FILENAMES:
        raise ValueError("public provenance must list each hashed public file exactly once")
    snapshots: dict[str, RegularSnapshot] = {}
    for record in provenance.public_files:
        require_safe_relative_path(value=record.name, label="public file name")
        if PurePosixPath(record.name).parent != PurePosixPath("."):
            raise ValueError("public provenance file names must be root-level names")
        snapshot = read_regular_snapshot(
            path=public_bundle / record.name,
            label="public bundle file",
        )
        if prefixed_sha256_bytes(data=snapshot.data) != record.sha256:
            raise ValueError(f"public file hash mismatch: {record.name!r}")
        snapshots[record.name] = snapshot
    return snapshots


def parse_canonical_jsonl(
    *, snapshot: RegularSnapshot, model_type: type[BaseModel], label: str
) -> tuple[BaseModel, ...]:
    if not snapshot.data or b"\r" in snapshot.data or not snapshot.data.endswith(b"\n"):
        raise ValueError(f"{label} must be non-empty LF-terminated JSONL")
    lines = snapshot.data.splitlines()
    models = tuple(model_type.model_validate_json(line) for line in lines)
    rendered = b"".join(canonical_model_bytes(model=model) for model in models)
    if snapshot.data != rendered:
        raise ValueError(f"{label} must be canonical JSONL")
    return models


def expected_public_review_items(
    *,
    rows: Sequence[CompletedReviewRow],
    runs: Sequence[PublicRunMapping],
    completed_review_sha256: str,
) -> tuple[PublicReviewItem, ...]:
    runs_by_label = {run.neutral_label: run for run in runs}
    if len(runs_by_label) != len(runs):
        raise ValueError("public run mappings contain duplicate neutral labels")
    expected: list[PublicReviewItem] = []
    for row in rows:
        run = runs_by_label.get(row.neutral_label)
        if run is None:
            raise ValueError("completed review row has no public run mapping")
        expected.append(
            PublicReviewItem(
                completed_review_sha256=completed_review_sha256,
                run_id=run.run_id,
                system=run.system,
                task_variant=row.task_variant,
                run_status=run.run_status,
                packet_sha256=row.packet_sha256,
                item_id=row.item_id,
                criterion=row.criterion,
                status=row.status,
                rationale=row.rationale,
            )
        )
    return tuple(expected)


def verify_finalized_review(
    *,
    commitment_path: Path,
    mapping_commitment_path: Path,
    sealed_mapping_path: Path,
    primary_review_path: Path,
    editorial_metadata_path: Path,
    review_bundle: Path,
    public_bundle: Path,
    output: Path,
) -> FinalizedReviewVerification:
    commitment, commitment_snapshot = load_canonical_review_commitment(
        path=commitment_path
    )
    mapping_commitment, mapping_commitment_snapshot = (
        load_canonical_mapping_commitment(path=mapping_commitment_path)
    )
    mapping_snapshot = read_sealed_mapping_snapshot(path=sealed_mapping_path)
    if (
        file_commitment(snapshot=mapping_snapshot, path="sealed-mapping.json")
        != mapping_commitment.mapping
        or commitment.sealed_mapping != mapping_commitment.mapping
        or commitment.sealed_mapping_freeze_sha256
        != mapping_commitment_snapshot.sha256
    ):
        raise ValueError("sealed mapping differs from its public pre-review commitment")
    neutral_root = require_regular_directory(
        path=review_bundle,
        label="neutral review bundle",
    )
    bundle, bundle_snapshot, review_snapshot, packet_records = (
        validate_neutral_review_bundle(review_bundle=neutral_root)
    )
    primary_snapshot, _ = read_primary_review_snapshot(
        path=primary_review_path,
        review_root=neutral_root,
        bundle=bundle,
    )
    _, editorial_snapshot = load_editorial_metadata(
        path=editorial_metadata_path,
        completed_review_sha256=prefixed_sha256_bytes(data=review_snapshot.data),
    )
    current_commitment = ReviewFreezeCommitment(
        bundle=file_commitment(snapshot=bundle_snapshot, path="bundle.json"),
        primary_review=file_commitment(
            snapshot=primary_snapshot,
            path="primary-review.csv",
        ),
        review=file_commitment(snapshot=review_snapshot, path="review.csv"),
        ledger_sha256=bundle.ledger_sha256,
        matrix_sha256=bundle.matrix_sha256,
        rubric_source_sha256=bundle.rubric_source_sha256,
        schedule_files=bundle.schedule_files,
        packets=[
            FrozenPacket(
                neutral_label=packet.neutral_label,
                task_variant=packet.task_variant,
                packet_sha256=packet.packet_sha256,
                runner_image_sha256=packet_records[packet.neutral_label][
                    0
                ].runner_image_sha256,
                packet_manifest=file_commitment(
                    snapshot=packet_records[packet.neutral_label][1],
                    path=f"packets/{packet.neutral_label}/packet.json",
                ),
            )
            for packet in bundle.packets
        ],
        editorial_metadata=file_commitment(
            snapshot=editorial_snapshot,
            path="artifact-review-editorial.json",
        ),
        sealed_mapping=mapping_commitment.mapping,
        sealed_mapping_freeze_sha256=mapping_commitment_snapshot.sha256,
    )
    if current_commitment != commitment:
        raise ValueError("neutral review bundle no longer matches its freeze commitment")
    public_root = require_regular_directory(
        path=public_bundle,
        label="finalized public review bundle",
    )
    require_exact_tree(
        root=public_root,
        expected_files=set(PUBLIC_BUNDLE_FILENAMES),
        label="finalized public review bundle",
    )
    provenance_snapshot = read_regular_snapshot(
        path=public_root / "provenance.json",
        label="public review provenance",
    )
    parsed = require_canonical_model_snapshot(
        snapshot=provenance_snapshot,
        model_type=PublicProvenance,
        label="public review provenance",
    )
    provenance = cast(PublicProvenance, parsed)
    public_snapshots = verify_public_file_hashes(
        public_bundle=public_root,
        provenance=provenance,
    )
    completed = public_snapshots["completed-review.csv"]
    if completed.data != review_snapshot.data:
        raise ValueError("public completed-review.csv is not byte-identical to committed review")
    expected_review_sha256 = f"sha256:{commitment.review.sha256}"
    if provenance.completed_review_sha256 != expected_review_sha256:
        raise ValueError("public provenance does not bind the committed review hash")
    if provenance.sealed_mapping_sha256 != prefixed_sha256_bytes(
        data=mapping_snapshot.data
    ):
        raise ValueError("public provenance does not bind the precommitted sealed mapping")
    if (
        prefixed_sha256_bytes(data=public_snapshots["ARTIFACT_REVIEW.md"].data)
        != commitment.rubric_source_sha256
        or public_snapshots["REVIEW_INSTRUCTIONS.md"].data
        != REVIEW_INSTRUCTIONS.encode(encoding="utf-8")
    ):
        raise ValueError("public rubric or review instructions differ from neutral bundle")
    if (
        provenance.ledger_sha256 != commitment.ledger_sha256
        or provenance.matrix_sha256 != commitment.matrix_sha256
        or provenance.rubric_source_sha256 != commitment.rubric_source_sha256
        or provenance.schedule_files != commitment.schedule_files
    ):
        raise ValueError("public provenance differs from committed neutral bundle sources")
    parsed_mappings = parse_canonical_jsonl(
        snapshot=public_snapshots["label-mapping.jsonl"],
        model_type=PublicRunMapping,
        label="public label mapping",
    )
    public_runs = tuple(cast(PublicRunMapping, model) for model in parsed_mappings)
    if list(public_runs) != provenance.runs or list(public_runs) != sorted(
        public_runs,
        key=lambda run: run.run_id,
    ):
        raise ValueError(
            "public label-mapping.jsonl does not equal the deterministic provenance runs"
        )
    completed_rows = validate_completed_review(
        snapshot=review_snapshot,
        bundle=bundle,
    )
    parsed_items = parse_canonical_jsonl(
        snapshot=public_snapshots["item-review.jsonl"],
        model_type=PublicReviewItem,
        label="public item review",
    )
    public_items = tuple(cast(PublicReviewItem, model) for model in parsed_items)
    expected_items = expected_public_review_items(
        rows=completed_rows,
        runs=public_runs,
        completed_review_sha256=expected_review_sha256,
    )
    if public_items != expected_items:
        raise ValueError(
            "public item-review.jsonl does not derive exactly from the committed review"
        )
    run_keys = [
        (run.neutral_label, run.packet_sha256, run.task_variant)
        for run in provenance.runs
    ]
    expected_run_keys = [
        (packet.neutral_label, packet.packet_sha256, packet.task_variant)
        for packet in commitment.packets
    ]
    unique_run_fields = all(
        len(values) == len(set(values))
        for values in (
            [run.neutral_label for run in provenance.runs],
            [run.packet_sha256 for run in provenance.runs],
            [run.run_id for run in provenance.runs],
        )
    )
    if (
        not unique_run_fields
        or len(run_keys) != len(set(run_keys))
        or set(run_keys) != set(expected_run_keys)
    ):
        raise ValueError("public provenance run set differs from committed neutral packets")
    verification = FinalizedReviewVerification(
        review_commitment_sha256=commitment_snapshot.sha256,
        completed_review_sha256=commitment.review.sha256,
        completed_review_size_bytes=commitment.review.size_bytes,
        provenance_sha256=provenance_snapshot.sha256,
        editorial_metadata_sha256=editorial_snapshot.sha256,
        sealed_mapping_freeze_sha256=mapping_commitment_snapshot.sha256,
        sealed_mapping_sha256=mapping_snapshot.sha256,
        packet_count=len(commitment.packets),
    )
    for protected in (neutral_root, public_root):
        require_outside_directory(
            path=output,
            directory=protected,
            label="finalized-review verification output",
        )
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=verification))
    return verification


def load_gate_key(*, path: Path, label: str) -> bytes:
    snapshot = read_regular_snapshot(path=path, label=label)
    if snapshot.mode & 0o077:
        raise ValueError(f"{label} must not be accessible to group or other")
    if snapshot.size_bytes != 32:
        raise ValueError(f"{label} must contain exactly 32 bytes")
    return snapshot.data


def run_git(*, repository_root: Path, arguments: Sequence[str]) -> bytes:
    result = subprocess.run(
        args=["git", "-C", str(repository_root), *arguments],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(encoding="utf-8", errors="replace").strip()
        raise ValueError(
            f"Git plumbing failed for {list(arguments)!r}: exit "
            f"{result.returncode}; stderr={stderr!r}"
        )
    if result.stderr:
        raise ValueError("Git plumbing unexpectedly wrote to standard error")
    return result.stdout


def require_head_committed_file(
    *, repository_root: Path, relative_path: str, working_bytes: bytes
) -> None:
    git_entry = repository_root / ".git"
    git_stat = os.lstat(git_entry)
    if stat.S_ISLNK(git_stat.st_mode) or not (
        stat.S_ISDIR(git_stat.st_mode) or stat.S_ISREG(git_stat.st_mode)
    ):
        raise ValueError("repository .git entry must be a regular file or directory")
    top_level = run_git(
        repository_root=repository_root,
        arguments=["rev-parse", "--show-toplevel"],
    ).decode(encoding="utf-8", errors="strict").strip()
    if Path(top_level).resolve(strict=True) != repository_root.resolve(strict=True):
        raise ValueError("repository root must be the Git worktree top level")
    tree_record = run_git(
        repository_root=repository_root,
        arguments=["ls-tree", "-z", "HEAD", "--", relative_path],
    )
    suffix = f"\t{relative_path}\0".encode(encoding="utf-8")
    if not tree_record.endswith(suffix) or tree_record.count(b"\0") != 1:
        raise ValueError(f"gate attestation is not tracked at HEAD: {relative_path!r}")
    header = tree_record[: -len(suffix)].decode(encoding="ascii", errors="strict")
    fields = header.split()
    if len(fields) != 3 or fields[0] != "100644" or fields[1] != "blob":
        raise ValueError(
            f"gate attestation must be a mode-100644 blob at HEAD: {relative_path!r}"
        )
    committed_bytes = run_git(
        repository_root=repository_root,
        arguments=["show", f"HEAD:{relative_path}"],
    )
    if working_bytes != committed_bytes:
        raise ValueError(
            f"gate attestation working bytes differ from HEAD: {relative_path!r}"
        )


def require_head_path_absent(*, repository_root: Path, relative_path: str) -> None:
    tree_record = run_git(
        repository_root=repository_root,
        arguments=["ls-tree", "-z", "HEAD", "--", relative_path],
    )
    if tree_record:
        raise ValueError(
            f"gate attestation must be absent from HEAD for core-only disclosure: "
            f"{relative_path!r}"
        )


def load_committed_attestation(
    *,
    repository_root: Path,
    relative_path: str,
    expected_datasets: frozenset[str],
    expected_closed_stages: list[str],
    key: bytes,
) -> GateAttestation:
    relative = require_safe_relative_path(
        value=relative_path,
        label="gate attestation path",
    )
    snapshot = read_regular_snapshot(
        path=repository_root.joinpath(*relative.parts),
        label="committed gate attestation",
    )
    require_head_committed_file(
        repository_root=repository_root,
        relative_path=relative_path,
        working_bytes=snapshot.data,
    )
    attestation = GateAttestation.model_validate_json(snapshot.data)
    expected_bytes = f"{gate_json(model=attestation)}\n".encode(encoding="utf-8")
    if snapshot.data != expected_bytes:
        raise ValueError(f"gate attestation is not canonical: {relative_path!r}")
    if str(attestation.dataset) not in expected_datasets:
        raise ValueError(f"gate attestation has unexpected dataset: {relative_path!r}")
    if attestation.closed_stages != expected_closed_stages:
        raise ValueError(
            f"gate attestation has unexpected closed-stage prefix: {relative_path!r}"
        )
    if sha256_bytes(data=key) != attestation.commitment_key_sha256:
        raise ValueError(f"gate key does not match attestation: {relative_path!r}")
    return attestation


def create_gate_disclosure(
    *,
    repository_root: Path,
    core_key_path: Path,
    extension_key_path: Path | None,
    core_only: bool,
    output: Path,
) -> GateKeyDisclosure:
    repository = require_regular_directory(
        path=repository_root,
        label="repository root",
    )
    core_key = load_gate_key(path=core_key_path, label="core gate key")
    load_committed_attestation(
        repository_root=repository,
        relative_path=CORE_ATTESTATION_PATH,
        expected_datasets=frozenset({"n3"}),
        expected_closed_stages=["core-n3"],
        key=core_key,
    )
    disclosed_gates = [
        DisclosedGateKey(
            attestation_path=CORE_ATTESTATION_PATH,
            commitment_key_hex=core_key.hex(),
        )
    ]
    extension_attestation = repository.joinpath(
        *PurePosixPath(EXTENSION_ATTESTATION_PATH).parts
    )
    extension_exists = path_exists_including_symlink(path=extension_attestation)
    if core_only and extension_exists:
        raise ValueError(
            "--core-only requires the extension attestation path to be absent"
        )
    if core_only:
        require_head_path_absent(
            repository_root=repository,
            relative_path=EXTENSION_ATTESTATION_PATH,
        )
    if core_only and extension_key_path is not None:
        raise ValueError("--core-only cannot be combined with an extension gate key")
    if not core_only and extension_key_path is None:
        raise ValueError(
            "extension gate key is required unless --core-only is explicit"
        )
    if not core_only and not extension_exists:
        raise ValueError(
            "extension gate attestation is required unless --core-only is explicit"
        )
    if extension_key_path is not None:
        extension_key = load_gate_key(
            path=extension_key_path,
            label="extension gate key",
        )
        if core_key == extension_key or sha256_bytes(data=core_key) == sha256_bytes(
            data=extension_key
        ):
            raise ValueError("core and extension gates must use distinct keys")
        load_committed_attestation(
            repository_root=repository,
            relative_path=EXTENSION_ATTESTATION_PATH,
            expected_datasets=frozenset({"n3", "n5"}),
            expected_closed_stages=["core-n3", "core-extend-n5"],
            key=extension_key,
        )
        disclosed_gates.append(
            DisclosedGateKey(
                attestation_path=EXTENSION_ATTESTATION_PATH,
                commitment_key_hex=extension_key.hex(),
            )
        )
    disclosure = GateKeyDisclosure(gates=disclosed_gates)
    write_atomic_exclusive(path=output, data=canonical_model_bytes(model=disclosure))
    return disclosure


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m operations.v4_finalization",
        description="Create content-blind V4 finalization commitments and continuity proofs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluation = subparsers.add_parser("freeze-evaluation")
    evaluation.add_argument("--repository-root", type=Path, required=True)
    evaluation.add_argument(
        "--dataset",
        dest="datasets",
        action="append",
        choices=tuple(DATASET_ORDER),
        default=[],
    )
    evaluation.add_argument("--allow-empty-selection", action="store_true")
    evaluation.add_argument("--evaluation-root", type=Path, required=True)
    evaluation.add_argument("--execution-environment", type=Path, required=True)
    evaluation.add_argument("--selection-source", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)

    environment = subparsers.add_parser("capture-evaluation-environment")
    environment.add_argument("--repository-root", type=Path, required=True)
    environment.add_argument("--output", type=Path, required=True)

    review = subparsers.add_parser("freeze-review")
    review.add_argument("--review-bundle", type=Path, required=True)
    review.add_argument("--primary-review", type=Path, required=True)
    review.add_argument("--mapping-freeze", type=Path, required=True)
    review.add_argument("--editorial-metadata", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)

    mapping = subparsers.add_parser("freeze-mapping")
    mapping.add_argument("--sealed-mapping", type=Path, required=True)
    mapping.add_argument("--output", type=Path, required=True)

    review_disclosure = subparsers.add_parser("create-review-disclosure")
    review_disclosure.add_argument("--review-bundle", type=Path, required=True)
    review_disclosure.add_argument("--primary-review", type=Path, required=True)
    review_disclosure.add_argument("--input", type=Path, required=True)
    review_disclosure.add_argument("--output", type=Path, required=True)

    primary_snapshot = subparsers.add_parser("snapshot-primary-review")
    primary_snapshot.add_argument("--review-bundle", type=Path, required=True)
    primary_snapshot.add_argument("--output", type=Path, required=True)

    review_difference = subparsers.add_parser("compare-reviews")
    review_difference.add_argument("--review-bundle", type=Path, required=True)
    review_difference.add_argument("--primary-review", type=Path, required=True)
    review_difference.add_argument("--output", type=Path, required=True)

    candidate_scan = subparsers.add_parser("scan-public-candidates")
    candidate_scan.add_argument("--repository-root", type=Path, required=True)
    candidate_scan.add_argument("--paths0", type=Path, required=True)
    candidate_scan.add_argument("--commit")
    candidate_scan.add_argument("--output", type=Path, required=True)

    finalized = subparsers.add_parser("verify-finalized-review")
    finalized.add_argument("--review-freeze", type=Path, required=True)
    finalized.add_argument("--mapping-freeze", type=Path, required=True)
    finalized.add_argument("--sealed-mapping", type=Path, required=True)
    finalized.add_argument("--primary-review", type=Path, required=True)
    finalized.add_argument("--editorial-metadata", type=Path, required=True)
    finalized.add_argument("--review-bundle", type=Path, required=True)
    finalized.add_argument("--public-bundle", type=Path, required=True)
    finalized.add_argument("--output", type=Path, required=True)

    disclosure = subparsers.add_parser("create-gate-disclosure")
    disclosure.add_argument("--repository-root", type=Path, required=True)
    disclosure.add_argument("--core-key", type=Path, required=True)
    disclosure_mode = disclosure.add_mutually_exclusive_group(required=True)
    disclosure_mode.add_argument("--extension-key", type=Path)
    disclosure_mode.add_argument("--core-only", action="store_true")
    disclosure.add_argument("--output", type=Path, required=True)
    return parser


def print_receipt(*, output: Path, kind: str, record_count: int) -> None:
    snapshot = read_regular_snapshot(path=output, label="created guardrail output")
    print(
        canonical_json(
            value={
                "kind": kind,
                "output": str(absolute_path(path=output)),
                "record_count": record_count,
                "sha256": snapshot.sha256,
            }
        )
    )


def main(*, arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(args=arguments)
    if parsed.command == "freeze-evaluation":
        commitment = freeze_evaluation(
            repository_root=parsed.repository_root,
            datasets=parsed.datasets,
            evaluation_root=parsed.evaluation_root,
            execution_environment=parsed.execution_environment,
            selection_source=parsed.selection_source,
            output=parsed.output,
            allow_empty_selection=parsed.allow_empty_selection,
        )
        print_receipt(
            output=parsed.output,
            kind=commitment.kind,
            record_count=len(commitment.files),
        )
        return 0
    if parsed.command == "capture-evaluation-environment":
        environment = capture_evaluation_environment(
            repository_root=parsed.repository_root,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind=environment.kind,
            record_count=1,
        )
        return 0
    if parsed.command == "freeze-review":
        commitment = freeze_review(
            review_bundle=parsed.review_bundle,
            primary_review=parsed.primary_review,
            mapping_freeze=parsed.mapping_freeze,
            editorial_metadata=parsed.editorial_metadata,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind=commitment.kind,
            record_count=len(commitment.packets),
        )
        return 0
    if parsed.command == "create-review-disclosure":
        metadata = create_review_disclosure(
            review_bundle=parsed.review_bundle,
            primary_review=parsed.primary_review,
            input_path=parsed.input,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind="v4-reviewer-disclosure",
            record_count=(
                1
                + int(metadata.second_review.occurred)
                + int(metadata.adjudication.occurred)
            ),
        )
        return 0
    if parsed.command == "snapshot-primary-review":
        snapshot_primary_review(
            review_bundle=parsed.review_bundle,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind="v4-primary-review-snapshot",
            record_count=1,
        )
        return 0
    if parsed.command == "compare-reviews":
        difference = write_review_difference(
            review_bundle=parsed.review_bundle,
            primary_review=parsed.primary_review,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind=difference.kind,
            record_count=difference.rows_changed,
        )
        return 0
    if parsed.command == "scan-public-candidates":
        receipt = scan_public_candidates(
            repository_root=parsed.repository_root,
            paths0=parsed.paths0,
            output=parsed.output,
            commit=parsed.commit,
        )
        print_receipt(
            output=parsed.output,
            kind=receipt.kind,
            record_count=receipt.path_count,
        )
        return 0
    if parsed.command == "freeze-mapping":
        commitment = freeze_sealed_mapping(
            sealed_mapping=parsed.sealed_mapping,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind=commitment.kind,
            record_count=1,
        )
        return 0
    if parsed.command == "verify-finalized-review":
        verification = verify_finalized_review(
            commitment_path=parsed.review_freeze,
            mapping_commitment_path=parsed.mapping_freeze,
            sealed_mapping_path=parsed.sealed_mapping,
            primary_review_path=parsed.primary_review,
            editorial_metadata_path=parsed.editorial_metadata,
            review_bundle=parsed.review_bundle,
            public_bundle=parsed.public_bundle,
            output=parsed.output,
        )
        print_receipt(
            output=parsed.output,
            kind=verification.kind,
            record_count=verification.packet_count,
        )
        return 0
    disclosure = create_gate_disclosure(
        repository_root=parsed.repository_root,
        core_key_path=parsed.core_key,
        extension_key_path=parsed.extension_key,
        core_only=parsed.core_only,
        output=parsed.output,
    )
    print_receipt(
        output=parsed.output,
        kind="v4-gate-key-disclosure",
        record_count=len(disclosure.gates),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
