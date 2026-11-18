"""Self-contained HTML dashboard (Plotly embedded, no server, no internet needed): dashboard/social_dashboard.html

Usage: python src/build_dashboard.py   (after src/run_sql.py)
Tabs: Overview by market (filters) · Content performance · Communities & creators · Public brand panel (PUBLIC DATA).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
PROC, PUB = ROOT / "data" / "processed", ROOT / "data" / "public"
OUT = ROOT / "dashboard" / "social_dashboard.html"


def recs(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", double_precision=5))


def data() -> dict:
    p = pd.read_csv(PROC / "posts_h.csv")
    p = p[p.in_market_kpis]
    p["org_eng"] = p.engagements.where(~p.is_sponsored, 0)
    p["org_reach"] = p.reach.where(~p.is_sponsored, 0)
    mp = p.groupby(["month", "market", "platform"], as_index=False).agg(
        posts=("post_id", "count"), reach=("reach", "sum"), eng=("engagements", "sum"), org_eng=("org_eng", "sum"),
        org_reach=("org_reach", "sum"), spend=("spend_eur", "sum"))
    k = pd.read_csv(PROC / "kpi_month_mp.csv")[["month", "market", "platform", "followers_end", "net_sentiment", "comments_scored"]]
    mp = mp.merge(k, on=["month", "market", "platform"], how="left")
    org = p[~p.is_sponsored]
    fmt = org.groupby(["market", "platform", "format"], as_index=False).agg(eng=("engagements", "sum"), reach=("reach", "sum"), posts=("post_id", "count"))
    theme = org.groupby(["market", "platform", "theme"], as_index=False).agg(eng=("engagements", "sum"), reach=("reach", "sum"))
    hl = org.groupby(["market", "platform", "local_hour"], as_index=False).agg(eng=("engagements", "sum"), reach=("reach", "sum"), posts=("post_id", "count"))
    hx = org.groupby(["market", "platform", "hour_as_exported"], as_index=False).agg(eng=("engagements", "sum"), reach=("reach", "sum"), posts=("post_id", "count"))
    net = pd.read_csv(PROC / "creator_network.csv")
    w = pd.read_csv(PUB / "wikipedia_pageviews.csv")
    full = w.groupby(["kind", "entity"]).lang.nunique()
    w = w[w.set_index(["kind", "entity"]).index.isin(full[full == 5].index)]
    wb = w[w.kind == "brand"].groupby(["entity", "lang"], as_index=False).per_million.mean()
    wt = w[w.kind == "topic"].groupby(["entity", "lang", "month"], as_index=False).per_million.sum().astype({"month": str})
    e = pd.read_csv(PUB / "eurostat_social_use.csv").sort_values("year").groupby("geo", as_index=False).last()
    m = pd.read_csv(PUB / "mastodon_sample.csv")
    th = [c for c in m.columns if c.startswith("theme_")]
    mth = (m[th].mean() * 100).rename(lambda c: c.replace("theme_", "")).round(1).reset_index()
    mth.columns = ["theme", "share"]
    return dict(mp=recs(mp), fmt=recs(fmt), theme=recs(theme), hl=recs(hl), hx=recs(hx),
                net=recs(net[["creator_id", "x", "y", "market", "tier", "niche", "community", "pagerank", "er_followers",
                              "authenticity_score", "followers"]]),
                comm=recs(pd.read_csv(PROC / "communities.csv")), short=recs(pd.read_csv(PROC / "creator_shortlist.csv")),
                det=recs(pd.read_csv(PROC / "detection.csv")[["event", "where", "evidence", "decision"]]),
                wb=recs(wb), wt=recs(wt), eu=recs(e[["geo", "year", "pct_individuals"]]), mth=recs(mth),
                facts=json.loads((PROC / "facts.json").read_text(encoding="utf-8")))


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Social reporting dashboard</title>
<style>
:root { --bg:#F4F2EE; --card:#FFFFFF; --ink:#1F1D1A; --muted:#6B6760; --line:#E3DED6; --plum:#6B2D5C; --blue:#1C5CAB; --green:#0E7A55; }
* { box-sizing:border-box } body { margin:0; font-family:'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--ink); }
header { padding:18px 24px 6px } h1 { font-size:21px; margin:0 } .sub { color:var(--muted); font-size:13px; margin-top:4px }
nav { display:flex; gap:6px; padding:8px 24px; flex-wrap:wrap } nav button { border:1px solid var(--line); background:var(--card);
 padding:7px 13px; border-radius:6px; cursor:pointer; font:inherit; font-size:13.5px } nav button.on { background:var(--plum); color:#fff; border-color:var(--plum) }
main { padding:6px 24px 24px } .tab { display:none } .tab.on { display:block }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(420px, 1fr)); gap:12px }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; min-width:0 }
.card h2 { font-size:14px; margin:0 0 6px } .kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px,1fr)); gap:10px; margin-bottom:12px }
.k .l { font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:.4px } .k .v { font-size:24px; font-weight:700; margin-top:2px }
.tag { font-size:10px; font-weight:700; padding:2px 6px; border-radius:3px; margin-left:6px; vertical-align:2px }
.sim { color:var(--blue); border:1px solid #86B6EF } .real { color:var(--green); border:1px solid #8FD3B8 }
.filters { display:flex; gap:10px; align-items:center; margin-bottom:10px; flex-wrap:wrap; font-size:13px }
select { font:inherit; padding:4px 6px } table { border-collapse:collapse; width:100%; font-size:12.5px }
th, td { text-align:left; padding:4px 6px; border-bottom:1px solid var(--line); vertical-align:top } .note { font-size:12px; color:var(--muted) }
footer { padding:0 24px 18px; font-size:11.5px; color:var(--muted) }
@media (max-width:520px) { .grid { grid-template-columns:1fr } header, nav, main, footer { padding-left:16px; padding-right:16px } }
</style><script>__PLOTLY__</script></head><body>
<header><h1>Comparable social media reporting across markets</h1>
<div class="sub">Fictitious global beauty retailer, 5 markets x 5 platforms, June 2025 - October 2026 <span class="tag sim">SIMULATED</span>
 · public brand panel <span class="tag real">PUBLIC DATA</span></div></header>
<nav><button data-t="t1" class="on">Overview by market</button><button data-t="t2">Content performance</button>
<button data-t="t3">Communities &amp; creators</button><button data-t="t4">Public brand panel</button></nav>
<main>
<section id="t1" class="tab on">
 <div class="filters">Market <select id="fm"></select> Platform <select id="fp"></select>
  <span class="note">KPIs harmonised: views = every display; engagement rate by reach on organic posts; global posts counted once.</span></div>
 <div class="kpis" id="kp"></div>
 <div class="grid"><div class="card"><h2>Engagement rate by reach, organic <span class="tag sim">SIMULATED</span></h2><div id="c1" style="height:320px"></div></div>
 <div class="card"><h2>Reach, organic vs sponsored <span class="tag sim">SIMULATED</span></h2><div id="c2" style="height:320px"></div></div>
 <div class="card"><h2>Net sentiment (% positive - % negative) <span class="tag sim">SIMULATED</span></h2><div id="c3" style="height:300px"></div></div>
 <div class="card"><h2>What the monthly review found <span class="tag sim">SIMULATED</span></h2><div id="det" style="max-height:300px; overflow:auto"></div></div></div>
</section>
<section id="t2" class="tab">
 <div class="filters">Platform <select id="fp2"></select> <span class="note">Organic posts, whole period.</span></div>
 <div class="grid"><div class="card"><h2>Engagement rate by reach, format x market <span class="tag sim">SIMULATED</span></h2><div id="c4" style="height:330px"></div></div>
 <div class="card"><h2>Engagement rate by reach, by theme <span class="tag sim">SIMULATED</span></h2><div id="c5" style="height:330px"></div></div>
 <div class="card"><h2>Best time to post: local time vs as exported <span class="tag sim">SIMULATED</span></h2>
  <div class="filters">Market <select id="fm3"></select></div><div id="c6" style="height:300px"></div>
  <div class="note">Germany's export is in UTC: read in export time, the evening peak looks earlier than it is.</div></div></div>
</section>
<section id="t3" class="tab">
 <div class="grid"><div class="card"><h2>Mention graph: creators by community <span class="tag sim">SIMULATED</span></h2><div id="c7" style="height:440px"></div>
  <div class="note">Size = PageRank. Black circle = excluded (authenticity score below 50).</div></div>
 <div class="card"><h2>Engagement per follower by tier <span class="tag sim">SIMULATED</span></h2><div id="c8" style="height:300px"></div>
  <h2 style="margin-top:8px">Authenticity score</h2><div id="c9" style="height:200px"></div></div>
 <div class="card"><h2>Communities <span class="tag sim">SIMULATED</span></h2><div id="tc"></div></div>
 <div class="card"><h2>Shortlist by market <span class="tag sim">SIMULATED</span></h2><div id="ts"></div></div></div>
</section>
<section id="t4" class="tab">
 <div class="grid"><div class="card"><h2>Individuals using social networks, % (Eurostat) <span class="tag real">PUBLIC DATA</span></h2><div id="c10" style="height:300px"></div>
  <div class="note">Eurostat isoc_ci_ac_i, I_IUSNET. UK: last year covered is 2020.</div></div>
 <div class="card"><h2>Brand interest by language: Wikipedia views per million <span class="tag real">PUBLIC DATA</span></h2><div id="c11" style="height:300px"></div>
  <div class="note">Monthly average, June 2025 - October 2026; brands with an article in all 5 editions. The English edition is global.</div></div>
 <div class="card"><h2>Seasonality of beauty topics by language <span class="tag real">PUBLIC DATA</span></h2>
  <div class="filters">Topic <select id="ft"></select></div><div id="c12" style="height:280px"></div></div>
 <div class="card"><h2>Mastodon sample: share of posts by theme <span class="tag real">PUBLIC DATA</span></h2><div id="c13" style="height:280px"></div>
  <div class="note">Public hashtag timelines, small volumes, aggregates only. YouTube panel: needs an API key (not run in this version).</div></div></div>
</section>
</main>
<footer>Independent case study based on public data · not affiliated with or endorsed by heaven or Hopscotch Groupe. SIMULATED data describe a fictitious account.</footer>
<script>
const D = __DATA__;
const MK = {FR:'France', UK:'United Kingdom', DE:'Germany', ES:'Spain', IT:'Italy'}, COL = {FR:'#6B2D5C', UK:'#1C5CAB', DE:'#B88A4E', ES:'#1E7A52', IT:'#B02E2E'};
const PL = ['Instagram','TikTok','Facebook','X','YouTube'];
const LAY = (o={}) => Object.assign({margin:{l:48,r:12,t:10,b:40}, font:{family:'Segoe UI', size:12, color:'#1F1D1A'}, paper_bgcolor:'rgba(0,0,0,0)',
  plot_bgcolor:'rgba(0,0,0,0)', xaxis:{gridcolor:'#E3DED6'}, yaxis:{gridcolor:'#E3DED6'}, legend:{orientation:'h', y:-0.2}}, o);
const CFG = {displayModeBar:false, responsive:true};
const fmt = (v, d=1) => v==null||isNaN(v) ? '-' : v.toLocaleString('en-GB', {maximumFractionDigits:d, minimumFractionDigits:d});
const opt = (id, vals, all=true) => { document.getElementById(id).innerHTML = (all?'<option value="All">All</option>':'') + vals.map(v=>`<option value="${v}">${MK[v]||v}</option>`).join(''); };
const tab = (el, cols, rows) => document.getElementById(el).innerHTML = '<table><tr>'+cols.map(c=>'<th>'+c[0]+'</th>').join('')+'</tr>'+rows.map(r=>'<tr>'+cols.map(c=>'<td>'+c[1](r)+'</td>').join('')+'</tr>').join('')+'</table>';
document.querySelectorAll('nav button').forEach(b => b.onclick = () => { document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('on', x===b));
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.id===b.dataset.t)); window.dispatchEvent(new Event('resize')); });
opt('fm', Object.keys(MK)); opt('fp', PL); opt('fp2', PL); opt('fm3', Object.keys(MK), false); document.getElementById('fm3').value='DE';
const months = [...new Set(D.mp.map(r=>r.month))].sort(), last = months[months.length-1], prev = months[months.length-2];
function agg(rows) { const s = k => rows.reduce((a,r)=>a+(r[k]||0),0); const c = rows.reduce((a,r)=>a+(r.comments_scored||0),0);
  return {reach:s('reach'), org:s('org_reach'), er: s('org_eng')/s('org_reach'), fol:s('followers_end'), spend:s('spend'),
          sent: c ? rows.reduce((a,r)=>a+(r.net_sentiment||0)*(r.comments_scored||0),0)/c : null}; }
function overview() {
  const m = fm.value, p = fp.value, sel = r => (m==='All'||r.market===m) && (p==='All'||r.platform===p);
  const A = agg(D.mp.filter(r=>sel(r)&&r.month===last)), B = agg(D.mp.filter(r=>sel(r)&&r.month===prev));
  const K = [['Reach, Oct 2026', fmt(A.reach/1e6)+'M', A.reach/B.reach-1], ['Engagement rate by reach', fmt(100*A.er)+'%', A.er/B.er-1],
             ['Net sentiment', fmt(A.sent,0), null], ['Followers', fmt(A.fol/1e3,0)+'k', null]];
  document.getElementById('kp').innerHTML = K.map(k=>`<div class="card k"><div class="l">${k[0]}</div><div class="v">${k[1]}</div><div class="note">${k[2]==null?'':'vs Sept '+(k[2]>=0?'+':'')+fmt(100*k[2],0)+'%'}</div></div>`).join('');
  const mks = m==='All' ? Object.keys(MK) : [m];
  Plotly.react('c1', mks.map(x => { const ys = months.map(mo => agg(D.mp.filter(r=>r.market===x&&r.month===mo&&(p==='All'||r.platform===p))).er*100);
    return {x:months, y:ys, name:MK[x], mode:'lines', line:{color:COL[x], width:2}}; }), LAY({yaxis:{ticksuffix:'%', gridcolor:'#E3DED6'}}), CFG);
  const R = months.map(mo => agg(D.mp.filter(r=>sel(r)&&r.month===mo)));
  Plotly.react('c2', [{x:months, y:R.map(a=>a.org/1e6), name:'organic', type:'bar', marker:{color:'#6B2D5C'}},
    {x:months, y:R.map(a=>(a.reach-a.org)/1e6), name:'sponsored', type:'bar', marker:{color:'#C9A6C0'}}], LAY({barmode:'stack', yaxis:{ticksuffix:'M', gridcolor:'#E3DED6'}}), CFG);
  Plotly.react('c3', mks.map(x => ({x:months, y:months.map(mo => agg(D.mp.filter(r=>r.market===x&&r.month===mo&&(p==='All'||r.platform===p))).sent),
    name:MK[x], mode:'lines', line:{color:COL[x], width:2}})), LAY(), CFG);
}
tab('det', [['Situation', r=>r.event.replaceAll('_',' ')], ['Where', r=>r.where], ['Evidence', r=>r.evidence], ['Decision', r=>r.decision]], D.det);
fm.onchange = fp.onchange = overview; overview();
function content() {
  const p = fp2.value, f = r => p==='All' || r.platform===p;
  const fmts = [...new Set(D.fmt.filter(f).map(r=>r.format))], mks = Object.keys(MK);
  const z = fmts.map(fo => mks.map(m => { const rs = D.fmt.filter(r=>f(r)&&r.format===fo&&r.market===m); const re = rs.reduce((a,r)=>a+r.reach,0);
     return re ? 100*rs.reduce((a,r)=>a+r.eng,0)/re : null; }));
  Plotly.react('c4', [{z, x:mks.map(m=>MK[m]), y:fmts, type:'heatmap', colorscale:[[0,'#F6F3EF'],[1,'#6B2D5C']], texttemplate:'%{z:.1f}%', hoverongaps:false, colorbar:{ticksuffix:'%'}}],
    LAY({margin:{l:90,r:10,t:10,b:40}}), CFG);
  const th = [...new Set(D.theme.map(r=>r.theme))].map(t => { const rs = D.theme.filter(r=>f(r)&&r.theme===t); return [t, 100*rs.reduce((a,r)=>a+r.eng,0)/rs.reduce((a,r)=>a+r.reach,0)]; }).sort((a,b)=>a[1]-b[1]);
  Plotly.react('c5', [{x:th.map(t=>t[1]), y:th.map(t=>t[0]), type:'bar', orientation:'h', marker:{color:'#6B2D5C'}, texttemplate:'%{x:.1f}%'}],
    LAY({margin:{l:110,r:10,t:10,b:40}, xaxis:{ticksuffix:'%', gridcolor:'#E3DED6'}}), CFG);
  const m = fm3.value, hours = [...Array(24).keys()].filter(h=>h>=6);
  const line = (src, key, name, col) => ({x:hours, y:hours.map(h => { const rs = src.filter(r=>r.market===m&&f(r)&&r[key]===h); const re = rs.reduce((a,r)=>a+r.reach,0);
      return rs.reduce((a,r)=>a+r.posts,0) >= 10 ? 100*rs.reduce((a,r)=>a+r.eng,0)/re : null; }), name, mode:'lines+markers', line:{color:col}});
  Plotly.react('c6', [line(D.hl,'local_hour','local time','#6B2D5C'), line(D.hx,'hour_as_exported','as exported','#B88A4E')],
    LAY({xaxis:{title:'hour', gridcolor:'#E3DED6'}, yaxis:{ticksuffix:'%', gridcolor:'#E3DED6'}}), CFG);
}
fp2.onchange = fm3.onchange = content; content();
(function creators() {
  const comms = [...new Set(D.net.map(r=>r.community))].sort((a,b)=>a-b), pal = ['#6B2D5C','#1C5CAB','#B88A4E','#1E7A52','#B02E2E','#8A6FB0','#3A8FA0','#C46A2D','#7C7A73'];
  const maxp = Math.max(...D.net.map(r=>r.pagerank));
  const tr = comms.map((c,i) => { const g = D.net.filter(r=>r.community===c); return {x:g.map(r=>r.x), y:g.map(r=>r.y), mode:'markers', type:'scatter', name:'community '+c,
     text:g.map(r=>`${r.creator_id} · ${MK[r.market]} · ${r.tier} · ${r.niche}`), hoverinfo:'text', marker:{size:g.map(r=>5+22*r.pagerank/maxp), color:pal[i%pal.length], opacity:.75}}; });
  const ex = D.net.filter(r=>r.authenticity_score<50);
  tr.push({x:ex.map(r=>r.x), y:ex.map(r=>r.y), mode:'markers', name:'excluded', text:ex.map(r=>r.creator_id), marker:{size:18, color:'rgba(0,0,0,0)', line:{color:'#000', width:2}}});
  Plotly.newPlot('c7', tr, LAY({xaxis:{visible:false}, yaxis:{visible:false}, margin:{l:5,r:5,t:5,b:5}, showlegend:true, legend:{orientation:'v', x:1, y:1}}), CFG);
  Plotly.newPlot('c8', ['nano','micro','macro'].map(t => ({y:D.net.filter(r=>r.tier===t).map(r=>100*r.er_followers), name:t, type:'box', marker:{color:'#6B2D5C'}})),
    LAY({yaxis:{ticksuffix:'%', gridcolor:'#E3DED6'}, showlegend:false}), CFG);
  Plotly.newPlot('c9', [{x:D.net.map(r=>r.authenticity_score), type:'histogram', xbins:{start:-5, end:105, size:10}, marker:{color:'#6B2D5C'}}], LAY({margin:{l:40,r:10,t:5,b:30}, yaxis:{type:'log', gridcolor:'#E3DED6', title:'creators (log)'}, xaxis:{title:'score', gridcolor:'#E3DED6'}}), CFG);
  tab('tc', [['#', r=>r.community], ['Size', r=>r.size], ['Market', r=>MK[r.main_market]], ['Main niche', r=>r.main_niche], ['Median ER', r=>fmt(100*r.median_er)+'%'], ['Hub', r=>r.hub]], D.comm);
  tab('ts', [['Market', r=>MK[r.market]], ['Creator', r=>r.creator_id], ['Tier', r=>r.tier], ['Niche', r=>r.niche], ['ER', r=>fmt(100*r.er_followers)+'%'], ['Eng. per €', r=>fmt(r.engagements_per_eur)], ['Score', r=>r.authenticity_score]], D.short);
})();
(function publicPanel() {
  const eu = D.eu.filter(r=>['FR','DE','ES','IT','UK','EU27_2020'].includes(r.geo)).sort((a,b)=>a.pct_individuals-b.pct_individuals);
  Plotly.newPlot('c10', [{y:eu.map(r=>(MK[r.geo]||'EU 27')+' ('+r.year+')'), x:eu.map(r=>r.pct_individuals), type:'bar', orientation:'h', marker:{color:'#0E7A55'}, texttemplate:'%{x:.1f}%'}],
    LAY({margin:{l:150,r:10,t:10,b:30}, xaxis:{ticksuffix:'%', gridcolor:'#E3DED6'}}), CFG);
  const langs = ['fr','en','de','es','it'], brands = [...new Set(D.wb.map(r=>r.entity))];
  Plotly.newPlot('c11', [{z:brands.map(b=>langs.map(l=>(D.wb.find(r=>r.entity===b&&r.lang===l)||{}).per_million)), x:langs, y:brands, type:'heatmap',
    colorscale:[[0,'#EEF6F1'],[1,'#0E7A55']], texttemplate:'%{z:.2f}'}], LAY({margin:{l:150,r:10,t:10,b:30}}), CFG);
  const topics = [...new Set(D.wt.map(r=>r.entity))]; opt('ft', topics, false); ft.value = topics.includes('Sunscreen') ? 'Sunscreen' : topics[0];
  const draw = () => Plotly.react('c12', langs.map(l => { const rs = D.wt.filter(r=>r.entity===ft.value&&r.lang===l).sort((a,b)=>a.month.localeCompare(b.month));
     return {x:rs.map(r=>r.month.slice(0,4)+'-'+r.month.slice(4)), y:rs.map(r=>r.per_million), name:l, mode:'lines'}; }), LAY(), CFG);
  ft.onchange = draw; draw();
  const mt = D.mth.sort((a,b)=>a.share-b.share);
  Plotly.newPlot('c13', [{x:mt.map(r=>r.share), y:mt.map(r=>r.theme.replaceAll('_',' ')), type:'bar', orientation:'h', marker:{color:'#0E7A55'}, texttemplate:'%{x:.0f}%'}],
    LAY({margin:{l:130,r:10,t:10,b:30}, xaxis:{ticksuffix:'%', gridcolor:'#E3DED6'}}), CFG);
})();
if (/^#t[1-4]$/.test(location.hash)) document.querySelector(`nav button[data-t="${location.hash.slice(1)}"]`).click();
</script></body></html>"""


def main():
    OUT.parent.mkdir(exist_ok=True)
    html = HTML.replace("__PLOTLY__", get_plotlyjs()).replace("__DATA__", json.dumps(data(), default=str))
    OUT.write_text(html, encoding="utf-8")
    print(f"dashboard: {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
