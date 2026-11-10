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


def ledger_entry(post, today, slot, item, res=None):
    from posts.ledger import entry
    res = res or {}
    st = item.get("state")
    return entry(day=today, slot=SLOTS[slot]["slot"], fmt="photo", pillar="Y", post_id=post["id"], caption=post["caption"],
                 state=None if st in (None, "all") else st, angle=item["id"],
                 facebook=res.get("facebook"), instagram=res.get("instagram"))


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
    from posts import ledger
    entry = ledger_entry(post, today, slot, item)
    bad = ledger.problems(entry, ledger.load(), today)
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
        rec = {"date": today.isoformat(), "slot": slot, "id": item["id"], "lead": post["lead"]}
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
