"""Configuration: defaults merged with an optional config.toml."""

from __future__ import annotations

import copy
import os
import tomllib
from pathlib import Path

DEFAULTS: dict = {
    "workspace": "workspace",
    "clips": {
        "count": 3,
        "min_seconds": 20,
        "max_seconds": 59,
        "layout": "blur",
        "captions": True,
        "hook_seconds": 3.5,
        "credit_source": True,
        "font": "Arial",
    },
    "ai": {
        "enabled": True,
        "model": "claude-opus-5-5",
        "effort": "medium",
        "niche": "GTA VI gameplay, trailers and news",
        "voice": "hyped but accurate, no clickbait lies, no spoilers in titles",
    },
    "sources": {
        "allowlist_channels": [],
        "query": "GTA VI gameplay",
        "allow_unverified": False,
        "max_source_minutes": 45,
    },
    "publish": {
        "mode": "outbox",
        "post_type": "draft",
        "platforms": ["tiktok", "youtube", "instagram", "facebook", "threads", "x", "reddit"],
        "post_times": ["12:00", "17:00", "21:00"],
        "max_posts_per_day": 3,
        "settings": {
            "tiktok": {
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "duet": False,
                "stitch": False,
                "comment": True,
                "autoAddMusic": "no",
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
                "content_posting_method": "DIRECT_POST",
            },
            "youtube": {"type": "public"},
            "instagram": {"post_type": "post"},
            "x": {"who_can_reply_post": "everyone"},
            "reddit": {"subreddit": ""},
        },
    },
    "schedule": {"enabled": False, "every_hours": 6},
}

# Rights a source can be processed under. "unverified" clips are never auto-published.
RIGHTS = ("own", "licensed", "cc", "unverified")


def _merge(base: dict, extra: dict) -> dict:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines without overriding variables that are already set."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def find_config_path() -> Path | None:
    candidates = [
        os.environ.get("CLIPFORGE_CONFIG"),
        "config.toml",
        str(Path.home() / ".clipforge" / "config.toml"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    return None


def load(path: Path | None = None) -> dict:
    """Return the effective config. `workspace` comes back as an absolute Path."""
    cfg = copy.deepcopy(DEFAULTS)
    path = path or find_config_path()
    base_dir = Path.cwd()
    if path:
        with open(path, "rb") as handle:
            _merge(cfg, tomllib.load(handle))
        base_dir = path.parent
    _load_env_file(base_dir / ".env")

    if cfg["clips"]["layout"] not in ("blur", "crop"):
        raise ValueError("clips.layout must be 'blur' or 'crop'")
    if cfg["publish"]["mode"] not in ("outbox", "postiz"):
        raise ValueError("publish.mode must be 'outbox' or 'postiz'")
    if cfg["publish"]["post_type"] not in ("draft", "schedule"):
        raise ValueError("publish.post_type must be 'draft' or 'schedule'")

    workspace = Path(cfg["workspace"]).expanduser()
    cfg["workspace"] = workspace if workspace.is_absolute() else (base_dir / workspace)
    cfg["workspace"].mkdir(parents=True, exist_ok=True)
    return cfg
