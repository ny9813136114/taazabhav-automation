# -*- coding: utf-8 -*-
"""Two "योजना की बात" carousels a day on the Facebook Page + Instagram
(10 Nov 2026, owner: more posts, scheme content is what gets the views).

  am  07:30 IST  sach / deadline / news items first
  pm  18:30 IST  state / kitna / portal / reject items first

Facts come only from content/posts/yojana_posts.json, a pool of its own (same item format as the
video queue, but never shared with it). An item is used once ever; the same
scheme at most once in 14 days and the same state at most once in 7 days. The
link to the matching taazabhav.com tool goes in the Page's first comment.

  preview (default): slides go to the owner's Telegram only.
  publish (repo variable YOJANA_POSTS_LIVE=1): FB multi-photo post + IG carousel.

python -m posts.yojana_post am|pm [preview|publish|dry]"""
import json
import os
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

from engine import yojana
from engine.text import day_hi
from posts.run import IST, alert, publish, send_preview

STATE = Path("data/posts/yojana_post.json")
QUEUE = Path("content/posts/yojana_posts.json")
SITE = "https://taazabhav.com"
TONE = {"good": "true", "low": "half", "bad": "false", "high": "false"}
SLOTS = {
    "am": {"slot": "07:30", "formats": ["sach", "deadline", "news"]},
    "pm": {"slot": "18:30", "formats": ["state", "kitna", "portal", "reject"]},
}


def mode(argv=None):
    argv = sys.argv if argv is None else argv
    m = (argv[2] if len(argv) > 2 else "").strip()
    if m:
        return m
    return "publish" if os.environ.get("YOJANA_POSTS_LIVE", "").strip() == "1" else "preview"


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"history": [], "preview": []}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    # Keep every id: card_history() reads them to stop a video reusing an item.
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def fact_text(f):
    return f.get("big") or ", ".join(x["value"] for x in f.get("items", []))


def build(item, today, slot):
    """-> post dict for posts.render / posts.run."""
    h, tool = item["hook"], item["tool"]
    fmt = item.get("format", "kitna")
    slides = [{"kind": "hook", "label": f"{yojana.FORMATS.get(fmt, 'योजना की बात')} · {h['label']}", "big": h["big"], "sub": h.get("sub", "")}]
    if fmt == "sach":
        v = item["verdict"]
        slides.append({"kind": "claim", "label": "सरकारी जांच", "claim": h["big"], "verdict": v["big"], "tone": TONE.get(v.get("tone"), "half")})
    if fmt == "deadline" and item.get("deadline"):
        days = (date.fromisoformat(item["deadline"]) - today).days
        if days < 0:
            return None
        slides.append({"kind": "answer", "label": "आखिरी तारीख", "big": f"{days} दिन बाकी" if days else "आज आखिरी दिन",
                       "sub": day_hi(item["deadline"], True)})
    for f in item["facts"]:
        if f.get("items"):
            slides.append({"kind": "list", "title": f["label"], "items": [f"{x['label']}: {x['value']}" if x.get("label") else x["value"] for x in f["items"]]})
        else:
            slides.append({"kind": "answer", "label": f["label"], "big": f["big"], "sub": f.get("sub", "")})
    link = f"{SITE}{tool['path']}"
    slides.append({"kind": "cta", "label": tool["label"], "big": tool["big"], "url": f"taazabhav.com{tool['path']}",
                   "ask": ["किस योजना पर अगली पोस्ट चाहिए?", "नाम कमेंट में लिखें 👇"]})
    bullets = "\n".join(f"• {f['label']}: {fact_text(f)}" + (f" ({f['sub']})" if f.get("sub") else "") for f in item["facts"] if f.get("big") or f.get("items"))
    title = item["title"].split("|")[0].strip()
    caption = (f"{title}\n\n{bullets}\n\nपूरी जानकारी और हिसाब (मुफ़्त, हिंदी में): {link}\n\n"
               f"सरकारी स्रोत: {item['source']} · जानकारी जांची: {day_hi(item['checked'], True)}\n"
               "नियम राज्य और साल के हिसाब से बदल सकते हैं। आवेदन से पहले सरकारी पोर्टल पर मिला लें।\n\n"
               "#किसान #सरकारीयोजना #kisan #yojana #taazabhav")[:2200]
    return {"id": f"yojana-{item['id']}", "item": item["id"], "slides": slides, "caption": caption, "caption_live": caption,
            "trust": f"स्रोत: {item['source']} · जांचा: {day_hi(item['checked'], True)}",
            "link": link, "link_label": f"{tool['label']}, मुफ़्त टूल", "lead": title}


def theme_of(today, scheme, state):
    """Carousel design 0-5. The same scheme never repeats a design until all
    have been used, and it is never the design of the previous post."""
    from engine import look
    from posts.render import THEMES
    recs = sorted(state.get("history", []) + state.get("preview", []), key=lambda r: (r["date"], r["slot"]))
    past = [(r.get("scheme"), r["theme"]) for r in recs if "theme" in r]
    return look.pick_theme(scheme, today, past, n=len(THEMES))


