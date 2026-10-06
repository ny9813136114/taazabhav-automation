# -*- coding: utf-8 -*-
"""Story engine (Batch 3, 27 Sep 2026): each scheduled slot picks the
strongest story of the day instead of a fixed state/crop.

Why: 69 Shorts in three weeks covered the same 5 fixed targets (UP onion,
MH onion, WB potato, KA tomato, PB potato) and views fell from 100-220 to
2-60 per Short. A fixed target means the same video every day, whether or
not anything happened. Now the data chooses: a crop-state pair where the
gap between mandis is wide, or the price moved sharply since the last run,
or a mandi that people search for by name (Mandsaur ~4.1K/month, Neemuch
~3.6K/month on YouTube per vidIQ, 26 Sep) is reporting today.

How a slot run works (daily.yml sets YT_SLOT=1..5):
  1. Fetch each candidate commodity ONCE (fetch_all_states pages through
     every state), clean each state's rows (clean_records).
  2. Score every (state, commodity) pair that has enough markets.
  3. Skip pairs already published today (publish_state), so the five
     slots of one morning never repeat a pair. Each slot is a separate
     GitHub Actions job, and the previous slot's run commits its
     published_log before the next one checks out, so later slots see it.
  4. Return the top remaining pair plus its already-fetched records, so
     main.py does not fetch the same data a second time.

Fallback: if every fetch fails or nothing scores, the slot falls back to
the old fixed target for that slot, so a bad data day behaves exactly like
before this change.

Nothing here invents numbers: every score comes from the same cleaned
data.gov.in rows the video shows.
"""
import json
from pathlib import Path

from fetch_prices import fetch_all_states, filter_by_state, clean_records, DataFetchError
from price_history import load_yesterday_prices, _modal_price_of

# The pre-Batch-3 fixed targets, kept as the per-slot fallback.
FALLBACK_BY_SLOT = {
    1: ("Uttar Pradesh", "Onion"),
    2: ("Maharashtra", "Onion"),
    3: ("West Bengal", "Potato"),
    4: ("Karnataka", "Tomato"),
    5: ("Punjab", "Potato"),
}

# Commodity names exactly as the website's fetch-daily.mjs queries them
# (proven to return rows). Kharif arrival season (Oct-Nov): soyabean,
# cotton, maize, groundnut join the daily vegetables.
CANDIDATE_COMMODITIES = ["Onion", "Potato", "Tomato", "Soyabean", "Garlic", "Cotton", "Maize", "Groundnut"]

# States the channel's audience and the Hindi script cover well. A pair
# outside this list is ignored even if its data scores high.
CANDIDATE_STATES = [
    "Uttar Pradesh", "Maharashtra", "Madhya Pradesh", "Rajasthan", "Gujarat",
    "Haryana", "Punjab", "West Bengal", "Karnataka", "Bihar",
]

# Mandis people search for by name on YouTube (vidIQ, IN, 26 Sep 2026).
SEARCHED_MANDIS = {"mandsaur": 4126, "neemuch": 3587}

# The day's ranking is computed ONCE (by whichever slot runs first) and
# saved here; later slots reuse it and only fetch their own chosen crop.
# Without this, 5 slots x 8 crops x 2-3 pages = ~100 calls a morning to an
# API that was already timing out (26-27 Sep 2026). Committed by the
# workflow's "Commit price history" step alongside data/published/.
STORIES_DIR = Path("data/stories")

MIN_MARKETS = 3          # a "gap between mandis" story needs at least 3 mandis
SPREAD_CAP = 1.0         # cap spread credit at 100% so one outlier row can't dominate
SHOCK_CAP = 0.30         # cap day-over-day move credit at 30%


def _modal(r):
    try:
        return float(r.get("modal_price"))
    except (TypeError, ValueError):
        return None


