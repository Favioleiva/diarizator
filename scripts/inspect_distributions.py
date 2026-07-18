"""Inspect built distributions for notebook integrity and publication boundaries."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import tarfile
import zipfile

from notebook_validation import validate_code_source

TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".cff", ".ipynb", ".in"}
SECRET = re.compile(r"hf_[A-Za-z0-9]{10,}")
PRIVATE = [
    re.compile(r"[A-Z]:\\" + "Agentic" + r" Tasks\\Diarizator" + r" Improvement", re.I),
    re.compile("/content/" + "drive/MyDrive", re.I),
]
PLACEHOLDER = re.compile("(?:" + "OWNER/" + "REPOSITORY|github\\.com/" + "OWNER|\\bREPOSITORY" + "_NAME\\b)")
FORBIDDEN = ("/Input/", "/Proposal/", "/Prompts/", "/Implementation/", "/Audio/", ".safetensors", ".ckpt", ".env")


def archive_entries(path: Path) -> dict[str, bytes]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    with tarfile.open(path) as archive:
        return {item.name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile()}


def inspect(path: Path) -> dict[str, object]:
    entries = archive_entries(path)
    errors: list[str] = []
    notebooks = [name for name in entries if name.endswith(".ipynb")]
    audio = [name for name in entries if Path(name).suffix.lower() in {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}]
    if len(audio) != 1 or not audio[0].endswith("examples/controlled_demo/The_Measure_of_a_Good_Life.mp3"):
        errors.append("unexpected audio allowlist: " + repr(audio))
    for name, payload in entries.items():
        normalized = "/" + name.replace("\\", "/")
        if any(value in normalized for value in FORBIDDEN):
            errors.append("forbidden path: " + name)
        if Path(name).suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = payload.decode("utf-8", errors="ignore")
        if SECRET.search(text): errors.append("secret-shaped value: " + name)
        if PLACEHOLDER.search(text): errors.append("publication placeholder: " + name)
        if any(pattern.search(text) for pattern in PRIVATE): errors.append("private path: " + name)
    for name in notebooks:
        data = json.loads(entries[name].decode("utf-8"))
        for index, cell in enumerate(data.get("cells", [])):
            if cell.get("cell_type") == "code":
                validate_code_source("".join(cell.get("source", [])), f"{path.name}:{name}", index, cell.get("id"))
                if cell.get("outputs") or cell.get("execution_count") is not None:
                    errors.append(f"persisted output: {name} cell {index}")
    if path.name.endswith(".tar.gz") and len(notebooks) != 1:
        errors.append("sdist must contain exactly one public notebook")
    if path.suffix == ".whl" and notebooks:
        errors.append("wheel unexpectedly contains notebook")
    if errors:
        raise RuntimeError(path.name + ": " + "; ".join(errors))
    return {"files": len(entries), "notebooks": len(notebooks), "approved_audio": len(audio), "status": "PASS"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args()
    archives = sorted(args.dist.glob("diarizator-*.whl")) + sorted(args.dist.glob("diarizator-*.tar.gz"))
    if len(archives) != 2:
        raise RuntimeError(f"Expected one wheel and one sdist, found {len(archives)}")
    print(json.dumps({path.name: inspect(path) for path in archives}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
