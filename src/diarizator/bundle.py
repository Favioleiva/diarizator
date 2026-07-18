from __future__ import annotations

import json
import hashlib
from pathlib import Path
import tempfile
import zipfile

from .inventory import sha256_file
from .security import contains_private_path, contains_secret


FORBIDDEN_SUFFIXES = {".wav", ".m4a", ".mp3", ".flac", ".ogg", ".opus"}
FORBIDDEN_PARTS = {"cache", "models", "canonical", "checkpoints", "credentials", "secrets"}


def _eligible(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    lowered = {part.lower() for part in relative.parts}
    return path.is_file() and path.suffix.lower() not in FORBIDDEN_SUFFIXES and not (lowered & FORBIDDEN_PARTS)


def create_bundle(run_dirs: list[Path], destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    manifest_entries: list[dict[str, object]] = []
    run_summaries: list[dict[str, object]] = []
    audio_by_hash: dict[str, dict[str, object]] = {}
    for run_dir in run_dirs:
        run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        input_metadata = json.loads((run_dir / "input_metadata.json").read_text(encoding="utf-8"))
        run_summaries.append({
            "run_id": run["run_id"], "status": run["status"],
            "speaker_count_mode": run["speaker_count_mode"],
            "backend": run["config"]["diarization"]["backend"],
            "input_sha256": run["input_sha256"], "config_hash": run["config_hash"],
        })
        audio_by_hash[input_metadata["sha256"]] = {
            key: input_metadata.get(key) for key in (
                "sanitized_filename", "sha256", "size_bytes", "duration_s", "format_name",
                "codec", "sample_rate_hz", "channels", "channel_layout", "canonical",
            )
        }
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".zip", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for run_dir in run_dirs:
                for path in sorted(run_dir.rglob("*")):
                    if not _eligible(path, run_dir):
                        continue
                    data = path.read_bytes()
                    if contains_secret(data.decode("utf-8", errors="ignore")):
                        raise ValueError(f"Potential secret in {path}")
                    if contains_private_path(data.decode("utf-8", errors="ignore")):
                        raise ValueError(f"Potential private path in {path}")
                    archive_name = Path(run_dir.name) / path.relative_to(run_dir)
                    archive.writestr(archive_name.as_posix(), data)
                    manifest_entries.append({
                        "path": archive_name.as_posix(),
                        "size_bytes": len(data),
                        "sha256": sha256_file(path),
                    })
            modes = sorted(summary["speaker_count_mode"] for summary in run_summaries)
            bundle_id = hashlib.sha256(json.dumps(run_summaries, sort_keys=True).encode()).hexdigest()[:16]
            readme = (
                "Phase 1 diarization result bundle.\n"
                f"Included speaker-count modes: {', '.join(modes)}.\n"
                "Audio, canonical WAV files, model caches, checkpoints, private paths, and credentials are intentionally excluded.\n"
                "A successful bundle establishes functional execution, not DER/JER or general accuracy.\n"
            )
            audio_inventory = {"schema_version": 1, "audio": list(audio_by_hash.values())}
            bundle_manifest = {
                "schema_version": 1, "bundle_id": bundle_id, "runs": run_summaries,
                "files": manifest_entries,
                "excluded": ["source_audio", "canonical_audio", "model_cache", "checkpoints", "credentials", "private_paths"],
            }
            archive.writestr("README.txt", readme)
            archive.writestr("README_RESULTS.md", "# Diarizator Phase 1 results\n\n" + readme)
            archive.writestr("audio_inventory.json", json.dumps(audio_inventory, indent=2) + "\n")
            archive.writestr("bundle_manifest.json", json.dumps(bundle_manifest, indent=2) + "\n")
            archive.writestr("manifest.json", json.dumps({"files": manifest_entries}, indent=2) + "\n")
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    validate_bundle(destination)
    return {"path": str(destination), "sha256": sha256_file(destination), "file_count": len(manifest_entries)}


def validate_bundle(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if "manifest.json" not in names or "README.txt" not in names:
            raise ValueError("Bundle metadata missing")
        canonical_metadata = {"bundle_manifest.json", "README_RESULTS.md", "audio_inventory.json"}
        if names and canonical_metadata & set(names) and not canonical_metadata.issubset(names):
            raise ValueError("Canonical bundle metadata is incomplete")
        for name in names:
            candidate = Path(name)
            lowered = {part.lower() for part in candidate.parts}
            if candidate.suffix.lower() in FORBIDDEN_SUFFIXES or lowered & FORBIDDEN_PARTS:
                raise ValueError(f"Forbidden bundle entry: {name}")
        manifest = json.loads(archive.read("manifest.json"))
        for item in manifest["files"]:
            data = archive.read(item["path"])
            if hashlib.sha256(data).hexdigest().upper() != item["sha256"]:
                raise ValueError(f"Bundle hash mismatch: {item['path']}")
