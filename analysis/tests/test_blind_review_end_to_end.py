from __future__ import annotations

import csv
import json
import stat
from pathlib import Path

import pytest

from analysis.blind_review import (
    REVIEW_FIELDNAMES,
    RUBRIC_ITEMS,
    PublicProvenance,
    SealedMapping,
    finalize_review_bundle,
    prepare_review_bundle,
)
from analysis.integrity import ARTIFACT_PATHS, load_single_jsonl
from analysis.tests.test_harvest_end_to_end import (
    canonical_json,
    digest_file,
    prepare_repository,
    render_tree_ledger,
    write_stage_schedule,
    write_synthetic_run,
)
from eng_bench.models import FrozenLedger, RunManifest, RunStatus


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUBRIC_SOURCE = REPOSITORY_ROOT / "protocol" / "ARTIFACT_REVIEW.md"


def rewrite_attempt_output(
    *,
    run_directory: Path,
    status: RunStatus,
    classification: str,
    served_models: list[str],
    note_contents: bytes,
) -> RunManifest:
    output_directory = run_directory / "workspace" / "output"
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "calculation_note.md").write_bytes(note_contents)
    predictions_bytes = (
        b'{"predictions":[{"confidence":0.72,"metric_id":"synthetic.heat_rate_w",'
        b'"p10":900.0,"p50":1000.0,"p90":1120.0,"units":"W"}]}\n'
    )
    (output_directory / "predictions.json").write_bytes(predictions_bytes)
    (run_directory / "workspace.sha256").write_text(
        render_tree_ledger(root=run_directory / "workspace"),
        encoding="utf-8",
    )
    original_manifest = load_single_jsonl(
        path=run_directory / "manifest.jsonl",
        model_type=RunManifest,
    )
    workspace_paths = sorted(
        path.relative_to(run_directory / "workspace").as_posix()
        for path in (run_directory / "workspace").rglob(pattern="*")
        if path.is_file()
    )
    manifest = original_manifest.model_copy(
        update={
            "status": status,
            "served_models": served_models,
            "artifact_paths": [
                f"{run_directory.name}/workspace/{relative_path}"
                for relative_path in workspace_paths
            ],
        }
    )
    (run_directory / "manifest.jsonl").write_text(
        f"{canonical_json(value=manifest.model_dump(mode='json'))}\n",
        encoding="utf-8",
    )
    if status is not RunStatus.COMPLETED:
        (run_directory / "predictions.jsonl").write_text("", encoding="utf-8")
    status_record = {
        "classification": classification,
        "detail": f"synthetic {status.value} outcome",
        "exit_code": 0,
        "canonical_status": status.value,
        "prediction_normalization": (
            "passed" if status is RunStatus.COMPLETED else "not_attempted"
        ),
        "served_models": served_models,
    }
    (run_directory / "status.json").write_text(
        f"{canonical_json(value=status_record)}\n",
        encoding="utf-8",
    )
    artifact_ledger = "".join(
        f"{digest_file(path=run_directory / relative_path)}  "
        f"/root/bench-v2/runs/{run_directory.name}/{relative_path}\n"
        for relative_path in ARTIFACT_PATHS
    )
    (run_directory / "artifact.sha256").write_text(
        artifact_ledger,
        encoding="utf-8",
    )
    return manifest


