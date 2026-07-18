from __future__ import annotations

import json
from pathlib import Path

from notebook_validation import validate_public_notebooks

ROOT = Path(__file__).resolve().parents[1]
results = validate_public_notebooks(ROOT / "notebooks")

for path in results:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    source = "".join("".join(cell.get("source", [])) for cell in data["cells"])
    assert all(not cell.get("outputs") and cell.get("execution_count") is None for cell in data["cells"] if cell["cell_type"] == "code")
    required = ["userdata.get(\"HF_TOKEN\")", "files.upload()", "files.download", "Favioleiva", "diarizator", "preflight_model_access", "DEPENDENCIES_INSTALLED_RESTART_REQUIRED"]
    assert all(item in source for item in required)
    assert 'OWNER = "Favioleiva"' in source and 'REPOSITORY = "diarizator"' in source
    assert 'REPO_URL = f"https://github.com/{OWNER}/{REPOSITORY}.git"' in source
    for forbidden in ("drive.mount", "MyDrive", "Agentic" + " Tasks", "Diarizator" + " Improvement", "Mapping_Global" + "_GDP", "runtime.restart_runtime", "print(HF_TOKEN", "repr(HF_TOKEN"):
        assert forbidden not in source, forbidden

print("NOTEBOOK_STATIC_VALIDATION_PASS", json.dumps(results, sort_keys=True))
