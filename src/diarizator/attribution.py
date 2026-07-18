from __future__ import annotations

from collections import defaultdict

from .models import SpeakerSegment, SpeakerTurn, Word


def attribute_words(words: list[Word], segments: list[SpeakerSegment], tolerance_s: float = 0.2) -> list[Word]:
    """Sweep sorted intervals; runtime is O((W+S)+candidate overlaps), not W*S."""
    ordered_segments = sorted(segments, key=lambda s: (s.start_s, s.end_s, s.speaker))
    active: list[SpeakerSegment] = []
    cursor = 0
    result: list[Word] = []
    for word in sorted(words, key=lambda w: (w.start_s, w.end_s, str(w.source_segment_id))):
        word.validate()
        while cursor < len(ordered_segments) and ordered_segments[cursor].start_s <= word.end_s:
            active.append(ordered_segments[cursor]); cursor += 1
        active = [segment for segment in active if segment.end_s >= word.start_s]
        totals: dict[str, float] = defaultdict(float)
        for segment in active:
            overlap = max(0.0, min(word.end_s, segment.end_s) - max(word.start_s, segment.start_s))
            if overlap > 0:
                totals[segment.speaker] += overlap
        if totals:
            winner = sorted(totals, key=lambda speaker: (-totals[speaker], speaker))[0]
            word.assigned_speaker, word.attribution_reason = winner, "maximum_overlap"
        else:
            nearest = _nearest_segment(word, ordered_segments)
            if nearest and nearest[0] <= tolerance_s:
                word.assigned_speaker, word.attribution_reason = nearest[1].speaker, "nearest_boundary_within_tolerance"
            else:
                word.assigned_speaker, word.attribution_reason = None, "no_safe_overlap"
        result.append(word)
    return result


def _nearest_segment(word: Word, segments: list[SpeakerSegment]) -> tuple[float, SpeakerSegment] | None:
    candidates = []
    for segment in segments:
        distance = max(segment.start_s - word.end_s, word.start_s - segment.end_s, 0.0)
        candidates.append((distance, segment.start_s, segment.end_s, segment.speaker, segment))
    if not candidates:
        return None
    best = min(candidates, key=lambda row: row[:4])
    return best[0], best[4]


def group_turns(words: list[Word], max_pause_s: float = 1.5) -> list[SpeakerTurn]:
    turns: list[SpeakerTurn] = []
    for word in sorted((w for w in words if w.text.strip()), key=lambda w: (w.start_s, w.end_s)):
        if turns and turns[-1].speaker == word.assigned_speaker and word.start_s - turns[-1].end_s <= max_pause_s:
            turns[-1].end_s = max(turns[-1].end_s, word.end_s)
            turns[-1].text = (turns[-1].text + word.text).strip()
        else:
            turns.append(SpeakerTurn(word.start_s, word.end_s, word.assigned_speaker, word.text.strip()))
    return turns
