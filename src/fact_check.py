"""Number checker for the monthly client report (adapted from an earlier release-commentary checker).

Every number written in the PowerPoint must be traceable to the fact sheet (data/processed/facts.json), with the right
market when the sentence names one, at the precision written (14.6 must be 14.6 once rounded, not 14.7). Structural
numbers (5 markets, 10 slides, dates, years) are allowed by explicit patterns only. The report is rejected if any
number fails; each failure says what was written and what the fact sheet holds.

Usage:  python src/fact_check.py                       (checks reports/monthly_report_oct2026.pptx, exit 1 on failure)
        python src/fact_check.py "some sentence"       (checks one sentence)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "processed" / "facts.json"
PPTX = ROOT / "reports" / "monthly_report_oct2026.pptx"

MARKETS = {"FR": r"France|French|\bFR\b", "UK": r"United Kingdom|British|\bUK\b", "DE": r"Germany|German|\bDE\b",
           "ES": r"Spain|Spanish|\bES\b", "IT": r"Italy|Italian|\bIT\b"}
NUM = re.compile(r"(?<![\w.])(?P<sign>[-+−])?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
                 r"(?P<suf>\s?(?:%|pts?\b|points?\b|M\b|k\b|x\b)|:00)?")
# Subject of a number = closest metric keyword (right after the number first, else the last one before it).
FAMILIES = {
    "sentiment": (r"sentiment", r"sent"),
    "share_of_voice": (r"share of voice", r"sov"),
    "cost": (r"cost per (?:paid )?engagement|€", r"cpe"),
    "paid_share": (r"paid share", r"paid_reach_share"),
    "engagement": (r"engagement (?:rate )?(?:per|by) (?:follower|reach)|engagement rate|engagement by reach",
                   r"(?:^|_)er(?:_|$)|_er\b|erf|err|theme_er|best_theme|worst_theme|top_posts|bottom_posts|shortlist"),
    "followers": (r"(?<!per )followers\b", r"followers|follower_jump|growth|suspect"),
}
# Structural numbers: allowed because they describe the report, not a result.
ALLOWED = [r"\b(?:20(?:25|26|27))\b", r"\b\d+\s(?:markets?|platforms?|messages|slides?|languages)\b",
           r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}\b",
           r"\bcreator_\d{3}\b", r"\b\d+ / 10\b", r"\b0[1-4]_\w+\.sql\b", r"\b\d+\s?(?:posts|scored comments) minimum\b",
           r"\bslide \d+\b", r"\bat least \d+ posts\b", r"\b[1-9]\.\s", r"\bTop \d\b", r"\b(?:3|6|12)[- ]months?\b",
           r"\bnext \d+ weeks?\b", r"\|z\| >= \d(?:\.\d)?\b", r"\b\d+ previous months\b", r"\bweek \d\b", r"\bQ[1-4]\b"]


@dataclass
class Finding:
    raw: str
    ok: bool
    note: str = ""


@dataclass
class Report:
    text: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(f.ok for f in self.findings)

    def errors(self):
        return [f for f in self.findings if not f.ok]

    def summary(self) -> str:
        return "\n".join(f"  [{'ok' if f.ok else 'REJECTED'}] {f.raw}: {f.note}" for f in self.findings if not f.ok) or "  all numbers traced"


def load_facts(path: Path = FACTS) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flat(facts: dict) -> list[tuple[str, float]]:
    out = []

    def walk(k, v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            out.append((k, float(v)))
            if abs(v) < 1 and re.search(r"er_|er$|share|rate|overstatement|accuracy|change|jump", k):  # fraction written as %
                out.append((k, float(v) * 100))
        elif isinstance(v, dict):
            for kk, vv in v.items():
                walk(f"{k}.{kk}", vv)
        elif isinstance(v, list):
            for i, vv in enumerate(v):
                walk(f"{k}[{i}]", vv)
    for k, v in facts.items():
        walk(k, v)
    return out


def market_of(key: str) -> str | None:
    head = key.split("_")[0].split("[")[0]
    if head in MARKETS:
        return head
    m = re.search(r"'market': '(\w\w)'", key)
    return m.group(1) if m else None


def masked(text: str) -> str:
    for rx in ALLOWED:
        text = re.sub(rx, lambda m: "#" * len(m.group(0)), text)
    return text


def subject(sentence: str, start: int, end: int) -> str | None:
    after = sentence[end:end + 12].lower()
    for fam, (kw, _) in FAMILIES.items():
        if re.match(r"\s*(?:" + kw + ")", after):
            return fam
    before = sentence[max(0, start - 70):start].lower()
    best, pos = None, -1
    for fam, (kw, _) in FAMILIES.items():
        for m in re.finditer(kw, before):
            if m.end() > pos:
                best, pos = fam, m.end()
    return best


def check(text: str, facts: dict) -> Report:
    rep = Report(text)
    values = flat(facts)
    # market of nested records (top_posts, shortlist) comes from the record itself
    rec_market = {}
    for name in ("top_posts", "bottom_posts", "shortlist"):
        for i, r in enumerate(facts.get(name, [])):
            rec_market[f"{name}[{i}]"] = r.get("market")
    for sentence in re.split(r"(?<=[.;!?])\s+|\n", text):
        named = [m for m, rx in MARKETS.items() if re.search(rx, sentence)]
        clean = masked(sentence)
        for mt in NUM.finditer(clean):
            raw = mt.group(0).strip()
            num = mt.group("num").replace(",", "")
            dec = len(num.split(".")[1]) if "." in num else 0
            val = float(num) * (-1 if mt.group("sign") in ("-", "−") else 1)
            suf = (mt.group("suf") or "").strip()
            scaled = val * {"M": 1e6, "k": 1e3}.get(suf, 1)
            fam = subject(clean, mt.start(), mt.end())
            cands = []
            for k, v in values:
                if fam and not re.search(FAMILIES[fam][1], k):
                    continue
                km = market_of(k) or rec_market.get(k.split(".")[0])
                if len(named) == 1 and km not in (None, named[0]):
                    continue
                cands.append((k, v))
            hit = next((k for k, v in cands if round(v, dec) == round(val, dec) or round(abs(v), dec) == round(abs(val), dec)
                        or (suf in ("M", "k") and round(v / {"M": 1e6, "k": 1e3}[suf], dec) == round(val, dec))
                        or round(v, dec) == round(scaled, dec)), None)
            if hit:
                rep.findings.append(Finding(raw, True, hit))
            else:
                near = sorted(cands, key=lambda kv: abs(kv[1] - val))[:2]
                ctx = f" (market: {named[0]})" if len(named) == 1 else ""
                ctx += f" (subject: {fam})" if fam else ""
                rep.findings.append(Finding(raw, False, f"not in the fact sheet{ctx}; nearest: " +
                                            ", ".join(f"{k}={v:g}" for k, v in near)))
    return rep


def pptx_text(path: Path = PPTX) -> list[tuple[int, str]]:
    from pptx import Presentation
    out = []
    for i, s in enumerate(Presentation(str(path)).slides, 1):
        for sh in s.shapes:
            if sh.has_text_frame:
                out.append((i, sh.text_frame.text))
            if sh.has_table:
                for row in sh.table.rows:
                    out.append((i, " ; ".join(c.text for c in row.cells)))
            if sh.has_chart and sh.chart.has_title:
                out.append((i, sh.chart.chart_title.text_frame.text))
    return out


def check_pptx(path: Path = PPTX, facts: dict | None = None) -> list[tuple[int, Report]]:
    facts = facts or load_facts()
    return [(i, check(t, facts)) for i, t in pptx_text(path)]


def main():
    if len(sys.argv) > 1:
        rep = check(sys.argv[1], load_facts())
        print("PASS" if rep.passed else "FAIL")
        print(rep.summary())
        sys.exit(0 if rep.passed else 1)
    reps = check_pptx()
    bad = [(i, r) for i, r in reps if not r.passed]
    n = sum(len(r.findings) for _, r in reps)
    print(f"{n} numbers checked in {PPTX.name}: {n - sum(len(r.errors()) for _, r in bad)} traced")
    for i, r in bad:
        print(f"slide {i}:\n{r.summary()}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
