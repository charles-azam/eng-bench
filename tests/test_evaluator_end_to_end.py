from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from eng_bench.integrity import evaluator_manifest_sha256
from eng_bench.io import write_json, write_jsonl
from eng_bench.models import (
    EvidenceClass,
    FrozenLedger,
    FrozenSystem,
    Measurement,
    MeasurementKind,
    Prediction,
    QualitativeAssessment,
    RunManifest,
    RunStatus,
    Score,
)
from eng_bench.task_output import TaskOutput
from eng_bench.units import can_convert_units


SHA_A = f"sha256:{'a' * 64}"
SHA_B = f"sha256:{'b' * 64}"
SHA_C = f"sha256:{'c' * 64}"
STARTED_AT = datetime(2026, 7, 12, 0, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_MANIFEST_PATH = REPO_ROOT / "protocol/evaluator_manifest.sha256"


def make_manifest(
    *,
    run_id: str,
    task_variant: str,
    system: str,
    status: RunStatus,
    attempt: int,
    artifact_paths: list[str],
) -> RunManifest:
    requested_model = "gpt-test" if system.startswith("codex") else "claude-test"
    cli_version = "codex-test-cli" if system.startswith("codex") else "claude-test-cli"
    return RunManifest(
        run_id=run_id,
        benchmark_version="2026-07-preregistered",
        task_variant=task_variant,
        system=system,
        requested_model=requested_model,
        served_models=(
            []
            if status in {RunStatus.PROVIDER_FAILURE, RunStatus.RUNNER_FAILURE}
            else [requested_model]
        ),
        cli_version=cli_version,
        effort="max",
        started_at=STARTED_AT + timedelta(minutes=attempt),
        ended_at=STARTED_AT + timedelta(minutes=attempt + 1),
        attempt=attempt,
        status=status,
        prompt_sha256=SHA_A,
        pack_sha256=SHA_B,
        runner_image_sha256=SHA_C,
        trace_path=f"{run_id}/trace.jsonl",
        artifact_paths=artifact_paths,
    )


def make_ledger(*, manifests: list[RunManifest]) -> FrozenLedger:
    first = manifests[0]
    return FrozenLedger(
        benchmark_version=first.benchmark_version,
        prompt_sha256=first.prompt_sha256,
        runner_image_sha256=first.runner_image_sha256,
        evaluator_manifest_sha256=evaluator_manifest_sha256(
            manifest_path=EVALUATOR_MANIFEST_PATH
        ),
        task_pack_sha256={
            manifest.task_variant: manifest.pack_sha256 for manifest in manifests
        },
        systems={
            manifest.system: FrozenSystem(
                requested_model=manifest.requested_model,
                cli_version=manifest.cli_version,
                effort=manifest.effort,
            )
            for manifest in manifests
        },
    )


def materialize_run(*, artifact_root: Path, manifest: RunManifest) -> None:
    trace_path = artifact_root / manifest.trace_path
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text('{"event":"complete"}\n', encoding="utf-8")
    for relative_path in manifest.artifact_paths:
        artifact_path = artifact_root / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("auditable calculation\n", encoding="utf-8")


def run_cli(
    *,
    manifests_path: Path,
    predictions_path: Path,
    measurements_path: Path,
    ledger_path: Path,
    artifact_root: Path,
    output_dir: Path,
) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "eng_bench",
            "evaluate",
            "--manifests",
            str(manifests_path),
            "--predictions",
            str(predictions_path),
            "--measurements",
            str(measurements_path),
            "--ledger",
            str(ledger_path),
            "--evaluator-manifest",
            str(EVALUATOR_MANIFEST_PATH),
            "--evaluator-root",
            str(REPO_ROOT),
            "--artifact-root",
            str(artifact_root),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
    )


