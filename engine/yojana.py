# -*- coding: utf-8 -*-
"""Series Y "योजना की बात" (3 Nov 2026): one government scheme explained in
about 20 seconds, every day at 12:30 IST, on YouTube, Facebook and Instagram.

Facts come only from content/yojana/queue.json, which is written from the
taazabhav.com scheme pages (each with its official source) and reviewed by
the owner. Nothing is invented here: no dates, no amounts. Each video ends on
one taazabhav.com tool page, shown and spoken, because links in Shorts are not
clickable.

v2 (9 Nov 2026, owner: "ultra rare", no repeats, all India): every item has a
format, and each weekday has its own format, so no two days look alike:
  Mon राज्य की योजना · Tue सच या झूठ · Wed कितना मिलेगा · Thu फॉर्म रिजेक्ट क्यों?
  Fri आखिरी तारीख · Sat पोर्टल डिकोडर · Sun सरकारी खबर

Picking rules:
  * an item is posted once, never again (when the queue runs dry the day is
    skipped and the owner is told; an old video is never reposted);
  * an item is used only between its validFrom and validUntil dates;
  * the same scheme at most once in SCHEME_GAP_DAYS days;
  * the same state at most once in STATE_GAP_DAYS days;
  * today's format first; if none is left, any other format, queue order.
"""
import json
from datetime import date
from pathlib import Path

from engine import look
from engine.text import day_hi, link

QUEUE = Path("content/yojana/queue.json")
SCHEME_GAP_DAYS = 14
STATE_GAP_DAYS = 7
LOW_QUEUE = 10  # fewer fresh items than this -> tell the owner to add more

FORMATS = {
    "state": "राज्य की योजना", "sach": "सच या झूठ", "kitna": "कितना मिलेगा", "reject": "फॉर्म रिजेक्ट क्यों?",
    "deadline": "आखिरी तारीख", "portal": "पोर्टल डिकोडर", "news": "सरकारी खबर",
}
WEEKDAY_FORMAT = ["state", "sach", "kitna", "reject", "deadline", "portal", "news"]  # Monday first
# Each format has its own colour, so the feed never looks like the same video.
FORMAT_COLOR = {"state": "#1f7a4d", "sach": "#c62828", "kitna": "#b8860b", "reject": "#6a1b9a",
                "deadline": "#d84315", "portal": "#1565c0", "news": "#37474f"}


def load_queue(path=QUEUE):
    return json.loads(Path(path).read_text(encoding="utf-8"))["items"]


def _valid(item, today):
    t = today.isoformat()
    return (item.get("validFrom") or "0000") <= t <= (item.get("validUntil") or "9999")


def _history(state):
    """item id -> last date it was published (series Y)."""
    last = {}
    for e in state.get("episodes", []):
        if e.get("series") == "Y":
            d = date.fromisoformat(e["date"])
            if e["key"] not in last or d > last[e["key"]]:
                last[e["key"]] = d
    return last


def pick(items, today, state):
    last = _history(state)
    by_id = {i["id"]: i for i in items}
    gap_scheme, gap_state = {}, {}
    for k, d in last.items():
        it = by_id.get(k)
        if not it:
            continue
        days = (today - d).days
        gap_scheme[it["scheme"]] = min(days, gap_scheme.get(it["scheme"], 10 ** 6))
        st = it.get("state") or "all"
        if st != "all":
            gap_state[st] = min(days, gap_state.get(st, 10 ** 6))
    ok = [i for i in items if _valid(i, today) and i["id"] not in last
          and gap_scheme.get(i["scheme"], 10 ** 6) >= SCHEME_GAP_DAYS
          and ((i.get("state") or "all") == "all" or gap_state.get(i["state"], 10 ** 6) >= STATE_GAP_DAYS)]
    if not ok:
        return None
    want = WEEKDAY_FORMAT[today.weekday()]
    same = [i for i in ok if i.get("format") == want]
    return (same or ok)[0]


