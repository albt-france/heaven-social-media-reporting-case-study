"""Collect the PUBLIC DATA used in the study (no key needed). Usage: python src/fetch_public.py

Sources (all official, documented, unauthenticated endpoints; see data/SOURCES.md):
- Wikimedia Pageviews API: monthly views of the panel brands and beauty topics, by language edition (fr, en, de, es, it);
- Eurostat isoc_ci_ac_i: share of individuals using social networks (I_IUSNET), by country;
- Mastodon (mastodon.social) public hashtag timelines: a small real social-listening sample;
- Bluesky public AppView: official accounts, only when the handle is a brand-owned domain (ownership proven by DNS).

Raw responses go to data/raw/ (not published). Published outputs in data/public/ are aggregates only:
no post text, no account identifier of a person.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polite  # noqa: E402
from lexicon import classify_themes, sentiment_score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, PUB = ROOT / "data" / "raw", ROOT / "data" / "public"
LANGS = ["fr", "en", "de", "es", "it"]
LANG_MARKET = {"fr": "France", "en": "United Kingdom*", "de": "Germany", "es": "Spain", "it": "Italy"}
START, END = "2025060100", "2026103100"

# Panel: product brands only (no beauty retailer, no brand that mainly sells through its own stores).
BRANDS = {"Maybelline": "maybelline.com", "Lancôme": "lancome.com", "NYX Professional Makeup": "nyxcosmetics.com",
          "Garnier": "garnier.com", "Nivea": "nivea.com", "CeraVe": "cerave.com", "La Roche-Posay": "laroche-posay.com",
          "Clinique": "clinique.com", "Rimmel": "rimmellondon.com", "Fenty Beauty": "fentybeauty.com"}
TOPICS = ["Cosmetics", "Sunscreen", "Lipstick", "Mascara", "Perfume"]
TAGS = ["skincare", "makeup", "beauty", "beauté", "maquillage", "skincareroutine", "hautpflege", "maquillaje", "trucco"]


def save_raw(sub: str, name: str, obj) -> None:
    d = RAW / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def langlinks(title: str) -> dict[str, str]:
    """Article titles in the 5 language editions, from the English article's interlanguage links."""
    u = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=langlinks&lllimit=500&titles="
         + quote(title))
    r = polite.get(u, check_robots=False)
    page = next(iter(r.json()["query"]["pages"].values()))
    out = {"en": page["title"]}
    for ll in page.get("langlinks", []):
        if ll["lang"] in LANGS:
            out[ll["lang"]] = ll["*"]
    return out


def pageviews(lang: str, title: str) -> list[dict]:
    u = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/"
         f"{quote(title.replace(' ', '_'), safe='')}/monthly/{START}/{END}")
    r = polite.get(u, check_robots=False)
    return r.json().get("items", []) if r is not None and r.ok else []


def wiki() -> pd.DataFrame:
    rows = []
    for kind, names in (("brand", list(BRANDS)), ("topic", TOPICS)):
        for name in names:
            titles = langlinks(name)
            for lang, t in titles.items():
                items = pageviews(lang, t)
                save_raw("wikipedia", f"{lang}_{re.sub(r'\W+', '_', t)}.json", items)
                rows += [dict(kind=kind, entity=name, lang=lang, article=t, month=i["timestamp"][:6], views=i["views"])
                         for i in items]
    df = pd.DataFrame(rows)
    # Normalise by the size of each language edition: views per million user pageviews of the whole wiki that month.
    tot = []
    for lang in LANGS:
        u = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/{lang}.wikipedia/all-access/user/monthly/"
             f"{START}/{END}")
        tot += [dict(lang=lang, month=i["timestamp"][:6], wiki_views=i["views"]) for i in polite.get(u, check_robots=False).json()["items"]]
    df = df.merge(pd.DataFrame(tot), on=["lang", "month"], how="left")
    df["per_million"] = df.views / df.wiki_views * 1e6
    df["market"] = df.lang.map(LANG_MARKET)
    return df