def ledger_entry(post, today, slot, item, res=None):
    from posts.ledger import entry
    res = res or {}
    if item is None:  # price post
        return entry(day=today, slot=SLOTS[slot]["slot"], fmt="photo", pillar="bhav2", post_id=post["id"], caption=post["caption"],
                     crops=post["crops"], angle=post["kind"], facebook=res.get("facebook"), instagram=res.get("instagram"))
    st = item.get("state")
    return entry(day=today, slot=SLOTS[slot]["slot"], fmt="photo", pillar="Y", post_id=post["id"], caption=post["caption"],
                 state=None if st in (None, "all") else st, angle=item["id"],
                 facebook=res.get("facebook"), instagram=res.get("instagram"))


# Evening slot: Mon/Tue/Wed are price posts built from today's site data
# (never run out); other days, or a day without fresh prices, a yojana card.
BHAV_KIND = {0: "chaal", 1: "msp", 2: "oonchi"}
MAX_PCT = 30  # a bigger one-report move is more likely a data glitch than news


def _cta(label):
    return {"kind": "cta", "label": label, "big": "अपनी मंडी का आज का भाव देखें", "url": "taazabhav.com",
            "ask": ["आपकी मंडी में आज भाव कितना?", "मंडी और भाव कमेंट में लिखें 👇"]}


def build_bhav(kind, feed, today):
    """-> post dict from today's crop reports, or None when the data can't support it."""
    from posts.bhav import crop_reports, hi_date, rs
    reps = crop_reports(feed, today.isoformat())
    if len(reps) < 3:
        return None
    day = hi_date(today)
    if kind == "chaal":
        ups = sorted((r for r in reps if 0 < (r["data"].get("pct") or 0) <= MAX_PCT), key=lambda r: -r["data"]["pct"])[:3]
        downs = sorted((r for r in reps if -MAX_PCT <= (r["data"].get("pct") or 0) < 0), key=lambda r: r["data"]["pct"])[:3]
        if not ups and not downs:
            return None
        rows = [[f"▲ {r['data']['nameHi']}", f"{rs(r['data']['typical'])} (+{r['data']['pct']:g}%)"] for r in ups]
        rows += [[f"▼ {r['data']['nameHi']}", f"{rs(r['data']['typical'])} ({r['data']['pct']:g}%)"] for r in downs]
        head = f"आज किस फसल का भाव ऊपर, किसका नीचे · {day}"
        slides = [{"kind": "hook", "label": f"भाव की चाल · {day}", "big": "आज कौन सी फसल चढ़ी, कौन गिरी?", "sub": "पिछली रिपोर्ट से तुलना, आम भाव ₹/क्विंटल →"},
                  {"kind": "table", "title": "भाव की चाल", "rows": rows, "note": "₹/क्विंटल, पिछली रिपोर्ट से बदलाव"}]
        crops = [r["data"]["slug"] for r in ups + downs]
        tip = "एक दिन की चाल से फैसला न करें, अपनी मंडी का भाव देखकर ही बेचें।"
    elif kind == "msp":
        rows, below = [], []
        for r in reps:
            d = r["data"]
            if d.get("msp"):
                diff = (d["typical"] - d["msp"]) / d["msp"] * 100
                rows.append([d["nameHi"], f"{rs(d['typical'])} · MSP {rs(d['msp'])} ({diff:+.0f}%)"])
                if diff < 0:
                    below.append(d["nameHi"])
        if len(rows) < 2:
            return None
        head = f"MSP से तुलना: आज का मंडी भाव · {day}"
        big = f"{', '.join(below[:2])} MSP से नीचे" if below else "आज MSP वाली फसलें MSP से ऊपर"
        slides = [{"kind": "hook", "label": f"MSP बनाम मंडी · {day}", "big": big, "sub": "आम मंडी भाव और सरकारी MSP, आज की रिपोर्ट →"},
                  {"kind": "table", "title": "मंडी भाव बनाम MSP", "rows": rows[:7], "note": "₹/क्विंटल, % = मंडी भाव MSP से कितना ऊपर/नीचे"}]
        crops = [r["data"]["slug"] for r in reps if r["data"].get("msp")]
        tip = "MSP पर खरीद सरकारी केंद्र पर होती है, पंजीकरण और शर्तें अपने राज्य में देखें।"
    else:  # oonchi
        lead = next((r for r in reps if len(r["data"].get("top") or []) >= 3), None)
        if not lead:
            return None
        d = lead["data"]
        rows = [[f"{t['marketHi']}, {t['stateHi']}", rs(t["modal"])] for t in d["top"][:5]]
        head = f"{d['nameHi']}: सबसे ऊंचा भाव किस मंडी में? · {day}"
        slides = [{"kind": "hook", "label": f"सबसे ऊंचा भाव · {day}", "big": f"{d['nameHi']} कहां सबसे महंगी बिकी?", "sub": f"आम भाव {rs(d['typical'])}, सबसे ऊंची 5 मंडियां →"},
                  {"kind": "table", "title": f"{d['nameHi']}: सबसे ऊंचे भाव की मंडियां", "rows": rows, "total": ["आम भाव", rs(d["typical"])], "note": "₹/क्विंटल"}]
        crops = [d["slug"]]
        tip = "ऊंचे भाव वाली मंडी दूर हो तो भाड़ा और मंडी शुल्क घटाकर तय करें।"
    slides.append(_cta("हर मंडी, हर फसल का भाव"))
    caption = (f"{head}\n\n" + "\n".join(f"• {a}: {b}" for a, b in rows) +
               f"\n\nअपनी मंडी का भाव: {SITE}\n\n{tip}\nभाव मंडी रिपोर्ट से हैं, बेचने से पहले अपनी मंडी में पक्का कर लें।\n\n#मंडीभाव #किसान #taazabhav")[:2200]
    return {"id": f"bhav-{kind}-{today.isoformat()}", "slides": slides, "caption": caption, "caption_live": caption, "kind": kind, "crops": crops,
            "trust": f"स्रोत: मंडी रिपोर्ट, taazabhav.com · {day}", "link": SITE, "link_label": "अपनी मंडी का आज का भाव", "lead": head}


