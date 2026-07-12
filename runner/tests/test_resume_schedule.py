from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from resume_schedule import ARTIFACT_PATHS, ScheduleRow, load_schedule, sha256_file


RUNNER_SOURCE = Path(__file__).resolve().parents[1]
RESUME_SCHEDULE = RUNNER_SOURCE / "resume_schedule.py"


def write_schedule(*, path: Path) -> tuple[ScheduleRow, ...]:
    path.write_text(
        "sequence\ttask\tsystem\treplicate\tstage\n"
        "1\tnstf_blind\tcodex\t1\tcore-v4\n"
        "2\tnstf_blind\tclaude\t1\tcore-v4\n"
        "3\ttriso_bounded\tcodex\t1\tcore-v4\n",
        encoding="utf-8",
    )
    checksum_path = Path(f"{path}.sha256")
    checksum_path.write_text(
        f"{sha256_file(path=path)}  {path}\n",
        encoding="utf-8",
    )
    return load_schedule(schedule_path=path)


def classification_for_status(*, canonical_status: str) -> str:
    if canonical_status == "refusal":
        return "model_refusal"
    if canonical_status == "fallback_contaminated":
        return "model_contamination"
    if canonical_status in {"provider_failure", "runner_failure"}:
        return "infrastructure_failure"
    return "complete"


def write_finalized_attempt(
    *,
    runs_root: Path,
    row: ScheduleRow,
    attempt: int,
    canonical_status: str,
    metadata_replicate: int | None = None,
    requested_model: str | None = None,
    cli_version: str = "synthetic-cli-v4",
    effort: str = "max",
    prompt_sha256: str = "1" * 64,
    protocol_manifest_sha256: str = "2" * 64,
    pack_sha256: str = "3" * 64,
    runner_image_sha256: str = "4" * 64,
) -> Path:
    run_id = row.run_id(attempt=attempt)
    run_directory = runs_root / run_id
    (run_directory / "runtime").mkdir(parents=True)
    metadata = {
        "run_id": run_id,
        "system": row.system,
        "requested_model": requested_model
        or ("gpt-5.6-sol" if row.system == "codex" else "claude-fable-5"),
        "cli_version": cli_version,
        "effort": effort,
        "stage": row.stage,
        "task": row.task,
        "replicate": (
            row.replicate if metadata_replicate is None else metadata_replicate
        ),
        "attempt": attempt,
        "start_time": "2026-07-12T08:00:00Z",
        "end_time": "2026-07-12T08:01:00Z",
        "prompt_sha256": prompt_sha256,
        "protocol_manifest_sha256": protocol_manifest_sha256,
    }
    status = {
        "classification": classification_for_status(
            canonical_status=canonical_status
        ),
        "detail": "synthetic finalized attempt",
        "exit_code": 0,
        "canonical_status": canonical_status,
        "prediction_normalization": "synthetic",
        "served_models": [],
    }
    (run_directory / "metadata.json").write_text(
        json.dumps(obj=metadata), encoding="utf-8"
    )
    (run_directory / "status.json").write_text(
        json.dumps(obj=status), encoding="utf-8"
    )
    manifest = {
        "run_id": run_id,
        "benchmark_version": "synthetic-v4",
        "task_variant": row.task,
        "system": row.system,
        "requested_model": metadata["requested_model"],
        "served_models": status["served_models"],
        "cli_version": cli_version,
        "effort": effort,
        "started_at": metadata["start_time"],
        "ended_at": metadata["end_time"],
        "attempt": attempt,
        "status": canonical_status,
        "prompt_sha256": f"sha256:{prompt_sha256}",
        "pack_sha256": f"sha256:{pack_sha256}",
        "runner_image_sha256": f"sha256:{runner_image_sha256}",
        "trace_path": f"{run_id}/events.jsonl",
        "artifact_paths": [],
    }
    (run_directory / "manifest.jsonl").write_text(
        json.dumps(obj=manifest) + "\n", encoding="utf-8"
    )
    opaque_payloads = {
        "events.jsonl": b"\xff\x00opaque-model-events-not-json\n",
        "stderr.log": b"opaque stderr\n",
        "proxy.jsonl": b"opaque proxy bytes\n",
        "predictions.jsonl": b"\xfdopaque-predictions-not-json\n",
        "input.sha256": b"opaque input ledger\n",
        "workspace.sha256": b"opaque workspace ledger\n",
        "normalization.stderr": b"opaque normalization diagnostics\n",
        "runtime/environment.json": b"opaque initial environment\n",
        "runtime/environment-final.json": b"opaque final environment\n",
    }
    for relative_path, payload in opaque_payloads.items():
        (run_directory / relative_path).write_bytes(payload)
    ledger = "".join(
        f"{sha256_file(path=run_directory / relative_path)}  "
        f"{runs_root / run_id / relative_path}\n"
        for relative_path in ARTIFACT_PATHS
    )
    (run_directory / "artifact.sha256").write_text(ledger, encoding="utf-8")
    return run_directory


