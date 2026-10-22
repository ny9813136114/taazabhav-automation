# -*- coding: utf-8 -*-
"""Batch 7 (27 Sep 2026): "किसान मेला अलर्ट" Shorts from the Kisan Mela
calendar on taazabhav.com.

Source of truth = the LIVE site, not a copy: /kisan-mela/sitemap.xml lists
every event page; each CONFIRMED event page carries schema.org Event JSON-LD
("expected" events deliberately have none). So a video can only ever show
dates the site itself states as confirmed -- dates are never guessed, and
when the calendar is updated the videos follow automatically.

Does NOT use data.gov.in, so it keeps publishing during mandi-data outages.

Schedule (workflow melas.yml, daily ~17:15 IST): an event gets a video
7 days before it starts ("7 दिन बाकी") and 1 day before ("कल से शुरू!").
Each (event, stage) is uploaded once -- data/published_melas.json.
"""
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

import requests

from hindi_names import date_hi

SITE = os.environ.get("TAAZABHAV_SITE", "https://taazabhav.com")
STAGES = {7: "week", 1: "tomorrow"}  # days before start -> stage key
PUBLISHED = Path("data/published_melas.json")
IST = timezone(timedelta(hours=5, minutes=30))
UA = {"User-Agent": "TaazaBhavBot/1.0 (+https://taazabhav.com)"}
TIMEOUT = 30


