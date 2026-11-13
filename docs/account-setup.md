# Account setup

You create these accounts yourself. Sign-up needs your phone number, your date of birth and
your agreement to each platform's terms, and platforms prohibit accounts created by automated
means (Instagram's terms say so explicitly; Meta has sued automation services over it). An
account an agent creates for you is the kind that gets banned first. Budget about an hour.

Researched 2026-11-13, mostly from secondary sources; items marked (unverified) should be
checked on the platform's own help page.

## Checklist

- [ ] Pick one handle that is free everywhere (check each site before committing)
- [ ] Gmail account for the brand, with 2-step verification on
- [ ] YouTube channel on that Google account
- [ ] Instagram, switched to a Business account
- [ ] Facebook Page (not a personal profile), linked to the Instagram account
- [ ] Threads (signs in with the Instagram account)
- [ ] TikTok, kept as a personal account
- [ ] X
- [ ] Reddit
- [ ] Postiz account, with every channel above connected
- [ ] Password manager entry for each, recovery email and phone recorded

## Order and account types

| # | Platform | Do this | Why |
|---|---|---|---|
| 1 | Gmail | Create at accounts.google.com. Use it as the sign-up email everywhere else. | One recovery point for the whole brand. |
| 2 | YouTube | Create a channel on the new Google account; verify the phone number in YouTube settings (unverified: needed for custom thumbnails and long uploads). | Shorts go here. |
| 3 | Instagram | Create the account, then switch to **Business** in settings. | Scheduling tools publish Reels through the API, which is reported to need a Business account ([Blotato](https://www.blotato.com/blog/instagram-posting-api)). |
| 4 | Facebook | Create a **Page** for the brand and link the Instagram account to it. | API posting works with Pages, not profiles. |
| 5 | Threads | Join with the Instagram account. | |
| 6 | TikTok | Create and keep it a **personal** account. | Only personal accounts are eligible for Creator Rewards and get the full music library ([Hootsuite](https://blog.hootsuite.com/tiktok-business-vs-personal)). |
| 7 | X | Create the account. | |
| 8 | Reddit | Create the account; spend a few days as a normal member before posting clips. | Gaming subreddits remove drive-by self-promotion. Read each subreddit's rules. |

Warm each account up for a few days (profile picture, bio, follow a few accounts in the niche,
watch and like some videos) before posting from a scheduler.

## Connecting them for automatic posting

ClipForge posts through [Postiz](https://postiz.com), an open-source scheduler.

- **Use hosted Postiz Cloud.** It supplies platform apps that are already approved. If you
  self-host or call the platform APIs yourself, TikTok and YouTube lock posts from unaudited
  apps to private, and those audits take days to weeks
  ([TikTok](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post),
  [YouTube](https://developers.google.com/youtube/v3/docs/videos/insert)).
- **Plan.** Reported pricing is $29 a month for 5 channels, $39 for 10, $49 for 30. Seven
  platforms needs the 10-channel tier. Confirm at <https://postiz.com/pricing>.
- **Connect.** Add each channel in the Postiz web app, then on the Mac:

  ```bash
  npm install -g postiz
  postiz auth:login
  postiz integrations:list      # every connected channel should appear
  ```

- **Switch ClipForge over.** In `config.toml` set `publish.mode = "postiz"`. Leave
  `post_type = "draft"` until you trust the output: clips arrive in Postiz as drafts and you
  press publish. Change to `"schedule"` to have them go out at your time slots unattended.
- **Check the plan before the first real run:** `clipforge publish <job id> --dry-run`.

## Limits worth knowing

| Platform | Limit | Source |
|---|---|---|
| TikTok | About 15 API posts per account per day | [TikTok guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines), partly third-party |
| Instagram | 100 API-published posts per rolling 24 hours | [Meta](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| Threads | 250 posts per 24 hours | [Meta](https://developers.facebook.com/documentation/threads/posts) |
| X | API posting is pay-per-use: about $0.015 a post, $0.20 if it contains a link | [postproxy](https://postproxy.dev/blog/x-api-pricing-2026) (third-party) |
| Reddit | No confirmed official video-upload route through the API | unverified |

ClipForge keeps X posts link-free for that reason, and skips Reddit until you set
`publish.settings.reddit.subreddit`. Run `postiz integrations:settings <channel id>` to see
exactly what each of your channels accepts.

All platforms take 9:16 video at 1080x1920, which is what ClipForge renders. Clips default to
under 60 seconds so the same file is valid as a Short, a Reel and a TikTok.
