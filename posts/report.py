# -*- coding: utf-8 -*-
"""Somvar Meta report (TaazaBhav FB/IG Content Engine plan, section 7).

Every Monday 08:30 IST: each Facebook + Instagram post of the last Monday-
Sunday week, with its reach, shares, comments, reactions/likes and saves,
straight from Meta. The full numbers are saved as JSON (the workflow keeps
them on the `reports` branch) and the owner gets a 5-line Telegram report:
the week's totals, the strongest and weakest format, the top post, and the
change from the week before (the first week is only the baseline).

Format = the daily slot the post went out in (07:30 Bhav Dhamaka Reel,
09:30 pillar/tool post, ...), matched by the post's time, so it works for
every poster without each one having to log anything.

Shares, comments and saves weigh most: shares are Meta's heaviest signal
and comments show which question works (plan, sections 2 and 7).

python -m posts.report [send|dry] [YYYY-MM-DD of the Monday] [reports dir]
(dry without a date: this week so far, printed only)"""
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import requests

from posts.run import IST, _owner, _tg

# Slot (IST) -> format name, as the owner knows them.
SLOTS = [("07:30", "Bhav Dhamaka Reel"), ("09:30", "09:30 post"), ("12:30", "Tool se hal Reel"),
         ("14:30", "Bhav carousel"), ("17:13", "Mela alert Reel"), ("18:30", "Kisan Khabar Reel"),
         ("20:30", "Kist ka Sach Reel")]
# Candidate reach metrics, newest first: Meta renamed several of them in 2025.
FB_REACH = ["post_total_media_view_unique", "post_impressions_unique"]
IG_METRICS = ["reach", "shares", "saved", "views", "total_interactions"]
PAGE_LIMIT = 50


def week_of(monday):
    """The Monday-Sunday week before this Monday, as IST datetimes."""
    start = datetime.combine(monday - timedelta(days=7), time(0), IST)
    return start, start + timedelta(days=7)


def slot_of(ts):
    """Nearest daily slot to a post time (IST) -> format name."""
    t = ts.astimezone(IST)
    mins = t.hour * 60 + t.minute
    best = min(SLOTS, key=lambda s: abs(int(s[0][:2]) * 60 + int(s[0][3:]) - mins))
    return best[1]


def _ts(s):
    return datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")


def _get(s, path, token, **params):
    r = s.get(f"https://graph.facebook.com/{os.environ.get('META_GRAPH_VERSION', 'v23.0')}/{path}",
              params={**params, "access_token": token}, timeout=60)
    b = r.json() if r.content else {}
    if r.status_code != 200 or "error" in b:
        raise RuntimeError((b.get("error") or {}).get("message") or f"HTTP {r.status_code}")
    return b


def _pages(s, path, token, start, **params):
    """Follow paging until posts are older than the week."""
    out, after = [], None
    for _ in range(10):
        b = _get(s, path, token, limit=PAGE_LIMIT, **({"after": after} if after else {}), **params)
        data = b.get("data", [])
        out += data
        after = (b.get("paging") or {}).get("cursors", {}).get("after")
        if not data or not after or not b.get("paging", {}).get("next"):
            break
        last = data[-1].get("created_time") or data[-1].get("timestamp")
        if last and _ts(last) < start:
            break
    return out


def fb_reach(s, pid, token, cache):
    """First reach metric this Page accepts; remembered for the run."""
    for m in sorted(FB_REACH, key=lambda m: m != cache.get("fb")):
        try:
            v = _get(s, f"{pid}/insights", token, metric=m).get("data", [])
            cache["fb"] = m
            return (v[0]["values"][0]["value"] if v else None)
        except Exception:
            continue
    return None


def fb_posts(s, page, token, start, end):
    rows, cache = [], {}
    fields = "id,created_time,message,permalink_url,status_type,shares,comments.summary(true).limit(0),reactions.summary(true).limit(0)"
    for p in _pages(s, f"{page}/posts", token, start, fields=fields):
        ts = _ts(p["created_time"])
        if not (start <= ts < end):
            continue
        rows.append({"net": "facebook", "id": p["id"], "time": ts.astimezone(IST).isoformat(), "format": slot_of(ts),
                     "hook": (p.get("message") or "").split("\n")[0][:90], "link": p.get("permalink_url"),
                     "reach": fb_reach(s, p["id"], token, cache),
                     "shares": (p.get("shares") or {}).get("count", 0),
                     "comments": ((p.get("comments") or {}).get("summary") or {}).get("total_count", 0),
                     "reactions": ((p.get("reactions") or {}).get("summary") or {}).get("total_count", 0)})
    return rows


def ig_insights(s, mid, token):
    """Each metric alone: one a media type doesn't support must not hide the rest."""
    out = {}
    for m in IG_METRICS:
        try:
            v = _get(s, f"{mid}/insights", token, metric=m).get("data", [])
            if v:
                out[m] = v[0].get("values", [{}])[0].get("value", v[0].get("total_value", {}).get("value"))
        except Exception:
            continue
    return out


