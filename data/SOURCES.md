# Data sources

Collected on **17 November 2026** with a neutral User-Agent (`social-case-study/1.0`), at most one request every 1.5 s,
`robots.txt` checked for web pages, official documented APIs only. No scraping of Instagram, TikTok, Facebook or X
(their terms forbid it and they require a login). No third-party influencer statistics tool.
Raw responses stay in `data/raw/` (not published); `data/public/` holds aggregates only (no post text, no personal account id).

## PUBLIC DATA

| # | Source | What is used | Access | Licence / terms |
|---|---|---|---|---|
| 1 | Hopscotch Groupe, investor relations: <https://hopscotch.one/en/investors-relations/> | H1 2026 results press release (30 Sep 2026), 2025 annual results press release (Mar 2026), H1 2026 activity release (Jul 2026), H1 2026 results presentation (Oct 2026) | public PDFs, `robots.txt` open | facts quoted "as stated by Hopscotch Groupe" |
| 2 | heaven: <https://heaven.paris/we-are/>, `/social-media/`, `/influence/`, `/heaven-consulting-data-insights/`, `/legal/` | services, size, clients the agency names itself | public pages, `robots.txt` open | facts quoted "as stated by heaven". The legal page gives no company registration number and the register lists several "HEAVEN" companies in Paris, so **no registry figure is quoted** for the agency. |
| 3 | Job posting "Data Analyst - Freelance" on Welcome to the Jungle | mission, profile, clients named in the posting | read in a browser on 17 Nov 2026 (automated access refused: HTTP 403, not bypassed) | quoted "as stated in the job posting" |
| 4 | Wikimedia Pageviews API: <https://wikimedia.org/api/rest_v1/metrics/pageviews/> | monthly user page views, June 2025 - October 2026, of 10 beauty product brands and 5 beauty topics in the fr, en, de, es, it editions; each article found through the English article's interlanguage links; normalised per million views of the whole edition | no key | data CC0; Wikimedia API terms |
| 5 | Eurostat `isoc_ci_ac_i`, indicator `I_IUSNET` (participating in social networks), unit `PC_IND`, all individuals: <https://ec.europa.eu/eurostat/databrowser/view/isoc_ci_ac_i/default/table> | share of individuals using social networks, FR, DE, ES, IT (2025) and UK (2020, last year the UK is covered) | JSON API, no key | Eurostat reuse policy (CC BY 4.0) |
| 6 | Mastodon, mastodon.social public hashtag timelines `/api/v1/timelines/tag/<tag>` | 9 beauty hashtags (#skincare, #makeup, #beauty, #beauté, #maquillage, #skincareroutine, #hautpflege, #maquillaje, #trucco), up to 200 posts each; only counts, dates, languages, interactions and lexicon tags are kept | public API, no account | posts belong to their authors: no text and no account is republished |
| 7 | Bluesky public AppView `public.api.bsky.app` (`resolveHandle`, `getProfile`, `getAuthorFeed`) | does each panel brand use its own domain as a Bluesky handle (ownership proven by DNS)? plus the Hopscotch Groupe account named in its press releases | public API, no account; post search needs a login and is **not** used | aggregates only |
| 8 | Meta for Developers, Instagram Platform changelog and Graph API v22.0 changelog: <https://developers.facebook.com/docs/graph-api/changelog/version22.0/>, <https://developers.facebook.com/documentation/instagram-platform/changelog> | the real case behind the comparability problem: a `views` metric introduced for media and account insights; `plays`, `clips_replays_count`, `ig_reels_aggregated_all_plays_count` and `impressions` deprecated from v22.0 (all versions from 21 April 2025) | public documentation | cited, not copied |
| 9 | TikTok API for Business documentation (v1.3): <https://business-api.tiktok.com/portal/docs/get-post-data-of-a-tiktok-account/v1.3> | account `video_views` counts organic and paid activity together, and the same field name is labelled differently across reports | public documentation | cited, not copied |
| 10 | YouTube Data API v3 (optional, `src/fetch_youtube.py`) | brand channels and creator videos | free API key | **not run for this version** (no key): the brand panel relies on sources 4, 6 and 7 |

## SIMULATED

`data/simulated/` is produced by `src/simulate.py` (seed 42) for a fictitious account, "a global beauty retailer".
It is not data from any real brand, from heaven, from Hopscotch Groupe or from any of their clients.
Assumptions: `data/ASSUMPTIONS.md`.
