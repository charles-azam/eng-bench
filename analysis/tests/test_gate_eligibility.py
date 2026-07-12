from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from analysis.gate_eligibility import build_attestation, main
from analysis.models import DatasetName
from analysis.tests.test_harvest_end_to_end import (
    prepare_repository,
    write_stage_schedule,
    write_synthetic_run,
)
from eng_bench.models import FrozenLedger, RunStatus


def populate_scheduled_stage(
    *,
    runs_root: Path,
    ledger: FrozenLedger,
    schedule_rows: list[tuple[str, str, int, str]],
    launch_count: int,
    start_hour: int,
    agent_failure_sequence: int | None,
) -> None:
    for sequence, (task, system, replicate, stage) in enumerate(
        schedule_rows[:launch_count], start=1
    ):
        status = (
            RunStatus.AGENT_FAILURE
            if sequence == agent_failure_sequence
            else RunStatus.COMPLETED
        )
        write_synthetic_run(
            runs_root=runs_root,
            ledger=ledger,
            stage=stage,
            task=task,
            system=system,
            replicate=replicate,
            attempt=1,
            status=status,
            start_time_override=f"2026-07-12T{start_hour:02d}:{sequence:02d}:00Z",
            end_time_override=f"2026-07-12T{start_hour:02d}:{sequence:02d}:30Z",
        )


def test_gate_reharvests_raw_attempts_and_rejects_incomplete_or_forged_inputs(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).parents[2]
    frozen_manifest_path = repository_root / "protocol" / "frozen_manifest.sha256"

    eligible_root = tmp_path / "eligible"
    eligible_root.mkdir()
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(
        root=eligible_root
    )
    schedules_root = eligible_root / "schedules"
    schedule_rows = write_stage_schedule(
        schedules_root=schedules_root,
        stage="core-n3",
        include_vps_sidecar=True,
    )
    populate_scheduled_stage(
        runs_root=runs_root,
        ledger=ledger,
        schedule_rows=schedule_rows,
        launch_count=12,
        start_hour=1,
        agent_failure_sequence=2,
    )
    output_path = eligible_root / "gate.json"
    commitment_key_path = eligible_root / "commitment.key"
    commitment_key_path.write_bytes(bytes(range(32)))
    commitment_key_path.chmod(mode=0o600)
    registered_ledger_sha256 = hashlib.sha256(ledger_path.read_bytes()).hexdigest()

    exit_code = main(
        arguments=[
            "--runs-root",
            str(runs_root),
            "--matrix",
            str(matrix_path),
            "--ledger",
            str(ledger_path),
            "--schedules-root",
            str(schedules_root),
            "--frozen-manifest",
            str(frozen_manifest_path),
            "--commitment-key",
            str(commitment_key_path),
            "--dataset",
            "n3",
            "--output",
            str(output_path),
        ],
        registered_attempt_protocol_manifest_sha256="f" * 64,
        registered_evaluation_ledger_sha256=registered_ledger_sha256,
    )
    attestation = build_attestation(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        schedules_root=schedules_root,
        frozen_manifest_path=frozen_manifest_path,
        commitment_key_path=commitment_key_path,
        dataset=DatasetName.N3,
        registered_attempt_protocol_manifest_sha256="f" * 64,
        registered_evaluation_ledger_sha256=registered_ledger_sha256,
    )

    assert exit_code == 0
    assert attestation.eligible
    assert len(attestation.cells) == 4
    assert all(
        cell.infrastructure_valid_replicates == [1, 2, 3]
        for cell in attestation.cells
    )
    assert "completed_replicates" not in output_path.read_text(encoding="utf-8")
    assert attestation.integrity_hmac_sha256
    assert attestation.schedule_integrity_hmac_sha256
    assert attestation.commitment_key_sha256 == hashlib.sha256(
        commitment_key_path.read_bytes()
    ).hexdigest()
    assert attestation.closed_stages == ["core-n3"]

    extension_rows = write_stage_schedule(
        schedules_root=schedules_root,
        stage="core-extend-n5",
    )
    with pytest.raises(ValueError, match="scheduled stages are not closed"):
        build_attestation(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            schedules_root=schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            commitment_key_path=commitment_key_path,
            dataset=DatasetName.N3,
            registered_attempt_protocol_manifest_sha256="f" * 64,
            registered_evaluation_ledger_sha256=registered_ledger_sha256,
        )

    populate_scheduled_stage(
        runs_root=runs_root,
        ledger=ledger,
        schedule_rows=extension_rows,
        launch_count=8,
        start_hour=2,
        agent_failure_sequence=None,
    )
    with pytest.raises(ValueError, match="registered primary selection is 'n5'"):
        build_attestation(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            schedules_root=schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            commitment_key_path=commitment_key_path,
            dataset=DatasetName.N3,
            registered_attempt_protocol_manifest_sha256="f" * 64,
            registered_evaluation_ledger_sha256=registered_ledger_sha256,
        )
    n5_attestation = build_attestation(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        schedules_root=schedules_root,
        frozen_manifest_path=frozen_manifest_path,
        commitment_key_path=commitment_key_path,
        dataset=DatasetName.N5,
        registered_attempt_protocol_manifest_sha256="f" * 64,
        registered_evaluation_ledger_sha256=registered_ledger_sha256,
    )
    assert n5_attestation.closed_stages == ["core-n3", "core-extend-n5"]

    incomplete_root = tmp_path / "incomplete"
    incomplete_root.mkdir()
    (
        incomplete_runs,
        incomplete_matrix,
        incomplete_ledger_path,
        incomplete_ledger,
    ) = prepare_repository(root=incomplete_root)
    incomplete_schedules = incomplete_root / "schedules"
    incomplete_rows = write_stage_schedule(
        schedules_root=incomplete_schedules,
        stage="core-n3",
    )
    populate_scheduled_stage(
        runs_root=incomplete_runs,
        ledger=incomplete_ledger,
        schedule_rows=incomplete_rows,
        launch_count=11,
        start_hour=1,
        agent_failure_sequence=2,
    )
    with pytest.raises(ValueError, match="is not eligible"):
        build_attestation(
            runs_root=incomplete_runs,
            matrix_path=incomplete_matrix,
            ledger_path=incomplete_ledger_path,
            schedules_root=incomplete_schedules,
            frozen_manifest_path=frozen_manifest_path,
            commitment_key_path=commitment_key_path,
            dataset=DatasetName.N3,
            registered_attempt_protocol_manifest_sha256="f" * 64,
            registered_evaluation_ledger_sha256=hashlib.sha256(
                incomplete_ledger_path.read_bytes()
            ).hexdigest(),
        )

    forged_matrix_path = eligible_root / "forged-matrix.tsv"
    forged_matrix_path.write_bytes(
        matrix_path.read_bytes().replace(
            b"nstf_blind_derive_duty", b"unregistered_task"
        )
    )
    with pytest.raises(ValueError, match="disagree with the frozen protocol manifest"):
        build_attestation(
            runs_root=runs_root,
            matrix_path=forged_matrix_path,
            ledger_path=ledger_path,
            schedules_root=schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            commitment_key_path=commitment_key_path,
            dataset=DatasetName.N3,
            registered_attempt_protocol_manifest_sha256="f" * 64,
            registered_evaluation_ledger_sha256=registered_ledger_sha256,
        )

    with pytest.raises(ValueError, match="evaluation ledger digest"):
        build_attestation(
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            schedules_root=schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            commitment_key_path=commitment_key_path,
            dataset=DatasetName.N3,
            registered_attempt_protocol_manifest_sha256="f" * 64,
        )