def materialize_complete_n3_campaign(
    *, runs_root: Path, schedules_root: Path, ledger: FrozenLedger
) -> None:
    schedule_rows = write_stage_schedule(
        schedules_root=schedules_root,
        stage="core-n3",
        include_vps_sidecar=True,
    )
    requested_models = {
        system: frozen_system.requested_model
        for system, frozen_system in ledger.systems.items()
    }
    for sequence, (task, system, replicate, stage) in enumerate(
        schedule_rows,
        start=1,
    ):
        first_status = RunStatus.PROVIDER_FAILURE if sequence == 1 else RunStatus.COMPLETED
        first_directory = write_synthetic_run(
            runs_root=runs_root,
            ledger=ledger,
            stage=stage,
            task=task,
            system=system,
            replicate=replicate,
            attempt=1,
            status=first_status,
            start_time_override=f"2026-07-12T01:{sequence:02d}:00Z",
            end_time_override=f"2026-07-12T01:{sequence:02d}:20Z",
        )
        if first_status is RunStatus.PROVIDER_FAILURE:
            retry_directory = write_synthetic_run(
                runs_root=runs_root,
                ledger=ledger,
                stage=stage,
                task=task,
                system=system,
                replicate=replicate,
                attempt=2,
                status=RunStatus.COMPLETED,
                start_time_override="2026-07-12T01:20:00Z",
                end_time_override="2026-07-12T01:20:30Z",
            )
            rewrite_attempt_output(
                run_directory=retry_directory,
                status=RunStatus.COMPLETED,
                classification="complete",
                served_models=[requested_models[system]],
                note_contents=b"# Retried calculation\nAuditable balances and uncertainty.\n",
            )
            continue
        special_statuses = {
            2: (RunStatus.AGENT_FAILURE, "agent_failure", [requested_models[system]]),
            3: (RunStatus.REFUSAL, "model_refusal", [requested_models[system]]),
            4: (
                RunStatus.FALLBACK_CONTAMINATED,
                "model_contamination",
                ["synthetic-fallback-model"],
            ),
        }
        status, classification, served_models = special_statuses.get(
            sequence,
            (RunStatus.COMPLETED, "complete", [requested_models[system]]),
        )
        rewrite_attempt_output(
            run_directory=first_directory,
            status=status,
            classification=classification,
            served_models=served_models,
            note_contents=(
                f"# Calculation packet {sequence}\n"
                f"Auditable balances and uncertainty for {task}.\n"
                + (
                    "Access attempt: an external lookup was blocked.\n"
                    if sequence % 2 == 0
                    else ""
                )
            ).encode(encoding="utf-8"),
        )


def materialize_complete_all_stage_campaign(
    *, runs_root: Path, schedules_root: Path, ledger: FrozenLedger
) -> None:
    stages = (
        ("core-n3", 1),
        ("core-extend-n5", 2),
        ("nstf-duty-ablation-n3", 3),
    )
    for stage, hour in stages:
        schedule_rows = write_stage_schedule(
            schedules_root=schedules_root,
            stage=stage,
            include_vps_sidecar=True,
        )
        for sequence, (task, system, replicate, scheduled_stage) in enumerate(
            schedule_rows,
            start=1,
        ):
            run_directory = write_synthetic_run(
                runs_root=runs_root,
                ledger=ledger,
                stage=scheduled_stage,
                task=task,
                system=system,
                replicate=replicate,
                attempt=1,
                status=RunStatus.COMPLETED,
                start_time_override=f"2026-07-12T0{hour}:{sequence:02d}:00Z",
                end_time_override=f"2026-07-12T0{hour}:{sequence:02d}:20Z",
            )
            rewrite_attempt_output(
                run_directory=run_directory,
                status=RunStatus.COMPLETED,
                classification="complete",
                served_models=[ledger.systems[system].requested_model],
                note_contents=(
                    f"# Stage {hour} calculation {sequence}\n"
                    f"Auditable balances and uncertainty for {task}.\n"
                ).encode(encoding="utf-8"),
            )


def bundle_locations(*, root: Path) -> tuple[Path, Path, Path]:
    review_parent = root / "review-area"
    private_parent = root / "private-area"
    public_parent = root / "publication-area"
    review_parent.mkdir()
    private_parent.mkdir()
    public_parent.mkdir()
    return (
        review_parent / "review-bundle",
        private_parent / "sealed-mapping.json",
        public_parent / "public-bundle",
    )


def prepare_synthetic_review(
    *, root: Path
) -> tuple[Path, Path, Path, Path, Path, Path, SealedMapping]:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=root)
    schedules_root = root / "schedules"
    materialize_complete_n3_campaign(
        runs_root=runs_root,
        schedules_root=schedules_root,
        ledger=ledger,
    )
    review_bundle, mapping_path, public_bundle = bundle_locations(root=root)
    packet_count = prepare_review_bundle(
        runs_root=runs_root,
        matrix_path=matrix_path,
        schedules_root=schedules_root,
        ledger_path=ledger_path,
        rubric_source_path=RUBRIC_SOURCE,
        review_bundle=review_bundle,
        sealed_mapping_path=mapping_path,
    )
    assert packet_count == 12
    mapping = SealedMapping.model_validate_json(mapping_path.read_bytes())
    return (
        runs_root,
        matrix_path,
        schedules_root,
        ledger_path,
        review_bundle,
        mapping_path,
        mapping,
    )


