from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .security import redact_text

COMMUNITY_REPO = "pyannote/speaker-diarization-community-1"
LEGACY_REPO = "pyannote/speaker-diarization-3.1"


def preflight_model_access(repo_id: str = COMMUNITY_REPO, token: str | None = None, cache_dir: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"repo_id": repo_id, "status": "EXTERNAL_VALIDATION_PENDING", "token_present": bool(token), "secret_persisted": False}
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, LocalEntryNotFoundError
    except Exception as exc:
        return {**result, "status": "INCOMPATIBLE_STACK", "detail": redact_text(f"{type(exc).__name__}: {exc}")}
    try:
        path = snapshot_download(repo_id=repo_id, cache_dir=cache_dir, local_files_only=True)
        return {**result, "status": "MODEL_CACHED", "cache_snapshot": str(Path(path).name), "detail": "cached snapshot is available"}
    except Exception:
        pass
    if not token:
        return {**result, "status": "TOKEN_MISSING", "detail": "HF_TOKEN is unavailable and no usable cached snapshot was found"}
    try:
        path = snapshot_download(repo_id=repo_id, token=token, cache_dir=cache_dir, allow_patterns=["config.yaml"])
        return {**result, "status": "MODEL_ACCESS_CONFIRMED", "cache_snapshot": str(Path(path).name), "detail": "authenticated model access confirmed"}
    except GatedRepoError as exc:
        text = str(exc).lower()
        status = "ACCESS_NOT_ACCEPTED" if "request" in text or "access" in text else "TOKEN_REJECTED"
        return {**result, "status": status, "detail": redact_text(f"{type(exc).__name__}: {exc}")}
    except HfHubHTTPError as exc:
        code = getattr(getattr(exc, "response", None), "status_code", None)
        status = "TOKEN_REJECTED" if code == 401 else "ACCESS_NOT_ACCEPTED" if code == 403 else "NETWORK_UNAVAILABLE" if code is None or code >= 500 else "UNKNOWN_ACCESS_FAILURE"
        return {**result, "status": status, "detail": redact_text(f"{type(exc).__name__}: HTTP {code}")}
    except (ConnectionError, TimeoutError, LocalEntryNotFoundError) as exc:
        return {**result, "status": "NETWORK_UNAVAILABLE", "detail": redact_text(type(exc).__name__)}
    except Exception as exc:
        return {**result, "status": "UNKNOWN_ACCESS_FAILURE", "detail": redact_text(f"{type(exc).__name__}: {exc}")}


def token_from_environment() -> str | None:
    return os.environ.get("HF_TOKEN") or None
