from __future__ import annotations

from typing import Any, Callable


def select_device_profile(name: str | None, total_gb: float | None, free_gb: float | None, cuda: bool, bf16: bool = False) -> dict[str, Any]:
    if not cuda:
        return {"profile": "CPU", "device": "cpu", "compute_type": "int8", "batch_candidates": [1], "bf16": False}
    label = (name or "").upper()
    if "T4" in label:
        start, profile = 4, "T4_16GB"
    elif "L4" in label:
        start, profile = 8, "L4_24GB"
    elif "A100" in label:
        start, profile = (32 if (total_gb or 0) >= 70 else 16), ("A100_80GB" if (total_gb or 0) >= 70 else "A100_40GB")
    else:
        start, profile = 2, "UNKNOWN_CUDA"
    if free_gb is not None and total_gb and free_gb / total_gb < 0.55:
        start = max(1, start // 2)
    candidates = []
    while start >= 1:
        candidates.append(start)
        start //= 2
    return {"profile": profile, "device": "cuda", "compute_type": "float16", "batch_candidates": candidates, "bf16": bool(bf16 and profile in {"L4_24GB", "A100_40GB", "A100_80GB"})}


def run_with_oom_backoff(candidates: list[int], operation: Callable[[int], Any], is_oom: Callable[[Exception], bool], cpu_fallback: Callable[[], Any] | None = None) -> tuple[Any, dict[str, Any]]:
    events = []
    for batch in candidates:
        try:
            return operation(batch), {"batch_size": batch, "events": events, "fallback": None}
        except Exception as exc:
            if not is_oom(exc):
                raise
            events.append({"event": "OOM", "batch_size": batch, "error_type": type(exc).__name__})
    if cpu_fallback is not None:
        return cpu_fallback(), {"batch_size": 1, "events": events, "fallback": "cpu"}
    raise RuntimeError("terminal OOM after bounded batch backoff")
