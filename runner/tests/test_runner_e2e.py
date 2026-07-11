from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


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
    with tempfile.TemporaryDirectory(prefix="pytest-isolation-", dir=PREFLIGHT) as temporary:
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
                str(RUNNER / "allowlist.txt"),
                "--log",
                str(probe / "proxy.jsonl"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            wait_for_socket(path=proxy_socket, timeout_seconds=5.0)
            result = run_command(
                arguments=[
                    str(RUNNER / "isolate.sh"),
                    "--workspace",
                    str(workspace),
                    "--runtime",
                    str(runtime),
                    "--",
                    "/runner/isolation-probe.sh",
                ]
            )
            assert result.returncode == 0, result.stderr
            assert "filesystem-hidden=true" in result.stdout
            assert "arbitrary-proxy-blocked=true" in result.stdout
            assert "direct-network-blocked=true" in result.stdout
        finally:
            proxy.terminate()
            proxy.wait(timeout=5.0)


def test_actual_event_streams_distinguish_result_refusal_and_fallback() -> None:
    codex = classify(
        system="codex",
        events=PREFLIGHT / "isolated-ready-v1-codex" / "events.jsonl",
        exit_code=0,
    )
    fable = classify(
        system="claude",
        events=PREFLIGHT / "isolated-heat-flow-v1-claude" / "events.jsonl",
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
