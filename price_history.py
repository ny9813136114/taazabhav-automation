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


def save_today_prices(state, commodity, records):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _history_file(state, commodity)
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    today = date.today().isoformat()
    history[today] = {
        r.get("market", ""): r.get("modal_price", "N/A") for r in records
    }

    for old_date in sorted(history.keys())[:-14]:
        del history[old_date]

    path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def compute_trend(yesterday_prices, market, today_price):
    try:
        old_price = float(yesterday_prices.get(market))
        new_price = float(today_price)
    except (TypeError, ValueError):
        return None
    if old_price == 0:
        return None

    pct = round(((new_price - old_price) / old_price) * 100, 1)
    if abs(pct) < 0.5:
        return ("flat", 0)
    return ("up" if pct > 0 else "down", abs(pct))