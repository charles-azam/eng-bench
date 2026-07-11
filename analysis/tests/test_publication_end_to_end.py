from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from analysis.harvest import harvest
from analysis.integrity import ARTIFACT_PATHS
from analysis.models import DatasetName
from analysis.publication import build_parser, generate_publication_tables
from analysis.tests.test_harvest_end_to_end import (
    canonical_json,
    digest_file,
    synthetic_ledger,
    write_matrix,
    write_stage_schedule,
    write_synthetic_run,
)
from eng_bench.integrity import evaluator_manifest_sha256, sha256_bytes
from eng_bench.io import load_jsonl, write_json, write_jsonl
from eng_bench.models import (
    EvaluationSummary,
    FrozenLedger,
    Measurement,
    Prediction,
    RunManifest,
    RunStatus,
    Score,
)
from eng_bench.scoring import aggregate_task, evaluate


REPO_ROOT = Path(__file__).resolve().parents[2]
MEASUREMENTS_PATH = REPO_ROOT / "measurements/held_out.jsonl"
EVALUATOR_MANIFEST_PATH = REPO_ROOT / "protocol/evaluator_manifest.sha256"
BASE_TIME = datetime(year=2026, month=7, day=12, hour=1, tzinfo=UTC)


class FixturePaths(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: Path
    raw: Path
    matrix: Path
    schedules: Path
    ledger: Path
    harvest: Path
    evaluation: Path
    retried_run_id: str


def iso_z(*, value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def write_ledger(*, path: Path) -> FrozenLedger:
    ledger = synthetic_ledger().model_copy(
        update={
            "evaluator_manifest_sha256": evaluator_manifest_sha256(
                manifest_path=EVALUATOR_MANIFEST_PATH
            )
        }
    )
    path.write_text(
        f"{canonical_json(value=ledger.model_dump(mode='json'))}\n",
        encoding="utf-8",
    )
    return ledger


def rewrite_artifact_ledger(*, run_directory: Path) -> None:
    run_id = run_directory.name
    contents = "".join(
        f"{digest_file(path=run_directory / relative_path)}  "
        f"/root/bench-v2/runs/{run_id}/{relative_path}\n"
        for relative_path in ARTIFACT_PATHS
    )
    (run_directory / "artifact.sha256").write_text(contents, encoding="utf-8")


def exact_prediction(*, run_id: str, task_variant: str) -> Prediction:
    if task_variant == "nstf_blind_derive_duty":
        return Prediction(
            run_id=run_id,
            metric_id="nstf.baseline.thermal_duty_to_loop_kw",
            point=56.12,
            p10=50.0,
            p50=56.12,
            p90=62.0,
            units="kW",
            confidence=0.8,
            source_artifact=f"{run_id}/workspace/output/calculation_note.md",
        )
    return Prediction(
        run_id=run_id,
        metric_id="triso.a1.failure_count",
        point=0.0,
        p10=0.0,
        p50=0.0,
        p90=1.0,
        units="count",
        confidence=0.8,
        source_artifact=f"{run_id}/workspace/output/calculation_note.md",
    )


def replace_completed_predictions(*, runs_root: Path) -> None:
    for run_directory in sorted(runs_root.iterdir(), key=lambda path: path.name):
        manifest = RunManifest.model_validate_json(
            (run_directory / "manifest.jsonl").read_text(encoding="utf-8")
        )
        if manifest.status is not RunStatus.COMPLETED:
            continue
        prediction = exact_prediction(
            run_id=manifest.run_id,
            task_variant=manifest.task_variant,
        )
        (run_directory / "predictions.jsonl").write_text(
            f"{canonical_json(value=prediction.model_dump(mode='json'))}\n",
            encoding="utf-8",
        )
        rewrite_artifact_ledger(run_directory=run_directory)


def prepare_fixture(*, root: Path) -> FixturePaths:
    root.mkdir(parents=True, exist_ok=True)
    raw = root / "raw"
    raw.mkdir()
    matrix = root / "matrix.tsv"
    schedules = root / "schedules"
    ledger_path = root / "ledger.json"
    harvest_output = root / "harvest"
    evaluation_output = root / "evaluation"
    write_matrix(path=matrix)
    ledger = write_ledger(path=ledger_path)
    schedule_rows = write_stage_schedule(
        schedules_root=schedules,
        stage="core-n3",
        include_vps_sidecar=True,
    )
    retried_identity = schedule_rows[0]
    retried_run_id = ""
    for sequence, (task, system, replicate, stage) in enumerate(
        schedule_rows, start=1
    ):
        started_at = BASE_TIME + timedelta(minutes=sequence)
        is_retry = (task, system, replicate, stage) == retried_identity
        write_synthetic_run(
            runs_root=raw,
            ledger=ledger,
            stage=stage,
            task=task,
            system=system,
            replicate=replicate,
            attempt=1,
            status=(
                RunStatus.PROVIDER_FAILURE if is_retry else RunStatus.COMPLETED
            ),
            start_time_override=iso_z(value=started_at),
            end_time_override=iso_z(value=started_at + timedelta(seconds=20)),
        )
        if is_retry:
            retry_directory = write_synthetic_run(
                runs_root=raw,
                ledger=ledger,
                stage=stage,
                task=task,
                system=system,
                replicate=replicate,
                attempt=2,
                status=RunStatus.COMPLETED,
                start_time_override=iso_z(
                    value=started_at + timedelta(seconds=21)
                ),
                end_time_override=iso_z(
                    value=started_at + timedelta(seconds=40)
                ),
            )
            retried_run_id = retry_directory.name
    replace_completed_predictions(runs_root=raw)
    report = harvest(
        runs_root=raw,
        matrix_path=matrix,
        ledger_path=ledger_path,
        output_directory=harvest_output,
        schedules_root=schedules,
    )
    assert next(
        item for item in report.datasets if item.dataset is DatasetName.N3
    ).eligible

    manifests = load_jsonl(
        path=harvest_output / "n3/manifests.jsonl",
        model_type=RunManifest,
    )
    predictions = load_jsonl(
        path=harvest_output / "n3/predictions.jsonl",
        model_type=Prediction,
    )
    measurements = load_jsonl(
        path=MEASUREMENTS_PATH,
        model_type=Measurement,
    )
    result = evaluate(
        manifests=manifests,
        predictions=predictions,
        measurements=measurements,
        artifact_root=raw,
        ledger=ledger,
    )
    evaluation_output.mkdir()
    write_jsonl(
        path=evaluation_output / "scores.jsonl",
        models=list(result.scores),
    )
    write_json(path=evaluation_output / "summary.json", model=result.summary)
    return FixturePaths(
        root=root,
        raw=raw,
        matrix=matrix,
        schedules=schedules,
        ledger=ledger_path,
        harvest=harvest_output,
        evaluation=evaluation_output,
        retried_run_id=retried_run_id,
    )


def generate(
    *,
    fixture: FixturePaths,
    output: Path,
    dataset: DatasetName = DatasetName.N3,
    measurements_path: Path = MEASUREMENTS_PATH,
) -> None:
    generate_publication_tables(
        dataset=dataset,
        manifests_path=fixture.harvest / "n3/manifests.jsonl",
        predictions_path=fixture.harvest / "n3/predictions.jsonl",
        measurements_path=measurements_path,
        scores_path=fixture.evaluation / "scores.jsonl",
        summary_path=fixture.evaluation / "summary.json",
        attempts_path=fixture.harvest / "attempts.csv",
        schedule_integrity_path=fixture.harvest / "schedule_integrity.jsonl",
        eligibility_path=fixture.harvest / "eligibility.json",
        matrix_path=fixture.matrix,
        schedules_root=fixture.schedules,
        runs_root=fixture.raw,
        artifact_root=fixture.raw,
        ledger_path=fixture.ledger,
        evaluator_manifest_path=EVALUATOR_MANIFEST_PATH,
        evaluator_root=REPO_ROOT,
        output_directory=output,
    )


def output_snapshot(*, root: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(root.iterdir(), key=lambda item: item.name)
        if path.is_file()
    }


def read_csv(*, path: Path) -> list[dict[str, str]]:
    with path.open(mode="r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_full_n3_publication_is_deterministic_bound_and_replicate_complete(
    tmp_path: Path,
) -> None:
    fixture = prepare_fixture(root=tmp_path / "fixture")
    relocated_fixture = prepare_fixture(root=tmp_path / "relocated-fixture")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(fixture=fixture, output=first)
    generate(fixture=relocated_fixture, output=second)
    assert output_snapshot(root=first) == output_snapshot(root=second)
    assert set(output_snapshot(root=first)) == {
        "cell_status.csv",
        "chart_data.json",
        "claims.json",
        "provenance.json",
        "replicate_metrics.csv",
        "run_status.csv",
        "sha256_manifest.json",
        "task_metric_summary.csv",
    }

    run_rows = read_csv(path=first / "run_status.csv")
    assert len(run_rows) == 13
    retry_rows = [
        row
        for row in run_rows
        if row["run_id"].removesuffix("-a01").removesuffix("-a02")
        == fixture.retried_run_id.removesuffix("-a02")
    ]
    assert [row["physical_attempt"] for row in retry_rows] == ["1", "2"]
    assert [row["status"] for row in retry_rows] == [
        "provider_failure",
        "completed",
    ]

    claims = json.loads((first / "claims.json").read_text(encoding="utf-8"))
    assert claims["scheduled_replicates"] == 12
    assert claims["eligible_replicates"] == 12
    assert claims["physical_attempts"] == 13
    assert claims["retries"] == 1
    assert len(claims["cells"]) == 4

    metric_rows = read_csv(path=first / "replicate_metrics.csv")
    assert any(row["prediction_present"] == "false" for row in metric_rows)
    assert any(row["scorable"] == "false" for row in metric_rows)
    assert any(row["measurement_required"] == "false" for row in metric_rows)
    assert {
        row["dependency_group"] for row in metric_rows if row["dependency_group"]
    }

    summaries = read_csv(path=first / "task_metric_summary.csv")
    summary_row = next(
        row
        for row in summaries
        if row["task_variant"] == "nstf_blind_derive_duty"
        and row["system"] == "codex"
        and row["metric_id"] == "nstf.baseline.thermal_duty_to_loop_kw"
    )
    assert summary_row["measurement_required"] == "true"
    assert summary_row["evidence_class"] == "derived_measurement"
    assert summary_row["dependency_group"] == "nstf_run011_energy_balance"
    assert summary_row["units"] == "kW"
    assert "ANL-ART-47" in summary_row["measurement_provenance"]
    matching_rows = [
        row
        for row in metric_rows
        if row["task_variant"] == summary_row["task_variant"]
        and row["system"] == summary_row["system"]
        and row["metric_id"] == summary_row["metric_id"]
        and row["scorable"] == "true"
        and row["prediction_interval_covered"]
    ]
    assert int(summary_row["prediction_interval_coverage_denominator"]) == len(
        matching_rows
    )
    assert int(summary_row["prediction_interval_coverage_numerator"]) == sum(
        row["prediction_interval_covered"] == "true" for row in matching_rows
    )

    provenance = json.loads(
        (first / "provenance.json").read_text(encoding="utf-8")
    )
    assert provenance["dataset_gate"] == {
        "actual_cells": 4,
        "actual_scheduled_replicates": 12,
        "dataset": "n3",
        "eligible": True,
        "required_cells": 4,
        "required_replicates_per_cell": 3,
        "stages": ["core-n3"],
    }
    source_roles = {item["role"] for item in provenance["source_hashes"]}
    assert {
        "ledger",
        "evaluator_manifest",
        "matrix",
        "eligibility",
        "attempts",
        "manifests",
        "predictions",
        "measurements",
        "scores",
        "summary",
        "schedule_integrity",
        "raw_integrity_snapshot",
    }.issubset(source_roles)
    source_paths = {
        item["role"]: item["path"] for item in provenance["source_hashes"]
    }
    assert source_paths["ledger"] == "protocol/evaluation_ledger.json"
    assert source_paths["measurements"] == "measurements/held_out.jsonl"
    assert source_paths["eligibility"] == "harvested/eligibility.json"
    assert source_paths["attempts"] == "harvested/attempts.csv"
    assert source_paths["schedule_integrity"] == (
        "harvested/schedule_integrity.jsonl"
    )
    assert source_paths["manifests"] == "harvested/n3/manifests.jsonl"
    assert source_paths["scores"] == "evaluation/n3/scores.jsonl"
    assert source_paths["raw_integrity_snapshot"] == (
        "raw/<verified-integrity-snapshot>"
    )
    assert all(str(tmp_path) not in path for path in source_paths.values())
    hash_manifest = json.loads(
        (first / "sha256_manifest.json").read_text(encoding="utf-8")
    )
    assert hash_manifest["self_excluded_path"] == "sha256_manifest.json"
    for record in hash_manifest["output_hashes"]:
        assert record["sha256"] == sha256_bytes(
            value=(first / record["path"]).read_bytes()
        )


def recompute_summary_from_scores(
    *, manifests: list[RunManifest], scores: list[Score]
) -> EvaluationSummary:
    manifests_by_task: dict[tuple[str, str], list[RunManifest]] = defaultdict(list)
    scores_by_task: dict[tuple[str, str], list[Score]] = defaultdict(list)
    for manifest in manifests:
        manifests_by_task[(manifest.system, manifest.task_variant)].append(manifest)
    for score in scores:
        scores_by_task[(score.system, score.task_variant)].append(score)
    return EvaluationSummary(
        benchmark_versions=sorted(
            {manifest.benchmark_version for manifest in manifests}
        ),
        total_attempts=len(manifests),
        task_results=[
            aggregate_task(
                system=system,
                task_variant=task_variant,
                manifests=manifests_by_task[(system, task_variant)],
                scores=scores_by_task[(system, task_variant)],
            )
            for system, task_variant in sorted(manifests_by_task)
        ],
    )


def test_independent_recomputation_rejects_joint_score_summary_tampering_and_artifact_loss(
    tmp_path: Path,
) -> None:
    tampered = prepare_fixture(root=tmp_path / "tampered")
    scores = load_jsonl(
        path=tampered.evaluation / "scores.jsonl",
        model_type=Score,
    )
    manifests = load_jsonl(
        path=tampered.harvest / "n3/manifests.jsonl",
        model_type=RunManifest,
    )
    target_index = next(
        index
        for index, score in enumerate(scores)
        if score.scorable and score.absolute_log_error is not None
    )
    scores[target_index] = scores[target_index].model_copy(
        update={"absolute_log_error": 999.0, "issues": ["tampered"]}
    )
    write_jsonl(path=tampered.evaluation / "scores.jsonl", models=scores)
    write_json(
        path=tampered.evaluation / "summary.json",
        model=recompute_summary_from_scores(manifests=manifests, scores=scores),
    )
    with pytest.raises(ValueError, match="independent exact recomputation"):
        generate(fixture=tampered, output=tmp_path / "tampered-output")
    assert not (tmp_path / "tampered-output").exists()

    deleted = prepare_fixture(root=tmp_path / "deleted")
    completed_manifest = next(
        manifest
        for manifest in load_jsonl(
            path=deleted.harvest / "n3/manifests.jsonl",
            model_type=RunManifest,
        )
        if manifest.status is RunStatus.COMPLETED
    )
    (deleted.raw / completed_manifest.artifact_paths[-1]).unlink()
    with pytest.raises(ValueError, match="file-set mismatch|checksum mismatch"):
        generate(fixture=deleted, output=tmp_path / "deleted-output")
    assert not (tmp_path / "deleted-output").exists()


def test_gate_measurement_schedule_and_retry_integrity_fail_closed(
    tmp_path: Path,
) -> None:
    mislabeled = prepare_fixture(root=tmp_path / "mislabeled")
    with pytest.raises(ValueError, match="chosen dataset gate is ineligible"):
        generate(
            fixture=mislabeled,
            output=tmp_path / "mislabeled-output",
            dataset=DatasetName.N5,
        )

    alternate = prepare_fixture(root=tmp_path / "alternate")
    alternate_measurements = alternate.root / "alternate-measurements.jsonl"
    alternate_measurements.write_bytes(MEASUREMENTS_PATH.read_bytes())
    with pytest.raises(ValueError, match="measurements path must resolve"):
        generate(
            fixture=alternate,
            output=tmp_path / "alternate-output",
            measurements_path=alternate_measurements,
        )

    reordered = prepare_fixture(root=tmp_path / "reordered")
    schedule_path = reordered.schedules / "core-n3.tsv"
    lines = schedule_path.read_text(encoding="utf-8").splitlines()
    first_row = lines[1].split("\t")
    second_row = lines[2].split("\t")
    lines[1] = "\t".join([first_row[0], *second_row[1:]])
    lines[2] = "\t".join([second_row[0], *first_row[1:]])
    schedule_path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    digest = digest_file(path=schedule_path)
    (reordered.schedules / "core-n3.tsv.sha256").write_text(
        f"{digest}  core-n3.tsv\n",
        encoding="utf-8",
    )
    (reordered.schedules / "core-n3.tsv.vps.sha256").write_text(
        f"{digest}  /root/bench-v2/schedules/core-n3.tsv\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="rows/order"):
        generate(fixture=reordered, output=tmp_path / "reordered-output")

    chronology = prepare_fixture(root=tmp_path / "chronology")
    with (chronology.schedules / "core-n3.tsv").open(
        mode="r", encoding="utf-8", newline=""
    ) as stream:
        scheduled_rows = list(csv.DictReader(stream, delimiter="\t"))
    first_run_id = (
        f"core-n3-{scheduled_rows[0]['task']}-{scheduled_rows[0]['system']}"
        f"-r{int(scheduled_rows[0]['replicate']):02d}-a01"
    )
    second_run_id = (
        f"core-n3-{scheduled_rows[1]['task']}-{scheduled_rows[1]['system']}"
        f"-r{int(scheduled_rows[1]['replicate']):02d}-a01"
    )
    first_start = json.loads(
        (chronology.raw / first_run_id / "metadata.json").read_text(
            encoding="utf-8"
        )
    )["start_time"]
    second_directory = chronology.raw / second_run_id
    second_metadata_path = second_directory / "metadata.json"
    second_metadata = json.loads(
        second_metadata_path.read_text(encoding="utf-8")
    )
    second_metadata["start_time"] = first_start
    second_metadata_path.write_text(
        f"{canonical_json(value=second_metadata)}\n",
        encoding="utf-8",
    )
    second_manifest_path = second_directory / "manifest.jsonl"
    second_manifest = json.loads(
        second_manifest_path.read_text(encoding="utf-8")
    )
    second_manifest["started_at"] = first_start
    second_manifest_path.write_text(
        f"{canonical_json(value=second_manifest)}\n",
        encoding="utf-8",
    )
    rewrite_artifact_ledger(run_directory=second_directory)
    with pytest.raises(ValueError, match="chronology violates schedule order"):
        generate(fixture=chronology, output=tmp_path / "chronology-output")

    retry_drift = prepare_fixture(root=tmp_path / "retry-drift")
    retry_directory = retry_drift.raw / retry_drift.retried_run_id
    metadata_path = retry_directory / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["protocol_manifest_sha256"] = "0" * 64
    metadata_path.write_text(
        f"{canonical_json(value=metadata)}\n",
        encoding="utf-8",
    )
    rewrite_artifact_ledger(run_directory=retry_directory)
    with pytest.raises(ValueError, match="retry changed frozen inputs"):
        generate(fixture=retry_drift, output=tmp_path / "retry-drift-output")

    lone_failure = prepare_fixture(root=tmp_path / "lone-failure")
    retry_directory = lone_failure.raw / lone_failure.retried_run_id
    for path in sorted(
        retry_directory.rglob(pattern="*"),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    retry_directory.rmdir()
    with pytest.raises(ValueError, match="not retried exactly once"):
        generate(fixture=lone_failure, output=tmp_path / "lone-failure-output")


def test_retry_overlap_existing_output_symlink_and_cli_contract(
    tmp_path: Path,
) -> None:
    overlap = prepare_fixture(root=tmp_path / "overlap")
    retry_directory = overlap.raw / overlap.retried_run_id
    first_directory = Path(str(retry_directory).replace("-a02", "-a01"))
    first_metadata = json.loads(
        (first_directory / "metadata.json").read_text(encoding="utf-8")
    )
    retry_metadata_path = retry_directory / "metadata.json"
    retry_metadata = json.loads(retry_metadata_path.read_text(encoding="utf-8"))
    retry_metadata["start_time"] = first_metadata["start_time"]
    retry_metadata_path.write_text(
        f"{canonical_json(value=retry_metadata)}\n",
        encoding="utf-8",
    )
    manifest_path = retry_directory / "manifest.jsonl"
    retry_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    retry_manifest["started_at"] = first_metadata["start_time"]
    manifest_path.write_text(
        f"{canonical_json(value=retry_manifest)}\n",
        encoding="utf-8",
    )
    rewrite_artifact_ledger(run_directory=retry_directory)
    with pytest.raises(ValueError, match="retry started before"):
        generate(fixture=overlap, output=tmp_path / "overlap-output")

    existing = prepare_fixture(root=tmp_path / "existing")
    existing_output = tmp_path / "existing-output"
    generate(fixture=existing, output=existing_output)
    with pytest.raises(ValueError, match="already exists"):
        generate(fixture=existing, output=existing_output)

    symlink_output = tmp_path / "symlink-output"
    symlink_output.symlink_to(target=tmp_path / "missing-target", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        generate(fixture=existing, output=symlink_output)

    required_flags = {
        action.dest
        for action in build_parser()._actions
        if action.required
    }
    assert {
        "dataset",
        "manifests",
        "predictions",
        "measurements",
        "scores",
        "summary",
        "attempts",
        "schedule_integrity",
        "eligibility",
        "matrix",
        "schedules_root",
        "runs_root",
        "artifact_root",
        "ledger",
        "evaluator_manifest",
        "evaluator_root",
        "output_dir",
    }.issubset(required_flags)
    parsed = build_parser().parse_args(
        args=[
            "--dataset",
            "n3",
            "--manifests",
            str(existing.harvest / "n3/manifests.jsonl"),
            "--predictions",
            str(existing.harvest / "n3/predictions.jsonl"),
            "--measurements",
            str(MEASUREMENTS_PATH),
            "--scores",
            str(existing.evaluation / "scores.jsonl"),
            "--summary",
            str(existing.evaluation / "summary.json"),
            "--attempts",
            str(existing.harvest / "attempts.csv"),
            "--schedule-integrity",
            str(existing.harvest / "schedule_integrity.jsonl"),
            "--eligibility",
            str(existing.harvest / "eligibility.json"),
            "--matrix",
            str(existing.matrix),
            "--schedules-root",
            str(existing.schedules),
            "--runs-root",
            str(existing.raw),
            "--artifact-root",
            str(existing.raw),
            "--ledger",
            str(existing.ledger),
            "--evaluator-manifest",
            str(EVALUATOR_MANIFEST_PATH),
            "--evaluator-root",
            str(REPO_ROOT),
            "--output-dir",
            str(tmp_path / "cli-output"),
        ]
    )
    assert parsed.dataset == "n3"
