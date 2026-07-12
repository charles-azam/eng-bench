from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from analysis.models import DatasetName, SystemName
from eng_bench.models import (
    EvidenceClass,
    MeasurementKind,
    QualitativeAssessment,
    RunStatus,
    Sha256,
)


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
NonNegativeInteger = Annotated[int, Field(ge=0)]
PositiveInteger = Annotated[int, Field(ge=1)]


class StrictPublicationModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class AttemptRecord(StrictPublicationModel):
    run_id: NonEmptyString
    stage: NonEmptyString
    task_variant: NonEmptyString
    system: SystemName
    scheduled_replicate: PositiveInteger
    physical_attempt: PositiveInteger
    is_retry: bool
    is_final_attempt_for_scheduled_replicate: bool
    status: RunStatus
    infrastructure_valid: bool
    included_n3: bool
    included_n5: bool
    included_ablation: bool

    def included_in(self, *, dataset: DatasetName) -> bool:
        if dataset is DatasetName.N3:
            return self.included_n3
        if dataset is DatasetName.N5:
            return self.included_n5
        return self.included_ablation

    @property
    def scheduled_key(self) -> tuple[str, str, str, int]:
        return (
            self.stage,
            self.task_variant,
            self.system,
            self.scheduled_replicate,
        )


class RunStatusRow(StrictPublicationModel):
    dataset: DatasetName
    run_id: NonEmptyString
    benchmark_version: NonEmptyString
    stage: NonEmptyString
    task_variant: NonEmptyString
    system: SystemName
    scheduled_replicate: PositiveInteger
    physical_attempt: PositiveInteger
    is_retry: bool
    is_final_attempt_for_scheduled_replicate: bool
    requested_model: NonEmptyString
    served_models: list[NonEmptyString]
    status: RunStatus
    infrastructure_valid: bool
    started_at: datetime
    ended_at: datetime
    wall_time_seconds: Annotated[float, Field(ge=0.0)]


class CampaignRunStatusRow(StrictPublicationModel):
    selected_dataset: DatasetName
    run_id: NonEmptyString
    benchmark_version: NonEmptyString
    stage: NonEmptyString
    task_variant: NonEmptyString
    system: SystemName
    scheduled_replicate: PositiveInteger
    physical_attempt: PositiveInteger
    is_retry: bool
    is_final_attempt_for_scheduled_replicate: bool
    requested_model: NonEmptyString
    served_models: list[NonEmptyString]
    status: RunStatus
    infrastructure_valid: bool
    started_at: datetime
    ended_at: datetime
    wall_time_seconds: Annotated[float, Field(ge=0.0)]
    included_n3: bool
    included_n5: bool
    included_ablation: bool
    included_selected_dataset: bool


class StatusCounts(StrictPublicationModel):
    completed: NonNegativeInteger
    agent_failure: NonNegativeInteger
    refusal: NonNegativeInteger
    fallback_contaminated: NonNegativeInteger
    provider_failure: NonNegativeInteger
    runner_failure: NonNegativeInteger


class CellStatusRow(StrictPublicationModel):
    dataset: DatasetName
    task_variant: NonEmptyString
    system: SystemName
    scheduled_replicates: PositiveInteger
    eligible_replicates: NonNegativeInteger
    completed_final_replicates: NonNegativeInteger
    non_completed_final_replicates: NonNegativeInteger
    physical_attempts: PositiveInteger
    retries: NonNegativeInteger
    non_completed_physical_attempts: NonNegativeInteger
    infrastructure_failed_physical_attempts: NonNegativeInteger
    completed_attempts: NonNegativeInteger
    agent_failure_attempts: NonNegativeInteger
    refusal_attempts: NonNegativeInteger
    fallback_contaminated_attempts: NonNegativeInteger
    provider_failure_attempts: NonNegativeInteger
    runner_failure_attempts: NonNegativeInteger


