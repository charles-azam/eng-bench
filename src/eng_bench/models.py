from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


Sha256 = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class RunStatus(StrEnum):
    COMPLETED = "completed"
    AGENT_FAILURE = "agent_failure"
    REFUSAL = "refusal"
    FALLBACK_CONTAMINATED = "fallback_contaminated"
    PROVIDER_FAILURE = "provider_failure"
    RUNNER_FAILURE = "runner_failure"


class MeasurementKind(StrEnum):
    POSITIVE = "positive"
    COUNT = "count"
    RADIATION = "radiation"
    CATEGORICAL = "categorical"
    UNSCORED = "unscored"


class QualitativeAssessment(StrEnum):
    DOMINANT = "dominant"
    NOT_DOMINANT = "not_dominant"
    UNCERTAIN = "uncertain"


class EvidenceClass(StrEnum):
    DIRECT_MEASUREMENT = "direct_measurement"
    DERIVED_MEASUREMENT = "derived_measurement"
    POSTCALC_ASSUMPTION = "postcalc_assumption"
    QUALITATIVE_STATEMENT = "qualitative_statement"
    SUPPLIED_INPUT = "supplied_input"
    UNAVAILABLE = "unavailable"


def validate_relative_artifact_path(*, value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or value == "." or ".." in path.parts or "\\" in value:
        raise ValueError("artifact paths must be normalized relative POSIX paths")
    return value


class RunManifest(StrictModel):
    run_id: NonEmptyString
    benchmark_version: NonEmptyString
    task_variant: NonEmptyString
    system: NonEmptyString
    requested_model: NonEmptyString
    served_models: list[NonEmptyString]
    cli_version: NonEmptyString
    effort: NonEmptyString
    started_at: datetime
    ended_at: datetime
    attempt: Annotated[int, Field(ge=1)]
    status: RunStatus
    prompt_sha256: Sha256
    pack_sha256: Sha256
    runner_image_sha256: Sha256
    trace_path: NonEmptyString
    artifact_paths: list[NonEmptyString] = Field(default_factory=list)

    @field_validator("trace_path")
    @classmethod
    def validate_trace_path(cls, value: str) -> str:
        return validate_relative_artifact_path(value=value)

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, values: list[str]) -> list[str]:
        validated = [validate_relative_artifact_path(value=value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("artifact_paths must not contain duplicates")
        return validated

    @model_validator(mode="after")
    def validate_timing(self) -> Self:
        if self.started_at.tzinfo is None or self.ended_at.tzinfo is None:
            raise ValueError("run timestamps must include a timezone")
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not precede started_at")
        inference_statuses = {
            RunStatus.COMPLETED,
            RunStatus.AGENT_FAILURE,
            RunStatus.REFUSAL,
            RunStatus.FALLBACK_CONTAMINATED,
        }
        if self.status in inference_statuses and not self.served_models:
            raise ValueError("inference-valid runs must record at least one served model")
        if self.status is RunStatus.FALLBACK_CONTAMINATED and all(
            served_model == self.requested_model for served_model in self.served_models
        ):
            raise ValueError("fallback-contaminated runs must record a non-requested served model")
        return self

    @property
    def infrastructure_valid(self) -> bool:
        return self.status in {
            RunStatus.COMPLETED,
            RunStatus.AGENT_FAILURE,
            RunStatus.REFUSAL,
            RunStatus.FALLBACK_CONTAMINATED,
        }


class FrozenSystem(StrictModel):
    requested_model: NonEmptyString
    cli_version: NonEmptyString
    effort: NonEmptyString


class FrozenLedger(StrictModel):
    benchmark_version: NonEmptyString
    prompt_sha256: Sha256
    runner_image_sha256: Sha256
    task_pack_sha256: dict[NonEmptyString, Sha256]
    systems: dict[NonEmptyString, FrozenSystem]

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        if not self.task_pack_sha256:
            raise ValueError("frozen ledger must contain at least one task pack")
        if not self.systems:
            raise ValueError("frozen ledger must contain at least one system")
        return self


class Prediction(StrictModel):
    run_id: NonEmptyString
    metric_id: NonEmptyString
    point: float | None = None
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    units: NonEmptyString
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    qualitative: QualitativeAssessment | None = None
    category: NonEmptyString | None = None
    source_artifact: NonEmptyString

    @field_validator("source_artifact")
    @classmethod
    def validate_source_artifact(cls, value: str) -> str:
        return validate_relative_artifact_path(value=value)

    @model_validator(mode="after")
    def validate_prediction_shape(self) -> Self:
        quantiles = (self.p10, self.p50, self.p90)
        if any(value is not None for value in quantiles) and not all(
            value is not None for value in quantiles
        ):
            raise ValueError("p10, p50, and p90 must be supplied together")
        if self.p10 is not None and self.p50 is not None and self.p90 is not None:
            if not self.p10 <= self.p50 <= self.p90:
                raise ValueError("prediction quantiles must satisfy p10 <= p50 <= p90")
        if (
            self.point is None
            and self.p50 is None
            and self.qualitative is None
            and self.category is None
        ):
            raise ValueError(
                "a prediction needs a point, quantiles, qualitative assessment, or category"
            )
        return self


class Measurement(StrictModel):
    task_variant: NonEmptyString
    metric_id: NonEmptyString
    kind: MeasurementKind
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    units: NonEmptyString
    expected_qualitative: QualitativeAssessment | None = None
    expected_category: NonEmptyString | None = None
    allowed_categories: list[NonEmptyString] = Field(default_factory=list)
    evidence_class: EvidenceClass
    dependency_group: NonEmptyString | None = None
    provenance: NonEmptyString
    required: bool = True

    @model_validator(mode="after")
    def validate_measurement_shape(self) -> Self:
        has_interval = self.lower is not None or self.upper is not None
        if has_interval and (self.lower is None or self.upper is None):
            raise ValueError("measurement lower and upper bounds must be supplied together")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("measurement lower must not exceed upper")
        if self.kind not in {
            MeasurementKind.CATEGORICAL,
            MeasurementKind.UNSCORED,
        } and self.value is None and not has_interval:
            raise ValueError("a measurement needs a value or an accepted interval")
        if self.kind is MeasurementKind.POSITIVE:
            references = [
                value for value in (self.value, self.lower, self.upper) if value is not None
            ]
            if any(value <= 0.0 for value in references):
                raise ValueError("positive measurements must be greater than zero")
        if self.kind is MeasurementKind.COUNT:
            references = [
                value for value in (self.value, self.lower, self.upper) if value is not None
            ]
            if any(value < 0.0 or not value.is_integer() for value in references):
                raise ValueError("count measurements must be non-negative integers")
        if self.kind is MeasurementKind.RADIATION:
            if self.lower is None or self.upper is None:
                raise ValueError("radiation measurements need an accepted interval")
            if self.expected_qualitative is None:
                raise ValueError("radiation measurements need an expected qualitative assessment")
        if self.kind is MeasurementKind.CATEGORICAL:
            if self.value is not None or has_interval:
                raise ValueError("categorical measurements must not contain numeric values")
            if self.units != "category":
                raise ValueError("categorical measurements must use 'category' units")
            if self.expected_category is None:
                raise ValueError("categorical measurements need an expected category")
            if len(self.allowed_categories) < 2:
                raise ValueError("categorical measurements need at least two allowed categories")
            if len(self.allowed_categories) != len(set(self.allowed_categories)):
                raise ValueError("allowed_categories must not contain duplicates")
            if self.expected_category not in self.allowed_categories:
                raise ValueError("expected_category must be present in allowed_categories")
        if self.kind is MeasurementKind.UNSCORED:
            if self.required:
                raise ValueError("unscored records must set required=false")
            if self.value is not None or has_interval:
                raise ValueError("unscored records must not contain numeric targets")
            if self.expected_category is not None or self.allowed_categories:
                raise ValueError("unscored records must not contain categorical targets")
        if self.evidence_class in {
            EvidenceClass.DERIVED_MEASUREMENT,
            EvidenceClass.POSTCALC_ASSUMPTION,
        } and self.dependency_group is None:
            raise ValueError("derived measurements and postcalculation assumptions need a dependency group")
        return self


class Score(StrictModel):
    run_id: NonEmptyString
    benchmark_version: NonEmptyString
    task_variant: NonEmptyString
    system: NonEmptyString
    requested_model: NonEmptyString
    served_models: list[NonEmptyString]
    run_status: RunStatus
    infrastructure_valid: bool
    metric_id: NonEmptyString
    measurement_kind: MeasurementKind
    evidence_class: EvidenceClass
    dependency_group: NonEmptyString | None
    completion_passed: bool
    compliance_passed: bool
    artifact_valid: bool
    scorable: bool
    normalized_point: float | None = None
    normalized_p10: float | None = None
    normalized_p50: float | None = None
    normalized_p90: float | None = None
    absolute_log_error: float | None = None
    signed_relative_error: float | None = None
    weighted_interval_score: float | None = None
    count_log_error: float | None = None
    interval_log_error: float | None = None
    prediction_interval_covered: bool | None = None
    point_in_measurement_interval: bool | None = None
    qualitative_passed: bool | None = None
    categorical_passed: bool | None = None
    issues: list[str] = Field(default_factory=list)


class MetricAggregate(StrictModel):
    metric_id: NonEmptyString
    measurement_kind: MeasurementKind
    expected_predictions: int
    completed_predictions: int
    scorable_predictions: int
    completion_rate: float | None
    artifact_validity_rate: float | None
    mean_absolute_log_error: float | None
    mean_signed_relative_error: float | None
    mean_weighted_interval_score: float | None
    mean_count_log_error: float | None
    mean_interval_log_error: float | None
    prediction_interval_coverage_rate: float | None
    point_interval_pass_rate: float | None
    qualitative_pass_rate: float | None
    categorical_pass_rate: float | None


class TaskAggregate(StrictModel):
    system: NonEmptyString
    task_variant: NonEmptyString
    attempts: int
    infrastructure_valid_attempts: int
    completed_attempts: int
    agent_failures: int
    refusals: int
    fallback_contaminated_attempts: int
    provider_failures: int
    runner_failures: int
    run_completion_rate: float | None
    mean_wall_time_seconds: float | None
    expected_metric_predictions: int
    completed_metric_predictions: int
    metric_completion_rate: float | None
    metrics: list[MetricAggregate]


class EvaluationSummary(StrictModel):
    schema_version: str = "1.0"
    benchmark_versions: list[str]
    total_attempts: int
    task_results: list[TaskAggregate]


class EvaluationResult(StrictModel):
    scores: list[Score]
    summary: EvaluationSummary
