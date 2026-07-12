from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import Field

from analysis.eligibility import DATASET_SPECS, load_matrix, schedules_for_spec
from analysis.harvest import harvest
from analysis.models import (
    DatasetEligibility,
    DatasetName,
    EligibilityReport,
    IntegrityRecord,
    PositiveInteger,
    RunMetadata,
    ScheduleIntegrityRecord,
    StrictAnalysisModel,
    SystemName,
)


V3_PROTOCOL_MANIFEST_SHA256 = (
    "29429843b248aa75c45cd47befa9029d2d94024144e6fcb02cc0ffe7f8bab5c3"
)
V3_EVALUATION_LEDGER_SHA256 = (
    "78999d11e9584dd7d3e938574ac1aecd68bd1e960a9b1a1d36066ea67a2bc799"
)
PROTOCOL_STAGE_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("core-n3",),
    ("core-n3", "core-extend-n5"),
    ("core-n3", "core-extend-n5", "nstf-duty-ablation-n3"),
)


class GateCell(StrictAnalysisModel):
    task_variant: str
    system: SystemName
    expected_replicates: list[PositiveInteger]
    infrastructure_valid_replicates: list[PositiveInteger]
    physical_attempts: PositiveInteger


class GateAttestation(StrictAnalysisModel):
    schema_version: Literal["1.0"] = "1.0"
    dataset: DatasetName
    attempts_hmac_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    commitment_key_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligibility_hmac_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    integrity_hmac_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ledger_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schedule_integrity_hmac_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_cells: PositiveInteger
    required_replicates_per_cell: PositiveInteger
    closed_stages: list[str]
    cells: list[GateCell]
    eligible: Literal[True] = True


