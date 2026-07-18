# Package architecture

`api.py` and `cli.py` are the public entry points. The runner coordinates access, media, device policy, inference adapters, attribution, checkpoints, provenance, validation, and output. Data crosses boundaries through package-owned dataclasses and JSON-compatible dictionaries. Model libraries are imported lazily, keeping inspection and validation usable without inference extras.
