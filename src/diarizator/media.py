from __future__ import annotations

import json
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any, Iterator

from .inventory import sha256_file
from .models import AudioAsset

SUPPORTED_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".mp4", ".mov", ".mkv", ".webm"}


class MediaError(RuntimeError):
    pass


def inspect_mp3(path: str | Path) -> dict[str, Any]:
    """Small dependency-free MPEG-1 Layer III inspector used when FFprobe is absent."""
    raw = Path(path).read_bytes()
    offset = 0
    if raw[:3] == b"ID3" and len(raw) >= 10:
        size = sum((raw[6 + index] & 0x7f) << (21 - 7 * index) for index in range(4))
        offset = 10 + size
    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
    rates = [44100, 48000, 32000]
    while offset + 4 <= len(raw):
        header = int.from_bytes(raw[offset:offset + 4], "big")
        if header & 0xFFE00000 == 0xFFE00000 and ((header >> 17) & 3) == 1 and ((header >> 19) & 3) == 3:
            bitrate_index, rate_index = (header >> 12) & 15, (header >> 10) & 3
            if 0 < bitrate_index < 15 and rate_index < 3:
                bitrate, sample_rate = bitrates[bitrate_index] * 1000, rates[rate_index]
                padding, channel_mode = (header >> 9) & 1, (header >> 6) & 3
                frame_size = 144 * bitrate // sample_rate + padding
                channels = 1 if channel_mode == 3 else 2
                side_info = 17 if channels == 1 else 32
                xing = offset + 4 + side_info
                frames = None
                if raw[xing:xing + 4] in {b"Xing", b"Info"} and xing + 12 <= len(raw):
                    flags = int.from_bytes(raw[xing + 4:xing + 8], "big")
                    if flags & 1:
                        frames = int.from_bytes(raw[xing + 8:xing + 12], "big")
                duration = frames * 1152 / sample_rate if frames else (len(raw) - offset) * 8 / bitrate
                return {"container": "MPEG audio", "format_name": "mp3", "codec": "mp3", "duration_s": duration, "sample_rate_hz": sample_rate, "channels": channels, "channel_layout": "mono" if channels == 1 else "stereo", "bitrate_bps": bitrate, "frame_size_bytes": frame_size, "validation_backend": "mp3_stdlib"}
        offset += 1
    raise MediaError("invalid or unsupported MP3 structure")


