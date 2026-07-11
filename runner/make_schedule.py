#!/usr/bin/env python3
"""Expand and shuffle one frozen stage with Python's registered RNG algorithm."""

from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Sequence
from pathlib import Path


type ScheduleRow = tuple[str, str, int, str]


def parse_arguments(*, arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(args=arguments)


def load_rows(*, matrix_path: Path, stage: str) -> list[ScheduleRow]:
    rows: list[ScheduleRow] = []
    with matrix_path.open(mode="r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        required = {"stage", "task", "system", "first_replicate", "last_replicate"}
        if set(reader.fieldnames or []) != required:
            raise ValueError(f"matrix columns must be exactly {sorted(required)}")
        for record in reader:
            if record["stage"] != stage:
                continue
            task = record["task"]
            system = record["system"]
            first_replicate = int(record["first_replicate"])
            last_replicate = int(record["last_replicate"])
            if system not in {"codex", "claude"}:
                raise ValueError(f"invalid system: {system!r}")
            if not task or not task.replace("-", "_").replace("_", "").isalnum():
                raise ValueError(f"invalid task: {task!r}")
            if first_replicate < 1 or last_replicate < first_replicate:
                raise ValueError("invalid replicate range")
            rows.extend(
                (task, system, replicate, stage)
                for replicate in range(first_replicate, last_replicate + 1)
            )
    if not rows:
        raise ValueError(f"matrix has no rows for stage {stage!r}")
    return rows


def write_schedule(*, rows: list[ScheduleRow], seed: int, output_path: Path) -> None:
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    with output_path.open(mode="x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["sequence", "task", "system", "replicate", "stage"])
        for sequence, (task, system, replicate, stage) in enumerate(shuffled, start=1):
            writer.writerow([sequence, task, system, replicate, stage])


def main() -> None:
    arguments = parse_arguments()
    rows = load_rows(matrix_path=arguments.matrix, stage=arguments.stage)
    write_schedule(rows=rows, seed=arguments.seed, output_path=arguments.output)


if __name__ == "__main__":
    main()

