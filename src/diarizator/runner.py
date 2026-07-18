from __future__ import annotations

import gc
import json
from pathlib import Path
import time
from typing import Any

from .access import preflight_model_access
from .attribution import attribute_words, group_turns
from .backends import FasterWhisperBackend, create_diarizer
from .benchmark import benchmark_status, score_rttm
from .checkpoints import atomic_write_json, atomic_write_text, validate_checkpoint, write_checkpoint
from .config import config_hash, run_id, validate_config
from .device import run_with_oom_backoff, select_device_profile
from .environment import capture_environment
from .inventory import sha256_file
from .media import canonical_decode, inspect_media
from .models import AudioAsset, DiarizationResult, SpeakerSegment, SpeakerTurn, Word
from .output import rttm_text, serialize_run, validate_run_outputs


def _release_cuda() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _sync_cuda() -> None:
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:
        pass


def _memory_stats() -> dict[str, int | None]:
    result: dict[str, int | None] = {"peak_rss_bytes": None, "cuda_peak_allocated_bytes": None, "cuda_peak_reserved_bytes": None}
    try:
        import resource
        result["peak_rss_bytes"] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            result["cuda_peak_allocated_bytes"] = int(torch.cuda.max_memory_allocated())
            result["cuda_peak_reserved_bytes"] = int(torch.cuda.max_memory_reserved())
    except Exception:
        pass
    return result


