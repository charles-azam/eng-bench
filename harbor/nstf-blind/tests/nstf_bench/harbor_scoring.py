"""Score one agent workspace against the held-out measurements, Harbor-style.

This is the light path used by the Harbor verifier: no frozen ledger, no runner
manifests — just "here is a workspace that should contain output/predictions.json;
score it". It reuses the deterministic per-metric scorer unchanged and reduces the
artifact check to "does the cited file exist under the workspace".

Fail-closed: score_task always produces reward.json, summary.json, and scores.jsonl.
A missing or malformed predictions file yields reward 0.0, never an exception.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median

from pydantic import Field, ValidationError

from nstf_bench.io import load_jsonl, write_json, write_jsonl
from nstf_bench.models import (
    Measurement,
    MeasurementKind,
    NonEmptyString,
    Prediction,
    RunManifest,
    RunStatus,
    Score,
    StrictModel,
)
from nstf_bench.scoring import empty_score, score_prediction
from nstf_bench.task_output import TaskOutput


HARBOR_RUN_ID = "harbor-run"
HARBOR_BENCHMARK_VERSION = "nstf-bench-harbor"
PLACEHOLDER_SHA256 = "sha256:" + "0" * 64
TEMPERATURE_ERROR_SCALE_K = 25.0
NETWORK_PATTERNS = (
    "WebFetch",
    "WebSearch",
    "curl ",
    "wget ",
    "pip install",
    "apt-get install",
    "osti.gov",
    "anl.gov",
)
MAX_NETWORK_MATCHES = 20


class MetricSummary(StrictModel):
    normalized_score: float
    scorable: bool
    issues: list[str] = Field(default_factory=list)


class HarborSummary(StrictModel):
    task_variant: NonEmptyString
    required_metrics: int
    predicted_metrics: int
    completion_rate: float
    compliance_rate: float
    artifact_validity_rate: float
    categorical_pass_rate: float | None
    interval_coverage_rate: float | None
    median_normalized_score: float
    parse_error: str | None = None
    network_activity_flag: bool = False
    network_activity_matches: list[str] = Field(default_factory=list)
    per_metric: dict[str, MetricSummary] = Field(default_factory=dict)


class HarborReward(StrictModel):
    reward: float


def synthetic_manifest(*, task_variant: str, artifact_paths: list[str]) -> RunManifest:
    timestamp = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return RunManifest(
        run_id=HARBOR_RUN_ID,
        benchmark_version=HARBOR_BENCHMARK_VERSION,
        task_variant=task_variant,
        system="harbor",
        requested_model="unknown",
        served_models=["unknown"],
        cli_version="unknown",
        effort="unknown",
        started_at=timestamp,
        ended_at=timestamp,
        attempt=1,
        status=RunStatus.COMPLETED,
        prompt_sha256=PLACEHOLDER_SHA256,
        pack_sha256=PLACEHOLDER_SHA256,
        runner_image_sha256=PLACEHOLDER_SHA256,
        trace_path="output/predictions.json",
        artifact_paths=artifact_paths,
    )


def load_task_predictions(
    *, predictions_path: Path, task_variant: str
) -> tuple[list[Prediction], str | None]:
    if not predictions_path.is_file():
        return [], "predictions_file_missing"
    try:
        task_output = TaskOutput.model_validate_json(
            predictions_path.read_text(encoding="utf-8")
        )
    except (ValidationError, ValueError) as error:
        return [], f"predictions_file_invalid: {type(error).__name__}"
    if task_output.task_id != task_variant:
        return [], f"task_id_mismatch: {task_output.task_id!r}"
    predictions = [
        Prediction(
            run_id=HARBOR_RUN_ID,
            metric_id=prediction.metric_id,
            point=prediction.point,
            p10=prediction.p10,
            p50=prediction.p50,
            p90=prediction.p90,
            units=prediction.units,
            confidence=prediction.confidence,
            category=prediction.category,
            source_artifact=prediction.source_artifact,
        )
        for prediction in task_output.predictions
    ]
    return predictions, None


def normalized_metric_score(*, score: Score) -> float:
    if not score.scorable:
        return 0.0
    if score.measurement_kind is MeasurementKind.CATEGORICAL:
        return 1.0 if score.categorical_passed else 0.0
    if score.measurement_kind is MeasurementKind.POSITIVE:
        if score.absolute_log_error is not None:
            return math.exp(-score.absolute_log_error)
        if score.interval_log_error is not None:
            return math.exp(-score.interval_log_error)
        return 0.0
    if score.measurement_kind is MeasurementKind.ABSOLUTE_TEMPERATURE:
        if score.absolute_error is not None:
            return math.exp(-score.absolute_error / TEMPERATURE_ERROR_SCALE_K)
        return 0.0
    if score.measurement_kind is MeasurementKind.COUNT:
        if score.count_log_error is not None:
            return 10.0 ** (-score.count_log_error)
        return 0.0
    if score.measurement_kind is MeasurementKind.RADIATION:
        if score.interval_log_error is not None:
            return math.exp(-score.interval_log_error)
        if score.qualitative_passed is not None:
            return 1.0 if score.qualitative_passed else 0.0
        return 0.0
    return 0.0


def scan_agent_logs(*, agent_logs_dir: Path) -> list[str]:
    pattern = re.compile("|".join(re.escape(token) for token in NETWORK_PATTERNS))
    matches: list[str] = []
    for path in sorted(agent_logs_dir.rglob("*")):
        if not path.is_file() or len(matches) >= MAX_NETWORK_MATCHES:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if pattern.search(line):
                matches.append(f"{path.name}: {line.strip()[:200]}")
                if len(matches) >= MAX_NETWORK_MATCHES:
                    break
    return matches


def score_task(
    *,
    predictions_path: Path,
    task_variant: str,
    measurements_path: Path,
    workspace: Path,
    output_dir: Path,
    agent_logs_dir: Path | None = None,
) -> HarborSummary:
    output_dir.mkdir(parents=True, exist_ok=True)
    measurements = [
        measurement
        for measurement in load_jsonl(path=measurements_path, model_type=Measurement)
        if measurement.task_variant == task_variant and measurement.required
    ]
    measurements.sort(key=lambda measurement: measurement.metric_id)

    predictions, parse_error = load_task_predictions(
        predictions_path=predictions_path,
        task_variant=task_variant,
    )
    prediction_by_metric = {
        prediction.metric_id: prediction for prediction in predictions
    }
    artifact_paths = sorted(
        {prediction.source_artifact for prediction in predictions}
    )
    manifest = synthetic_manifest(
        task_variant=task_variant,
        artifact_paths=artifact_paths,
    )

    scores: list[Score] = []
    for measurement in measurements:
        prediction = prediction_by_metric.get(measurement.metric_id)
        if parse_error is not None or prediction is None:
            issue = parse_error if parse_error is not None else "missing_prediction"
            scores.append(
                empty_score(manifest=manifest, measurement=measurement, issue=issue)
            )
        else:
            scores.append(
                score_prediction(
                    manifest=manifest,
                    prediction=prediction,
                    measurement=measurement,
                    artifact_root=workspace,
                )
            )

    metric_scores = {
        score.metric_id: normalized_metric_score(score=score) for score in scores
    }
    reward = median(metric_scores.values()) if metric_scores else 0.0

    categorical = [
        score.categorical_passed
        for score in scores
        if score.measurement_kind is MeasurementKind.CATEGORICAL
    ]
    coverage = [
        score.prediction_interval_covered
        for score in scores
        if score.prediction_interval_covered is not None
    ]
    network_matches = (
        scan_agent_logs(agent_logs_dir=agent_logs_dir)
        if agent_logs_dir is not None and agent_logs_dir.is_dir()
        else []
    )
    summary = HarborSummary(
        task_variant=task_variant,
        required_metrics=len(measurements),
        predicted_metrics=sum(
            1
            for measurement in measurements
            if measurement.metric_id in prediction_by_metric
        ),
        completion_rate=(
            sum(
                1
                for measurement in measurements
                if measurement.metric_id in prediction_by_metric
            )
            / len(measurements)
            if measurements
            else 0.0
        ),
        compliance_rate=(
            sum(score.compliance_passed for score in scores) / len(scores)
            if scores
            else 0.0
        ),
        artifact_validity_rate=(
            sum(score.artifact_valid for score in scores) / len(scores)
            if scores
            else 0.0
        ),
        categorical_pass_rate=(
            fmean(bool(value) for value in categorical) if categorical else None
        ),
        interval_coverage_rate=(
            fmean(bool(value) for value in coverage) if coverage else None
        ),
        median_normalized_score=reward,
        parse_error=parse_error,
        network_activity_flag=bool(network_matches),
        network_activity_matches=network_matches,
        per_metric={
            score.metric_id: MetricSummary(
                normalized_score=metric_scores[score.metric_id],
                scorable=score.scorable,
                issues=score.issues,
            )
            for score in scores
        },
    )

    write_json(path=output_dir / "reward.json", model=HarborReward(reward=reward))
    write_json(path=output_dir / "summary.json", model=summary)
    write_jsonl(path=output_dir / "scores.jsonl", models=list(scores))
    return summary
