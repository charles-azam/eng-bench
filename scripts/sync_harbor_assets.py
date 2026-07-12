"""Regenerate the derived copies inside harbor/ from their canonical sources.

The Harbor task directories contain byte-copies of the frozen pack files, the
held-out measurements, and the scorer package, because a docker build context
cannot follow symlinks out of environment/. This script is the single writer of
those copies; tests/test_harbor_wiring.py asserts they never drift.

Usage: uv run python scripts/sync_harbor_assets.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TASKS = {
    "nstf-blind": "nstf_blind_derive_duty",
    "nstf-supplied-duty": "nstf_supplied_duty",
}

INSTRUCTION_PREAMBLE = """\
Your workspace is /app. It contains TASK.md and an inputs/ directory. All relative paths in
TASK.md are relative to /app; write every deliverable under /app/output/.

"""


def sync_pack(*, task_dir: Path, variant: str) -> None:
    pack = task_dir / "environment/pack"
    if pack.exists():
        shutil.rmtree(pack)
    (pack / "inputs").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / f"inputs/{variant}/TASK.md", pack / "TASK.md")
    for source in sorted((REPO_ROOT / "inputs/nstf_common/inputs").iterdir()):
        shutil.copy2(source, pack / "inputs" / source.name)
    if variant == "nstf_supplied_duty":
        shutil.copy2(
            REPO_ROOT / "inputs/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv",
            pack / "inputs/05_supplied_thermal_duty.csv",
        )


def sync_tests(*, task_dir: Path) -> None:
    tests = task_dir / "tests"
    tests.mkdir(exist_ok=True)
    shutil.copy2(
        REPO_ROOT / "expected_output/held_out.jsonl", tests / "held_out.jsonl"
    )
    vendored = tests / "nstf_bench"
    if vendored.exists():
        shutil.rmtree(vendored)
    vendored.mkdir()
    for source in sorted((REPO_ROOT / "src/nstf_bench").glob("*.py")):
        shutil.copy2(source, vendored / source.name)


def sync_instruction(*, task_dir: Path) -> None:
    prompt = (REPO_ROOT / "protocol/PROMPT.md").read_text(encoding="utf-8")
    (task_dir / "instruction.md").write_text(
        INSTRUCTION_PREAMBLE + prompt, encoding="utf-8"
    )


def oracle_predictions(*, variant: str) -> dict:
    predictions = []
    for line in (
        (REPO_ROOT / "expected_output/held_out.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        record = json.loads(line)
        if record["task_variant"] != variant or not record.get("required", True):
            continue
        if record["kind"] == "categorical":
            predictions.append(
                {
                    "metric_id": record["metric_id"],
                    "point": None,
                    "p10": None,
                    "p50": None,
                    "p90": None,
                    "units": "category",
                    "confidence": None,
                    "qualitative": None,
                    "category": record["expected_category"],
                    "source_artifact": "output/calculation_note.md",
                }
            )
            continue
        value = record["value"]
        if record["kind"] == "absolute_temperature":
            p10, p90 = value - 5.0, value + 5.0
        else:
            p10, p90 = value * 0.97, value * 1.03
        predictions.append(
            {
                "metric_id": record["metric_id"],
                "point": value,
                "p10": p10,
                "p50": value,
                "p90": p90,
                "units": record["units"],
                "confidence": 0.9,
                "qualitative": None,
                "category": None,
                "source_artifact": "output/calculation_note.md",
            }
        )
    return {
        "schema_version": "1.0",
        "task_id": variant,
        "predictions": predictions,
        "annex_sufficiency": {
            "status": "sufficient",
            "missing_physics": ["oracle reference answer"],
            "consequence": "none; this is the wiring-check oracle",
        },
        "most_uncertain_assumption": "oracle reference answer built from the held-out records",
    }


def sync_solution(*, task_dir: Path, variant: str) -> None:
    solution = task_dir / "solution"
    solution.mkdir(exist_ok=True)
    payload = json.dumps(oracle_predictions(variant=variant), indent=2, sort_keys=False)
    (solution / "predictions.json").write_text(payload + "\n", encoding="utf-8")


def main() -> None:
    for task_name, variant in TASKS.items():
        task_dir = REPO_ROOT / "harbor" / task_name
        task_dir.mkdir(parents=True, exist_ok=True)
        sync_pack(task_dir=task_dir, variant=variant)
        sync_tests(task_dir=task_dir)
        sync_instruction(task_dir=task_dir)
        sync_solution(task_dir=task_dir, variant=variant)
        print(f"synced {task_dir.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
