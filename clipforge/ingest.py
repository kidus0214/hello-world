"""Bring a source video into a job folder: a URL (via yt-dlp) or a local file."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import media

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


class IngestError(RuntimeError):
    pass


def is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def _meta_from_info(info: dict) -> dict:
    return {
        "title": info.get("title") or "",
        "channel": info.get("channel") or info.get("uploader") or "",
        "channel_url": info.get("channel_url") or info.get("uploader_url") or "",
        "webpage_url": info.get("webpage_url") or "",
        "video_id": info.get("id") or "",
        "duration": float(info.get("duration") or 0),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date") or "",
        "license": info.get("license") or "",
    }


def fetch_metadata(url: str) -> dict:
    """Metadata only, no download."""
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
            return _meta_from_info(ydl.extract_info(url, download=False))
    except yt_dlp.utils.DownloadError as exc:
        raise IngestError(str(exc)) from exc


def download(url: str, folder: Path, max_minutes: float = 0) -> dict:
    """Download up to 1080p plus English captions into folder/source.*; return metadata."""
    import yt_dlp

    def too_long(info, *, incomplete=False):
        duration = info.get("duration")
        if max_minutes and duration and duration > max_minutes * 60:
            return f"source is {duration / 60:.0f} min, limit is {max_minutes:.0f} min"
        return None

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": str(folder / "source.%(ext)s"),
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-orig", "en-US", "en-GB"],
        "subtitlesformat": "json3/vtt/best",
        "match_filter": too_long,
        "retries": 3,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        raise IngestError(str(exc)) from exc
    if info is None or not find_source(folder):
        raise IngestError(f"nothing was downloaded from {url} (filtered out or unavailable)")
    return _meta_from_info(info)


def copy_local(path: str, folder: Path) -> dict:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise IngestError(f"file not found: {source}")
    if source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise IngestError(f"unsupported video type: {source.suffix}")
    shutil.copy2(source, folder / f"source{source.suffix.lower()}")
    for sidecar in (source.with_suffix(".vtt"), source.with_suffix(".srt")):
        if sidecar.is_file():
            shutil.copy2(sidecar, folder / f"source.en{sidecar.suffix}")
    return {
        "title": source.stem.replace("_", " ").replace("-", " "),
        "channel": "", "channel_url": "", "webpage_url": "", "video_id": source.stem,
        "duration": 0.0, "view_count": None, "upload_date": "", "license": "",
    }


def find_source(folder: Path) -> Path | None:
    for path in sorted(folder.glob("source.*")):
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            return path
    return None


def ingest(source: str, folder: Path, max_minutes: float = 0) -> tuple[Path, dict]:
    meta = download(source, folder, max_minutes) if is_url(source) else copy_local(source, folder)
    video = find_source(folder)
    if video is None:
        raise IngestError("no video file after ingest")
    info = media.probe(video)
    meta["duration"] = info["duration"] or meta["duration"]
    meta.update(width=info["width"], height=info["height"], fps=info["fps"], has_audio=info["has_audio"])
    return video, meta
