#!/usr/bin/env python3
"""Emit the deterministic host/runtime manifest used as the runner-image digest."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


RUNNER_ROOT = Path("/root/bench-v2/runner")
CODEX_NATIVE = Path(
    "/usr/lib/node_modules/@openai/codex/node_modules/@openai/"
    "codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex"
)
BWRAP = Path(
    "/usr/lib/node_modules/@openai/codex/node_modules/@openai/"
    "codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-resources/bwrap"
)
NORMALIZER_VENV = RUNNER_ROOT / ".venv"
NORMALIZER_PYTHON = NORMALIZER_VENV / "bin/python"
EXCLUDED_SOURCE_DIRECTORIES = frozenset({".pytest_cache", ".venv", "__pycache__"})
EXCLUDED_SOURCE_FILES = frozenset({"manifest.sha256"})


def sha256_bytes(*, value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(*, path: Path) -> str:
    digest = hashlib.sha256()
    with path.open(mode="rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def executable_path(*, name: str) -> Path:
    resolved = shutil.which(name)
    if resolved is None:
        raise ValueError(f"required executable is absent: {name}")
    return Path(resolved).resolve()


def command_output(*, arguments: list[str]) -> str:
    result = subprocess.run(
        args=arguments,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def installed_distribution_digest() -> str:
    records = sorted(
        f"{distribution.metadata['Name']}=={distribution.version}"
        for distribution in importlib.metadata.distributions()
    )
    return sha256_bytes(value=("\n".join(records) + "\n").encode(encoding="utf-8"))


def debian_package_digest() -> str:
    output = command_output(
        arguments=["dpkg-query", "--show", "--showformat=${Package}\t${Version}\n"]
    )
    records = sorted(output.splitlines())
    return sha256_bytes(value=("\n".join(records) + "\n").encode(encoding="utf-8"))


def module_version(*, distribution_name: str) -> str:
    return importlib.metadata.version(distribution_name)


def runner_source_paths(*, root: Path) -> tuple[str, ...]:
    paths: list[str] = []
    for directory, directory_names, file_names in root.walk():
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in EXCLUDED_SOURCE_DIRECTORIES
        )
        for file_name in sorted(file_names):
            if file_name in EXCLUDED_SOURCE_FILES or file_name.endswith(".pyc"):
                continue
            path = directory / file_name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"runner source must be a regular file: {path}")
            paths.append(f"./{path.relative_to(root).as_posix()}")
    return tuple(sorted(paths))


def manifest_record_paths(*, path: Path) -> tuple[str, ...]:
    records: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, separator, relative_path = line.partition("  ")
        if (
            separator != "  "
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not relative_path.startswith("./")
        ):
            raise ValueError(f"malformed runner manifest record: {line!r}")
        records.append(relative_path)
    if len(records) != len(set(records)):
        raise ValueError("runner manifest contains duplicate paths")
    if records != sorted(records):
        raise ValueError("runner manifest paths are not sorted")
    return tuple(records)


def verify_runner_manifest(*, path: Path, runner_root: Path = RUNNER_ROOT) -> None:
    recorded_paths = manifest_record_paths(path=path)
    actual_paths = runner_source_paths(root=runner_root)
    if recorded_paths != actual_paths:
        missing = sorted(set(actual_paths) - set(recorded_paths))
        extra = sorted(set(recorded_paths) - set(actual_paths))
        raise ValueError(
            f"runner manifest file-set mismatch; unrecorded={missing!r}, absent={extra!r}"
        )
    subprocess.run(
        args=["sha256sum", "--check", "--quiet", str(path)],
        cwd=runner_root,
        check=True,
    )


def tree_sha256(*, root: Path) -> str:
    if not root.is_dir():
        raise ValueError(f"tree root is absent: {root}")
    digest = hashlib.sha256()
    paths = sorted(
        path
        for path in root.rglob(pattern="*")
        if "__pycache__" not in path.relative_to(root).parts
        and not path.name.endswith(".pyc")
        and (path.is_symlink() or path.is_file())
    )
    for path in paths:
        relative_path = path.relative_to(root).as_posix().encode(encoding="utf-8")
        if path.is_symlink():
            target = os.readlink(path).encode(encoding="utf-8")
            digest.update(b"L\0" + relative_path + b"\0" + target + b"\0")
        else:
            file_digest = bytes.fromhex(sha256_file(path=path))
            digest.update(b"F\0" + relative_path + b"\0" + file_digest)
    return digest.hexdigest()


def main() -> None:
    codex = executable_path(name="codex")
    claude = executable_path(name="claude")
    python = Path(sys.executable).resolve()
    if not NORMALIZER_PYTHON.exists():
        raise ValueError(f"normalizer interpreter is absent: {NORMALIZER_PYTHON}")
    normalizer_python = NORMALIZER_PYTHON
    normalizer_executable = normalizer_python.resolve(strict=True)
    runner_manifest = Path("/root/bench-v2/runner.sha256")
    verify_runner_manifest(path=runner_manifest)
    manifest = {
        "schema_version": "1.0",
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "os_release_sha256": sha256_file(path=Path("/etc/os-release")),
        "debian_package_manifest_sha256": debian_package_digest(),
        "python": {
            "version": platform.python_version(),
            "executable_sha256": sha256_file(path=python),
            "distribution_manifest_sha256": installed_distribution_digest(),
            "numpy": module_version(distribution_name="numpy"),
            "scipy": module_version(distribution_name="scipy"),
            "matplotlib": module_version(distribution_name="matplotlib"),
        },
        "normalizer": {
            "python_version": command_output(
                arguments=[
                    str(normalizer_python),
                    "-c",
                    "import platform; print(platform.python_version())",
                ]
            ),
            "python_executable_sha256": sha256_file(path=normalizer_executable),
            "pydantic": command_output(
                arguments=[
                    str(normalizer_python),
                    "-c",
                    "import importlib.metadata; print(importlib.metadata.version('pydantic'))",
                ]
            ),
            "venv_tree_sha256": tree_sha256(root=NORMALIZER_VENV),
        },
        "codex": {
            "version": command_output(arguments=["codex", "--version"]),
            "launcher_sha256": sha256_file(path=codex),
            "native_sha256": sha256_file(path=CODEX_NATIVE),
        },
        "claude": {
            "version": command_output(arguments=["claude", "--version"]),
            "executable_sha256": sha256_file(path=claude),
        },
        "sandbox": {
            "bubblewrap_sha256": sha256_file(path=BWRAP),
            "codex_allowlist_sha256": sha256_file(
                path=RUNNER_ROOT / "allowlist-codex.txt"
            ),
            "claude_allowlist_sha256": sha256_file(
                path=RUNNER_ROOT / "allowlist-claude.txt"
            ),
            "claude_settings_sha256": sha256_file(
                path=RUNNER_ROOT / "claude-settings.json"
            ),
        },
        "runner_manifest_sha256": sha256_file(path=runner_manifest),
    }
    print(
        json.dumps(
            manifest,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
