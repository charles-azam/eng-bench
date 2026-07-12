from __future__ import annotations

import argparse
import shutil
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, field_validator, model_validator

from analysis.gate_eligibility import (
    PROTOCOL_STAGE_PREFIXES,
    V3_EVALUATION_LEDGER_SHA256,
    V3_PROTOCOL_MANIFEST_SHA256,
    GateAttestation,
    build_attestation,
    canonical_json,
    sha256_bytes,
)
from analysis.harvest import validate_raw_root
from analysis.models import DatasetName, RunMetadata, StrictAnalysisModel
from analysis.schedules import PROTOCOL_STAGE_ORDER, discover_schedule_stages


LowercaseKeyHex = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$"),
]
NonEmptyGateList = Annotated[list["DisclosedGateKey"], Field(min_length=1)]


class DisclosedGateKey(StrictAnalysisModel):
    attestation_path: str
    commitment_key_hex: LowercaseKeyHex

    @field_validator("attestation_path")
    @classmethod
    def require_safe_relative_attestation_path(cls, value: str) -> str:
        relative_path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or relative_path.is_absolute()
            or relative_path.as_posix() != value
            or any(part in {".", ".."} for part in relative_path.parts)
            or relative_path.suffix != ".json"
        ):
            raise ValueError(
                "attestation_path must be a canonical relative POSIX .json path"
            )
        return value


class GateKeyDisclosure(StrictAnalysisModel):
    schema_version: Literal["1.0"] = "1.0"
    gates: NonEmptyGateList

    @model_validator(mode="after")
    def require_unique_attestation_paths(self) -> Self:
        paths = [gate.attestation_path for gate in self.gates]
        if len(paths) != len(set(paths)):
            raise ValueError("gate disclosure contains duplicate attestation paths")
        return self


class VerifiedGateDisclosure(StrictAnalysisModel):
    attestation_path: str
    attestation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    commitment_key_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset: DatasetName
    closed_stages: list[str]
    verified: Literal[True] = True


class GateDisclosureVerificationReport(StrictAnalysisModel):
    schema_version: Literal["1.0"] = "1.0"
    gates: list[VerifiedGateDisclosure]
    verified: Literal[True] = True


def require_regular_file(*, path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def load_disclosure(*, path: Path) -> GateKeyDisclosure:
    require_regular_file(path=path, label="gate disclosure")
    return GateKeyDisclosure.model_validate_json(path.read_bytes())


def resolve_attestation_path(*, repository_root: Path, relative_path: str) -> Path:
    if repository_root.is_symlink() or not repository_root.is_dir():
        raise ValueError(
            "repository root must be a regular non-symlink directory: "
            f"{repository_root}"
        )
    candidate = repository_root
    for part in PurePosixPath(relative_path).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(
                f"attestation path must not traverse a symlink: {relative_path!r}"
            )
    require_regular_file(path=candidate, label="gate attestation")
    return candidate


def snapshot_regular_file(*, source: Path, destination: Path, label: str) -> None:
    require_regular_file(path=source, label=label)
    shutil.copyfile(src=source, dst=destination)


def snapshot_regular_tree(*, source: Path, destination: Path, label: str) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"{label} must be a regular non-symlink directory: {source}")
    destination.mkdir()
    for entry in sorted(source.iterdir(), key=lambda path: path.name):
        copied_entry = destination / entry.name
        if entry.is_symlink():
            raise ValueError(f"{label} must not contain symlinks: {entry}")
        if entry.is_dir():
            snapshot_regular_tree(
                source=entry,
                destination=copied_entry,
                label=label,
            )
        elif entry.is_file():
            snapshot_regular_file(
                source=entry,
                destination=copied_entry,
                label=label,
            )
        else:
            raise ValueError(f"{label} may contain only files and directories: {entry}")


