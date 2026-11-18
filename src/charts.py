"""Report charts (matplotlib -> inline SVG), reused from an earlier case study's helpers.
House style: plum = the simulated account, green = public data, grey = comparison, red = problems, Segoe UI."""
from __future__ import annotations

import io
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PLUM, PLUM_L, GREEN, GREEN_L = "#6B2D5C", "#C9A6C0", "#0E7A55", "#8FD3B8"
GRAY, GRAY_D, RED, GOLD, BLUE = "#C9C7BF", "#898781", "#B02E2E", "#B88A4E", "#1C5CAB"
INK2, GRID, CARD = "#52514E", "#E1E0D9", "#FFFFFF"
MCOL = {"FR": PLUM, "UK": BLUE, "DE": GOLD, "ES": GREEN, "IT": RED}
MK = {"FR": "France", "UK": "United Kingdom", "DE": "Germany", "ES": "Spain", "IT": "Italy"}
LCOL = {"fr": PLUM, "en": BLUE, "de": GOLD, "es": GREEN, "it": RED}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9.5, "text.color": INK2,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.facecolor": CARD, "figure.facecolor": CARD,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "xtick.color": GRAY_D, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "xtick.major.size": 0, "ytick.major.size": 0, "legend.frameon": False, "legend.fontsize": 8.5,
    "svg.fonttype": "none", "axes.axisbelow": True,
})


def fig(w_px, h_px):
    return plt.subplots(figsize=(w_px / 96, h_px / 96), dpi=96)


def svg(f) -> str:
    buf = io.StringIO()
    f.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.05)
    plt.close(f)
    s = buf.getvalue()
    s = s[s.find("<svg"):]
    s = re.sub(r'width="[\d.]+pt" height="[\d.]+pt"', 'width="100%" height="100%" preserveAspectRatio="xMidYMid meet"', s, 1)
    return re.sub(r"<metadata>.*?</metadata>", "", s, flags=re.S)


def months_axis(ax, idx):
    ticks = [i for i, m in enumerate(idx) if str(m)[5:7] in ("01", "07")]
    ax.set_xticks(ticks, [pd.Timestamp(str(idx[i])[:7] + "-01").strftime("%b %y") for i in ticks])


def eurostat_bars(e: pd.DataFrame, w=430, h=230):
    last = e.sort_values("year").groupby("geo").last()
    last = last.loc[[g for g in ["IT", "DE", "EU27_2020", "ES", "FR", "UK"] if g in last.index]]
    f, ax = fig(w, h)
    lab = [f"{MK.get(g, 'EU 27')} ({int(r.year)})" for g, r in last.iterrows()]
    ax.barh(lab, last.pct_individuals, color=[GRAY if g in ("EU27_2020", "UK") else GREEN for g in last.index])
    for i, v in enumerate(last.pct_individuals):
        ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, 90)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.set_xticks([])
    return svg(f)


def topic_season(w: pd.DataFrame, topic: str, wpx=470, h=230):
    t = w[(w.kind == "topic") & (w.entity == topic)].groupby(["month", "lang"]).per_million.sum().unstack()
    f, ax = fig(wpx, h)
    for lang in ["fr", "en", "de", "es", "it"]:
        if lang in t:
            ax.plot(range(len(t)), t[lang].values, color=LCOL[lang], lw=1.8, label=lang)
    months_axis(ax, [str(m)[:4] + "-" + str(m)[4:6] for m in t.index])
    ax.set_ylabel("views per million")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    return svg(f)


