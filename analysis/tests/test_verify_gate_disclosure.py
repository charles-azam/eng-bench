from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysis.gate_eligibility import (
    GateAttestation,
    build_attestation,
    canonical_json,
    write_attestation,
)
from analysis.models import DatasetName, StrictAnalysisModel
from analysis.tests.test_harvest_end_to_end import (
    prepare_repository,
    write_stage_schedule,
    write_synthetic_run,
)
from analysis.verify_gate_disclosure import (
    DisclosedGateKey,
    GateDisclosureVerificationReport,
    GateKeyDisclosure,
    main,
    verify_gate_disclosure,
)
from eng_bench.models import FrozenLedger, RunStatus


class SyntheticDisclosedCampaign(StrictAnalysisModel):
    repository_root: Path
    disclosure_path: Path
    runs_root: Path
    matrix_path: Path
    ledger_path: Path
    schedules_root: Path
    frozen_manifest_path: Path
    registered_ledger_sha256: str
    keys_by_attestation_path: dict[str, str]


def populate_stage(
    *,
    runs_root: Path,
    ledger: FrozenLedger,
    schedule_rows: list[tuple[str, str, int, str]],
    start_hour: int,
    retry_sequence: int | None,
    agent_failure_sequence: int | None,
) -> None:
    for sequence, (task, system, replicate, stage) in enumerate(
        schedule_rows, start=1
    ):
        first_status = (
            RunStatus.PROVIDER_FAILURE
            if sequence == retry_sequence
            else (
                RunStatus.AGENT_FAILURE
                if sequence == agent_failure_sequence
                else RunStatus.COMPLETED
            )
        )
        write_synthetic_run(
            runs_root=runs_root,
            ledger=ledger,
            stage=stage,
            task=task,
            system=system,
            replicate=replicate,
            attempt=1,
            status=first_status,
            start_time_override=f"2026-07-12T{start_hour:02d}:{sequence:02d}:00Z",
            end_time_override=f"2026-07-12T{start_hour:02d}:{sequence:02d}:10Z",
        )
        if sequence == retry_sequence:
            write_synthetic_run(
                runs_root=runs_root,
                ledger=ledger,
                stage=stage,
                task=task,
                system=system,
                replicate=replicate,
                attempt=2,
                status=RunStatus.COMPLETED,
                start_time_override=(
                    f"2026-07-12T{start_hour:02d}:{sequence:02d}:11Z"
                ),
                end_time_override=f"2026-07-12T{start_hour:02d}:{sequence:02d}:30Z",
            )


def commit_gate(
    *,
    output_path: Path,
    key_path: Path,
    key: bytes,
    dataset: DatasetName,
    runs_root: Path,
    matrix_path: Path,
    ledger_path: Path,
    schedules_root: Path,
    frozen_manifest_path: Path,
    registered_ledger_sha256: str,
) -> None:
    key_path.write_bytes(key)
    key_path.chmod(mode=0o600)
    attestation = build_attestation(
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        schedules_root=schedules_root,
        frozen_manifest_path=frozen_manifest_path,
        commitment_key_path=key_path,
        dataset=dataset,
        registered_attempt_protocol_manifest_sha256="f" * 64,
        registered_evaluation_ledger_sha256=registered_ledger_sha256,
    )
    write_attestation(path=output_path, attestation=attestation)


def write_disclosure(
    *, path: Path, keys_by_attestation_path: dict[str, str]
) -> None:
    disclosure = GateKeyDisclosure(
        gates=[
            DisclosedGateKey(
                attestation_path=attestation_path,
                commitment_key_hex=key_hex,
            )
            for attestation_path, key_hex in keys_by_attestation_path.items()
        ]
    )
    path.write_text(
        f"{canonical_json(model=disclosure)}\n",
        encoding="utf-8",
    )


def prepare_final_disclosed_campaign(*, root: Path) -> SyntheticDisclosedCampaign:
    repository_root = root / "public-repository"
    results_root = repository_root / "results"
    results_root.mkdir(parents=True)
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(
        root=results_root
    )
    schedules_root = results_root / "schedules" / "v4"
    gates_root = results_root / "gates"
    gates_root.mkdir()
    private_keys_root = root / "private-keys"
    private_keys_root.mkdir()
    frozen_manifest_path = (
        Path(__file__).parents[2] / "protocol" / "frozen_manifest.sha256"
    )
    registered_ledger_sha256 = hashlib.sha256(ledger_path.read_bytes()).hexdigest()

    keys_by_attestation_path: dict[str, str] = {}
    stage_specs = (
        ("core-n3", DatasetName.N3, 1, 2, 3, bytes(range(32))),
        ("core-extend-n5", DatasetName.N5, 2, None, None, bytes(range(32, 64))),
        (
            "nstf-duty-ablation-n3",
            DatasetName.ABLATION,
            3,
            None,
            None,
            bytes(range(64, 96)),
        ),
    )
    for stage, dataset, start_hour, retry_sequence, agent_failure_sequence, key in (
        stage_specs
    ):
        schedule_rows = write_stage_schedule(
            schedules_root=schedules_root,
            stage=stage,
            include_vps_sidecar=stage == "core-n3",
        )
        populate_stage(
            runs_root=runs_root,
            ledger=ledger,
            schedule_rows=schedule_rows,
            start_hour=start_hour,
            retry_sequence=retry_sequence,
            agent_failure_sequence=agent_failure_sequence,
        )
        attestation_relative_path = f"results/gates/{stage}.json"
        commit_gate(
            output_path=repository_root / attestation_relative_path,
            key_path=private_keys_root / f"{stage}.key",
            key=key,
            dataset=dataset,
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            schedules_root=schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            registered_ledger_sha256=registered_ledger_sha256,
        )
        keys_by_attestation_path[attestation_relative_path] = key.hex()

    disclosure_path = gates_root / "disclosed-keys.json"
    write_disclosure(
        path=disclosure_path,
        keys_by_attestation_path=keys_by_attestation_path,
    )
    return SyntheticDisclosedCampaign(
        repository_root=repository_root,
        disclosure_path=disclosure_path,
        runs_root=runs_root,
        matrix_path=matrix_path,
        ledger_path=ledger_path,
        schedules_root=schedules_root,
        frozen_manifest_path=frozen_manifest_path,
        registered_ledger_sha256=registered_ledger_sha256,
        keys_by_attestation_path=keys_by_attestation_path,
    )


