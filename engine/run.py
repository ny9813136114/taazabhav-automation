# -*- coding: utf-8 -*-
"""One video for one series: python -m engine.run A|B|C|D

Mode: ENGINE_MODE=preview|publish (manual runs). Scheduled runs publish only
when the repo variable ENGINE_LIVE is "1"; until then the video goes to the
owner's Telegram as a preview. ENGINE_DRY=1 renders to engine-out/ and sends
nothing (local checks)."""
import os
import shutil
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine import feed as F
from engine import media, qa, stories, tools

IST = timezone(timedelta(hours=5, minutes=30))
RECENT_DAYS = {"A": 7, "B": 1, "C": 1, "D": 21}


def mode():
    m = (os.environ.get("ENGINE_MODE") or "").strip().lower()
    if m in ("publish", "preview"):
        return m
    return "publish" if os.environ.get("ENGINE_LIVE", "").strip() == "1" else "preview"


def alert(msg):
    try:
        from notify import send_telegram_alert
        send_telegram_alert(msg)
    except Exception:
        print(msg)


def build(series, today, state):
    recent = F.recent_keys(state, series, today, RECENT_DAYS[series])
    if series == "D":
        return tools.build_d(today, recent)
    feed = F.load_feed(today, want_today=(series == "C"))
    if series == "A":
        return stories.build_a(feed, today, recent)
    if series == "C":
        return stories.build_c(feed, today, recent)
    claim = None
    try:
        from engine.claims import fetch_titles, top_claim
        pm = next((k for k in feed.get("kist", []) if k["key"] == "pmkisan"), None)
        if pm and not pm["next"].get("officialDate") and os.environ.get("ENGINE_DRY") != "1":
            claim = top_claim(fetch_titles(pm["next"]["n"]), today)
    except Exception as e:
        print(f"[engine] claim check skipped: {e}")
    return stories.build_b(feed, today, recent, claim=claim)


def main(series):
    today = datetime.now(IST).date()
    state = F.load_state()
    run_mode = "dry" if os.environ.get("ENGINE_DRY") == "1" else mode()
    work = Path("engine-out")
    work.mkdir(exist_ok=True)
    out = work / f"{series}-{today.isoformat()}.mp4"
    if run_mode != "dry":
        from engine.publish import youtube_login_problem
        problem = youtube_login_problem()
        if problem:
            alert("TaazaBhav: YouTube login band ho gaya hai, video upload nahi hoga.\n"
                  "Fix: PC par `python authorize.py` chalao, phir naya token.pickle base64 karke "
                  "GitHub secret YT_TOKEN_PICKLE_B64 mein daalo.\n\n" + problem[:300])
            if run_mode == "publish":
                return 1
    try:
        ep = build(series, today, state)
        if not ep:
            print(f"[engine] {series}: no story today")
            if series != "C":
                alert(f"TaazaBhav engine: no {series} story today (nothing new in the feed).")
            return 0
        print(f"[engine] {series} {run_mode}: {ep['key']} | {ep['title']}")
        qa.check_episode(ep)
        rec = None
        rec_secs = None
        if series == "D":
            rec = tools.record(ep["tool"], ep["case"], work / "rec.mp4")
            rec_secs = media._duration(rec)
        voice = media.synth([s["say"] for s in ep["scenes"]], media.PUBLIC / "voice")
        clip = media.fetch_clip(ep["clip"], f"{today}-{series}", work / "clip.mp4")
        props = media.build_props(ep, voice, clip, rec_secs)
        seconds = props["frames"] / media.FPS
        qa.check_length(ep, seconds)
        media.render(props, out, clip, rec)
        if run_mode == "dry":
            print(f"[engine] rendered {out} ({seconds:.1f}s)")
            return 0
        if run_mode == "preview":
            from engine.publish import send_preview
            send_preview(out, ep, seconds)
            print("[engine] preview sent")
            return 0
        from engine.publish import publish
        vid = publish(out, ep, alert)
        F.mark(state, series, ep["key"], today, vid, ep["title"])
        F.save_state(state)
        print(f"[engine] published https://youtu.be/{vid}")
        return 0
    except Exception as e:
        traceback.print_exc()
        alert(f"TaazaBhav engine: series {series} failed, slot skipped.\n\n{e}")
        return 1
    finally:
        if run_mode != "dry":
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "A").upper()))
