from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from environment_manifest import verify_runner_manifest


ROOT = Path("/root/bench-v2")
RUNNER = ROOT / "runner"
PREFLIGHT = ROOT / "preflight"


def run_command(*, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args=arguments,
        check=False,
        capture_output=True,
        text=True,
    )


def wait_for_socket(*, path: Path, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.is_socket():
            return
        time.sleep(0.05)
    raise AssertionError(f"socket did not appear: {path}")


def classify(*, system: str, events: Path, exit_code: int) -> dict[str, object]:
    result = run_command(
        arguments=[
            str(RUNNER / "validate-events.sh"),
            "--system",
            system,
            "--events",
            str(events),
            "--exit-code",
            str(exit_code),
        ]
    )
    assert result.returncode == 0, result.stderr
    parsed: dict[str, object] = json.loads(result.stdout)
    return parsed


def test_real_sandbox_hides_measurements_and_denies_arbitrary_network() -> None:
    for system in ("codex", "claude"):
        with tempfile.TemporaryDirectory(
            prefix=f"pytest-isolation-{system}-", dir=PREFLIGHT
        ) as temporary:
            probe = Path(temporary)
            workspace = probe / "workspace"
            runtime = probe / "runtime"
            workspace.mkdir(mode=0o700)
            runtime.mkdir(mode=0o700)
            proxy_socket = runtime / "proxy.sock"
            proxy = subprocess.Popen(
                args=[
                    "python3",
                    str(RUNNER / "connect_proxy.py"),
                    "--socket",
                    str(proxy_socket),
                    "--allowlist",
                    str(RUNNER / f"allowlist-{system}.txt"),
                    "--log",
                    str(probe / "proxy.jsonl"),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                wait_for_socket(path=proxy_socket, timeout_seconds=5.0)
                environment = dict(os.environ)
                environment["BENCH_HOST_SENTINEL"] = "must-not-cross"
                result = subprocess.run(
                    args=[
                        str(RUNNER / "isolate.sh"),
                        "--system",
                        system,
                        "--workspace",
                        str(workspace),
                        "--runtime",
                        str(runtime),
                        "--",
                        "/runner/isolation-probe.sh",
                        "--system",
                        system,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                assert result.returncode == 0, result.stderr
                assert "host-environment-cleared=true" in result.stdout
                assert "sandbox-marker-set=true" in result.stdout
                assert "filesystem-hidden=true" in result.stdout
                assert "selected-credential-mounted=true" in result.stdout
                assert "other-credential-empty=true" in result.stdout
                assert "opposite-provider-blocked=true" in result.stdout
                assert "arbitrary-proxy-blocked=true" in result.stdout
                assert "direct-network-blocked=true" in result.stdout
            finally:
                proxy.terminate()
                proxy.wait(timeout=5.0)


def test_actual_event_streams_distinguish_result_refusal_and_fallback() -> None:
    codex = classify(
        system="codex",
        events=PREFLIGHT / "isolated-ready-v3-codex" / "events.jsonl",
        exit_code=0,
    )
    fable = classify(
        system="claude",
        events=PREFLIGHT / "isolated-heat-flow-v3-claude" / "events.jsonl",
        exit_code=0,
    )
    refusal = classify(
        system="claude",
        events=PREFLIGHT / "isolated-ready-v1-claude" / "events.jsonl",
        exit_code=1,
    )
    contamination = classify(
        system="claude",
        events=PREFLIGHT
        / "fable-variants"
        / "exact-max-safe-switchtrue-fallbacksame"
        / "events.jsonl",
        exit_code=0,
    )

    assert codex["classification"] == "complete"
    assert fable["classification"] == "complete"
    assert refusal["classification"] == "model_refusal"
    assert contamination["classification"] == "model_contamination"

    with tempfile.TemporaryDirectory(
        prefix="pytest-model-id-", dir=PREFLIGHT
    ) as temporary:
        near_miss = Path(temporary) / "events.jsonl"
        for model_id in ("proxy-claude-fable-5", "claude-fable-5-20260711"):
            near_miss.write_text(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"model": model_id},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            assert classify(
                system="claude", events=near_miss, exit_code=0
            )["classification"] == "model_contamination"


def test_exact_scored_invocation_parity_smokes_completed() -> None:
    expected = (
        "a9f4f551c650380391f5a5f608c15b3b6fc4ddb988b0ed7150cc99526c0e8f4f"
        "  INPUT.txt\n"
    )
    for system in ("codex", "claude"):
        probe = PREFLIGHT / f"scored-parity-v3-final-{system}"
        exit_code = int(
            (probe / "exit-code.txt").read_text(encoding="utf-8").strip()
        )
        assert exit_code == 0
        classified = classify(
            system=system,
            events=probe / "events.jsonl",
            exit_code=exit_code,
        )
        assert classified["classification"] == "complete"
        assert (probe / "parity-check.txt").read_text(encoding="utf-8") == "passed\n"
        assert (
            probe / "workspace" / "output" / "parity.txt"
        ).read_text(encoding="utf-8") == expected


def test_prediction_contract_is_validated_and_run_scoped() -> None:
    with tempfile.TemporaryDirectory(prefix="pytest-normalize-", dir=PREFLIGHT) as temporary:
        workspace = Path(temporary) / "workspace"
        output = workspace / "output"
        output.mkdir(parents=True)
        (output / "calculation_note.md").write_text("# Synthetic note\n", encoding="utf-8")
        raw_path = output / "predictions.json"
        task_file = Path(temporary) / "TASK.md"
        task_file.write_text(
            "| Metric ID | Unit | Kind |\n"
            "|---|---|---|\n"
            "| `nstf.synthetic.heat_rate_w` | W | numeric |\n"
            "| `nstf.synthetic.release` | fraction | numeric |\n",
            encoding="utf-8",
        )
        raw = {
            "schema_version": "1.0",
            "task_id": "synthetic_task",
            "predictions": [
                {
                    "metric_id": "nstf.synthetic.heat_rate_w",
                    "point": 1200.0,
                    "p10": 1000.0,
                    "p50": 1200.0,
                    "p90": 1400.0,
                    "units": "W",
                    "confidence": 0.8,
                    "qualitative": None,
                    "category": None,
                    "source_artifact": "output/calculation_note.md",
                }
            ],
            "annex_sufficiency": {
                "status": "partially_sufficient",
                "missing_physics": ["contact resistance"],
                "consequence": "widens the heat-rate interval",
            },
            "most_uncertain_assumption": "contact resistance",
        }
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        normalized_path = Path(temporary) / "predictions.jsonl"
        valid = run_command(
            arguments=[
                sys.executable,
                str(RUNNER / "normalize_predictions.py"),
                "--input",
                str(raw_path),
                "--output",
                str(normalized_path),
                "--workspace",
                str(workspace),
                "--run-id",
                "synthetic-codex-r01-a01",
                "--task-id",
                "synthetic_task",
                "--task-file",
                str(task_file),
            ]
        )
        assert valid.returncode == 0, valid.stderr
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        assert normalized["run_id"] == "synthetic-codex-r01-a01"
        assert normalized["source_artifact"] == (
            "synthetic-codex-r01-a01/workspace/output/calculation_note.md"
        )

        raw["predictions"][0]["p10"] = 1300.0
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        invalid = run_command(
            arguments=[
                sys.executable,
                str(RUNNER / "normalize_predictions.py"),
                "--input",
                str(raw_path),
                "--output",
                str(normalized_path),
                "--workspace",
                str(workspace),
                "--run-id",
                "synthetic-codex-r01-a01",
                "--task-id",
                "synthetic_task",
                "--task-file",
                str(task_file),
            ]
        )
        assert invalid.returncode != 0
        assert "numeric quantiles must satisfy" in invalid.stderr

        raw["predictions"][0]["p10"] = 1000.0
        raw["predictions"][0]["metric_id"] = "nstf.synthetic.unregistered_w"
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        unknown_metric = run_command(
            arguments=[
                sys.executable,
                str(RUNNER / "normalize_predictions.py"),
                "--input",
                str(raw_path),
                "--output",
                str(normalized_path),
                "--workspace",
                str(workspace),
                "--run-id",
                "synthetic-codex-r01-a01",
                "--task-id",
                "synthetic_task",
                "--task-file",
                str(task_file),
            ]
        )
        assert unknown_metric.returncode != 0
        assert "unknown metric IDs" in unknown_metric.stderr

        raw["predictions"][0]["metric_id"] = "nstf.synthetic.release"
        raw["predictions"][0]["units"] = "fraction"
        raw["predictions"][0]["point"] = 1.2
        raw["predictions"][0]["p10"] = 0.8
        raw["predictions"][0]["p50"] = 1.2
        raw["predictions"][0]["p90"] = 1.4
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        invalid_fraction = run_command(
            arguments=[
                sys.executable,
                str(RUNNER / "normalize_predictions.py"),
                "--input",
                str(raw_path),
                "--output",
                str(normalized_path),
                "--workspace",
                str(workspace),
                "--run-id",
                "synthetic-codex-r01-a01",
                "--task-id",
                "synthetic_task",
                "--task-file",
                str(task_file),
            ]
        )
        assert invalid_fraction.returncode != 0
        assert "must be in (0, 1]" in invalid_fraction.stderr

        raw["predictions"][0]["metric_id"] = "nstf.synthetic.heat_rate_w"
        raw["predictions"][0]["units"] = "W"
        raw["predictions"][0]["point"] = 1200.0
        raw["predictions"][0]["p10"] = 1000.0
        raw["predictions"][0]["p50"] = 1200.0
        raw["predictions"][0]["p90"] = 1400.0
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        (output / "calculation_note.md").unlink()
        missing_note = run_command(
            arguments=[
                sys.executable,
                str(RUNNER / "normalize_predictions.py"),
                "--input",
                str(raw_path),
                "--output",
                str(normalized_path),
                "--workspace",
                str(workspace),
                "--run-id",
                "synthetic-codex-r01-a01",
                "--task-id",
                "synthetic_task",
                "--task-file",
                str(task_file),
            ]
        )
        assert missing_note.returncode != 0
        assert "output/calculation_note.md" in missing_note.stderr


def test_protocol_verifier_rejects_unlisted_files() -> None:
    with tempfile.TemporaryDirectory(prefix="pytest-protocol-", dir=PREFLIGHT) as temporary:
        protocol = Path(temporary)
        (protocol / "FROZEN").write_text("protocol_version=test\n", encoding="utf-8")
        manifest = protocol / "manifest.sha256"
        digest = subprocess.run(
            args=["sha256sum", "./FROZEN"],
            cwd=protocol,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        manifest.write_text(digest, encoding="utf-8")
        valid = run_command(
            arguments=[
                str(RUNNER / "verify-protocol.sh"),
                "--protocol",
                str(protocol),
            ]
        )
        assert valid.returncode == 0, valid.stderr

        (protocol / "unlisted-measurements.txt").write_text("hidden\n", encoding="utf-8")
        invalid = run_command(
            arguments=[
                str(RUNNER / "verify-protocol.sh"),
                "--protocol",
                str(protocol),
            ]
        )
        assert invalid.returncode != 0
        assert "unlisted-measurements.txt" in invalid.stdout


def test_runner_verifier_rejects_unlisted_source_files(tmp_path: Path) -> None:
    runner_root = tmp_path / "runner"
    runner_root.mkdir()
    source = runner_root / "tool.py"
    source.write_text("print('frozen')\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = tmp_path / "runner.sha256"
    manifest.write_text(f"{digest}  ./tool.py\n", encoding="utf-8")

    verify_runner_manifest(path=manifest, runner_root=runner_root)

    (runner_root / "unlisted.py").write_text("print('drift')\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unrecorded"):
        verify_runner_manifest(path=manifest, runner_root=runner_root)


def test_finalizer_writes_a_manifest_for_no_model_infrastructure_failure() -> None:
    runs_root = ROOT / "runs"
    with tempfile.TemporaryDirectory(prefix="pytest-finalize-", dir=runs_root) as temporary:
        run_dir = Path(temporary)
        workspace = run_dir / "workspace"
        workspace.mkdir(mode=0o700)
        run_id = run_dir.name
        (run_dir / "events.jsonl").write_text(
            '{"type":"error","message":"isolation process failed"}\n',
            encoding="utf-8",
        )
        (run_dir / "stderr.log").write_text("isolation process failed\n", encoding="utf-8")
        (run_dir / "status.json").write_text(
            json.dumps(
                {
                    "classification": "infrastructure_failure",
                    "detail": "synthetic runner failure",
                    "exit_code": 70,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "system": "codex",
                    "requested_model": "gpt-5.6-sol",
                    "cli_version": "codex-cli 0.144.1",
                    "effort": "max",
                    "task": "nstf_blind_derive_duty",
                    "attempt": 1,
                    "start_time": "2026-07-11T21:00:00Z",
                    "end_time": "2026-07-11T21:00:01Z",
                    "prompt_sha256": "a" * 64,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "input.sha256").write_text("", encoding="utf-8")

        finalized = run_command(
            arguments=[
                str(RUNNER / "finalize-run.sh"),
                "--run-dir",
                str(run_dir),
            ]
        )
        assert finalized.returncode == 0, finalized.stderr
        manifest = json.loads((run_dir / "manifest.jsonl").read_text(encoding="utf-8"))
        assert manifest["run_id"] == run_id
        assert manifest["status"] == "runner_failure"
        assert manifest["served_models"] == []
        status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        assert status["canonical_status"] == "runner_failure"
        assert status["prediction_normalization"] == "not_attempted"
        assert status["served_models"] == []


def test_finalizer_writes_a_manifest_for_malformed_claude_trace() -> None:
    runs_root = ROOT / "runs"
    with tempfile.TemporaryDirectory(prefix="pytest-finalize-", dir=runs_root) as temporary:
        run_dir = Path(temporary)
        workspace = run_dir / "workspace"
        workspace.mkdir(mode=0o700)
        run_id = run_dir.name
        (run_dir / "events.jsonl").write_text(
            '{"type":"assistant","message":', encoding="utf-8"
        )
        (run_dir / "stderr.log").write_text(
            "event stream ended mid-record\n", encoding="utf-8"
        )
        (run_dir / "status.json").write_text(
            json.dumps(
                {
                    "classification": "infrastructure_failure",
                    "detail": "malformed Claude JSONL",
                    "exit_code": 70,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "system": "claude",
                    "requested_model": "claude-fable-5",
                    "cli_version": "claude-code synthetic",
                    "effort": "max",
                    "task": "nstf_blind_derive_duty",
                    "attempt": 1,
                    "start_time": "2026-07-11T21:00:00Z",
                    "end_time": "2026-07-11T21:00:01Z",
                    "prompt_sha256": "b" * 64,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "input.sha256").write_text("", encoding="utf-8")

        finalized = run_command(
            arguments=[
                str(RUNNER / "finalize-run.sh"),
                "--run-dir",
                str(run_dir),
            ]
        )
        assert finalized.returncode == 0, finalized.stderr

        manifest = json.loads(
            (run_dir / "manifest.jsonl").read_text(encoding="utf-8")
        )
        status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "runner_failure"
        assert manifest["served_models"] == []
        assert status["canonical_status"] == "runner_failure"
        assert status["served_models"] == []