def verify_campaign(*, campaign: SyntheticDisclosedCampaign) -> GateDisclosureVerificationReport:
    return verify_gate_disclosure(
        repository_root=campaign.repository_root,
        disclosure_path=campaign.disclosure_path,
        runs_root=campaign.runs_root,
        matrix_path=campaign.matrix_path,
        ledger_path=campaign.ledger_path,
        schedules_root=campaign.schedules_root,
        frozen_manifest_path=campaign.frozen_manifest_path,
        registered_attempt_protocol_manifest_sha256="f" * 64,
        registered_evaluation_ledger_sha256=campaign.registered_ledger_sha256,
    )


def test_disclosed_keys_reconstruct_every_historical_gate_from_final_campaign(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    campaign = prepare_final_disclosed_campaign(root=tmp_path)

    exit_code = main(
        arguments=[
            "--repository-root",
            str(campaign.repository_root),
            "--disclosure",
            str(campaign.disclosure_path),
            "--runs-root",
            str(campaign.runs_root),
            "--matrix",
            str(campaign.matrix_path),
            "--ledger",
            str(campaign.ledger_path),
            "--schedules-root",
            str(campaign.schedules_root),
            "--frozen-manifest",
            str(campaign.frozen_manifest_path),
        ],
        registered_attempt_protocol_manifest_sha256="f" * 64,
        registered_evaluation_ledger_sha256=campaign.registered_ledger_sha256,
    )
    report = GateDisclosureVerificationReport.model_validate_json(
        capsys.readouterr().out
    )

    assert exit_code == 0
    assert report.verified
    assert [gate.dataset for gate in report.gates] == [
        DatasetName.N3,
        DatasetName.N5,
        DatasetName.ABLATION,
    ]
    assert [gate.closed_stages for gate in report.gates] == [
        ["core-n3"],
        ["core-n3", "core-extend-n5"],
        ["core-n3", "core-extend-n5", "nstf-duty-ablation-n3"],
    ]
    assert all(gate.attestation_sha256 for gate in report.gates)


def test_disclosure_is_strict_and_rejects_wrong_keys_or_changed_attestations(
    tmp_path: Path,
) -> None:
    campaign = prepare_final_disclosed_campaign(root=tmp_path)
    core_path = "results/gates/core-n3.json"
    core_attestation_path = campaign.repository_root / core_path
    committed_bytes = core_attestation_path.read_bytes()
    committed = GateAttestation.model_validate_json(committed_bytes)
    core_key_hex = campaign.keys_by_attestation_path[core_path]

    with pytest.raises(ValidationError, match="canonical relative POSIX"):
        GateKeyDisclosure.model_validate(
            {
                "schema_version": "1.0",
                "gates": [
                    {
                        "attestation_path": "../core-n3.json",
                        "commitment_key_hex": core_key_hex,
                    }
                ],
            }
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GateKeyDisclosure.model_validate(
            {
                "schema_version": "1.0",
                "gates": [
                    {
                        "attestation_path": core_path,
                        "commitment_key_hex": core_key_hex,
                        "note": "not allowed",
                    }
                ],
            }
        )

    write_disclosure(
        path=campaign.disclosure_path,
        keys_by_attestation_path={core_path: "0" * 64},
    )
    with pytest.raises(ValueError, match="disclosed commitment key does not match"):
        verify_campaign(campaign=campaign)

    write_disclosure(
        path=campaign.disclosure_path,
        keys_by_attestation_path={core_path: core_key_hex},
    )
    changed_model = committed.model_copy(
        update={"attempts_hmac_sha256": "0" * 64}
    )
    core_attestation_path.write_text(
        f"{canonical_json(model=changed_model)}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reconstructed gate model does not match"):
        verify_campaign(campaign=campaign)

    core_attestation_path.write_text(
        f"{json.dumps(committed.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reconstructed gate bytes do not match"):
        verify_campaign(campaign=campaign)

    core_attestation_path.write_bytes(committed_bytes)
    assert verify_campaign(campaign=campaign).verified
