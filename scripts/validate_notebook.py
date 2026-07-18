from __future__ import annotations

import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "notebooks" / "Diarizator_Community1_Colab.ipynb"
data = json.loads(path.read_text(encoding="utf-8"))
source = "".join("".join(cell.get("source", [])) for cell in data["cells"])
assert data["nbformat"] == 4
assert all(not cell.get("outputs") and cell.get("execution_count") is None for cell in data["cells"] if cell["cell_type"] == "code")
required = ["userdata.get(\"HF_TOKEN\")", "files.upload()", "files.download", "Favioleiva", "diarizator", "preflight_model_access", "DEPENDENCIES_INSTALLED_RESTART_REQUIRED"]
assert all(item in source for item in required)
for forbidden in ("drive.mount", "MyDrive", "Agentic" + " Tasks", "Diarizator" + " Improvement", "Mapping_Global" + "_GDP", "runtime.restart_runtime"):
    assert forbidden not in source, forbidden
print("NOTEBOOK_STATIC_VALIDATION_PASS")