class ReplicateMetricRow(StrictPublicationModel):
    dataset: DatasetName
    run_id: NonEmptyString
    benchmark_version: NonEmptyString
    stage: NonEmptyString
    task_variant: NonEmptyString
    system: SystemName
    scheduled_replicate: PositiveInteger
    physical_attempt: PositiveInteger
    is_retry: bool
    is_final_attempt_for_scheduled_replicate: bool
    run_status: RunStatus
    infrastructure_valid: bool
    metric_id: NonEmptyString
    measurement_kind: MeasurementKind
    measurement_required: bool
    evaluator_row_present: bool
    evidence_class: EvidenceClass
    dependency_group: NonEmptyString | None
    units: NonEmptyString
    observed_value: float | None
    accepted_lower: float | None
    accepted_upper: float | None
    expected_qualitative: QualitativeAssessment | None
    expected_category: NonEmptyString | None
    allowed_categories: list[NonEmptyString]
    measurement_provenance: NonEmptyString
    prediction_present: bool
    prediction_units: NonEmptyString | None
    prediction_confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None
    source_artifact: NonEmptyString | None
    raw_point: float | None
    raw_p10: float | None
    raw_p50: float | None
    raw_p90: float | None
    predicted_qualitative: QualitativeAssessment | None
    predicted_category: NonEmptyString | None
    point: float | None
    p10: float | None
    p50: float | None
    p90: float | None
    completion_passed: bool | None
    compliance_passed: bool | None
    artifact_valid: bool | None
    scorable: bool | None
    absolute_error: float | None
    signed_error: float | None
    absolute_log_error: float | None
    signed_relative_error: float | None
    weighted_interval_score: float | None
    count_log_error: float | None
    interval_log_error: float | None
    prediction_interval_covered: bool | None
    point_in_measurement_interval: bool | None
    qualitative_passed: bool | None
    categorical_passed: bool | None
    issues: list[str]
    publication_notes: list[str]


class TaskMetricSummaryRow(StrictPublicationModel):
    dataset: DatasetName
    system: SystemName
    task_variant: NonEmptyString
    task_attempts: NonNegativeInteger
    task_infrastructure_valid_attempts: NonNegativeInteger
    task_completed_attempts: NonNegativeInteger
    task_agent_failures: NonNegativeInteger
    task_refusals: NonNegativeInteger
    task_fallback_contaminated_attempts: NonNegativeInteger
    task_provider_failures: NonNegativeInteger
    task_runner_failures: NonNegativeInteger
    task_run_completion_rate: float | None
    task_run_completion_numerator: NonNegativeInteger
    task_run_completion_denominator: NonNegativeInteger
    task_mean_wall_time_seconds: float | None
    task_mean_wall_time_denominator: NonNegativeInteger
    task_expected_metric_predictions: NonNegativeInteger
    task_completed_metric_predictions: NonNegativeInteger
    task_metric_completion_rate: float | None
    task_metric_completion_numerator: NonNegativeInteger
    task_metric_completion_denominator: NonNegativeInteger
    metric_id: NonEmptyString
    measurement_kind: MeasurementKind
    measurement_required: bool
    evidence_class: EvidenceClass
    dependency_group: NonEmptyString | None
    units: NonEmptyString
    measurement_provenance: NonEmptyString
    expected_predictions: NonNegativeInteger
    completed_predictions: NonNegativeInteger
    scorable_predictions: NonNegativeInteger
    completion_rate: float | None
    completion_numerator: NonNegativeInteger
    completion_denominator: NonNegativeInteger
    artifact_validity_rate: float | None
    artifact_validity_numerator: NonNegativeInteger
    artifact_validity_denominator: NonNegativeInteger
    mean_absolute_error: float | None
    mean_absolute_error_denominator: NonNegativeInteger
    mean_signed_error: float | None
    mean_signed_error_denominator: NonNegativeInteger
    mean_absolute_log_error: float | None
    mean_absolute_log_error_denominator: NonNegativeInteger
    mean_signed_relative_error: float | None
    mean_signed_relative_error_denominator: NonNegativeInteger
    mean_weighted_interval_score: float | None
    mean_weighted_interval_score_denominator: NonNegativeInteger
    mean_count_log_error: float | None
    mean_count_log_error_denominator: NonNegativeInteger
    mean_interval_log_error: float | None
    mean_interval_log_error_denominator: NonNegativeInteger
    prediction_interval_coverage_rate: float | None
    prediction_interval_coverage_numerator: NonNegativeInteger
    prediction_interval_coverage_denominator: NonNegativeInteger
    point_interval_pass_rate: float | None
    point_interval_pass_numerator: NonNegativeInteger
    point_interval_pass_denominator: NonNegativeInteger
    qualitative_pass_rate: float | None
    qualitative_pass_numerator: NonNegativeInteger
    qualitative_pass_denominator: NonNegativeInteger
    categorical_pass_rate: float | None
    categorical_pass_numerator: NonNegativeInteger
    categorical_pass_denominator: NonNegativeInteger


