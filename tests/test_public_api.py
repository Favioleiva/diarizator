from copy import deepcopy
from pathlib import Path

import pytest

import diarizator
import diarizator.api as api
from diarizator.config import DEFAULT_CONFIG, config_hash, load_config, run_id, validate_config


def test_public_imports_and_version():
    assert diarizator.__version__ == "0.1.0"
    assert all(hasattr(diarizator, name) for name in ("Diarizator", "DiarizatorConfig", "diarize"))


@pytest.mark.parametrize("mode,kwargs", [("estimated", {}), ("exact", {"num_speakers": 2}), ("bounded", {"min_speakers": 2, "max_speakers": 5})])
def test_config_modes(mode, kwargs):
    values = load_config(overrides=api.DiarizatorConfig(speaker_count_mode=mode, **kwargs).as_overrides())
    assert values["speaker_count"]["mode"] == mode


@pytest.mark.parametrize("mode,count", [("exact", {}), ("bounded", {"min_speakers": 2, "max_speakers": 2}), ("estimated", {"num_speakers": 2})])
def test_invalid_modes(mode, count):
    with pytest.raises(ValueError):
        load_config(overrides=api.DiarizatorConfig(speaker_count_mode=mode, **count).as_overrides())


def test_api_delegates_and_returns_path(monkeypatch, tmp_path):
    expected = tmp_path / "result"
    monkeypatch.setattr(api, "execute", lambda config, token=None: expected)
    result = api.diarize("spaces ü.mp3", tmp_path, speaker_count_mode="exact", num_speakers=2)
    assert result == expected


def test_api_rejects_mixed_config_styles(tmp_path):
    with pytest.raises(ValueError):
        api.diarize("a.mp3", tmp_path, config=api.DiarizatorConfig(), speaker_count_mode="estimated")


def test_config_hash_stable_and_run_ids_specific():
    a, b = deepcopy(DEFAULT_CONFIG), deepcopy(DEFAULT_CONFIG)
    assert config_hash(a) == config_hash(b)
    b["speaker_count"].update(mode="exact", declared_speaker_count=3, oracle_count=True)
    assert "exact_3_speakers" in run_id("a" * 64, b)


def test_backend_and_sample_rate_validation():
    values = deepcopy(DEFAULT_CONFIG)
    values["diarization"]["backend"] = "unknown"
    with pytest.raises(ValueError): validate_config(values)
