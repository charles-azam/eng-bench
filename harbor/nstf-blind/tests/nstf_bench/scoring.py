from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Callable, Iterable, TypeVar

from nstf_bench.models import (
    EvaluationResult,
    EvaluationSummary,
    FrozenLedger,
    Measurement,
    MeasurementKind,
    MetricAggregate,
    Prediction,
    RunManifest,
    RunStatus,
    Score,
    TaskAggregate,
)
from nstf_bench.units import UNIT_DEFINITIONS, can_convert_units, convert_value


ValueT = TypeVar("ValueT")
KeyT = TypeVar("KeyT")


def index_unique(
    *, values: Iterable[ValueT], key: Callable[[ValueT], KeyT], label: str
) -> dict[KeyT, ValueT]:
    indexed: dict[KeyT, ValueT] = {}
    for value in values:
        item_key = key(value)
        if item_key in indexed:
            raise ValueError(f"duplicate {label}: {item_key!r}")
        indexed[item_key] = value
    return indexed


def prediction_point(*, prediction: Prediction) -> float | None:
    return prediction.point if prediction.point is not None else prediction.p50


def interval_distance(
    *, value: float, lower: float, upper: float, transform: Callable[[float], float]
) -> float:
    if lower <= value <= upper:
        return 0.0
    nearest = lower if value < lower else upper
    return abs(transform(value) - transform(nearest))


def log10p1(*, value: float) -> float:
    return math.log10(value + 1.0)


def weighted_interval_score(*, observed: float, p10: float, p50: float, p90: float) -> float:
    alpha = 0.2
    interval_score = p90 - p10
    if observed < p10:
        interval_score += (2.0 / alpha) * (p10 - observed)
    if observed > p90:
        interval_score += (2.0 / alpha) * (observed - p90)
    return (0.5 * abs(observed - p50) + (alpha / 2.0) * interval_score) / 1.5


def safe_file_exists(*, artifact_root: Path, relative_path: str) -> bool:
    resolved_root = artifact_root.resolve()
    resolved_file = (artifact_root / relative_path).resolve()
    return resolved_file.is_relative_to(resolved_root) and resolved_file.is_file()


def artifact_exists(*, artifact_root: Path, manifest: RunManifest, prediction: Prediction) -> bool:
    if prediction.source_artifact not in manifest.artifact_paths:
        return False
    return safe_file_exists(
        artifact_root=artifact_root,
        relative_path=manifest.trace_path,
    ) and safe_file_exists(
        artifact_root=artifact_root,
        relative_path=prediction.source_artifact,
    )


def normalized_prediction(
    *, prediction: Prediction, measurement: Measurement
) -> tuple[float | None, float | None, float | None, float | None]:
    def convert_optional(*, value: float | None) -> float | None:
        if value is None:
            return None
        return convert_value(value=value, from_units=prediction.units, to_units=measurement.units)

    return (
        convert_optional(value=prediction_point(prediction=prediction)),
        convert_optional(value=prediction.p10),
        convert_optional(value=prediction.p50),
        convert_optional(value=prediction.p90),
    )


def prediction_compliance_issues(
    *, prediction: Prediction, measurement: Measurement
) -> list[str]:
    if not can_convert_units(from_units=prediction.units, to_units=measurement.units):
        return ["incompatible_units"]

    point, p10, _, _ = normalized_prediction(prediction=prediction, measurement=measurement)
    issues: list[str] = []
    if measurement.kind in {
        MeasurementKind.POSITIVE,
        MeasurementKind.ABSOLUTE_TEMPERATURE,
        MeasurementKind.COUNT,
    } and point is None:
        issues.append("missing_numeric_point")
    if measurement.kind is MeasurementKind.POSITIVE:
        positive_values = [
            value
            for value in normalized_prediction(prediction=prediction, measurement=measurement)
            if value is not None
        ]
        if any(value <= 0.0 for value in positive_values):
            issues.append("non_positive_prediction")
    if measurement.kind is MeasurementKind.COUNT:
        numeric_values = [value for value in (point, p10) if value is not None]
        if any(value < 0.0 for value in numeric_values):
            issues.append("negative_count_prediction")
    if measurement.kind is MeasurementKind.RADIATION:
        if point is None and prediction.qualitative is None:
            issues.append("missing_radiation_assessment")
        dimension, _, _ = UNIT_DEFINITIONS[measurement.units]
        fraction_point = (
            convert_value(value=point, from_units=measurement.units, to_units="fraction")
            if point is not None and dimension == "fraction"
            else None
        )
        if fraction_point is not None and not 0.0 <= fraction_point <= 1.0:
            issues.append("radiation_fraction_out_of_range")
    if measurement.kind is MeasurementKind.CATEGORICAL:
        if prediction.category is None:
            issues.append("missing_category")
        elif prediction.category not in measurement.allowed_categories:
            issues.append("category_not_allowed")
    return issues


