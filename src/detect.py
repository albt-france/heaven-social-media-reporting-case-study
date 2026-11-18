"""Detection rules for the monthly review (SIMULATED data). Each rule reads the SQL outputs in data/processed/ and
returns what it found, the evidence, and the decision taken. Used by the notebook, the report and the tests.

The 8 situations the rules look for (the simulation hides them; src/simulate.py holds the parameters):
1 metric definition change   2 sponsored mixed into organic   3 export time zone   4 false signal (giveaway)
5 suspect creator            6 negative sentiment spike       7 market-specific format effect   8 duplicated global posts
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"


def rd(name: str) -> pd.DataFrame:
    return pd.read_csv(PROC / f"{name}.csv")


def definition_change() -> dict:
    """Largest before/after break in raw 'views' per reach, per platform; harmonised series must stay flat."""
    k = rd("kpi_month_mp")
    out = []
    for plat, g in k.groupby("platform"):
        s = g.groupby("month").agg(raw=("views_raw", "sum"), h=("views", "sum"), reach=("reach", "sum")).sort_index()
        raw, h = s.raw / s.reach, s.h / s.reach
        if not (raw > 0).any():
            continue
        best = None
        for i in range(3, len(s) - 3):
            r = raw.iloc[i:].mean() / raw.iloc[:i].mean()
            if best is None or abs(np.log(r)) > abs(np.log(best[1])):
                best = (s.index[i], r, h.iloc[i:].mean() / h.iloc[:i].mean())
        if best and abs(np.log(best[1])) > np.log(1.5):
            out.append(dict(platform=plat, break_month=best[0], raw_ratio=round(best[1], 2), harmonised_ratio=round(best[2], 3)))
    hit = out[0] if out else None
    return dict(event_id=1, event="metric_definition_change", detected=hit is not None,
                where=f"{hit['platform']} from {hit['break_month']}" if hit else "",
                evidence=(f"raw views per reach x{hit['raw_ratio']} after the break; harmonised views per reach "
                          f"x{hit['harmonised_ratio']}") if hit else "no break",
                decision="use harmonised views (impressions before the change, new views after)", **({"detail": hit} if hit else {}))


def sponsored_mix() -> dict:
    """Organic reach rate (reach / followers per post) as the tool exports it vs after the ad-spend correction."""
    d, p = rd("dq_sponsored"), rd("posts_h")
    p = p[p.in_market_kpis].assign(rate=lambda x: x.reach / x.followers)
    naive = p[p.paid_label == "organic"].groupby("market").rate.median()
    clean = p[~p.is_sponsored].groupby("market").rate.median()
    bad = d[d.share_mislabelled > 0.05]
    m = bad.market.iloc[0] if len(bad) else None
    r_naive = naive[m] / naive.drop(index=m).median() if m else None
    r_clean = clean[m] / clean.drop(index=m).median() if m else None
    return dict(event_id=2, event="sponsored_mixed_in_organic", detected=m is not None, where=m or "",
                evidence=(f"{int(bad.organic_label_with_spend.iloc[0])} posts labelled organic have ad spend; median "
                          f"'organic' reach rate x{r_naive:.2f} the other markets as exported, x{r_clean:.2f} after correction")
                if m else "",
                decision="sponsored = tool label OR ad spend > 0; organic KPIs on organic posts only",
                detail=dict(market=m, naive_vs_others=round(r_naive, 2) if m else None,
                            clean_vs_others=round(r_clean, 2) if m else None,
                            mislabelled=int(bad.organic_label_with_spend.iloc[0]) if m else 0))


def timezone_export() -> dict:
    t = rd("dq_timezone").set_index("market")
    base = t.share_before_8_exported.median()
    sus = t[(t.share_before_8_exported > 3 * base) | ((t.median_hour_exported - t.median_hour_exported.median()).abs() >= 2)]
    m = sus.index[0] if len(sus) else None
    p = rd("posts_h")
    p = p[(p.market == m) & ~p.is_sponsored & p.in_market_kpis] if m else p.iloc[:0]
    best_naive = p.groupby("hour_as_exported").er_reach.mean().idxmax() if m else None
    best_local = p.groupby("local_hour").er_reach.mean().idxmax() if m else None
    return dict(event_id=3, event="timezone_utc_export", detected=m is not None, where=m or "",
                evidence=(f"{t.loc[m, 'share_before_8_exported']:.0%} of posts before 08:00 as exported vs "
                          f"{base:.0%} elsewhere; export setting = {t.loc[m, 'timezone_of_export']}") if m else "",
                decision="convert every export to market local time before any 'best time to post'",
                detail=dict(market=m, best_hour_naive=int(best_naive) if m else None, best_hour_local=int(best_local) if m else None))


def false_signal(window: int = 6) -> dict:
    """A follower jump makes ER per follower fall; if ER per reach is flat, it is the denominator, not the content."""
    a, k = rd("anomalies"), rd("kpi_month_mp")
    jumps = a[(a.metric == "follower_growth") & a.flagged & (a.value > 0.10)]
    res = None
    for r in jumps.itertuples():
        g = k[(k.market == r.market) & (k.platform == r.platform)].sort_values("month").reset_index(drop=True)
        i = g.index[g.month == r.month][0]
        pre, post = g.iloc[max(0, i - window):i], g.iloc[i + 1:i + 1 + window]
        erf = post.er_followers_org.median() / pre.er_followers_org.median()
        err = post.er_reach_org.median() / pre.er_reach_org.median()
        res = dict(market=r.market, platform=r.platform, month=r.month, follower_jump=round(r.value, 3),
                   er_followers_change=round(erf - 1, 3), er_reach_change=round(err - 1, 3),
                   content_issue_raised=bool(abs(err - 1) > 0.10))
    ok = res is not None and res["er_followers_change"] < -0.10 and not res["content_issue_raised"]
    return dict(event_id=4, event="false_signal_contest", detected=ok, where=f"{res['market']} {res['platform']}" if res else "",
                evidence=(f"followers +{res['follower_jump']:.0%} in {res['month'][:7]}; ER per follower "
                          f"{res['er_followers_change']:+.0%}, ER per reach {res['er_reach_change']:+.0%} "
                          f"(medians, {window} months after vs before)") if res else "",
                decision="NOT raised as a content problem: report ER per reach; explain the giveaway followers",
                detail=res or {})


def suspect_creators() -> dict:
    c = rd("creator_scores")
    s = c[c.authenticity_score < 50].sort_values("authenticity_score")
    return dict(event_id=5, event="suspect_creator", detected=len(s) > 0, where=", ".join(s.creator_id),
                evidence="; ".join(f"{r.creator_id}: score {r.authenticity_score}, max weekly growth {r.max_weekly_growth:+.0%}, "
                                   f"ER {r.er_followers:.2%} vs tier median {r.tier_median_er:.2%}" for r in s.itertuples()),
                decision="excluded from recommendations until audience is audited", detail=dict(ids=list(s.creator_id)))


def sentiment_spike() -> dict:
    a = rd("anomalies")
    s = a[(a.metric == "net_sentiment") & (a.platform == "All") & a.flagged & (a.robust_z < 0)]
    if s.empty:
        return dict(event_id=6, event="negative_sentiment_spike", detected=False, where="", evidence="", decision="")
    r = s.sort_values("robust_z").iloc[0]
    c = rd("comments_scored")
    c["month"] = c.date.str[:7] + "-01"
    neg = c[(c.market == r.market) & (c.label == "negative")]
    now, before = neg[neg.month == r.month], neg[neg.month < r.month]
    return dict(event_id=6, event="negative_sentiment_spike", detected=True, where=f"{r.market} {r.month[:7]}",
                evidence=(f"net sentiment {r.value:.0f} vs {r.base_median:.0f} usual (z {r.robust_z:.1f}); stock / availability "
                          f"in {now.theme_stock_availability.mean():.0%} of negative comments vs {before.theme_stock_availability.mean():.0%} before"),
                decision="attention point: stock-out of a hero product; align community replies with supply dates",
                detail=dict(market=r.market, month=r.month, value=round(r.value, 1), usual=round(r.base_median, 1),
                            z=round(r.robust_z, 1), stock_share_now=round(now.theme_stock_availability.mean(), 3),
                            stock_share_before=round(before.theme_stock_availability.mean(), 3)))


def format_effect(n_boot: int = 400, seed: int = 42) -> dict:
    """Instagram, organic posts: ER per reach of short video vs carousel, by market, with a bootstrap 95% interval."""
    p = rd("posts_h")
    p = p[(p.platform == "Instagram") & ~p.is_sponsored & p.in_market_kpis].sort_values("post_id")
    rng = np.random.default_rng(seed)
    rows = []
    for m, g in p.groupby("market"):
        sv, ca = g[g.format == "short video"], g[g.format == "carousel"]
        ratio = (sv.engagements.sum() / sv.reach.sum()) / (ca.engagements.sum() / ca.reach.sum())
        boots = []
        for _ in range(n_boot):
            a, b = sv.sample(len(sv), replace=True, random_state=rng.integers(1e9)), ca.sample(len(ca), replace=True, random_state=rng.integers(1e9))
            boots.append((a.engagements.sum() / a.reach.sum()) / (b.engagements.sum() / b.reach.sum()))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append(dict(market=m, short_vs_carousel=round(ratio, 2), ci_low=round(lo, 2), ci_high=round(hi, 2),
                         n_short=len(sv), n_carousel=len(ca)))
    t = pd.DataFrame(rows)
    # material AND significant: at least +/-15% and the 95% interval excludes 1
    up = t[(t.short_vs_carousel >= 1.15) & (t.ci_low > 1)].market.tolist()
    down = t[(t.short_vs_carousel <= 0.85) & (t.ci_high < 1)].market.tolist()
    return dict(event_id=7, event="format_effect_by_market", detected=bool(up and down),
                where=f"short video ahead: {', '.join(up)}; carousel ahead: {', '.join(down)}",
                evidence="; ".join(f"{r.market} x{r.short_vs_carousel} [{r.ci_low}-{r.ci_high}]" for r in t.itertuples()),
                decision="format mix set per market, not one global rule", detail=dict(table=t.to_dict("records")))


def duplicates() -> dict:
    d, g = rd("dq_duplicates"), rd("group_totals")
    over = g.reach_naive.sum() / g.reach_dedup.sum() - 1
    r = d.iloc[0] if len(d) else None
    return dict(event_id=8, event="global_post_duplicates", detected=r is not None and r.extra_rows > 0,
                where=r.platform if r is not None else "",
                evidence=(f"{int(r.global_posts)} global posts appear {int(r.rows_in_exports)} times; group reach overstated by "
                          f"{over:.1%} without deduplication") if r is not None else "",
                decision="count each native post id once in group totals; keep it out of market comparisons",
                detail=dict(overstatement=round(over, 4)))


RULES = [definition_change, sponsored_mix, timezone_export, false_signal, suspect_creators, sentiment_spike, format_effect,
         duplicates]


def run_all() -> list[dict]:
    return [f() for f in RULES]


def score_against_truth(results: list[dict]) -> pd.DataFrame | None:
    """Compare with the hidden answer key when it is present (local runs only)."""
    f = ROOT / "data" / "_hidden_truth.csv"
    if not f.exists():
        return None
    t = pd.read_csv(f).set_index("event_id")
    rows = []
    for r in results:
        e = t.loc[r["event_id"]]
        where = str(r["where"])
        ok = r["detected"] and (e.market in ("all",) or all(m in where for m in str(e.market).split(",")) or
                                (r["event_id"] == 1 and str(e.platform) in where) or
                                (r["event_id"] == 5 and str(e.detail) in where))
        if r["event_id"] == 5:
            ok = r["detected"] and r["detail"]["ids"] == [e.detail]
        rows.append(dict(event_id=r["event_id"], event=r["event"], found=bool(ok)))
    return pd.DataFrame(rows)
