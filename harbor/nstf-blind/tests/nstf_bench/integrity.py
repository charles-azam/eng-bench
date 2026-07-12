from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath

from nstf_bench.models import Sha256


EVALUATOR_ROOT_FILES: tuple[str, ...] = (
    "expected_output/held_out.jsonl",
    "pyproject.toml",
    "uv.lock",
)
EVALUATOR_SOURCE_DIRECTORIES: tuple[str, ...] = (
    "src/nstf_bench",
    "tests",
)
EXCLUDED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".pytest_cache",
        "__pycache__",
    }
)
EXCLUDED_FILE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})
MANIFEST_LINE = re.compile(pattern=r"^(?P<digest>[0-9a-f]{64})  (?P<path>[^\r\n]+)$")


def sha256_bytes(*, value: bytes) -> Sha256:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_file(*, path: Path) -> Sha256:
    digest = hashlib.sha256()
    with path.open(mode="rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def is_evaluator_source_file(*, relative_path: PurePosixPath) -> bool:
    return (
        not EXCLUDED_DIRECTORY_NAMES.intersection(relative_path.parts)
        and relative_path.suffix not in EXCLUDED_FILE_SUFFIXES
    )


def evaluator_source_paths(*, root: Path) -> tuple[str, ...]:
    paths: list[str] = []
    for relative_path in EVALUATOR_ROOT_FILES:
        source_path = root / relative_path
        if not source_path.is_file() or source_path.is_symlink():
            raise ValueError(f"evaluator source must be a regular file: {relative_path!r}")
        paths.append(relative_path)

    for relative_directory in EVALUATOR_SOURCE_DIRECTORIES:
        source_directory = root / relative_directory
        if not source_directory.is_dir() or source_directory.is_symlink():
            raise ValueError(
                f"evaluator source directory must be a regular directory: "
                f"{relative_directory!r}"
            )
        for source_path in source_directory.rglob(pattern="*"):
            relative_path = PurePosixPath(source_path.relative_to(root).as_posix())
            if not is_evaluator_source_file(relative_path=relative_path):
                continue
            if source_path.is_symlink():
                raise ValueError(f"evaluator source must not be a symlink: {relative_path!s}")
            if source_path.is_file():
                paths.append(relative_path.as_posix())

    if len(paths) != len(set(paths)):
        raise ValueError("evaluator source discovery produced duplicate paths")
    return tuple(sorted(paths))


def render_evaluator_manifest(*, root: Path) -> str:
    lines = (
        f"{sha256_file(path=root / relative_path).removeprefix('sha256:')}  "
        f"{relative_path}\n"
        for relative_path in evaluator_source_paths(root=root)
    )
    return "".join(lines)


def evaluator_manifest_sha256(*, manifest_path: Path) -> Sha256:
    return sha256_file(path=manifest_path)


def parse_evaluator_manifest(*, manifest_text: str) -> dict[str, Sha256]:
    if not manifest_text or not manifest_text.endswith("\n"):
        raise ValueError("evaluator manifest must be non-empty and newline-terminated")

    entries: dict[str, Sha256] = {}
    for line_number, line in enumerate(manifest_text.splitlines(), start=1):
        match = MANIFEST_LINE.fullmatch(string=line)
        if match is None:
            raise ValueError(f"invalid evaluator manifest line {line_number}")
        relative_path = match.group("path")
        path = PurePosixPath(relative_path)
        if (
            path.is_absolute()
            or relative_path != path.as_posix()
            or ".." in path.parts
            or "\\" in relative_path
        ):
            raise ValueError(
                f"evaluator manifest path must be normalized and relative: "
                f"{relative_path!r}"
            )
        if relative_path in entries:
            raise ValueError(f"duplicate evaluator manifest path: {relative_path!r}")
        entries[relative_path] = f"sha256:{match.group('digest')}"
    return entries


def validate_evaluator_manifest(
    *,
    root: Path,
    manifest_path: Path,
    expected_manifest_sha256: Sha256,
) -> None:
    actual_manifest_sha256 = evaluator_manifest_sha256(manifest_path=manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise ValueError(
            "evaluator manifest does not match frozen ledger: "
            f"expected {expected_manifest_sha256}, got {actual_manifest_sha256}"
        )

    manifest_text = manifest_path.read_text(encoding="utf-8")
    entries = parse_evaluator_manifest(manifest_text=manifest_text)
    expected_paths = evaluator_source_paths(root=root)
    if tuple(entries) != expected_paths:
        missing_paths = sorted(set(expected_paths) - entries.keys())
        unexpected_paths = sorted(entries.keys() - set(expected_paths))
        raise ValueError(
            "evaluator manifest path coverage or ordering mismatch: "
            f"missing={missing_paths!r}, unexpected={unexpected_paths!r}"
        )

    mismatched_paths = [
        relative_path
        for relative_path, expected_sha256 in entries.items()
        if sha256_file(path=root / relative_path) != expected_sha256
    ]
    if mismatched_paths:
        raise ValueError(
            f"evaluator source hash mismatch: {sorted(mismatched_paths)!r}"
        )
