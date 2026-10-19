# -*- coding: utf-8 -*-
"""Daily "aaj ke mandi bhav" carousel on the Facebook Page + Instagram.

Today's main crops from taazabhav.com/api/yt-feed (the site's own crop
reports, so the post says exactly what the site says): one slide per crop
with the typical price, state-wise price, the highest-paying mandis and MSP.

  preview (default): slides go to the owner's Telegram chat only.
  publish (repo variable BHAV_POSTS_LIVE=1): FB multi-photo post + IG
  carousel, then a share kit to the owner's Telegram.

Posts nothing when the site has no prices for today (Sunday, a holiday, a
failed price pull): an old price posted as today's would mislead farmers.

python -m posts.bhav [preview|publish|dry]"""
import json
import os
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

from posts.run import IST, alert, publish, send_preview, share_kit

STATE = Path("data/posts/bhav.json")
SITE = "https://taazabhav.com"

# Order = which crops make the post when more than MAX_CROPS have prices.
# Kharif selling + rabi sowing season first; vegetables after.
PRIORITY = ["soybean", "cotton", "dhan-paddy", "wheat", "mustard", "maize", "chana",
            "onion", "groundnut", "bajra", "potato", "tomato", "garlic", "moong", "urad", "jowar", "tur"]
MAX_CROPS = 7
MIN_MARKETS = 3
STATE_ROWS = 3
TOP_ROWS = 2

HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]


def mode():
    m = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if m:
        return m
    return "publish" if os.environ.get("BHAV_POSTS_LIVE", "").strip() == "1" else "preview"


def rs(n):
    """Indian grouping: 123456 -> ₹1,23,456."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + "₹" + s


def hi_date(d):
    return f"{d.day} {HI_MONTHS[d.month - 1]}"


def crop_reports(feed, day):
    """Today's crop reports worth posting, in PRIORITY order."""
    reps = {r["data"]["slug"]: r for r in feed.get("reports", [])
            if r.get("kind") == "crop" and r.get("date") == day and r.get("data", {}).get("markets", 0) >= MIN_MARKETS}
    order = [s for s in PRIORITY if s in reps] + sorted(s for s in reps if s not in PRIORITY)
    return [reps[s] for s in order[:MAX_CROPS]]


def crop_slide(r):
    d = r["data"]
    rows = [[f"{s['stateHi']} ({s['markets']} मंडी)", rs(s["typical"])] for s in d.get("states", [])[:STATE_ROWS]]
    rows += [[f"{'सबसे ऊंचा' if i == 0 else 'दूसरा ऊंचा'}: {t['marketHi']}, {t['stateHi']}", rs(t["modal"])]
             for i, t in enumerate(d.get("top", [])[:TOP_ROWS])]
    slide = {"kind": "table", "title": f"{d['nameHi']}: आम भाव {rs(d['typical'])}", "rows": rows}
    if d.get("msp"):
        slide["total"] = ["MSP", rs(d["msp"])]
    pct = d.get("pct")
    slide["note"] = "₹/क्विंटल" + (f" · पिछली रिपोर्ट से {'+' if pct > 0 else ''}{pct:g}%" if pct else "")
    return slide


def build(feed, today):
    """-> post dict for posts.render / posts.run, or None if no prices today."""
    day = today.isoformat()
    reps = crop_reports(feed, day)
    if not reps:
        return None
    markets = sum(r["data"]["markets"] for r in reps)
    states = {s["state"] for r in reps for s in r["data"].get("states", [])}
    names = ", ".join(r["data"]["nameHi"] for r in reps[:3])
    slides = [{"kind": "hook", "label": f"आज के मंडी भाव · {hi_date(today)}", "big": f"{names} का भाव",
               "sub": f"{len(reps)} फसलें · {markets} मंडियां · {len(states)} राज्य · राज्य का भाव और सबसे ऊंचे भाव वाली मंडी →"}]
    slides += [crop_slide(r) for r in reps]
    slides.append({"kind": "cta", "label": "हर मंडी, हर फसल का भाव", "big": "अपनी मंडी का आज का भाव देखें",
                   "url": "taazabhav.com"})
    lines = []
    for r in reps:
        d = r["data"]
        top = d.get("top") or []
        hi = f" (सबसे ऊंचा {top[0]['marketHi']} {rs(top[0]['modal'])})" if top else ""
        lines.append(f"• {d['nameHi']}: {rs(d['typical'])}{hi}")
    link = f"{SITE}/?utm_source=facebook&utm_medium=social&utm_campaign=bhav_post"
    caption = (f"आज के मंडी भाव, {hi_date(today)} {today.year} (₹/क्विंटल, आम भाव)\n\n" + "\n".join(lines) +
               f"\n\nअपनी मंडी का भाव: {link}\n\nभाव मंडी रिपोर्ट से हैं, बेचने से पहले अपनी मंडी में पक्का कर लें।\n\n"
               "#मंडीभाव #आजकाभाव #किसान #mandibhav #taazabhav")[:2200]
    group = (f"आज {hi_date(today)} के मंडी भाव: " + "; ".join(f"{r['data']['nameHi']} {rs(r['data']['typical'])}" for r in reps[:4]) +
             f"। राज्य वार भाव और सबसे ऊंचे भाव वाली मंडी इस पोस्ट में देखें 👇")
    return {"id": f"bhav-{day}", "slides": slides, "caption": caption, "group": group}


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"history": [], "preview": []}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    for k in ("history", "preview"):
        state[k] = state.get(k, [])[-60:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    from engine.feed import load_feed
    run_mode = mode()
    today = datetime.now(IST).date()
    state = load_state()
    key = "history" if run_mode == "publish" else "preview"
    if run_mode != "dry" and any(h["date"] == today.isoformat() for h in state.get(key, [])):
        print(f"[bhav] {run_mode}: already done today")
        return 0
    try:
        feed = load_feed(today=today, want_today=True)
    except Exception as e:
        alert(f"TaazaBhav bhav post: site feed failed, nothing posted.\n\n{e}")
        return 1
    post = build(feed, today)
    if not post:
        print(f"[bhav] no prices for {today} (latest {feed.get('latestDate')}), nothing posted")
        return 0
    print(f"[bhav] {run_mode}: {post['id']} ({len(post['slides'])} slides)")
    try:
        from posts.render import render
        slides = render(post, Path("posts-out"))
        if run_mode == "dry":
            print("\n".join(map(str, slides)))
            return 0
        if run_mode == "preview":
            send_preview(post, slides)
            state.setdefault("preview", []).append({"date": today.isoformat(), "id": post["id"]})
            save_state(state)
            return 0
        res = publish(post, slides)
        state.setdefault("history", []).append({"date": today.isoformat(), "id": post["id"],
                                                "facebook": res["facebook"], "instagram": res["instagram"]})
        save_state(state)
        if res["errors"]:
            alert(f"TaazaBhav bhav post: " + "\n".join(res["errors"])[:500])
        try:
            share_kit(post, res["facebook"])
        except Exception as e:
            alert(f"TaazaBhav bhav post: share kit failed: {e}")
        print(f"[bhav] published FB {res['facebook']} IG {res['instagram']}")
        return 0
    except Exception as e:
        traceback.print_exc()
        alert(f"TaazaBhav bhav post failed, nothing posted today.\n\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