def snapshot_run_prefix(
    *, runs_root: Path, destination: Path, closed_stages: tuple[str, ...]
) -> None:
    validate_raw_root(runs_root=runs_root)
    destination.mkdir()
    for run_directory in sorted(runs_root.iterdir(), key=lambda path: path.name):
        lowered_name = run_directory.name.lower()
        if lowered_name.startswith("excluded") or "v1-finalizer-bug" in lowered_name:
            raise ValueError(
                "excluded campaign material was found in the final raw root and was "
                f"not inspected: {run_directory.name!r}"
            )
        if run_directory.is_symlink() or not run_directory.is_dir():
            raise ValueError(
                "final raw root may contain only regular run directories: "
                f"{run_directory}"
            )
        metadata_path = run_directory / "metadata.json"
        require_regular_file(path=metadata_path, label="run metadata")
        metadata = RunMetadata.model_validate_json(metadata_path.read_bytes())
        if metadata.run_id != run_directory.name:
            raise ValueError(
                "raw metadata run ID differs from its directory while selecting a "
                f"closed-stage prefix: {run_directory.name!r}"
            )
        if metadata.stage not in PROTOCOL_STAGE_ORDER:
            raise ValueError(
                f"raw attempt names an unknown protocol stage: {metadata.stage!r}"
            )
        if metadata.stage in closed_stages:
            snapshot_regular_tree(
                source=run_directory,
                destination=destination / run_directory.name,
                label="raw run directory",
            )


def snapshot_schedule_prefix(
    *, schedules_root: Path, destination: Path, closed_stages: tuple[str, ...]
) -> None:
    present_stages = discover_schedule_stages(schedules_root=schedules_root)
    if present_stages not in PROTOCOL_STAGE_PREFIXES:
        raise ValueError(
            f"final schedules are not a registered protocol prefix: {present_stages!r}"
        )
    if any(stage not in present_stages for stage in closed_stages):
        raise ValueError(
            "committed gate references a stage absent from the final public schedules"
        )

    destination.mkdir()
    readme_path = schedules_root / "README.md"
    if readme_path.exists() or readme_path.is_symlink():
        snapshot_regular_file(
            source=readme_path,
            destination=destination / readme_path.name,
            label="schedule provenance README",
        )
    for stage in closed_stages:
        for suffix in (".tsv", ".tsv.sha256"):
            name = f"{stage}{suffix}"
            snapshot_regular_file(
                source=schedules_root / name,
                destination=destination / name,
                label="stage schedule artifact",
            )
        vps_name = f"{stage}.tsv.vps.sha256"
        vps_source = schedules_root / vps_name
        if vps_source.exists() or vps_source.is_symlink():
            snapshot_regular_file(
                source=vps_source,
                destination=destination / vps_name,
                label="VPS schedule checksum",
            )


