# ClipForge

Paste a video link, get captioned vertical clips, and queue them for TikTok, YouTube Shorts,
Instagram, Facebook, Threads, X and Reddit. Built for a GTA VI clip account, usable for any
niche.

```
link or file ─▶ download ─▶ transcript ─▶ Claude picks the moments ─▶ ffmpeg renders 9:16
                                                                      with captions + hook
             ─▶ outbox folder, or Postiz drafts / scheduled posts on every platform
```

## Set up on a Mac

```bash
git clone <this repo> && cd hello-world
./mac/install.sh
```

The installer adds ffmpeg (with caption support), deno and node through Homebrew, creates a
Python environment, starts the dashboard as a background service and puts **ClipForge.app**
in `~/Applications`. Then:

1. Put your Claude API key in `.env` (`ANTHROPIC_API_KEY=...`).
2. Open ClipForge.app (or <http://127.0.0.1:8787>), paste a link, press **Make clips**.
3. To post automatically, follow `docs/account-setup.md` to create your accounts and connect
   them to Postiz, then set `publish.mode = "postiz"` in `config.toml`.

`clipforge doctor` shows what is installed and what is missing.

## Using it

| You want to | Do this |
|---|---|
| Clip one video | Dashboard, or `clipforge run "<url or file>" --rights own` |
| See what is worth clipping | `clipforge discover` |
| Clip the most viewed new video from your allowed channels | `clipforge auto`, or turn on the **Timer** in the dashboard |
| Send finished clips to the queue | **Send all to publish queue** in the dashboard, or `clipforge publish <job id>` |
| Preview what would be posted | `clipforge publish <job id> --dry-run` |
| Use it from Claude Code | `/clip <link>` and `/clip-scout` in this repo |

Clips land in `workspace/jobs/<job id>/clips/`. In the default `outbox` mode, publishing copies
each clip plus a text file of per-platform captions to `workspace/outbox/`, ready to upload by
hand.

### Rights

Every job records what rights you have to the source: `own` (your footage), `licensed` (a
clipping campaign or the creator said yes), `cc` (Creative Commons) or `unverified`.

- The timer only clips channels listed in `sources.allowlist_channels`.
- `unverified` clips are never auto-published; they become drafts for you to review.

Read `docs/gta6-content-rules.md` before posting GTA VI footage. Re-uploading trailers or
other creators' videos without permission is how new accounts get struck, and it does not
earn on any platform's monetization program.

### Without a Claude API key

ClipForge still runs. It picks moments from audio loudness and scene cuts and writes generic
captions; the job shows `moments picked by: signals`.

## Claude Code skills and subagents

| Name | Kind | Model | Purpose |
|---|---|---|---|
| `/clip` | skill | session model | Clip a link, review the copy, publish on request |
| `/clip-scout` | skill | session model | Find what to clip next |
| `trend-scout` | subagent | Haiku | Research what is trending in the niche |
| `caption-writer` | subagent | Haiku | Rewrite hooks, titles and captions |
| `clip-producer` | subagent | Sonnet | Run one video through the pipeline (use several in parallel) |
| `account-setup-guide` | subagent | Haiku | Walk you through creating and connecting accounts |

## Docs

- `docs/launch-plan.md`: what to do before, during and after GTA VI launch week
- `docs/monetization-playbook.md`: how clipping pays, with rates and requirements
- `docs/gta6-content-rules.md`: what is safe to post and what gets struck
- `docs/account-setup.md`: account checklist and Postiz connection

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests need `ffmpeg` on PATH; they build a small synthetic video and run the real pipeline on
it. Nothing in the test suite touches the network.
