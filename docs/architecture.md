# Architecture

`media` validates input and performs canonical decode. `backends` adapts faster-whisper and the Community-1/legacy pyannote interfaces into package-owned data classes. `attribution` assigns word midpoints against the exclusive timeline and groups turns. `runner` coordinates access preflight, checkpoints, GPU/CPU policy, provenance, output validation, and immutable completion. `bundle` applies the public export allowlist and hashes every included artifact.

Normal diarization preserves overlap. Exclusive diarization provides one speaker at a time for deterministic word assignment. Public API values are paths, dataclasses, dictionaries, and JSON-compatible records—not framework objects.
