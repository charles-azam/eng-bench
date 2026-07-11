from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from analysis.eligibility import (
    DATASET_SPECS,
    build_eligibility_report,
    dataset_schedule_keys,
    group_and_validate_attempts,
    load_matrix,
)
from analysis.integrity import load_and_verify_attempt
from analysis.models import (
    DatasetEligibility,
    DatasetName,
    EligibilityReport,
    HarvestedAttempt,
)
from analysis.schedules import verify_schedules
from eng_bench.models import FrozenLedger, Prediction, RunManifest


def canonical_json(*, value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def serialize_model(*, model: BaseModel) -> str:
    return canonical_json(value=model.model_dump(mode="json"))


def write_jsonl(*, path: Path, models: Sequence[BaseModel]) -> None:
    contents = "".join(f"{serialize_model(model=model)}\n" for model in models)
    path.write_text(contents, encoding="utf-8")


def validate_raw_root(*, runs_root: Path) -> None:
    lowered_parts = {part.lower() for part in runs_root.parts}
    if "excluded" in lowered_parts or any("v1-finalizer-bug" in part for part in lowered_parts):
        raise ValueError("excluded v1 material must never be used as a harvest root")
    if runs_root.is_symlink() or not runs_root.is_dir():
        raise ValueError(f"raw runs root must be a regular directory: {runs_root}")


def discover_attempts(
    *, runs_root: Path, ledger: FrozenLedger
) -> tuple[HarvestedAttempt, ...]:
    validate_raw_root(runs_root=runs_root)
    attempts: list[HarvestedAttempt] = []
    for entry in sorted(runs_root.iterdir(), key=lambda path: path.name):
        lowered_name = entry.name.lower()
        if lowered_name.startswith("excluded") or "v1-finalizer-bug" in lowered_name:
            raise ValueError(
                f"excluded v1 material was found in the raw root and was not inspected: "
                f"{entry.name!r}"
            )
        if entry.is_symlink() or not entry.is_dir():
            raise ValueError(f"raw runs root may contain only regular run directories: {entry}")
        attempts.append(load_and_verify_attempt(run_directory=entry, ledger=ledger))
    run_ids = [attempt.metadata.run_id for attempt in attempts]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("raw runs contain duplicate run IDs")
    return tuple(attempts)


def write_attempts_csv(
    *,
    path: Path,
    attempts: tuple[HarvestedAttempt, ...],
    eligibility: EligibilityReport,
    dataset_keys: dict[DatasetName, frozenset[tuple[str, str, str, int]]],
) -> None:
    eligibility_by_dataset = {
        dataset.dataset: dataset.eligible for dataset in eligibility.datasets
    }
    fieldnames = [
        "run_id",
        "stage",
        "task_variant",
        "system",
        "scheduled_replicate",
        "physical_attempt",
        "is_retry",
        "is_final_attempt_for_scheduled_replicate",
        "status",
        "infrastructure_valid",
        "included_n3",
        "included_n5",
        "included_ablation",
    ]
    final_attempt_numbers = {
        scheduled_key: max(
            attempt.metadata.attempt
            for attempt in attempts
            if attempt.scheduled_key == scheduled_key
        )
        for scheduled_key in {attempt.scheduled_key for attempt in attempts}
    }
    with path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for attempt in sorted(attempts, key=lambda item: item.metadata.run_id):
            inclusions = {
                dataset: (
                    eligibility_by_dataset[dataset]
                    and attempt.scheduled_key in dataset_keys[dataset]
                )
                for dataset in DatasetName
            }
            writer.writerow(
                {
                    "run_id": attempt.metadata.run_id,
                    "stage": attempt.metadata.stage,
                    "task_variant": attempt.metadata.task,
                    "system": attempt.metadata.system,
                    "scheduled_replicate": attempt.metadata.replicate,
                    "physical_attempt": attempt.metadata.attempt,
                    "is_retry": str(attempt.metadata.attempt == 2).lower(),
                    "is_final_attempt_for_scheduled_replicate": str(
                        attempt.metadata.attempt
                        == final_attempt_numbers[attempt.scheduled_key]
                    ).lower(),
                    "status": attempt.manifest.status.value,
                    "infrastructure_valid": str(
                        attempt.manifest.infrastructure_valid
                    ).lower(),
                    "included_n3": str(inclusions[DatasetName.N3]).lower(),
                    "included_n5": str(inclusions[DatasetName.N5]).lower(),
                    "included_ablation": str(
                        inclusions[DatasetName.ABLATION]
                    ).lower(),
                }
            )


def join_integers(*, values: list[int]) -> str:
    return ";".join(str(value) for value in values)


def write_eligibility_csv(*, path: Path, report: EligibilityReport) -> None:
    fieldnames = [
        "dataset",
        "dataset_eligible",
        "task_variant",
        "system",
        "cell_eligible",
        "expected_replicates",
        "infrastructure_valid_replicates",
        "completed_replicates",
        "missing_replicates",
        "infrastructure_failed_replicates",
        "physical_attempts",
        "dataset_reasons",
    ]
    with path.open(mode="w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for dataset in report.datasets:
            for cell in dataset.cells:
                writer.writerow(
                    {
                        "dataset": dataset.dataset.value,
                        "dataset_eligible": str(dataset.eligible).lower(),
                        "task_variant": cell.task_variant,
                        "system": cell.system,
                        "cell_eligible": str(cell.eligible).lower(),
                        "expected_replicates": join_integers(
                            values=cell.expected_replicates
                        ),
                        "infrastructure_valid_replicates": join_integers(
                            values=cell.infrastructure_valid_replicates
                        ),
                        "completed_replicates": join_integers(
                            values=cell.completed_replicates
                        ),
                        "missing_replicates": join_integers(
                            values=cell.missing_replicates
                        ),
                        "infrastructure_failed_replicates": join_integers(
                            values=cell.infrastructure_failed_replicates
                        ),
                        "physical_attempts": cell.physical_attempts,
                        "dataset_reasons": " | ".join(dataset.reasons),
                    }
                )


def select_dataset_attempts(
    *,
    attempts: tuple[HarvestedAttempt, ...],
    eligibility: DatasetEligibility,
    scheduled_keys: frozenset[tuple[str, str, str, int]],
) -> tuple[HarvestedAttempt, ...]:
    if not eligibility.eligible:
        return ()
    return tuple(
        sorted(
            (
                attempt
                for attempt in attempts
                if attempt.scheduled_key in scheduled_keys
            ),
            key=lambda item: item.metadata.run_id,
        )
    )


def write_dataset(
    *, output_directory: Path, attempts: tuple[HarvestedAttempt, ...]
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    manifests: list[RunManifest] = [attempt.manifest for attempt in attempts]
    predictions: list[Prediction] = sorted(
        (
            prediction
            for attempt in attempts
            for prediction in attempt.predictions
        ),
        key=lambda item: (item.run_id, item.metric_id),
    )
    write_jsonl(path=output_directory / "manifests.jsonl", models=manifests)
    write_jsonl(path=output_directory / "predictions.jsonl", models=predictions)


def validate_output_location(*, runs_root: Path, output_directory: Path) -> None:
    resolved_runs = runs_root.resolve()
    resolved_output = output_directory.resolve()
    if resolved_output == resolved_runs or resolved_output.is_relative_to(resolved_runs):
        raise ValueError("harvest output must be outside the immutable raw runs root")


def harvest(
    *,
    runs_root: Path,
    matrix_path: Path,
    ledger_path: Path,
    output_directory: Path,
    schedules_root: Path | None = None,
) -> EligibilityReport:
    validate_output_location(runs_root=runs_root, output_directory=output_directory)
    ledger = FrozenLedger.model_validate_json(ledger_path.read_text(encoding="utf-8"))
    schedule = load_matrix(matrix_path=matrix_path)
    attempts = discover_attempts(runs_root=runs_root, ledger=ledger)
    grouped_attempts = group_and_validate_attempts(
        attempts=attempts,
        schedule=schedule,
    )
    schedule_integrity = (
        verify_schedules(
            schedules_root=schedules_root,
            matrix_schedule=schedule,
            grouped_attempts=grouped_attempts,
        )
        if schedules_root is not None
        else ()
    )
    eligibility = build_eligibility_report(
        schedule=schedule,
        grouped_attempts=grouped_attempts,
    )
    eligibility_by_name = {
        dataset.dataset: dataset for dataset in eligibility.datasets
    }
    keys_by_name = {
        spec.dataset: dataset_schedule_keys(schedule=schedule, spec=spec)
        for spec in DATASET_SPECS
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "eligibility.json").write_text(
        f"{serialize_model(model=eligibility)}\n",
        encoding="utf-8",
    )
    write_eligibility_csv(
        path=output_directory / "eligibility.csv",
        report=eligibility,
    )
    write_attempts_csv(
        path=output_directory / "attempts.csv",
        attempts=attempts,
        eligibility=eligibility,
        dataset_keys=keys_by_name,
    )
    write_jsonl(
        path=output_directory / "integrity.jsonl",
        models=[
            attempt.integrity
            for attempt in sorted(attempts, key=lambda item: item.metadata.run_id)
        ],
    )
    write_jsonl(
        path=output_directory / "schedule_integrity.jsonl",
        models=list(schedule_integrity),
    )
    for spec in DATASET_SPECS:
        selected_attempts = select_dataset_attempts(
            attempts=attempts,
            eligibility=eligibility_by_name[spec.dataset],
            scheduled_keys=keys_by_name[spec.dataset],
        )
        write_dataset(
            output_directory=output_directory / spec.dataset.value,
            attempts=selected_attempts,
        )
    return eligibility


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analysis.harvest",
        description="Verify immutable benchmark runs and assemble gated scoring inputs.",
    )
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--schedules-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(*, arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(args=arguments)
    report = harvest(
        runs_root=parsed.runs_root,
        matrix_path=parsed.matrix,
        ledger_path=parsed.ledger,
        output_directory=parsed.output_dir,
        schedules_root=parsed.schedules_root,
    )
    print(serialize_model(model=report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
