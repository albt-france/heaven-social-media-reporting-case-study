"""8-page PDF case study (16:9): HTML + inline SVG charts, printed by headless Edge (generator reused from an earlier
case study). Numbers come from the pipeline outputs (data/processed/facts.json and tables); facts about Hopscotch Groupe
and heaven are quoted from their own publications (data/SOURCES.md).  Usage: python src/build_pdf.py
"""
from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
from jinja2 import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts as C  # noqa: E402
from fact_check import check_pptx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, PUB, DOCS, TMP = ROOT / "data" / "processed", ROOT / "data" / "public", ROOT / "docs", ROOT / ".tmp"
PDF = DOCS / "heaven_social_media_reporting_case_study.pdf"
F = json.loads((PROC / "facts.json").read_text(encoding="utf-8"))
rd = lambda n: pd.read_csv(PROC / f"{n}.csv")  # noqa: E731
MK = C.MK
FOOTER = "Independent case study based on public data · not affiliated with or endorsed by heaven or Hopscotch Groupe"
AI_NOTE = ("AI-assisted workflow: I used Claude, mainly to write scripts faster. I drove the project: I defined the questions, "
           "chose and validated the data sources, made the analytical decisions and checked every result.")
TITLE = "heaven: comparable social media reporting across markets, from metrics to recommendations"

CSS = """
@page { size: 16in 9in; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
body { font-family: 'Segoe UI', system-ui, sans-serif; color: #1F1D1A; background: #F2EFEA; }
.page { width: 1536px; height: 864px; padding: 28px 40px 16px; display: flex; flex-direction: column;
        background: #F2EFEA; page-break-after: always; overflow: hidden; position: relative }
header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; min-height: 54px }
h1 { font-size: 24px; font-weight: 700; line-height: 1.2; max-width: 1250px; letter-spacing: -0.2px }
.sub { color: #5A564F; font-size: 13.5px; margin-top: 5px; max-width: 1270px; line-height: 1.4 }
.tag { font-size: 11.5px; font-weight: 700; letter-spacing: .8px; border: 1px solid #C9C7BF; border-radius: 4px; padding: 4px 9px;
       white-space: nowrap; margin-top: 6px; background: #FFFFFF }
.tag.sim { color: #1C5CAB; border-color: #86B6EF } .tag.real { color: #0E7A55; border-color: #8FD3B8 } .tag.both { color: #52514E }
.kpis { display: grid; gap: 12px; margin-bottom: 12px }
.card { background: #FFFFFF; border: 1px solid #E3DED6; border-radius: 8px; padding: 12px 16px; display: flex;
        flex-direction: column; min-height: 0; overflow: hidden }
.kpi { padding: 11px 16px }
.klabel { font-size: 11px; font-weight: 700; color: #5A564F; letter-spacing: .5px; text-transform: uppercase }
.kval { font-size: 29px; font-weight: 700; margin-top: 2px; line-height: 1.15; color: #6B2D5C } .kval.red { color: #B02E2E } .kval.green { color: #0E7A55 }
.knote { font-size: 12px; color: #5A564F; margin-top: 3px; line-height: 1.35 }
.grid { display: grid; gap: 12px; flex: 1; min-height: 0 }
.card h3 { font-size: 13.5px; font-weight: 600; margin-bottom: 6px }
.ctag { font-size: 9.5px; font-weight: 700; letter-spacing: .6px; padding: 1px 5px; border-radius: 3px; margin-left: 6px; vertical-align: 1px }
.ctag.real { color: #0E7A55; border: 1px solid #8FD3B8 } .ctag.sim { color: #1C5CAB; border: 1px solid #86B6EF }
.body { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; font-size: 12.8px; line-height: 1.42 }
.body svg { width: 100%; height: 100% }
.body.text { display: block; overflow: hidden; color: #2B2A28 }
.body.text p { margin-bottom: 6px } .body.text ul { margin: 0 0 5px 17px } .body.text li { margin-bottom: 3px }
table { border-collapse: collapse; width: 100%; font-size: 11.8px }
th { text-align: left; color: #5A564F; font-weight: 600; border-bottom: 1px solid #C9C7BF; padding: 3px 5px }
td { padding: 3px 5px; border-bottom: 1px solid #EEEBE5; vertical-align: top } td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap }
td.red { color: #B02E2E; font-weight: 600 } td.green { color: #0E7A55; font-weight: 600 }
footer { font-size: 10.5px; color: #898781; margin-top: 8px }
b.plum { color: #6B2D5C } b.red { color: #B02E2E } b.green { color: #0E7A55 }
.flow { display: flex; gap: 7px; align-items: stretch; width: 100% }
.flow div.s { flex: 1; border: 1px solid #C9A6C0; background: #F7F0F5; border-radius: 6px; padding: 7px; font-size: 12px; text-align: center }
.flow div.s b { display: block; color: #6B2D5C; margin-bottom: 3px } .flow div.a { color: #898781; font-size: 18px; align-self: center }
.mono { font-family: Consolas, monospace; font-size: 11px; background: #F1EEE8; padding: 1px 4px; border-radius: 3px }
.ai { border-left: 3px solid #6B2D5C; padding: 6px 10px; background: #F7F0F5; font-size: 12.5px; margin-top: 4px }
.q { display: grid; grid-template-columns: 22px 1fr; gap: 9px 6px; font-size: 14px; line-height: 1.45 }
table.big { font-size: 14px } table.big td { padding: 8px 6px } .q b { color: #6B2D5C }
"""