def ig_posts(s, ig, token, start, end):
    rows = []
    fields = "id,timestamp,caption,media_product_type,permalink,like_count,comments_count"
    for p in _pages(s, f"{ig}/media", token, start, fields=fields):
        ts = _ts(p["timestamp"])
        if not (start <= ts < end):
            continue
        ins = ig_insights(s, p["id"], token)
        rows.append({"net": "instagram", "id": p["id"], "time": ts.astimezone(IST).isoformat(), "format": slot_of(ts),
                     "hook": (p.get("caption") or "").split("\n")[0][:90], "link": p.get("permalink"),
                     "reach": ins.get("reach"), "shares": ins.get("shares", 0), "saves": ins.get("saved", 0),
                     "views": ins.get("views"), "comments": p.get("comments_count", 0), "reactions": p.get("like_count", 0)})
    return rows


def score(r):
    """Shares and saves count double: the signals the plan grows on."""
    return 2 * (r.get("shares") or 0) + 2 * (r.get("saves") or 0) + (r.get("comments") or 0)


def summarise(rows):
    tot = {k: sum(r.get(k) or 0 for r in rows) for k in ("reach", "shares", "comments", "saves", "reactions")}
    fmts = {}
    for r in rows:
        f = fmts.setdefault(r["format"], {"posts": 0, "score": 0, "reach": 0})
        f["posts"] += 1
        f["score"] += score(r)
        f["reach"] += r.get("reach") or 0
    for f in fmts.values():
        f["per_post"] = round(f["score"] / f["posts"], 1)
    return {"posts": len(rows), "fb": sum(r["net"] == "facebook" for r in rows),
            "ig": sum(r["net"] == "instagram" for r in rows), "total": tot, "formats": fmts}


def _n(x):
    return f"{x:,}"


def message(start, summ, rows, prev=None):
    """The 5-line Telegram report."""
    end = start + timedelta(days=6)
    t = summ["total"]
    lines = [f"📊 Meta report {start:%d %b} - {end:%d %b}: {summ['posts']} posts (FB {summ['fb']}, IG {summ['ig']}), "
             f"reach {_n(t['reach'])}, shares {t['shares']}, comments {t['comments']}, saves {t['saves']}."]
    fm = sorted(summ["formats"].items(), key=lambda kv: kv[1]["per_post"], reverse=True)
    if fm:
        best, worst = fm[0], fm[-1]
        lines.append(f"💪 Sabse tagda: {best[0]} ({best[1]['per_post']} share+save+comment score har post).")
        lines.append(f"🐢 Sabse kamzor: {worst[0]} ({worst[1]['per_post']} har post, {worst[1]['posts']} post).")
    top = max(rows, key=score, default=None)
    if top and score(top):
        lines.append(f"🏆 Top post ({top['net'].upper()[:2]}, {top['format']}): {top['shares']} shares, "
                     f"{top.get('saves', 0)} saves, {top['comments']} comments. {top['link'] or ''}".strip())
    else:
        lines.append("🏆 Is hafte kisi post par share, save ya comment nahi aaya.")
    if prev:
        pt = prev["summary"]["total"]
        ch = lambda k: f"{k} {t[k] - pt.get(k, 0):+d}"
        lines.append("📈 Pichhle hafte se: " + ", ".join(ch(k) for k in ("reach", "shares", "comments", "saves")) + ".")
    else:
        lines.append("📍 Pehla hafta: yeh baseline hai, target agle hafte se.")
    return "\n".join(lines)


def previous(dir_, monday):
    files = sorted(p for p in Path(dir_).glob("*.json") if p.stem < monday.isoformat())
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main():
    run_mode = sys.argv[1] if len(sys.argv) > 1 else "send"
    today = datetime.now(IST).date()
    monday = today - timedelta(days=today.weekday())
    if len(sys.argv) > 2 and sys.argv[2]:
        monday = date.fromisoformat(sys.argv[2])
    elif run_mode == "dry":
        monday += timedelta(days=7)  # a check: this week so far
    out_dir = Path(sys.argv[3] if len(sys.argv) > 3 else "reports-out/meta")
    import meta_publish as mp
    start, end = week_of(monday)
    token, ig = mp.page_credentials()
    errors, rows = [], []
    try:
        rows += fb_posts(requests, os.environ["FB_PAGE_ID"], token, start, end)
    except Exception as e:
        errors.append(f"Facebook: {e}")
    if ig:
        try:
            rows += ig_posts(requests, ig, token, start, end)
        except Exception as e:
            errors.append(f"Instagram: {e}")
    summ = summarise(rows)
    msg = message(start.date(), summ, rows, previous(out_dir, monday))
    if errors:
        msg += "\n⚠️ " + "; ".join(errors)[:400]
    print(msg)
    for r in sorted(rows, key=score, reverse=True)[:15]:
        print(" ", r["net"][:2], r["format"], r.get("reach"), r["shares"], r.get("saves", 0), r["comments"], r["hook"][:50])
    if run_mode == "dry":
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{monday.isoformat()}.json").write_text(json.dumps(
        {"week_start": start.date().isoformat(), "summary": summ, "posts": rows, "errors": errors},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _tg("sendMessage", {"chat_id": _owner(), "text": msg, "disable_web_page_preview": "true"})
    return 1 if errors and not rows else 0


if __name__ == "__main__":
    sys.exit(main())
