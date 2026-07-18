import json
import zipfile
from pathlib import Path

import pytest

from diarizator.bundle import create_bundle, validate_bundle
from diarizator.models import DiarizationResult, SpeakerSegment, SpeakerTurn, Word
from diarizator.output import serialize_run, validate_run_outputs


def make_run(root: Path):
    result = DiarizationResult([SpeakerSegment(0, 1, "A")], [SpeakerSegment(0, 1, "A", timeline_type="exclusive")], 1)
    record = {"run_id": "test", "input_sha256": "a" * 64, "config_hash": "b" * 64, "speaker_count_mode": "estimated", "config": {"diarization": {"backend": "community-1"}}}
    serialize_run(root, record, {"device": {"type": "cpu"}}, {"wall_seconds": 1}, {}, {"sanitized_filename": "space ü.mp3", "sha256": "a" * 64}, result, [Word(0, .5, "hello", assigned_speaker="A")], [SpeakerTurn(0, .5, "A", "hello")], {"status": "MODEL_CACHED", "token_present": False}, {"status": "NOT_REQUESTED"})
    return root


def test_output_validation_and_bundle_exclusion(tmp_path):
    run = make_run(tmp_path / "run")
    assert validate_run_outputs(run)["status"] == "PASS"
    (run / "checkpoints" / "canonical.wav").parent.mkdir(parents=True, exist_ok=True)
    (run / "checkpoints" / "canonical.wav").write_bytes(b"private audio")
    bundle = tmp_path / "result.zip"
    create_bundle([run], bundle); validate_bundle(bundle)
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        assert not any(name.endswith(".wav") or "checkpoints" in name for name in names)
        assert "bundle_manifest.json" in names


def test_bundle_rejects_private_path(tmp_path):
    run = make_run(tmp_path / "run")
    (run / "logs" / "run.log").write_text("C:" + r"\Users\Person\private")
    with pytest.raises(ValueError): create_bundle([run], tmp_path / "bad.zip")
