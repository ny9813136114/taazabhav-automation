"""
Standalone daily script: posts a state-wise "trending mandi bhav" message to
a single shared PUBLIC Telegram channel.

This is completely independent from main.py / the YouTube pipeline -- if
this script fails, video uploads are unaffected (and vice versa). It
fetches its own wider pool of commodities (not just the 5 YouTube
targets) so the channel shows a richer, "today's biggest movers" picture
instead of a fixed onion/potato/tomato list.

Needs these environment variables (same secrets already used elsewhere in
this repo):
  DATA_GOV_API_KEY   -- used internally by fetch_prices.fetch_all_states()
  TELEGRAM_BOT_TOKEN -- the existing TaazaBhavAlerts_bot token

The bot must be added as an ADMIN (with "Post Messages" permission) in
the single public channel named below. It's public with a fixed
@username, so no numeric chat_id lookup is needed -- the @username
itself works as the chat_id.

One channel, 5 states: every morning the bot posts 5 separate messages
(one per state) into this same channel, one after another.

--- Reliability note (Phase 1A) ---
This used to call fetch_prices(state=state, commodity=commodity_name) once
per (state, commodity) pair: 5 states x 25 commodities = 125 sequential
upstream calls. But fetch_prices() itself already fetches ALL states for a
given commodity in a single request before filtering locally to one state
-- so the old loop order (state outer, commodity inner) was calling the
network for the SAME commodity's all-state data 5 times over, once per
state, purely because of loop order. This version fetches each of the 25
commodities' all-state data exactly ONCE (see _fetch_all_commodities()),
then filters to each state locally in memory -- an 80% reduction in
upstream calls, with no change to what gets posted. Those 25 fetches run
with modest bounded concurrency (MAX_CONCURRENT_FETCHES) and each one
retries transient failures internally (see fetch_prices.py's retry
policy), which is what actually keeps this workflow inside its 10-minute
budget: the previous, fully-serial version had already been observed
exceeding it and getting cancelled by GitHub Actions.
"""
import os
import sys
import json
import time
import traceback
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from fetch_prices import fetch_all_states, filter_by_state, clean_records
from notify import send_telegram_alert
from hindi_names import inr

# ---- Single shared channel -- every state's message goes here. ------------
CHANNEL = "@taazabhav"

# ---- States covered (same 5 as the YouTube pipeline's TARGETS). -----------
STATES = ["Uttar Pradesh", "Maharashtra", "West Bengal", "Karnataka", "Punjab"]

# How many commodity fetches run in flight at once. data.gov.in has
# confirmed intermittent 5xx errors in production, so this is deliberately
# modest (not "fetch all 25 at once") -- enough to fit comfortably inside
# the workflow's 10-minute timeout without hammering an already-flaky
# upstream harder than necessary.
MAX_CONCURRENT_FETCHES = 8

# ---- Wider commodity pool for the channel broadcast (kept separate from
# main.py's TARGETS -- this can grow independently of the YouTube side).
# Tuples are (name passed to fetch_prices, Hindi display name, emoji).
#
# IMPORTANT: the first value must match data.gov.in's Agmarknet commodity
# spelling exactly, or that item just returns no data. A wrong spelling
# does NOT crash anything -- _fetch_all_commodities() below treats "no
# records" as "skip this item" and moves on. After the first real run,
# check the Action log / Telegram alert for a summary of which names
# returned zero data, and fix just those entries here.
COMMODITY_POOL = [
    ("Onion", "Pyaz", "\U0001F9C5"),
    ("Potato", "Aloo", "\U0001F954"),
    ("Tomato", "Tamatar", "\U0001F345"),
    ("Garlic", "Lehsun", "\U0001F9C4"),
    ("Ginger", "Adrak", "\U0001FADA"),
    ("Green Chilli", "Hari Mirch", "\U0001F336"),
    ("Cabbage", "Patta Gobi", "\U0001F96C"),
    ("Cauliflower", "Phool Gobi", "\U0001F966"),
    ("Brinjal", "Baingan", "\U0001F346"),
    ("Bhindi", "Bhindi", "\U0001FAD8"),
    ("Green Peas", "Matar", "\U0001F7E2"),
    ("Capsicum", "Shimla Mirch", "\U0001FAD1"),
    ("Carrot", "Gajar", "\U0001F955"),
    ("Lemon", "Nimbu", "\U0001F34B"),
    ("Coriander", "Dhaniya", "\U0001F33F"),
    ("Cucumbar", "Kheera", "\U0001F952"),
    ("French Beans", "Beans", "\U0001FADB"),
    ("Spinach", "Palak", "\U0001F96C"),
    ("Raddish", "Mooli", "\U000026AA"),
    ("Pumpkin", "Kaddu", "\U0001F383"),
    ("Bitter Gourd", "Karela", "\U0001F952"),
    ("Bottle Gourd", "Lauki", "\U0001F952"),
    ("Sweet Potato", "Shakarkandi", "\U0001F360"),
    ("Banana", "Kela", "\U0001F34C"),
    ("Apple", "Seb", "\U0001F34E"),
]

