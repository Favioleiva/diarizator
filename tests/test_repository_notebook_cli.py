import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def command_env():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_cli_help_and_environment():
    help_run = subprocess.run([sys.executable, "-m", "diarizator", "--help"], capture_output=True, text=True, env=command_env())
    environment = subprocess.run([sys.executable, "-m", "diarizator", "environment"], capture_output=True, text=True, env=command_env())
    assert help_run.returncode == environment.returncode == 0
    assert "inspect" in help_run.stdout and "device" in environment.stdout


def test_cli_inspect_demo():
    result = subprocess.run([sys.executable, "-m", "diarizator", "inspect", str(ROOT / "examples" / "controlled_demo" / "The_Measure_of_a_Good_Life.mp3")], capture_output=True, text=True, env=command_env())
    assert result.returncode == 0 and '"codec": "mp3"' in result.stdout


def test_notebook_upload_first_and_output_free():
    notebook = json.loads((ROOT / "notebooks" / "Diarizator_Community1_Colab.ipynb").read_text())
    source = "".join("".join(c.get("source", [])) for c in notebook["cells"])
    assert "files.upload()" in source and "files.download" in source and "userdata.get(\"HF_TOKEN\")" in source
    assert all(not c.get("outputs") for c in notebook["cells"])
    assert all(x not in source for x in ("drive.mount", "MyDrive", "Agentic" + " Tasks", "Mapping_Global" + "_GDP"))


def test_configs_and_citation_parse():
    for path in (ROOT / "configs").glob("*.yaml"):
        assert isinstance(yaml.safe_load(path.read_text()), dict)
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    assert citation["version"] == "0.1.0" and citation["repository-code"] == "https://github.com/Favioleiva/diarizator"


def test_required_legal_and_docs_exist():
    required = ["LICENSE", "THIRD_PARTY_NOTICES.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "docs/privacy_and_consent.md", "examples/controlled_demo/AUDIO_LICENSE.md"]
    assert all((ROOT / name).is_file() for name in required)


def test_only_approved_audio_is_present():
    audio = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}]
    assert audio == ["examples/controlled_demo/The_Measure_of_a_Good_Life.mp3"]
