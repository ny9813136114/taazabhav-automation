# -*- coding: utf-8 -*-
"""Series Y "योजना की बात" (3 Nov 2026): one government scheme explained in
about 20 seconds, every day at 12:30 IST, on YouTube, Facebook and Instagram.

Facts come only from content/yojana/queue.json, which is written from the
taazabhav.com scheme pages (each with its official source) and reviewed by
the owner. Nothing is invented here: no dates, no amounts. Each video ends on
one taazabhav.com tool page, shown and spoken, because links in Shorts are not
clickable.

Picking rules:
  * an item is used only between its validFrom and validUntil dates;
  * the same item is not repeated within REPEAT_DAYS days;
  * one scheme at most SCHEME_PER_WEEK times in 7 days;
  * among the rest, the item not shown for longest goes first (queue order on a tie).
"""
import json
from datetime import date
from pathlib import Path

from engine.text import day_hi, link

QUEUE = Path("content/yojana/queue.json")
REPEAT_DAYS = 15
SCHEME_PER_WEEK = 2
LOW_QUEUE = 6  # fewer fresh items than this -> tell the owner to add more


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
    scheme_of = {i["id"]: i["scheme"] for i in items}
    week = [k for k, d in last.items() if (today - d).days < 7]
    per_scheme = {}
    for k in week:
        s = scheme_of.get(k)
        per_scheme[s] = per_scheme.get(s, 0) + 1
    ok = [i for i in items if _valid(i, today)
          and (i["id"] not in last or (today - last[i["id"]]).days >= REPEAT_DAYS)
          and per_scheme.get(i["scheme"], 0) < SCHEME_PER_WEEK]
    if not ok:
        return None
    order = {i["id"]: n for n, i in enumerate(items)}
    return min(ok, key=lambda i: (last.get(i["id"], date.min), order[i["id"]]))


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
    scenes = [{"kind": "headline", "label": h["label"], "big": h["big"], "sub": h.get("sub", ""), "tone": "white", "say": h["say"]}]
    for f in it["facts"]:
        scenes.append({"kind": "headline", "label": f["label"], "big": f["big"], "sub": f.get("sub", ""), "tone": "good", "say": f["say"]})
    scenes.append({"kind": "stamp", "label": "सरकारी स्रोत", "big": "✓ जांची जानकारी", "sub": it["source"], "tone": "good",
                   "say": "जानकारी सरकारी स्रोत से", "optional": True})
    scenes.append({"kind": "cta", "label": tool["label"], "big": tool["big"], "sub": f"taazabhav.com{tool['path']}", "say": tool["say"]})
    url = link(tool["path"])
    lines = [f"• {f['label']}: {f['big']}" + (f" ({f['sub']})" if f.get("sub") else "") for f in it["facts"]]
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
        "series": "Y", "key": it["id"], "clip": "generic", "stamp": day_hi(today), "stampTop": "योजना की बात",
        "scenes": scenes, "title": _fit(it["title"]), "description": desc,
        "tags": [*it.get("tags", []), "sarkari yojana", "kisan yojana", "taazabhav"],
        "comment": f"🔗 पूरी जानकारी: {url}\nकिस योजना पर अगला वीडियो चाहिए? कमेंट करें 👇",
        "playlist": "Y", "link": url, "tool": tool["path"].strip("/"), "scheme": it["scheme"],
    }