def _words_from_jsonl(path: Path) -> list[Word]:
    return [Word(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _diarization_from_json(path: Path) -> DiarizationResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    return DiarizationResult(
        [SpeakerSegment(**row) for row in data["normal_segments"]],
        [SpeakerSegment(**row) for row in data["exclusive_segments"]],
        data["estimated_speakers"], data.get("metadata", {}),
    )


def execute(config: dict[str, Any], token: str | None = None) -> Path:
    validate_config(config)
    source = Path(config["audio_path"]).resolve()
    output_root = Path(config["output_root"]).resolve()
    source_hash = sha256_file(source)
    identifier = run_id(source_hash, config)
    run_dir = output_root / identifier
    if (run_dir / "run.json").exists():
        if validate_run_outputs(run_dir)["status"] == "PASS":
            raise FileExistsError(f"Completed immutable run already exists: {run_dir}")
        raise RuntimeError(f"Existing completed marker is invalid: {run_dir}")

    model_id = "pyannote/speaker-diarization-community-1" if config["diarization"]["backend"] == "community-1" else "pyannote/speaker-diarization-3.1"
    access = preflight_model_access(model_id, token)
    if access["status"] not in {"MODEL_CACHED", "MODEL_ACCESS_CONFIRMED"}:
        raise PermissionError(f"Model preflight stopped before ASR: {access['status']}")
    run_dir.mkdir(parents=True, exist_ok=True)
    identity = {"run_id": identifier, "config_hash": config_hash(config), "source_hash": source_hash}
    media = inspect_media(source)
    _sync_cuda()
    started = time.perf_counter()

    canonical_path = run_dir / "checkpoints" / "canonical" / "audio.wav"
    canonical_checkpoint = run_dir / "checkpoints" / "canonical.json"
    if canonical_checkpoint.exists():
        validate_checkpoint(canonical_checkpoint, identity)
        audio = AudioAsset(str(source), source_hash, media, {"sha256": sha256_file(canonical_path), "sample_rate_hz": 16000, "channels": 1, "codec": "pcm_f32le", "resumed": True}, config["audio"]["channel_policy"], str(canonical_path))
    else:
        canonical_path.unlink(missing_ok=True)
        audio = canonical_decode(source, canonical_path, config["audio"]["channel_policy"])
        write_checkpoint(canonical_checkpoint, "canonical", identity, [str(canonical_path)])

    environment = capture_environment()
    detected = environment["device"]
    cuda = detected.get("type") == "cuda"
    total_gb = detected.get("total_memory_bytes", 0) / (1024**3) if cuda else None
    profile = select_device_profile(detected.get("name"), total_gb, total_gb, cuda)
    asr_metadata: dict[str, Any] = {}

    def transcribe(batch_size: int) -> list[Word]:
        output, metadata = FasterWhisperBackend().transcribe(str(canonical_path), config["asr"], profile["device"], profile["compute_type"], batch_size)
        asr_metadata.clear(); asr_metadata.update(metadata)
        return output

    is_oom = lambda exc: "out of memory" in str(exc).lower() or type(exc).__name__ == "OutOfMemoryError"
    cpu_fallback = None
    if config["device"]["allow_cpu_fallback"]:
        cpu_fallback = lambda: FasterWhisperBackend().transcribe(str(canonical_path), config["asr"], "cpu", "int8", 1)[0]
    asr_words_path = run_dir / "checkpoints" / "asr_words.jsonl"
    asr_metadata_path = run_dir / "checkpoints" / "asr_metadata.json"
    asr_checkpoint = run_dir / "checkpoints" / "asr.json"
    if asr_checkpoint.exists():
        validate_checkpoint(asr_checkpoint, identity)
        words = _words_from_jsonl(asr_words_path)
        asr_metadata.update(json.loads(asr_metadata_path.read_text(encoding="utf-8")))
        backoff = {"batch_size": asr_metadata.get("batch_size"), "events": [], "fallback": "checkpoint"}
    else:
        words, backoff = run_with_oom_backoff(profile["batch_candidates"], transcribe, is_oom, cpu_fallback=cpu_fallback)
        atomic_write_text(asr_words_path, "".join(json.dumps(word.to_dict(), sort_keys=True) + "\n" for word in words))
        atomic_write_json(asr_metadata_path, asr_metadata)
        write_checkpoint(asr_checkpoint, "asr", identity, [str(asr_words_path), str(asr_metadata_path)])
    _release_cuda()

    diarization_path = run_dir / "checkpoints" / "diarization.json"
    diarization_checkpoint = run_dir / "checkpoints" / "diarization_stage.json"
    if diarization_checkpoint.exists():
        validate_checkpoint(diarization_checkpoint, identity)
        diarization = _diarization_from_json(diarization_path)
    else:
        diarization = create_diarizer(config["diarization"]["backend"]).diarize(str(canonical_path), config["speaker_count"], profile["device"], token)
        atomic_write_json(diarization_path, diarization.to_dict())
        write_checkpoint(diarization_checkpoint, "diarization", identity, [str(diarization_path)])
    _release_cuda()

    attributed_path = run_dir / "checkpoints" / "attributed_words.jsonl"
    turns_path = run_dir / "checkpoints" / "turns.json"
    attribution_checkpoint = run_dir / "checkpoints" / "attribution.json"
    if attribution_checkpoint.exists():
        validate_checkpoint(attribution_checkpoint, identity)
        attributed = _words_from_jsonl(attributed_path)
        turns = [SpeakerTurn(**row) for row in json.loads(turns_path.read_text(encoding="utf-8"))]
    else:
        attributed = attribute_words(words, diarization.exclusive_segments, config["attribution"]["boundary_tolerance_s"])
        turns = group_turns(attributed, config["grouping"]["max_pause_s"])
        atomic_write_text(attributed_path, "".join(json.dumps(word.to_dict(), sort_keys=True) + "\n" for word in attributed))
        atomic_write_json(turns_path, [turn.to_dict() for turn in turns])
        write_checkpoint(attribution_checkpoint, "attribution", identity, [str(attributed_path), str(turns_path)])

    _sync_cuda()
    wall_seconds = time.perf_counter() - started
    duration = media.get("duration_s")
    timing = {"wall_seconds": wall_seconds, "audio_duration_seconds": duration, "real_time_factor": wall_seconds / duration if duration else None, "asr_batch_size": backoff["batch_size"], "oom_events": backoff["events"], "fallback": backoff["fallback"]}
    recorded_config = {**config, "audio_path": source.name, "output_root": "<run-root>"}
    if recorded_config.get("reference_rttm"):
        recorded_config["reference_rttm"] = Path(recorded_config["reference_rttm"]).name
    run_record = {"run_id": identifier, "input_sha256": source_hash, "source_filename": source.name, "config_hash": config_hash(config), "config": recorded_config, "asr": asr_metadata, "speaker_count_mode": config["speaker_count"]["mode"]}
    reference = Path(config["reference_rttm"]) if config.get("reference_rttm") else None
    if reference:
        benchmark_hypothesis = run_dir / "checkpoints" / "benchmark_hypothesis.rttm"
        atomic_write_text(benchmark_hypothesis, rttm_text(diarization, identifier))
        benchmark = score_rttm(reference, benchmark_hypothesis)
    else:
        benchmark = benchmark_status(None)
    serialize_run(run_dir, run_record, environment, timing, _memory_stats(), {**media, "canonical": audio.canonical_metadata}, diarization, attributed, turns, access, benchmark)
    if validate_run_outputs(run_dir)["status"] != "PASS":
        raise RuntimeError("Output validation failed")
    write_checkpoint(run_dir / "checkpoints" / "final.json", "final", identity, [str(run_dir / "run.json")])
    return run_dir
