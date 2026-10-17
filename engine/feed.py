# -*- coding: utf-8 -*-
"""Reads taazabhav.com/api/yt-feed: the newest Mandi Samachar reports, a
sell signal per crop and the kist status, so every video says exactly what
the site says. The route is cached for a day; if the copy is from before
today's price pull, one more request after a pause gets the refreshed copy
(Next serves the old copy once while it rebuilds)."""
import json
import os
import time
from datetime import date
from pathlib import Path

import requests

FEED_URL = os.environ.get("ENGINE_FEED_URL", "https://taazabhav.com/api/yt-feed")
STATE = Path("data/engine/published.json")


class FeedError(Exception):
    pass


def _get():
    r = requests.get(FEED_URL, timeout=90, headers={"User-Agent": "TaazaBhav-engine/1.0"})
    if r.status_code != 200:
        raise FeedError(f"yt-feed HTTP {r.status_code}")
    data = r.json()
    if "reports" not in data:
        raise FeedError("yt-feed has no reports")
    return data


def load_feed(today=None, want_today=False, sleep=time.sleep):
    """The feed as a dict. A local file (ENGINE_FEED_FILE) wins, for tests and
    previews. want_today: retry once if the newest report is older than today."""
    if os.environ.get("ENGINE_FEED_FILE"):
        return json.loads(Path(os.environ["ENGINE_FEED_FILE"]).read_text(encoding="utf-8"))
    data = _get()
    gen = (data.get("generatedAt") or "")[:10]
    stale = gen < (today or date.today()).isoformat() or (want_today and data.get("latestDate", "") < (today or date.today()).isoformat())
    if stale:
        sleep(45)
        try:
            data = _get()
        except FeedError:
            pass
    return data


# ---------------------------------------------------------------- published log
def load_state(path=STATE):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"episodes": []}


def save_state(state, path=STATE):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    state["episodes"] = state["episodes"][-400:]
    Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def recent_keys(state, series, today, days):
    """Story keys this series published in the last `days` days."""
    out = set()
    for e in state.get("episodes", []):
        if e.get("series") == series and (today - date.fromisoformat(e["date"])).days < days:
            out.add(e.get("key"))
    return out


def mark(state, series, key, today, video_id=None, title=None):
    state.setdefault("episodes", []).append(
        {"series": series, "key": key, "date": today.isoformat(), "video": video_id, "title": title})