def complete_review(*, review_path: Path) -> None:
    with review_path.open(mode="r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row["item_id"] == "no_unavailable_access":
            note = (
                review_path.parent
                / "packets"
                / row["neutral_label"]
                / "submitted-output"
                / "calculation_note.md"
            ).read_text(encoding="utf-8")
            if "Access attempt:" in note:
                row["status"] = "partial"
                row["rationale"] = (
                    "Submitted artifact evidence: calculation_note.md records an attempted "
                    "external lookup, but raw traces are absent."
                )
            else:
                row["status"] = "not_applicable"
                row["rationale"] = "Raw traces are absent from the identity-blind packet."
        elif row["item_id"] == "artifacts_and_offline_scripts":
            row["status"] = "pass"
            row["rationale"] = (
                "No applicable scripts: Cited artifacts verified: calculation_note.md "
                "and predictions.json."
            )
        else:
            row["status"] = "pass"
            row["rationale"] = "The submitted artifact provides auditable evidence."
    with review_path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(REVIEW_FIELDNAMES),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def test_prepare_and_finalize_complete_campaign_with_public_provenance(
    tmp_path: Path,
) -> None:
    (
        runs_root,
        matrix_path,
        schedules_root,
        ledger_path,
        review_bundle,
        mapping_path,
        mapping,
    ) = prepare_synthetic_review(root=tmp_path)
    public_parent = tmp_path / "publication-two"
    public_parent.mkdir()
    first_public = public_parent / "first"
    second_public = public_parent / "second"

    symlink_public = public_parent / "symlink-public"
    symlink_public.symlink_to(target=public_parent / "missing-public")
    with pytest.raises(ValueError, match="must not already exist"):
        finalize_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
            public_bundle=symlink_public,
        )
    symlink_public.unlink()

    misplaced_mapping = review_bundle.parent / "misplaced-mapping.json"
    misplaced_mapping.write_bytes(mapping_path.read_bytes())
    misplaced_mapping.chmod(mode=0o600)
    with pytest.raises(ValueError, match="outside protected directory"):
        finalize_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=misplaced_mapping,
            public_bundle=public_parent / "misplaced-map-output",
        )
    misplaced_mapping.unlink()

    assert stat.S_IMODE(mapping_path.stat().st_mode) == 0o600
    assert not any(
        path.name.startswith(".review-bundle.staging-")
        for path in review_bundle.parent.iterdir()
    )
    assert len(mapping.packets) == 12
    assert {packet.run_status for packet in mapping.packets} >= {
        RunStatus.COMPLETED,
        RunStatus.AGENT_FAILURE,
        RunStatus.REFUSAL,
        RunStatus.FALLBACK_CONTAMINATED,
    }
    assert all(packet.run_status is not RunStatus.PROVIDER_FAILURE for packet in mapping.packets)

    with (review_bundle / "review.csv").open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as stream:
        blank_rows = list(csv.DictReader(stream))
    assert len(blank_rows) == 12 * len(RUBRIC_ITEMS) == 96
    assert all(row["status"] == "" and row["rationale"] == "" for row in blank_rows)
    for packet in mapping.packets:
        packet_root = review_bundle / "packets" / packet.neutral_label
        roles = {file.role.value for file in packet.files}
        assert roles == {"task_context", "submitted_output"}
        assert (packet_root / "task-context" / "PROMPT.md").read_bytes() == (
            runs_root / packet.run_id / "input" / "PROMPT.md"
        ).read_bytes()
        predictions_mapping = next(
            file
            for file in packet.files
            if file.packet_relative_path == "submitted-output/predictions.json"
        )
        assert (
            packet_root / predictions_mapping.packet_relative_path
        ).read_bytes() == (
            runs_root / packet.run_id / predictions_mapping.source_relative_path
        ).read_bytes()
        packet_manifest = json.loads((packet_root / "packet.json").read_text())
        assert packet_manifest["benchmark_version"] == packet.benchmark_version
        assert packet_manifest["pack_sha256"] == packet.pack_sha256
        assert packet_manifest["runner_image_sha256"] == packet.runner_image_sha256

    blinded_metadata = (
        (review_bundle / "review.csv").read_text(encoding="utf-8")
        + (review_bundle / "bundle.json").read_text(encoding="utf-8")
        + "".join(
            (review_bundle / "packets" / packet.neutral_label / "packet.json").read_text(
                encoding="utf-8"
            )
            for packet in mapping.packets
        )
    ).lower()
    forbidden_metadata = {
        "codex",
        "claude",
        "run_id",
        "run_status",
        "trace_path",
        "started_at",
        "ended_at",
        "held_out_measurement",
        "evaluator_score",
        *(packet.run_id.lower() for packet in mapping.packets),
    }
    assert all(token not in blinded_metadata for token in forbidden_metadata)
    assert "predictions.json" in blinded_metadata

    complete_review(review_path=review_bundle / "review.csv")
    review_path = review_bundle / "review.csv"
    with review_path.open(mode="r", encoding="utf-8", newline="") as stream:
        valid_rows = list(csv.DictReader(stream))
    invalid_item_six_rows = [dict(row) for row in valid_rows]
    invalid_item_six = next(
        row
        for row in invalid_item_six_rows
        if row["item_id"] == "artifacts_and_offline_scripts"
    )
    packet_for_invalid_item = next(
        packet
        for packet in mapping.packets
        if packet.neutral_label == invalid_item_six["neutral_label"]
    )
    invalid_item_six["rationale"] = (
        "Offline command: bwrap --unshare-net uv run python check.py; "
        f"Runner manifest: {packet_for_invalid_item.runner_image_sha256}; Result: passed."
    )
    with review_path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(REVIEW_FIELDNAMES),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(invalid_item_six_rows)
    invalid_item_six_public = public_parent / "invalid-item-six"
    with pytest.raises(ValueError, match="no applicable submitted script"):
        finalize_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
            public_bundle=invalid_item_six_public,
        )
    assert not invalid_item_six_public.exists()

    invalid_partial_rows = [dict(row) for row in valid_rows]
    invalid_partial = next(
        row
        for row in invalid_partial_rows
        if row["item_id"] == "artifacts_and_offline_scripts"
    )
    invalid_partial["status"] = "partial"
    invalid_partial["rationale"] = "The cited artifact is incomplete."
    with review_path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(REVIEW_FIELDNAMES),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(invalid_partial_rows)
    invalid_partial_public = public_parent / "invalid-item-six-partial"
    with pytest.raises(ValueError, match="must disclose non-execution"):
        finalize_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
            public_bundle=invalid_partial_public,
        )
    assert not invalid_partial_public.exists()

    with review_path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(REVIEW_FIELDNAMES),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(valid_rows[:-1])
    incomplete_public = public_parent / "incomplete-review"
    with pytest.raises(ValueError, match="exactly eight"):
        finalize_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
            public_bundle=incomplete_public,
        )
    assert not incomplete_public.exists()

    invalid_rows = [dict(row) for row in valid_rows]
    invalid_item_eight = next(
        row for row in invalid_rows if row["item_id"] == "no_unavailable_access"
    )
    invalid_item_eight["status"] = "pass"
    invalid_item_eight["rationale"] = (
        "Submitted artifact evidence: calculation_note.md records no access attempt."
    )
    with review_path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(REVIEW_FIELDNAMES),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(invalid_rows)
    invalid_public = public_parent / "invalid-item-eight"
    with pytest.raises(ValueError, match="item 8 cannot pass"):
        finalize_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
            public_bundle=invalid_public,
        )
    assert not invalid_public.exists()
    complete_review(review_path=review_path)
    first_count = finalize_review_bundle(
        runs_root=runs_root,
        matrix_path=matrix_path,
        schedules_root=schedules_root,
        ledger_path=ledger_path,
        rubric_source_path=RUBRIC_SOURCE,
        review_bundle=review_bundle,
        sealed_mapping_path=mapping_path,
        public_bundle=first_public,
    )
    second_count = finalize_review_bundle(
        runs_root=runs_root,
        matrix_path=matrix_path,
        schedules_root=schedules_root,
        ledger_path=ledger_path,
        rubric_source_path=RUBRIC_SOURCE,
        review_bundle=review_bundle,
        sealed_mapping_path=mapping_path,
        public_bundle=second_public,
    )
    assert first_count == second_count == 96
    first_files = {
        path.relative_to(first_public).as_posix(): path.read_bytes()
        for path in first_public.rglob(pattern="*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second_public).as_posix(): path.read_bytes()
        for path in second_public.rglob(pattern="*")
        if path.is_file()
    }
    assert first_files == second_files
    public_item_rows = [
        json.loads(line)
        for line in (first_public / "item-review.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    item_six_rationales = [
        row["rationale"]
        for row in public_item_rows
        if row["item_id"] == "artifacts_and_offline_scripts"
    ]
    assert any(
        rationale.startswith("No applicable scripts: Cited artifacts verified:")
        for rationale in item_six_rationales
    )
    assert all("Offline command:" not in rationale for rationale in item_six_rationales)
    item_eight_statuses = {
        row["status"]
        for row in public_item_rows
        if row["item_id"] == "no_unavailable_access"
    }
    assert item_eight_statuses == {"not_applicable", "partial"}
    assert not any(
        path.name.startswith(".first.staging-")
        or path.name.startswith(".second.staging-")
        for path in public_parent.iterdir()
    )
    provenance = PublicProvenance.model_validate_json(
        (first_public / "provenance.json").read_bytes()
    )
    assert provenance.sealed_mapping_sha256 == f"sha256:{digest_file(path=mapping_path)}"
    assert provenance.ledger_sha256 == f"sha256:{digest_file(path=ledger_path)}"
    assert provenance.matrix_sha256 == f"sha256:{digest_file(path=matrix_path)}"
    assert provenance.rubric_source_sha256 == f"sha256:{digest_file(path=RUBRIC_SOURCE)}"
    assert len(provenance.runs) == 12
    assert len(provenance.campaign_attempts) == 13
    excluded_attempts = [
        attempt
        for attempt in provenance.campaign_attempts
        if not attempt.included_in_review
    ]
    assert len(excluded_attempts) == 1
    assert excluded_attempts[0].run_status is RunStatus.PROVIDER_FAILURE
    assert not excluded_attempts[0].infrastructure_valid
    assert {run.integrity.run_id for run in provenance.runs} == {
        packet.run_id for packet in mapping.packets
    }
    for public_file in provenance.public_files:
        assert public_file.sha256 == f"sha256:{digest_file(path=first_public / public_file.name)}"
    assert (first_public / "ARTIFACT_REVIEW.md").read_bytes() == RUBRIC_SOURCE.read_bytes()


def test_incomplete_schedule_and_rubric_drift_fail_before_publication(
    tmp_path: Path,
) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    rows = write_stage_schedule(schedules_root=schedules_root, stage="core-n3")
    task, system, replicate, stage = rows[0]
    write_synthetic_run(
        runs_root=runs_root,
        ledger=ledger,
        stage=stage,
        task=task,
        system=system,
        replicate=replicate,
        attempt=1,
        status=RunStatus.COMPLETED,
        start_time_override="2026-07-12T01:01:00Z",
        end_time_override="2026-07-12T01:01:20Z",
    )
    review_bundle, mapping_path, _ = bundle_locations(root=tmp_path)
    with pytest.raises(ValueError, match="launch prefix is incomplete"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
        )
    assert not review_bundle.exists()
    assert not mapping_path.exists()

    drifted_rubric = tmp_path / "drifted-rubric.md"
    drifted_rubric.write_bytes(RUBRIC_SOURCE.read_bytes() + b"\nDrift.\n")
    with pytest.raises(ValueError, match="rubric drifted"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=drifted_rubric,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
        )
    assert not review_bundle.exists()
    assert not mapping_path.exists()


def test_complete_n3_n5_and_ablation_campaign_selects_all_attempts(
    tmp_path: Path,
) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    materialize_complete_all_stage_campaign(
        runs_root=runs_root,
        schedules_root=schedules_root,
        ledger=ledger,
    )
    review_bundle, mapping_path, _ = bundle_locations(root=tmp_path)
    packet_count = prepare_review_bundle(
        runs_root=runs_root,
        matrix_path=matrix_path,
        schedules_root=schedules_root,
        ledger_path=ledger_path,
        rubric_source_path=RUBRIC_SOURCE,
        review_bundle=review_bundle,
        sealed_mapping_path=mapping_path,
    )
    mapping = SealedMapping.model_validate_json(mapping_path.read_bytes())
    assert packet_count == 26
    assert len(mapping.packets) == 26
    assert [schedule.stage for schedule in mapping.schedules] == [
        "core-n3",
        "core-extend-n5",
        "nstf-duty-ablation-n3",
    ]
    assert all(schedule.integrity.complete_launch_prefix for schedule in mapping.schedules)


def test_mapping_location_and_no_follow_destinations_are_refused(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    materialize_complete_n3_campaign(
        runs_root=runs_root,
        schedules_root=schedules_root,
        ledger=ledger,
    )
    review_parent = tmp_path / "review"
    review_parent.mkdir()
    review_bundle = review_parent / "bundle"
    mapping_inside_parent = review_parent / "mapping.json"
    with pytest.raises(ValueError, match="outside protected directory"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_inside_parent,
        )

    external_mapping = tmp_path / "external-private"
    external_mapping.mkdir()
    review_bundle.symlink_to(target=review_parent / "missing-bundle")
    with pytest.raises(ValueError, match="must not already exist"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=external_mapping / "mapping.json",
        )
    review_bundle.unlink()

    private_parent = tmp_path / "private"
    private_parent.mkdir()
    symlink_mapping = private_parent / "mapping.json"
    symlink_mapping.symlink_to(target=private_parent / "missing.json")
    with pytest.raises(ValueError, match="must not already exist"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=symlink_mapping,
        )
    assert not review_bundle.exists()


def test_explicit_identity_fails_closed(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    materialize_complete_n3_campaign(
        runs_root=runs_root,
        schedules_root=schedules_root,
        ledger=ledger,
    )
    leaky_run, manifest = next(
        (path, candidate_manifest)
        for path in runs_root.iterdir()
        for candidate_manifest in (
            load_single_jsonl(
                path=path / "manifest.jsonl",
                model_type=RunManifest,
            ),
        )
        if candidate_manifest.system == "codex"
        and candidate_manifest.status is RunStatus.COMPLETED
    )
    rewrite_attempt_output(
        run_directory=leaky_run,
        status=RunStatus.COMPLETED,
        classification="complete",
        served_models=manifest.served_models,
        note_contents=b"Produced by CODEX using GPT-5.6-SOL.\n",
    )
    review_bundle, mapping_path, _ = bundle_locations(root=tmp_path)
    with pytest.raises(ValueError, match="explicit run/system/model identity"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
        )
    assert not review_bundle.exists()
    assert not mapping_path.exists()


def test_credential_like_submitted_output_fails_closed(tmp_path: Path) -> None:
    runs_root, matrix_path, ledger_path, ledger = prepare_repository(root=tmp_path)
    schedules_root = tmp_path / "schedules"
    materialize_complete_n3_campaign(
        runs_root=runs_root,
        schedules_root=schedules_root,
        ledger=ledger,
    )
    leaky_run, manifest = next(
        (path, candidate_manifest)
        for path in runs_root.iterdir()
        for candidate_manifest in (
            load_single_jsonl(
                path=path / "manifest.jsonl",
                model_type=RunManifest,
            ),
        )
        if candidate_manifest.status is RunStatus.COMPLETED
    )
    rewrite_attempt_output(
        run_directory=leaky_run,
        status=RunStatus.COMPLETED,
        classification="complete",
        served_models=manifest.served_models,
        note_contents=(
            b"codex accidentally copied "
            b"access_token=synthetic_token_value_123456789\n"
        ),
    )
    review_bundle, mapping_path, _ = bundle_locations(root=tmp_path)

    with pytest.raises(ValueError, match="credential-like material"):
        prepare_review_bundle(
            runs_root=runs_root,
            matrix_path=matrix_path,
            schedules_root=schedules_root,
            ledger_path=ledger_path,
            rubric_source_path=RUBRIC_SOURCE,
            review_bundle=review_bundle,
            sealed_mapping_path=mapping_path,
        )
    assert not review_bundle.exists()
    assert not mapping_path.exists()
