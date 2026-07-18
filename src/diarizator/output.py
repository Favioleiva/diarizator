from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .checkpoints import atomic_write_json, atomic_write_text
from .inventory import sha256_file
from .models import DiarizationResult, SpeakerTurn, Word
from .security import contains_secret, sanitize


def srt_timestamp(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("invalid timestamp")
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000); minutes, rem = divmod(rem, 60_000); secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def rttm_text(result: DiarizationResult, uri: str) -> str:
    lines = []
    for segment in sorted(result.normal_segments, key=lambda s: (s.start_s, s.end_s, s.speaker)):
        segment.validate()
        duration = segment.end_s - segment.start_s
        if duration > 0:
            lines.append(f"SPEAKER {uri} 1 {segment.start_s:.3f} {duration:.3f} <NA> <NA> {segment.speaker} <NA> <NA>")
    return "\n".join(lines) + ("\n" if lines else "")


def turns_to_srt(turns: list[SpeakerTurn], attributed: bool = True) -> str:
    chunks = []
    for index, turn in enumerate(turns, 1):
        label = turn.speaker or "Unknown"
        text = f"[{label}] {turn.text}" if attributed else turn.text
        chunks.append(f"{index}\n{srt_timestamp(turn.start_s)} --> {srt_timestamp(turn.end_s)}\n{text}\n")
    return "\n".join(chunks)


def turns_to_txt(turns: list[SpeakerTurn], attributed: bool = True) -> str:
    lines = []
    for turn in turns:
        label = turn.speaker or "Unknown"
        prefix = f"[{srt_timestamp(turn.start_s)[:-4]} --> {srt_timestamp(turn.end_s)[:-4]}] "
        lines.append(prefix + (f"[{label}] " if attributed else "") + turn.text)
    return "\n\n".join(lines) + ("\n" if lines else "")


def serialize_run(run_dir: str | Path, run_record: dict[str, Any], environment: dict[str, Any], timings: dict[str, Any], memory: dict[str, Any], input_metadata: dict[str, Any], result: DiarizationResult, words: list[Word], turns: list[SpeakerTurn], access: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    root = Path(run_dir)
    if (root / "run.json").exists() and json.loads((root / "run.json").read_text(encoding="utf-8")).get("status") == "COMPLETED":
        raise FileExistsError("completed run cannot be overwritten")
    (root / "logs").mkdir(parents=True, exist_ok=True); (root / "diagnostics").mkdir(exist_ok=True); (root / "checkpoints").mkdir(exist_ok=True)
    atomic_write_json(root / "environment.json", sanitize(environment)); atomic_write_json(root / "timings.json", timings); atomic_write_json(root / "memory.json", memory); atomic_write_json(root / "input_metadata.json", input_metadata)
    atomic_write_text(root / "diarization.rttm", rttm_text(result, run_record["run_id"])); atomic_write_json(root / "diarization.json", result.to_dict())
    atomic_write_text(root / "words.jsonl", "".join(json.dumps(w.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for w in words))
    atomic_write_text(root / "transcript_speaker_attributed.txt", turns_to_txt(turns, True)); atomic_write_text(root / "transcript_speaker_attributed.srt", turns_to_srt(turns, True))
    atomic_write_text(root / "transcription_plain.txt", turns_to_txt(turns, False)); atomic_write_text(root / "transcription_plain.srt", turns_to_srt(turns, False))
    atomic_write_json(root / "diagnostics" / "access_preflight.json", sanitize(access)); atomic_write_json(root / "diagnostics" / "benchmark_summary.json", benchmark)
    atomic_write_text(root / "logs" / "run.log", "Phase 1 run completed; secrets are never serialized.\n")
    validation = validate_run_outputs(root); atomic_write_json(root / "diagnostics" / "output_validation.json", validation)
    run_record = sanitize({**run_record, "status": "COMPLETED" if validation["status"] == "PASS" else "FAILED", "artifacts": validation["artifacts"]})
    atomic_write_json(root / "run.json", run_record)
    return validation


def validate_run_outputs(root: str | Path) -> dict[str, Any]:
    path = Path(root)
    required = ["environment.json", "timings.json", "memory.json", "input_metadata.json", "diarization.rttm", "diarization.json", "words.jsonl", "transcript_speaker_attributed.txt", "transcript_speaker_attributed.srt", "transcription_plain.txt", "transcription_plain.srt", "diagnostics/access_preflight.json", "diagnostics/benchmark_summary.json", "logs/run.log"]
    errors, artifacts = [], []
    for name in required:
        item = path / name
        if not item.is_file(): errors.append(f"missing:{name}"); continue
        artifacts.append({"path": name, "sha256": sha256_file(item), "size_bytes": item.stat().st_size})
        if item.suffix == ".json":
            try: json.loads(item.read_text(encoding="utf-8"))
            except Exception: errors.append(f"invalid_json:{name}")
        if item.suffix in {".json", ".jsonl", ".txt", ".srt", ".log", ".rttm"}:
            if contains_secret(item.read_text(encoding="utf-8", errors="ignore")):
                errors.append(f"potential_secret:{name}")
    rttm = path / "diarization.rttm"
    if rttm.exists():
        for line in rttm.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) != 10 or fields[0] != "SPEAKER" or float(fields[3]) < 0 or float(fields[4]) <= 0: errors.append("invalid_rttm")
    for name in ["transcript_speaker_attributed.srt", "transcription_plain.srt"]:
        item = path / name
        if item.exists() and item.stat().st_size and not re.search(r"(?m)^1\n\d{2}:\d{2}:\d{2},\d{3} --> ", item.read_text(encoding="utf-8")): errors.append(f"invalid_srt:{name}")
    diarization_json = path / "diarization.json"
    if diarization_json.exists():
        try:
            data = json.loads(diarization_json.read_text(encoding="utf-8"))
            for key in ("normal_segments", "exclusive_segments"):
                previous_end = -1.0
                for row in sorted(data[key], key=lambda item: (item["start_s"], item["end_s"], item["speaker"])):
                    if row["start_s"] < 0 or row["end_s"] <= row["start_s"] or not row["speaker"]:
                        errors.append(f"invalid_interval:{key}")
                    if key == "exclusive_segments" and row["start_s"] < previous_end - 1e-9:
                        errors.append("overlap_in_exclusive_timeline")
                    previous_end = max(previous_end, row["end_s"])
        except (KeyError, TypeError, ValueError):
            errors.append("invalid_diarization_structure")
    words_path = path / "words.jsonl"
    if words_path.exists():
        previous_start = -1.0
        for line in words_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if row["start_s"] < previous_start or row["end_s"] < row["start_s"]:
                    errors.append("invalid_word_timeline")
                previous_start = row["start_s"]
            except (json.JSONDecodeError, KeyError, TypeError):
                errors.append("invalid_words_jsonl")
    return {"status": "PASS" if not errors else "FAIL", "errors": sorted(set(errors)), "artifacts": artifacts}