def empty_score(
    *, manifest: RunManifest, measurement: Measurement, issue: str
) -> Score:
    issues = [issue]
    if manifest.status is not RunStatus.COMPLETED:
        issues.insert(0, f"run_status_{manifest.status.value}")
    return Score(
        run_id=manifest.run_id,
        benchmark_version=manifest.benchmark_version,
        task_variant=manifest.task_variant,
        system=manifest.system,
        requested_model=manifest.requested_model,
        served_models=manifest.served_models,
        run_status=manifest.status,
        infrastructure_valid=manifest.infrastructure_valid,
        metric_id=measurement.metric_id,
        measurement_kind=measurement.kind,
        evidence_class=measurement.evidence_class,
        dependency_group=measurement.dependency_group,
        completion_passed=False,
        compliance_passed=False,
        artifact_valid=False,
        scorable=False,
        issues=issues,
    )


def score_prediction(
    *, manifest: RunManifest, prediction: Prediction, measurement: Measurement, artifact_root: Path
) -> Score:
    issues = prediction_compliance_issues(prediction=prediction, measurement=measurement)
    compliance_passed = not issues
    artifact_valid = artifact_exists(
        artifact_root=artifact_root,
        manifest=manifest,
        prediction=prediction,
    )
    if not artifact_valid:
        issues.append("artifact_missing_or_unlisted")
    excluded_quality_statuses = {
        RunStatus.AGENT_FAILURE,
        RunStatus.REFUSAL,
        RunStatus.FALLBACK_CONTAMINATED,
        RunStatus.PROVIDER_FAILURE,
        RunStatus.RUNNER_FAILURE,
    }
    if manifest.status in excluded_quality_statuses:
        issues.append(f"run_status_{manifest.status.value}")
        compliance_passed = False

    normalized_point: float | None = None
    normalized_p10: float | None = None
    normalized_p50: float | None = None
    normalized_p90: float | None = None
    absolute_error: float | None = None
    signed_error: float | None = None
    absolute_log_error: float | None = None
    signed_relative_error: float | None = None
    wis: float | None = None
    count_log_error: float | None = None
    interval_log_error: float | None = None
    prediction_interval_covered: bool | None = None
    point_in_measurement_interval: bool | None = None
    qualitative_passed: bool | None = None
    categorical_passed: bool | None = None

    if can_convert_units(from_units=prediction.units, to_units=measurement.units):
        normalized_point, normalized_p10, normalized_p50, normalized_p90 = normalized_prediction(
            prediction=prediction,
            measurement=measurement,
        )

    if compliance_passed and normalized_point is not None:
        if measurement.kind is MeasurementKind.POSITIVE:
            if measurement.value is not None:
                absolute_log_error = abs(math.log(normalized_point / measurement.value))
                signed_relative_error = (normalized_point - measurement.value) / measurement.value
            if measurement.lower is not None and measurement.upper is not None:
                interval_log_error = interval_distance(
                    value=normalized_point,
                    lower=measurement.lower,
                    upper=measurement.upper,
                    transform=math.log,
                )
                point_in_measurement_interval = (
                    measurement.lower <= normalized_point <= measurement.upper
                )
        if measurement.kind is MeasurementKind.ABSOLUTE_TEMPERATURE:
            if measurement.value is not None:
                signed_error = normalized_point - measurement.value
                absolute_error = abs(signed_error)
            if measurement.lower is not None and measurement.upper is not None:
                absolute_error = interval_distance(
                    value=normalized_point,
                    lower=measurement.lower,
                    upper=measurement.upper,
                    transform=lambda value: value,
                )
                point_in_measurement_interval = (
                    measurement.lower <= normalized_point <= measurement.upper
                )
        if measurement.kind is MeasurementKind.COUNT:
            if measurement.lower is not None and measurement.upper is not None:
                count_log_error = interval_distance(
                    value=normalized_point,
                    lower=measurement.lower,
                    upper=measurement.upper,
                    transform=lambda value: log10p1(value=value),
                )
                point_in_measurement_interval = (
                    measurement.lower <= normalized_point <= measurement.upper
                )
            elif measurement.value is not None:
                count_log_error = abs(
                    log10p1(value=normalized_point) - log10p1(value=measurement.value)
                )
            if measurement.value not in {None, 0.0}:
                signed_relative_error = (normalized_point - measurement.value) / measurement.value
        if measurement.kind is MeasurementKind.RADIATION:
            if measurement.lower is not None and measurement.upper is not None:
                interval_log_error = interval_distance(
                    value=normalized_point,
                    lower=measurement.lower,
                    upper=measurement.upper,
                    transform=math.log1p,
                )
                point_in_measurement_interval = (
                    measurement.lower <= normalized_point <= measurement.upper
                )

    if compliance_passed and measurement.value is not None:
        if normalized_p10 is not None and normalized_p50 is not None and normalized_p90 is not None:
            if measurement.kind is MeasurementKind.POSITIVE and measurement.units == "fraction":
                wis = weighted_interval_score(
                    observed=math.log(measurement.value),
                    p10=math.log(normalized_p10),
                    p50=math.log(normalized_p50),
                    p90=math.log(normalized_p90),
                )
            else:
                wis = weighted_interval_score(
                    observed=measurement.value,
                    p10=normalized_p10,
                    p50=normalized_p50,
                    p90=normalized_p90,
                )
            prediction_interval_covered = normalized_p10 <= measurement.value <= normalized_p90

    if measurement.kind is MeasurementKind.RADIATION and prediction.qualitative is not None:
        qualitative_passed = prediction.qualitative is measurement.expected_qualitative
    if measurement.kind is MeasurementKind.CATEGORICAL and prediction.category is not None:
        categorical_passed = prediction.category == measurement.expected_category

    completion_passed = manifest.status is RunStatus.COMPLETED
    scorable = completion_passed and compliance_passed and artifact_valid
    return Score(
        run_id=manifest.run_id,
        benchmark_version=manifest.benchmark_version,
        task_variant=manifest.task_variant,
        system=manifest.system,
        requested_model=manifest.requested_model,
        served_models=manifest.served_models,
        run_status=manifest.status,
        infrastructure_valid=manifest.infrastructure_valid,
        metric_id=measurement.metric_id,
        measurement_kind=measurement.kind,
        evidence_class=measurement.evidence_class,
        dependency_group=measurement.dependency_group,
        completion_passed=completion_passed,
        compliance_passed=compliance_passed,
        artifact_valid=artifact_valid,
        scorable=scorable,
        normalized_point=normalized_point,
        normalized_p10=normalized_p10,
        normalized_p50=normalized_p50,
        normalized_p90=normalized_p90,
        absolute_error=absolute_error,
        signed_error=signed_error,
        absolute_log_error=absolute_log_error,
        signed_relative_error=signed_relative_error,
        weighted_interval_score=wis,
        count_log_error=count_log_error,
        interval_log_error=interval_log_error,
        prediction_interval_covered=prediction_interval_covered,
        point_in_measurement_interval=point_in_measurement_interval,
        qualitative_passed=qualitative_passed,
        categorical_passed=categorical_passed,
        issues=issues,
    )


