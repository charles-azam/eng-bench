from __future__ import annotations

import csv
import hashlib
import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import pytest

from analysis.harvest import harvest
from analysis.integrity import ARTIFACT_PATHS, verify_tree_ledger
from analysis.models import DatasetEligibility, DatasetName, EligibilityReport
from eng_bench.models import (
    FrozenLedger,
    FrozenSystem,
    Prediction,
    RunManifest,
    RunStatus,
)


TASKS: tuple[str, ...] = (
    "nstf_blind_derive_duty",
    "triso_corrected_bounded_annex",
)
SYSTEMS: tuple[Literal["codex", "claude"], ...] = ("codex", "claude")
REQUESTED_MODELS: dict[str, str] = {
    "codex": "gpt-5.6-sol",
    "claude": "claude-fable-5",
}
CLI_VERSIONS: dict[str, str] = {
    "codex": "codex-cli synthetic",
    "claude": "synthetic (Claude Code)",
}
INPUT_CONTENTS: dict[str, str] = {
    "PROMPT.md": "Complete the engineering task offline.\n",
    "TASK.md": "# Synthetic frozen task\n",
}
ENVIRONMENT_CONTENT = '{"image":"synthetic-v2"}\n'


def digest_bytes(*, value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(*, path: Path) -> str:
    return digest_bytes(value=path.read_bytes())


def canonical_json(*, value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def render_input_ledger() -> str:
    return "".join(
        f"{digest_bytes(value=contents.encode())}  ./{relative_path}\n"
        for relative_path, contents in sorted(INPUT_CONTENTS.items())
    )


def write_matrix(*, path: Path) -> None:
    path.write_text(
        "stage\ttask\tsystem\tfirst_replicate\tlast_replicate\n"
        "core-n3\tnstf_blind_derive_duty\tcodex\t1\t3\n"
        "core-n3\tnstf_blind_derive_duty\tclaude\t1\t3\n"
        "core-n3\ttriso_corrected_bounded_annex\tcodex\t1\t3\n"
        "core-n3\ttriso_corrected_bounded_annex\tclaude\t1\t3\n"
        "core-extend-n5\tnstf_blind_derive_duty\tcodex\t4\t5\n"
        "core-extend-n5\tnstf_blind_derive_duty\tclaude\t4\t5\n"
        "core-extend-n5\ttriso_corrected_bounded_annex\tcodex\t4\t5\n"
        "core-extend-n5\ttriso_corrected_bounded_annex\tclaude\t4\t5\n"
        "nstf-duty-ablation-n3\tnstf_supplied_duty\tcodex\t1\t3\n"
        "nstf-duty-ablation-n3\tnstf_supplied_duty\tclaude\t1\t3\n",
        encoding="utf-8",
    )


def synthetic_ledger() -> FrozenLedger:
    pack_hash = f"sha256:{digest_bytes(value=render_input_ledger().encode())}"
    return FrozenLedger(
        benchmark_version="2026-07-11-v2",
        prompt_sha256=f"sha256:{digest_bytes(value=INPUT_CONTENTS['PROMPT.md'].encode())}",
        runner_image_sha256=f"sha256:{digest_bytes(value=ENVIRONMENT_CONTENT.encode())}",
        evaluator_manifest_sha256=f"sha256:{'e' * 64}",
        task_pack_sha256={
            "nstf_blind_derive_duty": pack_hash,
            "triso_corrected_bounded_annex": pack_hash,
            "nstf_supplied_duty": pack_hash,
        },
        systems={
            system: FrozenSystem(
                requested_model=REQUESTED_MODELS[system],
                cli_version=CLI_VERSIONS[system],
                effort="max",
            )
            for system in SYSTEMS
        },
    )


def write_ledger(*, path: Path) -> FrozenLedger:
    ledger = synthetic_ledger()
    path.write_text(
        f"{canonical_json(value=ledger.model_dump(mode='json'))}\n",
        encoding="utf-8",
    )
    return ledger


def write_files(*, root: Path, contents: dict[str, str]) -> None:
    for relative_path, text in contents.items():
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")


def render_tree_ledger(*, root: Path) -> str:
    relative_paths = sorted(
        path.relative_to(root).as_posix() for path in root.rglob(pattern="*") if path.is_file()
    )
    return "".join(
        f"{digest_file(path=root / relative_path)}  ./{relative_path}\n"
        for relative_path in relative_paths
    )


def run_id_for(
    *, stage: str, task: str, system: str, replicate: int, attempt: int
) -> str:
    return f"{stage}-{task}-{system}-r{replicate:02d}-a{attempt:02d}"


def status_payload(*, status: RunStatus, requested_model: str) -> dict[str, object]:
    if status is RunStatus.COMPLETED:
        return {
            "classification": "complete",
            "detail": "event stream and requested model passed runner checks",
            "exit_code": 0,
            "canonical_status": status.value,
            "prediction_normalization": "passed",
            "served_models": [requested_model],
        }
    if status is RunStatus.PROVIDER_FAILURE:
        return {
            "classification": "infrastructure_failure",
            "detail": "provider authentication failed",
            "exit_code": 1,
            "canonical_status": status.value,
            "prediction_normalization": "not_attempted",
            "served_models": [],
        }
    if status is RunStatus.RUNNER_FAILURE:
        return {
            "classification": "infrastructure_failure",
            "detail": "runner failed before inference",
            "exit_code": 1,
            "canonical_status": status.value,
            "prediction_normalization": "not_attempted",
            "served_models": [],
        }
    raise ValueError(f"unsupported synthetic status: {status.value}")


def write_synthetic_run(
    *,
    runs_root: Path,
    ledger: FrozenLedger,
    stage: str,
    task: str,
    system: Literal["codex", "claude"],
    replicate: int,
    attempt: int,
    status: RunStatus,
    retry_overlaps_first_attempt: bool = False,
    start_time_override: str | None = None,
    end_time_override: str | None = None,
) -> Path:
    run_id = run_id_for(
        stage=stage,
        task=task,
        system=system,
        replicate=replicate,
        attempt=attempt,
    )
    run_directory = runs_root / run_id
    input_directory = run_directory / "input"
    workspace_directory = run_directory / "workspace"
    runtime_directory = run_directory / "runtime"
    input_directory.mkdir(parents=True)
    workspace_directory.mkdir(parents=True)
    runtime_directory.mkdir(parents=True)
    write_files(root=input_directory, contents=INPUT_CONTENTS)
    write_files(root=workspace_directory, contents=INPUT_CONTENTS)
    if status is RunStatus.COMPLETED:
        write_files(
            root=workspace_directory,
            contents={"output/calculation_note.md": "# Synthetic calculation\n"},
        )
    (runtime_directory / "environment.json").write_text(
        ENVIRONMENT_CONTENT,
        encoding="utf-8",
    )
    (run_directory / "input.sha256").write_text(
        render_tree_ledger(root=input_directory),
        encoding="utf-8",
    )
    (run_directory / "workspace.sha256").write_text(
        render_tree_ledger(root=workspace_directory),
        encoding="utf-8",
    )

    requested_model = REQUESTED_MODELS[system]
    start_second = (
        20
        if attempt == 2 and retry_overlaps_first_attempt
        else 0 if attempt == 1 else 31
    )
    end_second = 30 if attempt == 1 else 59
    start_time = start_time_override or (
        f"2026-07-12T00:{replicate:02d}:{start_second:02d}Z"
    )
    end_time = end_time_override or (
        f"2026-07-12T00:{replicate:02d}:{end_second:02d}Z"
    )
    metadata = {
        "run_id": run_id,
        "system": system,
        "requested_model": requested_model,
        "cli_version": CLI_VERSIONS[system],
        "effort": "max",
        "stage": stage,
        "task": task,
        "replicate": replicate,
        "attempt": attempt,
        "start_time": start_time,
        "end_time": end_time,
        "prompt_sha256": ledger.prompt_sha256.removeprefix("sha256:"),
        "protocol_manifest_sha256": "f" * 64,
    }
    (run_directory / "metadata.json").write_text(
        f"{canonical_json(value=metadata)}\n",
        encoding="utf-8",
    )
    status_record = status_payload(status=status, requested_model=requested_model)
    (run_directory / "status.json").write_text(
        f"{canonical_json(value=status_record)}\n",
        encoding="utf-8",
    )

    workspace_paths = sorted(
        path.relative_to(workspace_directory).as_posix()
        for path in workspace_directory.rglob(pattern="*")
        if path.is_file()
    )
    served_models = [requested_model] if status is RunStatus.COMPLETED else []
    manifest = RunManifest(
        run_id=run_id,
        benchmark_version=ledger.benchmark_version,
        task_variant=task,
        system=system,
        requested_model=requested_model,
        served_models=served_models,
        cli_version=CLI_VERSIONS[system],
        effort="max",
        started_at=start_time,
        ended_at=end_time,
        attempt=attempt,
        status=status,
        prompt_sha256=ledger.prompt_sha256,
        pack_sha256=ledger.task_pack_sha256[task],
        runner_image_sha256=ledger.runner_image_sha256,
        trace_path=f"{run_id}/events.jsonl",
        artifact_paths=[f"{run_id}/workspace/{path}" for path in workspace_paths],
    )
    (run_directory / "manifest.jsonl").write_text(
        f"{canonical_json(value=manifest.model_dump(mode='json'))}\n",
        encoding="utf-8",
    )

    predictions: list[Prediction] = []
    if status is RunStatus.COMPLETED:
        predictions.append(
            Prediction(
                run_id=run_id,
                metric_id="synthetic.heat_rate_w",
                point=1000.0 + replicate,
                p10=900.0,
                p50=1000.0 + replicate,
                p90=1100.0,
                units="W",
                confidence=0.8,
                qualitative=None,
                category=None,
                source_artifact=f"{run_id}/workspace/output/calculation_note.md",
            )
        )
    (run_directory / "predictions.jsonl").write_text(
        "".join(
            f"{canonical_json(value=prediction.model_dump(mode='json'))}\n"
            for prediction in predictions
        ),
        encoding="utf-8",
    )
    (run_directory / "events.jsonl").write_text(
        f"{canonical_json(value={'type': 'synthetic'})}\n",
        encoding="utf-8",
    )
    (run_directory / "stderr.log").write_text(
        "authentication failure\n" if status is RunStatus.PROVIDER_FAILURE else "",
        encoding="utf-8",
    )
    (run_directory / "proxy.jsonl").write_text("", encoding="utf-8")
    (run_directory / "normalization.stderr").write_text("", encoding="utf-8")

    artifact_ledger = "".join(
        f"{digest_file(path=run_directory / relative_path)}  "
        f"/root/bench-v2/runs/{run_id}/{relative_path}\n"
        for relative_path in ARTIFACT_PATHS
    )
    (run_directory / "artifact.sha256").write_text(
        artifact_ledger,
        encoding="utf-8",
    )
    return run_directory


def prepare_repository(*, root: Path) -> tuple[Path, Path, Path, FrozenLedger]:
    runs_root = root / "raw"
    runs_root.mkdir()
    matrix_path = root / "matrix.tsv"
    ledger_path = root / "ledger.json"
    write_matrix(path=matrix_path)
    ledger = write_ledger(path=ledger_path)
    return runs_root, matrix_path, ledger_path, ledger


def frozen_stage_rows(*, stage: str) -> list[tuple[str, str, int, str]]:
    if stage == "core-n3":
        rows = [
            (task, system, replicate, stage)
            for task in TASKS
            for system in SYSTEMS
            for replicate in range(1, 4)
        ]
    elif stage == "core-extend-n5":
        rows = [
            (task, system, replicate, stage)
            for task in TASKS
            for system in SYSTEMS
            for replicate in range(4, 6)
        ]
    elif stage == "nstf-duty-ablation-n3":
        rows = [
            ("nstf_supplied_duty", system, replicate, stage)
            for system in SYSTEMS
            for replicate in range(1, 4)
        ]
    else:
        raise ValueError(f"unknown synthetic stage: {stage!r}")
    random.Random(20260711).shuffle(rows)
    return rows


def write_stage_schedule(
    *, schedules_root: Path, stage: str, include_vps_sidecar: bool = False
) -> list[tuple[str, str, int, str]]:
    schedules_root.mkdir(parents=True, exist_ok=True)
    (schedules_root / "README.md").write_text(
        "# Synthetic schedule provenance\n",
        encoding="utf-8",
    )
    rows = frozen_stage_rows(stage=stage)
    schedule_path = schedules_root / f"{stage}.tsv"
    with schedule_path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["sequence", "task", "system", "replicate", "stage"])
        for sequence, row in enumerate(rows, start=1):
            writer.writerow([sequence, *row])
    (schedules_root / f"{stage}.tsv.sha256").write_text(
        f"{digest_file(path=schedule_path)}  {schedule_path.name}\n",
        encoding="utf-8",
    )
    if include_vps_sidecar:
        (schedules_root / f"{stage}.tsv.vps.sha256").write_text(
            f"{digest_file(path=schedule_path)}  "
            f"/root/bench-v2/schedules/{schedule_path.name}\n",
            encoding="utf-8",
        )
    return rows


def populate_n3(
    *,
    runs_root: Path,
    ledger: FrozenLedger,
    omitted: tuple[str, str, int] | None = None,
    retried: tuple[str, str, int] | None = None,
) -> None:
    for task in TASKS:
        for system in SYSTEMS:
            for replicate in range(1, 4):
                identity = (task, system, replicate)
                if identity == omitted:
                    continue
                first_status = (
                    RunStatus.PROVIDER_FAILURE
                    if identity == retried
                    else RunStatus.COMPLETED
                )
                write_synthetic_run(
                    runs_root=runs_root,
                    ledger=ledger,
                    stage="core-n3",
                    task=task,
                    system=system,
                    replicate=replicate,
                    attempt=1,
                    status=first_status,
                )
                if identity == retried:
                    write_synthetic_run(
                        runs_root=runs_root,
                        ledger=ledger,
                        stage="core-n3",
                        task=task,
                        system=system,
                        replicate=replicate,
                        attempt=2,
                        status=RunStatus.COMPLETED,
                    )


def output_snapshot(*, root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob(pattern="*"))
        if path.is_file()
    }


