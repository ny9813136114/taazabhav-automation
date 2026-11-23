# -*- coding: utf-8 -*-
"""The "demand reel" (23 Nov 2026, owner: "one yojana a day, and besides that
something new we try that people want"). Facebook and Instagram only.

First experiment: the mandi "badi khabar" Reel from taazabhav.com's own price
feed (the weekly Instagram outlier scan showed this format winning: a crop,
today's price, "bari khabar"). It uses the same checked builder as the old
bhav Short (stories.build_bhav: one searched mandi, price per kg, week change,
sanity checks against the national price) and takes the 17:00 Reel slot on the
days the MP Kisan Kalyan Reel is not posted. No price or number is made up:
no fresh prices = no reel (build_n returns None, slot stays quiet).

Preview on the owner's Telegram until the repo variable N_LIVE is "1"."""
import os
from datetime import date

from engine import feed as F
from engine import stories

MAX_STALE_DAYS = 2   # prices older than this (data.gov.in outage) are never "bari khabar"
BADGE = "मंडी की बड़ी खबर"


def demand_day(today):
    """True on the days the MP Kisan Kalyan Reel stays out (the 20:30 kist
    video is MP that day), so the 17:00 slot is otherwise empty."""
    return os.environ.get("B_ALT") != "0" and stories.alt_scheme(today) == "mpkalyan"


def _history(state, today, days=14):
    eps = [e for e in state.get("episodes", []) if e.get("series") == "A" and e.get("key")
           and (today - date.fromisoformat(e["date"])).days < days]
    return [e["key"] for e in reversed(eps)]


def build_n(today, state):
    feed = F.load_feed(today)
    latest = feed.get("latestDate")
    if not latest or not feed.get("mandis"):
        return None
    if (today - date.fromisoformat(latest)).days > MAX_STALE_DAYS:
        print(f"[engine] N: newest prices are from {latest}, too old for a news reel")
        return None
    ep = stories.build_bhav(feed, today, _history(state, today))
    if not ep:
        return None
    ep["meta_only"] = True
    ep["demand"] = True
    ep["scheme"] = "bhavn"
    ep["badge"] = BADGE
    return ep