def invoke_planner(
    *, schedule_path: Path, runs_root: Path, phase: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args=[
            sys.executable,
            str(RESUME_SCHEDULE),
            "--schedule",
            str(schedule_path),
            "--checksum",
            f"{schedule_path}.sha256",
            "--runs-root",
            str(runs_root),
            "--phase",
            phase,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def assert_rejected(
    *, schedule_path: Path, runs_root: Path, phase: str, message: str
) -> None:
    result = invoke_planner(
        schedule_path=schedule_path,
        runs_root=runs_root,
        phase=phase,
    )
    assert result.returncode != 0
    assert message in result.stderr
    assert result.stdout == ""


def test_resume_lifecycle_preserves_full_schedule_and_registered_retry_order(
    tmp_path: Path,
) -> None:
    schedule_path = tmp_path / "core-v4.tsv"
    rows = write_schedule(path=schedule_path)
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    first = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="primary"
    )
    assert first.returncode == 0, first.stderr
    assert first.stdout == "1\tnstf_blind\tcodex\t1\tcore-v4\t1\n"

    write_finalized_attempt(
        runs_root=runs_root,
        row=rows[0],
        attempt=1,
        canonical_status="completed",
    )
    second = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="primary"
    )
    assert second.returncode == 0, second.stderr
    assert second.stdout == "2\tnstf_blind\tclaude\t1\tcore-v4\t1\n"

    write_finalized_attempt(
        runs_root=runs_root,
        row=rows[1],
        attempt=1,
        canonical_status="provider_failure",
    )
    third = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="primary"
    )
    assert third.returncode == 0, third.stderr
    assert third.stdout == "3\ttriso_bounded\tcodex\t1\tcore-v4\t1\n"

    write_finalized_attempt(
        runs_root=runs_root,
        row=rows[2],
        attempt=1,
        canonical_status="runner_failure",
    )
    primary_closed = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="primary"
    )
    first_retry = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="retry"
    )
    assert primary_closed.returncode == 0, primary_closed.stderr
    assert primary_closed.stdout == ""
    assert first_retry.returncode == 0, first_retry.stderr
    assert first_retry.stdout == "2\tnstf_blind\tclaude\t1\tcore-v4\t2\n"

    write_finalized_attempt(
        runs_root=runs_root,
        row=rows[1],
        attempt=2,
        canonical_status="completed",
    )
    second_retry = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="retry"
    )
    assert second_retry.returncode == 0, second_retry.stderr
    assert second_retry.stdout == "3\ttriso_bounded\tcodex\t1\tcore-v4\t2\n"

    write_finalized_attempt(
        runs_root=runs_root,
        row=rows[2],
        attempt=2,
        canonical_status="runner_failure",
    )
    campaign_closed = invoke_planner(
        schedule_path=schedule_path, runs_root=runs_root, phase="retry"
    )
    assert campaign_closed.returncode == 0, campaign_closed.stderr
    assert campaign_closed.stdout == ""
    assert not (runs_root / rows[2].run_id(attempt=3)).exists()


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    (
        ("gap", "first-attempt directories do not form a schedule prefix"),
        ("incomplete", "artifact checksum ledger must be"),
        ("corrupt", "artifact checksum mismatch"),
        ("identity", "attempt metadata does not match schedule row"),
        ("attempt_three", "only registered attempts a01 and a02"),
        ("schedule_checksum", "does not match its registered checksum"),
    ),
)
def test_resume_rejects_nonfinalized_or_noncanonical_primary_history(
    tmp_path: Path,
    mutation: str,
    expected_message: str,
) -> None:
    schedule_path = tmp_path / "core-v4.tsv"
    rows = write_schedule(path=schedule_path)
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    mutators: dict[str, Callable[[], None]] = {
        "gap": lambda: write_finalized_attempt(
            runs_root=runs_root,
            row=rows[1],
            attempt=1,
            canonical_status="completed",
        ),
        "incomplete": lambda: (runs_root / rows[0].run_id(attempt=1)).mkdir(),
        "corrupt": lambda: (
            write_finalized_attempt(
                runs_root=runs_root,
                row=rows[0],
                attempt=1,
                canonical_status="completed",
            )
            / "events.jsonl"
        ).write_bytes(b"changed after finalization\n"),
        "identity": lambda: write_finalized_attempt(
            runs_root=runs_root,
            row=rows[0],
            attempt=1,
            canonical_status="completed",
            metadata_replicate=99,
        ),
        "attempt_three": lambda: (
            runs_root / rows[0].run_id(attempt=3)
        ).mkdir(),
        "schedule_checksum": lambda: schedule_path.write_text(
            schedule_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        ),
    }
    mutators[mutation]()

    assert_rejected(
        schedule_path=schedule_path,
        runs_root=runs_root,
        phase="primary",
        message=expected_message,
    )


