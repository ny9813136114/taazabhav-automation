# -*- coding: utf-8 -*-
"""Fill the day's FB/IG photo quota with unique TaazaBhav website-feature posts.

Designed to coexist with existing 09:30 and 14:30 workflows. Uses their
shared ledger and publisher, never duplicates a previously used post ID or hook.
Run: python -m posts.content_engine [preview|publish|dry] [YYYY-MM-DD]
"""
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

from posts import ledger
from posts.run import IST, alert, publish, send_preview

STATE = Path("data/posts/content_engine.json")
TARGET = 3
FEATURES = [
    ("mandi", "/mandi-bhav/wheat", "गेहूं", "अपनी मंडी का गेहूं भाव", "मंडी बदलने से पहले भाव और दूरी दोनों देखें"),
    ("mandi", "/mandi-bhav/onion", "प्याज़", "प्याज़ का मंडी भाव", "सिर्फ सबसे ऊंचा भाव नहीं, ढुलाई भी जोड़ें"),
    ("mandi", "/mandi-bhav/tomato", "टमाटर", "टमाटर का मंडी भाव", "मंडी और तारीख देखकर ही तुलना करें"),
    ("compare", "/compare", "तुलना", "दो मंडियों का भाव मिलाएं", "अपनी नज़दीकी मंडी से तुलना शुरू करें"),
    ("calculator", "/kheti-lagat-munafa", "लागत-मुनाफा", "खेती में बचा कितना?", "खर्च, पैदावार और बिक्री जोड़कर हिसाब करें"),
    ("calculator", "/mandi-hisab", "मंडी हिसाब", "मंडी की पर्ची समझें", "कटौती और हाथ में आई रकम का हिसाब रखें"),
    ("calculator", "/khad-calculator", "खाद कैलकुलेटर", "खाद का खर्च समझें", "अपने खेत और ज़रूरत के अनुसार हिसाब लगाएं"),
    ("calculator", "/bigha-to-acre", "बीघा से एकड़", "बीघा और एकड़ का हिसाब", "क्षेत्र के अनुसार माप बदल सकता है"),
    ("calculator", "/msp-vs-mandi", "MSP तुलना", "MSP या मंडी?", "भाड़ा और दूसरे खर्च भी तुलना में रखें"),
    ("calculator", "/rokun-ya-bechun", "रोकूं या बेचूं", "फसल रोकने का खर्च", "भंडारण, ब्याज और नुकसान भी जोड़ें"),
    ("weather", "/aaj-ka-mausam", "मौसम", "खेती से पहले मौसम देखें", "स्थानीय पूर्वानुमान देखकर काम की योजना बनाएं"),
    ("guide", "/khet", "खेती जानकारी", "खेत की जानकारी एक जगह", "खेती से जुड़ी उपयोगी जानकारी पढ़ें"),
]
ANGLES = [
    ("स्मार्ट किसान टिप", "आज का एक काम"),
    ("काम की वेबसाइट", "मोबाइल पर आसान तरीका"),
    ("किसान चेकलिस्ट", "फैसले से पहले"),
    ("मंडी से पहले", "जल्दबाज़ी से बचें"),
    ("आज का सवाल", "आपने यह चेक किया?"),
    ("किसान की समझदारी", "हिसाब साफ़ रखें"),
    ("एक मिनट की सीख", "जानिए कैसे"),
    ("ताज़ाभाव टूल गाइड", "खुद जांचें"),
]


def make_post(feature, angle_index):
    kind, path, subject, headline, tip = feature
    label, hook = ANGLES[angle_index]
    key = path.strip("/").replace("/", "-")
    pid = f"social-v1-{key}-{angle_index}"
    first = f"{label}: {subject} — {hook}"
    url = "taazabhav.com" + path
    slides = [
        {"kind": "hook", "label": label, "big": headline, "sub": hook},
        {"kind": "list", "title": "किसान के लिए काम की बात", "items": [tip, "वेबसाइट पर अपने आंकड़े या मंडी चुनें", "दिखाई गई जानकारी की तारीख जांचें"]},
        {"kind": "cta", "big": "TaazaBhav पर खुद देखें", "url": url},
    ]
    caption = (f"{first}\n\n{headline}। {tip}।\n"
               f"अपने इलाके और जरूरत के हिसाब से देखें: https://{url}\n\n"
               "#TaazaBhav #किसान #खेती #मंडीभाव #Kisan")
    return {"id": pid, "path": path, "slides": slides, "caption": caption,
            "group": f"{headline}\nhttps://{url}", "link": f"https://{url}",
            "meta": {"angle": pid}, "kind": kind}


def candidate_entry(post, day, result=None):
    result = result or {}
    return ledger.entry(day=day, slot="18:00", fmt="photo", pillar="social-engine",
                        post_id=post["id"], caption=post["caption"],
                        angle=post["id"], facebook=result.get("facebook"),
                        instagram=result.get("instagram"))


def select(day, entries, state, n):
    used = {e.get("id") for e in entries}
    used.update(state.get("published_ids", []))
    seen_hooks = {e.get("hook_hash") for e in entries}
    chosen = []
    # Deterministic fair rotation; never re-use an ID or caption hook, ever.
    start = day.toordinal() % len(FEATURES)
    for angle in range(len(ANGLES)):
        for offset in range(len(FEATURES)):
            post = make_post(FEATURES[(start + offset) % len(FEATURES)], angle)
            entry = candidate_entry(post, day)
            if post["id"] in used or entry["hook_hash"] in seen_hooks:
                continue
            if ledger.problems(entry, entries, day):
                continue
            chosen.append(post)
            used.add(post["id"])
            seen_hooks.add(entry["hook_hash"])
            if len(chosen) == n:
                return chosen
    return chosen


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if mode not in ("preview", "publish", "dry"):
        raise ValueError("mode must be preview, publish, or dry")
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(IST).date()
    entries = ledger.load()
    # One shared daily cap across existing pillar/bhav workflows.
    existing = sum(e.get("date") == day.isoformat() and e.get("format") == "photo"
                   and (e.get("facebook") or e.get("instagram")) for e in entries)
    quota = max(0, TARGET - existing)
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {"published_ids": []}
    posts = select(day, entries, state, quota)
    if not posts:
        print(f"[content-engine] no safe unique posts available; existing={existing}, quota={quota}")
        return 0
    from posts.render import render
    for post in posts:
        print(f"[content-engine] {mode}: {post['id']}")
        slides = render(post, Path("posts-out") / post["id"])
        if mode == "dry":
            continue
        if mode == "preview":
            send_preview(post, slides)
            continue
        if not os.environ.get("CONTENT_ENGINE_LIVE") == "1":
            raise RuntimeError("CONTENT_ENGINE_LIVE must be 1 for publishing")
        result = publish(post, slides)
        if not result.get("facebook") and not result.get("instagram"):
            raise RuntimeError("Meta did not confirm a published post")
        state.setdefault("published_ids", []).append(post["id"])
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ledger.record(candidate_entry(post, day, result))
        if result.get("errors"):
            alert(f"Social engine {post['id']}: " + "; ".join(result["errors"]))
    if len(posts) < quota:
        alert(f"TaazaBhav social engine: only {len(posts)}/{quota} fresh posts left; add verified new angles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
