"""SIMULATED multi-market social media data for a fictitious account, "a global beauty retailer".

Usage: python src/simulate.py   (seed 42, 2025-06-01 to 2026-10-31, 5 markets x 5 platforms)

Nothing here describes a real brand, heaven, Hopscotch or any client. Orders of magnitude are calibrated on public data
(Eurostat social-network use by country) and on documented assumptions (data/ASSUMPTIONS.md).

Outputs (data/simulated/): posts, ads_spend, export_settings, accounts_daily, comments_sample, creators,
creators_weekly, mentions, campaigns. Hidden answer key: data/_hidden_truth.csv (removed before publication).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "simulated"
rng = np.random.default_rng(42)

START, END = pd.Timestamp("2025-06-01"), pd.Timestamp("2026-10-31")
DAYS = pd.date_range(START, END, freq="D")
MARKETS = {"FR": ("France", "Europe/Paris", "fr"), "UK": ("United Kingdom", "Europe/London", "en"),
           "DE": ("Germany", "Europe/Berlin", "de"), "ES": ("Spain", "Europe/Madrid", "es"), "IT": ("Italy", "Europe/Rome", "it")}
PLATFORMS = ["Instagram", "TikTok", "Facebook", "X", "YouTube"]

# ---------- calibration (see data/ASSUMPTIONS.md) ----------
EUROSTAT_DEFAULT = {"FR": 63.0, "UK": 77.0, "DE": 58.0, "ES": 68.0, "IT": 61.0}   # % individuals using social networks
PRESENCE = {"FR": 1.00, "UK": 0.85, "DE": 0.65, "ES": 0.75, "IT": 0.70}          # brand awareness assumption
PLATFORM_SIZE = {"Instagram": 1.0, "TikTok": 0.75, "Facebook": 0.6, "X": 0.2, "YouTube": 0.15}
BASE_FOLLOWERS = 420_000                                                           # Instagram, home market
MONTHLY_GROWTH = {"Instagram": 0.012, "TikTok": 0.025, "Facebook": 0.002, "X": -0.003, "YouTube": 0.008}
POSTS_PER_MONTH = {"Instagram": 22, "TikTok": 18, "Facebook": 12, "X": 20, "YouTube": 4}
FORMATS = {"Instagram": {"short video": .40, "carousel": .30, "image": .25, "live": .05},
           "TikTok": {"short video": .93, "live": .07},
           "Facebook": {"short video": .30, "image": .40, "carousel": .20, "live": .10},
           "X": {"image": .60, "short video": .40},
           "YouTube": {"short video": .65, "long video": .35}}
REACH_RATE = {("Instagram", "short video"): .35, ("Instagram", "carousel"): .22, ("Instagram", "image"): .15,
              ("Instagram", "live"): .05, ("TikTok", "short video"): .60, ("TikTok", "live"): .08,
              ("Facebook", "short video"): .10, ("Facebook", "image"): .05, ("Facebook", "carousel"): .06,
              ("Facebook", "live"): .03, ("X", "image"): .04, ("X", "short video"): .05,
              ("YouTube", "short video"): .30, ("YouTube", "long video"): .18}
ER_REACH = {("Instagram", "short video"): .055, ("Instagram", "carousel"): .060, ("Instagram", "image"): .045,
            ("Instagram", "live"): .080, ("TikTok", "short video"): .065, ("TikTok", "live"): .090,
            ("Facebook", "short video"): .025, ("Facebook", "image"): .020, ("Facebook", "carousel"): .022,
            ("Facebook", "live"): .040, ("X", "image"): .012, ("X", "short video"): .015,
            ("YouTube", "short video"): .040, ("YouTube", "long video"): .050}
THEMES = {"tutorial": 1.15, "product launch": 1.05, "promo & offers": 0.90, "creator collab": 1.20,
          "routine & tips": 1.10, "brand story": 0.85}
# Event 7: market-specific format effect on engagement per reach
FORMAT_MARKET = {("short video", "FR"): 1.35, ("short video", "ES"): 1.35, ("short video", "DE"): 0.85,
                 ("short video", "UK"): 1.10, ("short video", "IT"): 1.10, ("carousel", "DE"): 1.35}
HOUR_W = np.array([0, 0, 0, 0, 0, 0, 0, .02, .06, .07, .06, .06, .09, .08, .05, .04, .04, .05, .08, .10, .10, .06, .03, .01])
HOUR_W = HOUR_W / HOUR_W.sum()
HOUR_EFFECT = np.array([.7] * 7 + [.85, .9, .9, .92, .95, 1.05, 1.05, .95, .92, .95, 1.0, 1.1, 1.2, 1.22, 1.15, 1.0, .85])
SPLIT = {"Instagram": (.75, .06, .08, .11), "TikTok": (.82, .05, .08, .05), "Facebook": (.80, .10, .10, 0),
         "X": (.70, .10, .15, .05), "YouTube": (.90, .10, 0, 0)}

CAMPAIGNS = [("C01", "Black Friday 2025", "2025-11-24", "2025-12-01", "all"),
             ("C02", "Holiday gifting 2025", "2025-12-02", "2025-12-24", "all"),
             ("C03", "Winter sales 2026", "2026-01-07", "2026-01-31", "all"),
             ("C04", "Spring giveaway (Spain)", "2026-03-09", "2026-03-22", "ES"),
             ("C05", "Spring skincare launch", "2026-03-23", "2026-04-15", "all"),
             ("C06", "Summer sales 2026", "2026-06-24", "2026-07-20", "all"),
             ("C07", "Autumn make-up launch", "2026-09-15", "2026-10-10", "all")]

IG_BREAK = pd.Timestamp("2026-02-01")        # Event 1: Instagram 'views' definition change
SPONSOR_MISLABEL = "IT"                      # Event 2: sponsored posts exported as organic
UTC_EXPORT = "DE"                            # Event 3: export in UTC instead of local time
CONTEST = ("ES", "Instagram", pd.Timestamp("2026-03-09"), pd.Timestamp("2026-03-22"), 0.35)  # Event 4
STOCKOUT = ("FR", pd.Timestamp("2026-10-05"), pd.Timestamp("2026-10-25"))                # Event 6


def eurostat_use() -> dict:
    f = ROOT / "data" / "public" / "eurostat_social_use.csv"
    if not f.exists():
        return EUROSTAT_DEFAULT
    e = pd.read_csv(f)
    e = e[e.geo.isin(["FR", "DE", "ES", "IT", "UK"])].sort_values("year").groupby("geo").last()
    return {m: float(e.pct_individuals.get(m, EUROSTAT_DEFAULT[m])) for m in MARKETS}


def in_campaign(day: pd.Timestamp, market: str) -> str | None:
    for cid, _, s, e, mk in CAMPAIGNS:
        if pd.Timestamp(s) <= day <= pd.Timestamp(e) and mk in ("all", market):
            return cid
    return None


def followers_series(use: dict) -> pd.DataFrame:
    rows = []
    mean_use = np.mean(list(use.values()))
    for m in MARKETS:
        for p in PLATFORMS:
            base = BASE_FOLLOWERS * PLATFORM_SIZE[p] * PRESENCE[m] * use[m] / mean_use
            daily = (1 + MONTHLY_GROWTH[p]) ** (1 / 30.4) - 1
            noise = rng.normal(0, 0.0015, len(DAYS))
            organic = base * np.cumprod(1 + daily + noise)
            extra = np.zeros(len(DAYS))
            if (m, p) == CONTEST[:2]:
                s, e, lift = CONTEST[2], CONTEST[3], CONTEST[4]
                for i, d in enumerate(DAYS):
                    if s <= d <= e:
                        extra[i] = organic[i] * lift * (d - s).days / (e - s).days
                    elif d > e:
                        churn = min(1.0, (d - e).days / 60) * 0.15   # 15% of contest followers leave in 2 months
                        extra[i] = organic[i] * lift * (1 - churn)
            rows.append(pd.DataFrame(dict(date=DAYS, market=m, platform=p, followers=np.round(organic + extra).astype(int),
                                          engaged_base=np.round(organic).astype(int))))
    return pd.concat(rows, ignore_index=True)


def make_posts(fol: pd.DataFrame):
    fidx = fol.set_index(["market", "platform", "date"])
    posts, n = [], 0
    for m, (_, tz, _) in MARKETS.items():
        for p in PLATFORMS:
            for month in pd.period_range(START, END, freq="M"):
                k = rng.poisson(POSTS_PER_MONTH[p])
                days = month.to_timestamp() + pd.to_timedelta(rng.integers(0, month.days_in_month, k), unit="D")
                fmts = list(FORMATS[p])
                for d in days:
                    n += 1
                    fmt = rng.choice(fmts, p=list(FORMATS[p].values()))
                    theme = rng.choice(list(THEMES))
                    hour, minute = int(rng.choice(24, p=HOUR_W)), int(rng.integers(0, 60))
                    camp = in_campaign(d, m)
                    if camp and rng.random() < .3:
                        theme = "promo & offers" if camp in ("C01", "C03", "C06") else "product launch"
                    sponsored = rng.random() < (0.30 if camp else 0.12)
                    base = fidx.loc[(m, p, d), "engaged_base"]
                    fols = fidx.loc[(m, p, d), "followers"]
                    reach = base * REACH_RATE[(p, fmt)] * rng.lognormal(0, .9 if p == "TikTok" else .35)
                    reach *= 1.25 if camp else 1.0
                    reach *= FORMAT_MARKET.get((fmt, m), 1.0) ** .5
                    er = ER_REACH[(p, fmt)] * THEMES[theme] * HOUR_EFFECT[hour] * FORMAT_MARKET.get((fmt, m), 1.0)
                    er *= rng.lognormal(0, .25)
                    spend = 0.0
                    if sponsored:
                        reach *= rng.uniform(2.5, 4.0)
                        er *= 0.6
                        spend = round(reach / 1000 * rng.uniform(6, 9), 2)
                    reach = int(max(50, reach))
                    eng = int(rng.binomial(reach, min(er, .5)))
                    sp = np.array(SPLIT[p]) / sum(SPLIT[p])
                    likes, comments, shares, saves = rng.multinomial(eng, sp)
                    vid = fmt in ("short video", "long video", "live")
                    views = impressions = None
                    if p == "Instagram":
                        if d < IG_BREAK:   # before: 'views' column holds video plays only; impressions for all formats
                            views = int(reach * rng.uniform(1.3, 1.5)) if vid else None
                            impressions = int(reach * rng.uniform(1.6, 2.0))
                        else:              # after: 'views' counts every display of every format; impressions gone
                            views = int(reach * rng.uniform(1.6, 2.0))
                    elif p == "X":
                        impressions = int(reach * rng.uniform(1.4, 1.8))
                    else:
                        views = int(reach * rng.uniform(1.3, 1.8)) if (vid or p == "Facebook") else None
                    local = datetime(d.year, d.month, d.day, hour, minute, tzinfo=ZoneInfo(tz))
                    posts.append(dict(post_id=f"P{n:05d}", native_post_id=f"{p[:2].upper()}{m}{n:06d}", market=m,
                                      platform=p, format=fmt, theme=theme, campaign_id=camp, _sponsored=sponsored,
                                      _local=local, reach=reach, impressions=impressions, views=views,
                                      likes=int(likes), comments=int(comments), shares=int(shares), saves=int(saves),
                                      _spend=spend, _followers=fols))
    return posts


def global_crossposts(fol: pd.DataFrame, start_n: int):
    """Event 8: 3 global collab posts a month on Instagram, shown in all 5 market exports with identical metrics."""
    out, n = [], start_n
    tot = fol[fol.platform == "Instagram"].groupby("date").engaged_base.sum()
    for month in pd.period_range(START, END, freq="M"):
        for _ in range(3):
            n += 1
            d = month.to_timestamp() + pd.Timedelta(days=int(rng.integers(0, month.days_in_month)))
            reach = int(tot.loc[d] * .30 * rng.lognormal(0, .4))
            eng = int(rng.binomial(reach, .05))
            likes, comments, shares, saves = rng.multinomial(eng, np.array(SPLIT["Instagram"]))
            views = int(reach * rng.uniform(1.6, 2.0)) if d >= IG_BREAK else int(reach * 1.4)
            imp = None if d >= IG_BREAK else int(reach * rng.uniform(1.6, 2.0))
            native = f"IGGL{n:06d}"
            for i, (m, (_, tz, _)) in enumerate(MARKETS.items()):
                local = datetime(d.year, d.month, d.day, 18, 0, tzinfo=ZoneInfo("Europe/Paris")).astimezone(ZoneInfo(tz))
                out.append(dict(post_id=f"P{n:05d}{'abcde'[i]}", native_post_id=native, market=m, platform="Instagram",
                                format="short video", theme="creator collab", campaign_id=in_campaign(d, m),
                                _sponsored=False, _local=local, reach=reach, impressions=imp, views=views,
                                likes=int(likes), comments=int(comments), shares=int(shares), saves=int(saves), _spend=0.0,
                                _followers=None))
    return out, n


COMMENT_BANK = {
    "en": {"positive": ["love this {x}", "this {x} is amazing", "best {x} I have tried", "obsessed with the new {x}",
                        "my skin looks glowing, recommend", "gorgeous shade, works perfectly"],
           "neutral": ["which {x} is this?", "does it come in other shades?", "when is the {x} launching in store",
                       "price please", "is it fragrance-free?", "tutorial for the {x}?"],
           "negative": ["sold out again, so disappointing", "still unavailable online and in store",
                        "too expensive for what it is", "gave me a breakout", "not good on oily skin", "waste of money"]},
    "fr": {"positive": ["j'adore ce {x}", "trop bien ce {x}, je recommande", "la teinte est parfaite", "meilleur {x} testé",
                        "ma peau est sublime", "super efficace"],
           "neutral": ["c'est quelle teinte ?", "dispo en magasin quand ?", "il existe en version mate ?",
                       "quel prix ?", "il contient du parfum ?", "un tuto pour le {x} ?"],
           "negative": ["encore en rupture, trop déçue", "introuvable en ligne comme en magasin depuis des semaines",
                        "rupture de stock du {x}, c'est nul", "trop cher pour ce que c'est", "irritation dès le 1er jour",
                        "pas bon sur peau grasse"]},
    "de": {"positive": ["ich liebe diesen {x}", "toller {x}, empfehle ich", "perfekter Farbton", "bester {x} bisher",
                        "meine Haut ist so weich", "wirkt super"],
           "neutral": ["welcher Farbton ist das?", "wann im Laden?", "gibt es das auch matt?", "Preis?",
                       "ist da Parfum drin?", "Tutorial bitte"],
           "negative": ["schon wieder ausverkauft, enttäuschend", "zu teuer", "hat Pickel verursacht", "nicht gut für fettige Haut",
                        "klebrig und schlecht", "enttäuscht vom {x}"]},
    "es": {"positive": ["me encanta este {x}", "el mejor {x}, lo recomiendo", "tono perfecto", "piel suave y genial",
                        "increíble resultado", "precioso"],
           "neutral": ["¿qué tono es?", "¿cuándo llega a tienda?", "¿precio?", "¿tiene perfume?", "¿hay versión mate?",
                       "tutorial porfa"],
           "negative": ["agotado otra vez, decepcionada", "demasiado caro", "me salieron granos", "malo para piel grasa",
                        "pegajoso, no lo recomiendo", "estafa"]},
    "it": {"positive": ["adoro questo {x}", "il migliore {x}, consiglio", "tonalità perfetta", "pelle morbida, fantastico",
                        "risultato stupendo", "bellissimo"],
           "neutral": ["che tonalità è?", "quando arriva in negozio?", "prezzo?", "c'è profumo?", "esiste opaco?",
                       "tutorial per favore"],
           "negative": ["esaurito di nuovo, delusa", "troppo caro", "mi ha dato brufoli", "pessimo su pelle grassa",
                        "appiccicoso, deluso", "truffa"]},
}
HARD = {"en": [("not bad at all", "positive"), ("could be better", "negative"), ("yeah great, broke me out again", "negative")],
        "fr": [("pas terrible", "negative"), ("pas mal du tout", "positive"), ("génial, encore en rupture...", "negative")],
        "de": [("nicht schlecht", "positive"), ("geht so", "negative")],
        "es": [("no está mal", "positive"), ("regular", "negative")],
        "it": [("non male", "positive"), ("così così", "negative")]}
PRODUCT = {"en": "serum", "fr": "sérum", "de": "Serum", "es": "sérum", "it": "siero"}


def make_comments(posts: pd.DataFrame) -> pd.DataFrame:
    rows, cid = [], 0
    for r in posts.itertuples():
        k = min(int(r.comments), int(rng.poisson(3)))
        lang0 = MARKETS[r.market][2]
        day = r.posted_local_date
        stock = r.market == STOCKOUT[0] and STOCKOUT[1] <= day <= STOCKOUT[2]
        p_lab = [.42, .25, .33] if stock else [.55, .33, .12]
        for _ in range(k):
            cid += 1
            lang = lang0 if rng.random() > .1 else "en"
            if rng.random() < .07:
                text, lab = HARD[lang][int(rng.integers(len(HARD[lang])))]
            else:
                lab = rng.choice(["positive", "neutral", "negative"], p=p_lab)
                bank = COMMENT_BANK[lang][lab]
                if stock and lab == "negative" and lang == "fr" and rng.random() < .8:
                    text = bank[int(rng.integers(0, 3))]
                else:
                    text = bank[int(rng.integers(len(bank)))]
                text = text.format(x=PRODUCT[lang])
            rows.append(dict(comment_id=f"C{cid:06d}", post_id=r.post_id, market=r.market, platform=r.platform,
                             date=day.date().isoformat(), lang=lang, text=text, label_true=lab))
    return pd.DataFrame(rows)


def make_creators():
    """500 anonymous creators; weekly follower history; Event 5 = one creator with bought followers."""
    markets = rng.choice(list(MARKETS), 500, p=[.26, .22, .18, .18, .16])
    tiers = rng.choice(["nano", "micro", "macro"], 500, p=[.55, .35, .10])
    plats = rng.choice(["Instagram", "TikTok", "YouTube"], 500, p=[.5, .35, .15])
    niches = rng.choice(["make-up", "skincare", "hair & fragrance", "lifestyle"], 500, p=[.35, .35, .15, .15])
    rng_f = {"nano": (2_000, 10_000), "micro": (10_000, 100_000), "macro": (100_000, 900_000)}
    er_t = {"nano": .055, "micro": .034, "macro": .019}
    weeks = pd.date_range("2025-06-02", END, freq="W-MON")
    cr, hist = [], []
    suspect = None
    for i in range(500):
        t = tiers[i]
        lo, hi = rng_f[t]
        f0 = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        g = rng.normal(.006 if t != "macro" else .003, .003)
        path = f0 * np.cumprod(1 + g + rng.normal(0, .004, len(weeks)))
        er = er_t[t] * rng.lognormal(0, .3)
        own = float(np.clip(rng.normal(.72, .1), .35, .95))
        cpl = float(np.clip(rng.normal(.045, .015), .01, .12))
        cid = f"creator_{i + 1:03d}"
        if suspect is None and t == "macro" and markets[i] == "UK" and plats[i] == "Instagram":
            suspect = cid
            jump = int(np.where(weeks >= pd.Timestamp("2026-07-06"))[0][0])
            path[jump:] *= 2.6                     # +160% in one week
            er, own, cpl = .0028, .21, .006        # very low engagement, foreign audience, few comments per like
        cr.append(dict(creator_id=cid, market=markets[i], platform=plats[i], niche=niches[i], tier=t,
                       followers=int(path[-1]), er_followers=round(er, 4), audience_own_market=round(own, 3),
                       comments_per_like=round(cpl, 4), avg_reach_rate=round(float(np.clip(rng.normal(.28, .08), .05, .6)), 3),
                       collab_posts_12m=int(rng.poisson(2 if t == "nano" else 3)),
                       est_fee_eur=int(f0 * {"nano": .02, "micro": .015, "macro": .01}[t] * rng.lognormal(0, .2))))
        hist += [dict(creator_id=cid, week=w.date().isoformat(), followers=int(v)) for w, v in zip(weeks, path)]
    return pd.DataFrame(cr), pd.DataFrame(hist), suspect


def make_mentions(cr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ids = cr.creator_id.to_numpy()
    months = [p.strftime("%Y-%m") for p in pd.period_range(START, END, freq="M")]
    by_mn = cr.groupby(["market", "niche"]).creator_id.apply(list).to_dict()
    by_m = cr.groupby("market").creator_id.apply(list).to_dict()
    for c in cr.itertuples():
        for _ in range(int(rng.poisson(8))):
            u = rng.random()
            pool = by_mn[(c.market, c.niche)] if u < .7 else by_m[c.market] if u < .9 else \
                by_m["UK"] if rng.random() < .6 else ids
            tgt = str(rng.choice(pool))
            if tgt != c.creator_id:
                rows.append(dict(source=c.creator_id, target=tgt, target_type="creator", month=str(rng.choice(months)), n=1))
        share = {"FR": .34, "UK": .22, "DE": .18, "ES": .29, "IT": .25}[c.market]
        for _ in range(int(rng.poisson(5))):
            b = "our_account" if rng.random() < share else str(rng.choice(["competitor_A", "competitor_B", "competitor_C"]))
            rows.append(dict(source=c.creator_id, target=b, target_type="brand", month=str(rng.choice(months)), n=1))
    return pd.DataFrame(rows).groupby(["source", "target", "target_type", "month"], as_index=False).n.sum()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    use = eurostat_use()
    fol = followers_series(use)
    raw = make_posts(fol)
    xp, _ = global_crossposts(fol, len(raw) + 1)
    df = pd.DataFrame(raw + xp)
    df["posted_local_date"] = pd.to_datetime([t.date() for t in df._local])
    utc = [t.astimezone(ZoneInfo("UTC")) for t in df._local]
    # Export: every market exports local time, except Event 3 (UTC); all strings are naive, as in the tool export.
    df["posted_at"] = [(u if m == UTC_EXPORT else l).strftime("%Y-%m-%d %H:%M") for u, l, m in zip(utc, df._local, df.market)]
    df["paid_label"] = np.where(df._sponsored & (df.market != SPONSOR_MISLABEL), "sponsored", "organic")
    df = df.sort_values(["posted_at", "post_id"]).reset_index(drop=True)
    comments = make_comments(df)
    posts = df[["post_id", "native_post_id", "market", "platform", "format", "theme", "campaign_id", "paid_label",
                "posted_at", "reach", "impressions", "views", "likes", "comments", "shares", "saves"]].copy()
    for c in ("impressions", "views"):
        posts[c] = posts[c].astype("Int64")
    ads = df.loc[df._sponsored, ["post_id"]].assign(spend_eur=df.loc[df._sponsored, "_spend"].values)
    export = pd.DataFrame([dict(market=m, platform=p, timezone_of_export="UTC" if m == UTC_EXPORT else MARKETS[m][1],
                                market_timezone=MARKETS[m][1]) for m in MARKETS for p in PLATFORMS])
    cr, hist, suspect = make_creators()
    men = make_mentions(cr)
    camp = pd.DataFrame(CAMPAIGNS, columns=["campaign_id", "name", "start", "end", "markets"])
    acc = fol.drop(columns="engaged_base")
    acc["date"] = acc.date.dt.date
    for name, t in (("posts", posts), ("ads_spend", ads), ("export_settings", export), ("accounts_daily", acc),
                    ("comments_sample", comments), ("creators", cr), ("creators_weekly", hist), ("mentions", men),
                    ("campaigns", camp)):
        t.to_csv(OUT / f"{name}.csv", index=False)
    truth = pd.DataFrame([
        (1, "metric_definition_change", "all", "Instagram", IG_BREAK.date(), END.date(), "views column changes definition"),
        (2, "sponsored_mixed_in_organic", SPONSOR_MISLABEL, "all", START.date(), END.date(), "sponsored exported as organic"),
        (3, "timezone_utc_export", UTC_EXPORT, "all", START.date(), END.date(), "posted_at exported in UTC"),
        (4, "false_signal_contest", CONTEST[0], CONTEST[1], CONTEST[2].date(), END.date(),
         "ER per follower drops after giveaway; ER per reach stable -> NOT a content issue"),
        (5, "suspect_creator", "UK", "Instagram", "2026-07-06", END.date(), suspect),
        (6, "negative_sentiment_spike", STOCKOUT[0], "all", STOCKOUT[1].date(), STOCKOUT[2].date(), "hero product stock-out"),
        (7, "format_effect_by_market", "FR,ES,DE", "all", START.date(), END.date(), "short video up in FR/ES, carousel in DE"),
        (8, "global_post_duplicates", "all", "Instagram", START.date(), END.date(), "IGGL* native ids in 5 market exports"),
    ], columns=["event_id", "event", "market", "platform", "start", "end", "detail"])
    truth.to_csv(ROOT / "data" / "_hidden_truth.csv", index=False)
    print(f"posts {len(posts)}, comments {len(comments)}, creators {len(cr)}, mentions {len(men)}, "
          f"accounts_daily {len(acc)}, suspect {suspect}")


if __name__ == "__main__":
    main()
