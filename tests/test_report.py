"""Tests: number checker (traps), detection of the 8 situations, harmonisation, privacy of published outputs."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import detect  # noqa: E402
import simulate as sim  # noqa: E402
from fact_check import PPTX, check, check_pptx, load_facts  # noqa: E402

FACTS = load_facts()
PROC = ROOT / "data" / "processed"


# ---------- number checker ----------
def good_and_bad():
    f = FACTS
    return [
        (f"France reached {f['FR_reach_m']}M people.", True),
        (f"France reached {f['FR_reach_m'] + 0.1:.1f}M people.", False),                       # wrong value
        (f"Engagement rate by reach in Spain: {f['ES_er_reach']}%.", True),
        (f"Engagement rate by reach in Germany: {f['ES_er_reach']}%.", False),                 # right number, wrong market
        (f"Net sentiment in France fell to {f['fr_sent_now']:.0f} from {f['fr_sent_usual']:.0f}.", True),
        (f"Net sentiment in France fell to {f['fr_sent_now']:.0f} from {f['fr_sent_usual'] + 4:.0f}.", False),
        (f"Italy: {f['it_mislabelled']} boosted posts exported as organic.", True),
        (f"Italy: {f['it_mislabelled'] + 12} boosted posts exported as organic.", False),
        (f"Group reach is {f['group_reach_dedup_m']}M with each post counted once.", True),
        (f"Group reach is {f['group_reach_naive_m'] + 1:.1f}M with each post counted once.", False),
        ("Report for October 2026 across 5 markets and 5 platforms.", True),                   # structural numbers
    ]


@pytest.mark.parametrize("text,expected", good_and_bad())
def test_checker_traps(text, expected):
    assert check(text, FACTS).passed == expected


def test_every_number_in_the_deck_is_traced():
    bad = [(i, r.summary()) for i, r in check_pptx() if not r.passed]
    assert not bad, bad


def test_deck_has_10_slides_tagged_simulated_and_empty_author():
    from pptx import Presentation
    prs = Presentation(str(PPTX))
    assert len(prs.slides) == 10
    for s in prs.slides:
        assert any(sh.has_text_frame and "SIMULATED" in sh.text_frame.text for sh in s.shapes)
    assert prs.core_properties.author == "" and prs.core_properties.last_modified_by == ""


# ---------- detection ----------
@pytest.fixture(scope="module")
def results():
    return {r["event_id"]: r for r in detect.run_all()}


def test_all_eight_situations_found(results):
    assert all(r["detected"] for r in results.values()), [r["event"] for r in results.values() if not r["detected"]]


def test_detection_points_to_the_right_place(results):
    assert "Instagram" in results[1]["where"] and results[1]["detail"]["break_month"][:7] == sim.IG_BREAK.strftime("%Y-%m")
    assert results[2]["where"] == sim.SPONSOR_MISLABEL
    assert results[3]["where"] == sim.UTC_EXPORT
    assert results[4]["detail"]["market"] == sim.CONTEST[0] and results[4]["detail"]["platform"] == sim.CONTEST[1]
    assert results[6]["detail"]["market"] == sim.STOCKOUT[0]
    assert "FR" in results[7]["where"] and "ES" in results[7]["where"] and "carousel ahead: DE" in results[7]["where"]


def test_false_signal_is_not_raised_as_content_issue(results):
    d = results[4]["detail"]
    assert d["er_followers_change"] < -0.10 and not d["content_issue_raised"]


def test_only_one_creator_excluded(results):
    assert len(results[5]["detail"]["ids"]) == 1


# ---------- harmonisation ----------
def test_harmonised_views_have_no_break():
    d = pd.read_csv(PROC / "dq_definition.csv").iloc[0]
    assert d.raw_views_per_reach_after / d.raw_views_per_reach_before > 1.5
    assert abs(d.harmonised_views_per_reach_after / d.harmonised_views_per_reach_before - 1) < 0.05


def test_dedup_and_timezone():
    g = pd.read_csv(PROC / "group_totals.csv")
    assert (g.reach_dedup <= g.reach_naive).all() and g.reach_dedup.sum() < g.reach_naive.sum()
    t = pd.read_csv(PROC / "dq_timezone.csv").set_index("market")
    assert t.loc[sim.UTC_EXPORT, "median_hour_local"] > t.loc[sim.UTC_EXPORT, "median_hour_exported"]


# ---------- privacy of what is published ----------
def test_no_text_or_accounts_in_public_outputs():
    m = pd.read_csv(ROOT / "data" / "public" / "mastodon_sample.csv")
    assert not {"content", "text", "account", "acct", "username", "url"} & set(m.columns)
    assert "text" not in pd.read_csv(PROC / "comments_scored.csv", nrows=5).columns
    yt = ROOT / "data" / "public" / "youtube_creator_videos.csv"
    if yt.exists():
        assert "channel_real" not in pd.read_csv(yt, nrows=5).columns


def test_facts_file_is_json():
    assert json.loads((PROC / "facts.json").read_text(encoding="utf-8"))["events_found"] == 8