def verify_disclosed_gate(
    *,
    disclosure: DisclosedGateKey,
    repository_root: Path,
    runs_root: Path,
    matrix_path: Path,
    ledger_path: Path,
    schedules_root: Path,
    frozen_manifest_path: Path,
    registered_frozen_manifest_sha256: str,
    registered_attempt_protocol_manifest_sha256: str,
    registered_evaluation_ledger_sha256: str,
) -> VerifiedGateDisclosure:
    attestation_path = resolve_attestation_path(
        repository_root=repository_root,
        relative_path=disclosure.attestation_path,
    )
    committed_bytes = attestation_path.read_bytes()
    committed = GateAttestation.model_validate_json(committed_bytes)
    closed_stages = tuple(committed.closed_stages)
    if closed_stages not in PROTOCOL_STAGE_PREFIXES:
        raise ValueError(
            f"committed gate has an unregistered closed-stage prefix: {closed_stages!r}"
        )

    commitment_key = bytes.fromhex(disclosure.commitment_key_hex)
    commitment_key_sha256 = sha256_bytes(contents=commitment_key)
    if commitment_key_sha256 != committed.commitment_key_sha256:
        raise ValueError(
            "disclosed commitment key does not match the committed attestation: "
            f"{disclosure.attestation_path!r}"
        )

    with TemporaryDirectory(prefix="eng-bench-gate-disclosure-") as temporary_directory:
        snapshot_root = Path(temporary_directory)
        prefix_runs_root = snapshot_root / "raw"
        prefix_schedules_root = snapshot_root / "schedules"
        snapshot_run_prefix(
            runs_root=runs_root,
            destination=prefix_runs_root,
            closed_stages=closed_stages,
        )
        snapshot_schedule_prefix(
            schedules_root=schedules_root,
            destination=prefix_schedules_root,
            closed_stages=closed_stages,
        )
        commitment_key_path = snapshot_root / "commitment.key"
        commitment_key_path.write_bytes(commitment_key)
        commitment_key_path.chmod(mode=0o600)
        rebuilt = build_attestation(
            runs_root=prefix_runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            schedules_root=prefix_schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            commitment_key_path=commitment_key_path,
            dataset=committed.dataset,
            registered_frozen_manifest_sha256=registered_frozen_manifest_sha256,
            registered_attempt_protocol_manifest_sha256=(
                registered_attempt_protocol_manifest_sha256
            ),
            registered_evaluation_ledger_sha256=(
                registered_evaluation_ledger_sha256
            ),
        )

    if rebuilt != committed:
        raise ValueError(
            "reconstructed gate model does not match the committed attestation: "
            f"{disclosure.attestation_path!r}"
        )
    rebuilt_bytes = f"{canonical_json(model=rebuilt)}\n".encode(encoding="utf-8")
    if rebuilt_bytes != committed_bytes:
        raise ValueError(
            "reconstructed gate bytes do not match the committed attestation: "
            f"{disclosure.attestation_path!r}"
        )
    return VerifiedGateDisclosure(
        attestation_path=disclosure.attestation_path,
        attestation_sha256=sha256_bytes(contents=committed_bytes),
        commitment_key_sha256=commitment_key_sha256,
        dataset=committed.dataset,
        closed_stages=committed.closed_stages,
    )


def verify_gate_disclosure(
    *,
    repository_root: Path,
    disclosure_path: Path,
    runs_root: Path,
    matrix_path: Path,
    ledger_path: Path,
    schedules_root: Path,
    frozen_manifest_path: Path,
    registered_frozen_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_attempt_protocol_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_evaluation_ledger_sha256: str = V3_EVALUATION_LEDGER_SHA256,
) -> GateDisclosureVerificationReport:
    disclosure = load_disclosure(path=disclosure_path)
    verified_gates = [
        verify_disclosed_gate(
            disclosure=gate,
            repository_root=repository_root,
            runs_root=runs_root,
            matrix_path=matrix_path,
            ledger_path=ledger_path,
            schedules_root=schedules_root,
            frozen_manifest_path=frozen_manifest_path,
            registered_frozen_manifest_sha256=registered_frozen_manifest_sha256,
            registered_attempt_protocol_manifest_sha256=(
                registered_attempt_protocol_manifest_sha256
            ),
            registered_evaluation_ledger_sha256=(
                registered_evaluation_ledger_sha256
            ),
        )
        for gate in disclosure.gates
    ]
    return GateDisclosureVerificationReport(gates=verified_gates)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analysis.verify_gate_disclosure",
        description=(
            "Reconstruct every committed gate prefix and verify disclosed HMAC keys "
            "against the final public campaign."
        ),
    )
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--disclosure", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--schedules-root", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    return parser


def main(
    *,
    arguments: Sequence[str] | None = None,
    registered_frozen_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_attempt_protocol_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_evaluation_ledger_sha256: str = V3_EVALUATION_LEDGER_SHA256,
) -> int:
    parsed = build_parser().parse_args(args=arguments)
    report = verify_gate_disclosure(
        repository_root=parsed.repository_root,
        disclosure_path=parsed.disclosure,
        runs_root=parsed.runs_root,
        matrix_path=parsed.matrix,
        ledger_path=parsed.ledger,
        schedules_root=parsed.schedules_root,
        frozen_manifest_path=parsed.frozen_manifest,
        registered_frozen_manifest_sha256=registered_frozen_manifest_sha256,
        registered_attempt_protocol_manifest_sha256=(
            registered_attempt_protocol_manifest_sha256
        ),
        registered_evaluation_ledger_sha256=registered_evaluation_ledger_sha256,
    )
    print(canonical_json(model=report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
