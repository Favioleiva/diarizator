from __future__ import annotations

import hashlib
from datetime import timezone
from pathlib import Path
from typing import Iterable


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def inventory_files(root: str | Path, protected_dirs: Iterable[str] = ("Input", "Audio")) -> list[dict[str, object]]:
    root_path = Path(root).resolve()
    rows: list[dict[str, object]] = []
    for dirname in protected_dirs:
        base = root_path / dirname
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            stat = path.stat()
            rows.append({
                "relative_path": path.relative_to(root_path).as_posix(),
                "size_bytes": stat.st_size,
                "last_write_time_utc": stat.st_mtime_ns,
                "sha256": sha256_file(path),
            })
    return rows


def compare_inventories(before: list[dict[str, object]], after: list[dict[str, object]]) -> dict[str, object]:
    b = {str(row["relative_path"]): row for row in before}
    a = {str(row["relative_path"]): row for row in after}
    changed = sorted(k for k in b.keys() & a.keys() if b[k]["sha256"] != a[k]["sha256"] or b[k]["size_bytes"] != a[k]["size_bytes"])
    return {"status": "PASS" if b.keys() == a.keys() and not changed else "FAIL", "added": sorted(a.keys() - b.keys()), "removed": sorted(b.keys() - a.keys()), "changed": changed}
