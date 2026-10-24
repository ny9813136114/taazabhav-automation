# -*- coding: utf-8 -*-
"""Group kit: every evening the owner gets one Telegram message with all of
today's Facebook Page posts and Reels, so they can share each one into the
TaazaBhav Facebook group in a minute.

Meta removed posting to Groups from the Graph API in April 2024 (Graph API
v19: publish_to_groups gone), so no app can post in a group. Sharing the
Page's post into the group keeps the Page as the source, and the group sees
the full post with its link comment.

Posts nothing on the Page; only reads today's Page posts.

python -m posts.group_kit [send|dry] [YYYY-MM-DD]"""
import os
import sys
from datetime import date, datetime, time, timedelta

import requests

from posts.report import fb_posts
from posts.run import IST, _owner, _tg

MAX_TEXT = 3900  # Telegram's limit is 4096


def icon(row):
    link = row.get("link") or ""
    return "🎬" if "/reel/" in link or "/videos/" in link else "🖼"


def message(day, rows):
    rows = sorted(rows, key=lambda r: r["time"])
    if not rows:
        return None
    head = (f"👥 TaazaBhav ग्रुप के लिए आज ({day.strftime('%d %b')}) की {len(rows)} पोस्ट\n"
            "हर लिंक खोलें → Share → Group → TaazaBhav\n")
    lines = []
    for i, r in enumerate(rows, 1):
        hook = (r.get("hook") or "").strip() or "पोस्ट"
        lines.append(f"{i}. {icon(r)} {r['time'][11:16]} · {hook[:70]}\n{r['link']}")
    text = head
    for ln in lines:
        if len(text) + len(ln) + 2 > MAX_TEXT:
            text += "\n…बाकी पोस्ट Page पर देखें"
            break
        text += "\n" + ln + "\n"
    return text


def main():
    run_mode = sys.argv[1] if len(sys.argv) > 1 else "send"
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else datetime.now(IST).date()
    start = datetime.combine(day, time(0), IST)
    end = start + timedelta(days=1)
    import meta_publish as mp
    token, _ig = mp.page_credentials()
    rows = fb_posts(requests, os.environ["FB_PAGE_ID"], token, start, end, reach=False)
    text = message(day, [r for r in rows if r.get("link")])
    print(text or "[group_kit] no Page posts today")
    if run_mode == "dry" or not text:
        return 0
    _tg("sendMessage", {"chat_id": _owner(), "text": text, "disable_web_page_preview": "true"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
