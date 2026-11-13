# How clipping makes money

Researched 2026-11-13. The research could not open most official policy pages, so the numbers
here come mainly from secondary and vendor blogs (several of which sell clipping tools). Treat
them as directional and check the linked page before you rely on one.

## The short version

- **The realistic income is pay-per-view campaigns**, not platform ad revenue. A creator or
  brand pays you per 1,000 verified views on clips of *their* content, posted on *your*
  accounts. This is also the only lane where you clearly have permission to use the footage.
- **Platform payouts are small and gated** behind audiences a new account does not have.
- **Raw re-uploads earn nothing and get accounts limited.** Every major platform now
  demonetizes or down-ranks unoriginal reposts. Captions, reframing, a hook and your own
  commentary are what make a clip yours.
- At about $1 per 1,000 views, 100,000 views is roughly $100 before fees. Plan for weeks, not
  days, before a first payout.

## 1. Pay-per-view campaigns (start here)

| Where | How it works | Reported rate per 1,000 views | Watch for |
|---|---|---|---|
| Whop Content Rewards | Join a campaign, clip the creator's content, post it, submit the link. Paid on approved, verified views up to the campaign budget. | Median about $1.00, range $0.05 to $3.00 across 50 campaigns ([Foundry](https://www.builtbyfoundry.io/blog/what-is-clipping-1-dollar-per-1000-views-50-campaigns)); most $0.50 to $1.50 ([ClipAffiliates](https://www.clipaffiliates.com/blog/clipping-cpm-rates-2026)) | Some campaigns pay nothing until a clip passes 10K to 100K views ([Opus](https://www.opus.pro/blog/vyro-vs-whop)). Platform fee reported as 7% or 10%. |
| Vyro | Same model. | Marketed at $3, listed campaigns show $1 to $2 ([ClipAffiliates](https://www.clipaffiliates.com/blog/vyro-review)) | Per-clip ceiling reportedly $1,000; earnings can be clawed back for fake engagement. |
| Streamer-run programs | A streamer's team runs a Discord and pays clippers directly. | One reported example: $0.40 ($40 per 100K views) ([Lumina](https://luminaclippers.com/blog/clipping-streamers), relaying Business Insider) | Rules differ per streamer. |
| Gaming campaigns in general | | $0.30 to $1.50 ([OpenClip](https://openclip.app/clipping/gaming-clipping.md)) | |

No clipping program run by Rockstar or Take-Two was found. GTA VI money will come from
**streamers and YouTubers who play GTA VI and pay clippers**, so look for their campaigns
on Whop and in their Discords during launch week.

How to work a campaign with ClipForge:

1. Join the campaign and read its rules (required hashtags, banned edits, minimum views).
2. Add the creator's channel to `sources.allowlist_channels` in `config.toml`.
3. Clip with `--rights licensed`, or let the timer pick up their newest videos.
4. Post, then submit each post link to the campaign.

Warning signs: anything that charges you to join, hides its minimums or caps, or pays only in
"exposure". No verified scam reports were found, but check Reddit and Trustpilot for a
campaign's name before putting hours into it.

## 2. Platform programs (later)

| Platform | Reported bar to get paid | Notes |
|---|---|---|
| YouTube Shorts | 1,000 subscribers plus 10M Shorts views in 90 days ([AIR](https://air.io/en/monetization/youtube-partner-program-requirements-2026-the-complete-guide)) | A higher bar for new applicants is reported from 2027-02-01, with sources disagreeing on the numbers ([PPC Land](https://ppc.land/new-youtube-creators-face-8-000-hour-bar-for-ad-revenue-from-february-2027/)). Check YouTube's own page. |
| TikTok Creator Rewards | 10,000 followers, 100,000 views in 30 days, age 18+, personal account ([ttcalculator](https://ttcalculator.net/learn/creator-rewards-program/)) | Only videos of 60 seconds or more qualify. Reported $0.40 to $1.00 per 1,000 views. ClipForge defaults to clips under 60 seconds, so raise `clips.max_seconds` once you are in the program. |
| Facebook | Invite-only ([Buffer](https://buffer.com/resources/how-to-make-money-on-facebook/)) | Thresholds and rates conflict between sources. |
| X | The old revenue sharing closed to new sign-ups in August 2026; a replacement program exists ([X Help](https://help.x.com/en/using-x/creator-revenue-sharing)) | Details not confirmed. |
| Snapchat Spotlight | About 50,000 followers reported ([ShortSync](https://www.shortsync.app/resources/snapchat-spotlight-monetization-2026)) | Reported $0.10 to $0.30 per 1,000 views. |
| Instagram, Threads, Reddit | No reliable 2026 data found | Treat as reach, not income. |

## 3. What keeps a clip account monetizable

- YouTube's 2025 "inauthentic content" update targets templated, mass-produced channels;
  reused content is allowed when it adds real commentary or modification
  ([PPC Land](https://ppc.land/youtube-clarifies-inauthentic-content-policy-changes/)).
- Meta reduces reach and removes monetization for accounts that repeatedly repost others'
  content; reactions and commentary are fine
  ([TechCrunch](https://techcrunch.com/2025/07/14/following-youtube-meta-announces-crackdown-on-unoriginal-facebook-content)).
- TikTok is reported to treat reposts and watermarked copies as ineligible; a logo overlay
  does not make content original ([BigSeller](https://www.bigseller.pro/blog/articleDetails/3778/tiktok-unoriginal-content.htm)).

In practice: add your own voiceover or on-screen take, edit beyond a trim, give each clip its
own angle, and never upload a file with another platform's watermark on it.

## 4. Mistakes that get new accounts limited

1. Several accounts posting the same clips.
2. Posting the identical file everywhere at the same second, at high volume. ClipForge
   spaces posts into daily slots for this reason; start at one to three a day per platform.
3. Leaving another platform's watermark on a clip.
4. Zero transformation of someone else's footage.
5. Buying views or engagement. Campaigns claw back for it.

## Other income, once you have an audience

Driving viewers to your own long-form channel, affiliate links in your bio, and brand deals
are the usual next steps. No solid 2026 figures were found for any of them.
