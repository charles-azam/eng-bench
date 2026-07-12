from __future__ import annotations

import io
import json
import shutil
import stat
import sys
import tarfile
from pathlib import Path

import pytest

from operations.v4_stage_archive import (
    ARTIFACT_PATHS,
    STAGE_DEFINITIONS,
    create_stage_archive,
    import_stage_archive,
    parse_retention_state,
    parse_systemctl_state,
    rename_directory_exclusive,
    sha256_file,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLANNER_SCRIPT = REPOSITORY_ROOT / "runner" / "resume_schedule.py"
SYNTHETIC_STAGE = STAGE_DEFINITIONS["nstf-duty-ablation-n3"]


def synthetic_schedule_rows() -> tuple[tuple[str, str, int], ...]:
    return (
        ("nstf_supplied_duty", "codex", 1),
        ("nstf_supplied_duty", "claude", 1),
        ("nstf_supplied_duty", "codex", 2),
        ("nstf_supplied_duty", "claude", 2),
        ("nstf_supplied_duty", "codex", 3),
        ("nstf_supplied_duty", "claude", 3),
    )


def write_schedule(*, path: Path, checksum_path: Path, portable: bool) -> None:
    lines = ["sequence\ttask\tsystem\treplicate\tstage\n"]
    for sequence, (task, system, replicate) in enumerate(
        synthetic_schedule_rows(),
        start=1,
    ):
        lines.append(
            f"{sequence}\t{task}\t{system}\t{replicate}\t{SYNTHETIC_STAGE.stage}\n"
        )
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")
    recorded_path = path.name if portable else str(path)
    checksum_path.write_text(
        f"{sha256_file(path=path)}  {recorded_path}\n",
        encoding="utf-8",
    )


def run_id(*, task: str, system: str, replicate: int, attempt: int) -> str:
    return (
        f"{SYNTHETIC_STAGE.stage}-{task}-{system}"
        f"-r{replicate:02d}-a{attempt:02d}"
    )


def write_attempt(
    *,
    runs_root: Path,
    task: str,
    system: str,
    replicate: int,
    attempt: int,
    canonical_status: str,
) -> Path:
    identifier = run_id(
        task=task,
        system=system,
        replicate=replicate,
        attempt=attempt,
    )
    run_directory = runs_root / identifier
    output_directory = run_directory / "workspace" / "output"
    runtime_directory = run_directory / "runtime"
    input_directory = run_directory / "input"
    output_directory.mkdir(mode=0o700, parents=True)
    runtime_directory.mkdir(mode=0o700)
    input_directory.mkdir(mode=0o700)
    raw_output = f"synthetic opaque payload for {identifier}\n".encode(encoding="utf-8")
    (output_directory / "raw.txt").write_bytes(raw_output)
    requested_model = "gpt-5.6-sol" if system == "codex" else "claude-fable-5"
    cli_version = "codex-cli synthetic" if system == "codex" else "claude synthetic"
    served_models = [] if canonical_status == "runner_failure" else [requested_model]
    classification = (
        "infrastructure_failure" if canonical_status == "runner_failure" else "complete"
    )
    prediction_normalization = (
        "not_attempted" if canonical_status == "runner_failure" else "passed"
    )
    start_time = f"2026-07-12T08:{replicate:02d}:00Z"
    end_time = f"2026-07-12T08:{replicate:02d}:01Z"
    prompt_digest = "a" * 64
    metadata = {
        "run_id": identifier,
        "system": system,
        "requested_model": requested_model,
        "cli_version": cli_version,
        "effort": "max",
        "stage": SYNTHETIC_STAGE.stage,
        "task": task,
        "replicate": replicate,
        "attempt": attempt,
        "start_time": start_time,
        "end_time": end_time,
        "prompt_sha256": prompt_digest,
        "protocol_manifest_sha256": "b" * 64,
    }
    status = {
        "classification": classification,
        "detail": "synthetic terminal status",
        "exit_code": 70 if canonical_status == "runner_failure" else 0,
        "canonical_status": canonical_status,
        "prediction_normalization": prediction_normalization,
        "served_models": served_models,
    }
    manifest = {
        "run_id": identifier,
        "benchmark_version": "2026-07-12-v4",
        "task_variant": task,
        "system": system,
        "requested_model": requested_model,
        "served_models": served_models,
        "cli_version": cli_version,
        "effort": "max",
        "started_at": start_time,
        "ended_at": end_time,
        "attempt": attempt,
        "status": canonical_status,
        "prompt_sha256": f"sha256:{prompt_digest}",
        "pack_sha256": f"sha256:{'c' * 64}",
        "runner_image_sha256": f"sha256:{'d' * 64}",
        "trace_path": f"{identifier}/events.jsonl",
        "artifact_paths": [f"{identifier}/workspace/output/raw.txt"],
    }
    contents: dict[str, bytes] = {
        "metadata.json": json.dumps(metadata, sort_keys=True).encode(encoding="utf-8"),
        "events.jsonl": b'{"synthetic":"opaque event"}\n',
        "stderr.log": b"",
        "proxy.jsonl": b'{"synthetic":"opaque proxy record"}\n',
        "status.json": json.dumps(status, sort_keys=True).encode(encoding="utf-8"),
        "manifest.jsonl": (
            json.dumps(manifest, sort_keys=True) + "\n"
        ).encode(encoding="utf-8"),
        "predictions.jsonl": b"" if canonical_status == "runner_failure" else b"{}\n",
        "input.sha256": b"synthetic input ledger\n",
        "workspace.sha256": b"synthetic workspace ledger\n",
        "normalization.stderr": b"synthetic normalization record\n",
        "runtime/environment.json": b'{"synthetic":"environment"}\n',
        "runtime/environment-final.json": b'{"synthetic":"environment"}\n',
    }
    for relative_path, data in contents.items():
        path = run_directory / relative_path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(data)
    artifact_lines = [
        f"{sha256_file(path=run_directory / relative_path)}  "
        f"{runs_root / identifier / relative_path}\n"
        for relative_path in ARTIFACT_PATHS
    ]
    (run_directory / "artifact.sha256").write_text(
        "".join(artifact_lines),
        encoding="utf-8",
    )
    return run_directory


def build_closed_stage(*, root: Path) -> tuple[Path, Path, Path]:
    runs_root = root / "runs"
    runs_root.mkdir(mode=0o700)
    schedule_path = root / "schedules" / f"{SYNTHETIC_STAGE.stage}.tsv"
    schedule_checksum = schedule_path.with_suffix(".tsv.sha256")
    write_schedule(
        path=schedule_path,
        checksum_path=schedule_checksum,
        portable=False,
    )
    for index, (task, system, replicate) in enumerate(synthetic_schedule_rows()):
        status = "runner_failure" if index == 0 else "completed"
        write_attempt(
            runs_root=runs_root,
            task=task,
            system=system,
            replicate=replicate,
            attempt=1,
            canonical_status=status,
        )
        if status == "runner_failure":
            write_attempt(
                runs_root=runs_root,
                task=task,
                system=system,
                replicate=replicate,
                attempt=2,
                canonical_status="completed",
            )
    return runs_root, schedule_path, schedule_checksum


def assert_tree_is_not_writable(*, root: Path) -> None:
    for path in (root, *root.rglob(pattern="*")):
        assert stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) & 0o222 == 0


