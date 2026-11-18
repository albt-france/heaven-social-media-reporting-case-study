"""Polite HTTP helper used by every collector.

- robots.txt checked before fetching any web page (official APIs are documented endpoints and are called directly);
- at least 1.5 seconds between two requests;
- a neutral User-Agent, no contact details;
- raw responses are saved under data/raw/ (not published) so a snapshot can be re-read without re-collecting.
"""
from __future__ import annotations

import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = "social-case-study/1.0"
MIN_DELAY_S = 1.5
_last = 0.0
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


def allowed(url: str) -> bool:
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(root + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=20)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[root] = rp
    return _robots[root].can_fetch(USER_AGENT, url)


def get(url: str, check_robots: bool = True, **kw) -> requests.Response | None:
    global _last
    if check_robots and not allowed(url):
        print(f"[robots] skipped: {url}")
        return None
    wait = MIN_DELAY_S - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    headers = {"User-Agent": USER_AGENT}
    headers.update(kw.pop("headers", {}))
    try:
        r = requests.get(url, headers=headers, timeout=40, **kw)
        if r.status_code == 429:  # rate limited: wait as asked (or 60 s), then one retry
            time.sleep(min(120, int(r.headers.get("Retry-After", 60) or 60)))
            r = requests.get(url, headers=headers, timeout=40, **kw)
            _last = time.time()
        return r
    except requests.RequestException as e:
        print(f"[error] {url}: {type(e).__name__}")
        return None