def test_resume_rejects_early_noninfra_and_out_of_order_retries(
    tmp_path: Path,
) -> None:
    schedule_path = tmp_path / "core-v4.tsv"
    rows = write_schedule(path=schedule_path)

    early_root = tmp_path / "early-runs"
    early_root.mkdir()
    write_finalized_attempt(
        runs_root=early_root,
        row=rows[0],
        attempt=1,
        canonical_status="provider_failure",
    )
    write_finalized_attempt(
        runs_root=early_root,
        row=rows[0],
        attempt=2,
        canonical_status="completed",
    )
    assert_rejected(
        schedule_path=schedule_path,
        runs_root=early_root,
        phase="primary",
        message="retry exists before the first-attempt schedule closed",
    )

    noninfra_root = tmp_path / "noninfra-runs"
    noninfra_root.mkdir()
    for row in rows:
        write_finalized_attempt(
            runs_root=noninfra_root,
            row=row,
            attempt=1,
            canonical_status="completed",
        )
    write_finalized_attempt(
        runs_root=noninfra_root,
        row=rows[0],
        attempt=2,
        canonical_status="completed",
    )
    assert_rejected(
        schedule_path=schedule_path,
        runs_root=noninfra_root,
        phase="retry",
        message="retry exists for a non-infrastructure first attempt",
    )

    retry_gap_root = tmp_path / "retry-gap-runs"
    retry_gap_root.mkdir()
    for index, row in enumerate(rows):
        write_finalized_attempt(
            runs_root=retry_gap_root,
            row=row,
            attempt=1,
            canonical_status=(
                "provider_failure" if index in {0, 2} else "completed"
            ),
        )
    write_finalized_attempt(
        runs_root=retry_gap_root,
        row=rows[2],
        attempt=2,
        canonical_status="completed",
    )
    assert_rejected(
        schedule_path=schedule_path,
        runs_root=retry_gap_root,
        phase="retry",
        message="retry directories do not form the eligible schedule prefix",
    )

    frozen_drift_root = tmp_path / "frozen-drift-runs"
    frozen_drift_root.mkdir()
    for index, row in enumerate(rows):
        write_finalized_attempt(
            runs_root=frozen_drift_root,
            row=row,
            attempt=1,
            canonical_status=(
                "provider_failure" if index == 0 else "completed"
            ),
        )
    write_finalized_attempt(
        runs_root=frozen_drift_root,
        row=rows[0],
        attempt=2,
        canonical_status="completed",
        requested_model="different-model",
        cli_version="different-cli",
        effort="different-effort",
        prompt_sha256="5" * 64,
        protocol_manifest_sha256="6" * 64,
        pack_sha256="7" * 64,
        runner_image_sha256="8" * 64,
    )
    drifted_retry = invoke_planner(
        schedule_path=schedule_path,
        runs_root=frozen_drift_root,
        phase="retry",
    )
    assert drifted_retry.returncode != 0
    assert "retry differs from its first attempt on frozen fields" in (
        drifted_retry.stderr
    )
    for field in (
        "requested_model",
        "cli_version",
        "effort",
        "prompt_sha256",
        "protocol_manifest_sha256",
        "pack_sha256",
        "runner_image_sha256",
    ):
        assert field in drifted_retry.stderr
