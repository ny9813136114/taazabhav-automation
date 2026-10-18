"""
Standalone daily script: posts a state-wise "trending mandi bhav" message to
the public Telegram channel @taazabhav, one message per state.

18 Oct 2026: prices now come from taazabhav.com itself
(/api/home-tools/state/<state>, the same numbers the site shows), not from
data.gov.in. data.gov.in refuses GitHub's (non-Indian) runners, so every run
from 24 Sep to 18 Oct 2026 failed and the channel got nothing. The site
saves the day's prices from an Indian server, and that route is cached for a
day and refreshed after each price pull, so this costs no extra database
reads. Each state's message uses the site's state median per crop and the
site's own "since the previous report day" change.

Started at a fixed time by the Supabase clock (ops/supabase-clock.sql). The
GitHub schedule is only a fallback and posts nothing if today's broadcast
already went out (data/telegram_history/_last_post.json).

Needs TELEGRAM_BOT_TOKEN (the bot is an admin of the channel) and, for
alerts, TELEGRAM_CHAT_ID.
"""
import os
import sys
import json
import time
import traceback
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

from notify import send_telegram_alert
from hindi_names import inr

# ---- Single shared channel -- every state's message goes here. ------------
CHANNEL = "@taazabhav"

# ---- States covered (same 5 as the YouTube pipeline's TARGETS). -----------
STATES = ["Uttar Pradesh", "Maharashtra", "West Bengal", "Karnataka", "Punjab"]

SITE = os.environ.get("TAAZABHAV_SITE", "https://taazabhav.com")

# ---- Wider commodity pool for the channel broadcast (kept separate from
# main.py's TARGETS -- this can grow independently of the YouTube side).
# Tuples are (name passed to fetch_prices, Hindi display name, emoji).
#
# The first value is the Agmarknet name. Where the site's crop name differs
# (a bracketed variety or different case), SITE_NAMES says which one to use;
# a crop the site doesn't have for a state is simply left out.
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

SITE_NAMES = {
    "Ginger": "Ginger(Green)",
    "Bhindi": "Bhindi(Ladies Finger)",
    "Coriander": "Coriander(Leaves)",
    "Cucumbar": "Cucumbar(Kheera)",
    "French Beans": "French Beans(Frasbean)",
}

HISTORY_DIR = "data/telegram_history"
TOP_N = 15


IST = timezone(timedelta(hours=5, minutes=30))


def _slug(state):
    return state.lower().replace(" ", "-")


def _site_name(name, available):
    want = SITE_NAMES.get(name, name)
    if want in available:
        return want
    low = want.lower()
    return next((n for n in available if n.lower() == low), None)


def fetch_state(state, attempts=3):
    """The site's data for one state: {"byState": {crop: {typical, count,
    latestDate, ...}}, "stateMoves": [[crop, dayPct, weekPct, ...], ...]}.
    Retries a few times; raises on a persistent failure."""
    url = f"{SITE}/api/home-tools/state/{quote(_slug(state))}"
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "taazabhav-telegram"})
            if r.status_code == 200:
                data = r.json()
                if isinstance(data.get("byState"), dict) and data["byState"]:
                    return data
                last = RuntimeError(f"{url}: no prices in the answer")
            else:
                last = RuntimeError(f"{url}: HTTP {r.status_code}")
        except Exception as e:  # network error or bad JSON
            last = e
        if i < attempts - 1:
            time.sleep(10 * (i + 1))
    raise last


def state_prices(data):
    """-> (prices {pool name: median Rs/qtl}, counts, pct {pool name: % since
    the previous report day}, newest data date)."""
    by_state = data.get("byState") or {}
    moves = {}
    for row in data.get("stateMoves") or []:
        if isinstance(row, list) and len(row) >= 2 and row[1] is not None:
            moves[row[0]] = row[1]
    prices, counts, pct, newest = {}, {}, {}, None
    for name, _, _ in COMMODITY_POOL:
        site = _site_name(name, by_state)
        if not site:
            continue
        s = by_state[site]
        if not s.get("typical"):
            continue
        prices[name] = int(round(s["typical"]))
        counts[name] = s.get("count")
        if site in moves:
            pct[name] = moves[site]
        d = s.get("latestDate") or ""
        if d and (newest is None or d > newest):
            newest = d
    return prices, counts, pct, newest


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