def dataset_from_report(
    *, report: EligibilityReport, dataset_name: DatasetName
) -> DatasetEligibility:
    return next(dataset for dataset in report.datasets if dataset.dataset is dataset_name)


def test_tree_ledger_accepts_runner_locale_order_for_mixed_case_paths(
    tmp_path: Path,
) -> None:
    tree_root = tmp_path / "input"
    write_files(
        root=tree_root,
        contents={
            "inputs/01_geometry.md": "geometry\n",
            "inputs/02_materials.md": "materials\n",
            "PROMPT.md": "prompt\n",
            "TASK.md": "task\n",
        },
    )
    runner_locale_order = (
        "inputs/01_geometry.md",
        "inputs/02_materials.md",
        "PROMPT.md",
        "TASK.md",
    )
    ledger_path = tmp_path / "input.sha256"
    ledger_path.write_text(
        "".join(
            f"{digest_file(path=tree_root / relative_path)}  ./{relative_path}\n"
            for relative_path in runner_locale_order
        ),
        encoding="utf-8",
    )

    verified_paths = verify_tree_ledger(
        tree_root=tree_root,
        ledger_path=ledger_path,
    )

    assert verified_paths == tuple(sorted(runner_locale_order))


def test_valid_n3_harvest_is_gated_and_byte_deterministic(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    populate_n3(runs_root=runs_root, ledger=ledger)
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    first_report = harvest(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        output_directory=first_output,
    )
    second_report = harvest(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        output_directory=second_output,
    )

    assert first_report == second_report
    assert output_snapshot(root=first_output) == output_snapshot(root=second_output)
    assert dataset_from_report(
        report=first_report, dataset_name=DatasetName.N3
    ).eligible
    assert not dataset_from_report(
        report=first_report, dataset_name=DatasetName.N5
    ).eligible
    assert len((first_output / "n3" / "manifests.jsonl").read_text().splitlines()) == 12
    assert len((first_output / "n3" / "predictions.jsonl").read_text().splitlines()) == 12
    assert (first_output / "n5" / "manifests.jsonl").read_text() == ""
    assert len((first_output / "integrity.jsonl").read_text().splitlines()) == 12


def test_schedule_checksum_rows_prefix_and_first_attempt_chronology(
    tmp_path: Path,
) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    schedule_rows = write_stage_schedule(
        schedules_root=schedules_root,
        stage="core-n3",
        include_vps_sidecar=True,
    )
    for sequence, (task, system, replicate, stage) in enumerate(
        schedule_rows[:3], start=1
    ):
        write_synthetic_run(
            runs_root=runs_root,
            ledger=ledger,
            stage=stage,
            task=task,
            system=system,
            replicate=replicate,
            attempt=1,
            status=RunStatus.COMPLETED,
            start_time_override=f"2026-07-12T01:{sequence:02d}:00Z",
            end_time_override=f"2026-07-12T01:{sequence:02d}:30Z",
        )

    output_directory = tmp_path / "scheduled-output"
    report = harvest(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        output_directory=output_directory,
        schedules_root=schedules_root,
    )
    assert not dataset_from_report(
        report=report, dataset_name=DatasetName.N3
    ).eligible
    schedule_integrity = json.loads(
        (output_directory / "schedule_integrity.jsonl").read_text(encoding="utf-8")
    )
    assert schedule_integrity["stage"] == "core-n3"
    assert schedule_integrity["scheduled_replicates"] == 12
    assert schedule_integrity["launched_first_attempts"] == 3
    assert not schedule_integrity["complete_launch_prefix"]

    task, system, replicate, stage = schedule_rows[3]
    write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage=stage,
        task=task,
        system=system,
        replicate=replicate,
        attempt=1,
        status=RunStatus.COMPLETED,
        start_time_override="2026-07-12T01:03:20Z",
        end_time_override="2026-07-12T01:04:00Z",
    )
    with pytest.raises(ValueError, match="chronology violates schedule order"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "out-of-order-output",
            schedules_root=schedules_root,
        )