def optional_mean(*, values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return fmean(present) if present else None


def optional_rate(*, values: Iterable[bool | None]) -> float | None:
    present = [value for value in values if value is not None]
    return fmean(float(value) for value in present) if present else None


def aggregate_metric(*, scores: list[Score]) -> MetricAggregate:
    infrastructure_scores = [score for score in scores if score.infrastructure_valid]
    completed_scores = [score for score in infrastructure_scores if score.completion_passed]
    scorable_scores = [score for score in infrastructure_scores if score.scorable]
    artifact_scores = completed_scores
    expected = len(infrastructure_scores)
    return MetricAggregate(
        metric_id=scores[0].metric_id,
        measurement_kind=scores[0].measurement_kind,
        expected_predictions=expected,
        completed_predictions=len(completed_scores),
        scorable_predictions=len(scorable_scores),
        completion_rate=len(completed_scores) / expected if expected else None,
        artifact_validity_rate=(
            sum(score.artifact_valid for score in artifact_scores) / len(artifact_scores)
            if artifact_scores
            else None
        ),
        mean_absolute_error=optional_mean(
            values=(score.absolute_error for score in scorable_scores)
        ),
        mean_signed_error=optional_mean(
            values=(score.signed_error for score in scorable_scores)
        ),
        mean_absolute_log_error=optional_mean(
            values=(score.absolute_log_error for score in scorable_scores)
        ),
        mean_signed_relative_error=optional_mean(
            values=(score.signed_relative_error for score in scorable_scores)
        ),
        mean_weighted_interval_score=optional_mean(
            values=(score.weighted_interval_score for score in scorable_scores)
        ),
        mean_count_log_error=optional_mean(
            values=(score.count_log_error for score in scorable_scores)
        ),
        mean_interval_log_error=optional_mean(
            values=(score.interval_log_error for score in scorable_scores)
        ),
        prediction_interval_coverage_rate=optional_rate(
            values=(score.prediction_interval_covered for score in scorable_scores)
        ),
        point_interval_pass_rate=optional_rate(
            values=(score.point_in_measurement_interval for score in scorable_scores)
        ),
        qualitative_pass_rate=optional_rate(
            values=(score.qualitative_passed for score in scorable_scores)
        ),
        categorical_pass_rate=optional_rate(
            values=(score.categorical_passed for score in scorable_scores)
        ),
    )


def aggregate_task(
    *, system: str, task_variant: str, manifests: list[RunManifest], scores: list[Score]
) -> TaskAggregate:
    infrastructure_manifests = [manifest for manifest in manifests if manifest.infrastructure_valid]
    metric_groups: dict[str, list[Score]] = defaultdict(list)
    for score in scores:
        metric_groups[score.metric_id].append(score)
    metric_aggregates = [
        aggregate_metric(scores=metric_groups[metric_id]) for metric_id in sorted(metric_groups)
    ]
    expected_metric_predictions = sum(metric.expected_predictions for metric in metric_aggregates)
    completed_metric_predictions = sum(metric.completed_predictions for metric in metric_aggregates)
    return TaskAggregate(
        system=system,
        task_variant=task_variant,
        attempts=len(manifests),
        infrastructure_valid_attempts=len(infrastructure_manifests),
        completed_attempts=sum(manifest.status is RunStatus.COMPLETED for manifest in manifests),
        agent_failures=sum(manifest.status is RunStatus.AGENT_FAILURE for manifest in manifests),
        refusals=sum(manifest.status is RunStatus.REFUSAL for manifest in manifests),
        fallback_contaminated_attempts=sum(
            manifest.status is RunStatus.FALLBACK_CONTAMINATED for manifest in manifests
        ),
        provider_failures=sum(
            manifest.status is RunStatus.PROVIDER_FAILURE for manifest in manifests
        ),
        runner_failures=sum(manifest.status is RunStatus.RUNNER_FAILURE for manifest in manifests),
        run_completion_rate=(
            sum(manifest.status is RunStatus.COMPLETED for manifest in infrastructure_manifests)
            / len(infrastructure_manifests)
            if infrastructure_manifests
            else None
        ),
        mean_wall_time_seconds=optional_mean(
            values=(
                (manifest.ended_at - manifest.started_at).total_seconds()
                for manifest in manifests
            )
        ),
        expected_metric_predictions=expected_metric_predictions,
        completed_metric_predictions=completed_metric_predictions,
        metric_completion_rate=(
            completed_metric_predictions / expected_metric_predictions
            if expected_metric_predictions
            else None
        ),
        metrics=metric_aggregates,
    )


def evaluate(
    *,
    manifests: list[RunManifest],
    predictions: list[Prediction],
    measurements: list[Measurement],
    artifact_root: Path,
    ledger: FrozenLedger,
) -> EvaluationResult:
    validate_frozen_manifests(manifests=manifests, ledger=ledger)
    manifest_by_run = index_unique(values=manifests, key=lambda item: item.run_id, label="run_id")
    prediction_by_metric = index_unique(
        values=predictions,
        key=lambda item: (item.run_id, item.metric_id),
        label="prediction run/metric pair",
    )
    measurement_by_metric = index_unique(
        values=measurements,
        key=lambda item: (item.task_variant, item.metric_id),
        label="measurement task/metric pair",
    )

    measured_tasks = {
        measurement.task_variant for measurement in measurements if measurement.required
    }
    unmeasured_tasks = sorted(
        {
            manifest.task_variant
            for manifest in manifests
            if manifest.task_variant not in measured_tasks
        }
    )
    if unmeasured_tasks:
        raise ValueError(f"run manifests have no required measurements: {unmeasured_tasks!r}")

    for prediction in predictions:
        if prediction.run_id not in manifest_by_run:
            raise ValueError(f"prediction references unknown run: {prediction.run_id!r}")
        manifest = manifest_by_run[prediction.run_id]
        if (manifest.task_variant, prediction.metric_id) not in measurement_by_metric:
            raise ValueError(
                f"prediction references an unmeasured metric: "
                f"{manifest.task_variant!r}/{prediction.metric_id!r}"
            )

    scores: list[Score] = []
    for manifest in sorted(manifests, key=lambda item: item.run_id):
        task_measurements = sorted(
            (
                measurement
                for measurement in measurements
                if measurement.task_variant == manifest.task_variant and measurement.required
            ),
            key=lambda item: item.metric_id,
        )
        for measurement in task_measurements:
            prediction = prediction_by_metric.get((manifest.run_id, measurement.metric_id))
            score = (
                empty_score(
                    manifest=manifest,
                    measurement=measurement,
                    issue="missing_prediction",
                )
                if prediction is None
                else score_prediction(
                    manifest=manifest,
                    prediction=prediction,
                    measurement=measurement,
                    artifact_root=artifact_root,
                )
            )
            scores.append(score)

    task_manifests: dict[tuple[str, str], list[RunManifest]] = defaultdict(list)
    task_scores: dict[tuple[str, str], list[Score]] = defaultdict(list)
    for manifest in manifests:
        task_manifests[(manifest.system, manifest.task_variant)].append(manifest)
    for score in scores:
        task_scores[(score.system, score.task_variant)].append(score)

    task_results = [
        aggregate_task(
            system=system,
            task_variant=task_variant,
            manifests=task_manifests[(system, task_variant)],
            scores=task_scores[(system, task_variant)],
        )
        for system, task_variant in sorted(task_manifests)
    ]
    summary = EvaluationSummary(
        benchmark_versions=sorted({manifest.benchmark_version for manifest in manifests}),
        total_attempts=len(manifests),
        task_results=task_results,
    )
    return EvaluationResult(scores=scores, summary=summary)


def validate_frozen_manifests(
    *, manifests: list[RunManifest], ledger: FrozenLedger
) -> None:
    for manifest in manifests:
        issues: list[str] = []
        if manifest.benchmark_version != ledger.benchmark_version:
            issues.append("benchmark_version")
        if manifest.prompt_sha256 != ledger.prompt_sha256:
            issues.append("prompt_sha256")
        if manifest.runner_image_sha256 != ledger.runner_image_sha256:
            issues.append("runner_image_sha256")
        expected_pack = ledger.task_pack_sha256.get(manifest.task_variant)
        if expected_pack is None or manifest.pack_sha256 != expected_pack:
            issues.append("pack_sha256")
        expected_system = ledger.systems.get(manifest.system)
        if expected_system is None:
            issues.append("system")
        else:
            if manifest.requested_model != expected_system.requested_model:
                issues.append("requested_model")
            if manifest.cli_version != expected_system.cli_version:
                issues.append("cli_version")
            if manifest.effort != expected_system.effort:
                issues.append("effort")
        if manifest.status is not RunStatus.FALLBACK_CONTAMINATED and any(
            served_model != manifest.requested_model
            for served_model in manifest.served_models
        ):
            issues.append("unexpected_served_model")
        if issues:
            raise ValueError(
                f"run {manifest.run_id!r} violates frozen ledger fields: {sorted(issues)!r}"
            )
