import datetime as dt
import json
from types import SimpleNamespace

import pytest

from clipforge import publish, store

CLIP = {"id": "clip01", "file": "clip01.mp4", "title": "Bridge jump", "caption": "He cleared it.",
        "hashtags": ["gta6", "gaming", "stunts"]}


def _job(cfg, rights="licensed"):
    job = store.create(cfg, "x", rights)
    clips = store.job_dir(cfg, job["id"]) / "clips"
    clips.mkdir()
    (clips / "clip01.mp4").write_bytes(b"video")
    job["clips"] = [dict(CLIP)]
    store.save(cfg, job)
    return job


def _fake_postiz(calls, fail=()):
    def run(cmd, **_kwargs):
        calls.append(cmd)
        action = cmd[1]
        out = ""
        if action == "integrations:list":
            out = "Postiz CLI\n" + json.dumps([
                {"id": "tt1", "identifier": "tiktok", "name": "tt"},
                {"id": "yt1", "identifier": "youtube", "name": "yt"},
                {"id": "ig1", "identifier": "instagram-standalone", "name": "ig"},
                {"id": "rd1", "identifier": "reddit", "name": "rd"},
                {"id": "x1", "identifier": "x", "name": "x", "disabled": True},
            ])
        elif action == "upload":
            out = json.dumps({"path": "https://cdn.example/clip01.mp4"})
        failed = action == "posts:create" and cmd[cmd.index("-i") + 1] in fail
        return SimpleNamespace(returncode=1 if failed else 0, stdout=out, stderr="boom" if failed else "")
    return run


def test_captions_per_platform():
    assert publish.caption_for("tiktok", CLIP) == "He cleared it.\n\n#gta6 #gaming #stunts"
    assert publish.caption_for("youtube", CLIP).endswith("#Shorts")
    assert publish.caption_for("x", CLIP) == "Bridge jump #gta6 #gaming"


def test_next_slots_skip_past_and_taken(cfg):
    now = dt.datetime(2026, 11, 19, 16, 55).astimezone()
    taken = [dt.datetime(2026, 11, 19, 21, 0).astimezone().isoformat()]
    slots = publish.next_slots(3, cfg, taken, now)
    assert [(s.day, s.hour) for s in slots] == [(20, 12), (20, 17), (20, 21)]


def test_postiz_creates_drafts_on_connected_channels(cfg):
    cfg["publish"]["mode"] = "postiz"
    job, calls = _job(cfg), []
    results = publish.publish_postiz(cfg, job, job["clips"], run=_fake_postiz(calls))
    created = [c for c in calls if c[1] == "posts:create"]
    assert {c[c.index("-i") + 1] for c in created} == {"tt1", "yt1", "ig1"}   # x disabled, reddit unset
    assert all(c[c.index("-t") + 1] == "draft" and c[c.index("-m") + 1].startswith("https://cdn") for c in created)
    tiktok = next(c for c in created if "tt1" in c)
    assert json.loads(tiktok[tiktok.index("--settings") + 1])["content_posting_method"] == "DIRECT_POST"
    youtube = next(c for c in created if "yt1" in c)
    assert json.loads(youtube[youtube.index("--settings") + 1])["title"] == "Bridge jump"
    assert [r["platform"] for r in results if r.get("skipped")] == ["reddit"]
    assert len(store.read_state(cfg, "slots", [])) == 1


def test_unverified_rights_never_schedule(cfg):
    cfg["publish"].update(mode="postiz", post_type="schedule")
    calls = []
    job = _job(cfg, rights="unverified")
    publish.publish_postiz(cfg, job, job["clips"], run=_fake_postiz(calls))
    assert all(c[c.index("-t") + 1] == "draft" for c in calls if c[1] == "posts:create")
    calls.clear()
    job = _job(cfg, rights="licensed")
    publish.publish_postiz(cfg, job, job["clips"], run=_fake_postiz(calls))
    assert all(c[c.index("-t") + 1] == "schedule" for c in calls if c[1] == "posts:create")


def test_failed_posts_are_reported_and_do_not_burn_the_slot(cfg):
    cfg["publish"]["mode"] = "postiz"
    job, calls = _job(cfg), []
    results = publish.publish_postiz(cfg, job, job["clips"], run=_fake_postiz(calls, fail={"tt1", "yt1", "ig1"}))
    assert sum(1 for r in results if r.get("error")) == 3
    assert store.read_state(cfg, "slots", []) == []


def test_dry_run_uploads_nothing(cfg):
    cfg["publish"]["mode"] = "postiz"
    job, calls = _job(cfg), []
    results = publish.publish_postiz(cfg, job, job["clips"], dry_run=True, run=_fake_postiz(calls))
    assert not [c for c in calls if c[1] in ("upload", "posts:create")]
    assert all("command" in r for r in results if not r.get("skipped"))


def test_outbox_writes_clip_and_captions(cfg):
    job = _job(cfg)
    results = publish.publish(cfg, job)
    folder = cfg["workspace"] / "outbox" / job["id"]
    assert (folder / "clip01.mp4").read_bytes() == b"video"
    assert "--- tiktok ---" in (folder / "clip01.txt").read_text()
    assert store.load(cfg, job["id"])["clips"][0]["published"] == results


def test_publish_without_clips_fails(cfg):
    job = store.create(cfg, "x", "own")
    with pytest.raises(publish.PublishError):
        publish.publish(cfg, job)