PAGE = Template("""
<section class="page">
  <header><div><h1>{{ p.title }}</h1>{% if p.subtitle %}<p class="sub">{{ p.subtitle }}</p>{% endif %}</div>
  {% if p.tag %}<div class="tag {{ p.tag_class }}">{{ p.tag }}</div>{% endif %}</header>
  {% if p.kpis %}<div class="kpis" style="grid-template-columns: repeat({{ p.kpis|length }}, 1fr)">
    {% for k in p.kpis %}<div class="card kpi"><div class="klabel">{{ k[0] }}</div><div class="kval {{ k[3] if k|length > 3 else '' }}">{{ k[1] }}</div><div class="knote">{{ k[2] }}</div></div>{% endfor %}
  </div>{% endif %}
  <div class="grid" style="grid-template-columns: {{ p.cols }}; grid-template-rows: {{ p.rows }}">
    {% for c in p.cards %}<div class="card" style="grid-column: {{ c.col }}; grid-row: {{ c.row }}">
      {% if c.title %}<h3>{{ c.title }}{% if c.tag %}<span class="ctag {{ 'sim' if c.tag == 'SIMULATED' else 'real' }}">{{ c.tag }}</span>{% endif %}</h3>{% endif %}<div class="body {{ 'text' if c.text else '' }}">{{ c.body }}</div></div>{% endfor %}
  </div>
  <footer>{{ p.footer }} · {{ foot }}</footer>
</section>""")


def card(title, body, col="auto", row="auto", text=False, tag=None):
    return dict(title=title, body=body, col=col, row=row, text=text, tag=tag)


def flow(steps):
    return '<div class="flow">' + '<div class="a">→</div>'.join(f'<div class="s"><b>{a}</b>{b}</div>' for a, b in steps) + "</div>"


def esc(s) -> str:
    return html.escape(str(s))