def brand_heat(w: pd.DataFrame, wpx=520, h=250):
    full = w.groupby(["kind", "entity"]).lang.nunique()
    w = w[w.set_index(["kind", "entity"]).index.isin(full[full == 5].index)]
    b = w[w.kind == "brand"].pivot_table(index="entity", columns="lang", values="per_million", aggfunc="mean")[["fr", "en", "de", "es", "it"]]
    b = b.loc[b.mean(axis=1).sort_values().index]
    f, ax = fig(wpx, h)
    ax.imshow(b.values, cmap="Greens", aspect="auto")
    ax.set_xticks(range(5), ["fr", "en", "de", "es", "it"])
    ax.set_yticks(range(len(b)), b.index)
    for i in range(len(b)):
        for j in range(5):
            v = b.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5, color="white" if v > b.values.max() * .55 else INK2)
    ax.grid(False)
    return svg(f)


def mastodon_bars(m12: pd.DataFrame, wpx=420, h=230):
    th = [c for c in m12.columns if c.startswith("theme_")]
    s = (m12[th].mean() * 100).rename(lambda c: c.replace("theme_", "").replace("_", " ")).sort_values()
    f, ax = fig(wpx, h)
    ax.barh(s.index, s.values, color=GREEN)
    for i, v in enumerate(s.values):
        ax.text(v + .5, i, f"{v:.0f}%", va="center", fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_xticks([])
    return svg(f)


def ig_views(k: pd.DataFrame, wpx=430, h=220):
    ig = k[k.platform == "Instagram"].groupby("month")[["views_raw", "views", "reach"]].sum()
    f, ax = fig(wpx, h)
    x = range(len(ig))
    ax.plot(x, ig.views_raw / ig.reach, color=RED, lw=2, label="'views' as exported")
    ax.plot(x, ig.views / ig.reach, color=PLUM, lw=2, label="harmonised views")
    months_axis(ax, list(ig.index))
    ax.set_ylabel("views per reach")
    ax.set_ylim(0, 2.2)
    ax.legend(loc="lower right")
    return svg(f)


def group_reach(g: pd.DataFrame, wpx=430, h=220):
    f, ax = fig(wpx, h)
    x = np.arange(len(g))
    ax.bar(x, g.reach_naive / 1e6, color=GRAY, label="5 exports added up")
    ax.bar(x, g.reach_dedup / 1e6, color=PLUM, width=.55, label="each post once")
    months_axis(ax, list(g.month))
    ax.set_ylabel("group reach (M)")
    ax.legend(loc="upper left")
    return svg(f)


def hours(p: pd.DataFrame, market="DE", wpx=430, h=220):
    p = p[(p.market == market) & ~p.is_sponsored & p.in_market_kpis]
    f, ax = fig(wpx, h)
    for col, lab, c in (("local_hour", "local time", PLUM), ("hour_as_exported", "as exported (UTC)", GOLD)):
        s = p.groupby(col).apply(lambda x: 100 * x.engagements.sum() / x.reach.sum() if len(x) >= 10 else np.nan, include_groups=False)
        s = s[s.index >= 6]
        ax.plot(s.index, s.values, marker="o", ms=3, color=c, lw=1.8, label=lab)
    ax.set_xlabel("hour of posting")
    ax.set_ylabel("ER by reach (%)")
    ax.legend()
    return svg(f)


def er_lines(km: pd.DataFrame, wpx=470, h=230):
    f, ax = fig(wpx, h)
    months = sorted(km.month.unique())
    for m in MK:
        s = km[km.market == m].set_index("month").er_reach_org.reindex(months) * 100
        ax.plot(range(len(months)), s.values, color=MCOL[m], lw=1.8, label=MK[m])
    months_axis(ax, months)
    ax.set_ylabel("ER by reach, organic (%)")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.14), fontsize=8)
    return svg(f)


