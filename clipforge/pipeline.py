"""Run a job end to end: ingest, transcribe, pick moments, render, optionally publish."""

from __future__ import annotations

import copy
import traceback

from . import discover, ingest, media, picker, publish, render, store, transcript


def _job_cfg(cfg: dict, job: dict) -> dict:
    """Per-job overrides (clip count, layout) on top of the global config."""
    merged = copy.deepcopy(cfg)
    options = job.get("options", {})
    if options.get("count"):
        merged["clips"]["count"] = int(options["count"])
    if options.get("layout") in ("blur", "crop"):
        merged["clips"]["layout"] = options["layout"]
    return merged


def run_job(cfg: dict, job: dict) -> dict:
    jcfg = _job_cfg(cfg, job)
    folder = store.job_dir(cfg, job["id"])

    def step(name: str, message: str) -> None:
        job["status"], job["step"] = "running", name
        store.log(cfg, job, message)

    try:
        step("ingest", f"fetching {job['source']}")
        source, meta = ingest.ingest(job["source"], folder, cfg["sources"]["max_source_minutes"])
        job["meta"] = meta

        step("transcript", "reading captions")
        words = transcript.load_captions(folder)
        if not words and meta.get("has_audio") and transcript.whisper_available():
            store.log(cfg, job, "no captions found, transcribing locally with Whisper")
            words = transcript.transcribe_whisper(source)
        transcript.save(words, folder / "words.json")
        store.log(cfg, job, f"{len(words)} words of transcript")

        step("analyse", "measuring loudness and scene cuts")
        loudness = media.loudness_per_second(source) if meta.get("has_audio") else []
        cuts = media.scene_cuts(source)

        step("pick", "choosing moments")
        clips, selector = picker.pick(meta, words, loudness, cuts, jcfg,
                                      use_ai=not job["options"].get("no_ai"))
        job["selector"] = selector
        job["clips"] = clips
        store.log(cfg, job, f"{len(clips)} clips chosen by {selector}")
        if not clips:
            raise RuntimeError("no usable moments were found in this video")

        for clip in clips:
            step("render", f"rendering {clip['id']} ({clip['start']:.0f}s-{clip['end']:.0f}s)")
            clip.update(render.render_clip(source, clip, words, meta, jcfg, folder / "clips"))
            store.save(cfg, job)

        if job["options"].get("publish"):
            step("publish", "sending clips to " + cfg["publish"]["mode"])
            results = publish.publish(cfg, job)
            failed = [r for r in results if r.get("error")]
            store.log(cfg, job, f"published {len(results) - len(failed)} posts, {len(failed)} failed")

        job["status"], job["step"] = "done", ""
        store.log(cfg, job, "done")
    except Exception as exc:  # a job must always end in a recorded state
        job["status"] = "error"
        job["error"] = f"{type(exc).__name__}: {exc}"
        store.log(cfg, job, traceback.format_exc(limit=3))
    return job


def run_source(cfg: dict, source: str, rights: str = "unverified", **options) -> dict:
    job = store.create(cfg, source, rights, options)
    return run_job(cfg, job)


def auto(cfg: dict, query: str | None = None) -> dict:
    """Clip the most viewed new video from the allowed sources. Returns a summary."""
    found = discover.candidates(cfg, query)
    allow_unverified = cfg["sources"]["allow_unverified"]
    for item in found:
        if not item["trusted"] and not allow_unverified:
            continue
        rights = "licensed" if item["trusted"] else "unverified"
        job = run_source(cfg, item["url"], rights, publish=True)
        discover.mark_seen(cfg, item["id"])
        return {"picked": item, "job": job["id"], "status": job["status"], "error": job["error"]}
    skipped = [item for item in found if not item["trusted"]]
    return {
        "picked": None,
        "reason": (
            "no new videos from allowlisted channels"
            + (f"; {len(skipped)} search results were skipped because their channels are not on "
               "sources.allowlist_channels" if skipped else "")
        ),
    }
