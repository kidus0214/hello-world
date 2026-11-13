# GTA VI launch plan

GTA VI releases November 19, 2026. This plan assumes you start from zero accounts.

## Before launch (now to Nov 18)

1. Run `mac/install.sh` and `clipforge doctor` until everything required is `ok`.
2. Create the accounts in `docs/account-setup.md` and warm them up.
3. Sign up for Postiz Cloud, connect every channel, and send one test draft through
   `clipforge publish <job id>`.
4. Find campaigns: search Whop Content Rewards for GTA and gaming creators, and join the
   Discords of streamers who have said they will play at launch. Add each campaign creator's
   channel to `sources.allowlist_channels`.
5. Make three to five breakdown clips now so the accounts are not empty on launch day. Use
   your own commentary over short trailer excerpts, not trailer re-uploads
   (`docs/gta6-content-rules.md`, lane 5).

## Launch week (Nov 19 to 26)

- **If you have the game:** capture your own sessions with the radio off, drop each recording
  into ClipForge with rights set to "My own footage", and post two or three clips a day. This
  is the safest lane and the one platforms are least likely to treat as unoriginal.
- **Campaign clips:** turn the timer on (every 3 to 6 hours) so new videos from allowlisted
  creators are clipped as they land. Submit every post link to its campaign the same day.
- Keep spoilers out of hooks, titles and thumbnails. Rockstar names story reveals and endings
  as takedown targets, and spoiler posts get reported by viewers.
- Review drafts before they go out for the first week. Switch to `post_type = "schedule"`
  only once the picks are consistently good.

## After launch

- Each week, look at which clips passed 10K views and what their hooks had in common; put
  that into `ai.voice` in `config.toml` so the picker leans that way.
- When TikTok followers pass 10,000, raise `clips.max_seconds` above 60 for TikTok-eligible
  clips (Creator Rewards only counts videos of a minute or more).
- Add a second income lane only once one works: campaigns first, platform programs second.

## What it costs to run

| Item | Cost |
|---|---|
| Claude API, picking moments for one video | A few cents with `claude-opus-5-5` for a typical 10 to 20 minute transcript; set `ai.model = "claude-haiku-5-5"` to cut that by roughly 40x |
| Postiz Cloud, 10 channels | About $39 a month (confirm on their pricing page) |
| X API posts through a scheduler | May be billed per post; check whether your Postiz plan covers it |
| Everything else (ffmpeg, yt-dlp, ClipForge) | Free |
