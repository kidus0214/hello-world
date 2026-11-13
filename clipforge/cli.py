"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from . import config, discover, media, pipeline, publish, store, transcript


def cmd_doctor(cfg, _args) -> int:
    filters = media.ffmpeg_filters()
    checks = [
        ("ffmpeg", media.have("ffmpeg"), "brew install ffmpeg-full"),
        ("ffprobe", media.have("ffprobe"), "comes with ffmpeg"),
        ("ffmpeg caption filter (libass)", "ass" in filters,
         "Homebrew's slim ffmpeg lacks it: brew install ffmpeg-full"),
        ("yt-dlp", _importable("yt_dlp"), "pip install -U yt-dlp"),
        ("deno (yt-dlp needs a JS runtime for YouTube)", media.have("deno"), "brew install deno"),
        ("anthropic SDK", _importable("anthropic"), "pip install anthropic"),
        ("Claude credentials", _has_claude_credentials(),
         "put ANTHROPIC_API_KEY=... in .env (without it, moments are picked from audio and cuts only)"),
        ("local Whisper (optional)", transcript.whisper_available(), "pip install 'clipforge[whisper]'"),
        ("postiz CLI (optional)", shutil.which("postiz") is not None, "npm install -g postiz"),
    ]
    ok = True
    for name, passed, fix in checks:
        print(f"  {'ok  ' if passed else 'MISS'}  {name}" + ("" if passed else f"   -> {fix}"))
        if not passed and "optional" not in name and "deno" not in name and "Claude" not in name:
            ok = False
    print(f"\nworkspace: {cfg['workspace']}")
    print(f"publish mode: {cfg['publish']['mode']} ({cfg['publish']['post_type']})")
    return 0 if ok else 1


def _importable(module: str) -> bool:
    try:
        __import__(module)
    except ImportError:
        return False
    return True


def _has_claude_credentials() -> bool:
    import os
    from pathlib import Path

    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or (Path.home() / ".config" / "anthropic").is_dir()
    )


def _print_job(job: dict) -> None:
    print(f"\njob {job['id']}  [{job['status']}]  {job['meta'].get('title', job['source'])}")
    if job["error"]:
        print(f"  error: {job['error']}")
    if job["selector"]:
        print(f"  moments picked by: {job['selector']}")
    for clip in job["clips"]:
        print(f"  {clip['id']}  {clip['start']:7.1f}s -> {clip['end']:7.1f}s  "
              f"score {clip.get('score', '?'):>2}  {clip.get('title', '')}")
        for note in clip.get("notes", []):
            print(f"         note: {note}")


def cmd_run(cfg, args) -> int:
    job = pipeline.run_source(
        cfg, args.source, args.rights,
        count=args.clips, layout=args.layout, no_ai=args.no_ai, publish=args.publish,
    )
    _print_job(job)
    if job["status"] == "done":
        print(f"\nclips: {store.job_dir(cfg, job['id']) / 'clips'}")
    return 0 if job["status"] == "done" else 1


def cmd_discover(cfg, args) -> int:
    found = discover.candidates(cfg, args.query)
    if not found:
        print("nothing found (check sources.allowlist_channels / sources.query and your connection)")
        return 1
    for item in found[: args.top]:
        mark = "allowed " if item["trusted"] else "not-list"
        print(f"{item['views']:>12,}  {mark}  {item['duration'] / 60:5.1f}m  {item['title'][:70]}\n"
              f"{'':14}{item['url']}  ({item['channel']})")
    return 0


def cmd_auto(cfg, args) -> int:
    summary = pipeline.auto(cfg, args.query)
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary.get("picked") and summary.get("status") == "done" else 1


def cmd_publish(cfg, args) -> int:
    job = store.load(cfg, args.job)
    try:
        results = publish.publish(cfg, job, args.clips or None, dry_run=args.dry_run)
    except publish.PublishError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2))
    return 1 if any(r.get("error") for r in results) else 0


def cmd_jobs(cfg, _args) -> int:
    for job in store.list_jobs(cfg)[:30]:
        print(f"{job['id']}  {job['status']:8}  {len(job['clips'])} clips  "
              f"{job['meta'].get('title', job['source'])[:60]}")
    return 0


def cmd_serve(cfg, args) -> int:
    from . import server

    server.serve(cfg, args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clipforge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="check that everything needed is installed").set_defaults(fn=cmd_doctor)

    run = sub.add_parser("run", help="clip one video (URL or local file)")
    run.add_argument("source")
    run.add_argument("--rights", choices=config.RIGHTS, default="unverified",
                     help="own = your footage, licensed = you have permission, cc = Creative Commons")
    run.add_argument("--clips", type=int, help="number of clips")
    run.add_argument("--layout", choices=("blur", "crop"))
    run.add_argument("--no-ai", action="store_true", help="skip Claude, pick from audio and cuts")
    run.add_argument("--publish", action="store_true", help="send clips to the outbox / Postiz when done")
    run.set_defaults(fn=cmd_run)

    disc = sub.add_parser("discover", help="list the most viewed candidate videos")
    disc.add_argument("--query")
    disc.add_argument("--top", type=int, default=10)
    disc.set_defaults(fn=cmd_discover)

    auto = sub.add_parser("auto", help="clip the most viewed new video from allowed sources")
    auto.add_argument("--query")
    auto.set_defaults(fn=cmd_auto)

    pub = sub.add_parser("publish", help="publish a finished job's clips")
    pub.add_argument("job")
    pub.add_argument("--clips", nargs="*", help="clip ids (default: all)")
    pub.add_argument("--dry-run", action="store_true")
    pub.set_defaults(fn=cmd_publish)

    sub.add_parser("jobs", help="list recent jobs").set_defaults(fn=cmd_jobs)

    serve = sub.add_parser("serve", help="run the local dashboard")
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(fn=cmd_serve)

    args = parser.parse_args(argv)
    try:
        cfg = config.load()
    except (ValueError, OSError) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    return args.fn(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
