# Contributing

1. Fork and branch from `main`.
2. Do not commit private recordings, tokens, model weights, caches, or outputs.
3. Install development dependencies with `python -m pip install -e ".[dev]"`.
4. Run `python -m pytest -q` and `python scripts/verify_public_repository.py`.
5. Keep real-model tests behind the `real_model` marker.
6. Add tests and documentation for behavior changes.

Phase 2 model research is outside the 0.1.x maintenance scope unless proposed
and reviewed separately.
