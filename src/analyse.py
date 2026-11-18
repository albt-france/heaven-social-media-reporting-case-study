"""Analysis layer: detection results, influencer communities, public-data summaries and the fact sheet.

Usage: python src/analyse.py   (run after src/run_sql.py; run_sql.py calls it at the end)
Outputs (data/processed/): detection.csv, communities.csv, creator_network.csv, market_profiles.csv,
creator_shortlist.csv, format_by_market.csv, facts.json (every number quoted in the monthly report and the PDF).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, PUB = ROOT / "data" / "processed", ROOT / "data" / "public"
REPORT_MONTH = "2026-10-01"
MKT = {"FR": "France", "UK": "United Kingdom", "DE": "Germany", "ES": "Spain", "IT": "Italy"}


def communities() -> tuple[pd.DataFrame, pd.DataFrame, nx.Graph]:
    men, cs = pd.read_csv(ROOT / "data" / "simulated" / "mentions.csv"), pd.read_csv(PROC / "creator_scores.csv").sort_values("creator_id")
    cc = men[men.target_type == "creator"].groupby(["source", "target"], as_index=False).n.sum().sort_values(["source", "target"])
    G = nx.Graph()
    G.add_nodes_from(cs.creator_id)
    for r in cc.itertuples():
        w = G[r.source][r.target]["weight"] + r.n if G.has_edge(r.source, r.target) else r.n
        G.add_edge(r.source, r.target, weight=w)
    comms = nx.community.louvain_communities(G, weight="weight", seed=42, resolution=1.0)
    comm_of = {n: i for i, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}
    pr = nx.pagerank(G, weight="weight")
    bt = nx.betweenness_centrality(G, k=200, seed=42)
    pos = nx.spring_layout(G, seed=42, weight="weight", iterations=80)
    nodes = cs.set_index("creator_id")
    net = pd.DataFrame(dict(creator_id=list(G.nodes)))
    net["community"] = net.creator_id.map(comm_of)
    net["pagerank"] = net.creator_id.map(pr)
    net["betweenness"] = net.creator_id.map(bt)
    net["degree"] = net.creator_id.map(dict(G.degree()))
    net["x"], net["y"] = net.creator_id.map(lambda n: pos[n][0]), net.creator_id.map(lambda n: pos[n][1])
    net = net.join(nodes[["market", "tier", "niche", "platform", "followers", "er_followers", "authenticity_score",
                          "mentions_our_account"]], on="creator_id")
    # bridges: creators whose neighbours sit in other markets
    other = {n: np.mean([nodes.loc[v, "market"] != nodes.loc[n, "market"] for v in G[n]]) if G.degree(n) else 0 for n in G}
    net["cross_market_share"] = net.creator_id.map(other)
    rows = []
    for c, g in net.groupby("community"):
        top_m = g.market.value_counts()
        top_n = g.niche.value_counts()
        rows.append(dict(community=c, size=len(g), main_market=top_m.index[0], main_market_share=round(top_m.iloc[0] / len(g), 2),
                         main_niche=top_n.index[0], main_niche_share=round(top_n.iloc[0] / len(g), 2),
                         median_er=round(g.er_followers.median(), 4), macro_share=round((g.tier == "macro").mean(), 2),
                         mention_our_account_share=round((g.mentions_our_account > 0).mean(), 2),
                         hub=g.sort_values("pagerank").creator_id.iloc[-1]))
    return pd.DataFrame(rows), net, G


def market_profiles(net: pd.DataFrame, comm: pd.DataFrame) -> pd.DataFrame:
    sov = pd.read_csv(PROC / "share_of_voice.csv")
    sov = sov[sov.month >= "2026-08"].groupby("market").apply(
        lambda x: (x.share_of_voice * x.brand_mentions).sum() / x.brand_mentions.sum(), include_groups=False)
    rows = []
    for m, g in net.groupby("market"):
        main = comm[comm.main_market == m]
        rows.append(dict(market=m, creators=len(g), nano_share=round((g.tier == "nano").mean(), 2),
                         micro_share=round((g.tier == "micro").mean(), 2), macro_share=round((g.tier == "macro").mean(), 2),
                         median_er_nano=round(g[g.tier == "nano"].er_followers.median(), 4),
                         median_er_micro=round(g[g.tier == "micro"].er_followers.median(), 4),
                         median_er_macro=round(g[g.tier == "macro"].er_followers.median(), 4),
                         top_niche=g.niche.value_counts().index[0], communities=len(main),
                         cross_market_share=round(g.cross_market_share.mean(), 3),
                         share_of_voice_3m=round(float(sov.get(m, np.nan)), 3)))
    return pd.DataFrame(rows)


def shortlist(net: pd.DataFrame) -> pd.DataFrame:
    cs = pd.read_csv(PROC / "creator_scores.csv")
    ok = cs[(cs.authenticity_score >= 85) & (cs.audience_own_market >= 0.6) & (cs.tier != "macro")]
    ok = ok.merge(net[["creator_id", "community", "pagerank"]], on="creator_id")
    ok["rank"] = ok.groupby("market").engagements_per_eur.rank(ascending=False)
    return ok[ok["rank"] <= 3].sort_values(["market", "rank"])[
        ["market", "creator_id", "tier", "niche", "platform", "followers", "er_followers", "engagements_per_eur",
         "authenticity_score", "community"]]


def public_summary() -> dict:
    f = {}
    e = pd.read_csv(PUB / "eurostat_social_use.csv")
    last = e.sort_values("year").groupby("geo").last()
    for g in ["FR", "DE", "ES", "IT", "UK", "EU27_2020"]:
        if g in last.index:
            f[f"eurostat_{g}"] = round(float(last.loc[g, "pct_individuals"]), 1)
            f[f"eurostat_{g}_year"] = int(last.loc[g, "year"])
    w = pd.read_csv(PUB / "wikipedia_pageviews.csv")
    full = w.groupby(["kind", "entity"]).lang.nunique()
    w = w[w.set_index(["kind", "entity"]).index.isin(full[full == 5].index)]
    b = w[w.kind == "brand"].groupby(["lang", "entity"]).per_million.mean().reset_index()
    lead = b.loc[b.groupby("lang").per_million.idxmax()].set_index("lang")
    f["wiki_brands_all5"] = int((full.loc["brand"] == 5).sum())
    for lang in ["fr", "en", "de", "es", "it"]:
        f[f"wiki_lead_{lang}"] = lead.loc[lang, "entity"]
        f[f"wiki_lead_{lang}_pm"] = round(float(lead.loc[lang, "per_million"]), 1)
    t = w[w.kind == "topic"]
    sun = t[t.entity == "Sunscreen"].groupby(["lang", "month"]).per_million.sum().reset_index()
    peak = sun.groupby("lang").apply(lambda x: x.per_million.max() / x.per_million.min(), include_groups=False)
    f["wiki_sunscreen_peak_ratio_min"] = round(float(peak.min()), 1)
    f["wiki_sunscreen_peak_ratio_max"] = round(float(peak.max()), 1)
    m = pd.read_csv(PUB / "mastodon_sample.csv")
    collected = (PUB / "collected_on.txt").read_text().strip()
    m12 = m[m.date >= str(pd.Timestamp(collected) - pd.DateOffset(months=12))[:10]]
    f["mastodon_posts_total"] = int(len(m))
    f["mastodon_posts_12m"] = int(len(m12))
    f["mastodon_tags"] = int(m.tag.nunique())
    f["mastodon_median_interactions"] = float((m12.favourites + m12.reblogs + m12.replies).median())
    f["mastodon_share_en"] = round(float((m12.lang == "en").mean()), 3)
    f["mastodon_net_sentiment"] = round(float(100 * ((m12.sentiment > .25).mean() - (m12.sentiment < -.25).mean())), 1)
    th = [c for c in m12.columns if c.startswith("theme_")]
    f["mastodon_top_theme"] = m12[th].mean().idxmax().replace("theme_", "")
    f["mastodon_top_theme_share"] = round(float(m12[th].mean().max()), 3)
    bs = pd.read_csv(PUB / "bluesky_accounts.csv")
    f["bluesky_brands_verified"] = int(bs[bs.entity != "Hopscotch Groupe"].on_bluesky.sum())
    f["bluesky_brands_checked"] = int((bs.entity != "Hopscotch Groupe").sum())
    yt = PUB / "youtube_brand_videos.csv"
    f["youtube_available"] = yt.exists()
    f["collected_on"] = collected
    return f


def report_facts(res: list[dict], comm: pd.DataFrame, prof: pd.DataFrame, short: pd.DataFrame) -> dict:
    k = pd.read_csv(PROC / "kpi_month_market.csv")
    mp = pd.read_csv(PROC / "kpi_month_mp.csv")
    f = {"report_month": "October 2026",
         # method parameters quoted in the report (so the number checker can trace them too)
         "method": dict(ci_level=95, format_min_effect=15, shortlist_min_score=85, shortlist_min_own_market=60,
                        min_posts=8, min_comments=40, sentiment_scale_min=-100, sentiment_scale_max=100, z_threshold=3.5, baseline_months=6, excluded_below_score=50)}
    prev = "2026-09-01"
    for m in MKT:
        cur, pr = k[(k.market == m) & (k.month == REPORT_MONTH)].iloc[0], k[(k.market == m) & (k.month == prev)].iloc[0]
        f[f"{m}_reach_m"] = round(cur.reach / 1e6, 1)
        f[f"{m}_reach_mom"] = round(100 * (cur.reach / pr.reach - 1), 0)
        f[f"{m}_reach_prev_m"] = round(pr.reach / 1e6, 1)
        f[f"{m}_er_reach"] = round(100 * cur.er_reach_org, 1)
        f[f"{m}_er_reach_prev"] = round(100 * pr.er_reach_org, 1)
        f[f"{m}_net_sent"] = round(cur.net_sentiment, 0)
        f[f"{m}_followers_k"] = round(cur.followers_end / 1e3, 0)
        f[f"{m}_spend_k"] = round(cur.spend_eur / 1e3, 1)
        g = mp[(mp.market == m) & (mp.month == REPORT_MONTH)]
        f[f"{m}_cpe"] = round(g.spend_eur.sum() / g.engagements_paid.sum(), 2)
        f[f"{m}_sov"] = round(100 * prof.set_index("market").loc[m, "share_of_voice_3m"], 0)
        # which platform drove the month-on-month change in reach, and how much of the reach was paid
        plats = sorted(mp.platform.unique())
        gp = mp[(mp.market == m) & (mp.month == prev)].set_index("platform").reach.reindex(plats, fill_value=0)
        diff = (g.set_index("platform").reach.reindex(plats, fill_value=0) - gp).sort_values(key=abs)
        f[f"{m}_driver"] = diff.index[-1]
        f[f"{m}_driver_delta_m"] = round(diff.iloc[-1] / 1e6, 1)
        ph = pd.read_csv(PROC / "posts_h.csv", usecols=["market", "month", "reach", "is_sponsored", "in_market_kpis"])
        ph = ph[(ph.market == m) & (ph.month == REPORT_MONTH) & ph.in_market_kpis]
        f[f"{m}_paid_reach_share"] = round(100 * ph.loc[ph.is_sponsored, "reach"].sum() / ph.reach.sum(), 0)
    tot = k[k.month == REPORT_MONTH]
    f["group_reach_m"] = round(tot.reach.sum() / 1e6, 1)
    g = pd.read_csv(PROC / "group_totals.csv")
    gm = g[g.month == REPORT_MONTH].iloc[0]
    f["group_reach_dedup_m"] = round(gm.reach_dedup / 1e6, 1)
    f["group_reach_naive_m"] = round(gm.reach_naive / 1e6, 1)
    r = {x["event_id"]: x for x in res}
    d = r[1]["detail"]
    f.update(ig_raw_ratio=d["raw_ratio"], ig_break=d["break_month"][:7])
    f.update(it_mislabelled=r[2]["detail"]["mislabelled"], it_naive_ratio=r[2]["detail"]["naive_vs_others"])
    f.update(de_best_naive=r[3]["detail"]["best_hour_naive"], de_best_local=r[3]["detail"]["best_hour_local"])
    d = r[4]["detail"]
    f.update(es_follower_jump=round(100 * d["follower_jump"], 0), es_erf_change=round(100 * d["er_followers_change"], 0),
             es_err_change=round(100 * d["er_reach_change"], 0))
    d = r[6]["detail"]
    f.update(fr_sent_now=round(d["value"], 0), fr_sent_usual=round(d["usual"], 0),
             fr_stock_now=round(100 * d["stock_share_now"], 0), fr_stock_before=round(100 * d["stock_share_before"], 0))
    ft = pd.DataFrame(r[7]["detail"]["table"]).set_index("market")
    for m in MKT:
        f[f"{m}_short_vs_carousel"] = float(ft.loc[m, "short_vs_carousel"])
    f["dup_overstatement"] = round(100 * r[8]["detail"]["overstatement"], 1)
    f["dup_global_posts"] = int(pd.read_csv(PROC / "dq_duplicates.csv").global_posts.iloc[0])
    f["suspect_ids"] = r[5]["detail"]["ids"]
    cs = pd.read_csv(PROC / "creator_scores.csv")
    s = cs[cs.creator_id.isin(f["suspect_ids"])].iloc[0]
    f.update(suspect_growth=round(100 * s.max_weekly_growth, 0), suspect_er=round(100 * s.er_followers, 2),
             suspect_tier_er=round(100 * s.tier_median_er, 2))
    f["communities"] = int(len(comm))
    f["communities_single_market"] = int((comm.main_market_share >= 0.6).sum())
    f["creators"] = int(len(cs))
    a = pd.read_csv(PROC / "anomalies.csv")
    f["flags_total"] = int(a.flagged.sum())
    f["kpi_months_screened"] = int(len(a))
    f["events_found"] = int(sum(x["detected"] for x in res))
    for m in MKT:
        p = prof.set_index("market").loc[m]
        f[f"{m}_er_nano"] = round(100 * p.median_er_nano, 1)
        f[f"{m}_er_macro"] = round(100 * p.median_er_macro, 1)
    # top / bottom organic contents of the month (reach at least the market-platform median)
    p = pd.read_csv(PROC / "posts_h.csv")
    p = p[(p.month == REPORT_MONTH) & p.in_market_kpis & ~p.is_sponsored]
    p = p[p.reach >= p.groupby(["market", "platform"]).reach.transform("median")]
    top, bot = p.nlargest(3, "er_reach"), p.nsmallest(3, "er_reach")
    f["top_posts"] = top[["market", "platform", "format", "theme", "reach", "er_reach"]].round(4).to_dict("records")
    f["bottom_posts"] = bot[["market", "platform", "format", "theme", "reach", "er_reach"]].round(4).to_dict("records")
    th = p.groupby("theme").apply(lambda x: x.engagements.sum() / x.reach.sum(), include_groups=False).sort_values()
    f["best_theme"], f["best_theme_er"] = th.index[-1], round(100 * th.iloc[-1], 1)
    f["worst_theme"], f["worst_theme_er"] = th.index[0], round(100 * th.iloc[0], 1)
    f["shortlist"] = short.to_dict("records")
    c = pd.read_csv(PROC / "comments_scored.csv")
    f["lexicon_accuracy"] = round(100 * (c.label == c.label_true).mean(), 0)
    f["lexicon_neg_recall"] = round(100 * (c[c.label_true == "negative"].label == "negative").mean(), 0)
    acc = c.groupby("lang").apply(lambda x: (x.label == x.label_true).mean(), include_groups=False)
    f["lexicon_acc_min_lang"], f["lexicon_acc_min"] = acc.idxmin(), round(100 * acc.min(), 0)
    f["comments_scored"] = int(len(c))
    f["posts_total"] = int(len(pd.read_csv(ROOT / "data" / "simulated" / "posts.csv", usecols=["post_id"])))
    return f


def main():
    res = detect.run_all()
    pd.DataFrame([{k: v for k, v in r.items() if k != "detail"} for r in res]).to_csv(PROC / "detection.csv", index=False)
    pd.DataFrame(res[6]["detail"]["table"]).to_csv(PROC / "format_by_market.csv", index=False)
    sc = detect.score_against_truth(res)
    if sc is not None:
        sc.to_csv(PROC / "detection_vs_truth.csv", index=False)
    comm, net, _ = communities()
    comm.to_csv(PROC / "communities.csv", index=False)
    net.to_csv(PROC / "creator_network.csv", index=False)
    prof = market_profiles(net, comm)
    prof.to_csv(PROC / "market_profiles.csv", index=False)
    short = shortlist(net)
    short.to_csv(PROC / "creator_shortlist.csv", index=False)
    facts = {**public_summary(), **report_facts(res, comm, prof, short)}
    (PROC / "facts.json").write_text(json.dumps(facts, indent=1, default=str), encoding="utf-8")
    print(f"analysis done: {facts['events_found']}/8 situations found, {len(comm)} communities, facts: {len(facts)} keys")


if __name__ == "__main__":
    main()