def test_extension_cannot_start_before_all_core_final_attempts(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    write_stage_schedule(schedules_root=schedules_root, stage="core-n3")
    extension_rows = write_stage_schedule(
        schedules_root=schedules_root,
        stage="core-extend-n5",
    )
    task, system, replicate, stage = extension_rows[0]
    write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage=stage,
        task=task,
        system=system,
        replicate=replicate,
        attempt=1,
        status=RunStatus.COMPLETED,
        start_time_override="2026-07-12T02:00:00Z",
        end_time_override="2026-07-12T02:00:30Z",
    )

    with pytest.raises(ValueError, match="launched before all 'core-n3'"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "premature-extension-output",
            schedules_root=schedules_root,
        )


def test_unrelated_runtime_symlink_is_ignored_but_artifact_symlink_fails(
    tmp_path: Path,
) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    populate_n3(runs_root=runs_root, ledger=ledger)
    run_id = run_id_for(
        stage="core-n3",
        task="nstf_blind_derive_duty",
        system="codex",
        replicate=1,
        attempt=1,
    )
    run_directory = runs_root / run_id
    unrelated_target = run_directory / "runtime" / "temporary-home"
    unrelated_target.mkdir()
    (run_directory / "runtime" / "home-link").symlink_to(
        target_is_directory=True,
        target=unrelated_target,
    )

    report = harvest(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        output_directory=tmp_path / "allowed-runtime-link",
    )
    assert dataset_from_report(
        report=report, dataset_name=DatasetName.N3
    ).eligible

    artifact_path = run_directory / "events.jsonl"
    artifact_contents = artifact_path.read_text(encoding="utf-8")
    artifact_path.unlink()
    replacement = run_directory / "runtime" / "replacement-events.jsonl"
    replacement.write_text(artifact_contents, encoding="utf-8")
    artifact_path.symlink_to(target=replacement)
    with pytest.raises(ValueError, match="checksummed artifact must be"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "forbidden-artifact-link",
        )

    artifact_path.unlink()
    artifact_path.write_text(artifact_contents, encoding="utf-8")
    ledger_path_in_run = run_directory / "artifact.sha256"
    ledger_contents = ledger_path_in_run.read_text(encoding="utf-8")
    ledger_path_in_run.unlink()
    replacement_ledger = run_directory / "runtime" / "replacement-artifact.sha256"
    replacement_ledger.write_text(ledger_contents, encoding="utf-8")
    ledger_path_in_run.symlink_to(target=replacement_ledger)
    with pytest.raises(ValueError, match="artifact checksum ledger must be"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "forbidden-ledger-link",
        )


