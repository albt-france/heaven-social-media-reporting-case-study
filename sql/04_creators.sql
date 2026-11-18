-- 04_creators.sql  (SIMULATED data)  -  creator tiers, engagement, growth and audience-authenticity signals.
-- Creators are anonymous ids (creator_001...). Tiers by followers: nano < 10k, micro 10k-100k, macro >= 100k.
-- Authenticity score (0-100, start at 100, explained in docs/INFLUENCER_ANALYSIS_GUIDE.md):
--   -40 if one week shows a follower jump > 50% (or a weekly-growth robust z > 8)  -> bought or gifted followers?
--   -30 if engagement per follower < 30% of the tier median                        -> audience does not react
--   -15 if less than 40% of the audience is in the creator's own market           -> wrong audience for a local brief
--   -15 if comments per like < 0.01                                                -> likes without conversation
-- Score < 50: excluded from recommendations until checked by hand.

CREATE OR REPLACE TABLE creator_growth AS
WITH w AS (
    SELECT creator_id, CAST(week AS DATE) AS week, followers,
           followers / LAG(followers) OVER (PARTITION BY creator_id ORDER BY week)::DOUBLE - 1 AS weekly_growth
    FROM creators_weekly
),
s AS (
    SELECT creator_id,
           MEDIAN(weekly_growth) AS med_growth,
           MAD(weekly_growth)    AS mad_growth,
           MAX(weekly_growth)    AS max_weekly_growth,
           ARG_MAX(week, weekly_growth) AS week_of_max,
           LAST(followers ORDER BY week) / FIRST(followers ORDER BY week)::DOUBLE - 1 AS growth_period
    FROM w GROUP BY creator_id
)
SELECT *, (max_weekly_growth - med_growth) / (1.4826 * GREATEST(mad_growth, 1e-4)) AS max_growth_z
FROM s;

CREATE OR REPLACE TABLE creator_scores AS
WITH tier_med AS (
    SELECT tier, MEDIAN(er_followers) AS tier_median_er FROM creators GROUP BY tier
),
brand AS (
    SELECT source AS creator_id,
           SUM(n) FILTER (WHERE target = 'our_account') AS mentions_our_account,
           SUM(n) AS brand_mentions
    FROM mentions WHERE target_type = 'brand' GROUP BY source
)
SELECT c.*, g.max_weekly_growth, g.week_of_max, g.max_growth_z, g.growth_period,
       t.tier_median_er, c.er_followers / t.tier_median_er AS er_vs_tier,
       COALESCE(b.mentions_our_account, 0) AS mentions_our_account,
       COALESCE(b.brand_mentions, 0)       AS brand_mentions,
       (g.max_weekly_growth > 0.5 OR g.max_growth_z > 8) AS sig_growth_spike,
       c.er_followers / t.tier_median_er < 0.3           AS sig_low_engagement,
       c.audience_own_market < 0.4                       AS sig_foreign_audience,
       c.comments_per_like < 0.01                        AS sig_no_conversation,
       100 - 40 * (g.max_weekly_growth > 0.5 OR g.max_growth_z > 8)::INT
           - 30 * (c.er_followers / t.tier_median_er < 0.3)::INT
           - 15 * (c.audience_own_market < 0.4)::INT
           - 15 * (c.comments_per_like < 0.01)::INT     AS authenticity_score,
       -- expected engagements per euro of fee, for comparable shortlists within a tier
       c.followers * c.er_followers / NULLIF(c.est_fee_eur, 0) AS engagements_per_eur
FROM creators c
JOIN creator_growth g USING (creator_id)
JOIN tier_med t USING (tier)
LEFT JOIN brand b USING (creator_id);
