# KPI framework: one KPI, one meaning, in every market and on every platform

A comparison between countries or platforms is only fair if each KPI is computed the same way everywhere.
This page defines each KPI once, maps the native metrics of each platform to it, and lists the traps.

## Definitions

| KPI | Definition | Unit | Read it as |
|---|---|---|---|
| **Reach** | Unique accounts that saw the content at least once | accounts | size of the audience touched |
| **Views** (harmonised) | Every display of the content, all formats, repeats included | displays | exposure; always >= reach |
| **Impressions** | Former name of displays on several platforms; mapped to *views* | displays | only used to rebuild history |
| **Engagements** | likes (reactions) + comments (replies) + shares (reposts) + saves (bookmarks, favorites) | actions | active response |
| **Engagement rate by reach** | engagements / reach, on **organic** posts, summed over posts before dividing | % | content quality: did those who saw it react? **main comparison KPI** |
| **Engagement rate by followers** | average over posts of engagements / followers on the posting day | % | community activity; moves with the follower count, not only with content |
| **Follower growth** | followers at month end / followers at month start - 1 | % | community size; check for giveaways and bought followers |
| **Net sentiment** | % positive comments - % negative comments (rule-based lexicon in 5 languages) | points (-100 to +100) | direction of the conversation, not its exact level |
| **Share of voice** | mentions of the brand / mentions of all tracked brands, by creators of the market | % | weight in the creators' conversation |
| **Cost per engagement** | paid spend / engagements on sponsored posts | EUR | efficiency of paid support; never mixed with organic KPIs |

## Native metric -> harmonised metric

| Platform | Reach | Views | Engagements | Notes and traps |
|---|---|---|---|---|
| Instagram | reach | `impressions` before the definition change, `views` after | likes + comments + shares + saves | Meta introduced `views` and deprecated `plays` and `impressions` (Graph API v22.0, effective 21 April 2025 on all versions). Before the change, an export column called "views" may hold **video plays only**: never compare it with the new `views`. |
| TikTok | reach | video views | likes + comments + shares + favorites | the account export counts organic **and** paid views together: split with the ads export before reading organic results |
| Facebook | reach | views | reactions + comments + shares | no saves: engagement rates are slightly lower by construction |
| X | reach (when available) | impressions | likes + replies + reposts + bookmarks | |
| YouTube | unique viewers (estimated) | views | likes + comments | YouTube counts a view under its own rules: compare YouTube with YouTube |

## Comparison rules

1. **Organic and sponsored are never mixed.** A post is sponsored if the social tool says so *or* the ads export shows spend for it.
2. **One time zone per market.** Every timestamp is converted to the market's local time before "best time to post".
3. **Each post is counted once** in group totals; global posts shown in several market exports stay out of market comparisons.
4. **Engagement rate by reach is the main KPI across markets**; engagement rate by followers is read *with* follower growth.
5. **Compare platforms on rates, not volumes**, and only within the same format family (short video with short video).
6. **A definition change breaks a series**: rebuild the history with the new definition or show the break on the chart.
7. **Small samples are not compared**: under 8 posts (or 40 scored comments) a monthly rate is shown in grey, not ranked.