def false_signal(k: pd.DataFrame, wpx=430, h=220):
    es = k[(k.market == "ES") & (k.platform == "Instagram")].set_index("month").sort_index()
    base = es[["er_followers_org", "er_reach_org"]].iloc[:6].median()
    idx = es[["er_followers_org", "er_reach_org"]] / base
    sm = idx.rolling(3, min_periods=1).median()
    f, ax = fig(wpx, h)
    x = range(len(es))
    ax.plot(x, sm.er_followers_org, color=RED, lw=2, label="ER per follower")
    ax.plot(x, sm.er_reach_org, color=PLUM, lw=2, label="ER per reach")
    i = list(es.index).index("2026-03-01")
    ax.axvline(i, color=GRAY_D, ls=":", lw=1)
    ax.text(i + .2, 1.18, "giveaway", fontsize=8.5, color=GRAY_D)
    months_axis(ax, list(es.index))
    ax.set_ylabel("index, first 6 months = 1 (3-mo. median)")
    ax.set_ylim(0.6, 1.3)
    ax.legend(loc="lower left")
    return svg(f)


def fr_sentiment(c: pd.DataFrame, wpx=430, h=220):
    c = c[c.market == "FR"].assign(month=lambda x: x.date.str[:7])
    s = c.groupby("month").apply(lambda x: 100 * ((x.label == "positive").mean() - (x.label == "negative").mean()), include_groups=False)
    f, ax = fig(wpx, h)
    ax.plot(range(len(s)), s.values, color=PLUM, lw=2)
    ax.scatter([len(s) - 1], [s.values[-1]], color=RED, zorder=3)
    months_axis(ax, [m + "-01" for m in s.index])
    ax.set_ylabel("net sentiment (pts)")
    ax.set_ylim(-5, 55)
    return svg(f)


def format_ratio(t: pd.DataFrame, wpx=430, h=220):
    t = t.set_index("market").loc[list(MK)]
    f, ax = fig(wpx, h)
    col = [PLUM if (r.short_vs_carousel >= 1.15 and r.ci_low > 1) else GOLD if (r.short_vs_carousel <= .85 and r.ci_high < 1) else GRAY
           for r in t.itertuples()]
    ax.bar(list(t.index), t.short_vs_carousel, color=col,
           yerr=[t.short_vs_carousel - t.ci_low, t.ci_high - t.short_vs_carousel], capsize=3, ecolor=INK2)
    ax.axhline(1, color=INK2, lw=1, ls="--")
    for i, v in enumerate(t.short_vs_carousel):
        ax.text(i, v + .1, f"x{v:.2f}", ha="center", fontsize=8.5)
    ax.set_ylabel("short video / carousel")
    ax.set_ylim(0, 1.8)
    return svg(f)


def network(net: pd.DataFrame, wpx=520, h=330):
    f, ax = fig(wpx, h)
    for m, g in net.groupby("market"):
        ax.scatter(g.x, g.y, s=4 + 160 * g.pagerank / net.pagerank.max(), color=MCOL[m], alpha=.7, lw=0, label=MK[m])
    s = net[net.authenticity_score < 50]
    ax.scatter(s.x, s.y, s=140, facecolors="none", edgecolors="black", lw=1.4, label="excluded")
    ax.set_axis_off()
    ax.legend(ncol=1, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, markerscale=1.2, handletextpad=0.2)
    return svg(f)


def tier_box(cs: pd.DataFrame, wpx=330, h=220):
    f, ax = fig(wpx, h)
    data = [100 * cs[cs.tier == t].er_followers for t in ("nano", "micro", "macro")]
    b = ax.boxplot(data, tick_labels=["nano", "micro", "macro"], patch_artist=True, showfliers=False, widths=.5)
    for p in b["boxes"]:
        p.set_facecolor(PLUM_L)
        p.set_edgecolor(PLUM)
    for med in b["medians"]:
        med.set_color(PLUM)
    ax.set_ylabel("engagement per follower (%)")
    return svg(f)


def suspect_curve(hist: pd.DataFrame, cid: str, wpx=330, h=220):
    g = hist[hist.creator_id == cid]
    f, ax = fig(wpx, h)
    ax.plot(pd.to_datetime(g.week), g.followers / 1e3, color=RED, lw=2)
    ax.set_ylabel("followers (k)")
    ax.tick_params(axis="x", labelsize=8)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    return svg(f)
