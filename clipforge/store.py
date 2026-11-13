"""Job state on disk: one folder per job, one job.json inside it."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path

_lock = threading.Lock()


def jobs_dir(cfg: dict) -> Path:
    path = cfg["workspace"] / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_dir(cfg: dict, job_id: str) -> Path:
    # job ids are generated here; reject anything that could escape the jobs folder
    if not job_id or not all(c.isalnum() or c in "-_" for c in job_id):
        raise ValueError(f"bad job id: {job_id!r}")
    return jobs_dir(cfg) / job_id


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


def create(cfg: dict, source: str, rights: str, options: dict | None = None) -> dict:
    job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    job = {
        "id": job_id,
        "source": source,
        "rights": rights,
        "options": options or {},
        "status": "queued",
        "step": "",
        "created": time.time(),
        "meta": {},
        "selector": "",
        "clips": [],
        "log": [],
        "error": "",
    }
    job_dir(cfg, job_id).mkdir(parents=True)
    save(cfg, job)
    return job


def save(cfg: dict, job: dict) -> None:
    with _lock:
        _write_json(job_dir(cfg, job["id"]) / "job.json", job)


def load(cfg: dict, job_id: str) -> dict:
    return json.loads((job_dir(cfg, job_id) / "job.json").read_text())


def list_jobs(cfg: dict) -> list[dict]:
    jobs = []
    for path in sorted(jobs_dir(cfg).glob("*/job.json"), reverse=True):
        try:
            jobs.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return jobs


def log(cfg: dict, job: dict, message: str) -> None:
    job["log"].append({"t": time.time(), "msg": message})
    save(cfg, job)


def read_state(cfg: dict, name: str, default):
    path = cfg["workspace"] / f"{name}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def write_state(cfg: dict, name: str, data) -> None:
    with _lock:
        _write_json(cfg["workspace"] / f"{name}.json", data)
