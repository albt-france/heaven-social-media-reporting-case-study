-- 03_anomalies.sql  (SIMULATED data)  -  what moved more than usual, and is the data itself trustworthy?
-- Part A: robust z-score of each monthly KPI against its own previous 6 months (median and MAD, so one past spike
--         does not hide the next one). |z| >= 3.5 is flagged (only with >= 8 posts, and >= 40 scored comments for sentiment). A flag is a question, not a conclusion:
--         the detection rules in src/detect.py decide whether it is a content issue, a data issue or a false signal.
-- Part B: data-quality checks run every month before any comparison (docs/DATA_QUALITY_CHECKLIST.md).

CREATE OR REPLACE TABLE kpi_long AS
SELECT month, market, platform, posts, comments_scored, metric, value
FROM (
    SELECT month, market, platform, posts, comments_scored,
           er_reach_org, er_followers_org, follower_growth, net_sentiment,
           views / reach::DOUBLE                     AS views_per_reach,
           views_raw / reach::DOUBLE                 AS views_raw_per_reach
    FROM kpi_month_mp
    UNION ALL BY NAME   -- market level, all platforms together (platform = 'All')
    SELECT month, market, 'All' AS platform, posts, (SELECT SUM(comments_scored) FROM kpi_month_mp k
               WHERE k.month = m.month AND k.market = m.market) AS comments_scored,
           er_reach_org, net_sentiment
    FROM kpi_month_market m
) UNPIVOT (value FOR metric IN (er_reach_org, er_followers_org, follower_growth, net_sentiment,
                                views_per_reach, views_raw_per_reach));

CREATE OR REPLACE TABLE anomalies AS
WITH stats AS (
    SELECT *,
           MEDIAN(value) OVER w                       AS base_median,
           MAD(value)    OVER w                       AS base_mad,
           COUNT(value)  OVER w                       AS n_base
    FROM kpi_long
    WINDOW w AS (PARTITION BY market, platform, metric ORDER BY month ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING)
)
SELECT *, ABS(robust_z) >= 3.5 AS flagged
FROM (
    SELECT month, market, platform, metric, value, base_median, n_base, posts, comments_scored,
           -- dispersion floor: 10% of the median, or an absolute floor (0.4 pt of growth, 4 pts of net sentiment),
           -- so that a very flat history does not turn ordinary noise into a huge z
           (value - base_median) / (1.4826 * GREATEST(base_mad, 0.10 * ABS(base_median),
                CASE metric WHEN 'follower_growth' THEN 0.004 WHEN 'net_sentiment' THEN 4 ELSE 1e-9 END)) AS robust_z
    FROM stats
    WHERE n_base >= 4
      AND posts >= 8                                                   -- too few posts: rate too noisy to flag
      AND (metric <> 'net_sentiment' OR comments_scored >= 40)
) z;

-- Part B1: sponsored posts hidden in organic (paid spend found for posts the social tool calls organic).
CREATE OR REPLACE TABLE dq_sponsored AS
SELECT market,
       COUNT(*) FILTER (WHERE label_mismatch)                       AS organic_label_with_spend,
       COUNT(*) FILTER (WHERE is_sponsored)                         AS sponsored_posts,
       AVG(label_mismatch::INT)                                     AS share_mislabelled
FROM posts_h WHERE in_market_kpis GROUP BY market;

-- Part B2: time zone of the export. Posting policy is the same in every market (08:00-23:00 local);
-- an export in UTC shows posts earlier than any other market, and posts outside the policy window.
CREATE OR REPLACE TABLE dq_timezone AS
SELECT p.market, e.timezone_of_export, e.market_timezone,
       MEDIAN(hour_as_exported)                                     AS median_hour_exported,
       MEDIAN(local_hour)                                           AS median_hour_local,
       AVG((hour_as_exported < 8)::INT)                             AS share_before_8_exported
FROM posts_h p JOIN (SELECT DISTINCT market, timezone_of_export, market_timezone FROM export_settings) e USING (market)
WHERE in_market_kpis GROUP BY ALL;

-- Part B3: duplicates (same native post id in several market exports).
CREATE OR REPLACE TABLE dq_duplicates AS
SELECT platform, COUNT(DISTINCT native_post_id) AS global_posts, COUNT(*) AS rows_in_exports,
       COUNT(*) - COUNT(DISTINCT native_post_id) AS extra_rows,
       SUM(reach) FILTER (WHERE NOT keep_in_group_total) AS reach_counted_twice
FROM posts_h WHERE is_global_crosspost GROUP BY platform;

-- Part B4: definition break. Raw Instagram 'views' per reach before vs after the documented change date.
CREATE OR REPLACE TABLE dq_definition AS
SELECT p.platform,
       c.change_date,
       SUM(views_raw) FILTER (WHERE posted_local::DATE <  c.change_date) / SUM(reach) FILTER (WHERE posted_local::DATE <  c.change_date)::DOUBLE AS raw_views_per_reach_before,
       SUM(views_raw) FILTER (WHERE posted_local::DATE >= c.change_date) / SUM(reach) FILTER (WHERE posted_local::DATE >= c.change_date)::DOUBLE AS raw_views_per_reach_after,
       SUM(views_h)   FILTER (WHERE posted_local::DATE <  c.change_date) / SUM(reach) FILTER (WHERE posted_local::DATE <  c.change_date)::DOUBLE AS harmonised_views_per_reach_before,
       SUM(views_h)   FILTER (WHERE posted_local::DATE >= c.change_date) / SUM(reach) FILTER (WHERE posted_local::DATE >= c.change_date)::DOUBLE AS harmonised_views_per_reach_after,
       AVG((views_raw IS NULL)::INT) FILTER (WHERE posted_local::DATE < c.change_date) AS share_missing_raw_before
FROM posts_h p JOIN definition_changes c USING (platform)
WHERE in_market_kpis GROUP BY ALL;
