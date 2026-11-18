"""Write and execute the single analysis notebook: notebooks/social_analysis.ipynb.

Usage: python src/build_notebook.py   (after src/run_sql.py)
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "social_analysis.ipynb"

CELLS = [
    ("md", """# heaven: comparable social media reporting across markets

Independent case study based on public data · not affiliated with or endorsed by heaven or Hopscotch Groupe.

**Part 1 - PUBLIC DATA**: beauty brands' interest by language (Wikipedia), social-network use by country (Eurostat),
a small real social-listening sample (Mastodon), official brand accounts on Bluesky.
**Part 2 - SIMULATED**: a fictitious multi-market beauty retailer, 5 markets x 5 platforms: harmonised KPIs, the 8 hidden
situations and how they are found, sentiment and themes, influencer communities, recommendations by market.

Every table below is read from `data/public/` or `data/processed/` (built by `src/fetch_public.py`, `src/simulate.py`
and `src/run_sql.py`)."""),
    ("code", """import json, sys
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
PUB, PROC = ROOT / "data" / "public", ROOT / "data" / "processed"
F = json.loads((PROC / "facts.json").read_text(encoding="utf-8"))
plt.rcParams.update({"figure.figsize": (9, 3.6), "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
PLUM = "#6B2D5C"; print("collected on", F["collected_on"])"""),
    ("md", "## Part 1 - PUBLIC DATA\n### 1.1 Social-network use by country (Eurostat `isoc_ci_ac_i`, `I_IUSNET`)"),
    ("code", """e = pd.read_csv(PUB / "eurostat_social_use.csv")
last = e.sort_values("year").groupby("geo").last().sort_values("pct_individuals")
ax = last.pct_individuals.plot.barh(color=PLUM); ax.set_xlabel("% of individuals using social networks (latest year)")
for i, (g, r) in enumerate(last.iterrows()): ax.text(r.pct_individuals + .5, i, f"{r.pct_individuals:.1f}% ({int(r.year)})", va="center")
plt.show()"""),
    ("md", "The UK has no Eurostat figure after 2020 (last year it is covered); it is shown but not compared with 2025 values."),
    ("md", "### 1.2 Interest by language (Wikipedia page views per million views of each edition)"),
    ("code", """w = pd.read_csv(PUB / "wikipedia_pageviews.csv")
full = w.groupby(["kind", "entity"]).lang.nunique(); keep = full[full == 5].index
w5 = w[w.set_index(["kind", "entity"]).index.isin(keep)]
brand = w5[w5.kind == "brand"].pivot_table(index="entity", columns="lang", values="per_million", aggfunc="mean").round(2)
print("brands present in all 5 editions:", len(brand)); brand"""),
    ("code", """t = w5[w5.kind == "topic"].pivot_table(index="month", columns=["entity", "lang"], values="per_million", aggfunc="sum")
ax = t["Sunscreen"].plot(title="Sunscreen: page views per million, by language edition"); ax.set_xlabel(""); plt.show()"""),
    ("md", """Reading: interest is seasonal (sunscreen peaks in summer in every language) and brand interest differs by language,
so one European average would hide market differences. Limits: the English edition is global, not a UK measure;
page views measure curiosity, not purchases."""),
    ("md", "### 1.3 Mini social listening on Mastodon (public hashtag timelines)"),
    ("code", """m = pd.read_csv(PUB / "mastodon_sample.csv")
m12 = m[m.date >= str(pd.Timestamp(F["collected_on"]) - pd.DateOffset(months=12))[:10]]
print(f"{len(m)} posts collected, {len(m12)} in the last 12 months, {m.tag.nunique()} hashtags")
th = [c for c in m12.columns if c.startswith("theme_")]
summary = pd.DataFrame({"posts": m12.groupby("tag").size(), "median interactions": m12.assign(i=m12.favourites + m12.reblogs + m12.replies).groupby("tag").i.median()})
display(summary.sort_values("posts", ascending=False))
m12[th].mean().sort_values().rename(lambda c: c.replace("theme_", "")).plot.barh(color=PLUM, title="Share of posts by theme (lexicon rules)"); plt.show()"""),
    ("md", """Volumes are small and the platform's audience is not representative of beauty consumers; this sample only shows that
the listening pipeline (collection, language, themes, sentiment) runs on real public posts. No text or account is kept."""),
    ("md", "### 1.4 Official brand accounts on Bluesky (handle = brand domain, verified by DNS)"),
    ("code", """b = pd.read_csv(PUB / "bluesky_accounts.csv"); b[["entity", "handle", "on_bluesky"] + [c for c in ["followers", "posts_total"] if c in b]]"""),
    ("code", """yt = PUB / "youtube_brand_videos.csv"
print("YouTube panel available" if yt.exists() else "No YouTube API key: YouTube panel not collected (fallback: Wikipedia, Mastodon, Bluesky).")"""),
    ("md", "## Part 2 - SIMULATED account\n### 2.1 Data quality first: what the harmonisation corrects"),
    ("code", """for t in ["dq_definition", "dq_sponsored", "dq_timezone", "dq_duplicates"]:
    print(t); display(pd.read_csv(PROC / f"{t}.csv").round(3))"""),
    ("code", """k = pd.read_csv(PROC / "kpi_month_mp.csv"); ig = k[k.platform == "Instagram"].groupby("month")[["views_raw", "views", "reach"]].sum()
ax = (ig.views_raw / ig.reach).plot(label="raw 'views' / reach (as exported)", color="#B02E2E")
(ig.views / ig.reach).plot(ax=ax, label="harmonised views / reach", color=PLUM); ax.legend(); ax.set_title("Instagram: definition change"); plt.show()"""),
    ("md", "### 2.2 Monthly KPIs by market (harmonised, organic engagement)"),
    ("code", """km = pd.read_csv(PROC / "kpi_month_market.csv")
p = km.pivot(index="month", columns="market", values="er_reach_org") * 100
ax = p.plot(title="Engagement rate by reach, organic posts (%)"); ax.set_xlabel(""); plt.show()
km[km.month == "2026-10-01"].set_index("market")[["reach", "engagements", "er_reach_org", "net_sentiment", "followers_end"]].round(3)"""),
    ("md", "### 2.3 The 8 hidden situations: detection and decision"),
    ("code", """det = pd.read_csv(PROC / "detection.csv"); display(det[["event_id", "event", "detected", "where", "evidence", "decision"]])
truth = PROC / "detection_vs_truth.csv"
if truth.exists():
    s = pd.read_csv(truth); print(f"Detection rate against the hidden answer key: {s.found.sum()}/{len(s)}")"""),
    ("code", """a = pd.read_csv(PROC / "anomalies.csv")
print(f"{a.flagged.sum()} flags out of {len(a)} KPI-months screened (robust z, |z| >= 3.5)")
a[a.flagged].groupby("metric").size()"""),
    ("md", """**The false signal (Spain)**: engagement per follower falls after the giveaway, engagement per reach does not: the
denominator moved (followers who do not engage), not the content. The rule therefore does **not** raise a content issue."""),
    ("code", """es = k[(k.market == "ES") & (k.platform == "Instagram")].set_index("month")
ax = (es[["er_followers_org", "er_reach_org"]] / es[["er_followers_org", "er_reach_org"]].iloc[:6].median()).plot(
    title="Spain, Instagram: ER per follower vs ER per reach (index, first 6 months = 1)")
ax.axvline(list(es.index).index("2026-03-01"), color="grey", ls=":"); plt.show()"""),
    ("md", "### 2.4 Formats by market"),
    ("code", """pd.read_csv(PROC / "format_by_market.csv")"""),
    ("md", """### 2.5 Sentiment and themes (lexicon in FR / EN / DE / ES / IT, no LLM)

Method: positive and negative word lists per language, a negation flips the next 2 words, a few emojis;
score = (pos - neg) / (pos + neg). Themes are keyword rules. Limits: no irony, short lists, and the agreement below is
measured on **synthetic** comments built from templates, so it is optimistic: real comments need a hand-labelled sample."""),
    ("code", """c = pd.read_csv(PROC / "comments_scored.csv")
print(f"agreement with labels: {(c.label == c.label_true).mean():.0%}")
display(pd.crosstab(c.label_true, c.label, normalize="index").round(2))
c.groupby("lang").apply(lambda x: (x.label == x.label_true).mean(), include_groups=False).round(3)"""),
    ("code", """c["month"] = c.date.str[:7]
fr = c[c.market == "FR"].groupby("month").apply(lambda x: 100 * ((x.label == "positive").mean() - (x.label == "negative").mean()), include_groups=False)
ax = fr.plot(title="France: net sentiment by month", color=PLUM); plt.show()
neg = c[(c.market == "FR") & (c.label == "negative")]
neg.groupby("month")[[x for x in c.columns if x.startswith("theme_")]].mean().tail(4).round(2)"""),
    ("md", "### 2.6 Influencer communities (mention graph, Louvain, PageRank, betweenness)"),
    ("code", """net = pd.read_csv(PROC / "creator_network.csv"); comm = pd.read_csv(PROC / "communities.csv")
fig, ax = plt.subplots(figsize=(8, 6))
cols = {"FR": "#6B2D5C", "UK": "#1C5CAB", "DE": "#B88A4E", "ES": "#1E7A52", "IT": "#B02E2E"}
for mk, g in net.groupby("market"):
    ax.scatter(g.x, g.y, s=8 + 400 * g.pagerank / net.pagerank.max(), c=cols[mk], alpha=.7, label=mk)
sus = net[net.authenticity_score < 50]; ax.scatter(sus.x, sus.y, s=120, facecolors="none", edgecolors="black", label="excluded")
ax.legend(); ax.set_axis_off(); ax.set_title("Creators coloured by market, size = PageRank"); plt.show()
comm"""),
    ("code", """pd.read_csv(PROC / "market_profiles.csv")"""),
    ("code", """cs = pd.read_csv(PROC / "creator_scores.csv")
display(cs.sort_values("authenticity_score").head(3)[["creator_id", "market", "tier", "max_weekly_growth", "er_followers", "tier_median_er", "audience_own_market", "comments_per_like", "authenticity_score"]])
pd.read_csv(PROC / "creator_shortlist.csv")"""),
    ("md", """### 2.7 Recommendations by market (October 2026)

| Market | Lever | Test next | KPI to watch |
|---|---|---|---|
| France | answer stock questions with a restock date; more short video on Instagram | tutorial short videos with nano make-up creators | net sentiment back to usual |
| United Kingdom | keep the format mix; seed the skincare community (low share of voice) | micro skincare creators | share of voice |
| Germany | carousel first on Instagram; publish in the evening, local time | educational carousels | engagement rate by reach |
| Spain | report engagement by reach, not by followers, after the giveaway | re-engagement of giveaway followers | ER by reach, churn |
| Italy | fix the sponsored flag at source; reduce the paid share | lower paid share for two weeks | organic reach rate, cost per engagement |

What we cannot conclude: sentiment *levels* across languages, and any format effect before a test confirms it."""),
]


def main():
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in CELLS]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NB.parent.mkdir(exist_ok=True)
    ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(NB.parent)}})
    nbf.write(nb, NB)
    print(f"notebook executed: {NB.relative_to(ROOT)} ({len(nb.cells)} cells)")


if __name__ == "__main__":
    main()
