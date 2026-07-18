from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "audio": {"channel_policy": "mix", "sample_rate": 16000},
    "asr": {
        "model": "large-v3",
        "cpu_model": "small",
        "language": "auto",
        "beam_size": 5,
        "vad_filter": True,
        "min_silence_duration_ms": 500,
        "initial_prompt": "",
        "word_timestamps": True,
        "batch_size": "auto",
    },
    "diarization": {"backend": "community-1"},
    "speaker_count": {
        "mode": "estimated",
        "declared_speaker_count": None,
        "min_speakers": None,
        "max_speakers": None,
        "oracle_count": False,
    },
    "attribution": {"boundary_tolerance_s": 0.20},
    "grouping": {"max_pause_s": 1.5},
    "device": {"prefer_cuda": True, "allow_cpu_fallback": True},
    "output": {"include_canonical_audio_in_bundle": False},
    "reproducibility": {"seed": 17},
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if path:
        source = Path(path)
        raw = source.read_text(encoding="utf-8")
        if source.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise RuntimeError("Reading YAML configuration requires PyYAML") from exc
            supplied = yaml.safe_load(raw)
        else:
            supplied = json.loads(raw)
        _merge(config, supplied)
    if overrides:
        _merge(config, overrides)
    validate_config(config)
    return config


def _merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value


def validate_config(config: dict[str, Any]) -> None:
    policy = config["audio"]["channel_policy"]
    if policy not in {"mix", "left", "right"} and not (
        isinstance(policy, str) and policy.startswith("channel:") and policy[8:].isdigit()
    ):
        raise ValueError("unsupported channel policy")
    if config["audio"]["sample_rate"] != 16000:
        raise ValueError("Phase 1 canonical sample rate must be 16000")
    backend = config["diarization"]["backend"]
    if backend not in {"community-1", "legacy-3.1"}:
        raise ValueError("unsupported diarization backend")
    count = config["speaker_count"]
    mode = count["mode"]
    if mode not in {"exact", "estimated", "bounded"}:
        raise ValueError("unsupported speaker-count mode")
    if mode == "exact":
        if not isinstance(count.get("declared_speaker_count"), int) or count["declared_speaker_count"] < 1:
            raise ValueError("exact mode requires declared_speaker_count >= 1")
        if not count.get("oracle_count"):
            raise ValueError("exact mode must record oracle_count=true")
    elif mode == "estimated":
        if count.get("oracle_count"):
            raise ValueError("estimated mode cannot be oracle")
        if count.get("declared_speaker_count") is not None:
            raise ValueError("estimated mode cannot force a declared count")
    else:
        lo, hi = count.get("min_speakers"), count.get("max_speakers")
        if not isinstance(lo, int) or not isinstance(hi, int) or lo < 1 or hi < lo:
            raise ValueError("bounded mode requires valid min/max")
        if lo == hi:
            raise ValueError("bounded mode cannot disguise an exact count")
        if count.get("oracle_count"):
            raise ValueError("bounded mode cannot be oracle")
    if float(config["attribution"]["boundary_tolerance_s"]) < 0:
        raise ValueError("boundary tolerance cannot be negative")
    if float(config["grouping"]["max_pause_s"]) < 0:
        raise ValueError("grouping pause cannot be negative")


def run_id(input_hash: str, config: dict[str, Any]) -> str:
    count = config["speaker_count"]
    if count["mode"] == "exact":
        mode = f"exact_{count['declared_speaker_count']}_speakers"
    elif count["mode"] == "bounded":
        mode = f"bounded_{count['min_speakers']}_{count['max_speakers']}_speakers"
    else:
        mode = "estimated_speakers"
    backend = config["diarization"]["backend"].replace(".", "_")
    return f"{mode}-{backend}-{input_hash[:10]}-{config_hash(config)[:10]}"
