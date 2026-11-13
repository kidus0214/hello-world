"""ffmpeg / ffprobe helpers and cheap audio-visual signals."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


class MediaError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 3600) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, errors="replace")
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        raise MediaError(f"{cmd[0]} failed ({proc.returncode}):\n{tail}")
    return proc


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


@lru_cache(maxsize=1)
def ffmpeg_filters() -> frozenset[str]:
    if not have("ffmpeg"):
        return frozenset()
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return frozenset(m.group(1) for m in re.finditer(r"^\s*[A-Z.]{3}\s+(\w+)\s", out, re.M))


def probe(path: Path) -> dict:
    """Return {duration, width, height, fps, has_audio} for a media file."""
    out = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]).stdout
    data = json.loads(out)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise MediaError(f"no video stream in {path}")
    num, _, den = (video.get("avg_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    width, height = int(video["width"]), int(video["height"])
    rotation = abs(int(float((video.get("tags") or {}).get("rotate", 0) or 0)))
    for side in video.get("side_data_list") or []:
        rotation = abs(int(float(side.get("rotation", rotation) or 0)))
    if rotation in (90, 270):
        width, height = height, width
    return {
        "duration": float(data["format"].get("duration") or video.get("duration") or 0),
        "width": width,
        "height": height,
        "fps": fps or 30.0,
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }


def loudness_per_second(path: Path) -> list[float]:
    """RMS level in dB for every second of audio (index = second). Empty if no audio."""
    proc = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-v", "error", "-i", str(path), "-vn",
        "-af", "aresample=8000,asetnsamples=n=8000,astats=metadata=1:reset=1,"
               "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
        "-f", "null", "-",
    ], capture_output=True, text=True, errors="replace")
    levels = []
    for match in re.finditer(r"RMS_level=(-?inf|-?[\d.]+)", proc.stdout):
        value = match.group(1)
        levels.append(-90.0 if "inf" in value else max(-90.0, float(value)))
    return levels


def scene_cuts(path: Path, threshold: float = 0.3) -> list[float]:
    """Timestamps (seconds) of hard scene changes."""
    proc = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-v", "error", "-i", str(path), "-an",
        "-vf", f"scale=320:-2,select='gt(scene,{threshold})',metadata=print:file=-",
        "-f", "null", "-",
    ], capture_output=True, text=True, errors="replace")
    return [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", proc.stdout)]