# ---------------------------------------------------------------- reading
def event_urls(s=requests):
    r = s.get(f"{SITE}/kisan-mela/sitemap.xml", headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    root = ElementTree.fromstring(r.content)
    urls = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
    # event pages only: /kisan-mela/<slug> (not the list, not /state/..)
    return [u for u in urls if re.search(r"/kisan-mela/(?!state/)[^/?#]+/?$", u)]


def _walk(node):
    if isinstance(node, list):
        for n in node:
            yield from _walk(n)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from _walk(node["@graph"])


def _is_event(n):
    t = n.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(isinstance(x, str) and x.endswith("Event") for x in types)


def _d(v):
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except ValueError:
        return None


def parse_event(html, url):
    """Event dict from a page's JSON-LD, or None (e.g. an 'expected' event)."""
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(unescape(block.strip()))
        except ValueError:
            continue
        for n in _walk(data):
            if not _is_event(n):
                continue
            start = _d(n.get("startDate"))
            if not start or not n.get("name"):
                continue
            loc = n.get("location") or {}
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            addr = loc.get("address") or {}
            if isinstance(addr, str):
                addr = {"streetAddress": addr}
            return {
                "slug": url.rstrip("/").rsplit("/", 1)[-1],
                "url": url,
                "name": str(n["name"]).strip(),
                "start": start,
                "end": _d(n.get("endDate")) or start,
                "venue": str(loc.get("name") or "").strip(),
                "city": str(addr.get("addressLocality") or "").strip(),
                "state": str(addr.get("addressRegion") or "").strip(),
                "status": str(n.get("eventStatus") or ""),
            }
    return None


def fetch_events(s=requests):
    out = []
    for u in event_urls(s):
        try:
            r = s.get(u, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            ev = parse_event(r.text, u)
            if ev and not ev["status"].endswith(("EventCancelled", "EventPostponed")):
                out.append(ev)
        except Exception as e:
            print(f"[melas] skip {u}: {e}")
    return out


# ---------------------------------------------------------------- choosing
def due(events, today, published):
    """[(event, days_left, stage)] due today and not yet published."""
    res = []
    for ev in events:
        days = (ev["start"] - today).days
        stage = STAGES.get(days)
        if stage and f"{ev['slug']}:{ev['start'].isoformat()}:{stage}" not in published:
            res.append((ev, days, stage))
    return sorted(res, key=lambda x: x[1])


def load_published():
    try:
        return set(json.loads(PUBLISHED.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def mark_published(key):
    p = load_published()
    p.add(key)
    PUBLISHED.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED.write_text(json.dumps(sorted(p), ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- content
def date_range_hi(start, end):
    if end == start:
        return f"{date_hi(start)} {start.year}"
    if (start.month, start.year) == (end.month, end.year):
        return f"{start.day}–{date_hi(end)} {end.year}"
    return f"{date_hi(start)} – {date_hi(end)} {end.year}"


def place(ev):
    parts = [p for p in (ev["venue"], ev["city"], ev["state"]) if p]
    seen, out = set(), []
    for p in parts:  # venue often already contains the city
        if p.lower() not in seen and not any(p.lower() in o.lower() for o in out):
            out.append(p); seen.add(p.lower())
    return ", ".join(out)


def build_props(ev, days, clip=None, credit=None):
    return {
        "clip": clip, "credit": credit,
        "badge": "किसान मेला अलर्ट",
        "countdown": "कल से शुरू!" if days == 1 else f"{days} दिन बाकी",
        "urgent": days <= 1,
        "name": ev["name"],
        "dates": date_range_hi(ev["start"], ev["end"]),
        "place": place(ev),
        "cta": "तारीख, पता, कैलेंडर में जोड़ें:",
        "link": "taazabhav.com/kisan-mela",
        "seconds": 9,
    }


def metadata(ev, days):
    when = "कल से" if days == 1 else f"{days} दिन बाद"
    city = ev["city"] or ev["state"]
    title = f"{ev['name']} {when} शुरू! {date_range_hi(ev['start'], ev['end'])} | Kisan Mela {ev['start'].year} {city} #Shorts"
    if len(title) > 100:
        title = f"{ev['name']} {when}! | Kisan Mela {ev['start'].year} #Shorts"
    title = title[:100]
    link = ev["url"]
    desc = (
        f"{ev['name']} — {date_range_hi(ev['start'], ev['end'])}, {place(ev)}.\n"
        f"पूरी जानकारी, नक्शा और कैलेंडर में जोड़ें: {link}\n\n"
        f"सभी किसान मेले और कृषि प्रदर्शनी: {SITE}/kisan-mela\n"
        "तारीखें आयोजक की घोषणा के अनुसार; जाने से पहले आयोजक से पुष्टि करें।\n\n"
        "Telegram: https://t.me/taazabhav\n"
        f"#kisanmela #krishimela #agriexpo #{re.sub(r'[^a-z0-9]', '', (ev['state'] or 'india').lower())} #shorts"
    )
    tags = ["kisan mela", "krishi mela", "agri expo", ev["name"], f"kisan mela {ev['start'].year}",
            f"kisan mela {city}".strip(), "किसान मेला", "कृषि मेला"]
    comment = f"आप {ev['name']} जा रहे हैं? पूरी जानकारी: {link}"
    return title, desc, [t for t in tags if t], comment


# ---------------------------------------------------------------- render + run
def render(props, out_path):
    shorts = Path("shorts")
    pub = shorts / "public"
    (pub / "fonts").mkdir(parents=True, exist_ok=True)
    for f in ("Baloo2-Bold.ttf", "IBMPlexMono-SemiBold.ttf"):
        (pub / "fonts" / f).write_bytes((Path("assets/fonts") / f).read_bytes())
    if props.get("clip"):
        (pub / "clip.mp4").write_bytes(Path(props["clip"]).read_bytes())
        props = {**props, "clip": "clip.mp4"}
    pf = (shorts / "props.json").resolve()
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "src/Root.tsx", "MelaAlert", str(Path(out_path).resolve()),
           f"--props={pf}", "--log=error"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        cmd.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    subprocess.run(cmd, cwd=shorts, check=True, timeout=600)
    return out_path


def main():
    from notify import send_telegram_alert
    today = datetime.now(IST).date()
    try:
        events = fetch_events()
    except Exception as e:
        send_telegram_alert(f"TaazaBhav ALERT: could not read Kisan Mela calendar\n\n{e}")
        return 1
    todo = due(events, today, load_published())
    print(f"[melas] {len(events)} confirmed events, {len(todo)} due today")
    failed = 0
    for i, (ev, days, stage) in enumerate(todo[:3]):  # at most 3 a day
        key = f"{ev['slug']}:{ev['start'].isoformat()}:{stage}"
        out = f"mela_{i}.mp4"
        try:
            from fetch_clips import pick_clip, credit_for
            clip = pick_clip("generic", today, 10 + i)
            c = credit_for(clip)
            credit = f"Video: {c['author']} / {c['source']}" if c else None
            render(build_props(ev, days, str(clip) if clip else None, credit), out)
            title, desc, tags, comment = metadata(ev, days)
            if credit:
                desc = desc.replace("\n\nTelegram", f"\n{credit}\n\nTelegram", 1)
            from upload_youtube import upload_video
            vid = upload_video(out, title, desc, tags, thumbnail_path=None, comment_text=comment)
            mark_published(key)
            print(f"[melas] uploaded {key}: https://youtu.be/{vid}")
            try:
                import meta_publish
                if meta_publish.enabled():
                    cap = f"{title.split('|')[0].strip()}\n\n{desc.split(chr(10))[0]}\n\n🌐 पूरी जानकारी: taazabhav.com/kisan-mela (लिंक बायो में)\n\n#kisanmela #krishimela #agriexpo #kisan #taazabhav"
                    res = meta_publish.publish_all(out, cap, comment="👉 मेले की पूरी जानकारी, तारीख और जगह: https://taazabhav.com/kisan-mela", what="mela Reel")
                    if res.get("facebook") or res.get("instagram"):
                        from posts import ledger
                        ledger.safe_record(ledger.entry(day=today, slot="17:13", fmt="reel", pillar="mela", post_id=key,
                                                        caption=cap, state=ev.get("state") or None,
                                                        facebook=res.get("facebook"), instagram=res.get("instagram")))
                    if res["errors"]:
                        send_telegram_alert("TaazaBhav ALERT: mela Reel issue\n\n" + "\n".join(res["errors"]))
            except Exception as e:
                send_telegram_alert(f"TaazaBhav ALERT: mela Reel failed\n\n{e}")
        except Exception as e:
            failed += 1
            traceback.print_exc()
            send_telegram_alert(f"TaazaBhav ALERT: mela video failed for {ev['name']}\n\n{e}")
        finally:
            if os.path.exists(out):
                os.remove(out)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
