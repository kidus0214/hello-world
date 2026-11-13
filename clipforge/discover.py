"""Find the most viewed recent videos from sources you are allowed to clip."""

from __future__ import annotations

from . import store


def _norm(url: str) -> str:
    return (url or "").lower().rstrip("/").removesuffix("/videos")


def _flat(url: str, limit: int) -> list[dict]:
    import yt_dlp

    options = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlistend": limit}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError:
        return []
    return [entry for entry in (info or {}).get("entries", []) if entry]


def _candidate(entry: dict, trusted: bool, origin: str) -> dict:
    video_id = entry.get("id", "")
    return {
        "id": video_id,
        "url": entry.get("webpage_url") or entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
        "title": entry.get("title", ""),
        "channel": entry.get("channel") or entry.get("uploader") or "",
        "channel_urls": [_norm(entry.get("channel_url", "")), _norm(entry.get("uploader_url", ""))],
        "views": entry.get("view_count") or 0,
        "duration": entry.get("duration") or 0,
        "trusted": trusted,
        "origin": origin,
    }


def candidates(cfg: dict, query: str | None = None, per_source: int = 15) -> list[dict]:
    """Most viewed first. `trusted` marks videos from allowlisted channels."""
    sources = cfg["sources"]
    allow = {_norm(url) for url in sources["allowlist_channels"]}
    found: dict[str, dict] = {}

    for channel in sources["allowlist_channels"]:
        for entry in _flat(channel.rstrip("/") + "/videos", per_source):
            item = _candidate(entry, True, channel)
            found[item["id"]] = item

    query = sources["query"] if query is None else query
    if query:
        for entry in _flat(f"ytsearch{per_source * 2}:{query}", per_source * 2):
            item = _candidate(entry, False, f"search: {query}")
            item["trusted"] = any(url and url in allow for url in item["channel_urls"])
            found.setdefault(item["id"], item)

    seen = set(store.read_state(cfg, "seen", []))
    limit = sources["max_source_minutes"] * 60
    usable = [
        item for item in found.values()
        if item["id"] and item["id"] not in seen
        and (not item["duration"] or 45 <= item["duration"] <= limit)
    ]
    usable.sort(key=lambda item: item["views"], reverse=True)
    return usable


def mark_seen(cfg: dict, video_id: str) -> None:
    seen = store.read_state(cfg, "seen", [])
    if video_id and video_id not in seen:
        seen.append(video_id)
        store.write_state(cfg, "seen", seen[-5000:])
