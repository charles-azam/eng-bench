from __future__ import annotations

import re
import subprocess
from pathlib import Path

from eng_bench.io import load_jsonl
from eng_bench.models import Measurement


REPO_ROOT = Path(__file__).resolve().parents[1]
CASES = ("a1", "a2", "b", "c1", "c2")


def nstf_metric_ids(*, task_path: Path) -> set[str]:
    task = task_path.read_text(encoding="utf-8")
    return set(re.findall(pattern=r"\| `(nstf\.[^`]+)` \|", string=task))


def triso_metric_ids(*, task_path: Path) -> set[str]:
    task = task_path.read_text(encoding="utf-8")
    templates = re.findall(pattern=r"`(triso\.<case>\.[^`]+)`", string=task)
    expanded = {
        template.replace("<case>", case)
        for template in templates
        for case in CASES
    }
    explicit = set(re.findall(pattern=r"\| `(triso\.[^`]+)` \|", string=task))
    return expanded | explicit


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
    triso_ids = triso_metric_ids(
        task_path=REPO_ROOT / "tasks/triso_corrected_bounded_annex/TASK.md"
    )

    assert measurement_ids["nstf_blind_derive_duty"] == blind_ids
    assert measurement_ids["nstf_supplied_duty"] == supplied_ids
    assert measurement_ids["triso_corrected_bounded_annex"] == triso_ids
