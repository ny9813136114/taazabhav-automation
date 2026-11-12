# -*- coding: utf-8 -*-
"""One video for one series: python -m engine.run A|B|C|D|Y|M

Mode: ENGINE_MODE=preview|publish (manual runs). Scheduled runs publish only
when the repo variable ENGINE_LIVE is "1"; until then the video goes to the
owner's Telegram as a preview. ENGINE_DRY=1 renders to engine-out/ and sends
nothing (local checks)."""
import os
import shutil
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from engine import feed as F
from engine import look, media, qa, stories, tools, yojana

IST = timezone(timedelta(hours=5, minutes=30))
RECENT_DAYS = {"A": 7, "B": 60, "C": 1, "D": 21, "Y": 15}
# 3 Nov 2026: E = the evening bhav Short (18:30 IST, the old C slot). It is
# an A video (same builder, playlist and log), only its slot differs.
SLOT_OF = {"E": "A"}
# Voice speeds tried in turn when a video is over its length limit.
SPEEDS = ("+8%", "+18%", "+28%")


def mode(series=None):
    m = (os.environ.get("ENGINE_MODE") or "").strip().lower()
    if m in ("publish", "preview"):
        return m
    # The new mandi bhav Short previews on the owner's Telegram until the
    # repo variable BHAV_V2_LIVE is "1" (owner rule: 2 preview days first).
    if series in ("A", "E") and os.environ.get("BHAV_V2_LIVE", "").strip() != "1":
        return "preview"
    # Series Y posts at 12:30 (owner "haan", 9 Nov 2026); YOJANA_LIVE=0 makes it a preview again.
    if series == "Y" and os.environ.get("YOJANA_LIVE", "").strip() == "0":
        return "preview"
    # MP Kisan Kalyan Reel (M): live at once (owner, 12 Nov 2026: "dono upload kar do"); MPKK_LIVE=0 = preview.
    if series == "M" and os.environ.get("MPKK_LIVE", "").strip() == "0":
        return "preview"
    return "publish" if os.environ.get("ENGINE_LIVE", "").strip() == "1" else "preview"


def alert(msg):
    try:
        from notify import send_telegram_alert
        send_telegram_alert(msg)
    except Exception:
        print(msg)


def a_history(state, today, days=14):
    """A keys of the last `days` days, newest first."""
    eps = [e for e in state.get("episodes", []) if e.get("series") == "A" and e.get("key")
           and (today - date.fromisoformat(e["date"])).days < days]
    return [e["key"] for e in reversed(eps)]


def build(series, today, state):
    if series == "M":
        from engine import mpkalyan
        return mpkalyan.build_m(today)
    if series == "Y":
        items = yojana.load_queue()
        left = yojana.fresh_count(items, today, state)
        if left < yojana.LOW_QUEUE:
            alert(f"TaazaBhav engine: yojana queue mein sirf {left} naye topic bache hain. content/yojana/queue.json mein aur jodo.")
        return yojana.build_y(today, state, items)
    series = SLOT_OF.get(series, series)
    recent = F.recent_keys(state, series, today, RECENT_DAYS[series])
    if series == "D":
        return tools.build_d(today, recent)
    feed = F.load_feed(today, want_today=(series == "C"))
    if series == "A":
        if not feed.get("mandis"):
            raise RuntimeError("yt-feed has no 'mandis' yet (website PR #171 not live), A needs it")
        return stories.build_bhav(feed, today, a_history(state, today))
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
    run_mode = "dry" if os.environ.get("ENGINE_DRY") == "1" else mode(series)
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
            if series not in ("B", "C", "M"):  # B skips on purpose when B_ONLY_NEWS=1; M on the days B posts MP
                alert(f"TaazaBhav engine: no {series} story today (nothing new in the feed).")
            return 0
        print(f"[engine] {series} {run_mode}: {ep['key']} | {ep['title']}")
        series = ep["series"]
        ep.setdefault("theme", look.theme_for(today))
        # Same scheme again = a new theme, clip and voice (never the last ones used for it).
        scheme = ep.get("scheme") or ("pmkisan" if series == "B" else None)
        lk = look.pick_look(scheme, today, state.get("episodes", []), scheme) if scheme else None
        if lk:
            ep["theme"], ep["clip"] = lk["theme"], lk["clip"]
            print(f"[engine] look for {scheme}: theme {lk['theme']}, clip {lk['clip']}, {lk['voice']} voice")
        qa.check_episode(ep)
        rec = None
        rec_secs = None
        if series == "D":
            rec = tools.record(ep["tool"], ep["case"], work / "rec.mp4")
            rec_secs = media._duration(rec)
        clip = media.fetch_clip(ep["clip"], f"{today}-{series}", work / "clip.mp4")
        rates = list(SPEEDS)
        while True:
            voice = media.synth([s["say"] for s in ep["scenes"]], media.PUBLIC / "voice", rate=rates[0], voice=media.VOICES[lk["voice"]] if lk and not os.environ.get("ENGINE_VOICE") else media.voice_for(today, ep["key"]))
            props = media.build_props(ep, voice, clip, rec_secs)
            seconds = props["frames"] / media.FPS
            if seconds <= qa.BOUNDS[series][1]:
                break
            # Too long: drop optional scenes first, then speak faster, rather than skip the slot.
            spare = next((s for s in ep["scenes"] if s.get("optional")), None)
            if spare:
                print(f"[engine] {seconds:.1f}s too long, dropping the {spare['kind']} scene")
                ep["scenes"].remove(spare)
            elif len(rates) > 1:
                rates.pop(0)
                print(f"[engine] {seconds:.1f}s too long, voice speed {rates[0]}")
            else:
                break
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
        F.mark(state, ep["series"], ep["key"], today, vid, ep["title"], scheme, lk)
        F.save_state(state)
        print(f"[engine] published {'https://youtu.be/' + vid if vid else '(FB/IG only, not on YouTube)'}")
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