def fresh_count(items, today, state):
    """Items still valid and never published: the owner tops the queue up below LOW_QUEUE."""
    last = _history(state)
    return sum(1 for i in items if _valid(i, today) and i["id"] not in last)


def build_y(today, state, items=None):
    items = load_queue() if items is None else items
    it = pick(items, today, state)
    if not it:
        return None
    from engine.stories import _fit
    h, tool = it["hook"], it["tool"]
    fmt = it.get("format", "kitna")
    scenes = [_scene(h, "claim" if fmt == "sach" else "headline", "white")]
    if fmt == "sach":
        v = it["verdict"]
        scenes.append({"kind": "stamp", "label": "सरकारी जांच", "big": v["big"], "sub": v.get("sub", ""),
                       "tone": v.get("tone", "low"), "say": v["say"]})
    if fmt == "deadline" and it.get("deadline"):
        days = (date.fromisoformat(it["deadline"]) - today).days
        if days < 0:
            return None
        scenes.append({"kind": "number", "label": "आखिरी तारीख", "big": f"{days} दिन बाकी" if days else "आज आखिरी दिन",
                       "count": days or None, "sub": day_hi(it["deadline"], True), "tone": "low",
                       "say": (f"आखिरी तारीख {day_hi(it['deadline'])}, यानी सिर्फ़ {days} दिन बाकी" if days else "आज आखिरी दिन है")})
    for f in it["facts"]:
        scenes.append(_scene(f, f.get("kind", "headline"), "good"))
    scenes.append({"kind": "stamp", "label": "सरकारी स्रोत", "big": "✓ जांची जानकारी", "sub": it["source"], "tone": "good",
                   "say": "जानकारी सरकारी स्रोत से", "optional": True})
    scenes.append({"kind": "cta", "label": tool["label"], "big": tool["big"], "sub": f"taazabhav.com{tool['path']}", "say": tool["say"]})
    url = link(tool["path"])
    lines = [f"• {f['label']}: {f.get('big') or ', '.join(x['value'] for x in f.get('items', []))}" + (f" ({f['sub']})" if f.get("sub") else "")
             for f in it["facts"]]
    desc = "\n".join([
        it["title"].split("|")[0].strip(),
        "",
        *lines,
        "",
        f"पूरी जानकारी और हिसाब (मुफ़्त, हिंदी में): {url}",
        f"सरकारी स्रोत: {it['source']} · जानकारी जांची: {day_hi(it['checked'], True)}",
        "नियम राज्य और साल के हिसाब से बदल सकते हैं। आवेदन से पहले सरकारी पोर्टल पर मिला लें।",
        "Telegram: https://t.me/taazabhav",
        "#kisan #yojana #sarkariyojana #किसान #taazabhav",
    ])
    return {
        "series": "Y", "key": it["id"], "clip": look.clip_for(it["id"], today, it.get("scheme", "")), "theme": look.theme_for(today), "stamp": day_hi(today), "stampTop": "योजना की बात", "badge": FORMATS.get(fmt), "color": FORMAT_COLOR.get(fmt),
        "scenes": scenes, "title": _fit(it["title"]), "description": desc,
        "tags": [*it.get("tags", []), "sarkari yojana", "kisan yojana", "taazabhav"],
        "comment": f"🔗 पूरी जानकारी: {url}\nकिस योजना पर अगला वीडियो चाहिए? कमेंट करें 👇",
        "playlist": "Y", "link": url, "tool": tool["path"].strip("/"), "scheme": it["scheme"], "format": fmt,
    }


def _scene(part, kind, tone):
    """Queue card -> Desk scene. Extra fields (items for a timeline, count for
    a number) pass through as they are."""
    sc = {"kind": kind, "tone": part.get("tone", tone)}
    for k in ("label", "big", "sub", "say", "items", "count", "left", "right"):
        if k in part:
            sc[k] = part[k]
    sc.setdefault("label", "")
    sc.setdefault("sub", "")
    return sc
