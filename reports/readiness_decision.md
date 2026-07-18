# Readiness decision after public-notebook incident

Decision: **GITHUB_READY**

## Incident acknowledgement

The notebook in the initial public commit was invalid. Code cells 1, 3, 4, 6, and 7 contained 79 lines whose first character was an accidental `+`, producing `SyntaxError`. The previous `GITHUB_READY` decision was invalidated. The previous static validator checked JSON structure, required phrases, outputs, and prohibited paths, but never compiled cell source and never checked for diff/merge markers; it therefore reported a false pass.

## Exact root cause and correction

`scripts/build_public_notebook.py` contained 79 literal `\n+` sequences inside five multiline code-cell strings. Those plus signs originated as patch-addition prefixes and became cell content when the generator split and serialized the strings. The checked-in notebook and the prior sdist reproduced the defect; the wheel did not contain a notebook. This was not a JSON or Colab formatting transformation.

Only those identified line prefixes were removed from the generator, and the notebook was regenerated without changing cell order, markdown, metadata, upload-first behavior, authentication, speaker-count defaults, or ZIP download behavior. The generator now validates every code cell before serialization.

## Strengthened validation

`scripts/notebook_validation.py` now loads every public notebook as JSON, checks code lines for leading `+`, `<<<<<<<`, `=======`, and `>>>>>>>` outside strings/comments, and compiles every code cell individually with `compile(source, filename, "exec")`. Failures identify notebook, cell index/ID, line, and message. Regression tests prove that `+import os` fails while `value = "a" + "b"` succeeds; merge-marker, string/comment, syntax-location, public-repository, and output-free cases are also covered.

## Final evidence

- Tests: 47 passed.
- Public notebooks: 1 valid JSON notebook; 5 code cells compiled successfully.
- Repository line-prefix marker search: no findings.
- Notebook static check: PASS.
- Wheel and sdist builds: PASS.
- Clean wheel and clean sdist installs: PASS; public import and CLI help passed in both.
- Distribution inspection: PASS; corrected notebook compiled inside the sdist, wheel contains no notebook, and each archive contains only the approved demo audio.
- Secret, private-path, placeholder, prohibited-file, and audio-allowlist scans: PASS.
- Saved notebook outputs: none.
- Required public repository identity: `Favioleiva/diarizator`; Google Drive and Windows/private paths are absent.
- Final diff: inspected before commit.

Authenticated Community-1 inference in a fresh Colab session was not executed during this correction and remains **EXTERNAL_VALIDATION_PENDING**. No GPU, runtime, DER, JER, or accuracy result is claimed. Do not create `v0.1.0` until that external validation succeeds.