class CellClaim(StrictPublicationModel):
    task_variant: NonEmptyString
    system: SystemName
    eligible_replicates: NonNegativeInteger
    scheduled_replicates: PositiveInteger
    physical_attempts: PositiveInteger
    retries: NonNegativeInteger
    non_completed_physical_attempts: NonNegativeInteger
    infrastructure_failed_physical_attempts: NonNegativeInteger
    status_counts: StatusCounts


class StageCompletionClaim(StrictPublicationModel):
    stage: NonEmptyString
    scheduled_replicates: PositiveInteger
    launched_first_attempts: NonNegativeInteger
    complete_launch_prefix: bool
    schedule_sha256: NonEmptyString


class IntervalCoverageClaim(StrictPublicationModel):
    task_variant: NonEmptyString
    system: SystemName
    metric_id: NonEmptyString
    prediction_interval_covered_numerator: NonNegativeInteger
    prediction_interval_covered_denominator: NonNegativeInteger
    point_in_measurement_interval_numerator: NonNegativeInteger
    point_in_measurement_interval_denominator: NonNegativeInteger


class PublicationClaims(StrictPublicationModel):
    schema_version: Literal["1.0"] = "1.0"
    dataset: DatasetName
    scheduled_replicates: PositiveInteger
    eligible_replicates: NonNegativeInteger
    physical_attempts: PositiveInteger
    retries: NonNegativeInteger
    non_completed_physical_attempts: NonNegativeInteger
    infrastructure_failed_physical_attempts: NonNegativeInteger
    status_counts: StatusCounts
    cells: list[CellClaim]
    schedule_stages: list[StageCompletionClaim]
    interval_coverage: list[IntervalCoverageClaim]


class ChartData(StrictPublicationModel):
    schema_version: Literal["1.0"] = "1.0"
    dataset: DatasetName
    grain: Literal["physical_attempt_x_measurement"] = (
        "physical_attempt_x_measurement"
    )
    records: list[ReplicateMetricRow]


class HashRecord(StrictPublicationModel):
    role: NonEmptyString
    path: NonEmptyString
    sha256: Sha256
    byte_count: NonNegativeInteger
    record_count: NonNegativeInteger | None = None


class PublicationBundleCounts(StrictPublicationModel):
    raw_physical_attempts: PositiveInteger
    campaign_attempt_rows: PositiveInteger
    campaign_run_status_rows: PositiveInteger
    campaign_eligibility_datasets: PositiveInteger
    selected_physical_attempts: PositiveInteger
    selected_scheduled_replicates: PositiveInteger
    selected_predictions: NonNegativeInteger
    held_out_measurements: PositiveInteger
    evaluator_scores: PositiveInteger
    run_status_rows: PositiveInteger
    cell_status_rows: PositiveInteger
    replicate_metric_rows: PositiveInteger
    task_metric_summary_rows: PositiveInteger


class DatasetGateProvenance(StrictPublicationModel):
    dataset: DatasetName
    eligible: Literal[True]
    stages: list[NonEmptyString]
    required_cells: PositiveInteger
    required_replicates_per_cell: PositiveInteger
    actual_cells: PositiveInteger
    actual_scheduled_replicates: PositiveInteger


class PublicationProvenance(StrictPublicationModel):
    schema_version: Literal["1.0"] = "1.0"
    benchmark_version: NonEmptyString
    dataset_gate: DatasetGateProvenance
    counts: PublicationBundleCounts
    source_hashes: list[HashRecord]
    data_output_hashes: list[HashRecord]


class PublicationHashManifest(StrictPublicationModel):
    schema_version: Literal["1.0"] = "1.0"
    algorithm: Literal["sha256"] = "sha256"
    dataset: DatasetName
    source_hashes: list[HashRecord]
    output_hashes: list[HashRecord]
    self_excluded_path: Literal["sha256_manifest.json"] = "sha256_manifest.json"
