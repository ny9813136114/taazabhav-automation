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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from fetch_prices import fetch_all_states, filter_by_state
from notify import send_telegram_alert

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


def _price_of(record):
    try:
        return float(record.get("modal_price", 0))
    except (TypeError, ValueError):
        return 0.0


def _fetch_all_commodities():
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
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FETCHES) as pool:
        future_to_name = {
            pool.submit(fetch_all_states, name): name
            for name, _, _ in COMMODITY_POOL
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


def _load_yesterday(state):
    path = _history_path(state)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_today(state, prices_by_commodity):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(_history_path(state), "w", encoding="utf-8") as f:
        json.dump(prices_by_commodity, f, ensure_ascii=False, indent=2)


def _post_to_channel(bot_token, channel, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, data={"chat_id": channel, "text": text}, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Telegram post to {channel} failed: HTTP {resp.status_code} -- {resp.text}"
        )


def _build_message(state, date_str, today_prices, yesterday_prices):
    """today_prices / yesterday_prices: {commodity_name: modal_price(float)}.
    Returns the message text, or None if there's nothing to show at all."""
    rows = []
    for commodity_name, hindi_name, emoji in COMMODITY_POOL:
        today_p = today_prices.get(commodity_name)
        if today_p is None:
            continue
        yday_p = yesterday_prices.get(commodity_name)
        pct = (today_p - yday_p) / yday_p * 100 if yday_p else None
        rows.append((hindi_name, emoji, today_p, pct))

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
    for hindi_name, emoji, price, pct in top:
        price_str = f"Rs.{int(price)}/quintal"
        if pct is None:
            lines.append(f"{emoji} {hindi_name}: {price_str}")
        else:
            arrow = "\U0001F53A" if pct >= 0 else "\U0001F53B"
            lines.append(f"{arrow} {hindi_name}: {price_str} ({pct:+.0f}% kal se)")

    lines += [
        "",
        "━" * 12,
        footer_note,
        "✅ Roz subah yahi update yahin milega",
        # Was youtube.com/@TaazaBhav -- that handle is a DIFFERENT (2023)
        # mandi channel, not ours. Ours is @TaazaBhavIN (fixed 26 Sep 2026).
        "🌐 Har mandi ka poora bhav: taazabhav.com",
        "▶️ Roz ka video: youtube.com/@TaazaBhavIN",
        "",
        "#TaazaBhav #MandiBhav",
    ]
    return "\n".join(lines)


def run_for_state(state, channel, bot_token, date_str, all_commodity_records):
    """all_commodity_records: the dict returned by _fetch_all_commodities()
    -- {commodity_name: list[record] or None}, already fetched once for
    every state, filtered here locally (no network calls in this
    function)."""
    yesterday = _load_yesterday(state)
    today_prices = {}
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
        today_prices[commodity_name] = _price_of(state_records[0])

    if missing:
        print(f"[{state}] No data for: {', '.join(missing)} (skipped, not a state-level failure).")

    if not today_prices:
        print(f"[{state}] No data at all for any pooled commodity today -- skipping broadcast.")
        return

    message = _build_message(state, date_str, today_prices, yesterday)
    if message is None:
        print(f"[{state}] Nothing to post.")
        return

    _post_to_channel(bot_token, channel, message)
    print(f"[{state}] Posted to {channel} ({len(today_prices)} items fetched).")
    _save_today(state, today_prices)


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

    date_str = datetime.now().strftime("%d %b %Y")

    all_commodity_records = _fetch_all_commodities()
    failed_commodities = [name for name, recs in all_commodity_records.items() if recs is None]
    if failed_commodities:
        print(f"[telegram_broadcast] {len(failed_commodities)} commodity fetch(es) permanently failed: {failed_commodities}")

    failed_states = []
    for i, state in enumerate(STATES):
        try:
            run_for_state(state, CHANNEL, bot_token, date_str, all_commodity_records)
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
