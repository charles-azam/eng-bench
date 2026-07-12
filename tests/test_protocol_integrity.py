from __future__ import annotations

import re
import subprocess
from pathlib import Path

from nstf_bench.integrity import render_evaluator_manifest, validate_evaluator_manifest
from nstf_bench.io import load_jsonl
from nstf_bench.models import FrozenLedger, Measurement


REPO_ROOT = Path(__file__).resolve().parents[1]


def nstf_metric_ids(*, task_path: Path) -> set[str]:
    task = task_path.read_text(encoding="utf-8")
    return set(re.findall(pattern=r"\| `(nstf\.[^`]+)` \|", string=task))


def test_frozen_task_contracts_match_held_out_records_and_pass_leakage_checks() -> None:
    subprocess.run(
        ["bash", "protocol/validate_task_packs.sh"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    measurements = load_jsonl(
        path=REPO_ROOT / "measurements/held_out.jsonl",
        model_type=Measurement,
    )
    measurement_ids = {
        task_variant: {
            measurement.metric_id
            for measurement in measurements
            if measurement.task_variant == task_variant
        }
        for task_variant in {
            measurement.task_variant for measurement in measurements
        }
    }

    blind_ids = nstf_metric_ids(
        task_path=REPO_ROOT / "tasks/nstf_blind_derive_duty/TASK.md"
    )
    supplied_ids = nstf_metric_ids(
        task_path=REPO_ROOT / "tasks/nstf_supplied_duty/TASK.md"
    )

    assert set(measurement_ids) == {"nstf_blind_derive_duty", "nstf_supplied_duty"}
    assert measurement_ids["nstf_blind_derive_duty"] == blind_ids
    assert measurement_ids["nstf_supplied_duty"] == supplied_ids


def test_frozen_evaluator_manifest_covers_exact_sources_and_matches_ledger() -> None:
    manifest_path = REPO_ROOT / "protocol/evaluator_manifest.sha256"
    ledger = FrozenLedger.model_validate_json(
        (REPO_ROOT / "protocol/evaluation_ledger.json").read_text(encoding="utf-8")
    )

    validate_evaluator_manifest(
        root=REPO_ROOT,
        manifest_path=manifest_path,
        expected_manifest_sha256=ledger.evaluator_manifest_sha256,
    )
    assert manifest_path.read_text(encoding="utf-8") == render_evaluator_manifest(
        root=REPO_ROOT
    )