def load_scores(*, path: Path) -> list[Score]:
    return [
        Score.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_task_output_normalization_enforces_the_frozen_agent_contract(
    tmp_path: Path,
) -> None:
    task_output_path = tmp_path / "predictions.json"
    normalized_path = tmp_path / "normalized.jsonl"
    task_output_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "task_id": "nstf_blind_derive_duty",
                "predictions": [
                    {
                        "metric_id": "nstf.baseline.mass_flow_kg_s",
                        "point": 0.57,
                        "p10": 0.45,
                        "p50": 0.57,
                        "p90": 0.72,
                        "units": "kg/s",
                        "confidence": 0.7,
                        "qualitative": None,
                        "category": None,
                        "source_artifact": "output/calculation_note.md",
                    },
                    {
                        "metric_id": "nstf.accident.response_through_peak",
                        "point": None,
                        "p10": None,
                        "p50": None,
                        "p90": None,
                        "units": "category",
                        "confidence": 0.6,
                        "qualitative": None,
                        "category": "bounded_through_peak",
                        "source_artifact": "output/calculation_note.md",
                    },
                ],
                "annex_sufficiency": {
                    "status": "partially_sufficient",
                    "missing_physics": ["parasitic structural heat losses"],
                    "consequence": "thermal duty dominates the uncertainty",
                },
                "most_uncertain_assumption": "heater-to-loop efficiency",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "eng_bench",
            "normalize",
            "--run-id",
            "codex-nstf-01",
            "--task-output",
            str(task_output_path),
            "--output",
            str(normalized_path),
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
    )
    normalized = [
        Prediction.model_validate_json(line)
        for line in normalized_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(normalized) == 2
    assert normalized[0].run_id == "codex-nstf-01"
    assert normalized[0].source_artifact == (
        "codex-nstf-01/workspace/output/calculation_note.md"
    )
    assert normalized[1].category == "bounded_through_peak"

    invalid = json.loads(task_output_path.read_text(encoding="utf-8"))
    invalid["predictions"][0]["source_artifact"] = "output/calculation_note.md#baseline"
    with pytest.raises(ValueError, match="plain relative path"):
        TaskOutput.model_validate(invalid)
    assert can_convert_units(from_units="K", to_units="degC") is False


def test_cli_pipeline_scores_units_zero_counts_and_failures_deterministically(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    manifests = [
        make_manifest(
            run_id="codex-nstf-01",
            task_variant="nstf-blind",
            system="codex-gpt-5.6-sol",
            status=RunStatus.COMPLETED,
            attempt=1,
            artifact_paths=["codex-nstf-01/calculation.md"],
        ),
        make_manifest(
            run_id="claude-nstf-01",
            task_variant="nstf-blind",
            system="claude-fable-5",
            status=RunStatus.AGENT_FAILURE,
            attempt=1,
            artifact_paths=[],
        ),
        RunManifest(
            run_id="claude-nstf-fallback-03",
            benchmark_version="2026-07-preregistered",
            task_variant="nstf-blind",
            system="claude-fable-5",
            requested_model="claude-test",
            served_models=["claude-test", "claude-opus-test"],
            cli_version="claude-test-cli",
            effort="max",
            started_at=STARTED_AT + timedelta(minutes=3),
            ended_at=STARTED_AT + timedelta(minutes=4),
            attempt=3,
            status=RunStatus.FALLBACK_CONTAMINATED,
            prompt_sha256=SHA_A,
            pack_sha256=SHA_B,
            runner_image_sha256=SHA_C,
            trace_path="claude-nstf-fallback-03/trace.jsonl",
            artifact_paths=["claude-nstf-fallback-03/calculation.md"],
        ),
        make_manifest(
            run_id="claude-nstf-provider-02",
            task_variant="nstf-blind",
            system="claude-fable-5",
            status=RunStatus.PROVIDER_FAILURE,
            attempt=2,
            artifact_paths=[],
        ),
        make_manifest(
            run_id="claude-nstf-refusal-04",
            task_variant="nstf-blind",
            system="claude-fable-5",
            status=RunStatus.REFUSAL,
            attempt=4,
            artifact_paths=[],
        ),
        make_manifest(
            run_id="codex-count-01",
            task_variant="synthetic-count-task",
            system="codex-gpt-5.6-sol",
            status=RunStatus.COMPLETED,
            attempt=1,
            artifact_paths=["codex-count-01/calculation.md"],
        ),
    ]
    materialize_run(artifact_root=artifact_root, manifest=manifests[0])
    materialize_run(artifact_root=artifact_root, manifest=manifests[2])
    materialize_run(artifact_root=artifact_root, manifest=manifests[5])

    predictions = [
        Prediction(
            run_id="codex-nstf-01",
            metric_id="thermal_duty",
            point=58.0,
            p10=52.0,
            p50=58.0,
            p90=63.0,
            units="kW",
            confidence=0.8,
            source_artifact="codex-nstf-01/calculation.md",
        ),
        Prediction(
            run_id="codex-nstf-01",
            metric_id="radiative_fraction",
            point=85.0,
            p10=75.0,
            p50=85.0,
            p90=95.0,
            units="%",
            confidence=0.7,
            qualitative=QualitativeAssessment.DOMINANT,
            source_artifact="codex-nstf-01/calculation.md",
        ),
        Prediction(
            run_id="codex-nstf-01",
            metric_id="bounded_through_peak",
            units="category",
            category="bounded",
            source_artifact="codex-nstf-01/calculation.md",
        ),
        Prediction(
            run_id="codex-count-01",
            metric_id="failed_particles",
            point=0.0,
            p10=0.0,
            p50=0.0,
            p90=1.0,
            units="count",
            confidence=0.9,
            source_artifact="codex-count-01/calculation.md",
        ),
        Prediction(
            run_id="claude-nstf-fallback-03",
            metric_id="thermal_duty",
            point=56.0,
            p10=55.0,
            p50=56.0,
            p90=57.0,
            units="kW",
            confidence=0.99,
            source_artifact="claude-nstf-fallback-03/calculation.md",
        ),
        Prediction(
            run_id="claude-nstf-01",
            metric_id="thermal_duty",
            point=56.0,
            units="kW",
            source_artifact="claude-nstf-01/partial.md",
        ),
    ]
    measurements = [
        Measurement(
            task_variant="nstf-blind",
            metric_id="thermal_duty",
            kind=MeasurementKind.POSITIVE,
            value=56_000.0,
            units="W",
            evidence_class=EvidenceClass.DERIVED_MEASUREMENT,
            dependency_group="nstf-baseline-energy-balance",
            provenance="NSTF data table",
        ),
        Measurement(
            task_variant="nstf-blind",
            metric_id="radiative_fraction",
            kind=MeasurementKind.RADIATION,
            lower=0.7,
            upper=0.9,
            units="fraction",
            expected_qualitative=QualitativeAssessment.DOMINANT,
            evidence_class=EvidenceClass.QUALITATIVE_STATEMENT,
            provenance="NSTF sensor synthesis",
        ),
        Measurement(
            task_variant="nstf-blind",
            metric_id="bounded_through_peak",
            kind=MeasurementKind.CATEGORICAL,
            units="category",
            expected_category="bounded",
            allowed_categories=["bounded", "exceeded", "indeterminate"],
            evidence_class=EvidenceClass.QUALITATIVE_STATEMENT,
            provenance="NSTF transient envelope",
        ),
        Measurement(
            task_variant="synthetic-count-task",
            metric_id="failed_particles",
            kind=MeasurementKind.COUNT,
            value=0.0,
            units="count",
            evidence_class=EvidenceClass.POSTCALC_ASSUMPTION,
            dependency_group="synthetic-kr-trace-a1",
            provenance="IAEA furnace result",
        ),
    ]

    manifests_path = tmp_path / "manifests.jsonl"
    predictions_path = tmp_path / "predictions.jsonl"
    measurements_path = tmp_path / "measurements.jsonl"
    ledger_path = tmp_path / "ledger.json"
    write_jsonl(path=manifests_path, models=manifests)
    write_jsonl(path=predictions_path, models=predictions)
    write_jsonl(path=measurements_path, models=measurements)
    write_json(path=ledger_path, model=make_ledger(manifests=manifests))

    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    run_cli(
        manifests_path=manifests_path,
        predictions_path=predictions_path,
        measurements_path=measurements_path,
        ledger_path=ledger_path,
        artifact_root=artifact_root,
        output_dir=first_output,
    )
    run_cli(
        manifests_path=manifests_path,
        predictions_path=predictions_path,
        measurements_path=measurements_path,
        ledger_path=ledger_path,
        artifact_root=artifact_root,
        output_dir=second_output,
    )

    assert (first_output / "scores.jsonl").read_bytes() == (
        second_output / "scores.jsonl"
    ).read_bytes()
    assert (first_output / "summary.json").read_bytes() == (
        second_output / "summary.json"
    ).read_bytes()

    frozen_ledger = make_ledger(manifests=manifests)
    write_json(
        path=ledger_path,
        model=frozen_ledger.model_copy(update={"evaluator_manifest_sha256": SHA_A}),
    )
    with pytest.raises(subprocess.CalledProcessError):
        run_cli(
            manifests_path=manifests_path,
            predictions_path=predictions_path,
            measurements_path=measurements_path,
            ledger_path=ledger_path,
            artifact_root=artifact_root,
            output_dir=tmp_path / "evaluator-manifest-drifted",
        )

    write_json(path=ledger_path, model=frozen_ledger)
    drifted_manifests = [
        manifests[0].model_copy(update={"runner_image_sha256": SHA_A}),
        *manifests[1:],
    ]
    write_jsonl(path=manifests_path, models=drifted_manifests)
    with pytest.raises(subprocess.CalledProcessError):
        run_cli(
            manifests_path=manifests_path,
            predictions_path=predictions_path,
            measurements_path=measurements_path,
            ledger_path=ledger_path,
            artifact_root=artifact_root,
            output_dir=tmp_path / "drifted",
        )

    scores = load_scores(path=first_output / "scores.jsonl")
    duty_score = next(
        score
        for score in scores
        if score.run_id == "codex-nstf-01" and score.metric_id == "thermal_duty"
    )
    assert duty_score.normalized_point == 58_000.0
    assert duty_score.absolute_log_error == pytest.approx(math.log(58_000.0 / 56_000.0))
    assert duty_score.signed_relative_error == pytest.approx(2_000.0 / 56_000.0)
    assert duty_score.prediction_interval_covered is True
    assert duty_score.artifact_valid is True
    assert duty_score.scorable is True
    assert duty_score.evidence_class is EvidenceClass.DERIVED_MEASUREMENT
    assert duty_score.dependency_group == "nstf-baseline-energy-balance"

    radiation_score = next(
        score
        for score in scores
        if score.run_id == "codex-nstf-01" and score.metric_id == "radiative_fraction"
    )
    assert radiation_score.normalized_point == pytest.approx(0.85)
    assert radiation_score.point_in_measurement_interval is True
    assert radiation_score.qualitative_passed is True

    categorical_score = next(
        score
        for score in scores
        if score.run_id == "codex-nstf-01" and score.metric_id == "bounded_through_peak"
    )
    assert categorical_score.categorical_passed is True
    assert categorical_score.scorable is True

    count_score = next(
        score
        for score in scores
        if score.run_id == "codex-count-01" and score.metric_id == "failed_particles"
    )
    assert count_score.count_log_error == 0.0
    assert count_score.signed_relative_error is None
    assert count_score.prediction_interval_covered is True

    agent_failure_scores = [
        score for score in scores if score.run_id == "claude-nstf-01"
    ]
    assert len(agent_failure_scores) == 3
    assert all(score.infrastructure_valid for score in agent_failure_scores)
    assert all(score.completion_passed is False for score in agent_failure_scores)
    assert all("run_status_agent_failure" in score.issues for score in agent_failure_scores)
    partial_failure_score = next(
        score for score in agent_failure_scores if score.metric_id == "thermal_duty"
    )
    assert partial_failure_score.absolute_log_error is None
    assert partial_failure_score.scorable is False

    provider_scores = [
        score for score in scores if score.run_id == "claude-nstf-provider-02"
    ]
    assert len(provider_scores) == 3
    assert all(score.infrastructure_valid is False for score in provider_scores)
    assert all("run_status_provider_failure" in score.issues for score in provider_scores)

    refusal_scores = [
        score for score in scores if score.run_id == "claude-nstf-refusal-04"
    ]
    assert len(refusal_scores) == 3
    assert all(score.infrastructure_valid for score in refusal_scores)
    assert all("run_status_refusal" in score.issues for score in refusal_scores)

    summary = json.loads((first_output / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_attempts"] == 6
    assert "overall_score" not in summary
    claude_summary = next(
        result
        for result in summary["task_results"]
        if result["system"] == "claude-fable-5"
    )
    assert claude_summary["attempts"] == 4
    assert claude_summary["infrastructure_valid_attempts"] == 3
    assert claude_summary["agent_failures"] == 1
    assert claude_summary["refusals"] == 1
    assert claude_summary["fallback_contaminated_attempts"] == 1
    assert claude_summary["provider_failures"] == 1
    assert claude_summary["metric_completion_rate"] == 0.0

    fallback_score = next(
        score
        for score in scores
        if score.run_id == "claude-nstf-fallback-03" and score.metric_id == "thermal_duty"
    )
    assert fallback_score.completion_passed is False
    assert fallback_score.infrastructure_valid is True
    assert fallback_score.compliance_passed is False
    assert fallback_score.scorable is False
    assert fallback_score.absolute_log_error is None
    assert fallback_score.weighted_interval_score is None
    assert "run_status_fallback_contaminated" in fallback_score.issues

    codex_nstf_summary = next(
        result
        for result in summary["task_results"]
        if result["system"] == "codex-gpt-5.6-sol"
        and result["task_variant"] == "nstf-blind"
    )
    categorical_summary = next(
        metric
        for metric in codex_nstf_summary["metrics"]
        if metric["metric_id"] == "bounded_through_peak"
    )
    assert categorical_summary["categorical_pass_rate"] == 1.0
    assert categorical_summary["mean_absolute_log_error"] is None


def test_pipeline_keeps_unverifiable_and_noncompliant_predictions_visible(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    manifest = make_manifest(
        run_id="codex-edge-01",
        task_variant="edge-cases",
        system="codex-gpt-5.6-sol",
        status=RunStatus.COMPLETED,
        attempt=1,
        artifact_paths=["codex-edge-01/units.md"],
    )
    materialize_run(artifact_root=artifact_root, manifest=manifest)
    missing_artifact_prediction = Prediction(
        run_id=manifest.run_id,
        metric_id="failures",
        point=4.0,
        p10=2.0,
        p50=4.0,
        p90=7.0,
        units="counts",
        source_artifact="codex-edge-01/not-published.md",
    )
    incompatible_prediction = Prediction(
        run_id=manifest.run_id,
        metric_id="power",
        point=56.0,
        units="count",
        source_artifact="codex-edge-01/units.md",
    )
    wrong_category_prediction = Prediction(
        run_id=manifest.run_id,
        metric_id="transient_state",
        units="category",
        category="exceeded",
        source_artifact="codex-edge-01/units.md",
    )
    release_prediction = Prediction(
        run_id=manifest.run_id,
        metric_id="fractional_release",
        point=0.1,
        p10=0.01,
        p50=0.1,
        p90=0.2,
        units="fraction",
        confidence=0.5,
        source_artifact="codex-edge-01/units.md",
    )
    temperature_prediction = Prediction(
        run_id=manifest.run_id,
        metric_id="plate_temperature",
        point=400.0,
        p10=380.0,
        p50=400.0,
        p90=420.0,
        units="degC",
        confidence=0.7,
        source_artifact="codex-edge-01/units.md",
    )
    measurements = [
        Measurement(
            task_variant="edge-cases",
            metric_id="failures",
            kind=MeasurementKind.COUNT,
            lower=0.0,
            upper=1.0,
            units="count",
            evidence_class=EvidenceClass.DIRECT_MEASUREMENT,
            provenance="held-out count interval",
        ),
        Measurement(
            task_variant="edge-cases",
            metric_id="power",
            kind=MeasurementKind.POSITIVE,
            value=56_000.0,
            units="W",
            evidence_class=EvidenceClass.DIRECT_MEASUREMENT,
            provenance="held-out thermal duty",
        ),
        Measurement(
            task_variant="edge-cases",
            metric_id="transient_state",
            kind=MeasurementKind.CATEGORICAL,
            units="category",
            expected_category="bounded",
            allowed_categories=["bounded", "exceeded", "indeterminate"],
            evidence_class=EvidenceClass.QUALITATIVE_STATEMENT,
            provenance="held-out transient classification",
        ),
        Measurement(
            task_variant="edge-cases",
            metric_id="fractional_release",
            kind=MeasurementKind.POSITIVE,
            value=0.05,
            units="fraction",
            evidence_class=EvidenceClass.DIRECT_MEASUREMENT,
            provenance="held-out fractional release",
        ),
        Measurement(
            task_variant="edge-cases",
            metric_id="plate_temperature",
            kind=MeasurementKind.ABSOLUTE_TEMPERATURE,
            value=390.0,
            units="degC",
            evidence_class=EvidenceClass.DIRECT_MEASUREMENT,
            provenance="held-out plate temperature",
        ),
    ]

    manifests_path = tmp_path / "manifests.jsonl"
    predictions_path = tmp_path / "predictions.jsonl"
    measurements_path = tmp_path / "measurements.jsonl"
    ledger_path = tmp_path / "ledger.json"
    write_jsonl(path=manifests_path, models=[manifest])
    write_jsonl(
        path=predictions_path,
        models=[
            missing_artifact_prediction,
            incompatible_prediction,
            wrong_category_prediction,
            release_prediction,
            temperature_prediction,
        ],
    )
    write_jsonl(path=measurements_path, models=measurements)
    write_json(path=ledger_path, model=make_ledger(manifests=[manifest]))
    output_dir = tmp_path / "output"
    run_cli(
        manifests_path=manifests_path,
        predictions_path=predictions_path,
        measurements_path=measurements_path,
        ledger_path=ledger_path,
        artifact_root=artifact_root,
        output_dir=output_dir,
    )

    scores = load_scores(path=output_dir / "scores.jsonl")
    count_score = next(score for score in scores if score.metric_id == "failures")
    assert count_score.count_log_error == pytest.approx(math.log10(5.0) - math.log10(2.0))
    assert count_score.point_in_measurement_interval is False
    assert count_score.artifact_valid is False
    assert count_score.scorable is False
    assert "artifact_missing_or_unlisted" in count_score.issues

    power_score = next(score for score in scores if score.metric_id == "power")
    assert power_score.completion_passed is True
    assert power_score.compliance_passed is False
    assert power_score.artifact_valid is True
    assert power_score.normalized_point is None
    assert power_score.scorable is False
    assert power_score.issues == ["incompatible_units"]

    category_score = next(score for score in scores if score.metric_id == "transient_state")
    assert category_score.completion_passed is True
    assert category_score.compliance_passed is True
    assert category_score.scorable is True
    assert category_score.categorical_passed is False

    release_score = next(
        score for score in scores if score.metric_id == "fractional_release"
    )
    assert release_score.weighted_interval_score == pytest.approx(
        0.4307645450908127
    )

    temperature_score = next(
        score for score in scores if score.metric_id == "plate_temperature"
    )
    assert temperature_score.absolute_error == 10.0
    assert temperature_score.signed_error == 10.0
    assert temperature_score.absolute_log_error is None
    assert temperature_score.signed_relative_error is None

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    task_summary = summary["task_results"][0]
    assert task_summary["metric_completion_rate"] == 1.0
    metric_summaries = {metric["metric_id"]: metric for metric in task_summary["metrics"]}
    assert metric_summaries["failures"]["artifact_validity_rate"] == 0.0
    assert metric_summaries["failures"]["scorable_predictions"] == 0
    assert metric_summaries["failures"]["mean_count_log_error"] is None
    assert metric_summaries["power"]["artifact_validity_rate"] == 1.0
    assert metric_summaries["power"]["scorable_predictions"] == 0
    assert metric_summaries["transient_state"]["categorical_pass_rate"] == 0.0
    assert metric_summaries["transient_state"]["mean_absolute_log_error"] is None