def eurostat() -> pd.DataFrame:
    geos = ["FR", "DE", "ES", "IT", "UK", "EU27_2020"]
    u = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ci_ac_i?format=JSON&lang=EN"
         "&indic_is=I_IUSNET&unit=PC_IND&ind_type=IND_TOTAL" + "".join(f"&geo={g}" for g in geos))
    j = polite.get(u, check_robots=False).json()
    save_raw("eurostat", "isoc_ci_ac_i.json", j)
    dims, size = j["id"], j["size"]
    idx = {d: {v: k for k, v in j["dimension"][d]["category"]["index"].items()} for d in dims}
    rows = []
    for flat, val in j["value"].items():
        flat, pos = int(flat), {}
        for d, s in zip(reversed(dims), reversed(size)):
            pos[d] = flat % s
            flat //= s
        rows.append(dict(geo=idx["geo"][pos["geo"]], year=int(idx["time"][pos["time"]]), pct_individuals=val))
    return pd.DataFrame(rows).sort_values(["geo", "year"])


def strip(h: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def mastodon(pages: int = 5) -> pd.DataFrame:
    rows, seen = [], set()
    for tag in TAGS:
        max_id = None
        for _ in range(pages):
            u = f"https://mastodon.social/api/v1/timelines/tag/{quote(tag)}?limit=40" + (f"&max_id={max_id}" if max_id else "")
            r = polite.get(u, check_robots=False)
            if r is None or not r.ok or not r.json():
                break
            batch = r.json()
            save_raw("mastodon", f"{tag}_{max_id or 'first'}.json", batch)
            for s in batch:
                if s["id"] in seen:
                    continue
                seen.add(s["id"])
                text = strip(s.get("content"))
                rows.append(dict(tag=tag, date=s["created_at"][:10], lang=s.get("language") or "und",
                                 favourites=s["favourites_count"], reblogs=s["reblogs_count"], replies=s["replies_count"],
                                 has_media=bool(s.get("media_attachments")), n_words=len(text.split()),
                                 sentiment=sentiment_score(text, s.get("language") or "en"),
                                 **{f"theme_{k}": v for k, v in classify_themes(text).items()}))
            max_id = batch[-1]["id"]
    return pd.DataFrame(rows)


def bluesky() -> pd.DataFrame:
    """Official accounts only: a handle equal to the brand's own domain is DNS-verified by the brand."""
    base, rows = "https://public.api.bsky.app/xrpc/", []
    # Hopscotch: the handle it names in its own press releases ("@HOPSCOTCHgroupe on Bluesky").
    for brand, dom in {**BRANDS, "Hopscotch Groupe": "hopscotchgroupe.bsky.social"}.items():
        r = polite.get(base + "com.atproto.identity.resolveHandle?handle=" + dom, check_robots=False)
        if r is None or not r.ok:
            rows.append(dict(entity=brand, handle=dom, on_bluesky=False))
            continue
        p = polite.get(base + "app.bsky.actor.getProfile?actor=" + dom, check_robots=False).json()
        f = polite.get(base + "app.bsky.feed.getAuthorFeed?filter=posts_no_replies&limit=100&actor=" + dom, check_robots=False).json()
        save_raw("bluesky", f"{dom}.json", dict(profile=p, feed=f))
        posts = [i["post"] for i in f.get("feed", []) if i["post"]["author"]["handle"] == dom]
        eng = [x.get("likeCount", 0) + x.get("repostCount", 0) + x.get("replyCount", 0) + x.get("quoteCount", 0) for x in posts]
        rows.append(dict(entity=brand, handle=dom, on_bluesky=True, followers=p.get("followersCount"),
                         posts_total=p.get("postsCount"), posts_sampled=len(posts),
                         first_sampled=min((x["record"]["createdAt"][:10] for x in posts), default=None),
                         last_sampled=max((x["record"]["createdAt"][:10] for x in posts), default=None),
                         median_engagement=float(pd.Series(eng).median()) if eng else None))
    return pd.DataFrame(rows)


def main(only: str | None = None):
    PUB.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    for name, fn in (("wikipedia_pageviews", wiki), ("eurostat_social_use", eurostat), ("mastodon_sample", mastodon),
                     ("bluesky_accounts", bluesky)):
        if only and only != name:
            continue
        try:
            df = fn()
            df.to_csv(PUB / f"{name}.csv", index=False)
            print(f"{name}: {len(df)} rows")
        except Exception as e:  # one source down must not stop the others; the report says what is missing
            print(f"[fail] {name}: {type(e).__name__}: {e}")
    (PUB / "collected_on.txt").write_text(stamp, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
