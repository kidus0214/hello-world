# ClipForge

Python tool that turns long videos into captioned vertical clips and queues them for posting.
See `README.md` for usage.

## Layout

- `clipforge/pipeline.py`: job orchestration (ingest, transcript, pick, render, publish)
- `clipforge/picker.py`: Claude moment selection with a signal-based fallback
- `clipforge/render.py`: ffmpeg filter graph and ASS captions
- `clipforge/publish.py`: Postiz CLI wrapper and outbox export
- `clipforge/server.py` + `clipforge/web/index.html`: local dashboard and timer
- `mac/install.sh`: launchd service and ClipForge.app
- `docs/`: research (monetization, GTA VI content rules, account setup, launch plan)

## Commands

- `pytest` runs everything (needs ffmpeg, no network)
- `clipforge doctor` checks the local toolchain
- `CLIPFORGE_CONFIG=/path/config.toml` points at a different config

## Rules for changes

- The rights model is load-bearing: the timer only processes allowlisted channels, and
  `unverified` jobs must never be scheduled or auto-published. Keep the tests that cover this.
- The dashboard binds to 127.0.0.1 and rejects cross-origin POSTs. Video titles, captions and
  logs are untrusted text; render them with `textContent`, never as HTML.
- Never add code that creates platform accounts, automates sign-up or login, or gets around a
  platform's rate limits or verification.
- Claude API calls go through the `anthropic` SDK. Check the `claude-api` skill before
  changing model ids or request parameters.