def score_pair(records, yesterday_prices=None):
    """Returns (score, story_type, details) for one state's cleaned records
    (highest modal first). story_type is "spread", "shock", "searched" or
    "best". Score is 0 when there isn't enough data to say anything."""
    prices = [p for p in (_modal(r) for r in records) if p]
    if len(prices) < MIN_MARKETS:
        return 0.0, None, {}
    high, low = max(prices), min(prices)
    spread = (high - low) / low if low > 0 else 0.0

    shock = 0.0
    if yesterday_prices:
        old = [p for p in (_safe_float(_modal_price_of(v)) for v in yesterday_prices.values()) if p]
        if old:
            old_avg = sum(old) / len(old)
            new_avg = sum(prices) / len(prices)
            if old_avg > 0:
                shock = abs(new_avg - old_avg) / old_avg

    searched = 0
    names = " ".join(str(r.get("market", "")).lower() for r in records)
    for mandi, volume in SEARCHED_MANDIS.items():
        if mandi in names:
            searched = max(searched, volume)

    s_spread = min(spread, SPREAD_CAP)
    s_shock = min(shock, SHOCK_CAP) / SHOCK_CAP  # 0..1
    s_search = 0.6 if searched else 0.0
    score = s_spread + s_shock + s_search + min(len(prices), 20) / 100

    parts = {"spread": s_spread, "shock": s_shock, "searched": s_search}
    story = max(parts, key=parts.get) if max(parts.values()) > 0.25 else "best"
    return round(score, 4), story, {
        "spread": round(spread, 3), "shock": round(shock, 3),
        "searched_mandi_volume": searched, "markets": len(prices),
    }


def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def rank_candidates(fetch=fetch_all_states, load_yesterday=load_yesterday_prices,
                    commodities=CANDIDATE_COMMODITIES, states=CANDIDATE_STATES):
    """Scores every candidate pair. Returns a list of dicts sorted best
    first: {state, commodity, score, story, details, records}. Commodities
    whose fetch fails are skipped (logged), never fatal."""
    ranked = []
    for commodity in commodities:
        try:
            all_rows = fetch(commodity)
        except DataFetchError as e:
            print(f"[pick_story] {commodity}: fetch failed, skipping ({e})")
            continue
        for state in states:
            recs = clean_records(filter_by_state(all_rows, state))
            if len(recs) < MIN_MARKETS:
                continue
            score, story, details = score_pair(recs, load_yesterday(state, commodity))
            if score > 0:
                ranked.append({
                    "state": state, "commodity": commodity, "score": score,
                    "story": story, "details": details, "records": recs,
                })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def choose_for_slot(slot, run_date, is_published, ranked):
    """Best pair not yet published today. Diversity rule: a slot never
    repeats a commodity that is already published today while another
    commodity is still available, so one morning isn't five onion videos.
    Returns (state, commodity, records_or_None, reason)."""
    today = run_date.isoformat()
    unpublished = [c for c in ranked if not is_published(today, c["state"], c["commodity"])]
    published_commodities = {
        c["commodity"] for c in ranked if is_published(today, c["state"], c["commodity"])
    }
    fresh = [c for c in unpublished if c["commodity"] not in published_commodities]
    pool = fresh or unpublished
    if pool:
        top = pool[0]
        return top["state"], top["commodity"], top["records"], (
            f"story={top['story']} score={top['score']} {top['details']}"
        )
    state, commodity = FALLBACK_BY_SLOT.get(int(slot), FALLBACK_BY_SLOT[1])
    return state, commodity, None, "fallback: no scored candidate available"


def save_snapshot(run_date, ranked):
    """Writes the day's ranking without the raw records (small file)."""
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
    rows = [{k: v for k, v in c.items() if k != "records"} for c in ranked]
    path = STORIES_DIR / f"{run_date.isoformat()}.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    # keep only the last 14 days of snapshots
    for old in sorted(STORIES_DIR.glob("*.json"))[:-14]:
        old.unlink()


def load_snapshot(run_date):
    """The ranking an earlier slot saved today, or None. Rows carry no
    records, so the caller fetches the chosen pair itself."""
    path = STORIES_DIR / f"{run_date.isoformat()}.json"
    if not path.exists():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    for r in rows:
        r["records"] = None
    return rows or None


def ranked_for_today(run_date):
    """Reuse today's saved ranking if an earlier slot made one; otherwise
    score everything now and save it for the later slots."""
    snap = load_snapshot(run_date)
    if snap is not None:
        print(f"[pick_story] reusing today's ranking ({len(snap)} pairs)")
        return snap
    ranked = rank_candidates()
    if ranked:
        save_snapshot(run_date, ranked)
    return ranked
