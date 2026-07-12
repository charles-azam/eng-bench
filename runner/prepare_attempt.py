#!/usr/bin/env python3
"""Publish a fresh attempt directory only after environment verification."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DATA_ERROR_EXIT_CODE = 65
EXISTING_ATTEMPT_EXIT_CODE = 73


def files_are_identical(*, first_path: Path, second_path: Path) -> bool:
    with first_path.open(mode="rb") as first_stream, second_path.open(
        mode="rb"
    ) as second_stream:
        while True:
            first_block = first_stream.read(1024 * 1024)
            second_block = second_stream.read(1024 * 1024)
            if first_block != second_block:
                return False
            if not first_block:
                return True


def prepare_attempt(
    *,
    run_directory: Path,
    frozen_environment_path: Path,
    observed_environment_path: Path,
) -> int:
    if run_directory.exists() or run_directory.is_symlink():
        print(f"run already exists: {run_directory.name}", file=sys.stderr)
        return EXISTING_ATTEMPT_EXIT_CODE
    if (
        not frozen_environment_path.is_file()
        or frozen_environment_path.is_symlink()
    ):
        print("frozen environment manifest must be a regular file", file=sys.stderr)
        return DATA_ERROR_EXIT_CODE
    if (
        not observed_environment_path.is_file()
        or observed_environment_path.is_symlink()
    ):
        print("observed environment manifest must be a regular file", file=sys.stderr)
        return DATA_ERROR_EXIT_CODE
    if not files_are_identical(
        first_path=frozen_environment_path,
        second_path=observed_environment_path,
    ):
        print("runtime environment differs from frozen manifest", file=sys.stderr)
        return DATA_ERROR_EXIT_CODE

    run_directory.mkdir(mode=0o700)
    input_directory = run_directory / "input"
    workspace_directory = run_directory / "workspace"
    runtime_directory = run_directory / "runtime"
    input_directory.mkdir(mode=0o700)
    workspace_directory.mkdir(mode=0o700)
    runtime_directory.mkdir(mode=0o700)
    observed_environment_path.replace(runtime_directory / "environment.json")
    return 0


def parse_arguments() -> tuple[Path, Path, Path]:
    parser = argparse.ArgumentParser(
        description=(
            "Create an attempt directory only if the observed and frozen "
            "environment manifests are byte-identical."
        )
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--frozen-environment", required=True, type=Path)
    parser.add_argument("--observed-environment", required=True, type=Path)
    arguments = parser.parse_args()
    return (
        Path(arguments.run_dir),
        Path(arguments.frozen_environment),
        Path(arguments.observed_environment),
    )


def main() -> int:
    run_directory, frozen_environment_path, observed_environment_path = (
        parse_arguments()
    )
    return prepare_attempt(
        run_directory=run_directory,
        frozen_environment_path=frozen_environment_path,
        observed_environment_path=observed_environment_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
