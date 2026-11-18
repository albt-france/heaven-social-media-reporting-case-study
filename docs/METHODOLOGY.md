# Methodology: collection, analysis, reporting

## 1. Collection

| Source type | Example | Frequency | Checks at collection |
|---|---|---|---|
| Platform exports (native tools or API) | posts, reach, views, engagements, followers | daily or weekly, frozen monthly on day 3 | row counts vs last month, missing days, export settings (time zone, attribution window) |
| Ads exports | spend by post | weekly | every boosted post has an id that matches a post |
| Social listening | mentions, comments, hashtags | daily | language detected, duplicates removed, spam filter |
| Creator data | followers history, engagement, audience location | at shortlisting and monthly for active creators | follower history long enough (>= 6 months) |
| Public context | Eurostat, Wikipedia interest, platform changelogs | monthly | source, date and licence written in `data/SOURCES.md` |

This case study only uses public data and simulated data: see `data/SOURCES.md`. With a client, the same pipeline reads
the platform exports instead of `data/simulated/`.

## 2. Analysis

**Quantitative** (SQL in `sql/`, DuckDB):
1. Harmonise (`01_harmonise.sql`): time zones, sponsored flag, one definition of views, deduplication.
2. Monthly KPIs (`02_monthly_kpis.sql`): by market x platform x format, month-on-month change, average of the 3 previous months.
3. Anomalies (`03_anomalies.sql`): robust z-score of each KPI against its own previous 6 months (median and MAD);
   |z| >= 3.5 is flagged, only with enough posts. Plus the data-quality checks of `docs/DATA_QUALITY_CHECKLIST.md`.
4. Creators (`04_creators.sql`): tiers, engagement vs tier, growth, authenticity score.

**Each flag gets a decision** (`src/detect.py`): content issue, data issue, or false signal. Example: engagement per
follower falls after a giveaway, but engagement per reach is flat: the denominator moved, not the content.

**Qualitative**: comments are scored with a rule-based lexicon in 5 languages (no LLM: explainable and repeatable), then
tagged by theme (price, stock, efficacy, texture and shade, ingredients, creator content, service). Themes explain *why*
sentiment moved. The lexicon is checked against a hand-labelled sample every quarter; its accuracy is reported.

**Influencer communities**: mention graph (`networkx`), Louvain communities, PageRank (influence inside the graph),
betweenness (bridges between communities). See `docs/INFLUENCER_ANALYSIS_GUIDE.md`.

## 3. Reporting

| When | What | Who reads it |
|---|---|---|
| Weekly (Monday) | 1 page: alerts (sentiment, stock, crisis), top posts | community managers |
| Monthly (day 5) | client report, 10 slides: 3 messages, KPIs by market, content, formats, communities, attention points, recommendations by market, method | brand and country teams |
| Quarterly | review of KPI definitions, lexicon accuracy, creator roster | client lead and analysts |

**Structure of a monthly message**: what happened (number vs last month and vs 3-month average) -> why (driver: platform,
format, theme, campaign, data issue) -> so what (decision or test).

## 4. What we do not compare

- Engagement rates across platforms with different engagement actions (Facebook has no saves) without saying so.
- Instagram views before and after the definition change, unless rebuilt.
- Organic results of a market whose export mixes sponsored posts, until corrected.
- Engagement per follower across markets with very different follower growth or giveaway history.
- Sentiment levels across languages: only the change within a market is read (each lexicon has its own bias).
- Monthly rates built on fewer than 8 posts.
