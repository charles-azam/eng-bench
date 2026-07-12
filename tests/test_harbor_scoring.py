from __future__ import annotations

import json
from pathlib import Path

import pytest

from nstf_bench.harbor_scoring import score_task

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS = REPO_ROOT / "measurements/held_out.jsonl"
ORACLE = REPO_ROOT / "harbor/nstf-blind/solution/predictions.json"
VARIANT = "nstf_blind_derive_duty"


def build_workspace(*, root: Path, predictions_text: str | None) -> Path:
    workspace = root / "workspace"
    output = workspace / "output"
    output.mkdir(parents=True)
    (output / "calculation_note.md").write_text("note\n", encoding="utf-8")
    if predictions_text is not None:
        (output / "predictions.json").write_text(predictions_text, encoding="utf-8")
    return workspace


def run(*, workspace: Path, output_dir: Path):
    return score_task(
        predictions_path=workspace / "output/predictions.json",
        task_variant=VARIANT,
        measurements_path=MEASUREMENTS,
        workspace=workspace,
        output_dir=output_dir,
    )


def test_oracle_predictions_score_one(tmp_path: Path) -> None:
    workspace = build_workspace(
        root=tmp_path, predictions_text=ORACLE.read_text(encoding="utf-8")
    )
    summary = run(workspace=workspace, output_dir=tmp_path / "verifier")
    reward = json.loads((tmp_path / "verifier/reward.json").read_text(encoding="utf-8"))
    assert set(reward) == {"reward"}
    assert reward["reward"] == pytest.approx(1.0)
    assert summary.median_normalized_score == pytest.approx(1.0)
    assert summary.required_metrics == 11
    assert summary.predicted_metrics == 11
    assert summary.compliance_rate == 1.0
    assert summary.artifact_validity_rate == 1.0
    assert summary.categorical_pass_rate == 1.0
    assert summary.interval_coverage_rate == 1.0
    assert (tmp_path / "verifier/summary.json").is_file()
    assert (tmp_path / "verifier/scores.jsonl").is_file()


def test_missing_predictions_file_rewards_zero(tmp_path: Path) -> None:
    workspace = build_workspace(root=tmp_path, predictions_text=None)
    summary = run(workspace=workspace, output_dir=tmp_path / "verifier")
    reward = json.loads((tmp_path / "verifier/reward.json").read_text(encoding="utf-8"))
    assert reward == {"reward": 0.0}
    assert summary.parse_error == "predictions_file_missing"
    assert summary.predicted_metrics == 0


def test_malformed_json_rewards_zero(tmp_path: Path) -> None:
    workspace = build_workspace(root=tmp_path, predictions_text="{not json")
    summary = run(workspace=workspace, output_dir=tmp_path / "verifier")
    assert summary.median_normalized_score == 0.0
    assert summary.parse_error is not None and "invalid" in summary.parse_error


def test_wrong_units_fail_compliance_for_that_metric(tmp_path: Path) -> None:
    payload = json.loads(ORACLE.read_text(encoding="utf-8"))
    for prediction in payload["predictions"]:
        if prediction["metric_id"] == "nstf.baseline.mass_flow_kg_s":
            prediction["units"] = "kW"
    workspace = build_workspace(root=tmp_path, predictions_text=json.dumps(payload))
    summary = run(workspace=workspace, output_dir=tmp_path / "verifier")
    metric = summary.per_metric["nstf.baseline.mass_flow_kg_s"]
    assert metric.normalized_score == 0.0
    assert "incompatible_units" in metric.issues
    assert summary.median_normalized_score == pytest.approx(1.0)  # median survives one zero


def test_missing_source_artifact_scores_zero_for_metric(tmp_path: Path) -> None:
    payload = json.loads(ORACLE.read_text(encoding="utf-8"))
    for prediction in payload["predictions"]:
        if prediction["metric_id"] == "nstf.baseline.heated_plate_front_c":
            prediction["source_artifact"] = "output/does_not_exist.md"
    workspace = build_workspace(root=tmp_path, predictions_text=json.dumps(payload))
    summary = run(workspace=workspace, output_dir=tmp_path / "verifier")
    metric = summary.per_metric["nstf.baseline.heated_plate_front_c"]
    assert metric.normalized_score == 0.0
    assert not metric.scorable


def test_deterministic_outputs(tmp_path: Path) -> None:
    workspace = build_workspace(
        root=tmp_path, predictions_text=ORACLE.read_text(encoding="utf-8")
    )
    run(workspace=workspace, output_dir=tmp_path / "first")
    run(workspace=workspace, output_dir=tmp_path / "second")
    for name in ("reward.json", "summary.json", "scores.jsonl"):
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes()


def test_task_id_mismatch_rewards_zero(tmp_path: Path) -> None:
    payload = json.loads(ORACLE.read_text(encoding="utf-8"))
    payload["task_id"] = "nstf_supplied_duty"
    workspace = build_workspace(root=tmp_path, predictions_text=json.dumps(payload))
    summary = run(workspace=workspace, output_dir=tmp_path / "verifier")
    assert summary.median_normalized_score == 0.0
    assert summary.parse_error is not None and "task_id_mismatch" in summary.parse_error
