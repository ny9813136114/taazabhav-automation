# -*- coding: utf-8 -*-
"""Farmer jawab loop (TaazaBhav FB/IG Content Engine plan, sections 3, 4, 8).

Every night it reads the farmers' comments under the Page's last 3 days of
posts (Facebook + Instagram):

  * a comment with a crop, a mandi and a price ("नीमच मंडी में सोयाबीन 4650")
    becomes a farmer price report (data/farmer/prices/<date>.json). Only the
    crop, mandi, price and comment id are kept: never a name.
  * a Facebook comment with a photo is kept as a possible mandi parchi
    (data/farmer/parchi/, private repo) and sent to the owner's Telegram.

On Friday night, when Saturday's 09:30 pillar is P1 and the week has at
least MIN_REPORTS farmer prices, it builds "Aapki Mandi Report" from them
(farmer price next to the official price of the day) and on Saturday night,
when a read parchi is waiting in content/parchi/<Sunday>.json, the Parchi
Doctor post. Both go to the owner's Telegram first: the post goes out only
if the owner answers "haan" before 09:30 (posts/pillar.py checks it); if
not, the day's normal pillar post goes instead.

python -m posts.jawab [collect|need|draft|all] [YYYY-MM-DD]"""
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from posts.run import IST, _owner, _tg, alert

PRICES = Path("data/farmer/prices")
PARCHI = Path("data/farmer/parchi")
DRAFTS = Path("data/farmer/drafts")
PARCHI_POSTS = Path("content/parchi")
DAYS_BACK = 3
REPORT_DAYS = 7
MIN_REPORTS = 3
MAX_ROWS = 6
# A farmer's price far from the day's official price is more likely a typo
# (or a different unit) than a real sale: it stays out of the post.
SANE = (0.5, 1.8)
YES = {"haan", "han", "ha", "haa", "हां", "हाँ", "हा", "yes", "ok", "👍"}

# crop slug -> words farmers type for it (Hindi first).
CROPS = {
    "soybean": ["सोयाबीन", "सोयाबिन", "सोया", "soybean", "soyabean", "soya"],
    "dhan-paddy": ["धान", "paddy", "dhan"],
    "wheat": ["गेहूं", "गेहूँ", "गेंहू", "गेहू", "wheat", "gehu", "gehun"],
    "mustard": ["सरसों", "सरसो", "mustard", "sarso", "sarson"],
    "maize": ["मक्का", "makka", "maize", "corn"],
    "chana": ["चना", "chana"],
    "cotton": ["कपास", "नरमा", "cotton", "kapas", "narma"],
    "onion": ["प्याज़", "प्याज", "onion", "pyaj", "pyaz"],
    "garlic": ["लहसुन", "garlic", "lahsun"],
    "potato": ["आलू", "potato", "aloo", "alu"],
    "groundnut": ["मूंगफली", "मूँगफली", "groundnut", "mungfali"],
    "bajra": ["बाजरा", "bajra"],
    "moong": ["मूंग", "मूँग", "moong", "mung"],
    "urad": ["उड़द", "उडद", "urad"],
    "tur": ["तुअर", "अरहर", "तूर", "tur", "arhar"],
    "jowar": ["ज्वार", "jowar"],
    "tomato": ["टमाटर", "tomato"],
}
_NUM = re.compile(r"(?:₹|rs\.?|रु\.?)?\s*(\d{1,2}[,.]?\d{3}|\d{3,5})(?!\d)", re.I)
_MANDI = re.compile(r"([^\s,.।:;!?0-9₹]{2,20}(?:\s[^\s,.।:;!?0-9₹]{2,20})?)\s+(?:मंडी|mandi|मण्डी|apmc)|(?:मंडी|mandi)\s*[:-]?\s*([^\s,.।:;!?0-9₹]{2,20})", re.I)
_STOP = {"मेरी", "हमारी", "हमारे", "आपकी", "अपनी", "आज", "की", "का", "में", "my", "our", "the", "aaj", "हमारा"}


