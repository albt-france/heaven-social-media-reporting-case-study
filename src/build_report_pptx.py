"""Monthly client report, October 2026, agency format, 10 slides (python-pptx). SIMULATED account on every slide.

Usage: python src/build_report_pptx.py   -> reports/monthly_report_oct2026.pptx (+ .pdf if LibreOffice is installed)
Every number comes from data/processed/facts.json; src/fact_check.py then checks every number written in the deck.
Charts are native PowerPoint charts, so the client team can edit them.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "monthly_report_oct2026.pptx"
F = json.loads((ROOT / "data" / "processed" / "facts.json").read_text(encoding="utf-8"))

INK, MUTED, LINE, PANEL = RGBColor(0x1F, 0x1D, 0x1A), RGBColor(0x6B, 0x67, 0x60), RGBColor(0xDD, 0xD8, 0xD0), RGBColor(0xF6, 0xF3, 0xEF)
PLUM, PLUM_L, GOLD, RED, GREEN = (RGBColor(0x6B, 0x2D, 0x5C), RGBColor(0xC9, 0xA6, 0xC0), RGBColor(0xB8, 0x8A, 0x4E),
                                  RGBColor(0xB0, 0x2E, 0x2E), RGBColor(0x1E, 0x7A, 0x52))
WHITE, BLUE = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0x1C, 0x5C, 0xAB)
FONT = "Segoe UI"
MK = {"FR": "France", "UK": "United Kingdom", "DE": "Germany", "ES": "Spain", "IT": "Italy"}
FOOT = ("SIMULATED data · fictitious account · Independent case study based on public data · "
        "not affiliated with or endorsed by heaven or Hopscotch Groupe")
N_SLIDES = 10


def pd_month(ym: str) -> str:
    import calendar
    y, m = ym.split("-")[:2]
    return f"{calendar.month_name[int(m)]} {y}"


def pct(v, d=1):
    return f"{v:.{d}f}%"


def sg(v, d=0, suf="%"):
    return f"{v:+.{d}f}{suf}"


def run(p, text, size=14, bold=False, color=INK, italic=False):
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(size), bold, italic, FONT
    r.font.color.rgb = color
    return r


def box(s, x, y, w, h, paras, fill=None, line=None, anchor=MSO_ANCHOR.TOP, margin=0.08):
    shp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)) if fill or line else \
        s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if fill or line:
        shp.fill.solid() if fill else shp.fill.background()
        if fill:
            shp.fill.fore_color.rgb = fill
        if line:
            shp.line.color.rgb = line
            shp.line.width = Pt(0.75)
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
    tf = shp.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Inches(margin))
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        items = para if isinstance(para, list) else [para]
        for it in items:
            if isinstance(it, str):
                it = (it,)
            run(p, *it) if len(it) == 1 else run(p, it[0], **it[1])
        p.space_after = Pt(6)
    return shp


def base(prs, n, kicker, title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    box(s, 0.5, 0.28, 9.5, 0.3, [[(kicker.upper(), dict(size=10.5, bold=True, color=PLUM))]], margin=0)
    box(s, 0.5, 0.55, 10.9, 1.0, [[(title, dict(size=24, bold=True))]], margin=0)
    tag = box(s, 11.55, 0.3, 1.3, 0.32, [[("SIMULATED", dict(size=10, bold=True, color=BLUE))]], line=RGBColor(0x86, 0xB6, 0xEF),
              anchor=MSO_ANCHOR.MIDDLE, margin=0.02)
    tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    ln = s.shapes.add_connector(1, Inches(0.5), Inches(7.0), Inches(12.83), Inches(7.0))
    ln.line.color.rgb, ln.line.width = LINE, Pt(0.75)
    box(s, 0.5, 7.03, 11.2, 0.3, [[(FOOT, dict(size=8.5, color=MUTED))]], margin=0)
    num = box(s, 11.9, 7.03, 0.93, 0.3, [[(f"slide {n}", dict(size=8.5, color=MUTED))]], margin=0)
    num.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
    return s


def table(s, x, y, w, h, header, rows, widths=None, size=11, first_bold=True, colors=None):
    t = s.shapes.add_table(len(rows) + 1, len(header), Inches(x), Inches(y), Inches(w), Inches(h)).table
    for j, wd in enumerate(widths or [w / len(header)] * len(header)):
        t.columns[j].width = Inches(wd)
    for i, row in enumerate([header] + rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = PLUM if i == 0 else (PANEL if i % 2 == 0 else WHITE)
            c.margin_left = c.margin_right = Inches(0.06)
            c.margin_top = c.margin_bottom = Inches(0.03)
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            col = WHITE if i == 0 else (colors.get((i - 1, j), INK) if colors else INK)
            run(p, str(val), size=size if i else size - 0.5, bold=(i == 0) or (first_bold and j == 0), color=col)
            p.alignment = PP_ALIGN.LEFT if j == 0 or i == 0 else PP_ALIGN.LEFT
    return t


def bar_chart(s, x, y, w, h, cats, series, colors, number_format='0.0', legend=True, title=None, horizontal=False):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    ch = s.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.font.name, ch.font.size, ch.font.color.rgb = FONT, Pt(11), INK
    ch.has_legend = legend and len(series) > 1
    if ch.has_legend:
        ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
    if title:
        ch.has_title = True
        ch.chart_title.text_frame.text = title
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    else:
        ch.has_title = False
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = LINE
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(10)
    va.tick_labels.font.color.rgb = MUTED
    ch.category_axis.tick_labels.font.size = Pt(11)
    ch.category_axis.format.line.color.rgb = LINE
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = 60, -10
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = number_format, False
    dl.font.size, dl.position = Pt(10), XL_LABEL_POSITION.OUTSIDE_END
    for ser, col in zip(plot.series, colors):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = col
    return ch


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    mk = list(MK)

    # 1. Cover
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = PLUM
    bg.line.fill.background()
    box(s, 0.8, 2.2, 11, 1.0, [[("Monthly social media report", dict(size=40, bold=True, color=WHITE))]], margin=0)
    box(s, 0.8, 3.25, 11.5, 1.2, [[(f"{F['report_month']} · a global beauty retailer (fictitious account) · 5 markets · 5 platforms",
                                     dict(size=18, color=WHITE))],
                                   [("Instagram, TikTok, Facebook, X and YouTube · France, United Kingdom, Germany, Spain, Italy",
                                     dict(size=13, color=PLUM_L))]], margin=0)
    box(s, 0.8, 5.6, 11.8, 0.8, [[("Agency-format example built on SIMULATED data. It does not describe any real brand, "
                                   "heaven, Hopscotch Groupe or any of their clients.", dict(size=12, color=WHITE))],
                                 [(FOOT.replace("SIMULATED data · fictitious account · ", ""), dict(size=10, color=PLUM_L))]], margin=0)
    tag = box(s, 11.3, 0.45, 1.5, 0.36, [[("SIMULATED", dict(size=11, bold=True, color=WHITE))]], line=WHITE,
              anchor=MSO_ANCHOR.MIDDLE, margin=0.02)
    tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # 2. Three messages
    up = [m for m in mk if F[f"{m}_er_reach"] - F[f"{m}_er_reach_prev"] >= 0.3]
    down = [m for m in mk if F[f"{m}_er_reach"] - F[f"{m}_er_reach_prev"] <= -0.3]
    s = base(prs, 2, "October 2026 in three messages", "Content quality rose in "
             f"{' and '.join(MK[m] for m in up)}, France faces a stock-out, and formats work differently by market")
    msgs = [
        ("1  Content quality", f"Organic engagement rate by reach rose in " +
         "; ".join(f"{MK[m]} ({pct(F[f'{m}_er_reach'])}, from {pct(F[f'{m}_er_reach_prev'])})" for m in up) +
         ". It fell in " + "; ".join(f"{MK[m]} ({pct(F[f'{m}_er_reach'])}, from {pct(F[f'{m}_er_reach_prev'])})" for m in down) + "."),
        ("2  Attention point", f"In France, the stock-out of a hero product turned the conversation negative: net sentiment "
         f"{F['fr_sent_now']:.0f} vs {F['fr_sent_usual']:.0f} usually. Stock or availability is the topic of {pct(F['fr_stock_now'], 0)} "
         f"of negative comments."),
        ("3  Formats", f"On Instagram, short video beats carousel in France (x{F['FR_short_vs_carousel']}) and Spain "
         f"(x{F['ES_short_vs_carousel']}); in Germany carousel wins (short video x{F['DE_short_vs_carousel']}). "
         "One global format rule would cost engagement."),
    ]
    for i, (h, t) in enumerate(msgs):
        box(s, 0.5 + i * 4.15, 1.75, 3.95, 2.75, [[(h, dict(size=16, bold=True, color=PLUM))], [(t, dict(size=15))]],
            fill=PANEL, margin=0.2)
    cards = [("Group reach, each post once", f"{F['group_reach_dedup_m']}M"),
             ("Best engagement rate by reach", f"{MK[max(mk, key=lambda m: F[f'{m}_er_reach'])]} "
                                               f"{pct(max(F[f'{m}_er_reach'] for m in mk))}"),
             ("Net sentiment, France", f"{F['FR_net_sent']:+.0f} (usually {F['fr_sent_usual']:.0f})"),
             ("Data issues fixed before reading", "four")]
    for i, (lab, val) in enumerate(cards):
        box(s, 0.5 + i * 3.1, 4.75, 2.95, 1.0, [[(lab.upper(), dict(size=9.5, bold=True, color=MUTED))],
                                                 [(val, dict(size=20, bold=True, color=RED if 'France' in lab else PLUM))]],
            line=LINE, margin=0.12)
    box(s, 0.5, 5.95, 12.3, 0.95, [[("Also this month: ", dict(size=12.5, bold=True)),
                                   (f"group reach {F['group_reach_dedup_m']}M with each post counted once "
                                    f"({F['group_reach_naive_m']}M if global posts are added up market by market). "
                                    f"The drop in Spain's engagement per follower is a false alarm (giveaway followers), "
                                    "not a content problem: see slide 8.", dict(size=12.5))]], margin=0)

    # 3. KPI table
    best = max(mk, key=lambda m: F[f"{m}_er_reach"])
    big = max(mk, key=lambda m: F[f"{m}_reach_m"])
    s = base(prs, 3, "KPIs by market, October 2026",
             f"{MK[best]} leads on engagement by reach ({pct(F[f'{best}_er_reach'])}); "
             f"{'the ' if big == 'UK' else ''}{MK[big]} has the largest reach ({F[f'{big}_reach_m']}M)")
    rows = []
    for m in mk:
        rows.append([MK[m], f"{F[f'{m}_reach_m']}M", sg(F[f'{m}_reach_mom']), f"{pct(F[f'{m}_er_reach'])} ({pct(F[f'{m}_er_reach_prev'])})",
                     f"{F[f'{m}_followers_k']:,.0f}k", f"{F[f'{m}_net_sent']:+.0f}", pct(F[f'{m}_sov'], 0),
                     pct(F[f'{m}_paid_reach_share'], 0), f"€{F[f'{m}_cpe']:.2f}"])
    colors = {(i, 6 - 1): (RED if F[f"{m}_net_sent"] < 15 else INK) for i, m in enumerate(mk)}
    table(s, 0.5, 1.75, 12.3, 3.2, ["Market", "Reach", "vs Sept", "Engagement rate by reach, organic (Sept)", "Followers",
                                   "Net sentiment", "Share of voice, 3 months", "Paid share of reach",
                                   "Cost per paid engagement"],
          rows, widths=[1.55, 0.95, 0.9, 2.15, 1.15, 1.15, 1.6, 1.3, 1.55], size=12.5, colors=colors)
    box(s, 0.5, 5.25, 12.3, 1.6, [
        [("How to read it. ", dict(size=12, bold=True)), ("Engagement rate by reach = engagements / reach on organic posts: the "
         "comparison KPI across markets. Net sentiment = % positive - % negative comments (-100 to +100). Share of voice = "
         "mentions of the brand / all brand mentions by the market's creators.", dict(size=12, color=MUTED))],
        [("Group total. ", dict(size=12, bold=True)), (f"{F['group_reach_dedup_m']}M reach, each post counted once; adding the five "
         f"market exports gives {F['group_reach_naive_m']}M because {F['dup_global_posts']} global posts sit in every export "
         "(see slide 8).", dict(size=12, color=MUTED))]], margin=0)

    # 4. Reach drivers
    s = base(prs, 4, "Reach: what moved",
             f"Reach swings came mostly from TikTok, and paid posts bring {pct(min(F[f'{m}_paid_reach_share'] for m in mk), 0)} "
             f"to {pct(max(F[f'{m}_paid_reach_share'] for m in mk), 0)} of reach: quality is read on organic posts")
    bar_chart(s, 0.5, 1.7, 7.3, 5.1, [MK[m] for m in mk],
              [("September", [F[f"{m}_reach_prev_m"] for m in mk]), ("October", [F[f"{m}_reach_m"] for m in mk])],
              [PLUM_L, PLUM], title="Reach by market (millions)")
    paras = [[("Biggest change by platform", dict(size=14, bold=True, color=PLUM))]]
    for m in mk:
        paras.append([(f"{MK[m]}: ", dict(size=13, bold=True)),
                      (f"{sg(F[f'{m}_reach_mom'])} reach, mostly {F[f'{m}_driver']} ({F[f'{m}_driver_delta_m']:+.1f}M). "
                       f"Paid share {pct(F[f'{m}_paid_reach_share'], 0)}.", dict(size=13))])
    paras.append([("TikTok reach is driven by a few posts that travel far beyond followers: one month is not a trend.",
                   dict(size=12, color=MUTED, italic=True))])
    box(s, 8.1, 1.75, 4.75, 5.1, paras, fill=PANEL, margin=0.18)

    # 5. Best and worst content
    s = base(prs, 5, "Content performance",
             f"Tutorials engage most ({pct(F['best_theme_er'])} by reach), brand stories least ({pct(F['worst_theme_er'])})"
             if F["best_theme"] == "tutorial" and F["worst_theme"] == "brand story" else
             f"{F['best_theme'].capitalize()} engages most ({pct(F['best_theme_er'])}), {F['worst_theme']} least ({pct(F['worst_theme_er'])})")
    hdr = ["Market", "Platform", "Format", "Theme", "Reach", "Engagement rate by reach"]
    w = [1.6, 1.25, 1.35, 1.6, 1.05, 1.3]
    for k, (name, key) in enumerate((("Top 3 organic posts", "top_posts"), ("Bottom 3 organic posts", "bottom_posts"))):
        box(s, 0.5, 1.7 + k * 2.45, 8.2, 0.35, [[(name, dict(size=14, bold=True, color=GREEN if k == 0 else RED))]], margin=0)
        rows = [[MK[r["market"]], r["platform"], r["format"], r["theme"],
                 f"{r['reach'] / 1e6:.2f}M" if r["reach"] >= 1e6 else f"{r['reach'] / 1e3:.0f}k", pct(100 * r["er_reach"])]
                for r in F[key]]
        table(s, 0.5, 2.1 + k * 2.45, 8.15, 1.6, hdr, rows, widths=w, size=12)
    box(s, 9.0, 1.75, 3.85, 5.0, [
        [("What the ranking says", dict(size=14, bold=True, color=PLUM))],
        [("Only posts with at least the median reach of their market and platform are ranked, so a post seen by a "
          "handful of people cannot top the list.", dict(size=12.5))],
        [(f"Themes: {F['best_theme']} {pct(F['best_theme_er'])} vs {F['worst_theme']} {pct(F['worst_theme_er'])} engagement "
          "by reach across markets. Show the product in use; keep brand stories for paid reach.", dict(size=12.5))],
        [("Sponsored posts are ranked separately, on cost per engagement.", dict(size=12, color=MUTED, italic=True))]],
        fill=PANEL, margin=0.18)

    # 6. Formats
    s = base(prs, 6, "Formats by market",
             "Short video wins in France and Spain, carousel in Germany: the format mix is set market by market")
    bar_chart(s, 0.5, 1.7, 7.6, 5.1, [MK[m] for m in mk], [("Short video vs carousel", [F[f"{m}_short_vs_carousel"] for m in mk])],
              [PLUM], number_format='0.00"x"', legend=False,
              title="Instagram, organic: engagement rate by reach of short video / carousel (1.00 = equal)")
    box(s, 8.4, 1.75, 4.45, 5.1, [
        [("How to read it", dict(size=14, bold=True, color=PLUM))],
        [(f"France x{F['FR_short_vs_carousel']}: a short video earns {F['FR_short_vs_carousel']} times the engagement rate "
          "of a carousel.", dict(size=13))],
        [(f"Germany x{F['DE_short_vs_carousel']}: the carousel does better; educational, swipeable content fits.", dict(size=13))],
        [(f"United Kingdom x{F['UK_short_vs_carousel']} and Italy x{F['IT_short_vs_carousel']}: no material difference; "
          "keep a balanced mix.", dict(size=13))],
        [("Method: all organic Instagram posts since June 2025, bootstrap 95% intervals; a difference is retained only "
          "if it is at least 15% and the interval excludes 1.", dict(size=11.5, color=MUTED, italic=True))]],
        fill=PANEL, margin=0.18)

    # 7. Communities and creators
    s = base(prs, 7, "Influencer communities and creators",
             f"Influence is local: {F['communities']} creator communities, each anchored in one market; nano creators engage "
             "about three times more than macro")
    rows = []
    for m in mk:
        sl = [r for r in F["shortlist"] if r["market"] == m][:1]
        top = f"{sl[0]['creator_id']} ({sl[0]['tier']}, {sl[0]['niche']}, {pct(100 * sl[0]['er_followers'])})" if sl else "-"
        rows.append([MK[m], pct(F[f"{m}_er_nano"]), pct(F[f"{m}_er_macro"]), pct(F[f"{m}_sov"], 0), top])
    table(s, 0.5, 1.75, 8.3, 3.0, ["Market", "Engagement per follower, nano", "Engagement per follower, macro",
                                   "Share of voice", "First creator on the shortlist"], rows,
          widths=[1.55, 1.45, 1.45, 1.15, 2.7], size=12)
    box(s, 0.5, 5.0, 8.3, 1.85, [
        [("Shortlist rule: ", dict(size=12, bold=True)), ("authenticity score of 85 or more, at least 60% of the audience in the "
         "market, nano or micro, ranked by expected engagements per euro of fee. Macro creators are chosen separately, for "
         "launches.", dict(size=12, color=MUTED))],
        [("Communities ", dict(size=12, bold=True)), ("come from the graph of mentions between creators (Louvain method). Each "
         "one is a market x niche, so briefs, codes and creators are planned per market.", dict(size=12, color=MUTED))]], margin=0)
    sid = F["suspect_ids"][0]
    box(s, 9.1, 1.75, 3.75, 5.1, [
        [("Excluded this month", dict(size=14, bold=True, color=RED))],
        [(f"{sid}: followers {sg(F['suspect_growth'])} in a single week, engagement per follower {pct(F['suspect_er'], 2)} "
          f"vs {pct(F['suspect_tier_er'], 1)} for its tier, most of its audience outside its market.", dict(size=13))],
        [("Out of the recommendations until its audience is audited (platform insights, comment review). "
          "The score ranks risk; it does not prove fraud.", dict(size=12, color=MUTED))]], fill=PANEL, margin=0.18)

    # 8. Attention points
    s = base(prs, 8, "Attention points",
             "One real alert (France stock-out), one false alarm (Spain) and four data fixes made before any comparison")
    box(s, 0.5, 1.75, 6.05, 5.05, [
        [("Business", dict(size=15, bold=True, color=PLUM))],
        [("France, stock-out. ", dict(size=13, bold=True, color=RED)),
         (f"Net sentiment fell to {F['fr_sent_now']:.0f} from {F['fr_sent_usual']:.0f} usually. Stock or availability: "
          f"{pct(F['fr_stock_now'], 0)} of negative comments vs {pct(F['fr_stock_before'], 0)} before. Replies need a restock date.",
          dict(size=13))],
        [("Spain, false alarm. ", dict(size=13, bold=True, color=GREEN)),
         (f"Engagement per follower is {sg(F['es_erf_change'])} since the March giveaway, which added {sg(F['es_follower_jump'])} "
          f"followers who do not engage. Engagement per reach is {sg(F['es_err_change'])}: the content is not the problem.",
          dict(size=13))]], fill=PANEL, margin=0.2)
    box(s, 6.8, 1.75, 6.05, 5.05, [
        [("Data fixed before reading the KPIs", dict(size=15, bold=True, color=PLUM))],
        [("Instagram views. ", dict(size=12.5, bold=True)),
         (f"The 'views' column changed definition in {pd_month(F['ig_break'])} (video plays only before, every display after): "
          f"x{F['ig_raw_ratio']} overnight. History rebuilt with impressions.", dict(size=12.5))],
        [("Italy, sponsored. ", dict(size=12.5, bold=True)),
         (f"{F['it_mislabelled']} boosted posts were exported as organic, making 'organic' reach look x{F['it_naive_ratio']} "
          "the other markets. Fixed with the ads export.", dict(size=12.5))],
        [("Germany, time zone. ", dict(size=12.5, bold=True)),
         (f"Export in UTC: the best hour looked like {F['de_best_naive']}:00; in local time it is {F['de_best_local']}:00.",
          dict(size=12.5))],
        [("Global posts. ", dict(size=12.5, bold=True)),
         (f"{F['dup_global_posts']} global posts sit in all five market exports; added up, group reach is "
          f"{sg(F['dup_overstatement'], 1)} too high. Counted once.", dict(size=12.5))]], fill=PANEL, margin=0.2)

    # 9. Recommendations by market
    s = base(prs, 9, "Recommendations by market", "Recommendations for November, market by market")
    rec = [
        ["France", f"Reply to stock questions with a restock date; pause paid support on the hero product until restock. "
                   f"Instagram: more short video (x{F['FR_short_vs_carousel']} vs carousel).",
         "Tutorial short videos with nano make-up creators", f"Net sentiment back to its usual level ({F['fr_sent_usual']:.0f})"],
        ["United Kingdom", f"Keep the format mix (short video x{F['UK_short_vs_carousel']} vs carousel). Share of voice "
                           f"{pct(F['UK_sov'], 0)}: seed the skincare creator community.",
         "Micro skincare creators, product seeding", "Share of voice among creators"],
        ["Germany", f"Instagram carousel first (short video x{F['DE_short_vs_carousel']}); publish at {F['de_best_local']}:00 local.",
         "Educational carousels on ingredients", f"Engagement rate by reach back to {pct(F['DE_er_reach_prev'])}"],
        ["Spain", f"Report engagement by reach ({pct(F['ES_er_reach'])}), not by followers, until giveaway followers settle. "
                  f"Short video x{F['ES_short_vs_carousel']}.", "Re-engagement series for giveaway followers",
         "Engagement rate by reach; follower churn"],
        ["Italy", f"Fix the sponsored flag at source ({F['it_mislabelled']} posts). Paid share of reach {pct(F['IT_paid_reach_share'], 0)}, "
                  f"cost per paid engagement €{F['IT_cpe']:.2f}.", "Lower paid share for two weeks, same budget elsewhere",
         "Organic reach rate; cost per engagement"],
    ]
    table(s, 0.5, 1.7, 12.3, 4.6, ["Market", "Keep / do", "Test next month", "KPI to watch"], rec,
          widths=[1.6, 5.9, 2.6, 2.2], size=12)
    box(s, 0.5, 6.4, 12.3, 0.5, [[("What we cannot conclude yet: ", dict(size=11.5, bold=True)),
                                  ("sentiment levels between languages (each lexicon has its own bias), and the effect of a "
                                   "format in a market before a test confirms it.", dict(size=11.5, color=MUTED))]], margin=0)

    # 10. Appendix: method
    s = base(prs, 10, "Appendix: method", "Method: same definitions everywhere, data checks first, numbers checked by script")
    box(s, 0.5, 1.75, 6.05, 5.05, [
        [("KPI definitions (identical in every market)", dict(size=14, bold=True, color=PLUM))],
        [("Reach: unique accounts that saw the content. Views: every display, all formats (Instagram history rebuilt). "
          "Engagements: likes + comments + shares + saves.", dict(size=12))],
        [("Engagement rate by reach (main KPI): engagements / reach, organic posts. Engagement rate by followers: read with "
          "follower growth.", dict(size=12))],
        [(f"Sentiment: rule-based lexicon in 5 languages, no AI model; {F['comments_scored']:,} comments scored. Agreement "
          f"with labels: {pct(F['lexicon_accuracy'], 0)} on simulated comments (lowest: German, {pct(F['lexicon_acc_min'], 0)}), "
          "optimistic for real comments.", dict(size=12))]], fill=PANEL, margin=0.2)
    box(s, 6.8, 1.75, 6.05, 5.05, [
        [("Checks before every report", dict(size=14, bold=True, color=PLUM))],
        [("1. Definition changes (platform changelogs)  2. Duplicated global posts  3. Export time zones  "
          "4. Sponsored posts hidden in organic  5. Small samples: at least 8 posts per rate  6. Follower jumps", dict(size=12))],
        [(f"Anomalies: robust z-score against the 6 previous months, flagged at |z| >= 3.5; {F['flags_total']} flags out of "
          f"{F['kpi_months_screened']:,} KPI-months this period, each with a decision (content, data or false signal).",
          dict(size=12))],
        [("Data: SIMULATED account (seed 42). Public context in the case study: Eurostat, Wikipedia page views, Mastodon. "
          "Full method: docs/METHODOLOGY.md.", dict(size=12, color=MUTED))]], fill=PANEL, margin=0.2)

    cp = prs.core_properties
    cp.author = cp.last_modified_by = cp.comments = cp.keywords = cp.subject = cp.category = ""
    cp.title = "Monthly social media report, October 2026 (SIMULATED)"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    assert len(prs.slides) == N_SLIDES
    print(f"saved {OUT.relative_to(ROOT)} ({len(prs.slides)} slides)")


def to_pdf():
    soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
    if not Path(soffice).exists():
        print("LibreOffice not found: no PDF export")
        return
    tmp = ROOT / ".tmp" / "lo-profile"
    subprocess.run([soffice, f"-env:UserInstallation={tmp.as_uri()}", "--headless", "--convert-to", "pdf", "--outdir",
                    str(OUT.parent), str(OUT)], check=True, capture_output=True, timeout=240)
    pdf = OUT.with_suffix(".pdf")
    from pypdf import PdfReader, PdfWriter
    r, w = PdfReader(str(pdf)), PdfWriter()
    for p in r.pages:
        w.add_page(p)
    w.add_metadata({"/Title": "Monthly social media report, October 2026 (SIMULATED)"})
    for k in ("/Producer", "/Creator", "/Author"):
        w._info.get_object().pop(k, None)
    with open(pdf, "wb") as fh:
        w.write(fh)
    print(f"saved {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
    to_pdf()
