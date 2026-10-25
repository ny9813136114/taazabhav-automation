# -*- coding: utf-8 -*-
"""Preview to the owner, or publish: YouTube upload + playlist + comment,
then the Telegram channel, then the same video as a Facebook + Instagram Reel."""
import json
import os
import pickle
from pathlib import Path

import requests

PLAYLISTS = Path("data/engine/playlists.json")
# Videos whose playlist add failed even after retries; every publish tries
# them again first (20 Oct 2026: B HSgV2jIHyOw hit YouTube's 409).
PLAYLIST_PENDING = Path("data/engine/playlist_pending.json")
PLAYLIST_NAMES = {
    "A": ("भाव धमाका – आज के मंडी भाव | Mandi Bhav Today", "रोज़ सुबह 7:30 बजे: आज का सबसे बड़ा मंडी भाव, उछाल-गिरावट और फ़ैसला। सरकारी आँकड़े, ताज़ा भाव।"),
    "B": ("किस्त का सच – PM Kisan, MP, Rajasthan | Kist Date", "किस्त की सिर्फ़ सरकारी तारीख। वायरल दावों का सच। ताज़ा भाव किस्त ट्रैकर।"),
    "C": ("किसान खबर – रोज़ की 3 खबर | Kisan News", "रोज़ शाम 6:30 बजे: आज की 3 काम की खबर, 40 सेकंड में।"),
    "D": ("टूल से हल – किसान के मुफ़्त टूल | Free Kisan Tools", "खाद, मंडी पर्ची, MSP बनाम मंडी, फ़सल नुकसान: ताज़ा भाव के मुफ़्त टूल, असली स्क्रीन पर।"),
}
CHANNEL = "@taazabhav"


def _tg(method, data, files=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, files=files, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram {method} HTTP {r.status_code}: {r.text[:300]}")


def send_preview(path, ep, seconds):
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat:
        raise RuntimeError("TELEGRAM_CHAT_ID not set")
    cap = f"PREVIEW ({ep['series']}, {seconds:.0f}s, not posted)\n{ep['title']}\n\nComment: {ep['comment']}"
    with open(path, "rb") as f:
        _tg("sendVideo", {"chat_id": chat, "caption": cap[:1000], "supports_streaming": "true"}, files={"video": f})


def _youtube():
    from googleapiclient.discovery import build
    with open("token.pickle", "rb") as f:
        return build("youtube", "v3", credentials=pickle.load(f))


def youtube_login_problem():
    """None when the saved YouTube login still works, else the reason.
    Checked on every run, previews too, so an expired login shows up before
    a publish day instead of on it (18 Oct 2026)."""
    try:
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
        from google.auth.transport.requests import Request
        if not getattr(creds, "refresh_token", None):
            return "token.pickle has no refresh token"
        creds.refresh(Request())
        return None
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def playlist_id(youtube, series):
    ids = json.loads(PLAYLISTS.read_text(encoding="utf-8")) if PLAYLISTS.exists() else {}
    if ids.get(series):
        return ids[series]
    title, desc = PLAYLIST_NAMES[series]
    from upload_youtube import execute
    r = execute(youtube.playlists().insert(part="snippet,status", body={
        "snippet": {"title": title, "description": desc, "defaultLanguage": "hi"}, "status": {"privacyStatus": "public"}}))
    ids[series] = r["id"]
    PLAYLISTS.parent.mkdir(parents=True, exist_ok=True)
    PLAYLISTS.write_text(json.dumps(ids, indent=1), encoding="utf-8")
    return r["id"]


def _pending():
    try:
        return json.loads(PLAYLIST_PENDING.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def add_to_playlists(series, vid, alert, youtube=None):
    """Adds vid, plus any earlier video still pending, to its series playlist.
    A pending video is checked first so it is never added twice. Only a
    failure of today's video is alerted, once; it stays pending."""
    from upload_youtube import execute
    todo = [p for p in _pending() if p["video"] != vid] + [{"series": series, "video": vid}]
    left = []
    try:
        yt = youtube or _youtube()
    except Exception as e:
        yt, err = None, e
    for p in todo:
        try:
            if yt is None:
                raise err
            pl = playlist_id(yt, p["series"])
            if p["video"] != vid and execute(yt.playlistItems().list(part="id", playlistId=pl, videoId=p["video"])).get("items"):
                continue
            execute(yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": p["video"]}}}))
        except Exception as e:
            left.append(p)
            if p["video"] == vid:
                alert(f"TaazaBhav engine: playlist add failed ({series}) after retries, will retry on the next video: {e}"[:600])
    PLAYLIST_PENDING.parent.mkdir(parents=True, exist_ok=True)
    PLAYLIST_PENDING.write_text(json.dumps(left, indent=1), encoding="utf-8")
    return left


def publish(path, ep, alert):
    from upload_youtube import upload_video
    vid = upload_video(path, ep["title"], ep["description"], ep["tags"], thumbnail_path=None, comment_text=ep["comment"])
    add_to_playlists(ep["series"], vid, alert)
    try:
        _tg("sendMessage", {"chat_id": CHANNEL, "text": f"{ep['title'].replace(' #Shorts', '')}\n\n▶️ https://youtu.be/{vid}\n🌐 {ep['link']}",
                            "disable_web_page_preview": "false"})
    except Exception as e:
        alert(f"TaazaBhav engine: Telegram channel post failed: {e}")
    meta_reels(path, ep, alert)
    return vid


def meta_caption(ep):
    """Reel caption: the title without #Shorts, then the YouTube description.
    Meta's limit is 2200 characters."""
    title = ep["title"].replace(" #Shorts", "").strip()
    return f"{title}\n\n{ep['description']}"[:2200]


def meta_reels(path, ep, alert):
    """Never changes the YouTube result: any Meta error is only alerted."""
    import meta_publish
    if not meta_publish.enabled():
        return None
    if not meta_publish.on_meta(ep["series"]):
        print(f"[engine] Meta Reel: series {ep['series']} is off (META_ON), YouTube only")
        return None
    try:
        res = meta_publish.publish_all(path, meta_caption(ep), comment=ep.get("comment"), what=f"Reel {ep['series']}")
    except Exception as e:
        res = {"errors": [str(e)]}
    print(f"[engine] Meta Reel: FB {res.get('facebook')} IG {res.get('instagram')}")
    for err in res.get("errors") or []:
        print(f"[engine] Meta error: {err}")
    if res.get("errors"):
        alert(f"TaazaBhav engine: FB/IG Reel ({ep['series']}) failed:\n" + "\n".join(res["errors"])[:500])
    if res.get("facebook") or res.get("instagram"):
        ledger_record(ep, res)
    return res


SLOTS = {"A": "07:30", "D": "12:30", "C": "18:30", "B": "20:30"}


def ledger_record(ep, res, today=None):
    """Logs the Reel in the FB/IG no-repeat ledger, so the day's photo posts
    don't repeat its tool or crop (posts/ledger.py)."""
    from datetime import datetime
    from posts import ledger
    from posts.run import IST
    day = today or datetime.now(IST).date()
    crop = ep["key"].split("|")[0].lower() if ep["series"] == "A" else None
    return ledger.safe_record(ledger.entry(
        day=day, slot=SLOTS.get(ep["series"], ""), fmt="reel", pillar=ep["series"], post_id=ep["key"],
        hook=ep["title"].replace(" #Shorts", "").strip(), tool=ep.get("tool"), crop=crop,
        facebook=res.get("facebook"), instagram=res.get("instagram")))
