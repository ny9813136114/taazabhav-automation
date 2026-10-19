# -*- coding: utf-8 -*-
"""Daily "tool se hal" carousel post on the Facebook Page + Instagram.

One post a day from content/tool_posts.json (numbers built from the website's
own tool code by ops/build_tool_posts.ts), rendered to PNG slides.

  preview (default): slides go to the owner's Telegram chat only.
  publish (repo variable POSTS_LIVE=1): FB multi-photo post + IG carousel,
  then a "share kit" (post link + group text) to the owner's Telegram so
  they can share it into mandi/kisan groups by hand (Meta has no groups API).

python -m posts.run [preview|publish|dry]"""
import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

QUEUE = Path("content/tool_posts.json")
STATE = Path("data/posts/state.json")
IST = timezone(timedelta(hours=5, minutes=30))


def mode():
    m = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if m:
        return m
    return "publish" if os.environ.get("POSTS_LIVE", "").strip() == "1" else "preview"


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"history": []}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def d_tool(today):
    """Tool the YouTube engine's series D is likely to show today (same rotation
    as engine.tools.pick_d), so the carousel and the Reel don't repeat it."""
    ids = ["khad", "msp", "hisab", "nuksan"]
    return ids[today.toordinal() % len(ids)]


def pick(posts, history, today):
    """Next post after the last one used, skipping expired posts, today's D
    tool and anything posted in the last len(posts)-1 days' worth."""
    live = [p for p in posts if not p.get("validUntil") or date.fromisoformat(p["validUntil"]) >= today]
    if not live:
        return None
    recent = {h["id"] for h in history[-(len(live) - 1):]} if len(live) > 1 else set()
    last = history[-1]["id"] if history else None
    ids = [p["id"] for p in posts]
    start = ids.index(last) + 1 if last in ids else 0
    avoid = d_tool(today)
    order = [posts[(start + i) % len(posts)] for i in range(len(posts))]
    for strict in (True, False):
        for p in order:
            if p in live and p["id"] not in recent and (not strict or p["tool"] != avoid):
                return p
    return live[0]


