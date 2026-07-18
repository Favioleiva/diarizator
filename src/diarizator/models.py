from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AudioAsset:
    path: str
    sha256: str
    source_metadata: dict[str, Any]
    canonical_metadata: dict[str, Any] = field(default_factory=dict)
    channel_policy: str = "mix"
    waveform_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Word:
    start_s: float
    end_s: float
    text: str
    probability: float | None = None
    source_segment_id: str | int | None = None
    assigned_speaker: str | None = None
    attribution_reason: str | None = None

    def validate(self) -> None:
        if self.start_s < 0 or self.end_s < self.start_s:
            raise ValueError("invalid word interval")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpeakerSegment:
    start_s: float
    end_s: float
    speaker: str
    track: str | None = None
    confidence: float | None = None
    timeline_type: str = "normal"

    def validate(self) -> None:
        if self.start_s < 0 or self.end_s < self.start_s:
            raise ValueError("invalid speaker interval")
        if not self.speaker:
            raise ValueError("speaker is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DiarizationResult:
    normal_segments: list[SpeakerSegment]
    exclusive_segments: list[SpeakerSegment]
    estimated_speakers: int | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for segment in self.normal_segments + self.exclusive_segments:
            segment.validate()
        if any(s.timeline_type != "normal" for s in self.normal_segments):
            raise ValueError("normal timeline mislabeled")
        if any(s.timeline_type != "exclusive" for s in self.exclusive_segments):
            raise ValueError("exclusive timeline mislabeled")

    def to_dict(self) -> dict[str, Any]:
        return {
            "normal_segments": [s.to_dict() for s in self.normal_segments],
            "exclusive_segments": [s.to_dict() for s in self.exclusive_segments],
            "estimated_speakers": self.estimated_speakers,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class SpeakerTurn:
    start_s: float
    end_s: float
    speaker: str | None
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def filename_only(path: str | Path) -> str:
    return Path(path).name
