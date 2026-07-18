from __future__ import annotations

import importlib.metadata
import platform
import shutil
import subprocess
import sys
from typing import Any


TRACKED_PACKAGES = (
    "torch",
    "torchaudio",
    "torchcodec",
    "pyannote.audio",
    "pyannote.metrics",
    "faster-whisper",
    "huggingface-hub",
    "ctranslate2",
    "numpy",
    "pandas",
    "jedi",
    "opentelemetry-api",
    "opentelemetry-sdk",
)


def _version(command: str) -> str | None:
    executable = shutil.which(command)
    if executable is None:
        return None
    result = subprocess.run(
        [executable, "-version" if command == "ffmpeg" else "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    line = (result.stdout or result.stderr).splitlines()
    return line[0] if line else None


def capture_environment() -> dict[str, Any]:
    packages: dict[str, str | None] = {}
    for package in TRACKED_PACKAGES:
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None

    device: dict[str, Any] = {"type": "cpu", "name": platform.processor() or "unknown"}
    torch_runtime: dict[str, Any] = {}
    try:
        import torch

        torch_runtime = {
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version(),
        }

        if torch.cuda.is_available():
            index = torch.cuda.current_device()
            properties = torch.cuda.get_device_properties(index)
            device = {
                "type": "cuda",
                "name": properties.name,
                "total_memory_bytes": properties.total_memory,
                "compute_capability": [properties.major, properties.minor],
            }
    except Exception as exc:  # Environment reporting must never mask a run result.
        device["inspection_error"] = type(exc).__name__

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": packages,
        "torch_runtime": torch_runtime,
        "software": {"ffmpeg": _version("ffmpeg"), "ffprobe": _version("ffprobe")},
        "device": device,
    }
