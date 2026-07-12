from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import Field, model_validator

from nstf_bench.models import NonEmptyString, Prediction, StrictModel


class TaskPrediction(StrictModel):
    metric_id: NonEmptyString
    point: float | None
    p10: float | None
    p50: float | None
    p90: float | None
    units: NonEmptyString
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None
    qualitative: None
    category: NonEmptyString | None
    source_artifact: NonEmptyString

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        path = PurePosixPath(self.source_artifact)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != "output"
            or "#" in self.source_artifact
            or "\\" in self.source_artifact
        ):
            raise ValueError("source_artifact must be a plain relative path under output/")

        numeric_values = (self.point, self.p10, self.p50, self.p90)
        has_numeric = any(value is not None for value in numeric_values)
        if has_numeric:
            if not all(value is not None for value in numeric_values):
                raise ValueError("numeric task predictions require point, p10, p50, and p90")
            if self.category is not None:
                raise ValueError("numeric task predictions must not contain a category")
            if self.confidence is None:
                raise ValueError("numeric task predictions require confidence")
            if self.point != self.p50:
                raise ValueError("numeric task predictions require point == p50")
            if self.p10 is None or self.p50 is None or self.p90 is None:
                raise ValueError("numeric prediction quantiles are incomplete")
            if not self.p10 <= self.p50 <= self.p90:
                raise ValueError("numeric prediction quantiles must satisfy p10 <= p50 <= p90")
            return self

        if self.units != "category" or self.category is None:
            raise ValueError("non-numeric task predictions require category units and a category")
        return self


class AnnexSufficiency(StrictModel):
    status: Annotated[
        str,
        Field(pattern=r"^(sufficient|partially_sufficient|insufficient)$"),
    ]
    missing_physics: list[NonEmptyString]
    consequence: NonEmptyString


class TaskOutput(StrictModel):
    schema_version: Annotated[str, Field(pattern=r"^1\.0$")]
    task_id: NonEmptyString
    predictions: list[TaskPrediction]
    annex_sufficiency: AnnexSufficiency
    most_uncertain_assumption: NonEmptyString

    @model_validator(mode="after")
    def validate_unique_metrics(self) -> Self:
        metric_ids = [prediction.metric_id for prediction in self.predictions]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("task output contains duplicate metric IDs")
        return self


def normalize_task_output(*, run_id: str, task_output: TaskOutput) -> list[Prediction]:
    return [
        Prediction(
            run_id=run_id,
            metric_id=prediction.metric_id,
            point=prediction.point,
            p10=prediction.p10,
            p50=prediction.p50,
            p90=prediction.p90,
            units=prediction.units,
            confidence=prediction.confidence,
            category=prediction.category,
            source_artifact=str(
                PurePosixPath(run_id) / "workspace" / prediction.source_artifact
            ),
        )
        for prediction in task_output.predictions
    ]
