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
    DATA_GOV_API_KEY   -- used internally by fetch_prices()
    TELEGRAM_BOT_TOKEN -- the existing TaazaBhavAlerts_bot token

The bot must be added as an ADMIN (with "Post Messages" permission) in
the single public channel named below. It's public with a fixed
@username, so no numeric chat_id lookup is needed -- the @username
itself works as the chat_id.

One channel, 5 states: every morning the bot posts 5 separate messages
(one per state) into this same channel, one after another.
"""
import os
import json
import time
import traceback
from datetime import datetime

import requests

from fetch_prices import fetch_prices
from notify import send_telegram_alert

# ---- Single shared channel -- every state's message goes here. ------------
CHANNEL = "@taazabhav"

# ---- States covered (same 5 as the YouTube pipeline's TARGETS). -----------
STATES = ["Uttar Pradesh", "Maharashtra", "West Bengal", "Karnataka", "Punjab"]

# ---- Wider commodity pool for the channel broadcast (kept separate from
# main.py's TARGETS -- this can grow independently of the YouTube side).
# Tuples are (name passed to fetch_prices, Hindi display name, emoji).
#
# IMPORTANT: the first value must match data.gov.in's Agmarknet commodity
# spelling exactly, or that item just returns no data. A wrong spelling
# does NOT crash anything -- _fetch_commodity() below treats "no records"
# as "skip this item" and moves on. After the first real run, check the
# Action log / Telegram alert for a summary of which names returned zero
# data, and fix just those entries here.
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


def _fetch_commodity(state, commodity_name):
    """Returns today's first/representative record for one commodity in
    one state, or None if there's no data or the call errored out. Callers
    must treat None as "skip" -- never as a reason to stop the whole run."""
    try:
        records = fetch_prices(state=state, commodity=commodity_name)
    except Exception:
        return None
    if not records:
        return None
    return records[0]


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
        "\u2501" * 12,
        footer_note,
        "\u2705 Roz subah yahi update yahin milega",
        "\u25B6\uFE0F Poora video dekhne ke liye: youtube.com/@TaazaBhav",
        "",
        "#TaazaBhav #MandiBhav",
    ]
    return "\n".join(lines)


def run_for_state(state, channel, bot_token, date_str):
    yesterday = _load_yesterday(state)
    today_prices = {}
    missing = []
    for commodity_name, hindi_name, emoji in COMMODITY_POOL:
        record = _fetch_commodity(state, commodity_name)
        if record is None:
            missing.append(commodity_name)
            continue
        today_prices[commodity_name] = _price_of(record)

    if missing:
        print(f"[{state}] No data for: {', '.join(missing)} (skipped, not an error).")

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
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not set -- skipping Telegram broadcast entirely.")
        return

    date_str = datetime.now().strftime("%d %b %Y")

    for i, state in enumerate(STATES):
        try:
            run_for_state(state, CHANNEL, bot_token, date_str)
        except Exception as e:
            print(f"Error broadcasting for {state}: {e}")
            traceback.print_exc()
            send_telegram_alert(
                f"TaazaBhav ALERT: Telegram channel broadcast failed for {state}\n\n{e}"
            )
        if i < len(STATES) - 1:
            time.sleep(3)  # small gap between back-to-back posts to the same channel


if __name__ == "__main__":
    main()