def _tg(method, data, files=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, files=files, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram {method} HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def _owner():
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat:
        raise RuntimeError("TELEGRAM_CHAT_ID not set")
    return chat


def send_preview(post, slides):
    files = {f"s{i}": open(p, "rb") for i, p in enumerate(slides)}
    try:
        media = [{"type": "photo", "media": f"attach://s{i}"} for i in range(len(slides))]
        media[0]["caption"] = f"PREVIEW (not posted): {post['id']}\n\n{post['caption']}"[:1000]
        _tg("sendMediaGroup", {"chat_id": _owner(), "media": json.dumps(media)}, files)
    finally:
        for f in files.values():
            f.close()


def alert(msg):
    try:
        from notify import send_telegram_alert
        send_telegram_alert(msg)
    except Exception:
        print("[posts] alert failed:", msg)


# ---------- Meta ----------

def post_facebook(slides, caption, page_token, s=requests):
    import meta_publish as mp
    page = os.environ["FB_PAGE_ID"]
    ids = []
    for p in slides:
        with open(p, "rb") as fh:
            b = mp._check(s.post(f"{mp.GRAPH}/{page}/photos", data={"published": "false", "access_token": page_token},
                                 files={"source": fh}, timeout=mp.TIMEOUT), "FB photo upload")
        ids.append(b["id"])
    data = {"message": caption, "access_token": page_token}
    for i, pid in enumerate(ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    b = mp._check(s.post(f"{mp.GRAPH}/{page}/feed", data=data, timeout=mp.TIMEOUT), "FB post")
    return b["id"], ids


def post_instagram(photo_ids, caption, ig, token, s=requests, sleep=time.sleep):
    """IG takes images only by public URL: use the Facebook CDN URL of the
    photos just uploaded to the Page."""
    import meta_publish as mp
    children = []
    for pid in photo_ids:
        img = mp._check(s.get(f"{mp.GRAPH}/{pid}", params={"fields": "images", "access_token": token}, timeout=mp.TIMEOUT), "FB photo url")
        url = max(img["images"], key=lambda x: x.get("width", 0))["source"]
        c = mp._check(s.post(f"{mp.GRAPH}/{ig}/media", data={"image_url": url, "is_carousel_item": "true", "access_token": token},
                             timeout=mp.TIMEOUT), "IG item")
        children.append(c["id"])
    box = mp._check(s.post(f"{mp.GRAPH}/{ig}/media", data={"media_type": "CAROUSEL", "children": ",".join(children),
                                                            "caption": caption, "access_token": token}, timeout=mp.TIMEOUT), "IG carousel")
    for _ in range(mp.IG_POLL_MAX):
        st = mp._check(s.get(f"{mp.GRAPH}/{box['id']}", params={"fields": "status_code", "access_token": token},
                             timeout=mp.TIMEOUT), "IG status").get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise mp.MetaError(f"IG carousel {st}")
        sleep(mp.IG_POLL_SECONDS)
    b = mp._check(s.post(f"{mp.GRAPH}/{ig}/media_publish", data={"creation_id": box["id"], "access_token": token},
                         timeout=mp.TIMEOUT), "IG publish")
    return b.get("id")


def publish(post, slides):
    import meta_publish as mp
    if not mp.enabled():
        raise RuntimeError("META_TOKEN / FB_PAGE_ID not set")
    out = {"facebook": None, "instagram": None, "errors": []}
    token, ig = mp.page_credentials()
    fb_id, photo_ids = post_facebook(slides, post["caption"], token)
    out["facebook"] = fb_id
    if ig:
        try:
            out["instagram"] = post_instagram(photo_ids, post["caption"], ig, token)
        except Exception as e:
            out["errors"].append(f"Instagram: {e}")
    else:
        out["errors"].append("Instagram: no account linked to the Page")
    return out


def share_kit(post, fb_id):
    link = f"https://www.facebook.com/{fb_id}"
    text = (f"आज की पोस्ट शेयर करें (3-4 ग्रुप, रोज़ अलग ग्रुप):\n{link}\n\n"
            f"ग्रुप में ये लिखें:\n{post['group']}")
    _tg("sendMessage", {"chat_id": _owner(), "text": text, "disable_web_page_preview": "false"})


def main():
    run_mode = mode()
    today = datetime.now(IST).date()
    posts = json.loads(QUEUE.read_text(encoding="utf-8"))["posts"]
    state = load_state()
    if run_mode == "publish" and any(h["date"] == today.isoformat() for h in state.get("history", [])):
        print("[posts] already posted today")
        return 0
    key = "history" if run_mode == "publish" else "preview"
    post = pick(posts, state.get(key, []), today)
    if not post:
        alert("TaazaBhav posts: no post left in content/tool_posts.json (all expired).")
        return 1
    print(f"[posts] {run_mode}: {post['id']}")
    try:
        from posts.render import render
        slides = render(post, Path("posts-out"))
        if run_mode == "dry":
            print("\n".join(map(str, slides)))
            return 0
        if run_mode == "preview":
            send_preview(post, slides)
            # Previews walk the queue too, so the owner sees a different post each day.
            state.setdefault("preview", []).append({"date": today.isoformat(), "id": post["id"]})
            save_state(state)
            return 0
        res = publish(post, slides)
        state.setdefault("history", []).append({"date": today.isoformat(), "id": post["id"], "facebook": res["facebook"], "instagram": res["instagram"]})
        save_state(state)
        if res["errors"]:
            alert(f"TaazaBhav posts ({post['id']}): " + "\n".join(res["errors"])[:500])
        try:
            share_kit(post, res["facebook"])
        except Exception as e:
            alert(f"TaazaBhav posts: share kit failed: {e}")
        print(f"[posts] published FB {res['facebook']} IG {res['instagram']}")
        return 0
    except Exception as e:
        traceback.print_exc()
        alert(f"TaazaBhav posts: {post['id']} failed, nothing posted today.\n\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
