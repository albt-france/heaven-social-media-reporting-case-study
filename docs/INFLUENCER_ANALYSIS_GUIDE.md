# Influencer analysis guide

## Creator tiers

| Tier | Followers | Typical role | What to check |
|---|---|---|---|
| Nano | < 10k | trust, local conversation, reviews | real audience in the market, consistency |
| Micro | 10k - 100k | reach with credibility, niche expertise | engagement vs tier, audience location |
| Macro | >= 100k | reach and launches | cost per engagement, audience quality, brand fit |

Engagement per follower falls as audiences grow (simulated medians: about 5.5% nano, 3.4% micro, 1.9% macro), so a
creator is always compared **with the median of its own tier**, never with all creators.

## Audience-quality signals (authenticity score, 0-100)

| Signal | Rule | Penalty | Why |
|---|---|---|---|
| Growth spike | one week > +50% followers, or weekly growth z > 8 vs the creator's own history | -40 | bought, gifted or giveaway followers |
| Low engagement | engagement per follower < 30% of the tier median | -30 | audience does not react |
| Foreign audience | < 40% of the audience in the creator's market | -15 | wrong audience for a local brief |
| No conversation | comments per like < 0.01 | -15 | likes without real exchange |

A score under 50 removes the creator from recommendations until the audience is audited by hand (platform insights
shared by the creator, comment review). The score ranks risk; it does not prove fraud.

## Reading a community graph

- **Node** = a creator; **link** = mentions between two creators (tags, collaborations, replies), weighted by count.
- **Community** (Louvain): a group that mentions itself more than the rest; usually a market x niche (e.g. French make-up).
- **PageRank**: influence inside the graph; a hub is mentioned by creators who are themselves mentioned.
- **Betweenness**: bridges between communities; useful to carry a message from one niche or market to another.
- **Cross-market share**: share of a creator's links outside its market; high values point to pan-European voices.

**How it is used**: one brief per community (its niche and codes), a hub to launch, nano and micro creators of the same
community to repeat the message, and a bridge when a launch must travel across markets.

## Shortlist rule used in this study

Authenticity score >= 85, at least 60% of the audience in the market, nano or micro, ranked by expected engagements per
euro of fee; macro creators are chosen separately, for launches, on cost per engagement.
