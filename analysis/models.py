from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from eng_bench.models import Prediction, RunManifest, RunStatus, Sha256


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
HexDigest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PositiveInteger = Annotated[int, Field(ge=1)]
SystemName = Literal["codex", "claude"]


class StrictAnalysisModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class RunnerClassification(StrEnum):
    COMPLETE = "complete"
    MODEL_REFUSAL = "model_refusal"
    MODEL_CONTAMINATION = "model_contamination"
    AGENT_FAILURE = "agent_failure"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


class DatasetName(StrEnum):
    N3 = "n3"
    N5 = "n5"
    ABLATION = "ablation"


class RunMetadata(StrictAnalysisModel):
    run_id: NonEmptyString
    system: SystemName
    requested_model: NonEmptyString
    cli_version: NonEmptyString
    effort: NonEmptyString
    stage: NonEmptyString
    task: NonEmptyString
    replicate: PositiveInteger
    attempt: PositiveInteger
    start_time: datetime
    end_time: datetime
    prompt_sha256: HexDigest
    protocol_manifest_sha256: HexDigest


class RunStatusRecord(StrictAnalysisModel):
    classification: RunnerClassification
    detail: NonEmptyString
    exit_code: int
    canonical_status: RunStatus
    prediction_normalization: NonEmptyString
    served_models: list[NonEmptyString]


class ScheduleReplicate(StrictAnalysisModel):
    stage: NonEmptyString
    task: NonEmptyString
    system: SystemName
    replicate: PositiveInteger

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.stage, self.task, self.system, self.replicate)


class ScheduledLaunch(StrictAnalysisModel):
    sequence: PositiveInteger
    task: NonEmptyString
    system: SystemName
    replicate: PositiveInteger
    stage: NonEmptyString

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.stage, self.task, self.system, self.replicate)


class ScheduleIntegrityRecord(StrictAnalysisModel):
    stage: NonEmptyString
    schedule_sha256: Sha256
    scheduled_replicates: PositiveInteger
    launched_first_attempts: Annotated[int, Field(ge=0)]
    complete_launch_prefix: bool
    first_started_at: datetime | None = None
    last_first_attempt_ended_at: datetime | None = None


class DatasetSpec(StrictAnalysisModel):
    dataset: DatasetName
    stages: tuple[NonEmptyString, ...]
    required_cells: PositiveInteger
    required_replicates_per_cell: PositiveInteger


class IntegrityRecord(StrictAnalysisModel):
    run_id: NonEmptyString
    stage: NonEmptyString
    task_variant: NonEmptyString
    system: SystemName
    replicate: PositiveInteger
    physical_attempt: PositiveInteger
    status: RunStatus
    infrastructure_valid: bool
    artifact_ledger_sha256: Sha256
    metadata_sha256: Sha256
    manifest_sha256: Sha256
    predictions_sha256: Sha256
    input_ledger_sha256: Sha256
    workspace_ledger_sha256: Sha256
    input_file_count: Annotated[int, Field(ge=1)]
    workspace_file_count: Annotated[int, Field(ge=1)]
    artifact_file_count: Annotated[int, Field(ge=1)]


class HarvestedAttempt(StrictAnalysisModel):
    run_directory: Path
    metadata: RunMetadata
    status: RunStatusRecord
    manifest: RunManifest
    predictions: list[Prediction]
    integrity: IntegrityRecord

    @property
    def scheduled_key(self) -> tuple[str, str, str, int]:
        return (
            self.metadata.stage,
            self.metadata.task,
            self.metadata.system,
            self.metadata.replicate,
        )


class CellEligibility(StrictAnalysisModel):
    task_variant: NonEmptyString
    system: SystemName
    expected_replicates: list[PositiveInteger]
    infrastructure_valid_replicates: list[PositiveInteger]
    completed_replicates: list[PositiveInteger]
    missing_replicates: list[PositiveInteger]
    infrastructure_failed_replicates: list[PositiveInteger]
    physical_attempts: Annotated[int, Field(ge=0)]
    eligible: bool


class DatasetEligibility(StrictAnalysisModel):
    dataset: DatasetName
    eligible: bool
    required_cells: Annotated[int, Field(ge=1)]
    required_replicates_per_cell: PositiveInteger
    cells: list[CellEligibility]
    reasons: list[NonEmptyString]


class EligibilityReport(StrictAnalysisModel):
    schema_version: Literal["1.0"] = "1.0"
    datasets: list[DatasetEligibility]
