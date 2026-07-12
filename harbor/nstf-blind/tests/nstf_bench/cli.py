from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from nstf_bench.integrity import (
    evaluator_manifest_sha256,
    render_evaluator_manifest,
    validate_evaluator_manifest,
)
from nstf_bench.io import load_jsonl, write_json, write_jsonl
from nstf_bench.models import FrozenLedger, Measurement, Prediction, RunManifest
from nstf_bench.scoring import evaluate
from nstf_bench.task_output import TaskOutput, normalize_task_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nstf-bench",
        description="Validate and score frozen nstf-bench run artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="score runs against held-out measurements",
    )
    evaluate_parser.add_argument("--manifests", type=Path, required=True)
    evaluate_parser.add_argument("--predictions", type=Path, required=True)
    evaluate_parser.add_argument("--measurements", type=Path, required=True)
    evaluate_parser.add_argument("--ledger", type=Path, required=True)
    evaluate_parser.add_argument(
        "--evaluator-manifest",
        type=Path,
        default=Path("protocol/evaluator_manifest.sha256"),
    )
    evaluate_parser.add_argument(
        "--evaluator-root",
        type=Path,
        default=Path("."),
    )
    evaluate_parser.add_argument("--artifact-root", type=Path, required=True)
    evaluate_parser.add_argument("--output-dir", type=Path, required=True)
    normalize_parser = subparsers.add_parser(
        "normalize",
        help="validate a task predictions file and inject its frozen run ID",
    )
    normalize_parser.add_argument("--run-id", required=True)
    normalize_parser.add_argument("--task-output", type=Path, required=True)
    normalize_parser.add_argument("--output", type=Path, required=True)
    freeze_parser = subparsers.add_parser(
        "freeze-evaluator",
        help="write the deterministic evaluator source manifest",
    )
    freeze_parser.add_argument("--root", type=Path, default=Path("."))
    freeze_parser.add_argument(
        "--output",
        type=Path,
        default=Path("protocol/evaluator_manifest.sha256"),
    )
    score_task_parser = subparsers.add_parser(
        "score-task",
        help="score one agent workspace Harbor-style (fail-closed, no ledger)",
    )
    score_task_parser.add_argument("--predictions", type=Path, required=True)
    score_task_parser.add_argument("--task-variant", required=True)
    score_task_parser.add_argument("--measurements", type=Path, required=True)
    score_task_parser.add_argument("--workspace", type=Path, required=True)
    score_task_parser.add_argument("--output-dir", type=Path, required=True)
    score_task_parser.add_argument("--agent-logs", type=Path, default=None)
    return parser


def run_evaluate(*, arguments: argparse.Namespace) -> int:
    manifests = load_jsonl(path=arguments.manifests, model_type=RunManifest)
    predictions = load_jsonl(path=arguments.predictions, model_type=Prediction)
    measurements = load_jsonl(path=arguments.measurements, model_type=Measurement)
    ledger = FrozenLedger.model_validate_json(
        arguments.ledger.read_text(encoding="utf-8")
    )
    validate_evaluator_manifest(
        root=arguments.evaluator_root,
        manifest_path=arguments.evaluator_manifest,
        expected_manifest_sha256=ledger.evaluator_manifest_sha256,
    )
    result = evaluate(
        manifests=manifests,
        predictions=predictions,
        measurements=measurements,
        artifact_root=arguments.artifact_root,
        ledger=ledger,
    )
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(path=arguments.output_dir / "scores.jsonl", models=list(result.scores))
    write_json(path=arguments.output_dir / "summary.json", model=result.summary)
    return 0


def run_normalize(*, arguments: argparse.Namespace) -> int:
    task_output = TaskOutput.model_validate_json(
        arguments.task_output.read_text(encoding="utf-8")
    )
    predictions = normalize_task_output(
        run_id=arguments.run_id,
        task_output=task_output,
    )
    write_jsonl(path=arguments.output, models=predictions)
    return 0


def run_freeze_evaluator(*, arguments: argparse.Namespace) -> int:
    manifest_text = render_evaluator_manifest(root=arguments.root)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(manifest_text, encoding="utf-8")
    print(evaluator_manifest_sha256(manifest_path=arguments.output))
    return 0


def run_score_task(*, arguments: argparse.Namespace) -> int:
    from nstf_bench.harbor_scoring import HarborReward, score_task

    try:
        summary = score_task(
            predictions_path=arguments.predictions,
            task_variant=arguments.task_variant,
            measurements_path=arguments.measurements,
            workspace=arguments.workspace,
            output_dir=arguments.output_dir,
            agent_logs_dir=arguments.agent_logs,
        )
        print(f"reward={summary.median_normalized_score}")
    except Exception as error:  # fail-closed: the verifier must always get a reward
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            path=arguments.output_dir / "reward.json",
            model=HarborReward(reward=0.0),
        )
        print(f"score-task failed closed: {type(error).__name__}: {error}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "evaluate":
        return run_evaluate(arguments=arguments)
    if arguments.command == "normalize":
        return run_normalize(arguments=arguments)
    if arguments.command == "freeze-evaluator":
        return run_freeze_evaluator(arguments=arguments)
    if arguments.command == "score-task":
        return run_score_task(arguments=arguments)
    parser.error(f"unsupported command: {arguments.command}")
    return 2
