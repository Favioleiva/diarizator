from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import canonical_json


def atomic_write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def atomic_write_json(path: str | Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_checkpoint(path: str | Path, stage: str, identity: dict[str, str], artifacts: list[str]) -> None:
    target = Path(path)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("identity") != identity:
            raise ValueError("checkpoint identity mismatch")
        return
    atomic_write_json(target, {"schema_version": 1, "stage": stage, "identity": identity, "artifacts": artifacts, "complete": True})


def validate_checkpoint(path: str | Path, expected_identity: dict[str, str]) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data.get("complete") or data.get("identity") != expected_identity:
        raise ValueError("stale, partial, or mismatched checkpoint")
    for artifact in data.get("artifacts", []):
        if not Path(artifact).exists():
            raise ValueError("checkpoint artifact missing")
    return data
