from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


def load_jsonl(*, path: Path, model_type: type[ModelT]) -> list[ModelT]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [model_type.model_validate_json(line) for line in lines]


def canonical_json(*, value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def write_jsonl(*, path: Path, models: list[BaseModel]) -> None:
    serialized = [canonical_json(value=model.model_dump(mode="json")) for model in models]
    path.write_text("".join(f"{line}\n" for line in serialized), encoding="utf-8")


def write_json(*, path: Path, model: BaseModel) -> None:
    serialized = canonical_json(value=model.model_dump(mode="json"))
    path.write_text(f"{serialized}\n", encoding="utf-8")