def parse(text):
    """Comment text -> [{"crop", "price", "mandi"}]; [] when it doesn't
    name all three. The price nearest each crop word is taken."""
    t = text or ""
    low = t.lower()
    nums = [(m.start(), int(re.sub(r"[,.]", "", m.group(1)))) for m in _NUM.finditer(t)]
    nums = [(i, n) for i, n in nums if 300 <= n <= 30000]
    mandi = None
    for m in _MANDI.finditer(t):
        words = [w for w in (m.group(1) or m.group(2) or "").split() if w.lower() not in _STOP]
        if words:
            mandi = " ".join(w.title() if w.isascii() else w for w in words)
            break
    if not nums or not mandi:
        return []
    out = []
    for slug, words in CROPS.items():
        pos = [low.find(w.lower()) for w in words if low.find(w.lower()) >= 0]
        if not pos:
            continue
        at = min(pos)
        price = min(nums, key=lambda x: abs(x[0] - at))[1]
        out.append({"crop": slug, "price": price, "mandi": mandi})
    return out


# ---------------------------------------------------------------- Meta
def _get(path, token, **params):
    import meta_publish as mp
    return mp._check(requests.get(f"{mp.GRAPH}/{path}", params={**params, "access_token": token}, timeout=mp.TIMEOUT), path)