def _build_message(state, date_str, today_prices, yesterday_prices, counts=None, pct_by_name=None):
    """today_prices / yesterday_prices: {commodity_name: median modal (int, Rs/quintal)}.
    pct_by_name: the site's own % change, used before yesterday_prices.
    Returns the message text, or None if there's nothing to show at all."""
    rows = []
    for commodity_name, hindi_name, emoji in COMMODITY_POOL:
        today_p = today_prices.get(commodity_name)
        if today_p is None:
            continue
        yday_p = yesterday_prices.get(commodity_name)
        if pct_by_name and commodity_name in pct_by_name:
            pct = pct_by_name[commodity_name]
        else:
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
        "ℹ️ Bhav = sabhi mandiyon ka beech ka (median) thok bhav, pichhle report din se badlav. Source: Agmarknet (Govt of India)",
        "✅ Roz dopahar yahi update yahin milega",
        # Was youtube.com/@TaazaBhav -- that handle is a DIFFERENT (2023)
        # mandi channel, not ours. Ours is @TaazaBhavIN (fixed 26 Sep 2026).
        "🌐 Har mandi ka poora bhav: taazabhav.com",
        "▶️ Roz ka video: youtube.com/@TaazaBhavIN",
        "",
        "#TaazaBhav #MandiBhav",
    ]
    return "\n".join(lines)


LAST_POST = os.path.join(HISTORY_DIR, "_last_post.json")


def _already_posted(data_date):
    try:
        with open(LAST_POST, encoding="utf-8") as f:
            return json.load(f).get("date") == data_date
    except (OSError, ValueError, AttributeError):
        return False


def _mark_posted(data_date):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(LAST_POST, "w", encoding="utf-8") as f:
        json.dump({"date": data_date}, f)


def run_for_state(state, channel, bot_token, date_str, data, today=None):
    """data: this state's answer from fetch_state(). Posts one message."""
    today = today or datetime.now(IST).date()
    yesterday = _load_previous(state, today)
    today_prices, counts, pct, _ = state_prices(data)
    if not today_prices:
        print(f"[{state}] No pooled crop on the site for this state today -- skipping.")
        return False
    message = _build_message(state, date_str, today_prices, yesterday, counts, pct)
    if message is None:
        return False
    _post_to_channel(bot_token, channel, message)
    print(f"[{state}] Posted to {channel} ({len(today_prices)} crops).")
    _save_today(state, today, today_prices)
    return True


def main():
    """0 when every state was posted (or today's post already went out),
    1 when the site could not be read or a post failed. The owner gets a
    Telegram alert for every failure."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not set -- skipping Telegram broadcast entirely.")
        return 0

    today = datetime.now(IST).date()  # runner clock is UTC
    data, failed = {}, []
    for state in STATES:
        try:
            data[state] = fetch_state(state)
        except Exception as e:
            print(f"[{state}] could not read the site: {e}")
            failed.append(state)
    if not data:
        send_telegram_alert(
            "TaazaBhav ALERT: Telegram channel broadcast skipped -- taazabhav.com prices could not be read.\n\n"
            + ", ".join(failed))
        return 1

    newest = max((state_prices(d)[3] or "" for d in data.values()), default="")
    if newest and _already_posted(newest):
        print(f"Broadcast for {newest} already posted -- nothing to do.")
        return 0
    try:
        data_day = datetime.strptime(newest, "%Y-%m-%d").date()
    except ValueError:
        data_day = None
    # Label the post with the DATA's date, not the run date.
    date_str = (data_day or today).strftime("%d %b %Y")
    if data_day and data_day < today - timedelta(days=1):
        date_str += " (latest available)"

    posted = 0
    for i, state in enumerate(STATES):
        if state not in data:
            continue
        try:
            if run_for_state(state, CHANNEL, bot_token, date_str, data[state], today):
                posted += 1
        except Exception as e:
            print(f"Error broadcasting for {state}: {e}")
            traceback.print_exc()
            failed.append(state)
        if i < len(STATES) - 1:
            time.sleep(3)  # small gap between back-to-back posts to the same channel

    if posted and newest:
        _mark_posted(newest)
    if failed:
        send_telegram_alert("TaazaBhav ALERT: Telegram channel broadcast failed for: " + ", ".join(failed))
        print(f"\nTelegram broadcast finished with failures: {failed}")
        return 1
    print(f"\nTelegram broadcast finished: {posted} state(s) posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
