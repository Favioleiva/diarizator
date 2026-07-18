# Documented deviations

- The suggested fine-grained `asr/` and `diarization/` package trees are consolidated in `backends.py`; the interfaces and lazy-loading boundary are preserved with less duplication.
- Schema, grouping, provenance, validation, and exception responsibilities are implemented by `models.py`, `attribution.py`, `environment.py`, `output.py`, and domain exceptions rather than one file per suggested name.
- Exact Colab constraints use the versions recorded by the accepted execution. NumPy and SciPy are installed together at 2.2.2/1.16.3, correcting the reference notebook's internally inconsistent repair pin.
- The safe dependency-repair path requires a manual runtime restart and second **Run all** only when the current Colab image is incompatible. A compatible image follows the standard single **Run all** workflow.
