#!/usr/bin/env python3
"""Validate a task prediction envelope and add run-scoped evaluator paths."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class RawPrediction(StrictModel):
    metric_id: str = Field(min_length=1)
    point: float | None
    p10: float | None
    p50: float | None
    p90: float | None
    units: str = Field(min_length=1)
    confidence: float | None = Field(ge=0.0, le=1.0)
    qualitative: Literal["dominant", "not_dominant", "uncertain"] | None
    category: str | None
    source_artifact: str = Field(min_length=1)

    @field_validator("source_artifact")
    @classmethod
    def validate_source_artifact(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or not path.parts
            or path.parts[0] != "output"
            or ".." in path.parts
            or "\\" in value
            or "#" in value
        ):
            raise ValueError("source_artifact must be a plain relative path under output/")
        return value

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        numeric = (self.point, self.p10, self.p50, self.p90)
        if self.category is not None:
            if not self.category:
                raise ValueError("categorical predictions require a non-empty category")
            if any(value is not None for value in numeric):
                raise ValueError("categorical predictions must have null numeric fields")
            if self.units != "category" or self.qualitative is not None:
                raise ValueError("categorical predictions require category units and null qualitative")
            return self
        if not all(value is not None for value in numeric):
            raise ValueError("numeric predictions require point, p10, p50, and p90")
        if self.qualitative is not None:
            raise ValueError("numeric predictions require null qualitative")
        if self.confidence is None:
            raise ValueError("numeric predictions require confidence")
        assert self.point is not None
        assert self.p10 is not None
        assert self.p50 is not None
        assert self.p90 is not None
        if self.point != self.p50:
            raise ValueError("numeric point must equal p50")
        if not self.p10 <= self.p50 <= self.p90:
            raise ValueError("numeric quantiles must satisfy p10 <= p50 <= p90")
        return self


class AnnexSufficiency(StrictModel):
    status: Literal["sufficient", "partially_sufficient", "insufficient"]
    missing_physics: list[str]
    consequence: str = Field(min_length=1)


class RawOutput(StrictModel):
    schema_version: Literal["1.0"]
    task_id: str = Field(min_length=1)
    predictions: list[RawPrediction]
    annex_sufficiency: AnnexSufficiency
    most_uncertain_assumption: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_metrics(self) -> Self:
        metric_ids = [prediction.metric_id for prediction in self.predictions]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("prediction metric_id values must be unique")
        return self


class MetricContract(StrictModel):
    metric_id: str = Field(min_length=1)
    units: str = Field(min_length=1)


def parse_arguments(*, arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-file", required=True, type=Path)
    return parser.parse_args(args=arguments)


def load_metric_contracts(*, task_file: Path) -> dict[str, MetricContract]:
    task_text = task_file.read_text(encoding="utf-8")
    rows = re.findall(
        pattern=r"^\| `(nstf\.[^`]+|triso\.[^`]+)` \| ([^|]+) \|",
        string=task_text,
        flags=re.MULTILINE,
    )
    contracts = {
        metric_id: MetricContract(metric_id=metric_id, units=units.strip())
        for metric_id, units in rows
    }
    if not contracts:
        raise ValueError(f"task definition contains no output metric IDs: {task_file}")
    if len(contracts) != len(rows):
        raise ValueError(f"task definition contains duplicate output metric IDs: {task_file}")
    return contracts


def require_workspace_artifact(*, workspace: Path, relative_path: str) -> Path:
    resolved_workspace = workspace.resolve()
    artifact = workspace / relative_path
    if (
        artifact.is_symlink()
        or not artifact.is_file()
        or not artifact.resolve().is_relative_to(resolved_workspace)
    ):
        raise ValueError(f"required source artifact does not exist: {relative_path}")
    return artifact


def normalize(
    *,
    raw_output: RawOutput,
    workspace: Path,
    run_id: str,
    task_id: str,
    metric_contracts: dict[str, MetricContract],
) -> list[dict[str, object]]:
    if raw_output.task_id != task_id:
        raise ValueError(
            f"task_id mismatch: expected {task_id!r}, got {raw_output.task_id!r}"
        )
    unknown_metric_ids = sorted(
        prediction.metric_id
        for prediction in raw_output.predictions
        if prediction.metric_id not in metric_contracts
    )
    if unknown_metric_ids:
        raise ValueError(f"prediction contains unknown metric IDs: {unknown_metric_ids!r}")
    require_workspace_artifact(
        workspace=workspace,
        relative_path="output/calculation_note.md",
    )
    normalized: list[dict[str, object]] = []
    for prediction in raw_output.predictions:
        contract = metric_contracts[prediction.metric_id]
        if prediction.units != contract.units:
            raise ValueError(
                f"metric {prediction.metric_id!r} requires units {contract.units!r}, "
                f"got {prediction.units!r}"
            )
        numeric_values = (prediction.point, prediction.p10, prediction.p50, prediction.p90)
        if contract.units == "fraction" and any(
            value is not None and (value <= 0.0 or value > 1.0)
            for value in numeric_values
        ):
            raise ValueError(
                f"release fraction {prediction.metric_id!r} must be in (0, 1]"
            )
        if contract.units == "count" and any(
            value is not None and value < 0.0 for value in numeric_values
        ):
            raise ValueError(f"count {prediction.metric_id!r} must be non-negative")
        require_workspace_artifact(
            workspace=workspace,
            relative_path=prediction.source_artifact,
        )
        record = prediction.model_dump(mode="json")
        record["run_id"] = run_id
        record["source_artifact"] = (
            f"{run_id}/workspace/{prediction.source_artifact}"
        )
        normalized.append(record)
    return normalized


def main() -> None:
    arguments = parse_arguments()
    raw_output = RawOutput.model_validate_json(
        arguments.input.read_text(encoding="utf-8")
    )
    normalized = normalize(
        raw_output=raw_output,
        workspace=arguments.workspace,
        run_id=arguments.run_id,
        task_id=arguments.task_id,
        metric_contracts=load_metric_contracts(task_file=arguments.task_file),
    )
    lines = [
        json.dumps(
            record,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        for record in normalized
    ]
    arguments.output.write_text(
        "".join(f"{line}\n" for line in lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
