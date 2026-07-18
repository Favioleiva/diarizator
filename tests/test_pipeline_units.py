import json
from pathlib import Path

import pytest

import diarizator.access as access
from diarizator.attribution import attribute_words, group_turns
from diarizator.backends import create_diarizer, derive_exclusive
from diarizator.models import SpeakerSegment, Word


def test_missing_token_preflight_never_persists(monkeypatch):
    class Hub:
        @staticmethod
        def snapshot_download(*args, **kwargs): raise RuntimeError("not cached")
    monkeypatch.setattr(access, "__import__", __import__, raising=False)
    result = access.preflight_model_access(token=None)
    assert result["status"] in {"TOKEN_MISSING", "INCOMPATIBLE_STACK"}
    assert result["secret_persisted"] is False


def test_normal_and_exclusive_timelines():
    normal = [SpeakerSegment(0, 2, "A"), SpeakerSegment(1, 3, "B")]
    exclusive = derive_exclusive(normal)
    assert any(a.start_s < b.end_s and b.start_s < a.end_s for a in normal for b in normal if a is not b)
    assert all(a.end_s <= b.start_s for a, b in zip(exclusive, exclusive[1:]))
    assert all(item.timeline_type == "exclusive" for item in exclusive)


def test_word_attribution_overlap_tolerance_and_unknown():
    segments = [SpeakerSegment(0, 1, "A", timeline_type="exclusive")]
    words = [Word(.2, .4, "one"), Word(1.05, 1.1, "two"), Word(2, 2.1, "three")]
    result = attribute_words(words, segments, tolerance_s=.2)
    assert [w.assigned_speaker for w in result] == ["A", "A", None]
    assert result[-1].attribution_reason == "no_safe_overlap"


def test_turn_grouping_preserves_unknown():
    words = [Word(0, .2, " hello", assigned_speaker="A"), Word(.3, .5, " world", assigned_speaker="A"), Word(3, 3.2, "unknown", assigned_speaker=None)]
    turns = group_turns(words)
    assert len(turns) == 2 and turns[1].speaker is None


def test_backend_selection():
    assert create_diarizer("community-1").model_id.endswith("community-1")
    assert create_diarizer("legacy-3.1").model_id.endswith("3.1")
    with pytest.raises(ValueError): create_diarizer("bad")