def inspect_wav(path: str | Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as stream:
            channels, rate, frames, width = stream.getnchannels(), stream.getframerate(), stream.getnframes(), stream.getsampwidth()
    except (wave.Error, EOFError) as exc:
        raise MediaError("invalid WAV structure") from exc
    return {"container": "WAV", "format_name": "wav", "codec": f"pcm_s{width * 8}le", "duration_s": frames / rate if rate else None, "sample_rate_hz": rate, "channels": channels, "channel_layout": "mono" if channels == 1 else "stereo" if channels == 2 else f"{channels} channels", "bitrate_bps": rate * channels * width * 8, "validation_backend": "wave_stdlib"}


def _boxes(handle, start: int, end: int) -> Iterator[tuple[str, int, int, int]]:
    pos = start
    while pos + 8 <= end:
        handle.seek(pos)
        header = handle.read(8)
        if len(header) < 8:
            return
        size, kind = struct.unpack(">I4s", header)
        header_size = 8
        if size == 1:
            raw = handle.read(8)
            if len(raw) < 8:
                return
            size, header_size = struct.unpack(">Q", raw)[0], 16
        elif size == 0:
            size = end - pos
        if size < header_size or pos + size > end:
            return
        yield kind.decode("latin-1"), pos + header_size, pos + size, header_size
        pos += size


def _children(handle, payload_start: int, box_end: int, kind: str) -> Iterator[tuple[str, int, int, int]]:
    # meta carries a 4-byte FullBox header before children.
    return _boxes(handle, payload_start + (4 if kind == "meta" else 0), box_end)


def _find_path(handle, start: int, end: int, path: list[str]) -> list[tuple[int, int]]:
    current = [(start, end)]
    for wanted in path:
        found = []
        for left, right in current:
            for kind, payload, box_end, _ in _boxes(handle, left, right):
                if kind == wanted:
                    found.append((payload, box_end))
        current = found
    return current


def inspect_iso_bmff(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    size = source.stat().st_size
    result: dict[str, Any] = {"container": "ISO Base Media File", "format_name": "mov,mp4,m4a,3gp,3g2,mj2", "validation_backend": "iso_bmff_stdlib"}
    with source.open("rb") as handle:
        top = list(_boxes(handle, 0, size))
        kinds = {box[0] for box in top}
        if "ftyp" not in kinds or "moov" not in kinds or "mdat" not in kinds:
            raise MediaError("invalid or unsupported ISO-BMFF structure")
        ftyp = next(box for box in top if box[0] == "ftyp")
        handle.seek(ftyp[1])
        result["major_brand"] = handle.read(4).decode("latin-1")
        moov = next(box for box in top if box[0] == "moov")
        audio_mdia = None
        for kind, trak_start, trak_end, _ in _boxes(handle, moov[1], moov[2]):
            if kind != "trak":
                continue
            mdias = _find_path(handle, trak_start, trak_end, ["mdia"])
            if not mdias:
                continue
            mdia_start, mdia_end = mdias[0]
            hdlrs = _find_path(handle, mdia_start, mdia_end, ["hdlr"])
            if not hdlrs:
                continue
            handle.seek(hdlrs[0][0] + 8)
            if handle.read(4) == b"soun":
                audio_mdia = (mdia_start, mdia_end)
                break
        if audio_mdia is None:
            raise MediaError("no audio track found")
        mdia_start, mdia_end = audio_mdia
        mdhd = _find_path(handle, mdia_start, mdia_end, ["mdhd"])[0]
        handle.seek(mdhd[0])
        version = handle.read(1)[0]
        handle.read(3)
        if version == 1:
            handle.read(16); timescale, duration = struct.unpack(">IQ", handle.read(12))
        else:
            handle.read(8); timescale, duration = struct.unpack(">II", handle.read(8))
        result["duration_s"] = duration / timescale if timescale and duration else None
        if not result["duration_s"]:
            sidx_boxes = [box for box in top if box[0] == "sidx"]
            if sidx_boxes:
                handle.seek(sidx_boxes[0][1])
                sidx_version = handle.read(1)[0]
                handle.read(3)
                handle.read(4)
                sidx_timescale = struct.unpack(">I", handle.read(4))[0]
                handle.read(16 if sidx_version == 1 else 8)
                handle.read(2)
                reference_count = struct.unpack(">H", handle.read(2))[0]
                total_duration = 0
                for _ in range(reference_count):
                    handle.read(4)
                    total_duration += struct.unpack(">I", handle.read(4))[0]
                    handle.read(4)
                result["duration_s"] = total_duration / sidx_timescale if sidx_timescale else None
                result["duration_source"] = "sidx"
        stsd = _find_path(handle, mdia_start, mdia_end, ["minf", "stbl", "stsd"])[0]
        handle.seek(stsd[0]); handle.read(4)
        entry_count = struct.unpack(">I", handle.read(4))[0]
        if entry_count < 1:
            raise MediaError("audio sample description missing")
        entry_start = handle.tell()
        entry_size, codec = struct.unpack(">I4s", handle.read(8))
        handle.read(6); handle.read(2); handle.read(2); handle.read(2); handle.read(4)
        channels, sample_size = struct.unpack(">HH", handle.read(4))
        handle.read(4)
        sample_rate = struct.unpack(">I", handle.read(4))[0] >> 16
        result.update({
            "codec": codec.decode("latin-1"),
            "sample_rate_hz": sample_rate,
            "channels": channels,
            "sample_size_bits": sample_size,
            "channel_layout": {1: "mono", 2: "stereo"}.get(channels, f"{channels} channels"),
            "bitrate_bps_estimate": round(source.stat().st_size * 8 / result["duration_s"]) if result.get("duration_s") else None,
        })
    return result


def inspect_media(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise MediaError("media file does not exist")
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise MediaError("unsupported media suffix")
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        command = [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", "-select_streams", "a:0", str(source)]
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise MediaError("FFprobe failed: " + proc.stderr[-500:])
        data = json.loads(proc.stdout)
        if not data.get("streams"):
            raise MediaError("no audio stream found")
        stream, fmt = data["streams"][0], data.get("format", {})
        metadata = {
            "container": fmt.get("format_long_name"), "format_name": fmt.get("format_name"),
            "codec": stream.get("codec_name"), "duration_s": float(stream.get("duration") or fmt.get("duration")),
            "sample_rate_hz": int(stream["sample_rate"]), "channels": int(stream["channels"]),
            "channel_layout": stream.get("channel_layout"), "bitrate_bps": int(stream.get("bit_rate") or fmt.get("bit_rate") or 0) or None,
            "validation_backend": "ffprobe",
        }
    elif source.suffix.lower() in {".m4a", ".mp4", ".mov"}:
        metadata = inspect_iso_bmff(source)
    elif source.suffix.lower() == ".mp3":
        metadata = inspect_mp3(source)
    elif source.suffix.lower() == ".wav":
        metadata = inspect_wav(source)
    else:
        raise MediaError("FFprobe is required for this media type")
    metadata.update({"sanitized_filename": source.name, "size_bytes": source.stat().st_size, "sha256": sha256_file(source), "validation_status": "PASS"})
    return metadata


def canonical_decode(source: str | Path, destination: str | Path, channel_policy: str = "mix", sample_rate: int = 16000) -> AudioAsset:
    source_path, dest = Path(source).resolve(), Path(destination).resolve()
    metadata = inspect_media(source_path)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MediaError("FFmpeg is required for canonical decode")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError("canonical destination already exists")
    pan = {"mix": None, "left": "pan=mono|c0=c0", "right": "pan=mono|c0=c1"}.get(channel_policy)
    if channel_policy.startswith("channel:"):
        pan = f"pan=mono|c0=c{int(channel_policy[8:])}"
    command = [ffmpeg, "-nostdin", "-v", "error", "-i", str(source_path), "-map", "0:a:0"]
    if pan:
        command += ["-af", pan]
    command += ["-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_f32le", str(dest)]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        dest.unlink(missing_ok=True)
        raise MediaError("FFmpeg decode failed: " + proc.stderr[-500:])
    return AudioAsset(str(source_path), metadata["sha256"], metadata, {"sample_rate_hz": sample_rate, "channels": 1, "codec": "pcm_f32le", "sha256": sha256_file(dest), "decoding_backend": "ffmpeg", "parameters": ["map=0:a:0", f"channel_policy={channel_policy}", f"sample_rate={sample_rate}"]}, channel_policy, str(dest))
