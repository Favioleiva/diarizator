# Outputs

Each immutable run includes a manifest, environment, timing, memory, technical input metadata, normal/exclusive diarization JSON, RTTM, word JSONL, attributed and plain TXT/SRT, validation diagnostics, model-access status, benchmark status, and a minimal log. Model attribution and speaker-count provenance are recorded.

The ZIP exporter excludes source/canonical audio, caches, model weights, checkpoints, credentials, environment-variable values, temporary files, and absolute private paths. Its manifest records file hashes. A successful bundle proves that the workflow completed; it is not an accuracy score.
