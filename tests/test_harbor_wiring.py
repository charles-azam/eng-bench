"""Drift guard: the derived copies inside harbor/ must match their canonical sources.

scripts/sync_harbor_assets.py is the only writer of these copies. If this test fails,
rerun it: uv run python scripts/sync_harbor_assets.py
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TASKS = {
    "nstf-blind": "nstf_blind_derive_duty",
    "nstf-supplied-duty": "nstf_supplied_duty",
}


def assert_same_bytes(*, canonical: Path, copy: Path) -> None:
    assert copy.is_file(), f"missing derived copy: {copy}"
    assert copy.read_bytes() == canonical.read_bytes(), (
        f"{copy} drifted from {canonical}; rerun scripts/sync_harbor_assets.py"
    )


def test_pack_copies_match_frozen_sources() -> None:
    for task_name, variant in TASKS.items():
        pack = REPO_ROOT / "harbor" / task_name / "environment/pack"
        assert_same_bytes(
            canonical=REPO_ROOT / f"inputs/{variant}/TASK.md",
            copy=pack / "TASK.md",
        )
        for source in sorted((REPO_ROOT / "inputs/nstf_common/inputs").iterdir()):
            assert_same_bytes(canonical=source, copy=pack / "inputs" / source.name)
    assert_same_bytes(
        canonical=REPO_ROOT
        / "inputs/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv",
        copy=REPO_ROOT
        / "harbor/nstf-supplied-duty/environment/pack/inputs/05_supplied_thermal_duty.csv",
    )
    blind_inputs = {
        path.name
        for path in (
            REPO_ROOT / "harbor/nstf-blind/environment/pack/inputs"
        ).iterdir()
    }
    assert "05_supplied_thermal_duty.csv" not in blind_inputs


def test_held_out_and_scorer_copies_match() -> None:
    for task_name in TASKS:
        tests_dir = REPO_ROOT / "harbor" / task_name / "tests"
        assert_same_bytes(
            canonical=REPO_ROOT / "expected_output/held_out.jsonl",
            copy=tests_dir / "held_out.jsonl",
        )
        canonical_modules = sorted(
            path.name for path in (REPO_ROOT / "src/nstf_bench").glob("*.py")
        )
        vendored_modules = sorted(
            path.name for path in (tests_dir / "nstf_bench").glob("*.py")
        )
        assert vendored_modules == canonical_modules
        for name in canonical_modules:
            assert_same_bytes(
                canonical=REPO_ROOT / "src/nstf_bench" / name,
                copy=tests_dir / "nstf_bench" / name,
            )


def test_instruction_embeds_prompt_verbatim() -> None:
    prompt = (REPO_ROOT / "protocol/PROMPT.md").read_text(encoding="utf-8")
    for task_name in TASKS:
        instruction = (
            REPO_ROOT / "harbor" / task_name / "instruction.md"
        ).read_text(encoding="utf-8")
        assert prompt in instruction


def test_verifier_scripts_target_their_variant() -> None:
    for task_name, variant in TASKS.items():
        test_sh = (
            REPO_ROOT / "harbor" / task_name / "tests/test.sh"
        ).read_text(encoding="utf-8")
        assert f"--task-variant {variant}" in test_sh
        assert "reward.json" in test_sh


def test_oracle_predictions_match_generator() -> None:
    import json
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from sync_harbor_assets import oracle_predictions
    finally:
        sys.path.pop(0)
    for task_name, variant in TASKS.items():
        committed = json.loads(
            (REPO_ROOT / "harbor" / task_name / "solution/predictions.json").read_text(
                encoding="utf-8"
            )
        )
        assert committed == oracle_predictions(variant=variant)