def test_stage_archive_round_trip_preserves_exact_bytes_and_registered_retry(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    runs_root, schedule_path, schedule_checksum = build_closed_stage(root=source_root)
    archive_directory = create_stage_archive(
        stage=SYNTHETIC_STAGE,
        runs_root=runs_root,
        schedule_path=schedule_path,
        schedule_checksum_path=schedule_checksum,
        planner_script=PLANNER_SCRIPT,
        planner_python=Path(sys.executable),
        archive_root=tmp_path / "archives",
        recorded_runs_root=runs_root,
    )

    assert sorted(path.name for path in archive_directory.iterdir()) == [
        f"v4-{SYNTHETIC_STAGE.stage}.files0",
        f"v4-{SYNTHETIC_STAGE.stage}.tar",
        f"v4-{SYNTHETIC_STAGE.stage}.tar.sha256",
        f"v4-{SYNTHETIC_STAGE.stage}.tree.sha256",
    ]
    assert_tree_is_not_writable(root=archive_directory)

    import_repository = tmp_path / "repository"
    local_schedule = (
        import_repository
        / "results"
        / "schedules"
        / "v4"
        / f"{SYNTHETIC_STAGE.stage}.tsv"
    )
    local_checksum = local_schedule.with_suffix(".tsv.sha256")
    local_schedule.parent.mkdir(mode=0o755, parents=True)
    shutil.copyfile(src=schedule_path, dst=local_schedule)
    local_checksum.write_text(
        f"{sha256_file(path=local_schedule)}  {local_schedule.name}\n",
        encoding="utf-8",
    )

    imported = import_stage_archive(
        stage=SYNTHETIC_STAGE,
        archive_directory=archive_directory,
        repository_root=import_repository,
        recorded_runs_root=runs_root,
    )

    assert len(imported) == 7
    assert sum(path.name.endswith("-a01") for path in imported) == 6
    assert sum(path.name.endswith("-a02") for path in imported) == 1
    for run_directory in imported:
        assert_tree_is_not_writable(root=run_directory)
        source_payload = runs_root / run_directory.name / "workspace" / "output" / "raw.txt"
        imported_payload = run_directory / "workspace" / "output" / "raw.txt"
        assert imported_payload.read_bytes() == source_payload.read_bytes()
    ledger = (
        import_repository
        / "results"
        / "raw-ledgers"
        / f"v4-{SYNTHETIC_STAGE.stage}.tree.sha256"
    )
    assert ledger.is_file()
    assert stat.S_IMODE(ledger.stat().st_mode) == 0o444
    archive_ledger = (
        archive_directory
        / f"v4-{SYNTHETIC_STAGE.stage}.tree.sha256"
    )
    assert ledger.read_bytes() == archive_ledger.read_bytes()

    with pytest.raises(FileExistsError, match="raw stage ledger already exists"):
        import_stage_archive(
            stage=SYNTHETIC_STAGE,
            archive_directory=archive_directory,
            repository_root=import_repository,
            recorded_runs_root=runs_root,
        )


def test_archive_and_import_fail_closed_on_symlink_or_changed_tar(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    runs_root, schedule_path, schedule_checksum = build_closed_stage(root=source_root)
    extra_task, extra_system, extra_replicate = synthetic_schedule_rows()[1]
    extra_retry = write_attempt(
        runs_root=runs_root,
        task=extra_task,
        system=extra_system,
        replicate=extra_replicate,
        attempt=2,
        canonical_status="completed",
    )
    with pytest.raises(ValueError, match="stage retries do not exactly match"):
        create_stage_archive(
            stage=SYNTHETIC_STAGE,
            runs_root=runs_root,
            schedule_path=schedule_path,
            schedule_checksum_path=schedule_checksum,
            planner_script=PLANNER_SCRIPT,
            planner_python=Path(sys.executable),
            archive_root=tmp_path / "wrong-retry-archives",
            recorded_runs_root=runs_root,
        )
    shutil.rmtree(path=extra_retry)

    first_run = sorted(runs_root.iterdir(), key=lambda path: path.name)[0]
    (first_run / "workspace" / "forbidden-link").symlink_to(
        first_run / "workspace" / "output" / "raw.txt"
    )

    with pytest.raises(ValueError, match="regular non-symlink"):
        create_stage_archive(
            stage=SYNTHETIC_STAGE,
            runs_root=runs_root,
            schedule_path=schedule_path,
            schedule_checksum_path=schedule_checksum,
            planner_script=PLANNER_SCRIPT,
            planner_python=Path(sys.executable),
            archive_root=tmp_path / "rejected-archives",
            recorded_runs_root=runs_root,
        )
    assert not (tmp_path / "rejected-archives" / f"v4-{SYNTHETIC_STAGE.stage}").exists()

    (first_run / "workspace" / "forbidden-link").unlink()
    archive_directory = create_stage_archive(
        stage=SYNTHETIC_STAGE,
        runs_root=runs_root,
        schedule_path=schedule_path,
        schedule_checksum_path=schedule_checksum,
        planner_script=PLANNER_SCRIPT,
        planner_python=Path(sys.executable),
        archive_root=tmp_path / "accepted-archives",
        recorded_runs_root=runs_root,
    )
    unsafe_archive = tmp_path / "unsafe-archive"
    shutil.copytree(src=archive_directory, dst=unsafe_archive)
    unsafe_archive.chmod(mode=0o700)
    unsafe_tar = unsafe_archive / f"v4-{SYNTHETIC_STAGE.stage}.tar"
    unsafe_tar.chmod(mode=0o644)
    with tarfile.open(name=unsafe_tar, mode="a") as archive:
        unsafe_member = tarfile.TarInfo(name="../escape")
        unsafe_member.size = 1
        archive.addfile(tarinfo=unsafe_member, fileobj=io.BytesIO(b"x"))
    unsafe_checksum = unsafe_archive / f"v4-{SYNTHETIC_STAGE.stage}.tar.sha256"
    unsafe_checksum.chmod(mode=0o644)
    unsafe_checksum.write_text(
        f"{sha256_file(path=unsafe_tar)}  {unsafe_tar.name}\n",
        encoding="utf-8",
    )
    for archive_file in unsafe_archive.iterdir():
        archive_file.chmod(
            mode=stat.S_IMODE(archive_file.stat().st_mode) & ~0o222
        )

    tar_path = archive_directory / f"v4-{SYNTHETIC_STAGE.stage}.tar"
    tar_path.chmod(mode=0o644)
    with tar_path.open(mode="ab") as stream:
        stream.write(b"changed-after-archive")
    tar_path.chmod(mode=0o444)

    import_repository = tmp_path / "tampered-repository"
    local_schedule = (
        import_repository
        / "results"
        / "schedules"
        / "v4"
        / f"{SYNTHETIC_STAGE.stage}.tsv"
    )
    local_checksum = local_schedule.with_suffix(".tsv.sha256")
    local_schedule.parent.mkdir(mode=0o755, parents=True)
    shutil.copyfile(src=schedule_path, dst=local_schedule)
    local_checksum.write_text(
        f"{sha256_file(path=local_schedule)}  {local_schedule.name}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="stage tar checksum mismatch"):
        import_stage_archive(
            stage=SYNTHETIC_STAGE,
            archive_directory=archive_directory,
            repository_root=import_repository,
            recorded_runs_root=runs_root,
        )
    assert not (import_repository / "results" / "raw").exists()

    with pytest.raises(ValueError, match="unsafe archive path"):
        import_stage_archive(
            stage=SYNTHETIC_STAGE,
            archive_directory=unsafe_archive,
            repository_root=import_repository,
            recorded_runs_root=runs_root,
        )
    assert not (tmp_path / "escape").exists()


def test_terminal_service_state_parser_is_strict() -> None:
    state = parse_systemctl_state(
        output=(
            b"LoadState=loaded\n"
            b"ActiveState=inactive\n"
            b"SubState=dead\n"
            b"Result=success\n"
            b"ExecMainStatus=0\n"
            b"MainPID=0\n"
        )
    )
    assert state.result == "success"
    with pytest.raises(ValueError):
        parse_systemctl_state(
            output=(
                b"LoadState=loaded\n"
                b"ActiveState=active\n"
                b"SubState=running\n"
                b"Result=success\n"
                b"ExecMainStatus=0\n"
                b"MainPID=42\n"
            )
        )
    with pytest.raises(ValueError):
        parse_systemctl_state(
            output=(
                b"LoadState=not-found\n"
                b"ActiveState=inactive\n"
                b"SubState=dead\n"
                b"Result=success\n"
                b"ExecMainStatus=0\n"
                b"MainPID=0\n"
            )
        )

    retention = parse_retention_state(
        output=(
            b"LoadState=loaded\n"
            b"ActiveState=active\n"
            b"SubState=running\n"
            b"Result=success\n"
            b"ExecMainStatus=0\n"
            b"MainPID=42\n"
            b"Wants=eng-bench-core-n3-v4.service\n"
        ),
        expected_service="eng-bench-core-n3-v4.service",
    )
    assert retention.main_pid == 42
    with pytest.raises(ValueError, match="wrong Wants dependency"):
        parse_retention_state(
            output=(
                b"LoadState=loaded\n"
                b"ActiveState=active\n"
                b"SubState=running\n"
                b"Result=success\n"
                b"ExecMainStatus=0\n"
                b"MainPID=42\n"
                b"Wants=eng-bench-core-extend-n5-v4.service\n"
            ),
            expected_service="eng-bench-core-n3-v4.service",
        )


def test_directory_publication_uses_atomic_no_replace(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "source-marker").write_text("source\n", encoding="utf-8")
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "destination-marker").write_text("destination\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        rename_directory_exclusive(source=source, destination=occupied)

    assert (source / "source-marker").read_text(encoding="utf-8") == "source\n"
    assert (occupied / "destination-marker").read_text(encoding="utf-8") == "destination\n"

    destination = tmp_path / "destination"
    rename_directory_exclusive(source=source, destination=destination)
    assert not source.exists()
    assert (destination / "source-marker").read_text(encoding="utf-8") == "source\n"