def test_infrastructure_retry_is_preserved_but_counts_one_replicate(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    retried = ("nstf_blind_derive_duty", "codex", 1)
    populate_n3(runs_root=runs_root, ledger=ledger, retried=retried)
    output_directory = tmp_path / "harvested"

    report = harvest(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        output_directory=output_directory,
    )

    n3 = dataset_from_report(report=report, dataset_name=DatasetName.N3)
    assert n3.eligible
    affected_cell = next(
        cell
        for cell in n3.cells
        if cell.task_variant == retried[0] and cell.system == retried[1]
    )
    assert affected_cell.infrastructure_valid_replicates == [1, 2, 3]
    assert affected_cell.physical_attempts == 4
    assert len((output_directory / "n3" / "manifests.jsonl").read_text().splitlines()) == 13
    assert len((output_directory / "n3" / "predictions.jsonl").read_text().splitlines()) == 12
    with (output_directory / "attempts.csv").open(
        mode="r", encoding="utf-8", newline=""
    ) as stream:
        attempts = list(csv.DictReader(stream))
    retried_rows = [
        row
        for row in attempts
        if row["scheduled_replicate"] == "1"
        and row["task_variant"] == retried[0]
        and row["system"] == retried[1]
    ]
    assert [row["physical_attempt"] for row in retried_rows] == ["1", "2"]
    assert [row["status"] for row in retried_rows] == ["provider_failure", "completed"]
    assert [
        row["is_final_attempt_for_scheduled_replicate"] for row in retried_rows
    ] == ["false", "true"]

    write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage="core-n3",
        task="nstf_blind_derive_duty",
        system="codex",
        replicate=2,
        attempt=2,
        status=RunStatus.COMPLETED,
    )
    with pytest.raises(ValueError, match="retry is forbidden"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "invalid-retry-output",
        )


