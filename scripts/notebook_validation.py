"""Syntax and integrity validation for public Jupyter notebooks."""
from __future__ import annotations

import io
import json
from pathlib import Path
import tokenize

DIFF_MARKERS = ("<<<<<<<", "=======", ">>>>>>>", "+")


class NotebookValidationError(ValueError):
    """A notebook cell is not safe to publish or cannot be compiled."""


def _protected_line_starts(source: str) -> set[int]:
    """Return lines whose column zero lies inside a string or comment token."""
    protected: set[int] = set()
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    try:
        for token in tokens:
            if token.type not in {tokenize.STRING, tokenize.COMMENT}:
                continue
            start_line, start_col = token.start
            end_line, end_col = token.end
            for line_number in range(start_line, end_line + 1):
                if line_number == start_line and start_col > 0:
                    continue
                if line_number == end_line and end_line > start_line and end_col == 0:
                    continue
                protected.add(line_number)
    except (IndentationError, tokenize.TokenError):
        # Compilation below reports malformed token streams with exact location.
        pass
    return protected


def diff_marker_lines(source: str) -> list[tuple[int, str]]:
    """Find leading diff markers in actual code, excluding strings/comments."""
    protected = _protected_line_starts(source)
    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(source.splitlines(), 1):
        if line_number in protected:
            continue
        marker = next((candidate for candidate in DIFF_MARKERS if line.startswith(candidate)), None)
        if marker is not None:
            findings.append((line_number, marker))
    return findings


def validate_code_source(source: str, filename: str, cell_index: int | str, cell_id: str | None = None) -> None:
    label = f"{filename}: cell {cell_index}" + (f" (id={cell_id})" if cell_id else "")
    markers = diff_marker_lines(source)
    if markers:
        line_number, marker = markers[0]
        raise NotebookValidationError(f"{label}, line {line_number}: accidental diff marker {marker!r}")
    try:
        compile(source, filename, "exec")
    except SyntaxError as exc:
        raise NotebookValidationError(
            f"{label}, line {exc.lineno}: {exc.msg}"
        ) from exc


def validate_notebook(path: str | Path) -> dict[str, int]:
    notebook_path = Path(path)
    try:
        data = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NotebookValidationError(f"{notebook_path}: invalid notebook JSON: {exc}") from exc
    if data.get("nbformat") != 4 or not isinstance(data.get("cells"), list):
        raise NotebookValidationError(f"{notebook_path}: unsupported or malformed notebook structure")
    code_cells = 0
    for index, cell in enumerate(data["cells"]):
        if cell.get("cell_type") != "code":
            continue
        code_cells += 1
        source = "".join(cell.get("source", []))
        validate_code_source(source, notebook_path.as_posix(), index, cell.get("id"))
    return {"cells": len(data["cells"]), "code_cells": code_cells}


def validate_public_notebooks(root: str | Path) -> dict[str, dict[str, int]]:
    notebook_root = Path(root)
    notebooks = sorted(notebook_root.rglob("*.ipynb"))
    if not notebooks:
        raise NotebookValidationError(f"{notebook_root}: no public notebooks found")
    return {path.as_posix(): validate_notebook(path) for path in notebooks}