HISTORY_DIR = "data/telegram_history"
TOP_N = 15


IST = timezone(timedelta(hours=5, minutes=30))


def _state_price(state_records):
    """(Batch 5, 27 Sep 2026) The state's representative price: the MEDIAN
    of one-row-per-mandi modal prices, plus the mandi count.

    Before: this took state_records[0] -- simply the first raw row the API
    returned (any mandi, any variety, often with paise). So "Pyaz Rs.X" was
    a random mandi's price, and the "+N% kal se" compared one random mandi
    today with a DIFFERENT random mandi yesterday -- fake movers."""
    rows = clean_records(state_records)
    if not rows:
        return None, 0
    prices = sorted(r["modal_price"] for r in rows)
    n = len(prices)
    median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2] + 1) // 2
    return median, n


def _data_date(records):
    """Latest arrival_date (dd/mm/yyyy) in the rows, as a date, or None."""
    best = None
    for r in records:
        try:
            d = datetime.strptime(str(r.get("arrival_date", "")).strip(), "%d/%m/%Y").date()
        except ValueError:
            continue
        if best is None or d > best:
            best = d
    return best


def _fetch_all_commodities(skip=None):
    """Fetches ALL-STATE records for every pooled commodity exactly once,
    with bounded concurrency. Returns {commodity_name: list[record] or None}
    -- None means that commodity's fetch permanently failed; callers must
    treat None as "skip this commodity everywhere today", the same way a
    per-item empty result was already treated before this change, while
    also surfacing it as a real failure (see main()).

    Catches Exception broadly, not just DataFetchError: this preserves the
    original _fetch_commodity()'s "one item's failure never stops the
    whole run" guarantee for ANY exception a single commodity's fetch can
    raise (e.g. a malformed/non-JSON response body), not only the ones
    fetch_prices.py happens to classify as DataFetchError. This function
    has no surrounding try/except at its own call site in main(), so an
    exception escaping here would otherwise crash the entire broadcast for
    all 5 states, silently (before any per-state Telegram alert fires)."""
    results = dict(skip or {})
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FETCHES) as pool:
        future_to_name = {
            pool.submit(fetch_all_states, name): name
            for name, _, _ in COMMODITY_POOL if name not in results
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception as e:
                print(f"[telegram_broadcast] Permanent fetch failure for commodity '{name}': {e}")
                results[name] = None
    return results


def _history_path(state):
    safe = state.replace(" ", "_")
    return os.path.join(HISTORY_DIR, f"{safe}.json")


def _load_previous(state, today):
    """Returns the previous post's {commodity: price} ONLY if it is from the
    day before `today`. After an outage the file can be days old; comparing
    with it and calling it "kal se" was wrong. Old files (flat dict, no
    date, first-raw-row prices) are ignored once, so no fake % on day 1."""
    path = _history_path(state)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict) or "date" not in data or "prices" not in data:
        return {}
    if data["date"] != (today - timedelta(days=1)).isoformat():
        return {}
    return data["prices"]


