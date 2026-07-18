from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Interval:
    start: float
    end: float
    speaker: str


def parse_rttm(path: Path) -> list[Interval]:
    intervals: list[Interval] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 8 or fields[0] != "SPEAKER":
            raise ValueError(f"Invalid RTTM at line {line_number}")
        start, duration = float(fields[3]), float(fields[4])
        if start < 0 or duration <= 0:
            raise ValueError(f"Invalid RTTM interval at line {line_number}")
        intervals.append(Interval(start, start + duration, fields[7]))
    return intervals


def benchmark_status(reference_path: Path | None) -> dict[str, object]:
    if reference_path is None or not reference_path.exists():
        return {
            "status": "REFERENCE_MISSING",
            "der": None,
            "jer": None,
            "collar_seconds": 0.0,
            "overlap_evaluation": True,
        }
    parse_rttm(reference_path)
    return {"status": "REFERENCE_PRESENT", "reference": reference_path.name, "der": None, "jer": None, "collar_seconds": 0.0, "overlap_evaluation": True}


def score_rttm(reference_path: Path, hypothesis_path: Path) -> dict[str, object]:
    from pyannote.core import Annotation, Segment
    from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate

    def annotation(path: Path) -> Annotation:
        result = Annotation(uri=path.stem)
        for index, item in enumerate(parse_rttm(path)):
            result[Segment(item.start, item.end), index] = item.speaker
        return result

    reference, hypothesis = annotation(reference_path), annotation(hypothesis_path)
    der_metric = DiarizationErrorRate(collar=0.0, skip_overlap=False)
    jer_metric = JaccardErrorRate(collar=0.0, skip_overlap=False)
    detailed = der_metric(reference, hypothesis, detailed=True)
    return {
        "status": "SCORED", "reference": reference_path.name, "hypothesis": hypothesis_path.name,
        "der": float(der_metric(reference, hypothesis)), "jer": float(jer_metric(reference, hypothesis)),
        "der_components": {str(key): float(value) for key, value in detailed.items()},
        "collar_seconds": 0.0, "overlap_evaluation": True,
    }
