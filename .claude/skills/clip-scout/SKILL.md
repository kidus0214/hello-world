---
name: clip-scout
description: Find the most viewed new videos worth clipping (allowlisted channels first) and optionally clip the top one. Use when the user asks what to clip next, wants trending GTA VI videos, or wants the scheduled "grab the top video" run done now.
---

# Scout for videos to clip

1. Run `clipforge discover --top 10` (add `--query "<terms>"` if the user named a topic).
   Rows marked `allowed` come from channels in `sources.allowlist_channels` in `config.toml`,
   meaning the user owns them or has clipping permission. `not-list` rows do not.
2. Present the list: views, length, title, channel, and whether it is allowed. Recommend one
   or two, favouring allowed sources with a clear standalone moment over raw view count.
3. For a `not-list` video the user wants anyway, tell them the two real options: get the
   creator's permission (many run clipping campaigns, see `docs/monetization-playbook.md`)
   and add the channel to the allowlist, or clip it as `--rights unverified`, which stays a
   draft for them to judge. Never add a channel to the allowlist on your own.
4. To clip the top allowed video in one go, run `clipforge auto`. It skips videos already
   processed and sends the clips to the configured publish queue.

For broad research ("what is trending around GTA VI this week") delegate to the
`trend-scout` subagent and keep only its shortlist.