def _save_today(state, today, prices_by_commodity):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(_history_path(state), "w", encoding="utf-8") as f:
        json.dump({"date": today.isoformat(), "prices": prices_by_commodity}, f, ensure_ascii=False, indent=2)


def _post_to_channel(bot_token, channel, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, data={"chat_id": channel, "text": text}, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Telegram post to {channel} failed: HTTP {resp.status_code} -- {resp.text}"
        )


def _build_message(state, date_str, today_prices, yesterday_prices, counts=None):
    """today_prices / yesterday_prices: {commodity_name: median modal (int, Rs/quintal)}.
    Returns the message text, or None if there's nothing to show at all."""
    rows = []
    for commodity_name, hindi_name, emoji in COMMODITY_POOL:
        today_p = today_prices.get(commodity_name)
        if today_p is None:
            continue
        yday_p = yesterday_prices.get(commodity_name)
        pct = (today_p - yday_p) / yday_p * 100 if yday_p else None
        n = (counts or {}).get(commodity_name)
        rows.append((hindi_name, emoji, today_p, pct, n))

    if not rows:
        return None

    have_trend = any(r[3] is not None for r in rows)
    if have_trend:
        top = sorted(rows, key=lambda r: abs(r[3]) if r[3] is not None else -1, reverse=True)[:TOP_N]
        header = "\U0001F33E TAAZABHAV - Aaj Ke TRENDING Mandi Bhav \U0001F33E"
        footer_note = "\U0001F4CA Ye wahi items hain jinke bhav mein aaj sabse zyada uttar-chadhaav hua"
    else:
        # Day 1 (or a lost/reset history file) -- no comparison possible
        # yet, so just show the pool as a plain rate card.
        top = rows[:TOP_N]
        header = "\U0001F33E TAAZABHAV - Aaj Ka Mandi Bhav \U0001F33E"
        footer_note = "\U0001F4CA Kal se trend dikhna shuru hoga"

    lines = [header, f"\U0001F4C5 {date_str} | \U0001F4CD {state}", ""]
    for hindi_name, emoji, price, pct, n in top:
        # Rs/kg first (what people understand), quintal for traders.
        kg = price / 100
        kg_str = f"{kg:.0f}" if kg >= 10 else f"{kg:.1f}"
        price_str = f"₹{kg_str}/kg (₹{inr(price)}/qtl)"
        mandis = f" · {n} mandi" if n else ""
        if pct is None or abs(pct) < 0.5:
            tail = "" if pct is None else " (kal jaisa)"
            lines.append(f"{emoji} {hindi_name}: {price_str}{mandis}{tail}")
        else:
            arrow = "\U0001F53A" if pct > 0 else "\U0001F53B"
            lines.append(f"{arrow} {hindi_name}: {price_str}{mandis} ({pct:+.0f}% kal se)")

    lines += [
        "",
        "━" * 12,
        footer_note,
        "ℹ️ Bhav = sabhi mandiyon ka beech ka (median) thok bhav. Source: Agmarknet (Govt of India)",
        "✅ Roz subah yahi update yahin milega",
        # Was youtube.com/@TaazaBhav -- that handle is a DIFFERENT (2023)
        # mandi channel, not ours. Ours is @TaazaBhavIN (fixed 26 Sep 2026).
        "🌐 Har mandi ka poora bhav: taazabhav.com",
        "▶️ Roz ka video: youtube.com/@TaazaBhavIN",
        "",
        "#TaazaBhav #MandiBhav",
    ]
    return "\n".join(lines)


