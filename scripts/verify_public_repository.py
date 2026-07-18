from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".pytest_cache", "__pycache__", "dist", "build", ".venv"}
APPROVED_AUDIO = "examples/controlled_demo/The_Measure_of_a_Good_Life.mp3"
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".cff", ".ipynb", ".in", ".gitignore", ".gitattributes"}
token_pattern = re.compile(r"hf_[A-Za-z0-9]{10,}")
private_patterns = [
    re.compile(r"[A-Z]:\\" + "Agentic" + r" Tasks\\Diarizator" + r" Improvement", re.I),
    re.compile("/content/" + "drive/MyDrive", re.I),
    re.compile("Mapping_Global" + "_GDP", re.I),
    re.compile("Diarizator_Phase1" + "_results", re.I),
]
placeholders = re.compile("(?:" + "OWNER/" + "REPOSITORY|github\\.com/" + "OWNER|\\bREPOSITORY" + "_NAME\\b)")
errors = []
files = []
audio = []
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in SKIP for part in path.parts): continue
    rel = path.relative_to(ROOT).as_posix(); files.append(rel)
    if path.suffix.lower() in {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac", ".mp4", ".mov", ".mkv", ".webm"}: audio.append(rel)
    if path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith("."):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if token_pattern.search(text): errors.append(f"secret:{rel}")
        if placeholders.search(text): errors.append(f"placeholder:{rel}")
        if rel != "reports/source_mapping.md" and any(pattern.search(text) for pattern in private_patterns): errors.append(f"private_path:{rel}")
for forbidden in ("Input", "Proposal", "Prompts", "Implementation", "Audio"):
    if (ROOT / forbidden).exists(): errors.append(f"forbidden_tree:{forbidden}")
if audio != [APPROVED_AUDIO]: errors.append("audio_allowlist:" + json.dumps(audio))
required = ["README.md", "LICENSE", "CITATION.cff", "THIRD_PARTY_NOTICES.md", "notebooks/Diarizator_Community1_Colab.ipynb", APPROVED_AUDIO]
for item in required:
    if item not in files: errors.append("missing:" + item)
report = {"status": "PASS" if not errors else "FAIL", "file_count": len(files), "approved_audio": audio, "errors": sorted(errors)}
print(json.dumps(report, indent=2))
raise SystemExit(0 if not errors else 1)