def recent_posts(token, ig, since):
    page = os.environ["FB_PAGE_ID"]
    fb = [p["id"] for p in _get(f"{page}/posts", token, fields="id,created_time", since=int(since.timestamp()), limit=50).get("data", [])]
    igm = []
    if ig:
        for m in _get(f"{ig}/media", token, fields="id,timestamp", limit=40).get("data", []):
            if datetime.strptime(m["timestamp"].replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z") >= since:
                igm.append(m["id"])
    return fb, igm


def fb_comments(post_id, token):
    page = os.environ["FB_PAGE_ID"]
    rows = _get(f"{post_id}/comments", token, fields="id,message,created_time,from{id},attachment{type,media,url}",
                filter="stream", limit=100).get("data", [])
    return [c for c in rows if (c.get("from") or {}).get("id") != page]


def ig_comments(media_id, token, own):
    rows = _get(f"{media_id}/comments", token, fields="id,text,timestamp,username", limit=50).get("data", [])
    return [c for c in rows if c.get("username") != own]


# ---------------------------------------------------------------- store
def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def seen_ids():
    ids = {r["comment"] for f in PRICES.glob("*.json") for r in _load(f, [])}
    ids |= {p["comment"] for p in _load(PARCHI / "index.json", [])}
    return ids


def collect(day, token, ig, own, fetch=None):
    """-> (new price reports, new parchi). fetch: test hook returning
    [(net, post_id, comment)]."""
    seen = seen_ids()
    if fetch is None:
        since = datetime.combine(day - timedelta(days=DAYS_BACK), datetime.min.time(), IST)
        fb, igm = recent_posts(token, ig, since)
        items = [("facebook", p, c) for p in fb for c in fb_comments(p, token)]
        items += [("instagram", m, c) for m in igm for c in ig_comments(m, token, own)]
    else:
        items = fetch()
    prices, parchi = [], []
    for net, post, c in items:
        if c["id"] in seen:
            continue
        text = c.get("message") or c.get("text") or ""
        when = (c.get("created_time") or c.get("timestamp") or "")[:10]
        for r in parse(text):
            prices.append({**r, "net": net, "post": post, "comment": c["id"], "date": when})
        att = c.get("attachment") or {}
        img = ((att.get("media") or {}).get("image") or {}).get("src")
        if net == "facebook" and att.get("type") in ("photo", "sticker_photo", None) and img and att.get("type") != "sticker":
            parchi.append({"comment": c["id"], "post": post, "date": when, "image": img, "note": text[:200], "read": False})
        seen.add(c["id"])
    if prices:
        f = PRICES / f"{day.isoformat()}.json"
        _save(f, _load(f, []) + prices)
    if parchi:
        idx = _load(PARCHI / "index.json", [])
        for p in parchi:
            try:
                r = requests.get(p["image"], timeout=60)
                r.raise_for_status()
                name = f"{p['date']}-{re.sub(r'[^0-9_]', '', p['comment'])}.jpg"
                (PARCHI / name).parent.mkdir(parents=True, exist_ok=True)
                (PARCHI / name).write_bytes(r.content)
                p["file"] = name
            except Exception as e:
                p["error"] = str(e)[:200]
            p.pop("image", None)  # signed CDN URL: expires, and isn't needed once saved
            idx.append(p)
        _save(PARCHI / "index.json", idx)
    return prices, parchi


# ---------------------------------------------------------------- approval
def request_approval(key, post, slides, deadline):
    """Post preview to the owner with a "haan" request; remembers when."""
    from posts.run import send_preview
    send_preview(post, slides)
    r = _tg("sendMessage", {"chat_id": _owner(),
                            "text": f"Kya yeh post {deadline} par Page par jaaye? Haan ho to is message ka reply \"haan\" likh do. "
                                    f"Jawab na aaya to us din ki normal post jaayegi.\n\n({key})"})
    approvals = _load(DRAFTS / "approvals.json", {})
    approvals[key] = {"message_id": r["result"]["message_id"], "sent": int(time.time())}
    _save(DRAFTS / "approvals.json", approvals)


def approved(key, updates=None):
    """True when the owner answered "haan" after the request: as a reply to
    it, or as a plain message in the owner chat."""
    req = _load(DRAFTS / "approvals.json", {}).get(key)
    if not req:
        return False
    if updates is None:
        try:
            updates = _tg("getUpdates", {"allowed_updates": json.dumps(["message"]), "limit": 100}).get("result", [])
        except Exception as e:
            alert(f"TaazaBhav jawab: could not read Telegram replies ({e}); {key} not posted.")
            return False
    owner = str(_owner())
    for u in updates:
        m = u.get("message") or {}
        if str((m.get("chat") or {}).get("id")) != owner or m.get("date", 0) < req["sent"]:
            continue
        reply = (m.get("reply_to_message") or {}).get("message_id")
        if reply not in (None, req["message_id"]):
            continue
        words = re.findall(r"[^\s,.!।]+", (m.get("text") or "").lower())
        if words and words[0] in YES:
            return True
    return False


def draft_for(day):
    """Approved draft for this day's 09:30 slot, or None."""
    d = _load(DRAFTS / f"{day.isoformat()}.json", None)
    if d and approved(d["key"]):
        return d
    return None


# ---------------------------------------------------------------- P1 from farmers
def week_reports(day):
    start = (day - timedelta(days=REPORT_DAYS)).isoformat()
    rows = [r for f in PRICES.glob("*.json") for r in _load(f, []) if r.get("date", "") >= start]
    # One report per mandi + crop: the latest.
    best = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        best[(r["mandi"], r["crop"])] = r
    return list(best.values())


def official(feed, crop):
    return next((r["data"] for r in feed.get("reports", []) if r.get("kind") == "crop" and r["data"].get("slug") == crop), None)


def build_p1_farmers(feed, day, reports):
    from posts.pillar import feed_trust, hi_date, make_post, rs
    rows, names = [], {}
    for r in reports:
        o = official(feed, r["crop"])
        if not o or not o.get("typical"):
            continue
        if not SANE[0] <= r["price"] / o["typical"] <= SANE[1]:
            continue
        names[r["crop"]] = o["nameHi"]
        rows.append((r, o))
    if len(rows) < MIN_REPORTS:
        return None
    rows.sort(key=lambda x: x[0]["price"] - x[1]["typical"])
    rows = rows[:MAX_ROWS]
    below = sum(r["price"] < o["typical"] for r, o in rows)
    mandis = len({r["mandi"] for r, _ in rows})
    table = [[f"{r['mandi']} · {o['nameHi']}", f"{rs(r['price'])} ({rs(o['typical'])})"] for r, o in rows]
    gap_r, gap_o = rows[0]
    slides = [
        {"kind": "hook", "label": f"आपकी मंडी रिपोर्ट · किसानों ने बताया · {hi_date(day)}",
         "big": f"{len(rows)} किसान, {mandis} मंडियां: असली बिका भाव", "sub": "पेज पर आपके कमेंट बनाम सरकारी आम भाव →"},
        {"kind": "table", "title": "किसान का बिका भाव (सरकारी आम भाव) ₹/क्विंटल", "rows": table,
         "note": "सरकारी = उस दिन देश की मंडियों का आम भाव, मंडी रिपोर्ट से"},
        {"kind": "list", "title": "क्या दिखा", "items": [
            f"{len(rows)} में से {below} जगह किसान को सरकारी आम भाव से कम मिला",
            f"सबसे बड़ा फ़र्क: {gap_r['mandi']} में {gap_o['nameHi']} {rs(abs(gap_r['price'] - gap_o['typical']))}",
            "बेचने से पहले पास की 2-3 मंडी का भाव मिलाएं"]},
    ]
    lines = [f"किसानों ने कमेंट में बताया, उनकी मंडी में फसल किस भाव बिकी ({hi_date(day)} तक का हफ्ता):"]
    lines += [f"• {r['mandi']} मंडी, {o['nameHi']}: {rs(r['price'])} (सरकारी आम भाव {rs(o['typical'])})" for r, o in rows]
    lines.append(f"{len(rows)} में से {below} जगह भाव सरकारी आम भाव से कम मिला।")
    trust = f"स्रोत: TaazaBhav पेज पर किसानों के कमेंट + मंडी भाव Agmarknet · जाँच: {hi_date(day)} {day.year}"
    post = make_post(f"p1-farmers-{day.isoformat()}", "/mandi-bhav", slides, lines,
                     "आपकी मंडी में इस हफ्ते किस भाव बिका? मंडी, फसल और भाव कमेंट करें, अगली रिपोर्ट में आएगा।",
                     f"किसानों ने बताया असली बिका भाव, {mandis} मंडियां 👇", trust,
                     {"angle": f"farmers-{day.isoformat()}"})
    return post


def calendar_pillar(day):
    from posts.pillar import calendar
    return calendar(day)[1]


def needs_draft(today):
    """Cheap check (no browser): is there a farmer post to ask about tonight?"""
    day = today + timedelta(days=1)
    plan = calendar_pillar(day)
    if not plan or plan["pillar"] not in ("P1", "P2"):
        return False
    if plan["pillar"] == "P1":
        return len(week_reports(today)) >= MIN_REPORTS
    return (PARCHI_POSTS / f"{day.isoformat()}.json").exists()


def make_drafts(today, feed_loader, render=None):
    """Night before a P1/P2 day: build the farmer post and ask the owner."""
    day = today + timedelta(days=1)
    plan = calendar_pillar(day)
    if not plan or plan["pillar"] not in ("P1", "P2"):
        return None
    if plan["pillar"] == "P1":
        reports = week_reports(today)
        if len(reports) < MIN_REPORTS:
            print(f"[jawab] {len(reports)} farmer prices this week, P1 stays the normal one")
            return None
        post = build_p1_farmers(feed_loader(), day, reports)
    else:
        post = _load(PARCHI_POSTS / f"{day.isoformat()}.json", None)
    if not post:
        return None
    key = f"{plan['pillar']}-{day.isoformat()}"
    if render is None:
        from posts.render import render
    post["comment_mode"] = True
    slides = render(post, Path("posts-out"))
    request_approval(key, post, slides, f"{day.day} तारीख 09:30")
    _save(DRAFTS / f"{day.isoformat()}.json", {"key": key, "pillar": plan["pillar"], "post": post})
    return key


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    today = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(IST).date()
    code = 0
    if what in ("collect", "all"):
        import meta_publish as mp
        try:
            token, ig = mp.page_credentials()
            own = _get(ig, token, fields="username").get("username") if ig else None
            prices, parchi = collect(today, token, ig, own)
            print(f"[jawab] {len(prices)} new farmer prices, {len(parchi)} new photos")
            for p in parchi:
                f = PARCHI / p.get("file", "")
                if p.get("file") and f.exists():
                    with open(f, "rb") as fh:
                        _tg("sendPhoto", {"chat_id": _owner(), "caption": f"Nayi parchi/photo comment mein aayi ({p['date']}): {p['note'][:300]}"},
                            {"photo": fh})
        except Exception as e:
            alert(f"TaazaBhav jawab: reading comments failed: {e}"[:600])
            code = 1
    if what == "need":
        need = needs_draft(today)
        print(f"[jawab] farmer draft tonight: {need}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                fh.write(f"need={'1' if need else ''}\n")
    if what in ("draft", "all"):
        try:
            from engine.feed import load_feed
            key = make_drafts(today, lambda: load_feed(today=today))
            print(f"[jawab] draft: {key}")
        except Exception as e:
            alert(f"TaazaBhav jawab: farmer post draft failed: {e}"[:600])
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
