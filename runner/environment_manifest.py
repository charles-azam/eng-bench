#!/usr/bin/env python3
"""Emit the deterministic host/runtime manifest used as the runner-image digest."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
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


def verify_runner_manifest(*, path: Path) -> None:
    subprocess.run(
        args=["sha256sum", "--check", "--quiet", str(path)],
        cwd=RUNNER_ROOT,
        check=True,
    )


def main() -> None:
    codex = executable_path(name="codex")
    claude = executable_path(name="claude")
    python = Path(sys.executable).resolve()
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
            "allowlist_sha256": sha256_file(path=RUNNER_ROOT / "allowlist.txt"),
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
