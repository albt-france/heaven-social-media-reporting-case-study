# Simulation assumptions (SIMULATED data)

The simulated account is **a fictitious global beauty retailer** on 5 markets (France, United Kingdom, Germany, Spain,
Italy) and 5 platforms (Instagram, TikTok, Facebook, X, YouTube), from 1 June 2025 to 31 October 2026, seed 42.
It exists to run the reporting mission end to end; it says nothing about any real company.

## Calibration

| Item | Assumption | Basis |
|---|---|---|
| Followers by market | 420k on Instagram in the home market, scaled by platform size, brand presence and **Eurostat social-network use** (FR 70.8%, DE 59.2%, ES 69.5%, IT 56.4% in 2025; UK 75.7% in 2020) | Eurostat (PUBLIC DATA) + presence assumption FR 1.00, UK 0.85, ES 0.75, IT 0.70, DE 0.65 |
| Platform size | Instagram 1.0, TikTok 0.75, Facebook 0.6, X 0.2, YouTube 0.15 (relative to Instagram) | assumption |
| Monthly follower growth | TikTok 2.5%, Instagram 1.2%, YouTube 0.8%, Facebook 0.2%, X -0.3% | assumption |
| Posts per account and month | Instagram 22, X 20, TikTok 18, Facebook 12, YouTube 4 (Poisson) | assumption |
| Reach per post | followers x reach rate by platform and format (e.g. Instagram short video 35%, TikTok short video 60% with a heavy tail) | assumption |
| Engagement per reach | 1.2% (X image) to 9% (TikTok live), times theme, hour and market-format effects | assumption |
| Sponsored posts | 12% of posts (30% during campaigns); paid reach x2.5-4, engagement per reach x0.6, CPM EUR 6-9 | assumption |
| Comments | about 3 sampled comments per post, synthetic texts in 5 languages from short templates, 7% "hard" phrases (negations, irony) to show the lexicon's limits | synthetic |
| Creators | 500 anonymous creators: nano (55%), micro (35%), macro (10%); engagement per follower 5.5% / 3.4% / 1.9% at the median | assumption |
| Mentions | each creator mentions about 8 creators a month (70% same market and niche, 20% same market, 10% elsewhere) and about 5 brands | assumption |

## Situations hidden in the data (the review must find them)

1. Instagram `views` changes definition on 1 Feb 2026 (video plays only before, every display after), modelled on Meta's 2025 change.
2. In one market, sponsored posts are exported as organic (the spend is only in the ads export).
3. One market's export is in UTC instead of local time.
4. A giveaway in one market adds followers who do not engage: engagement per follower falls, engagement per reach does not.
5. One creator gains followers abruptly while engagement stays very low.
6. A hero product is out of stock in one market for three weeks: negative comments rise.
7. Short video works better in some markets, carousel in another.
8. Global posts appear in every market export and are counted several times in group totals.

The answer key (`data/_hidden_truth.csv`) is used locally to score the detection and is not published;
`src/simulate.py` keeps the parameters in plain sight.
