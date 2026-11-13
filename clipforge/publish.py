"""Hand finished clips to Postiz (drafts or scheduled posts) or to a local outbox folder."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

from . import store


class PublishError(RuntimeError):
    pass


def caption_for(platform: str, clip: dict) -> str:
    tags = " ".join("#" + tag for tag in clip.get("hashtags", []))
    caption = clip.get("caption") or clip.get("title", "")
    if platform == "x":
        # X charges more for posts with links and trims long posts; keep it short and link-free
        text = clip.get("title", caption)
        few = " ".join("#" + tag for tag in clip.get("hashtags", [])[:2])
        return f"{text} {few}".strip()[:270]
    if platform == "youtube":
        return f"{caption}\n\n{tags} #Shorts".strip()
    if platform == "reddit":
        return caption
    return f"{caption}\n\n{tags}".strip()


def settings_for(platform: str, clip: dict, cfg: dict) -> dict | None:
    """Provider settings for Postiz, or None when the platform should be skipped."""
    settings = dict(cfg["publish"]["settings"].get(platform, {}))
    if platform == "youtube":
        settings["title"] = clip.get("title", "")[:100]
        settings.setdefault("tags", [
            {"value": tag, "label": tag} for tag in clip.get("hashtags", [])[:8]
        ])
    if platform == "reddit":
        subreddit = settings.pop("subreddit", "")
        if not subreddit:
            return None
        post_kind = settings.pop("type", "media")
        settings = {"subreddit": [{"value": {
            "subreddit": subreddit, "title": clip.get("title", "")[:300],
            "type": post_kind, "url": "", "is_flair_required": False,
        }}]}
    return settings


def next_slots(count: int, cfg: dict, taken: list[str], now: dt.datetime | None = None) -> list[dt.datetime]:
    """The next free posting slots (timezone-aware local datetimes)."""
    now = now or dt.datetime.now().astimezone()
    times = sorted(cfg["publish"]["post_times"])[: cfg["publish"]["max_posts_per_day"]]
    if not times:
        raise PublishError("publish.post_times is empty")
    slots: list[dt.datetime] = []
    day = now.date()
    while len(slots) < count:
        for hhmm in times:
            hour, minute = (int(part) for part in hhmm.split(":"))
            slot = dt.datetime.combine(day, dt.time(hour, minute)).astimezone()
            if slot <= now + dt.timedelta(minutes=10):
                continue
            if slot.isoformat() in taken:
                continue
            slots.append(slot)
            if len(slots) == count:
                break
        day += dt.timedelta(days=1)
    return slots


def _json_from(output: str):
    """The Postiz CLI may print a banner line before its JSON."""
    for opener in ("[", "{"):
        index = output.find(opener)
        while index != -1:
            try:
                return json.loads(output[index:])
            except json.JSONDecodeError:
                index = output.find(opener, index + 1)
    raise PublishError(f"could not read Postiz output: {output[:200]!r}")


def _postiz(args: list[str], run=subprocess.run) -> str:
    try:
        proc = run(["postiz", *args], capture_output=True, text=True, timeout=900)
    except FileNotFoundError as exc:
        raise PublishError("the postiz CLI is not installed (npm install -g postiz)") from exc
    if proc.returncode != 0:
        raise PublishError(f"postiz {args[0]} failed: {(proc.stderr or proc.stdout).strip()[:400]}")
    return proc.stdout


def match_integrations(integrations: list[dict], platforms: list[str]) -> dict[str, dict]:
    """Map our platform names to connected Postiz channels by identifier prefix."""
    matched = {}
    for platform in platforms:
        for item in integrations:
            identifier = (item.get("identifier") or "").lower()
            if item.get("disabled"):
                continue
            if identifier == platform or identifier.startswith(platform + "-"):
                matched[platform] = item
                break
    return matched


def publish_outbox(cfg: dict, job: dict, clips: list[dict]) -> list[dict]:
    folder = cfg["workspace"] / "outbox" / job["id"]
    folder.mkdir(parents=True, exist_ok=True)
    clips_dir = store.job_dir(cfg, job["id"]) / "clips"
    results = []
    for clip in clips:
        shutil.copy2(clips_dir / clip["file"], folder / clip["file"])
        text = [f"TITLE: {clip.get('title', '')}", ""]
        for platform in cfg["publish"]["platforms"]:
            text += [f"--- {platform} ---", caption_for(platform, clip), ""]
        (folder / f"{clip['id']}.txt").write_text("\n".join(text), encoding="utf-8")
        results.append({"clip": clip["id"], "mode": "outbox", "path": str(folder / clip["file"])})
    return results


def publish_postiz(cfg: dict, job: dict, clips: list[dict], dry_run: bool = False, run=subprocess.run) -> list[dict]:
    post_type = cfg["publish"]["post_type"]
    if job.get("rights") == "unverified":
        post_type = "draft"  # never auto-publish footage whose rights nobody confirmed

    _postiz(["auth:status"], run)
    integrations = _json_from(_postiz(["integrations:list"], run))
    channels = match_integrations(integrations, cfg["publish"]["platforms"])
    if not channels:
        raise PublishError("no connected Postiz channels match publish.platforms")

    taken = store.read_state(cfg, "slots", [])
    slots = next_slots(len(clips), cfg, taken)
    clips_dir = store.job_dir(cfg, job["id"]) / "clips"
    results = []
    for clip, slot in zip(clips, slots):
        when = slot.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        media_url = ""
        posted = False
        if not dry_run:
            media_url = _json_from(_postiz(["upload", str(clips_dir / clip["file"])], run))["path"]
        for platform, channel in channels.items():
            settings = settings_for(platform, clip, cfg)
            entry = {"clip": clip["id"], "mode": "postiz", "platform": platform,
                     "channel": channel.get("name", ""), "when": when, "type": post_type}
            if settings is None:
                entry["skipped"] = f"publish.settings.{platform} is not configured"
                results.append(entry)
                continue
            args = ["posts:create", "-c", caption_for(platform, clip), "-s", when,
                    "-t", post_type, "-i", channel["id"]]
            if settings:
                args += ["--settings", json.dumps(settings)]
            if dry_run:
                entry["command"] = ["postiz", *args, "-m", "<uploaded clip url>"]
            else:
                try:
                    _postiz([*args, "-m", media_url], run)
                    posted = True
                except PublishError as exc:
                    entry["error"] = str(exc)
            results.append(entry)
        if posted:
            taken.append(slot.isoformat())
    if not dry_run:
        store.write_state(cfg, "slots", taken[-500:])
    return results


def publish(cfg: dict, job: dict, clip_ids: list[str] | None = None, dry_run: bool = False) -> list[dict]:
    clips = [c for c in job["clips"] if c.get("file") and (not clip_ids or c["id"] in clip_ids)]
    if not clips:
        raise PublishError("no rendered clips to publish")
    if cfg["publish"]["mode"] == "postiz":
        results = publish_postiz(cfg, job, clips, dry_run)
    else:
        results = [] if dry_run else publish_outbox(cfg, job, clips)
    if not dry_run:
        for clip in job["clips"]:
            mine = [r for r in results if r["clip"] == clip["id"]]
            if mine:
                clip.setdefault("published", []).extend(mine)
        store.save(cfg, job)
    return results