def sha256_bytes(*, contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def hmac_sha256_bytes(*, key: bytes, contents: bytes) -> str:
    return hmac.new(key=key, msg=contents, digestmod=hashlib.sha256).hexdigest()


def load_commitment_key(*, path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("gate commitment key must be a regular non-symlink file")
    if path.stat().st_mode & 0o077:
        raise ValueError("gate commitment key must not be accessible to group or other")
    key = path.read_bytes()
    if len(key) != 32:
        raise ValueError("gate commitment key must contain exactly 32 random bytes")
    return key


def frozen_matrix_sha256(*, manifest_contents: bytes) -> str:
    records: list[str] = []
    for line in manifest_contents.decode(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            raise ValueError("frozen manifest contains a malformed checksum record")
        digest, path = fields
        if path == "./matrix.tsv":
            records.append(digest)
    if len(records) != 1:
        raise ValueError("frozen manifest must contain exactly one ./matrix.tsv record")
    digest = records[0]
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("frozen manifest matrix checksum is not lowercase SHA-256")
    return digest


def selected_dataset(
    *, report: EligibilityReport, dataset: DatasetName
) -> DatasetEligibility:
    matching = [record for record in report.datasets if record.dataset is dataset]
    if len(matching) != 1:
        raise ValueError(
            f"eligibility report must contain exactly one {dataset.value!r} record"
        )
    return matching[0]


def protocol_spec(*, dataset: DatasetName) -> tuple[int, int]:
    matching = [spec for spec in DATASET_SPECS if spec.dataset is dataset]
    if len(matching) != 1:
        raise ValueError(
            f"analysis has no unique protocol specification for {dataset.value!r}"
        )
    return (
        matching[0].required_cells,
        matching[0].required_replicates_per_cell,
    )


def matrix_cells(
    *, matrix_path: Path, dataset: DatasetName
) -> dict[tuple[str, str], list[int]]:
    matching = [spec for spec in DATASET_SPECS if spec.dataset is dataset]
    if len(matching) != 1:
        raise ValueError(
            f"analysis has no unique protocol specification for {dataset.value!r}"
        )
    schedule = load_matrix(matrix_path=matrix_path)
    selected = schedules_for_spec(schedule=schedule, spec=matching[0])
    cells: dict[tuple[str, str], list[int]] = {}
    for replicate in selected:
        identity = (replicate.task, replicate.system)
        cells.setdefault(identity, []).append(replicate.replicate)
    return {
        identity: sorted(replicates)
        for identity, replicates in sorted(cells.items())
    }


def snapshot_schedule_directory(
    *, source: Path, destination: Path
) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("schedules root must be a regular non-symlink directory")
    destination.mkdir()
    for entry in sorted(source.iterdir(), key=lambda path: path.name):
        if entry.is_symlink() or not entry.is_file():
            raise ValueError(f"schedules root may contain only regular files: {entry}")
        (destination / entry.name).write_bytes(entry.read_bytes())


def require_closed_eligible_dataset(
    *,
    record: DatasetEligibility,
    expected_cells: dict[tuple[str, str], list[int]],
) -> tuple[GateCell, ...]:
    if not record.eligible:
        raise ValueError(f"dataset {record.dataset.value!r} is not eligible")
    if record.reasons:
        raise ValueError("eligible dataset must not retain ineligibility reasons")
    required_cells, required_replicates_per_cell = protocol_spec(dataset=record.dataset)
    if record.required_cells != required_cells:
        raise ValueError(
            f"dataset declares {record.required_cells} cells; protocol requires {required_cells}"
        )
    if record.required_replicates_per_cell != required_replicates_per_cell:
        raise ValueError(
            "dataset replicate requirement differs from the protocol specification"
        )
    if len(record.cells) != required_cells:
        raise ValueError(
            f"protocol requires {required_cells} cells but report contains {len(record.cells)}"
        )

    cells: list[GateCell] = []
    identities: set[tuple[str, str]] = set()
    for cell in record.cells:
        identity = (cell.task_variant, cell.system)
        if identity in identities:
            raise ValueError(f"dataset contains duplicate cell {identity!r}")
        identities.add(identity)
        expected_replicates = expected_cells.get(identity)
        if expected_replicates is None:
            raise ValueError(
                f"dataset contains cell absent from the frozen matrix: {identity!r}"
            )
        if not cell.eligible:
            raise ValueError(f"dataset contains ineligible cell {identity!r}")
        if cell.expected_replicates != expected_replicates:
            raise ValueError(f"cell {identity!r} has the wrong registered replicates")
        if cell.infrastructure_valid_replicates != expected_replicates:
            raise ValueError(
                f"cell {identity!r} does not have every infrastructure-valid final outcome"
            )
        if cell.missing_replicates:
            raise ValueError(f"cell {identity!r} has missing final outcomes")
        if cell.infrastructure_failed_replicates:
            raise ValueError(f"cell {identity!r} has infrastructure-failed final outcomes")
        if not (
            required_replicates_per_cell
            <= cell.physical_attempts
            <= 2 * required_replicates_per_cell
        ):
            raise ValueError(f"cell {identity!r} has an impossible physical-attempt count")
        cells.append(
            GateCell(
                task_variant=cell.task_variant,
                system=cell.system,
                expected_replicates=cell.expected_replicates,
                infrastructure_valid_replicates=cell.infrastructure_valid_replicates,
                physical_attempts=cell.physical_attempts,
            )
        )
    if identities != set(expected_cells):
        missing = sorted(set(expected_cells) - identities)
        raise ValueError(f"dataset omits frozen matrix cells: {missing!r}")
    return tuple(sorted(cells, key=lambda cell: (cell.task_variant, cell.system)))


def require_protocol_bound_metadata(
    *,
    runs_root: Path,
    integrity_contents: bytes,
    registered_protocol_manifest_sha256: str,
) -> None:
    records = [
        IntegrityRecord.model_validate_json(line)
        for line in integrity_contents.splitlines()
        if line
    ]
    run_ids = [record.run_id for record in records]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("harvested integrity contains duplicate run IDs")
    for record in records:
        if Path(record.run_id).name != record.run_id:
            raise ValueError("harvested integrity contains an unsafe run ID")
        metadata_contents = (runs_root / record.run_id / "metadata.json").read_bytes()
        metadata_sha256 = f"sha256:{sha256_bytes(contents=metadata_contents)}"
        if metadata_sha256 != record.metadata_sha256:
            raise ValueError(
                f"raw metadata changed after harvest: {record.run_id!r}"
            )
        metadata = RunMetadata.model_validate_json(metadata_contents)
        if metadata.run_id != record.run_id:
            raise ValueError("raw metadata run ID differs from harvested integrity")
        if metadata.protocol_manifest_sha256 != registered_protocol_manifest_sha256:
            raise ValueError(
                f"raw attempt is not bound to the registered v3 protocol: {record.run_id!r}"
            )


def require_closed_schedules(
    *, schedule_integrity_contents: bytes
) -> tuple[str, ...]:
    records = [
        ScheduleIntegrityRecord.model_validate_json(line)
        for line in schedule_integrity_contents.splitlines()
        if line
    ]
    if not records:
        raise ValueError("gate requires at least one frozen stage schedule")
    stages = [record.stage for record in records]
    if len(stages) != len(set(stages)):
        raise ValueError("schedule integrity contains duplicate stages")
    incomplete = [
        record.stage
        for record in records
        if not record.complete_launch_prefix
        or record.launched_first_attempts != record.scheduled_replicates
    ]
    if incomplete:
        raise ValueError(f"scheduled stages are not closed: {sorted(incomplete)!r}")
    return tuple(stages)


def require_registered_dataset_selection(
    *,
    report: EligibilityReport,
    closed_stages: tuple[str, ...],
    requested_dataset: DatasetName,
) -> None:
    if closed_stages not in PROTOCOL_STAGE_PREFIXES:
        raise ValueError(
            f"closed stage set is not a registered protocol prefix: {closed_stages!r}"
        )
    if requested_dataset is DatasetName.ABLATION:
        if "nstf-duty-ablation-n3" not in closed_stages:
            raise ValueError("ablation cannot be selected before its stage is closed")
        return

    n5 = selected_dataset(report=report, dataset=DatasetName.N5)
    selected_primary = (
        DatasetName.N5
        if "core-extend-n5" in closed_stages and n5.eligible
        else DatasetName.N3
    )
    if requested_dataset is not selected_primary:
        raise ValueError(
            f"registered primary selection is {selected_primary.value!r}, "
            f"not {requested_dataset.value!r}"
        )


def build_attestation(
    *,
    runs_root: Path,
    matrix_path: Path,
    ledger_path: Path,
    schedules_root: Path,
    frozen_manifest_path: Path,
    commitment_key_path: Path,
    dataset: DatasetName,
    registered_frozen_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_attempt_protocol_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_evaluation_ledger_sha256: str = V3_EVALUATION_LEDGER_SHA256,
) -> GateAttestation:
    matrix_contents = matrix_path.read_bytes()
    ledger_contents = ledger_path.read_bytes()
    frozen_manifest_contents = frozen_manifest_path.read_bytes()
    commitment_key = load_commitment_key(path=commitment_key_path)
    actual_frozen_manifest_sha256 = sha256_bytes(contents=frozen_manifest_contents)
    if actual_frozen_manifest_sha256 != registered_frozen_manifest_sha256:
        raise ValueError("frozen protocol manifest digest is not the registered v3 digest")
    actual_ledger_sha256 = sha256_bytes(contents=ledger_contents)
    if actual_ledger_sha256 != registered_evaluation_ledger_sha256:
        raise ValueError("evaluation ledger digest is not the registered v3 digest")
    expected_matrix_sha256 = frozen_matrix_sha256(
        manifest_contents=frozen_manifest_contents
    )
    actual_matrix_sha256 = sha256_bytes(contents=matrix_contents)
    if actual_matrix_sha256 != expected_matrix_sha256:
        raise ValueError("matrix bytes disagree with the frozen protocol manifest")

    with TemporaryDirectory(prefix="eng-bench-gate-harvest-") as temporary_directory:
        snapshot_root = Path(temporary_directory)
        snapshot_matrix_path = snapshot_root / "matrix.tsv"
        snapshot_matrix_path.write_bytes(matrix_contents)
        snapshot_ledger_path = snapshot_root / "evaluation_ledger.json"
        snapshot_ledger_path.write_bytes(ledger_contents)
        snapshot_schedules_root = snapshot_root / "schedules"
        snapshot_schedule_directory(
            source=schedules_root,
            destination=snapshot_schedules_root,
        )
        harvest_directory = snapshot_root / "harvested"
        report = harvest(
            runs_root=runs_root,
            matrix_path=snapshot_matrix_path,
            ledger_path=snapshot_ledger_path,
            output_directory=harvest_directory,
            schedules_root=snapshot_schedules_root,
        )
        eligibility_contents = (harvest_directory / "eligibility.json").read_bytes()
        persisted_report = EligibilityReport.model_validate_json(eligibility_contents)
        if persisted_report != report:
            raise ValueError("harvester return value differs from its eligibility artifact")
        attempts_contents = (harvest_directory / "attempts.csv").read_bytes()
        integrity_contents = (harvest_directory / "integrity.jsonl").read_bytes()
        schedule_integrity_contents = (
            harvest_directory / "schedule_integrity.jsonl"
        ).read_bytes()
        require_protocol_bound_metadata(
            runs_root=runs_root,
            integrity_contents=integrity_contents,
            registered_protocol_manifest_sha256=(
                registered_attempt_protocol_manifest_sha256
            ),
        )
        expected_cells = matrix_cells(
            matrix_path=snapshot_matrix_path,
            dataset=dataset,
        )

    record = selected_dataset(report=report, dataset=dataset)
    cells = require_closed_eligible_dataset(
        record=record,
        expected_cells=expected_cells,
    )
    closed_stages = require_closed_schedules(
        schedule_integrity_contents=schedule_integrity_contents
    )
    require_registered_dataset_selection(
        report=report,
        closed_stages=closed_stages,
        requested_dataset=dataset,
    )
    return GateAttestation(
        dataset=dataset,
        attempts_hmac_sha256=hmac_sha256_bytes(
            key=commitment_key,
            contents=attempts_contents,
        ),
        commitment_key_sha256=sha256_bytes(contents=commitment_key),
        eligibility_hmac_sha256=hmac_sha256_bytes(
            key=commitment_key,
            contents=eligibility_contents,
        ),
        frozen_manifest_sha256=actual_frozen_manifest_sha256,
        integrity_hmac_sha256=hmac_sha256_bytes(
            key=commitment_key,
            contents=integrity_contents,
        ),
        ledger_sha256=actual_ledger_sha256,
        matrix_sha256=actual_matrix_sha256,
        schedule_integrity_hmac_sha256=hmac_sha256_bytes(
            key=commitment_key,
            contents=schedule_integrity_contents
        ),
        required_cells=record.required_cells,
        required_replicates_per_cell=record.required_replicates_per_cell,
        closed_stages=list(closed_stages),
        cells=list(cells),
    )


def canonical_json(*, model: StrictAnalysisModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def write_attestation(*, path: Path, attestation: GateAttestation) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode="x", encoding="utf-8") as stream:
        stream.write(f"{canonical_json(model=attestation)}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analysis.gate_eligibility",
        description=(
            "Fail closed unless a harvested dataset has every registered "
            "infrastructure-valid final outcome."
        ),
    )
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--schedules-root", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    parser.add_argument("--commitment-key", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        choices=[dataset.value for dataset in DatasetName],
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(
    *,
    arguments: Sequence[str] | None = None,
    registered_frozen_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_attempt_protocol_manifest_sha256: str = V3_PROTOCOL_MANIFEST_SHA256,
    registered_evaluation_ledger_sha256: str = V3_EVALUATION_LEDGER_SHA256,
) -> int:
    parsed = build_parser().parse_args(args=arguments)
    attestation = build_attestation(
        runs_root=parsed.runs_root,
        matrix_path=parsed.matrix,
        ledger_path=parsed.ledger,
        schedules_root=parsed.schedules_root,
        frozen_manifest_path=parsed.frozen_manifest,
        commitment_key_path=parsed.commitment_key,
        dataset=DatasetName(parsed.dataset),
        registered_frozen_manifest_sha256=registered_frozen_manifest_sha256,
        registered_attempt_protocol_manifest_sha256=(
            registered_attempt_protocol_manifest_sha256
        ),
        registered_evaluation_ledger_sha256=registered_evaluation_ledger_sha256,
    )
    write_attestation(path=parsed.output, attestation=attestation)
    print(canonical_json(model=attestation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
