import os
import requests


def annotate(message):
    """On GitHub Actions, also print the alert as an error annotation, so a
    failed run says why on its summary page (raw logs are not always
    reachable) instead of only "Process completed with exit code 1"."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    text = str(message).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error::{text}")


def send_telegram_alert(message):
    """Sends message to the configured Telegram chat via the Bot API.

    Deliberately fails silent: if TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID aren't
    set (e.g. secrets not configured yet), or the Telegram API call itself
    errors out (network hiccup, bad token), this just prints a note and
    returns -- it never raises. An alerting helper that can itself crash the
    pipeline would defeat the point: a failure notification going missing is
    fine, but it must never turn one real failure into two.
    """
    annotate(message)
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Telegram alert skipped: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set.")
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        resp = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=15)
        if resp.status_code != 200:
            print(f"Telegram alert failed: HTTP {resp.status_code} -- {resp.text}")
        else:
            print("Telegram alert sent.")
    except Exception as e:
        print(f"Telegram alert failed to send: {e}")
