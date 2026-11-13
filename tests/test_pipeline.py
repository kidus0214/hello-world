import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from clipforge import discover, media, pipeline, render, server, store
from clipforge.transcript import Word


def test_run_local_file_end_to_end(cfg, sample_video):
    job = pipeline.run_source(cfg, str(sample_video), "own", no_ai=True, publish=True)
    assert job["status"] == "done", job["error"]
    assert job["selector"] == "signals" and job["clips"]
    best = max(job["clips"], key=lambda c: c["score"])
    assert best["start"] < 20 and best["end"] > 12          # the loud passage
    clips_dir = store.job_dir(cfg, job["id"]) / "clips"
    info = media.probe(clips_dir / best["file"])
    assert (info["width"], info["height"]) == (1080, 1920) and info["has_audio"]
    assert abs(info["duration"] - (best["end"] - best["start"])) < 0.3
    assert (clips_dir / best["thumb"]).stat().st_size > 0
    assert (cfg["workspace"] / "outbox" / job["id"] / best["file"]).is_file()


def test_missing_source_is_a_recorded_error(cfg):
    job = pipeline.run_source(cfg, "/nope/missing.mp4", "own")
    assert job["status"] == "error" and "file not found" in job["error"]


def test_captions_never_overlap_on_screen(cfg):
    words = [Word(i * 0.5, i * 0.5 + 0.5, f"w{i}") for i in range(12)]
    ass = render.build_ass({"start": 0, "end": 6, "hook": "A {tricky} hook"}, words, cfg, "via Someone")
    captions = [line.split(",") for line in ass.splitlines() if ",Caption," in line]
    spans = [(line[1], line[2]) for line in captions]
    assert len(spans) == 12
    assert all(a_end <= b_start for (_, a_end), (b_start, _) in zip(spans, spans[1:]))
    assert "A (tricky) hook" in ass and "via Someone" in ass


def test_crop_layout_and_vertical_sources_skip_the_blur():
    assert "boxblur" in render.video_filter(1920, 1080, "blur", None)
    assert "boxblur" not in render.video_filter(1920, 1080, "crop", None)
    assert "boxblur" not in render.video_filter(1080, 1920, "blur", "c.ass")


def test_auto_only_clips_allowlisted_sources(cfg, monkeypatch):
    found = [
        {"id": "a", "url": "u1", "title": "big", "views": 900, "trusted": False},
        {"id": "b", "url": "u2", "title": "mine", "views": 10, "trusted": True},
    ]
    monkeypatch.setattr(discover, "candidates", lambda *_a, **_k: found)
    ran = []

    def fake_run(_cfg, source, rights, **options):
        ran.append((source, rights, options))
        return {"id": "j", "status": "done", "error": ""}

    monkeypatch.setattr(pipeline, "run_source", fake_run)
    summary = pipeline.auto(cfg)
    assert ran == [("u2", "licensed", {"publish": True})] and summary["picked"]["id"] == "b"
    assert store.read_state(cfg, "seen", []) == ["b"]

    monkeypatch.setattr(discover, "candidates", lambda *_a, **_k: found[:1])
    summary = pipeline.auto(cfg)
    assert summary["picked"] is None and "not on" in summary["reason"] and len(ran) == 1

    cfg["sources"]["allow_unverified"] = True
    pipeline.auto(cfg)
    assert ran[-1][:2] == ("u1", "unverified")


def _request(port, path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def test_dashboard_api(cfg):
    job = store.create(cfg, "x", "own")
    clips = store.job_dir(cfg, job["id"]) / "clips"
    clips.mkdir()
    (clips / "clip01.mp4").write_bytes(bytes(range(100)))
    job["status"] = "running"
    store.save(cfg, job)

    app = server.App(cfg)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(app))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, body, _ = _request(port, "/")
        assert status == 200 and b"ClipForge" in body
        state = json.loads(_request(port, "/api/state")[1])
        assert state["jobs"][0]["status"] == "error"          # stale job from before the restart

        status, body, headers = _request(port, f"/media/{job['id']}/clip01.mp4", headers={"Range": "bytes=10-19"})
        assert status == 206 and body == bytes(range(10, 20)) and headers["Content-Range"] == "bytes 10-19/100"
        assert _request(port, f"/media/{job['id']}/..%2Fjob.json")[0] == 404

        status, _, _ = _request(port, "/api/schedule", {"enabled": True}, {"Origin": "https://evil.example"})
        assert status == 403 and app.schedule["enabled"] is False
        status, body, _ = _request(port, "/api/schedule", {"enabled": True, "every_hours": 0.1},
                                   {"Origin": f"http://127.0.0.1:{port}"})
        assert status == 200 and json.loads(body)["every_hours"] == 0.5
        assert store.read_state(cfg, "schedule", {})["enabled"] is True

        assert _request(port, "/api/jobs", {"source": ""})[0] == 400
        assert _request(port, "/api/jobs", {"source": "x", "rights": "stolen"})[0] == 400
    finally:
        httpd.shutdown()
