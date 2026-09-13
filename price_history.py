import json
from pathlib import Path
from datetime import date

HISTORY_DIR = Path("data/history")

def _history_file(state, commodity):
    slug = f"{state.lower().replace(' ', '-')}-{commodity.lower()}"
    return HISTORY_DIR / f"{slug}.json"

def load_yesterday_prices(state, commodity):
    path = _history_file(state, commodity)
    if not path.exists():
        return {}
    history = json.loads(path.read_text(encoding="utf-8"))
    dates = sorted(history.keys())
    if not dates:
        return {}
    return history[dates[-1]]

def _modal_price_of(stored_value):
    """A per-market value in data/history/*.json is either a bare number
    (the pre-Phase-1B-B schema -- still present in every file already on
    disk, and never rewritten by this change) or {"modal_price": ...,
    "arrival_date": ...} (the current schema, written going forward). This
    extracts the modal price either way, so compute_trend() keeps working
    against old AND new entries without any migration of existing files."""
    if isinstance(stored_value, dict):
        return stored_value.get("modal_price")
    return stored_value

def save_today_prices(state, commodity, records, run_date):
    """run_date: the canonical business date for this pipeline run (a
    datetime.date), supplied by main.py -- Phase 1B-B. Required, no
    fallback: this is the exact call site a real production incident
    traced back to a UTC-vs-IST date.today() disagreeing with the same
    run's video title.

    Each market's stored value also now carries the source's own
    `arrival_date` field alongside the existing modal_price (Phase 1B-B
    Part 6) -- captured verbatim, exactly as returned by data.gov.in,
    never invented when absent (stored as null) and never treated as
    equivalent to run_date: this is deliberately a separate, independent
    piece of information, not a replacement for the business date above.
    """
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _history_file(state, commodity)
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    today = run_date.isoformat()
    history[today] = {
        r.get("market", ""): {
            "modal_price": r.get("modal_price", "N/A"),
            "arrival_date": r.get("arrival_date"),
        }
        for r in records
    }

    for old_date in sorted(history.keys())[:-14]:
        del history[old_date]

    path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def compute_trend(yesterday_prices, market, today_price):
    try:
        old_price = float(_modal_price_of(yesterday_prices.get(market)))
        new_price = float(today_price)
    except (TypeError, ValueError):
        return None
    if old_price == 0:
        return None

    pct = round(((new_price - old_price) / old_price) * 100, 1)
    if abs(pct) < 0.5:
        return ("flat", 0)
    return ("up" if pct > 0 else "down", abs(pct))
