-- 02_monthly_kpis.sql  (SIMULATED data)  -  monthly KPIs by market x platform (x format), with month-on-month
-- change and the average of the 3 previous months. Global cross-posts are excluded from market KPIs and counted
-- once in the group total. Engagement rates are computed on ORGANIC posts only, so paid reach does not inflate them.
--   er_reach     = SUM(engagements) / SUM(reach)                     (weighted: big posts weigh more)
--   er_followers = AVG(engagements / followers at the post date)     (per post, then averaged)

CREATE OR REPLACE TABLE kpi_month_mpf AS
SELECT month, market, platform, format,
       COUNT(*)                                                             AS posts,
       SUM(reach)                                                           AS reach,
       SUM(views_h)                                                         AS views,
       SUM(engagements)                                                     AS engagements,
       SUM(engagements) FILTER (WHERE NOT is_sponsored) / NULLIF(SUM(reach) FILTER (WHERE NOT is_sponsored), 0)::DOUBLE AS er_reach_org,
       AVG(er_followers) FILTER (WHERE NOT is_sponsored)                    AS er_followers_org
FROM posts_h
WHERE in_market_kpis
GROUP BY ALL;

CREATE OR REPLACE TABLE kpi_month_mp AS
WITH base AS (
    SELECT month, market, platform,
           COUNT(*)                                                         AS posts,
           COUNT(*) FILTER (WHERE is_sponsored)                             AS sponsored_posts,
           SUM(spend_eur)                                                   AS spend_eur,
           SUM(reach)                                                       AS reach,
           SUM(views_h)                                                     AS views,
           SUM(views_raw)                                                   AS views_raw,
           SUM(engagements)                                                 AS engagements,
           SUM(engagements) FILTER (WHERE is_sponsored)                     AS engagements_paid,
           SUM(engagements) FILTER (WHERE NOT is_sponsored) / NULLIF(SUM(reach) FILTER (WHERE NOT is_sponsored), 0)::DOUBLE AS er_reach_org,
           AVG(er_followers) FILTER (WHERE NOT is_sponsored)                AS er_followers_org,
           -- the naive version: trusts the export label, so mislabelled paid posts count as organic
           SUM(engagements) FILTER (WHERE paid_label = 'organic') / NULLIF(SUM(reach) FILTER (WHERE paid_label = 'organic'), 0)::DOUBLE AS er_reach_org_naive,
           SUM(reach) FILTER (WHERE paid_label = 'organic') / NULLIF(COUNT(*) FILTER (WHERE paid_label = 'organic'), 0)::DOUBLE AS reach_per_org_post_naive,
           SUM(reach) FILTER (WHERE NOT is_sponsored) / NULLIF(COUNT(*) FILTER (WHERE NOT is_sponsored), 0)::DOUBLE AS reach_per_org_post
    FROM posts_h
    WHERE in_market_kpis
    GROUP BY ALL
),
fol AS (   -- followers at month end and growth over the month
    SELECT DATE_TRUNC('month', date)::DATE AS month, market, platform,
           ARG_MAX(followers, date) AS followers_end, ARG_MIN(followers, date) AS followers_start
    FROM accounts_daily GROUP BY ALL
),
sent AS (  -- net sentiment = % positive - % negative comments (lexicon labels from src/sentiment.py)
    SELECT DATE_TRUNC('month', CAST(date AS DATE))::DATE AS month, market, platform,
           COUNT(*) AS comments_scored,
           100.0 * (AVG((label = 'positive')::INT) - AVG((label = 'negative')::INT)) AS net_sentiment
    FROM comments_scored GROUP BY ALL
)
SELECT b.*, f.followers_end,
       f.followers_end / f.followers_start::DOUBLE - 1                       AS follower_growth,
       b.spend_eur / NULLIF(b.engagements_paid, 0)                          AS cost_per_engagement,
       s.net_sentiment, s.comments_scored,
       -- month-on-month change and 3-previous-month average (window functions per market x platform)
       b.er_reach_org / LAG(b.er_reach_org) OVER w - 1                       AS er_reach_mom,
       AVG(b.er_reach_org) OVER (w ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS er_reach_prev3,
       b.reach / LAG(b.reach) OVER w::DOUBLE - 1                             AS reach_mom,
       AVG(b.reach) OVER (w ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)        AS reach_prev3
FROM base b
JOIN fol f USING (month, market, platform)
LEFT JOIN sent s USING (month, market, platform)
WINDOW w AS (PARTITION BY b.market, b.platform ORDER BY b.month);

-- Market level (all platforms), the view a country manager reads first.
CREATE OR REPLACE TABLE kpi_month_market AS
SELECT month, market,
       SUM(posts) AS posts, SUM(reach) AS reach, SUM(views) AS views, SUM(engagements) AS engagements,
       SUM(spend_eur) AS spend_eur, SUM(followers_end) AS followers_end,
       SUM(er_reach_org * reach) / SUM(reach) AS er_reach_org,   -- reach-weighted across platforms
       SUM(net_sentiment * comments_scored) / SUM(comments_scored) AS net_sentiment
FROM kpi_month_mp GROUP BY ALL;

-- Share of voice among creators: mentions of our account / all brand mentions, by market and month.
CREATE OR REPLACE TABLE share_of_voice AS
SELECT m.month, c.market,
       SUM(m.n) FILTER (WHERE m.target = 'our_account') / SUM(m.n)::DOUBLE AS share_of_voice,
       SUM(m.n) AS brand_mentions
FROM mentions m JOIN creators c ON c.creator_id = m.source
WHERE m.target_type = 'brand'
GROUP BY ALL;

-- Group totals: naive (sum of the 5 market exports) vs deduplicated (each native post once).
CREATE OR REPLACE TABLE group_totals AS
SELECT month,
       SUM(reach)                                            AS reach_naive,
       SUM(reach) FILTER (WHERE keep_in_group_total)         AS reach_dedup,
       SUM(engagements)                                      AS engagements_naive,
       SUM(engagements) FILTER (WHERE keep_in_group_total)   AS engagements_dedup,
       COUNT(*)                                              AS posts_naive,
       COUNT(*) FILTER (WHERE keep_in_group_total)           AS posts_dedup
FROM posts_h GROUP BY month;