def pick_item(slot, today, state):
    items = yojana.load_queue(QUEUE)
    cards = {}
    for h in state.get("history", []) + state.get("preview", []):
        d = date.fromisoformat(h["date"])
        cards[h["id"]] = max(d, cards.get(h["id"], d))
    fake = {"episodes": [{"series": "Y", "key": k, "date": d.isoformat()} for k, d in cards.items()]}
    # Slot's formats first; pick() then takes the first fresh item that obeys the gap rules.
    want = [i for i in items if i.get("format") in SLOTS[slot]["formats"]]
    return yojana.pick(want, today, fake) or yojana.pick(items, today, fake), yojana.fresh_count(items, today, fake)


def main():
    slot = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if slot not in SLOTS:
        print("usage: python -m posts.yojana_post am|pm [preview|publish|dry]")
        return 2
    run_mode = mode()
    from posts.run import meta_off_skip
    if run_mode == "publish" and not meta_off_skip("Y"):
        return 0
    today = datetime.now(IST).date()
    state = load_state()
    key = "history" if run_mode == "publish" else "preview"
    if run_mode != "dry" and any(h["date"] == today.isoformat() and h["slot"] == slot for h in state.get(key, [])):
        print(f"[yojana_post] {slot} {run_mode}: already done today")
        return 0
    post, item, skip = None, None, ()
    if slot == "pm" and today.weekday() in BHAV_KIND:
        try:
            from engine.feed import load_feed
            post = build_bhav(BHAV_KIND[today.weekday()], load_feed(today=today, want_today=True), today)
        except Exception as e:
            print(f"[yojana_post] price post not built ({e}), using a yojana card")
        skip = ("topic",)  # the same kind comes back every week
    if not post:
        skip = ()
        item, left = pick_item(slot, today, state)
        if left < yojana.LOW_QUEUE:
            alert(f"TaazaBhav yojana posts: queue mein sirf {left} naye topic bache hain. content/posts/yojana_posts.json mein aur jodo.")
        if not item:
            alert(f"TaazaBhav yojana post ({slot}): aaj ke liye koi naya topic nahi, post skip. Queue mein aur topic jodo.")
            return 0
        post = build(item, today, slot)
        if not post:
            print(f"[yojana_post] {item['id']} cannot be built today, skipped")
            return 0
    scheme = item["scheme"] if item else f"bhav-{post['kind']}"
    post["theme"] = theme_of(today, scheme, state)
    from posts import ledger
    entry = ledger_entry(post, today, slot, item)
    bad = ledger.problems(entry, ledger.load(), today, skip)
    if bad:
        alert(f"TaazaBhav yojana post: {post['id']} blocked by the no-repeat ledger, nothing posted.\n\n" + "\n".join(bad))
        return 1
    print(f"[yojana_post] {slot} {run_mode}: {post['id']} ({len(post['slides'])} slides)")
    try:
        from posts.render import render
        if run_mode != "publish":
            post["comment_mode"] = True
        slides = render(post, Path("posts-out"))
        if run_mode == "dry":
            print("\n".join(map(str, slides)))
            return 0
        rec = {"date": today.isoformat(), "slot": slot, "id": item["id"] if item else post["id"], "lead": post["lead"],
               "scheme": scheme, "theme": post["theme"]}
        if run_mode == "preview":
            send_preview(post, slides)
            state.setdefault("preview", []).append(rec)
            save_state(state)
            return 0
        res = publish(post, slides)
        state.setdefault("history", []).append({**rec, "facebook": res["facebook"], "instagram": res["instagram"]})
        save_state(state)
        ledger.safe_record(ledger_entry(post, today, slot, item, res))
        if res["errors"]:
            alert("TaazaBhav yojana post: " + "\n".join(res["errors"])[:500])
        print(f"[yojana_post] published FB {res['facebook']} IG {res['instagram']}")
        return 0
    except Exception as e:
        alert(f"TaazaBhav yojana post ({slot}) failed: {e}\n\n{traceback.format_exc()[-600:]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
