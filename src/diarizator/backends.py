from __future__ import annotations

import gc
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import DiarizationResult, SpeakerSegment, Word


class DiarizerBackend(ABC):
    model_id: str

    @abstractmethod
    def diarize(self, audio_path: str, count_config: dict[str, Any], device: str, token: str | None) -> DiarizationResult: ...


def _annotation_segments(annotation: Any, timeline_type: str) -> list[SpeakerSegment]:
    segments = []
    for turn, track, speaker in annotation.itertracks(yield_label=True):
        segments.append(SpeakerSegment(float(turn.start), float(turn.end), str(speaker), str(track) if track is not None else None, None, timeline_type))
    return sorted(segments, key=lambda s: (s.start_s, s.end_s, s.speaker))


def derive_exclusive(normal: list[SpeakerSegment]) -> list[SpeakerSegment]:
    boundaries = sorted({x for s in normal for x in (s.start_s, s.end_s)})
    output: list[SpeakerSegment] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end <= start:
            continue
        active = sorted({s.speaker for s in normal if s.start_s < end and s.end_s > start})
        if not active:
            continue
        speaker = active[0]
        if output and output[-1].speaker == speaker and abs(output[-1].end_s - start) < 1e-9:
            output[-1].end_s = end
        else:
            output.append(SpeakerSegment(start, end, speaker, timeline_type="exclusive"))
    return output


class PyannoteBackend(DiarizerBackend):
    def __init__(self, model_id: str, require_native_exclusive: bool):
        self.model_id = model_id
        self.require_native_exclusive = require_native_exclusive

    def diarize(self, audio_path: str, count_config: dict[str, Any], device: str, token: str | None) -> DiarizationResult:
        import torch
        from pyannote.audio import Pipeline
        pipeline = Pipeline.from_pretrained(self.model_id, token=token)
        if pipeline is None:
            raise RuntimeError(f"unable to load selected backend {self.model_id}")
        if device == "cuda":
            pipeline.to(torch.device("cuda"))
        kwargs: dict[str, Any] = {}
        mode = count_config["mode"]
        if mode == "exact":
            kwargs["num_speakers"] = count_config["declared_speaker_count"]
        elif mode == "bounded":
            kwargs.update(min_speakers=count_config["min_speakers"], max_speakers=count_config["max_speakers"])
        output = pipeline(audio_path, **kwargs)
        normal_annotation = getattr(output, "speaker_diarization", output)
        normal = _annotation_segments(normal_annotation, "normal")
        exclusive_annotation = getattr(output, "exclusive_speaker_diarization", None)
        if exclusive_annotation is None:
            if self.require_native_exclusive:
                raise RuntimeError("Community-1 output did not expose exclusive_speaker_diarization")
            exclusive, exclusive_source = derive_exclusive(normal), "deterministic_legacy_derivation"
        else:
            exclusive, exclusive_source = _annotation_segments(exclusive_annotation, "exclusive"), "community_1_native"
        labels = sorted({s.speaker for s in normal})
        result = DiarizationResult(normal, exclusive, len(labels), {"model_id": self.model_id, "exclusive_source": exclusive_source, "device": device})
        result.validate()
        del pipeline
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        return result


def create_diarizer(name: str) -> DiarizerBackend:
    if name == "community-1":
        return PyannoteBackend("pyannote/speaker-diarization-community-1", True)
    if name == "legacy-3.1":
        return PyannoteBackend("pyannote/speaker-diarization-3.1", False)
    raise ValueError("unknown diarizer backend")


class FasterWhisperBackend:
    def transcribe(self, audio_path: str, config: dict[str, Any], device: str, compute_type: str, batch_size: int) -> tuple[list[Word], dict[str, Any]]:
        from faster_whisper import BatchedInferencePipeline, WhisperModel
        model_name = config["model"] if device == "cuda" else config["cpu_model"]
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        engine: Any = BatchedInferencePipeline(model=model) if batch_size > 1 else model
        kwargs = {
            "language": None if config["language"] == "auto" else config["language"],
            "beam_size": config["beam_size"], "vad_filter": config["vad_filter"],
            "vad_parameters": {"min_silence_duration_ms": config["min_silence_duration_ms"]},
            "word_timestamps": config["word_timestamps"], "initial_prompt": config.get("initial_prompt") or None,
        }
        if batch_size > 1:
            kwargs["batch_size"] = batch_size
        segments, info = engine.transcribe(audio_path, **kwargs)
        words: list[Word] = []
        segment_count = 0
        for segment_count, segment in enumerate(segments, 1):
            if getattr(segment, "words", None):
                for word in segment.words:
                    words.append(Word(float(word.start), float(word.end), str(word.word), float(word.probability) if word.probability is not None else None, segment_count - 1))
            else:
                words.append(Word(float(segment.start), float(segment.end), str(segment.text), None, segment_count - 1))
        metadata = {"model": model_name, "device": device, "compute_type": compute_type, "batch_size": batch_size, "language": getattr(info, "language", None), "language_probability": getattr(info, "language_probability", None), "segment_count": segment_count}
        del engine, model
        gc.collect()
        return words, metadata
