# Test report

`python -m pytest -q`: **47 passed** after the public-notebook correction. Nine notebook-validation tests now cover compilation of every public code cell, accidental leading `+`, merge markers, legitimate `+` operators, marker text in strings/comments, detailed syntax locations, output-free state, and the correct public repository identity. The broader API, CLI, media, access, privacy, output, bundle, citation, and audio-allowlist tests remain green. Gated real-model execution is intentionally excluded from public CPU CI.