def test_retry_must_start_after_first_attempt_ends(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage="core-n3",
        task="nstf_blind_derive_duty",
        system="codex",
        replicate=1,
        attempt=1,
        status=RunStatus.PROVIDER_FAILURE,
    )
    write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage="core-n3",
        task="nstf_blind_derive_duty",
        system="codex",
        replicate=1,
        attempt=2,
        status=RunStatus.COMPLETED,
        retry_overlaps_first_attempt=True,
    )

    with pytest.raises(ValueError, match="retry started before"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "overlapping-retry-output",
        )


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda run_directory: (run_directory / "workspace" / "TASK.md").write_text(
            "corrupted after finalization\n", encoding="utf-8"
        ),
        lambda run_directory: (
            run_directory / "workspace" / "unrecorded-extra.txt"
        ).write_text("extra\n", encoding="utf-8"),
    ],
    ids=["hash-mismatch", "extra-file"],
)
def test_corrupt_hash_or_extra_workspace_file_fails_closed(
    tmp_path: Path,
    corrupt: Callable[[Path], int],
) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    run_directory = write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage="core-n3",
        task="nstf_blind_derive_duty",
        system="codex",
        replicate=1,
        attempt=1,
        status=RunStatus.COMPLETED,
    )
    corrupt(run_directory)

    with pytest.raises(ValueError, match="checksum"):
        harvest(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            output_directory=tmp_path / "harvested",
        )


def test_unequal_primary_cell_blocks_partial_n3_dataset(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    omitted = ("triso_corrected_bounded_annex", "claude", 3)
    populate_n3(runs_root=runs_root, ledger=ledger, omitted=omitted)
    output_directory = tmp_path / "harvested"

    report = harvest(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        output_directory=output_directory,
    )

    n3 = dataset_from_report(report=report, dataset_name=DatasetName.N3)
    assert not n3.eligible
    blocked_cell = next(
        cell
        for cell in n3.cells
        if cell.task_variant == omitted[0] and cell.system == omitted[1]
    )
    assert blocked_cell.missing_replicates == [3]
    assert blocked_cell.infrastructure_valid_replicates == [1, 2]
    assert (output_directory / "n3" / "manifests.jsonl").read_text() == ""
    assert (output_directory / "n3" / "predictions.jsonl").read_text() == ""
    assert len((output_directory / "attempts.csv").read_text().splitlines()) == 12
