from __future__ import annotations

import re
from typing import Any

_TOKEN_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)(HF_TOKEN\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+"),
]
_PRIVATE_PATH_PATTERNS = [
    re.compile(r"(?i)(?:[A-Z]:\\(?:Users|Agentic Tasks|content\\drive)\\[^\s\"']+|/content/drive/[^\s\"']+|/home/[^\s\"']+)"),
]


def redact_text(value: str) -> str:
    result = value
    for pattern in _TOKEN_PATTERNS:
        result = pattern.sub(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", result)
    return result


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            k: (v if k == "token_present" and isinstance(v, bool) else "[REDACTED]")
            if "token" in k.lower() or "secret" in k.lower()
            else sanitize(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def contains_secret(value: str) -> bool:
    return any(pattern.search(value) is not None for pattern in _TOKEN_PATTERNS)


def contains_private_path(value: str) -> bool:
    return any(pattern.search(value) is not None for pattern in _PRIVATE_PATH_PATTERNS)