def tbl(header, rows, num=()):
    h = "".join(f'<th class="{"n" if i in num else ""}">{x}</th>' for i, x in enumerate(header))
    b = "".join("<tr>" + "".join(f'<td class="{"n" if i in num else ""}">{x}</td>' for i, x in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"


def pct(v, d=1):
    return f"{v:.{d}f}%"


def build_pages(n_checked: int) -> list[dict]:
    mk = list(MK)
    km, k, w = rd("kpi_month_market"), rd("kpi_month_mp"), pd.read_csv(PUB / "wikipedia_pageviews.csv")
    e, m = pd.read_csv(PUB / "eurostat_social_use.csv"), pd.read_csv(PUB / "mastodon_sample.csv")
    m12 = m[m.date >= str(pd.Timestamp(F["collected_on"]) - pd.DateOffset(months=12))[:10]]
    net, cs, comm = rd("creator_network"), rd("creator_scores"), rd("communities")
    pages = []

    # 0. Overview
    q = [("Can one KPI mean the same thing in every market and on every platform?",
          f"Yes, after four corrections: definitions, sponsored posts, time zones, duplicates. Without them group reach is {F['dup_overstatement']}% too high."),
         ("What does a monthly client report look like?", f"10 slides, 3 messages, KPIs by market, recommendations by market; {n_checked} numbers checked by script."),
         ("Which signals are real and which are false alarms?", f"{F['events_found']} of 8 hidden situations found, including a false alarm that is correctly not raised."),
         ("How do influencer communities differ by market?", f"{F['communities']} communities, each anchored in one market: influence is planned market by market."),
         ("What do public data add?", "Interest by language and social-network use by country differ: market weights cannot be copied from one country to another.")]
    pages.append(dict(
        title=TITLE, tag="PUBLIC DATA + SIMULATED", tag_class="both",
        subtitle="Public data on Hopscotch Groupe and on beauty brands' public signals (Wikipedia interest, Eurostat, Mastodon, Bluesky), "
                 "plus a simulated, calibrated multi-market beauty retail account, turned into a harmonised KPI framework, a monthly "
                 "client report, an influencer community analysis and a reusable methodology.",
        kpis=[("Hidden situations found", f"{F['events_found']} / 8", "incl. the false alarm, correctly not raised"),
              ("Numbers checked in the report", f"{n_checked}", "every number traced to the fact sheet"),
              ("Group reach overstated", f"+{F['dup_overstatement']}%", "if global posts are added up market by market", "red"),
              ("Creator communities", f"{F['communities']}", "each anchored in a single market")],
        cols="1.25fr 1fr", rows="1fr 1fr",
        cards=[card("Five questions, five answers", '<div class="q">' + "".join(f"<b>{i + 1}</b><div><b>{a}</b><br>{b}</div>" for i, (a, b) in enumerate(q)) + "</div>",
                    row="1 / span 2", text=True),
               card("Recommendations by market (October 2026, simulated account)", '<table class="big">' + tbl(["Market", "Main lever"], [
                   ["France", "answer stock questions with a restock date; more short video"],
                   ["United Kingdom", "seed the skincare creator community (low share of voice)"],
                   ["Germany", "carousel first on Instagram; post in the evening, local time"],
                   ["Spain", "read engagement by reach: the follower drop is a giveaway effect"],
                   ["Italy", "fix the sponsored flag at source; lower the paid share"]])[7:], text=True),
               card("Method and deliverables", flow([("Collect", "public APIs, simulated exports"), ("Harmonise", "SQL, 4 corrections"),
                                                     ("Detect", "robust z + rules"), ("Explain", "themes, communities"),
                                                     ("Report", "PowerPoint, dashboard, PDF")]) +
                    '<p style="margin-top:10px">Deliverables: monthly client report (PowerPoint, 10 slides), HTML dashboard, one notebook, '
                    'KPI framework, methodology, influencer guide and data-quality checklist.</p>', text=True)],
        footer="Sources: see page 7"))

    # 1. heaven, Hopscotch and the social beauty market
    pages.append(dict(
        title="heaven brings social and influence expertise inside a listed communication group; social use and beauty interest differ by market",
        tag="PUBLIC DATA", tag_class="real",
        subtitle="Facts about Hopscotch Groupe and heaven as stated in their own publications (no estimate added). Market context from Eurostat and Wikipedia.",
        cols="1fr 1fr 1fr", rows="1fr 1fr",
        cards=[card("Hopscotch Groupe, as stated by Hopscotch Groupe", tbl(["", ""], [
                   ["Listing", "Euronext Growth Paris"],
                   ["2025 revenue / gross margin", "€270.8M / €98.8M (-5.7%)"],
                   ["H1 2026 revenue / gross profit", "€116.7M / €43.0M (-6.3%); France stable"],
                   ["People and offices", "1,200+ employees, half abroad; 40 offices on 5 continents"],
                   ["Businesses", "Events, Digital, PR and Influence"],
                   ["2030 ambition", "€200M gross margin, 15% operating income"]]) +
                   '<p style="margin-top:6px;font-size:11px;color:#898781">H1 2026 results press release (30 Sep 2026); 2025 annual results release.</p>',
                   text=True, tag="PUBLIC DATA"),
               card("heaven, as stated by heaven and in the job posting", "<ul>"
                    "<li>Digital advertising agency of the group (\"Digital and Marketing\"), team of 80+ in Paris.</li>"
                    "<li>Offers: social media and brand content, influence, digital studio, media, consulting with social data analysis.</li>"
                    "<li>Says it pioneered influence marketing in France and ran a French influencer network as early as 2006.</li>"
                    "<li>Clients it names on its site include Microsoft, Sony, Samsung, Danone and Disney; the job posting names Crunchyroll, Carte Noire and Deliveroo.</li>"
                    "<li>The mission: social reporting and influencer analysis for a confidential beauty retail client, across markets.</li></ul>",
                    text=True, tag="PUBLIC DATA"),
               card("Individuals using social networks, latest year (Eurostat)", C.eurostat_bars(e), tag="PUBLIC DATA"),
               card("Sunscreen interest by language edition (Wikipedia views per million)", C.topic_season(w, "Sunscreen"), col="1 / span 2", tag="PUBLIC DATA"),
               card("What it means for the reporting", f"<p>Social-network use ranges from {F['eurostat_IT']}% (Italy) to {F['eurostat_FR']}% (France) in 2025; "
                    f"the UK figure ({F['eurostat_UK']}%) dates from {F['eurostat_UK_year']}, its last year in Eurostat.</p>"
                    f"<p>Seasonal peaks differ: sunscreen interest moves {F['wiki_sunscreen_peak_ratio_min']}x to {F['wiki_sunscreen_peak_ratio_max']}x "
                    "between low and high months depending on the language. A month is compared with the same market's history, not with "
                    "another country.</p>", text=True)],
        footer="Sources: Hopscotch Groupe investor relations; heaven.paris; Eurostat isoc_ci_ac_i (I_IUSNET); Wikimedia Pageviews API, collected 17 Nov 2026"))

    # 2. Public brand panel
    lead = ", ".join(f"{lang}: {F[f'wiki_lead_{lang}']}" for lang in ["fr", "en", "de", "es", "it"])
    pages.append(dict(
        title="Public signals on beauty brands differ by language; post-level performance needs platform access",
        tag="PUBLIC DATA", tag_class="real",
        subtitle="Panel of 10 beauty product brands (no retailer). Without a YouTube API key in this version, the panel relies on Wikipedia "
                 "interest, Mastodon public hashtags and a Bluesky account check; the YouTube collector is ready (src/fetch_youtube.py).",
        cols="1.15fr 1fr", rows="1fr 1fr",
        cards=[card("Brand interest by language: Wikipedia page views per million views of the edition (monthly average)", C.brand_heat(w),
                    row="1 / span 2", tag="PUBLIC DATA"),
               card("Mastodon: share of beauty posts by theme (last 12 months)", C.mastodon_bars(m12), tag="PUBLIC DATA"),
               card("What the public panel shows, and its limits", f"<p><b class='green'>Leaders differ by language</b>: {esc(lead)} "
                    f"({F['wiki_brands_all5']} brands have an article in all five editions).</p>"
                    f"<p><b class='green'>Real listening sample</b>: {F['mastodon_posts_12m']:,} posts in 12 months on {F['mastodon_tags']} hashtags; "
                    f"median interactions {F['mastodon_median_interactions']:.0f}; {pct(100 * F['mastodon_share_en'], 0)} in English. "
                    "It tests the pipeline, it does not represent beauty consumers.</p>"
                    f"<p><b class='green'>Bluesky</b>: {F['bluesky_brands_verified']} of {F['bluesky_brands_checked']} panel brands use their own domain as "
                    "a handle, so no official brand feed could be analysed there.</p>"
                    "<p>Instagram, TikTok, Facebook and X are not scraped (terms of use, login required).</p>", text=True)],
        footer="Sources: Wikimedia Pageviews API (CC0); mastodon.social public API (aggregates only, no text or account kept); Bluesky public AppView; collected 17 Nov 2026"))

    # 3. One KPI, one meaning
    dq_s = rd("dq_sponsored").set_index("market")
    pages.append(dict(
        title="One KPI, one meaning, in every market: four corrections come before any comparison",
        tag="SIMULATED", tag_class="sim",
        subtitle="Fictitious account, 5 markets x 5 platforms, June 2025 - October 2026. The harmonised framework (docs/KPI_FRAMEWORK.md) maps each "
                 "platform's native metrics to one definition; sql/01_harmonise.sql applies it.",
        cols="1fr 1fr 1fr", rows="1fr 1fr",
        cards=[card("Harmonised definitions", tbl(["KPI", "Definition"], [
                   ["Reach", "unique accounts that saw the content"], ["Views", "every display, all formats"],
                   ["Engagements", "likes + comments + shares + saves"], ["ER by reach", "engagements / reach, organic posts (main KPI)"],
                   ["ER by followers", "engagements / followers; read with follower growth"], ["Net sentiment", "% positive - % negative comments"],
                   ["Share of voice", "brand mentions / all brand mentions by creators"], ["Cost per engagement", "spend / paid engagements"]]),
                   row="1 / span 2", text=True),
               card(f"1. Definition change: Instagram 'views' x{F['ig_raw_ratio']} overnight", C.ig_views(k), tag="SIMULATED"),
               card(f"2. Duplicates: group reach +{F['dup_overstatement']}% if exports are added up", C.group_reach(rd("group_totals")), tag="SIMULATED"),
               card(f"3. Time zone: Germany exported in UTC (best hour {F['de_best_local']}:00 local, not {F['de_best_naive']}:00)", C.hours(rd("posts_h")), tag="SIMULATED"),
               card("4. Sponsored posts hidden in organic, and the real-world case", f"<p>Italy: <b class='red'>{F['it_mislabelled']}</b> posts labelled organic "
                    f"have ad spend; 'organic' reach rate looked x{F['it_naive_ratio']} the other markets. Rule: sponsored = tool label or spend &gt; 0.</p>"
                    "<p><b>Real case behind correction 1</b>: Meta introduced a <span class='mono'>views</span> metric and deprecated "
                    "<span class='mono'>plays</span> and <span class='mono'>impressions</span> for Instagram insights (Graph API v22.0, effective "
                    "21 April 2025). TikTok's account <span class='mono'>video_views</span> counts organic and paid together. "
                    "Any history crossing such a change must be rebuilt before it is compared.</p>", text=True)],
        footer="SIMULATED data (seed 42) · real definition change: Meta for Developers changelogs; TikTok API for Business docs"))

    # 4. The monthly report
    rows = [[MK[x], f"{F[f'{x}_reach_m']}M", f"{F[f'{x}_reach_mom']:+.0f}%", pct(F[f'{x}_er_reach']), f"{F[f'{x}_net_sent']:+.0f}",
             pct(F[f'{x}_sov'], 0)] for x in mk]
    pages.append(dict(
        title="The October report: France faces a stock-out, Spain's drop is a false alarm, formats work differently by market",
        tag="SIMULATED", tag_class="sim",
        subtitle=f"Extract of the 10-slide client report (reports/monthly_report_oct2026.pptx). {F['flags_total']} flags out of "
                 f"{F['kpi_months_screened']:,} KPI-months screened; each flag gets a decision: content issue, data issue or false signal.",
        cols="1.05fr 1fr 1fr", rows="1fr 1fr",
        cards=[card("KPIs by market, October 2026", tbl(["Market", "Reach", "vs Sept", "ER by reach", "Net sent.", "Share of voice"], rows, num=(1, 2, 3, 4, 5)) +
                    f"<p style='margin-top:8px'>Group reach {F['group_reach_dedup_m']}M, each post counted once.</p>", text=True, tag="SIMULATED"),
               card("Engagement rate by reach, organic, by market", C.er_lines(km), col="2 / span 2", tag="SIMULATED"),
               card(f"Spain: ER per follower {F['es_erf_change']:+.0f}%, ER per reach {F['es_err_change']:+.0f}%: a giveaway effect, not content",
                    C.false_signal(k), tag="SIMULATED"),
               card(f"France: net sentiment {F['fr_sent_now']:.0f} in October vs {F['fr_sent_usual']:.0f} usually (stock-out)", C.fr_sentiment(rd("comments_scored")),
                    tag="SIMULATED"),
               card("Instagram: short video vs carousel (ER by reach, 95% interval)", C.format_ratio(rd("format_by_market")), tag="SIMULATED")],
        footer="SIMULATED data (seed 42) · sentiment: rule-based lexicon in 5 languages, no LLM"))

    # 5. Influencer communities
    sid = F["suspect_ids"][0]
    prof = rd("market_profiles").set_index("market")
    pages.append(dict(
        title=f"Influencer communities are local: {F['communities']} communities, each anchored in one market, and one creator excluded",
        tag="SIMULATED", tag_class="sim",
        subtitle=f"{F['creators']} anonymous creators (creator_001...), mention graph analysed with networkx: Louvain communities, PageRank "
                 "(influence), betweenness (bridges). Authenticity score explained in docs/INFLUENCER_ANALYSIS_GUIDE.md.",
        cols="1.45fr 1fr 1fr", rows="1fr 1fr",
        cards=[card("Mention graph: creators coloured by market, size = PageRank", C.network(net), row="1 / span 2", tag="SIMULATED"),
               card("Engagement per follower falls with audience size", C.tier_box(cs), tag="SIMULATED"),
               card(f"Excluded: {sid}, +{F['suspect_growth']:.0f}% followers in one week", C.suspect_curve(pd.read_csv(ROOT / 'data' / 'simulated' / 'creators_weekly.csv'), sid),
                    tag="SIMULATED"),
               card("Communities", tbl(["#", "Size", "Market", "Niche", "Median ER"],
                                       [[r.community, r.size, MK[r.main_market], r.main_niche, pct(100 * r.median_er)] for r in comm.itertuples()],
                                       num=(1, 4)), text=True),
               card("Profiles by market", tbl(["Market", "Nano ER", "Macro ER", "Share of voice"],
                                              [[MK[x], pct(100 * prof.loc[x, 'median_er_nano']), pct(100 * prof.loc[x, 'median_er_macro']),
                                                pct(100 * prof.loc[x, 'share_of_voice_3m'], 0)] for x in mk], num=(1, 2, 3)) +
                    f"<p style='margin-top:6px'>{sid}: engagement per follower {F['suspect_er']}% vs {F['suspect_tier_er']}% for its tier and most "
                    "of its audience abroad: out of recommendations until audited.</p>", text=True)],
        footer="SIMULATED data (seed 42) · no real creator: names never collected, ids only"))

    # 6. Recommendations
    rec = [["France", f"Reply to stock questions with a restock date; pause paid support on the hero product. More short video (x{F['FR_short_vs_carousel']}).",
            "Tutorial short videos with nano make-up creators", "Net sentiment back to usual"],
           ["United Kingdom", f"Keep the format mix (x{F['UK_short_vs_carousel']}). Seed the skincare community: share of voice {pct(F['UK_sov'], 0)}.",
            "Micro skincare creators", "Share of voice"],
           ["Germany", f"Carousel first on Instagram (short video x{F['DE_short_vs_carousel']}); post at {F['de_best_local']}:00 local.",
            "Educational carousels on ingredients", "ER by reach"],
           ["Spain", f"Report ER by reach ({pct(F['ES_er_reach'])}), not by followers, after the giveaway.", "Re-engagement series", "ER by reach, churn"],
           ["Italy", f"Fix the sponsored flag at source; paid share of reach {pct(F['IT_paid_reach_share'], 0)}.", "Lower paid share for two weeks",
            "Organic reach rate, cost per engagement"]]
    pages.append(dict(
        title="Recommendations are set market by market: what to do, what to test next, and what we cannot conclude",
        tag="SIMULATED + PUBLIC DATA", tag_class="both",
        subtitle="Recommendations come from the simulated account; public data only set the context (social use, seasonality, interest by language).",
        cols="1.7fr 1fr", rows="1fr 1fr",
        cards=[card("Levers by market (simulated account, October 2026)", tbl(["Market", "Keep / do", "Test next", "KPI to watch"], rec).replace("<table>", '<table class="big">'),
                    row="1 / span 2", text=True, tag="SIMULATED"),
               card("How tests are run", "<ul><li>One change at a time, per market, 4 weeks, with the previous 3 months as baseline.</li>"
                    "<li>Formats: success only if the gap is at least 15% and the 95% interval excludes no effect.</li>"
                    "<li>Creators: shortlist = authenticity score of 85 or more, 60%+ local audience, ranked by expected engagements per euro.</li></ul>", text=True),
               card("What we cannot conclude", "<ul><li>Sentiment <i>levels</i> across languages: each lexicon has its own bias; only changes within a market are read.</li>"
                    "<li>Real brand performance on Instagram or TikTok: no access without the account owner (public data only here).</li>"
                    "<li>Seasonality for the client: public interest curves show it exists, the client's own history must confirm it.</li></ul>", text=True)],
        footer="SIMULATED data (seed 42) + PUBLIC DATA context (Eurostat, Wikipedia)"))

    # 7. Methods
    pages.append(dict(
        title="Methods, limits and AI note: every source dated, every number traced, everything re-runs without a key",
        tag="PUBLIC DATA + SIMULATED", tag_class="both",
        subtitle="Collection: official APIs and public pages only, robots.txt respected, low frequency, neutral User-Agent; no scraping of Instagram, TikTok, Facebook or X.",
        cols="1.25fr 1fr", rows="1fr 1fr",
        cards=[card("Sources (collected 17 Nov 2026)", tbl(["Source", "Use", "Terms"], [
                   ["Hopscotch Groupe investor relations (PDFs)", "group facts, as stated", "public"],
                   ["heaven.paris; job posting", "agency facts, as stated", "public"],
                   ["Eurostat isoc_ci_ac_i (I_IUSNET)", "social-network use by country", "CC BY 4.0"],
                   ["Wikimedia Pageviews API", "interest by language", "CC0"],
                   ["mastodon.social public hashtags", "listening sample, aggregates only", "API terms"],
                   ["Bluesky public AppView", "official brand accounts check", "API terms"],
                   ["Meta, TikTok developer docs", "metric definition changes", "cited"],
                   ["Simulated account (seed 42)", "the reporting mission end to end", "SIMULATED"]]), row="1 / span 2", text=True),
               card("Pipeline and checks", "<p><span class='mono'>fetch_public.py</span> → <span class='mono'>simulate.py</span> → "
                    "<span class='mono'>run_sql.py</span> (DuckDB, 4 SQL files) → detection, communities, fact sheet → "
                    "<span class='mono'>build_report_pptx.py</span> → <span class='mono'>pytest</span> → notebook, dashboard, PDF.</p>"
                    f"<p>Number checker: {n_checked} numbers in the client report traced to the fact sheet (market and subject included). "
                    f"Lexicon: {pct(F['lexicon_accuracy'], 0)} agreement on simulated comments (lowest German, {pct(F['lexicon_acc_min'], 0)}), optimistic for real comments.</p>",
                    text=True),
               card("Limits and AI note", "<ul><li>No access to real Instagram or TikTok data; the account, comments and creators are simulated.</li>"
                    "<li>Mastodon volumes are small and not representative; the English Wikipedia is global, not a UK measure; UK Eurostat data stop in 2020.</li>"
                    "<li>No professional social-listening tool used; the same pipeline would read its exports.</li></ul>"
                    f"<div class='ai'>{esc(AI_NOTE)}</div>", text=True)],
        footer="Licences: Eurostat CC BY 4.0, Wikimedia CC0; Hopscotch Groupe and heaven facts quoted as stated, with links in data/SOURCES.md"))
    return pages


def edge() -> str:
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if Path(p).exists():
            return p
    return shutil.which("msedge") or "msedge"


def wait_file(path: Path, timeout=120):
    last, t0 = -1, time.time()
    while time.time() - t0 < timeout:
        if path.exists() and path.stat().st_size > 0 and path.stat().st_size == last:
            return
        last = path.stat().st_size if path.exists() else -1
        time.sleep(1.5)
    raise TimeoutError(f"{path} not produced")


def clean_pdf(path: Path):
    """Metadata reduced to the title: no author, tool or path."""
    from pypdf import PdfReader, PdfWriter
    r, w = PdfReader(str(path)), PdfWriter()
    for pg in r.pages:
        w.add_page(pg)
    w.add_metadata({"/Title": TITLE})
    for k in ("/Producer", "/Creator", "/Author"):
        w._info.get_object().pop(k, None)
    tmp = path.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as fh:
        w.write(fh)
    tmp.replace(path)


def main():
    TMP.mkdir(exist_ok=True)
    (DOCS / "img").mkdir(parents=True, exist_ok=True)
    prof = TMP / "edge-profile"
    n_checked = sum(len(r.findings) for _, r in check_pptx())
    pages = build_pages(n_checked)
    head = f"<!doctype html><html><head><meta charset='utf-8'><title>heaven case study</title><style>{CSS}</style></head><body>"
    sections = [PAGE.render(p=p, foot=FOOTER) for p in pages]
    src = TMP / "report.html"
    src.write_text(head + "".join(sections) + "</body></html>", encoding="utf-8")
    PDF.unlink(missing_ok=True)
    subprocess.run([edge(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                    f"--user-data-dir={prof}", f"--print-to-pdf={PDF}", src.as_uri()], check=True, capture_output=True, timeout=180)
    wait_file(PDF)
    clean_pdf(PDF)
    names = ["00_overview", "01_heaven_market", "02_public_panel", "03_one_kpi", "04_monthly_report", "05_communities",
             "06_recommendations", "07_methods"]
    for name, sec in zip(names, sections):
        one = TMP / f"{name}.html"
        one.write_text(head.replace("page-break-after: always", "") + sec + "</body></html>", encoding="utf-8")
        out = DOCS / "img" / f"{name}.png"
        out.unlink(missing_ok=True)
        subprocess.run([edge(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                        "--window-size=1536,864", f"--screenshot={out}", one.as_uri()], check=True, capture_output=True, timeout=120)
        wait_file(out)
    from pypdf import PdfReader
    print("PDF:", PDF.relative_to(ROOT), f"({PDF.stat().st_size // 1024} KB, {len(PdfReader(str(PDF)).pages)} pages)")


if __name__ == "__main__":
    main()
