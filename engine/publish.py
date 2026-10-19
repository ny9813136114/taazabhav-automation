# -*- coding: utf-8 -*-
"""Preview to the owner, or publish: YouTube upload + playlist + comment,
then the Telegram channel, then the same video as a Facebook + Instagram Reel."""
import json
import os
import pickle
from pathlib import Path

import requests

PLAYLISTS = Path("data/engine/playlists.json")
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
    r = youtube.playlists().insert(part="snippet,status", body={
        "snippet": {"title": title, "description": desc, "defaultLanguage": "hi"}, "status": {"privacyStatus": "public"}}).execute()
    ids[series] = r["id"]
    PLAYLISTS.parent.mkdir(parents=True, exist_ok=True)
    PLAYLISTS.write_text(json.dumps(ids, indent=1), encoding="utf-8")
    return r["id"]


def publish(path, ep, alert):
    from upload_youtube import upload_video
    vid = upload_video(path, ep["title"], ep["description"], ep["tags"], thumbnail_path=None, comment_text=ep["comment"])
    try:
        yt = _youtube()
        yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id(yt, ep["series"]),
                                                                    "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    except Exception as e:
        alert(f"TaazaBhav engine: playlist add failed ({ep['series']}): {e}")
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
    try:
        res = meta_publish.publish_all(path, meta_caption(ep))
    except Exception as e:
        res = {"errors": [str(e)]}
    print(f"[engine] Meta Reel: FB {res.get('facebook')} IG {res.get('instagram')}")
    if res.get("errors"):
        alert(f"TaazaBhav engine: FB/IG Reel ({ep['series']}) failed:\n" + "\n".join(res["errors"])[:500])
    return res
