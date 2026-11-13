---
name: clip
description: Turn a video link or local file into captioned vertical clips with ClipForge and queue them for posting. Use when the user gives a video URL/file and wants clips, shorts, reels or TikToks made from it, or asks to publish finished clips.
---

# Clip a video

The user gives a video URL or a file path (in the arguments or the message). Produce clips
with the `clipforge` CLI in this repo, then report what was made.

1. **Rights.** Work out which applies and pass it as `--rights`:
   - `own`: the user's own captured footage
   - `licensed`: a clipping campaign or the creator gave permission
   - `cc`: the video is Creative Commons licensed
   - `unverified`: anything else, including "it's on YouTube". These clips only ever become
     drafts. If the user hasn't said, ask once which applies; do not guess `own` or `licensed`.
2. **Run it.** `clipforge run "<source>" --rights <rights>` (add `--clips N`, `--layout crop`
   when asked). If `clipforge` is not on PATH use `.venv/bin/clipforge`. A run takes a few
   minutes; run it in the background for long videos.
3. **Review the picks.** Read `workspace/jobs/<job id>/job.json`. For each clip check the
   hook, title and caption against `docs/gta6-content-rules.md`: no story spoilers in titles,
   nothing presented as confirmed that is rumour, nothing calling footage "leaked". Fix weak
   or misleading copy by editing the clip's fields in `job.json` before publishing.
4. **Show the result.** List each clip with time range, score and title, and where the files
   are (`workspace/jobs/<job id>/clips/`). Mention if moments were picked by `signals`
   instead of Claude, since that means the captions are generic.
5. **Publish only when asked.** `clipforge publish <job id> --dry-run` first, show the plan,
   then `clipforge publish <job id>`. In `postiz` mode read the `postiz` skill's rules before
   changing any provider settings. Report failures per platform; do not retry blindly.

If a step fails, run `clipforge doctor` and fix what it reports before trying again.
