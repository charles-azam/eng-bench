from __future__ import annotations

import csv
import hashlib
import json
import stat
import subprocess
from pathlib import Path

import pytest
from pydantic import BaseModel

from analysis.blind_review import (
    REVIEW_INSTRUCTIONS,
    RUBRIC_ITEMS,
    BundlePacket,
    CompletedReviewRow,
    HashedSourceFile,
    PacketFile,
    PacketFileRole,
    PacketManifest,
    PacketPayload,
    PublicFileHash,
    PublicProvenance,
    PublicReviewItem,
    PublicRunMapping,
    ReviewBundleManifest,
    ReviewStatus,
    packet_payload_sha256,
    serialize_model,
)
from analysis.gate_eligibility import GateAttestation, canonical_json as gate_json
from analysis.models import IntegrityRecord
from eng_bench.models import RunStatus
from operations.v4_finalization import (
    CORE_ATTESTATION_PATH,
    EXTENSION_ATTESTATION_PATH,
    EvaluationExecutionEnvironment,
    EvaluationFreezeCommitment,
    FinalizedReviewVerification,
    PublicCandidateScanReceipt,
    ReviewDifferenceReceipt,
    ReviewFreezeCommitment,
    canonical_model_bytes,
    main,
    render_completed_review_csv,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def prefixed_digest(*, data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def write_model(*, path: Path, model: BaseModel) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    serialized = serialize_model(model=model)
    path.write_text(f"{serialized}\n", encoding="utf-8", newline="")


def write_evaluation_environment(*, path: Path) -> None:
    write_model(
        path=path,
        model=EvaluationExecutionEnvironment(
            repository_commit="a" * 40,
            python_implementation="CPython",
            python_version="3.13.14",
            python_executable="/synthetic/python",
            python_executable_sha256="b" * 64,
            platform_system="Linux",
            platform_release="synthetic-kernel",
            platform_machine="x86_64",
            byteorder="little",
            uv_lock_sha256="c" * 64,
            evaluator_manifest_sha256="d" * 64,
        ),
    )


def prepare_neutral_review_bundle(
    *, root: Path, include_submitted_output: bool = True
) -> ReviewBundleManifest:
    rubric = (REPOSITORY_ROOT / "protocol" / "ARTIFACT_REVIEW.md").read_bytes()
    rubric_sha256 = prefixed_digest(data=rubric)
    packet_file_contents: dict[str, bytes] = {
        "task-context/task.md": b"# Neutral task\nCompute the supplied case.\n",
    }
    if include_submitted_output:
        packet_file_contents["submitted-output/calculation.md"] = (
            b"# Calculation\nA traceable synthetic result.\n"
        )
    packet_files = [
        PacketFile(
            role=PacketFileRole.TASK_CONTEXT,
            relative_path="task-context/task.md",
            sha256=prefixed_digest(data=packet_file_contents["task-context/task.md"]),
            size_bytes=len(packet_file_contents["task-context/task.md"]),
        ),
    ]
    if include_submitted_output:
        packet_files.append(
            PacketFile(
                role=PacketFileRole.SUBMITTED_OUTPUT,
                relative_path="submitted-output/calculation.md",
                sha256=prefixed_digest(
                    data=packet_file_contents["submitted-output/calculation.md"]
                ),
                size_bytes=len(packet_file_contents["submitted-output/calculation.md"]),
            )
        )
    payload = PacketPayload(
        neutral_label="case-0123456789abcdef",
        task_variant="synthetic-engineering-task",
        benchmark_version="4.0",
        pack_sha256=f"sha256:{'a' * 64}",
        runner_image_sha256=f"sha256:{'b' * 64}",
        rubric_source_sha256=rubric_sha256,
        files=packet_files,
    )
    manifest = PacketManifest(
        **payload.model_dump(mode="python"),
        packet_sha256=packet_payload_sha256(payload=payload),
    )
    packet_root = root / "packets" / payload.neutral_label
    for relative_path, contents in packet_file_contents.items():
        destination = packet_root / relative_path
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        destination.write_bytes(contents)
    write_model(path=packet_root / "packet.json", model=manifest)
    bundle = ReviewBundleManifest(
        ledger_sha256=f"sha256:{'c' * 64}",
        matrix_sha256=f"sha256:{'d' * 64}",
        rubric_source_sha256=rubric_sha256,
        schedule_files=[],
        packets=[
            BundlePacket(
                neutral_label=payload.neutral_label,
                task_variant=payload.task_variant,
                packet_sha256=manifest.packet_sha256,
            )
        ],
    )
    write_model(path=root / "bundle.json", model=bundle)
    (root / "ARTIFACT_REVIEW.md").write_bytes(rubric)
    (root / "REVIEW_INSTRUCTIONS.md").write_text(
        REVIEW_INSTRUCTIONS,
        encoding="utf-8",
        newline="",
    )
    rows = [
        CompletedReviewRow(
            neutral_label=payload.neutral_label,
            packet_sha256=manifest.packet_sha256,
            task_variant=payload.task_variant,
            item_id=item.item_id,
            criterion=item.criterion,
            status=(
                ReviewStatus.NOT_APPLICABLE
                if item.item_id == "no_unavailable_access"
                else (
                    ReviewStatus.FAIL
                    if not include_submitted_output
                    and item.item_id
                    in {"required_note", "artifacts_and_offline_scripts"}
                    else ReviewStatus.PASS
                )
            ),
            rationale=(
                (
                    "No submitted output was available to review; scripts were not executed."
                    if not include_submitted_output
                    else "No applicable scripts: Cited artifacts verified: calculation.md exists."
                )
                if item.item_id == "artifacts_and_offline_scripts"
                else (
                    "The required calculation note was absent."
                    if not include_submitted_output and item.item_id == "required_note"
                    else "Synthetic neutral artifact evidence supports this judgment."
                )
            ),
        )
        for item in RUBRIC_ITEMS
    ]
    (root / "review.csv").write_bytes(render_completed_review_csv(rows=rows))
    return bundle


def synthetic_integrity(*, run_id: str, task_variant: str) -> IntegrityRecord:
    return IntegrityRecord(
        run_id=run_id,
        stage="core-n3",
        task_variant=task_variant,
        system="codex",
        replicate=1,
        physical_attempt=1,
        status=RunStatus.COMPLETED,
        infrastructure_valid=True,
        artifact_ledger_sha256=f"sha256:{'1' * 64}",
        metadata_sha256=f"sha256:{'2' * 64}",
        manifest_sha256=f"sha256:{'3' * 64}",
        predictions_sha256=f"sha256:{'4' * 64}",
        input_ledger_sha256=f"sha256:{'5' * 64}",
        workspace_ledger_sha256=f"sha256:{'6' * 64}",
        input_file_count=1,
        workspace_file_count=1,
        artifact_file_count=1,
    )


def prepare_public_bundle(
    *,
    root: Path,
    review_bundle: Path,
    bundle: ReviewBundleManifest,
    sealed_mapping_sha256: str,
) -> PublicProvenance:
    root.mkdir(mode=0o755)
    completed = (review_bundle / "review.csv").read_bytes()
    rubric = (review_bundle / "ARTIFACT_REVIEW.md").read_bytes()
    instructions = (review_bundle / "REVIEW_INSTRUCTIONS.md").read_bytes()
    packet = bundle.packets[0]
    packet_manifest = PacketManifest.model_validate_json(
        (review_bundle / "packets" / packet.neutral_label / "packet.json").read_bytes()
    )
    run_id = "core-n3-synthetic-engineering-task-codex-r01-a01"
    public_run = PublicRunMapping(
        neutral_label=packet.neutral_label,
        packet_sha256=packet.packet_sha256,
        run_id=run_id,
        system="codex",
        task_variant=packet.task_variant,
        run_status=RunStatus.COMPLETED,
        benchmark_version=packet_manifest.benchmark_version,
        pack_sha256=packet_manifest.pack_sha256,
        runner_image_sha256=packet_manifest.runner_image_sha256,
        integrity=synthetic_integrity(
            run_id=run_id,
            task_variant=packet.task_variant,
        ),
        files=[],
    )
    completed_rows = [
        CompletedReviewRow.model_validate(row)
        for row in csv.DictReader(completed.decode(encoding="utf-8").splitlines())
    ]
    public_items = [
        PublicReviewItem(
            completed_review_sha256=prefixed_digest(data=completed),
            run_id=public_run.run_id,
            system=public_run.system,
            task_variant=row.task_variant,
            run_status=public_run.run_status,
            packet_sha256=row.packet_sha256,
            item_id=row.item_id,
            criterion=row.criterion,
            status=row.status,
            rationale=row.rationale,
        )
        for row in completed_rows
    ]
    public_bytes = {
        "ARTIFACT_REVIEW.md": rubric,
        "REVIEW_INSTRUCTIONS.md": instructions,
        "completed-review.csv": completed,
        "item-review.jsonl": "".join(
            f"{serialize_model(model=item)}\n" for item in public_items
        ).encode(encoding="utf-8"),
        "label-mapping.jsonl": (
            f"{serialize_model(model=public_run)}\n".encode(encoding="utf-8")
        ),
    }
    for name, contents in public_bytes.items():
        (root / name).write_bytes(contents)
    provenance = PublicProvenance(
        completed_review_sha256=prefixed_digest(data=completed),
        sealed_mapping_sha256=sealed_mapping_sha256,
        ledger_sha256=bundle.ledger_sha256,
        matrix_sha256=bundle.matrix_sha256,
        rubric_source_sha256=bundle.rubric_source_sha256,
        schedule_files=[],
        schedules=[],
        campaign_attempts=[],
        runs=[public_run],
        public_files=[
            PublicFileHash(name=name, sha256=prefixed_digest(data=contents))
            for name, contents in public_bytes.items()
        ],
    )
    write_model(path=root / "provenance.json", model=provenance)
    return provenance


def prepare_mapping_freeze(*, root: Path) -> tuple[Path, Path, str]:
    sealed_mapping = root / "sealed-mapping.json"
    mapping_bytes = b'{"opaque":"synthetic-sealed-mapping"}\n'
    sealed_mapping.write_bytes(mapping_bytes)
    sealed_mapping.chmod(mode=0o600)
    mapping_freeze = root / "mapping-freeze.json"
    assert main(
        arguments=[
            "freeze-mapping",
            "--sealed-mapping",
            str(sealed_mapping),
            "--output",
            str(mapping_freeze),
        ]
    ) == 0
    return sealed_mapping, mapping_freeze, prefixed_digest(data=mapping_bytes)


def prepare_editorial_metadata(*, root: Path, review_bundle: Path) -> tuple[Path, Path]:
    completed_review = review_bundle / "review.csv"
    primary_review = root / "primary-review.csv"
    assert main(
        arguments=[
            "snapshot-primary-review",
            "--review-bundle",
            str(review_bundle),
            "--output",
            str(primary_review),
        ]
    ) == 0
    assert primary_review.read_bytes() == completed_review.read_bytes()
    assert stat.S_IMODE(primary_review.stat().st_mode) == 0o400
    draft = root / "reviewer-disclosure-draft.json"
    draft.write_text(
        f"{json.dumps({
            'schema_version': '1.0',
            'completed_review_sha256': prefixed_digest(data=completed_review.read_bytes()),
            'frozen_at': '2026-07-12T13:00:00+02:00',
            'primary_reviewer': {
                'display_name': 'OpenAI Codex',
                'affiliation': 'OpenAI',
                'role': 'Primary artifact reviewer under author authorization',
                'prior_exposure': 'Received only the neutral review bundle for this pass.',
            },
            'second_review': {
                'occurred': False,
                'disclosure': 'No second artifact review was performed.',
            },
            'adjudication': {
                'occurred': False,
                'rows_changed': 0,
                'disclosure': 'No adjudication was performed.',
            },
            'protocol_deviations': [{
                'deviation_id': 'submitted-scripts-not-executed',
                'disclosure': 'The proposed offline runner was withdrawn before review; applicable submitted scripts were not executed and item 6 could not pass for them.',
            }, {
                'deviation_id': 'benchmark-sandbox-exposed-host-secrets',
                'disclosure': 'The frozen benchmark sandbox ran as root and exposed broad host configuration plus live provider credentials; raw attempts remain private and submitted output is scanned before review.',
            }],
        }, allow_nan=False, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}\n",
        encoding="utf-8",
        newline="",
    )
    output = root / "artifact-review-editorial.json"
    assert main(
        arguments=[
            "create-review-disclosure",
            "--review-bundle",
            str(review_bundle),
            "--primary-review",
            str(primary_review),
            "--input",
            str(draft),
            "--output",
            str(output),
        ]
    ) == 0
    return output, primary_review


