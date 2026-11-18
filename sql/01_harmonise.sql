-- 01_harmonise.sql  (SIMULATED data)  -  one KPI, one meaning, in every market and on every platform.
-- Input tables (loaded by src/run_sql.py from data/simulated/): posts, ads_spend, export_settings, accounts_daily.
-- Output: metric_map (dictionary), definition_changes, posts_h (one clean row per post, ready for KPIs).
-- Four corrections are applied, in this order:
--   1. time zones   : every export string is read in the time zone the tool used, then converted to market local time;
--   2. sponsored    : a post is sponsored if the social tool says so OR the ads manager shows spend for it;
--   3. definitions  : 'views' is mapped to one harmonised definition (every display), using the platform changelog;
--   4. duplicates   : a global post shown in several market exports is counted once in group totals.

-- Dictionary: native metric of each platform -> harmonised metric (documented in docs/KPI_FRAMEWORK.md).
CREATE OR REPLACE TABLE metric_map AS
SELECT * FROM (VALUES
    ('Instagram', 'reach',               'reach',       'Unique accounts that saw the content'),
    ('Instagram', 'impressions',         'views',       'All displays; available until the definition change'),
    ('Instagram', 'views (old)',         'video_plays', 'Before the change: video plays only -> NOT used as views'),
    ('Instagram', 'views (new)',         'views',       'After the change: every display of every format'),
    ('Instagram', 'likes/comments/shares/saves', 'engagements', 'Sum of the four interactions'),
    ('TikTok',    'video views',         'views',       'Plays started (organic + paid in the account export)'),
    ('TikTok',    'likes/comments/shares/favorites', 'engagements', 'favorites = saves'),
    ('Facebook',  'views',               'views',       'All displays (Meta views metric)'),
    ('Facebook',  'reactions/comments/shares', 'engagements', 'reactions = likes; no saves'),
    ('X',         'impressions',         'views',       'All displays'),
    ('X',         'likes/replies/reposts/bookmarks', 'engagements', 'replies = comments, reposts = shares, bookmarks = saves'),
    ('YouTube',   'views',               'views',       'Counted views (YouTube rules)'),
    ('YouTube',   'likes/comments',      'engagements', 'no shares or saves in the export')
) AS t(platform, native_metric, harmonised_metric, note);

-- Definition changes known from the platforms' developer changelogs (here: SIMULATED date).
-- 03_anomalies.sql checks that the data show a break on that date before the rule is trusted.
CREATE OR REPLACE TABLE definition_changes AS
SELECT 'Instagram' AS platform, 'views' AS metric, DATE '2026-02-01' AS change_date,
       'views now counts every display of every format (was: video plays only)' AS what;

CREATE OR REPLACE TABLE posts_h AS
WITH timed AS (
    SELECT p.*,
           e.timezone_of_export,
           e.market_timezone,
           CAST(p.posted_at AS TIMESTAMP)                                     AS ts_export,      -- naive string as exported
           timezone(e.timezone_of_export, CAST(p.posted_at AS TIMESTAMP))      AS ts_instant      -- true instant (timestamptz)
    FROM posts p
    JOIN export_settings e USING (market, platform)
),
localised AS (
    SELECT *,
           timezone('UTC', ts_instant)              AS posted_utc,
           timezone(market_timezone, ts_instant)    AS posted_local
    FROM timed
),
dups AS (   -- same native id in several market exports = one global post shown everywhere
    SELECT native_post_id, COUNT(DISTINCT market) AS n_markets
    FROM posts GROUP BY native_post_id
),
enriched AS (
    SELECT l.*,
           COALESCE(a.spend_eur, 0)                                          AS spend_eur,
           (l.paid_label = 'sponsored' OR COALESCE(a.spend_eur, 0) > 0)      AS is_sponsored,
           (l.paid_label = 'organic'   AND COALESCE(a.spend_eur, 0) > 0)     AS label_mismatch,
           d.n_markets > 1                                                   AS is_global_crosspost,
           ROW_NUMBER() OVER (PARTITION BY l.native_post_id ORDER BY l.market) = 1 AS keep_in_group_total
    FROM localised l
    LEFT JOIN ads_spend a USING (post_id)
    JOIN dups d USING (native_post_id)
)
SELECT e.post_id, e.native_post_id, e.market, e.platform, e.format, e.theme, e.campaign_id,
       e.paid_label, e.is_sponsored, e.label_mismatch, e.spend_eur,
       e.is_global_crosspost, e.keep_in_group_total,
       NOT e.is_global_crosspost                                    AS in_market_kpis,
       e.ts_export, e.posted_utc, e.posted_local,
       HOUR(e.ts_export)                                            AS hour_as_exported,   -- what a naive analysis uses
       HOUR(e.posted_local)                                         AS local_hour,
       DATE_TRUNC('month', e.posted_local)::DATE                    AS month,
       e.reach,
       e.views                                                      AS views_raw,
       -- harmonised views = every display of every format
       CASE WHEN e.platform = 'Instagram' AND e.posted_local::DATE < c.change_date THEN e.impressions
            WHEN e.platform = 'X' THEN e.impressions
            ELSE e.views END                                        AS views_h,
       e.likes, e.comments, e.shares, e.saves,
       e.likes + e.comments + e.shares + e.saves                    AS engagements,
       (e.likes + e.comments + e.shares + e.saves) / e.reach::DOUBLE AS er_reach,
       f.followers,
       (e.likes + e.comments + e.shares + e.saves) / NULLIF(f.followers, 0)::DOUBLE AS er_followers
FROM enriched e
LEFT JOIN definition_changes c ON c.platform = e.platform AND c.metric = 'views'
LEFT JOIN accounts_daily f
       ON f.market = e.market AND f.platform = e.platform AND f.date = e.posted_local::DATE;
