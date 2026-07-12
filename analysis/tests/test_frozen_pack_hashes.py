from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from eng_bench.models import FrozenLedger


REPO_ROOT = Path(__file__).resolve().parents[2]


def shell_task_pack_ledger_sha256(*, task_directory: Path) -> str:
    environment = {
        **os.environ,
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
    }
    ledger = subprocess.run(
        args=[
            "bash",
            "-c",
            "find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum",
        ],
        cwd=task_directory,
        env=environment,
        check=True,
        capture_output=True,
    )
    digest = hashlib.sha256(ledger.stdout).hexdigest()
    return f"sha256:{digest}"


def test_frozen_task_pack_hashes_match_real_shell_ledgers(
    tmp_path: Path,
) -> None:
    ledger = FrozenLedger.model_validate_json(
        (REPO_ROOT / "protocol/evaluation_ledger.json").read_text(encoding="utf-8")
    )
    assembled = tmp_path / "assembled-protocol"
    subprocess.run(
        args=[
            "bash",
            "protocol/assemble_frozen_packs.sh",
            str(assembled),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
        check=True,
        capture_output=True,
        text=True,
    )
    calculated = {
        task_variant: shell_task_pack_ledger_sha256(
            task_directory=assembled / "tasks" / task_variant
        )
        for task_variant in sorted(ledger.task_pack_sha256)
    }

    assert calculated == ledger.task_pack_sha256
