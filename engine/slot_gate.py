# -*- coding: utf-8 -*-
"""Runs each engine series once per slot, whoever starts it (18 Oct 2026).

The Supabase clock (ops/supabase-clock.sql) starts each series at its exact
time. GitHub's own schedule stays as a fallback, but GitHub starts it hours
late (D's 12:30 IST run started at 17:24 IST on 18 Oct), so it must not post
the same series twice:

  python -m engine.slot_gate check A   -> prints run=true|false (+ slot=...)
  python -m engine.slot_gate done A    -> records today's slot as done

A slot is the series' latest start time that has passed. A run more than
MAX_LATE hours after its slot is skipped: an evening video at 3 a.m. is
worse than none. Nothing posts between 23:00 and 06:00 IST either (20 Oct:
a late backup posted the 20:30 B video at 01:48 IST, titled for the next day). A fallback run that finds its slot not done means the
Supabase clock did not fire, so it alerts the owner (and still runs).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
SLOTS = {"A": (7, 30), "D": (12, 30), "C": (18, 30), "B": (20, 30)}  # IST
MAX_LATE = timedelta(hours=6)
NIGHT = (23, 6)  # IST hours [23:00, 06:00): no posting
STATE = Path("data/engine/slots.json")


def slot_start(series, now):
    h, m = SLOTS[series]
    start = now.astimezone(IST).replace(hour=h, minute=m, second=0, microsecond=0)
    # Started a little early (clock skew) still counts as today's slot.
    if start - now > timedelta(minutes=30):
        start -= timedelta(days=1)
    return start


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def decide(series, now, done, fallback):
    """-> (run, slot_date, note)."""
    start = slot_start(series, now)
    slot = start.date().isoformat()
    if done.get(series) == slot:
        return False, slot, "already done"
    hour = now.astimezone(IST).hour
    if now - start > MAX_LATE or hour >= NIGHT[0] or hour < NIGHT[1]:
        return False, slot, "too late"
    return True, slot, "clock missed" if fallback else ""


def tell_owner(text):
    """Telegram message to the owner. Plain urllib: this step runs before
    pip install. Never raises."""
    import urllib.parse
    import urllib.request
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print(text)
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=20)
    except Exception as e:
        print(f"alert not sent: {e}")


def main(argv):
    action, series = argv[0], argv[1].upper()
    now = datetime.now(timezone.utc)
    done = load()
    if action == "done":
        done[series] = slot_start(series, now).date().isoformat()
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(done, indent=1, sort_keys=True), encoding="utf-8")
        return 0
    fallback = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    run, slot, note = decide(series, now, done, fallback)
    print(f"[slot] {series} slot {slot}: {'run' if run else 'skip'} {note}".strip())
    if note in ("clock missed", "too late") and fallback:
        tell_owner(
            f"TaazaBhav: engine series {series} ({slot}) was not finished at its exact time "
            "(that run failed, see its own alert, or the Supabase clock did not start it). "
            + ("GitHub's late backup run is making it now." if run else "It is too late now, so this slot is skipped.")
            + " Check the Supabase clock and its GitHub token (ops/supabase-clock.sql).")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"run={'true' if run else 'false'}\nslot={slot}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
