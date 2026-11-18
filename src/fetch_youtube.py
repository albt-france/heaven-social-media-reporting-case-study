"""OPTIONAL: public YouTube data for the brand panel and for beauty creators (YouTube Data API v3, free key).

Usage: put YOUTUBE_API_KEY=... in .env, then python src/fetch_youtube.py
Without a key the script stops cleanly and the study uses Wikipedia, Bluesky and Mastodon only (the PDF says so).

- Brand channels: candidate handles per brand and market, kept only if the channel title contains the brand name.
- Videos: up to 200 latest uploads per channel (views, likes, comments, duration, short vs long, date).
- Creators: top videos for one beauty query per language since 2025-06-01; channels are anonymised as creator_001...
  The name <-> id table stays in data/raw/ (never published). Quota used: about 1,000 units of the 10,000 free daily units.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polite  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, PUB = ROOT / "data" / "raw" / "youtube", ROOT / "data" / "public"
API = "https://www.googleapis.com/youtube/v3/"
MARKETS = {"FR": "France", "GB": "United Kingdom", "DE": "Germany", "ES": "Spain", "IT": "Italy"}
# Global handle first, then market handles to try. Only channels whose title contains the brand key are kept.
HANDLES = {
    "Maybelline": ["maybelline", "MaybellineFrance", "MaybellineUK", "MaybellineDeutschland", "MaybellineEspana", "MaybellineItalia"],
    "Lancôme": ["lancome", "lancomefr", "LancomeUK", "LancomeDE", "LancomeES", "LancomeIT"],
    "NYX Professional Makeup": ["NYXCosmetics", "NYXProfessionalMakeupFrance", "NYXCosmeticsUK", "NYXDeutschland", "NYXEspana", "NYXItalia"],
    "Garnier": ["garnier", "GarnierFrance", "GarnierUK", "GarnierDeutschland", "GarnierEspana", "GarnierItalia"],
    "Nivea": ["NIVEA", "NIVEAFrance", "NIVEAUK", "NIVEADeutschland", "NIVEAEspana", "NIVEAItalia"],
    "CeraVe": ["CeraVe", "CeraVeFrance", "CeraVeUK", "CeraVeDeutschland", "CeraVeEspana", "CeraVeItalia"],
    "La Roche-Posay": ["LaRochePosay", "LaRochePosayFrance", "LaRochePosayUK", "LaRochePosayDE", "LaRochePosayES", "LaRochePosayIT"],
    "Clinique": ["clinique", "CliniqueFrance", "CliniqueUK", "CliniqueDE", "CliniqueES", "CliniqueIT"],
    "Rimmel": ["rimmellondon", "RimmelLondonFrance", "RimmelLondonUK", "RimmelDE", "RimmelES", "RimmelIT"],
    "Fenty Beauty": ["fentybeauty"],
}
QUERIES = {"FR": ("routine skincare", "fr"), "GB": ("skincare routine", "en"), "DE": ("Hautpflege Routine", "de"),
           "ES": ("rutina skincare", "es"), "IT": ("skincare routine", "it")}


def call(endpoint: str, key: str, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    r = polite.get(f"{API}{endpoint}?{q}&key={key}", check_robots=False)
    if r is None or not r.ok:
        raise RuntimeError(f"{endpoint}: HTTP {getattr(r, 'status_code', None)}")
    return r.json()


def iso_seconds(d: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    dd, h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0, 0)
    return dd * 86400 + h * 3600 + mi * 60 + s


def videos_details(ids: list[str], key: str) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        j = call("videos", key, part="snippet,contentDetails,statistics", id=",".join(ids[i:i + 50]), maxResults=50)
        out += j.get("items", [])
    return out


def video_row(v: dict) -> dict:
    s, st, cd = v["snippet"], v.get("statistics", {}), v["contentDetails"]
    sec = iso_seconds(cd.get("duration"))
    return dict(video_id=v["id"], published=s["publishedAt"][:10], hour_utc=int(s["publishedAt"][11:13]),
                duration_s=sec, format="short (<=60s)" if sec <= 60 else "long (>60s)",
                lang=(s.get("defaultAudioLanguage") or s.get("defaultLanguage") or "und")[:2],
                views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)) if "likeCount" in st else None,
                comments=int(st.get("commentCount", 0)) if "commentCount" in st else None)


def main():
    load_dotenv(ROOT / ".env")
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("No YOUTUBE_API_KEY in .env: YouTube panel skipped (fallback: Wikipedia, Bluesky, Mastodon).")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    chans, vids = [], []
    for brand, handles in HANDLES.items():
        brand_key = re.sub(r"[^a-z]", "", brand.lower().replace("ô", "o"))[:6]
        for h in handles:
            j = call("channels", key, part="snippet,statistics,contentDetails", forHandle="@" + h)
            if not j.get("items"):
                continue
            c = j["items"][0]
            title = re.sub(r"[^a-z]", "", c["snippet"]["title"].lower().replace("ô", "o"))
            if brand_key not in title or c["id"] in {x["channel_id"] for x in chans}:
                continue
            chans.append(dict(brand=brand, channel_id=c["id"], handle=h, country=c["snippet"].get("country"),
                              subscribers=int(c["statistics"].get("subscriberCount", 0)),
                              total_views=int(c["statistics"].get("viewCount", 0)),
                              total_videos=int(c["statistics"].get("videoCount", 0))))
            up, ids, tok = c["contentDetails"]["relatedPlaylists"]["uploads"], [], ""
            for _ in range(4):
                p = call("playlistItems", key, part="contentDetails", playlistId=up, maxResults=50, **({"pageToken": tok} if tok else {}))
                ids += [i["contentDetails"]["videoId"] for i in p.get("items", [])]
                tok = p.get("nextPageToken")
                if not tok:
                    break
            det = videos_details(ids, key)
            (RAW / f"{c['id']}.json").write_text(json.dumps(det), encoding="utf-8")
            vids += [dict(brand=brand, channel_id=c["id"], **video_row(v)) for v in det]
    ch, vd = pd.DataFrame(chans), pd.DataFrame(vids)
    ch.to_csv(PUB / "youtube_brand_channels.csv", index=False)
    vd.to_csv(PUB / "youtube_brand_videos.csv", index=False)
    print(f"brand channels: {len(ch)}, videos: {len(vd)}")

    # Creators: top videos per market query, then anonymised channel ids.
    rows = []
    for cc, (q, lang) in QUERIES.items():
        j = call("search", key, part="snippet", type="video", order="viewCount", maxResults=50, regionCode=cc,
                 relevanceLanguage=lang, publishedAfter="2025-06-01T00:00:00Z", q=q.replace(" ", "+"))
        ids = [i["id"]["videoId"] for i in j.get("items", [])]
        for v in videos_details(ids, key):
            rows.append(dict(market=MARKETS[cc], query_lang=lang, channel_real=v["snippet"]["channelId"], **video_row(v)))
    cr = pd.DataFrame(rows)
    brand_ids = set(ch.channel_id) if len(ch) else set()
    cr = cr[~cr.channel_real.isin(brand_ids)]
    cmap = {c: f"creator_{i + 1:03d}" for i, c in enumerate(sorted(cr.channel_real.unique()))}
    pd.Series(cmap).rename_axis("channel_real").rename("creator_id").to_csv(RAW / "creator_mapping.csv")
    subs = {}
    real = list(cmap)
    for i in range(0, len(real), 50):
        for c in call("channels", key, part="statistics", id=",".join(real[i:i + 50]), maxResults=50).get("items", []):
            subs[c["id"]] = int(c["statistics"].get("subscriberCount", 0))
    cr["creator_id"] = cr.channel_real.map(cmap)
    cr["creator_subscribers"] = cr.channel_real.map(subs)
    cr.drop(columns=["channel_real", "video_id"]).to_csv(PUB / "youtube_creator_videos.csv", index=False)
    print(f"creator videos: {len(cr)} from {len(cmap)} anonymised creators")


if __name__ == "__main__":
    main()
