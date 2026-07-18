import hashlib
import json
import wave
from pathlib import Path

import pytest

import diarizator.media as media
from diarizator.security import contains_private_path, contains_secret, redact_text, sanitize

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "controlled_demo" / "The_Measure_of_a_Good_Life.mp3"


def test_demo_mp3_metadata_and_hash(monkeypatch):
    monkeypatch.setattr(media.shutil, "which", lambda _: None)
    info = media.inspect_media(DEMO)
    assert info["codec"] == "mp3" and info["sample_rate_hz"] == 44100 and info["channels"] == 2
    assert 369 < info["duration_s"] < 371
    assert info["sha256"] == "380B6EFFCC11FC00FFB8DDCBECAD8FD61707DDA84D8BCBB2C712A6B6CA08F552"


def test_wav_metadata_without_ffprobe(monkeypatch, tmp_path):
    path = tmp_path / "voice ü space.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000); out.writeframes(b"\0\0" * 1600)
    monkeypatch.setattr(media.shutil, "which", lambda _: None)
    info = media.inspect_media(path)
    assert info["duration_s"] == pytest.approx(.1) and info["sanitized_filename"] == path.name


@pytest.mark.parametrize("suffix", [".flac", ".ogg", ".opus", ".aac", ".mkv", ".webm"])
def test_supported_suffixes_declared(suffix):
    assert suffix in media.SUPPORTED_SUFFIXES


def test_invalid_suffix_rejected(tmp_path):
    path = tmp_path / "not-audio.txt"; path.write_text("x")
    with pytest.raises(media.MediaError): media.inspect_media(path)


def test_token_redaction_and_structured_sanitize():
    token = "h" + "f_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert contains_secret(token)
    assert token not in redact_text("Authorization: Bearer " + token)
    assert sanitize({"token": token, "token_present": True}) == {"token": "[REDACTED]", "token_present": True}


@pytest.mark.parametrize("value", ["C:" + r"\Users\Person\private.wav", "X:" + r"\Agentic" + " Tasks" + r"\private", "/content/" + "drive/MyDrive/private"])
def test_private_paths_detected(value):
    assert contains_private_path(value)


def test_manifest_matches_demo():
    manifest = json.loads((DEMO.parent / "demo_manifest.json").read_text())
    assert manifest["sha256"] == hashlib.sha256(DEMO.read_bytes()).hexdigest().upper()
