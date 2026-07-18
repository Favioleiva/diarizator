from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .config import load_config
from .runner import execute


SpeakerMode = Literal["estimated", "exact", "bounded"]


@dataclass(slots=True)
class DiarizatorConfig:
    """Stable, intentionally small configuration surface for a diarization run."""

    speaker_count_mode: SpeakerMode = "estimated"
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None
    backend: Literal["community-1", "legacy-3.1"] = "community-1"
    language: str = "auto"
    asr_model: str = "large-v3"
    cpu_asr_model: str = "small"
    channel_policy: str = "mix"
    include_canonical_audio: bool = False

    def __post_init__(self) -> None:
        if self.speaker_count_mode == "estimated" and any(value is not None for value in (self.num_speakers, self.min_speakers, self.max_speakers)):
            raise ValueError("estimated mode does not accept speaker-count bounds")
        if self.speaker_count_mode == "exact" and (not isinstance(self.num_speakers, int) or self.num_speakers < 1):
            raise ValueError("exact mode requires num_speakers >= 1")
        if self.speaker_count_mode == "bounded" and (not isinstance(self.min_speakers, int) or not isinstance(self.max_speakers, int) or self.min_speakers < 1 or self.max_speakers <= self.min_speakers):
            raise ValueError("bounded mode requires 1 <= min_speakers < max_speakers")

    def as_overrides(self) -> dict:
        mode = self.speaker_count_mode
        count = {
            "mode": mode,
            "declared_speaker_count": self.num_speakers if mode == "exact" else None,
            "min_speakers": self.min_speakers if mode == "bounded" else None,
            "max_speakers": self.max_speakers if mode == "bounded" else None,
            "oracle_count": mode == "exact",
        }
        return {
            "audio": {"channel_policy": self.channel_policy},
            "asr": {"model": self.asr_model, "cpu_model": self.cpu_asr_model, "language": self.language},
            "diarization": {"backend": self.backend},
            "speaker_count": count,
            "output": {"include_canonical_audio_in_bundle": self.include_canonical_audio},
        }


class Diarizator:
    def __init__(self, config: DiarizatorConfig | None = None) -> None:
        self.config = config or DiarizatorConfig()

    def run(self, audio_path: str | Path, output_dir: str | Path, *, token: str | None = None) -> Path:
        values = load_config(overrides=self.config.as_overrides())
        values["audio_path"] = str(Path(audio_path))
        values["output_root"] = str(Path(output_dir))
        return execute(values, token=token)


def diarize(
    audio_path: str | Path,
    output_dir: str | Path,
    *,
    config: DiarizatorConfig | None = None,
    token: str | None = None,
    speaker_count_mode: SpeakerMode | None = None,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> Path:
    """Run diarization and return the immutable result directory."""

    if config is not None and speaker_count_mode is not None:
        raise ValueError("Pass either config or speaker-count keyword arguments, not both")
    if config is None:
        config = DiarizatorConfig(
            speaker_count_mode=speaker_count_mode or "estimated",
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
    return Diarizator(config).run(audio_path, output_dir, token=token)
