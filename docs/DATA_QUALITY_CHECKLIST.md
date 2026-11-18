# Monthly data-quality checklist (before any comparison)

Run on day 3 of each month, after the exports are frozen. A failed check is fixed or written in the report's method
slide; it is never ignored. The SQL behind each check is in `sql/03_anomalies.sql`.

| # | Check | How | Pass if | In this study (SIMULATED) |
|---|---|---|---|---|
| 1 | **Definition changes** | read platform changelogs; compare raw "views" per reach before / after each documented date | ratio stable, or history rebuilt | Instagram raw views per reach x2.2 after Feb 2026: rebuilt with impressions before the change |
| 2 | **Duplicates** | same native post id in several market exports | each id counted once in group totals | 51 global posts appear 255 times; group reach overstated by 11% without the fix |
| 3 | **Time zones** | export setting per market; share of posts outside the posting policy window | every market in local time | Germany exported in UTC: 12% of posts "before 08:00" vs 2% elsewhere |
| 4 | **Sponsored vs organic** | join the ads export; spend on posts labelled organic | no organic post with spend | Italy: 228 posts labelled organic have ad spend |
| 5 | **Completeness** | posts and days per account vs last month | no gap > 2 days, no account missing | - |
| 6 | **Small samples** | posts per market x platform x month | >= 8 posts before ranking a rate | rates below the threshold shown in grey |
| 7 | **Denominator moves** | follower growth > 10% in a month | giveaway or campaign explained before reading ER by followers | Spain Instagram +37% in March 2026 (giveaway) |
| 8 | **Creator audience** | authenticity score of active creators | score >= 50 | one creator excluded |
| 9 | **Lexicon drift** | accuracy on a hand-labelled sample | >= 75% | see notebook |
