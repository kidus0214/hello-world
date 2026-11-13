"""Local dashboard: paste a link, watch the job, review clips, set the timer.

Binds to 127.0.0.1 only. State-changing requests must come from the dashboard page itself
(same-origin check), so another website open in the browser cannot start jobs.
"""

from __future__ import annotations

import json
import mimetypes
import queue
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import urlparse

from . import config, pipeline, publish, store


class App:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.jobs: queue.Queue = queue.Queue()
        self.schedule = store.read_state(cfg, "schedule", {
            "enabled": cfg["schedule"]["enabled"],
            "every_hours": cfg["schedule"]["every_hours"],
            "query": cfg["sources"]["query"],
            "last_run": 0,
            "last_result": "",
        })
        for job in store.list_jobs(cfg):  # jobs cut off by a restart would otherwise look busy forever
            if job["status"] in ("queued", "running"):
                job["status"], job["error"] = "error", "interrupted by a restart; submit it again"
                store.save(cfg, job)
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._timer, daemon=True).start()

    def _worker(self) -> None:
        """One job at a time: rendering already uses every core."""
        while True:
            task = self.jobs.get()
            try:
                task()
            except Exception as exc:  # keep the worker alive whatever a job does
                print(f"worker error: {exc}")

    def _timer(self) -> None:
        while True:
            time.sleep(30)
            sched = self.schedule
            due = sched["last_run"] + float(sched["every_hours"]) * 3600
            if sched["enabled"] and time.time() >= due:
                sched["last_run"] = time.time()
                self.save_schedule()
                self.jobs.put(self.run_auto)

    def run_auto(self) -> None:
        summary = pipeline.auto(self.cfg, self.schedule.get("query") or None)
        picked = summary.get("picked")
        self.schedule["last_result"] = (
            f"clipped: {picked['title']}" if picked else summary.get("reason", "nothing to do")
        )
        self.save_schedule()

    def save_schedule(self) -> None:
        store.write_state(self.cfg, "schedule", self.schedule)

    def submit(self, source: str, rights: str, options: dict) -> dict:
        job = store.create(self.cfg, source, rights, options)
        self.jobs.put(lambda: pipeline.run_job(self.cfg, job))
        return job


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ClipForge"

        def log_message(self, *_args) -> None:
            pass

        def _json(self, data, status: int = 200) -> None:
            body = json.dumps(data, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _same_origin(self) -> bool:
            host = self.headers.get("Host", "")
            if host.split(":")[0] not in ("127.0.0.1", "localhost"):
                return False
            origin = self.headers.get("Origin")
            return origin is None or urlparse(origin).netloc == host

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 1_000_000:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                body = resources.files("clipforge").joinpath("web/index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/state":
                self._json({
                    "jobs": store.list_jobs(app.cfg)[:40],
                    "schedule": app.schedule,
                    "publish": {k: app.cfg["publish"][k] for k in ("mode", "post_type", "platforms")},
                    "allowlist": app.cfg["sources"]["allowlist_channels"],
                })
            elif path.startswith("/media/"):
                self._media(path)
            else:
                self._json({"error": "not found"}, 404)

        def _media(self, path: str) -> None:
            match = re.fullmatch(r"/media/([\w-]+)/([\w-]+\.(?:mp4|jpg))", path)
            if not match:
                return self._json({"error": "not found"}, 404)
            file = store.job_dir(app.cfg, match.group(1)) / "clips" / match.group(2)
            if not file.is_file():
                return self._json({"error": "not found"}, 404)
            size = file.stat().st_size
            start, end = 0, size - 1
            ranged = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            if ranged and (ranged.group(1) or ranged.group(2)):
                if ranged.group(1):
                    start = int(ranged.group(1))
                    end = min(int(ranged.group(2)), size - 1) if ranged.group(2) else size - 1
                else:
                    start = max(size - int(ranged.group(2)), 0)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else:
                self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            with open(file, "rb") as handle:
                handle.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = handle.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    remaining -= len(chunk)

        def do_POST(self) -> None:
            if not self._same_origin():
                return self._json({"error": "forbidden"}, 403)
            path = urlparse(self.path).path
            try:
                data = self._body()
                if path == "/api/jobs":
                    source = str(data.get("source", "")).strip()
                    rights = data.get("rights", "unverified")
                    if not source:
                        return self._json({"error": "paste a video link or file path"}, 400)
                    if rights not in config.RIGHTS:
                        return self._json({"error": "unknown rights value"}, 400)
                    options = {
                        "count": int(data["count"]) if data.get("count") else None,
                        "layout": data.get("layout") if data.get("layout") in ("blur", "crop") else None,
                        "publish": bool(data.get("publish")),
                    }
                    return self._json(app.submit(source, rights, options), 201)
                if path == "/api/publish":
                    job = store.load(app.cfg, str(data.get("job", "")))
                    results = publish.publish(app.cfg, job, data.get("clips") or None)
                    return self._json({"results": results})
                if path == "/api/schedule":
                    if "enabled" in data:
                        app.schedule["enabled"] = bool(data["enabled"])
                    if "every_hours" in data:
                        app.schedule["every_hours"] = min(max(float(data["every_hours"]), 0.5), 168)
                    if "query" in data:
                        app.schedule["query"] = str(data["query"])[:200]
                    app.save_schedule()
                    return self._json(app.schedule)
                if path == "/api/auto":
                    app.schedule["last_run"] = time.time()
                    app.save_schedule()
                    app.jobs.put(app.run_auto)
                    return self._json({"queued": True})
                self._json({"error": "not found"}, 404)
            except publish.PublishError as exc:
                self._json({"error": str(exc)}, 502)
            except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc) or type(exc).__name__}, 400)

    return Handler


def serve(cfg: dict, port: int = 8787) -> None:
    app = App(cfg)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    print(f"ClipForge dashboard: http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