def synthetic_gate_attestation(
    *, dataset: str, key: bytes, closed_stages: list[str]
) -> GateAttestation:
    return GateAttestation(
        dataset=dataset,
        attempts_hmac_sha256="1" * 64,
        commitment_key_sha256=hashlib.sha256(key).hexdigest(),
        eligibility_hmac_sha256="2" * 64,
        frozen_manifest_sha256="3" * 64,
        integrity_hmac_sha256="4" * 64,
        ledger_sha256="5" * 64,
        matrix_sha256="6" * 64,
        schedule_integrity_hmac_sha256="7" * 64,
        required_cells=1,
        required_replicates_per_cell=1,
        closed_stages=closed_stages,
        cells=[],
    )


def write_gate_attestation(*, root: Path, relative_path: str, model: GateAttestation) -> None:
    destination = root / relative_path
    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    destination.write_text(
        f"{gate_json(model=model)}\n",
        encoding="utf-8",
        newline="",
    )


def run_git(*, repository: Path, arguments: list[str]) -> None:
    subprocess.run(
        args=["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    )


def commit_gate_attestations(*, repository: Path, relative_paths: list[str]) -> None:
    run_git(repository=repository, arguments=["init", "--quiet"])
    run_git(
        repository=repository,
        arguments=["config", "user.name", "Synthetic Test"],
    )
    run_git(
        repository=repository,
        arguments=["config", "user.email", "synthetic@example.invalid"],
    )
    run_git(repository=repository, arguments=["add", "--", *relative_paths])
    run_git(
        repository=repository,
        arguments=["commit", "--quiet", "-m", "Commit synthetic gate attestations"],
    )


def test_evaluation_freeze_is_content_blind_exact_and_new_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    evaluation = repository / "fresh-evaluation"
    dataset_root = evaluation / "n3"
    dataset_root.mkdir(mode=0o755, parents=True)
    scores = b"deliberately opaque and not parsed by this command\n"
    summary = b"not JSON; only its bytes are committed\n"
    (dataset_root / "scores.jsonl").write_bytes(scores)
    (dataset_root / "summary.json").write_bytes(summary)
    selection_source = repository / "eligibility.selection"
    selection_source.write_bytes(b"selected=n3\n")
    execution_environment = repository / "evaluation-environment.json"
    write_evaluation_environment(path=execution_environment)
    output = repository / "evaluation-freeze.json"

    assert main(
        arguments=[
            "freeze-evaluation",
            "--repository-root",
            str(repository),
            "--dataset",
            "n3",
            "--evaluation-root",
            str(evaluation),
            "--execution-environment",
            str(execution_environment),
            "--selection-source",
            str(selection_source),
            "--output",
            str(output),
        ]
    ) == 0
    receipt = json.loads(capsys.readouterr().out)
    commitment = EvaluationFreezeCommitment.model_validate_json(output.read_bytes())
    assert receipt["kind"] == "v4-evaluation-freeze"
    assert commitment.selection_mode == "eligible-datasets"
    assert commitment.datasets == ["n3"]
    assert [record.path for record in commitment.files] == [
        "fresh-evaluation/n3/scores.jsonl",
        "fresh-evaluation/n3/summary.json",
    ]
    assert commitment.files[0].sha256 == hashlib.sha256(scores).hexdigest()
    assert commitment.selection_source.sha256 == hashlib.sha256(
        selection_source.read_bytes()
    ).hexdigest()
    assert output.read_bytes() == canonical_model_bytes(model=commitment)

    with pytest.raises(ValueError, match="must not already exist"):
        main(
            arguments=[
                "freeze-evaluation",
                "--repository-root",
                str(repository),
                "--dataset",
                "n3",
                "--evaluation-root",
                str(evaluation),
                "--execution-environment",
                str(execution_environment),
                "--selection-source",
                str(selection_source),
                "--output",
                str(output),
            ]
        )

    (dataset_root / "unexpected.txt").write_text("not allowed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="entries differ"):
        main(
            arguments=[
                "freeze-evaluation",
                "--repository-root",
                str(repository),
                "--dataset",
                "n3",
                "--evaluation-root",
                str(evaluation),
                "--execution-environment",
                str(execution_environment),
                "--selection-source",
                str(selection_source),
                "--output",
                str(repository / "must-not-exist.json"),
            ]
        )
    assert not (repository / "must-not-exist.json").exists()

    (dataset_root / "unexpected.txt").unlink()
    (dataset_root / "summary.json").unlink()
    symlink_target = repository / "outside-summary.json"
    symlink_target.write_bytes(summary)
    (dataset_root / "summary.json").symlink_to(symlink_target)
    symlink_output = repository / "symlink-must-not-exist.json"
    with pytest.raises(ValueError, match="must not traverse a symlink"):
        main(
            arguments=[
                "freeze-evaluation",
                "--repository-root",
                str(repository),
                "--dataset",
                "n3",
                "--evaluation-root",
                str(evaluation),
                "--execution-environment",
                str(execution_environment),
                "--selection-source",
                str(selection_source),
                "--output",
                str(symlink_output),
            ]
        )
    assert not symlink_output.exists()


def test_capture_evaluation_environment_binds_runtime_and_public_source(
    tmp_path: Path,
) -> None:
    output = tmp_path / "evaluation-environment.json"

    assert main(
        arguments=[
            "capture-evaluation-environment",
            "--repository-root",
            str(REPOSITORY_ROOT),
            "--output",
            str(output),
        ]
    ) == 0
    environment = EvaluationExecutionEnvironment.model_validate_json(
        output.read_bytes()
    )
    assert environment.python_version
    assert environment.platform_system
    assert environment.uv_lock_sha256 == hashlib.sha256(
        (REPOSITORY_ROOT / "uv.lock").read_bytes()
    ).hexdigest()
    assert environment.evaluator_manifest_sha256 == hashlib.sha256(
        (REPOSITORY_ROOT / "protocol" / "evaluator_manifest.sha256").read_bytes()
    ).hexdigest()


def test_evaluation_freeze_requires_explicit_zero_score_terminal_case(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    evaluation = repository / "fresh-empty-evaluation"
    evaluation.mkdir(mode=0o755, parents=True)
    selection_source = repository / "eligibility.json"
    selection_source.write_bytes(b'{"eligible_primary":null}\n')
    execution_environment = repository / "evaluation-environment.json"
    write_evaluation_environment(path=execution_environment)
    output = repository / "empty-evaluation-freeze.json"

    with pytest.raises(ValueError, match="allow-empty-selection"):
        main(
            arguments=[
                "freeze-evaluation",
                "--repository-root",
                str(repository),
                "--evaluation-root",
                str(evaluation),
                "--execution-environment",
                str(execution_environment),
                "--selection-source",
                str(selection_source),
                "--output",
                str(output),
            ]
        )
    assert not output.exists()

    assert main(
        arguments=[
            "freeze-evaluation",
            "--repository-root",
            str(repository),
            "--allow-empty-selection",
            "--evaluation-root",
            str(evaluation),
            "--execution-environment",
            str(execution_environment),
            "--selection-source",
            str(selection_source),
            "--output",
            str(output),
        ]
    ) == 0
    commitment = EvaluationFreezeCommitment.model_validate_json(output.read_bytes())
    assert commitment.selection_mode == "no-eligible-primary"
    assert commitment.datasets == []
    assert commitment.files == []
    assert commitment.selection_source.sha256 == hashlib.sha256(
        selection_source.read_bytes()
    ).hexdigest()


def test_review_freeze_and_finalized_public_bundle_preserve_exact_bytes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    review_bundle = tmp_path / "review-bundle"
    bundle = prepare_neutral_review_bundle(root=review_bundle)
    sealed_mapping, mapping_freeze, sealed_mapping_sha256 = prepare_mapping_freeze(
        root=tmp_path
    )
    editorial_metadata, primary_review = prepare_editorial_metadata(
        root=tmp_path,
        review_bundle=review_bundle,
    )
    invalid_disclosure = tmp_path / "invalid-reviewer-disclosure.json"
    invalid_payload = json.loads(editorial_metadata.read_bytes())
    invalid_payload["adjudication"] = {
        "occurred": True,
        "rows_changed": 0,
        "adjudicator": {
            "display_name": "OpenAI Codex",
            "affiliation": "OpenAI",
        },
        "method": "Synthetic adjudication.",
        "disclosure": "Invalid because no second review occurred.",
    }
    invalid_disclosure.write_text(
        f"{json.dumps(invalid_payload, allow_nan=False, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}\n",
        encoding="utf-8",
        newline="",
    )
    with pytest.raises(ValueError, match="requires an occurred second review"):
        main(
            arguments=[
                "create-review-disclosure",
                "--review-bundle",
                str(review_bundle),
                "--primary-review",
                str(primary_review),
                "--input",
                str(invalid_disclosure),
                "--output",
                str(tmp_path / "invalid-reviewer-output.json"),
            ]
        )
    review_freeze = tmp_path / "review-freeze.json"

    assert main(
        arguments=[
            "freeze-review",
            "--review-bundle",
            str(review_bundle),
            "--primary-review",
            str(primary_review),
            "--mapping-freeze",
            str(mapping_freeze),
            "--editorial-metadata",
            str(editorial_metadata),
            "--output",
            str(review_freeze),
        ]
    ) == 0
    capsys.readouterr()
    commitment = ReviewFreezeCommitment.model_validate_json(review_freeze.read_bytes())
    assert commitment.review.sha256 == hashlib.sha256(
        (review_bundle / "review.csv").read_bytes()
    ).hexdigest()
    assert commitment.packets[0].neutral_label == "case-0123456789abcdef"

    public_bundle = tmp_path / "public-bundle"
    provenance = prepare_public_bundle(
        root=public_bundle,
        review_bundle=review_bundle,
        bundle=bundle,
        sealed_mapping_sha256=sealed_mapping_sha256,
    )
    verification_output = tmp_path / "review-verification.json"
    assert main(
        arguments=[
            "verify-finalized-review",
            "--review-freeze",
            str(review_freeze),
            "--mapping-freeze",
            str(mapping_freeze),
            "--sealed-mapping",
            str(sealed_mapping),
            "--primary-review",
            str(primary_review),
            "--editorial-metadata",
            str(editorial_metadata),
            "--review-bundle",
            str(review_bundle),
            "--public-bundle",
            str(public_bundle),
            "--output",
            str(verification_output),
        ]
    ) == 0
    capsys.readouterr()
    verification = FinalizedReviewVerification.model_validate_json(
        verification_output.read_bytes()
    )
    assert verification.verified
    assert verification.completed_review_sha256 == commitment.review.sha256
    assert provenance.completed_review_sha256 == f"sha256:{commitment.review.sha256}"
    assert (public_bundle / "completed-review.csv").read_bytes() == (
        review_bundle / "review.csv"
    ).read_bytes()

    original_item_bytes = (public_bundle / "item-review.jsonl").read_bytes()
    original_provenance_bytes = (public_bundle / "provenance.json").read_bytes()
    public_items = [
        PublicReviewItem.model_validate_json(line)
        for line in original_item_bytes.splitlines()
    ]
    public_items[0] = public_items[0].model_copy(
        update={"rationale": "A changed but still canonical public rationale."}
    )
    changed_item_bytes = "".join(
        f"{serialize_model(model=item)}\n" for item in public_items
    ).encode(encoding="utf-8")
    (public_bundle / "item-review.jsonl").write_bytes(changed_item_bytes)
    changed_public_hashes = [
        PublicFileHash(
            name=record.name,
            sha256=(
                prefixed_digest(data=changed_item_bytes)
                if record.name == "item-review.jsonl"
                else record.sha256
            ),
        )
        for record in provenance.public_files
    ]
    changed_provenance = provenance.model_copy(
        update={"public_files": changed_public_hashes}
    )
    write_model(path=public_bundle / "provenance.json", model=changed_provenance)
    derived_failure_output = tmp_path / "derived-failure.json"
    with pytest.raises(ValueError, match="does not derive exactly"):
        main(
            arguments=[
                "verify-finalized-review",
                "--review-freeze",
                str(review_freeze),
                "--mapping-freeze",
                str(mapping_freeze),
                "--sealed-mapping",
                str(sealed_mapping),
                "--primary-review",
                str(primary_review),
                "--editorial-metadata",
                str(editorial_metadata),
                "--review-bundle",
                str(review_bundle),
                "--public-bundle",
                str(public_bundle),
                "--output",
                str(derived_failure_output),
            ]
        )
    assert not derived_failure_output.exists()
    (public_bundle / "item-review.jsonl").write_bytes(original_item_bytes)
    (public_bundle / "provenance.json").write_bytes(original_provenance_bytes)

    changed_schedule_provenance = provenance.model_copy(
        update={
            "schedule_files": [
                HashedSourceFile(
                    name="unexpected.tsv",
                    sha256=f"sha256:{'9' * 64}",
                )
            ]
        }
    )
    write_model(
        path=public_bundle / "provenance.json",
        model=changed_schedule_provenance,
    )
    schedule_failure_output = tmp_path / "schedule-failure.json"
    with pytest.raises(ValueError, match="neutral bundle sources"):
        main(
            arguments=[
                "verify-finalized-review",
                "--review-freeze",
                str(review_freeze),
                "--mapping-freeze",
                str(mapping_freeze),
                "--sealed-mapping",
                str(sealed_mapping),
                "--primary-review",
                str(primary_review),
                "--editorial-metadata",
                str(editorial_metadata),
                "--review-bundle",
                str(review_bundle),
                "--public-bundle",
                str(public_bundle),
                "--output",
                str(schedule_failure_output),
            ]
        )
    assert not schedule_failure_output.exists()
    (public_bundle / "provenance.json").write_bytes(original_provenance_bytes)

    original_mapping_bytes = sealed_mapping.read_bytes()
    sealed_mapping.write_bytes(b'{"opaque":"changed-mapping"}\n')
    sealed_mapping.chmod(mode=0o600)
    mapping_failure_output = tmp_path / "mapping-failure.json"
    with pytest.raises(ValueError, match="pre-review commitment"):
        main(
            arguments=[
                "verify-finalized-review",
                "--review-freeze",
                str(review_freeze),
                "--mapping-freeze",
                str(mapping_freeze),
                "--sealed-mapping",
                str(sealed_mapping),
                "--primary-review",
                str(primary_review),
                "--editorial-metadata",
                str(editorial_metadata),
                "--review-bundle",
                str(review_bundle),
                "--public-bundle",
                str(public_bundle),
                "--output",
                str(mapping_failure_output),
            ]
        )
    assert not mapping_failure_output.exists()
    sealed_mapping.write_bytes(original_mapping_bytes)
    sealed_mapping.chmod(mode=0o600)

    changed = (public_bundle / "completed-review.csv").read_bytes() + b"\n"
    (public_bundle / "completed-review.csv").write_bytes(changed)
    failed_output = tmp_path / "failed-verification.json"
    with pytest.raises(ValueError, match="public file hash mismatch"):
        main(
            arguments=[
                "verify-finalized-review",
                "--review-freeze",
                str(review_freeze),
                "--mapping-freeze",
                str(mapping_freeze),
                "--sealed-mapping",
                str(sealed_mapping),
                "--primary-review",
                str(primary_review),
                "--editorial-metadata",
                str(editorial_metadata),
                "--review-bundle",
                str(review_bundle),
                "--public-bundle",
                str(public_bundle),
                "--output",
                str(failed_output),
            ]
        )
    assert not failed_output.exists()


def test_review_freeze_accepts_an_infrastructure_valid_task_only_packet(
    tmp_path: Path,
) -> None:
    review_bundle = tmp_path / "task-only-review"
    prepare_neutral_review_bundle(
        root=review_bundle,
        include_submitted_output=False,
    )
    _, mapping_freeze, _ = prepare_mapping_freeze(root=tmp_path)
    editorial_metadata, primary_review = prepare_editorial_metadata(
        root=tmp_path,
        review_bundle=review_bundle,
    )
    output = tmp_path / "task-only-freeze.json"

    assert main(
        arguments=[
            "freeze-review",
            "--review-bundle",
            str(review_bundle),
            "--primary-review",
            str(primary_review),
            "--mapping-freeze",
            str(mapping_freeze),
            "--editorial-metadata",
            str(editorial_metadata),
            "--output",
            str(output),
        ]
    ) == 0
    commitment = ReviewFreezeCommitment.model_validate_json(output.read_bytes())
    assert len(commitment.packets) == 1


def test_review_difference_is_derived_from_primary_and_final_bytes(
    tmp_path: Path,
) -> None:
    review_bundle = tmp_path / "review-bundle"
    prepare_neutral_review_bundle(root=review_bundle)
    primary_review = tmp_path / "primary-review.csv"
    assert main(
        arguments=[
            "snapshot-primary-review",
            "--review-bundle",
            str(review_bundle),
            "--output",
            str(primary_review),
        ]
    ) == 0
    review_path = review_bundle / "review.csv"
    rows = [
        CompletedReviewRow.model_validate(row)
        for row in csv.DictReader(review_path.read_text(encoding="utf-8").splitlines())
    ]
    rows[0] = rows[0].model_copy(
        update={"rationale": "The blind consistency pass clarified this cited evidence."}
    )
    review_path.write_bytes(render_completed_review_csv(rows=rows))

    difference_path = tmp_path / "review-difference.json"
    assert main(
        arguments=[
            "compare-reviews",
            "--review-bundle",
            str(review_bundle),
            "--primary-review",
            str(primary_review),
            "--output",
            str(difference_path),
        ]
    ) == 0
    difference = ReviewDifferenceReceipt.model_validate_json(
        difference_path.read_bytes()
    )
    assert difference.rows_changed == 1
    assert difference.primary_review_sha256 == prefixed_digest(
        data=primary_review.read_bytes()
    )
    assert difference.completed_review_sha256 == prefixed_digest(
        data=review_path.read_bytes()
    )


def test_public_candidate_scan_matches_worktree_and_commit_and_fails_closed(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    ledger = repository / "results" / "raw-ledgers" / "v4-core-n3.tree.sha256"
    publication = repository / "results" / "publication" / "summary.json"
    ledger.parent.mkdir(mode=0o755, parents=True)
    publication.parent.mkdir(mode=0o755, parents=True)
    ledger.write_bytes(
        (
            f"{'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}  "
            "./core-n3-synthetic-codex-r01-a01/runtime/home/.codex/auth.json\n"
            f"{'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}  "
            "./core-n3-synthetic-claude-r01-a01/runtime/home/.claude/.credentials.json\n"
        ).encode()
        + b"sha256-safe  workspace/report.txt\n"
    )
    publication.write_bytes(b'{"result":"synthetic"}\n')
    relative_paths = [
        "results/publication/summary.json",
        "results/raw-ledgers/v4-core-n3.tree.sha256",
    ]
    paths0 = tmp_path / "candidates.paths0"
    paths0.write_bytes(b"\0".join(path.encode() for path in relative_paths) + b"\0")

    run_git(repository=repository, arguments=["init", "--quiet"])
    run_git(repository=repository, arguments=["config", "user.name", "Synthetic Test"])
    run_git(
        repository=repository,
        arguments=["config", "user.email", "synthetic@example.invalid"],
    )
    run_git(repository=repository, arguments=["add", "--", *relative_paths])
    run_git(repository=repository, arguments=["commit", "--quiet", "-m", "Synthetic"])
    commit = subprocess.run(
        args=["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    worktree_receipt_path = tmp_path / "worktree-scan.json"
    assert main(
        arguments=[
            "scan-public-candidates",
            "--repository-root",
            str(repository),
            "--paths0",
            str(paths0),
            "--output",
            str(worktree_receipt_path),
        ]
    ) == 0
    committed_receipt_path = tmp_path / "commit-scan.json"
    assert main(
        arguments=[
            "scan-public-candidates",
            "--repository-root",
            str(repository),
            "--paths0",
            str(paths0),
            "--commit",
            commit,
            "--output",
            str(committed_receipt_path),
        ]
    ) == 0
    worktree_receipt = PublicCandidateScanReceipt.model_validate_json(
        worktree_receipt_path.read_bytes()
    )
    committed_receipt = PublicCandidateScanReceipt.model_validate_json(
        committed_receipt_path.read_bytes()
    )
    assert worktree_receipt.aggregate_sha256 == committed_receipt.aggregate_sha256
    assert committed_receipt.repository_commit == commit
    assert committed_receipt.path_count == 2

    ledger.write_bytes(
        b"1111111111111111111111111111111111111111111111111111111111111111  "
        b"./core-n3-synthetic-codex-r01-a01/runtime/home/.codex/auth.json\n"
    )
    with pytest.raises(ValueError, match="credential-like embedded path"):
        main(
            arguments=[
                "scan-public-candidates",
                "--repository-root",
                str(repository),
                "--paths0",
                str(paths0),
                "--output",
                str(tmp_path / "nonempty-placeholder-must-not-exist.json"),
            ]
        )

    ledger.write_bytes(b"sha256-unsafe  workspace/credentials.json\n")
    with pytest.raises(ValueError, match="credential-like embedded path"):
        main(
            arguments=[
                "scan-public-candidates",
                "--repository-root",
                str(repository),
                "--paths0",
                str(paths0),
                "--output",
                str(tmp_path / "must-not-exist.json"),
            ]
        )


@pytest.mark.parametrize(
    ("mutation", "error_match"),
    [
        ("crlf", "LF-terminated"),
        ("item-eight-pass", "item 8 cannot pass"),
        ("bad-item-six", "no applicable submitted script"),
        ("offline-item-six", "no applicable submitted script"),
        ("item-six-not-applicable", "cannot be not_applicable"),
        ("item-six-partial", "must disclose non-execution"),
    ],
)
def test_review_freeze_rejects_noncanonical_or_semantically_invalid_judgments(
    tmp_path: Path,
    mutation: str,
    error_match: str,
) -> None:
    review_bundle = tmp_path / "review-bundle"
    prepare_neutral_review_bundle(root=review_bundle)
    _, mapping_freeze, _ = prepare_mapping_freeze(root=tmp_path)
    editorial_metadata, primary_review = prepare_editorial_metadata(
        root=tmp_path,
        review_bundle=review_bundle,
    )
    review_path = review_bundle / "review.csv"
    if mutation == "crlf":
        review_path.write_bytes(review_path.read_bytes().replace(b"\n", b"\r\n"))
    else:
        rows = list(
            CompletedReviewRow.model_validate(row)
            for row in csv.DictReader(
                review_path.read_text(encoding="utf-8").splitlines()
            )
        )
        target_item = (
            "no_unavailable_access"
            if mutation == "item-eight-pass"
            else "artifacts_and_offline_scripts"
        )
        status = {
            "item-six-not-applicable": ReviewStatus.NOT_APPLICABLE,
            "item-six-partial": ReviewStatus.PARTIAL,
        }.get(mutation, ReviewStatus.PASS)
        rationale = (
            "Offline command: synthetic-runner check.py; "
            f"Runner manifest: sha256:{'b' * 64}; Result: passed."
            if mutation == "offline-item-six"
            else "Looks fine."
        )
        rows = [
            row.model_copy(
                update={
                    "status": status,
                    "rationale": rationale,
                }
            )
            if row.item_id == target_item
            else row
            for row in rows
        ]
        review_path.write_bytes(render_completed_review_csv(rows=rows))
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(ValueError, match=error_match):
        main(
            arguments=[
                "freeze-review",
                "--review-bundle",
                str(review_bundle),
                "--primary-review",
                str(primary_review),
                "--mapping-freeze",
                str(mapping_freeze),
                "--editorial-metadata",
                str(editorial_metadata),
                "--output",
                str(output),
            ]
        )
    assert not output.exists()

    traversal_output = (
        tmp_path / "outside" / ".." / "review-bundle" / "inside-freeze.json"
    )
    with pytest.raises(ValueError, match="must not contain '..'"):
        main(
            arguments=[
                "freeze-review",
                "--review-bundle",
                str(review_bundle),
                "--primary-review",
                str(primary_review),
                "--mapping-freeze",
                str(mapping_freeze),
                "--editorial-metadata",
                str(editorial_metadata),
                "--output",
                str(traversal_output),
            ]
        )
    assert not (review_bundle / "inside-freeze.json").exists()


@pytest.mark.parametrize("extension_dataset", ["n3", "n5"])
def test_gate_disclosure_binds_exact_paths_without_printing_keys(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    extension_dataset: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir(mode=0o755)
    core_key = bytes(range(32))
    extension_key = bytes(range(32, 64))
    core_key_path = tmp_path / "core.key"
    extension_key_path = tmp_path / "extension.key"
    core_key_path.write_bytes(core_key)
    extension_key_path.write_bytes(extension_key)
    core_key_path.chmod(mode=0o600)
    extension_key_path.chmod(mode=0o600)
    write_gate_attestation(
        root=repository,
        relative_path=CORE_ATTESTATION_PATH,
        model=synthetic_gate_attestation(
            dataset="n3",
            key=core_key,
            closed_stages=["core-n3"],
        ),
    )
    write_gate_attestation(
        root=repository,
        relative_path=EXTENSION_ATTESTATION_PATH,
        model=synthetic_gate_attestation(
            dataset=extension_dataset,
            key=extension_key,
            closed_stages=["core-n3", "core-extend-n5"],
        ),
    )
    commit_gate_attestations(
        repository=repository,
        relative_paths=[CORE_ATTESTATION_PATH, EXTENSION_ATTESTATION_PATH],
    )
    output = tmp_path / "disclosed-keys.json"

    assert main(
        arguments=[
            "create-gate-disclosure",
            "--repository-root",
            str(repository),
            "--core-key",
            str(core_key_path),
            "--extension-key",
            str(extension_key_path),
            "--output",
            str(output),
        ]
    ) == 0
    standard_output = capsys.readouterr().out
    disclosure = json.loads(output.read_bytes())
    assert [gate["attestation_path"] for gate in disclosure["gates"]] == [
        CORE_ATTESTATION_PATH,
        EXTENSION_ATTESTATION_PATH,
    ]
    assert disclosure["gates"][0]["commitment_key_hex"] == core_key.hex()
    assert disclosure["gates"][1]["commitment_key_hex"] == extension_key.hex()
    assert core_key.hex() not in standard_output
    assert extension_key.hex() not in standard_output

    wrong_key = bytes(reversed(core_key))
    wrong_key_path = tmp_path / "wrong.key"
    wrong_key_path.write_bytes(wrong_key)
    wrong_key_path.chmod(mode=0o600)
    failed_output = tmp_path / "wrong-disclosure.json"
    with pytest.raises(ValueError, match="does not match attestation"):
        main(
            arguments=[
                "create-gate-disclosure",
                "--repository-root",
                str(repository),
                "--core-key",
                str(wrong_key_path),
                "--extension-key",
                str(extension_key_path),
                "--output",
                str(failed_output),
            ]
        )
    assert not failed_output.exists()

    committed_core = GateAttestation.model_validate_json(
        (repository / CORE_ATTESTATION_PATH).read_bytes()
    )
    write_gate_attestation(
        root=repository,
        relative_path=CORE_ATTESTATION_PATH,
        model=committed_core.model_copy(update={"attempts_hmac_sha256": "8" * 64}),
    )
    changed_output = tmp_path / "changed-attestation-disclosure.json"
    with pytest.raises(ValueError, match="working bytes differ from HEAD"):
        main(
            arguments=[
                "create-gate-disclosure",
                "--repository-root",
                str(repository),
                "--core-key",
                str(core_key_path),
                "--extension-key",
                str(extension_key_path),
                "--output",
                str(changed_output),
            ]
        )
    assert not changed_output.exists()


def test_gate_disclosure_allows_registered_core_only_terminal_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir(mode=0o755)
    core_key = bytes(range(32))
    core_key_path = tmp_path / "core.key"
    core_key_path.write_bytes(core_key)
    core_key_path.chmod(mode=0o600)
    write_gate_attestation(
        root=repository,
        relative_path=CORE_ATTESTATION_PATH,
        model=synthetic_gate_attestation(
            dataset="n3",
            key=core_key,
            closed_stages=["core-n3"],
        ),
    )
    commit_gate_attestations(
        repository=repository,
        relative_paths=[CORE_ATTESTATION_PATH],
    )
    output = tmp_path / "core-only-disclosure.json"

    assert main(
        arguments=[
            "create-gate-disclosure",
            "--repository-root",
            str(repository),
            "--core-key",
            str(core_key_path),
            "--core-only",
            "--output",
            str(output),
        ]
    ) == 0
    standard_output = capsys.readouterr().out
    disclosure = json.loads(output.read_bytes())
    assert [gate["attestation_path"] for gate in disclosure["gates"]] == [
        CORE_ATTESTATION_PATH
    ]
    assert core_key.hex() not in standard_output


def test_core_only_disclosure_rejects_a_worktree_deleted_extension_gate(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir(mode=0o755)
    core_key = bytes(range(32))
    extension_key = bytes(range(32, 64))
    core_key_path = tmp_path / "core.key"
    core_key_path.write_bytes(core_key)
    core_key_path.chmod(mode=0o600)
    write_gate_attestation(
        root=repository,
        relative_path=CORE_ATTESTATION_PATH,
        model=synthetic_gate_attestation(
            dataset="n3",
            key=core_key,
            closed_stages=["core-n3"],
        ),
    )
    write_gate_attestation(
        root=repository,
        relative_path=EXTENSION_ATTESTATION_PATH,
        model=synthetic_gate_attestation(
            dataset="n5",
            key=extension_key,
            closed_stages=["core-n3", "core-extend-n5"],
        ),
    )
    commit_gate_attestations(
        repository=repository,
        relative_paths=[CORE_ATTESTATION_PATH, EXTENSION_ATTESTATION_PATH],
    )
    (repository / EXTENSION_ATTESTATION_PATH).unlink()
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(ValueError, match="must be absent from HEAD"):
        main(
            arguments=[
                "create-gate-disclosure",
                "--repository-root",
                str(repository),
                "--core-key",
                str(core_key_path),
                "--core-only",
                "--output",
                str(output),
            ]
        )
    assert not output.exists()
