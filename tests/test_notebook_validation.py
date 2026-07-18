import json
from pathlib import Path

import pytest

from scripts.notebook_validation import (
    NotebookValidationError,
    diff_marker_lines,
    validate_code_source,
    validate_public_notebooks,
)

ROOT = Path(__file__).resolve().parents[1]


def test_all_public_notebook_cells_compile():
    results = validate_public_notebooks(ROOT / "notebooks")
    assert results
    assert all(item["code_cells"] > 0 for item in results.values())


def test_public_notebook_is_output_free_and_uses_public_repository():
    notebook = json.loads((ROOT / "notebooks" / "Diarizator_Community1_Colab.ipynb").read_text(encoding="utf-8"))
    source = "".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert all(not cell.get("outputs") for cell in notebook["cells"] if cell.get("cell_type") == "code")
    assert 'OWNER = "Favioleiva"' in source and 'REPOSITORY = "diarizator"' in source
    assert 'REPO_URL = f"https://github.com/{OWNER}/{REPOSITORY}.git"' in source
    assert "drive.mount" not in source and "MyDrive" not in source and "print(HF_TOKEN" not in source


def test_prefixed_plus_regression_is_rejected():
    with pytest.raises(NotebookValidationError, match=r"line 1.*diff marker '\+'"):
        validate_code_source("+import os\n", "regression.ipynb", 0, "bad-cell")


def test_legitimate_plus_operator_is_accepted():
    validate_code_source('value = "a" + "b"\n', "regression.ipynb", 0, "good-cell")


@pytest.mark.parametrize("marker", ["<<<<<<< HEAD", "=======", ">>>>>>> branch"])
def test_merge_markers_are_rejected(marker):
    with pytest.raises(NotebookValidationError, match="diff marker"):
        validate_code_source(marker + "\n", "regression.ipynb", 2)


def test_marker_text_inside_string_or_comment_is_allowed():
    source = 'text = """\n+not a diff\n<<<<<<< also text\n"""\n# >>>>>>> comment\n'
    assert diff_marker_lines(source) == []
    validate_code_source(source, "regression.ipynb", 1)


def test_syntax_error_reports_notebook_cell_and_line():
    with pytest.raises(NotebookValidationError) as captured:
        validate_code_source("if True print('bad')\n", "broken.ipynb", 3, "cell-id")
    message = str(captured.value)
    assert "broken.ipynb" in message and "cell 3" in message and "id=cell-id" in message and "line 1" in message