def run_for_state(state, channel, bot_token, date_str, all_commodity_records, today=None):
    """all_commodity_records: the dict returned by _fetch_all_commodities()
    -- {commodity_name: list[record] or None}, already fetched once for
    every state, filtered here locally (no network calls in this
    function)."""
    today = today or datetime.now(IST).date()
    yesterday = _load_previous(state, today)
    today_prices = {}
    counts = {}
    missing = []
    for commodity_name, hindi_name, emoji in COMMODITY_POOL:
        all_state_records = all_commodity_records.get(commodity_name)
        if all_state_records is None:
            missing.append(f"{commodity_name} (fetch failed)")
            continue
        state_records = filter_by_state(all_state_records, state)
        if not state_records:
            missing.append(commodity_name)
            continue
        price, n = _state_price(state_records)
        if price is None:
            missing.append(commodity_name)
            continue
        today_prices[commodity_name] = price
        counts[commodity_name] = n

    if missing:
        print(f"[{state}] No data for: {', '.join(missing)} (skipped, not a state-level failure).")

    if not today_prices:
        print(f"[{state}] No data at all for any pooled commodity today -- skipping broadcast.")
        return

    message = _build_message(state, date_str, today_prices, yesterday, counts)
    if message is None:
        print(f"[{state}] Nothing to post.")
        return

    _post_to_channel(bot_token, channel, message)
    print(f"[{state}] Posted to {channel} ({len(today_prices)} items fetched).")
    _save_today(state, today, today_prices)


def main():
    """Returns a process exit code: 0 if the broadcast completed with no
    real failures, non-zero if at least one commodity's fetch permanently
    failed or at least one state's post failed. A day with legitimately no
    data for some/all commodities (a normal, expected outcome -- see
    run_for_state()'s `missing` handling) is NOT a failure. Every state is
    still attempted regardless of how an earlier one ended."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not set -- skipping Telegram broadcast entirely.")
        return 0

    today = datetime.now(IST).date()  # runner clock is UTC

    # Fail fast (Batch 5): one probe before 25 commodities x up to 12 pages.
    # When data.gov.in is down, the old code spent 6+ minutes timing out on
    # every commodity (and with the 60 s timeout it would pass the job's
    # limit and be cancelled), then sent a 25-name alert. Now: one clear
    # alert, exit in about 3 minutes.
    try:
        probe = fetch_all_states(COMMODITY_POOL[0][0])
    except Exception as e:  # any failure -- never crash the process
        print(f"[telegram_broadcast] data.gov.in is not responding, skipping today: {e}")
        send_telegram_alert(f"TaazaBhav ALERT: data.gov.in down -- Telegram broadcast skipped today.\n\n{e}")
        return 1

    all_commodity_records = _fetch_all_commodities(skip={COMMODITY_POOL[0][0]: probe})

    # Label the post with the DATA's date, not the run date: if the API is
    # serving an older day, readers must see that.
    data_day = _data_date(r for recs in all_commodity_records.values() if recs for r in recs)
    date_str = (data_day or today).strftime("%d %b %Y")
    if data_day and data_day < today - timedelta(days=1):
        date_str += " (latest available)"
    failed_commodities = [name for name, recs in all_commodity_records.items() if recs is None]
    if failed_commodities:
        print(f"[telegram_broadcast] {len(failed_commodities)} commodity fetch(es) permanently failed: {failed_commodities}")

    failed_states = []
    for i, state in enumerate(STATES):
        try:
            run_for_state(state, CHANNEL, bot_token, date_str, all_commodity_records, today)
        except Exception as e:
            print(f"Error broadcasting for {state}: {e}")
            traceback.print_exc()
            send_telegram_alert(
                f"TaazaBhav ALERT: Telegram channel broadcast failed for {state}\n\n{e}"
            )
            failed_states.append(state)
        if i < len(STATES) - 1:
            time.sleep(3)  # small gap between back-to-back posts to the same channel

    if failed_commodities or failed_states:
        if failed_commodities:
            send_telegram_alert(
                "TaazaBhav ALERT: Telegram broadcast had permanent data fetch failures for: "
                + ", ".join(failed_commodities)
            )
        print(f"\nTelegram broadcast finished with failures. failed_commodities={failed_commodities} failed_states={failed_states}")
        return 1

    print("\nTelegram broadcast finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
