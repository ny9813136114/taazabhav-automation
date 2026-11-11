# -*- coding: utf-8 -*-
"""Every FB/IG feed post and Reel also goes to the Facebook Page Story and
the Instagram Story (owner, 11 Nov 2026: "wo sab stories par bhi jana chahiye").

Called right after a feed post / Reel was published (posts.run.publish and
meta_publish.publish_all). Never raises: a Story problem comes back as error
text and never changes the feed post's result.

  STORIES_LIVE=1 (repo variable): the Story is published on FB + IG.
  otherwise: PREVIEW, the would-be Story goes to the owner's Telegram only.

Carousel -> one 1080x1920 picture: the first slide on a brand background with
"poori post Page par" (links in Stories need a sticker, which the API can't add).
Reel -> the same video as a video Story when it is 3-60 s long (Meta's limit
for API Stories); a longer Reel gets no Story, and the log says so.

Graph API used (token already has pages_manage_posts + instagram_content_publish):
  FB photo:  POST /{page}/photos published=false -> POST /{page}/photo_stories photo_id
  FB video:  POST /{page}/video_stories upload_phase=start|finish (+ rupload)
  IG:        POST /{ig}/media media_type=STORIES (image_url | resumable video) -> media_publish
"""
import base64
import os
import time
from pathlib import Path

import requests

import meta_publish as mp

SW, SH = 1080, 1920
VIDEO_MIN, VIDEO_MAX = 3, 60


def live():
    return os.environ.get("STORIES_LIVE", "").strip() == "1"


# ---------- picture ----------

STORY_HTML = """<!doctype html><meta charset=utf-8><style>
@font-face{{font-family:NS;src:url('{font}')}}
*{{box-sizing:border-box;margin:0}}
body{{width:{w}px;height:{h}px;background:linear-gradient(160deg,#0B4A2C,#0F6B3E 60%,#14261C);
font-family:NS,'Noto Sans Devanagari',sans-serif;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:space-between;overflow:hidden}}
.top{{margin-top:120px;font-size:46px;font-weight:700;color:#FFD65A;text-align:center}}
img{{width:1000px;border-radius:28px;box-shadow:0 18px 50px rgba(0,0,0,.45)}}
.bot{{margin-bottom:150px;text-align:center}}
.cta{{background:#E09A12;color:#14261C;border-radius:24px;padding:26px 54px;font-size:44px;font-weight:800}}
.url{{margin-top:22px;font-size:36px;opacity:.9}}
</style>
<div class="top">{top}</div>
<img src="{img}">
<div class="bot"><div class="cta">{cta}</div><div class="url">taazabhav.com</div></div>"""


def _font_url():
    # Inlined: a page set with set_content() may not load file:// fonts.
    p = Path(__file__).resolve().parent / "assets" / "fonts" / "NotoSansDevanagari-Bold.ttf"
    return "data:font/ttf;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def story_image(slide, dest, top="ताज़ाभाव पर नई पोस्ट", cta="पूरी पोस्ट हमारे पेज पर देखें"):
    """First carousel slide (1080x1350 PNG) -> 1080x1920 Story PNG at dest."""
    from playwright.sync_api import sync_playwright
    img = "data:image/png;base64," + base64.b64encode(Path(slide).read_bytes()).decode()
    html = STORY_HTML.format(font=_font_url(), w=SW, h=SH, img=img, top=mp_escape(top), cta=mp_escape(cta))
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": SW, "height": SH})
        pg.set_content(html, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(dest), full_page=False)
        b.close()
    return dest


def mp_escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- Graph calls ----------

def fb_photo_story(path, page_token, s=requests):
    page = os.environ["FB_PAGE_ID"]
    with open(path, "rb") as fh:
        ph = mp._check(s.post(f"{mp.GRAPH}/{page}/photos", data={"published": "false", "access_token": page_token},
                              files={"source": fh}, timeout=mp.TIMEOUT), "FB story photo upload")
    b = mp._check(s.post(f"{mp.GRAPH}/{page}/photo_stories", data={"photo_id": ph["id"], "access_token": page_token},
                         timeout=mp.TIMEOUT), "FB photo story")
    return b.get("post_id") or ph["id"], ph["id"]


def fb_video_story(path, page_token, s=requests):
    page = os.environ["FB_PAGE_ID"]
    b = mp._check(s.post(f"{mp.GRAPH}/{page}/video_stories",
                         params={"upload_phase": "start", "access_token": page_token}, timeout=mp.TIMEOUT), "FB video story start")
    vid = b["video_id"]
    url = b.get("upload_url") or f"https://rupload.facebook.com/video-upload/{mp.GRAPH_VERSION}/{vid}"
    mp._upload_bytes(s, url, page_token, path)
    b = mp._check(s.post(f"{mp.GRAPH}/{page}/video_stories",
                         params={"upload_phase": "finish", "video_id": vid, "access_token": page_token},
                         timeout=mp.TIMEOUT), "FB video story finish")
    return b.get("post_id") or vid


def _ig_wait_publish(cid, ig, token, s, sleep):
    for _ in range(mp.IG_POLL_MAX):
        st = mp._check(s.get(f"{mp.GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": token},
                             timeout=mp.TIMEOUT), "IG story status")
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise mp.MetaError(f"IG story {code}: {st.get('status') or 'no reason given'}")
        sleep(mp.IG_POLL_SECONDS)
    else:
        raise mp.MetaError("IG story did not finish processing")
    for i in range(mp.IG_PUBLISH_TRIES):
        try:
            b = mp._check(s.post(f"{mp.GRAPH}/{ig}/media_publish", params={"creation_id": cid, "access_token": token},
                                 timeout=mp.TIMEOUT), "IG story publish")
            return b.get("id")
        except mp.MetaError:
            if i == mp.IG_PUBLISH_TRIES - 1:
                raise
            sleep(20)


def ig_image_story(image_url, ig, token, s=requests, sleep=time.sleep):
    b = mp._check(s.post(f"{mp.GRAPH}/{ig}/media", data={"media_type": "STORIES", "image_url": image_url, "access_token": token},
                         timeout=mp.TIMEOUT), "IG story container")
    return _ig_wait_publish(b["id"], ig, token, s, sleep)


def ig_video_story(path, ig, token, s=requests, sleep=time.sleep):
    b = mp._check(s.post(f"{mp.GRAPH}/{ig}/media",
                         params={"media_type": "STORIES", "upload_type": "resumable", "access_token": token},
                         timeout=mp.TIMEOUT), "IG video story container")
    cid = b["id"]
    url = b.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{mp.GRAPH_VERSION}/{cid}"
    mp._upload_bytes(s, url, token, path)
    return _ig_wait_publish(cid, ig, token, s, sleep)


def _photo_url(photo_id, token, s):
    img = mp._check(s.get(f"{mp.GRAPH}/{photo_id}", params={"fields": "images", "access_token": token},
                          timeout=mp.TIMEOUT), "FB story photo url")
    return max(img["images"], key=lambda x: x.get("width", 0))["source"]


def video_seconds(path):
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.count_frames_and_secs(str(path))[1]
    except Exception:
        return None


# ---------- entry points (never raise) ----------

def _preview_photo(what, path):
    from posts.run import _owner, _tg
    with open(path, "rb") as fh:
        _tg("sendPhoto", {"chat_id": _owner(), "disable_notification": "true",
                          "caption": f"STORY PREVIEW (not posted): {what}\nSTORIES_LIVE=1 hone par ye FB + IG Story par jayega."},
            files={"photo": fh})


def share_post(what, slides, page_token, ig, s=requests, sleep=time.sleep, out_dir="posts-out"):
    """Carousel just posted -> its Story. -> {"facebook", "instagram", "errors"}."""
    res = {"facebook": None, "instagram": None, "errors": []}
    try:
        path = story_image(slides[0], Path(out_dir) / f"{what}-story.png")
    except Exception as e:
        res["errors"].append(f"Story picture: {e}")
        return res
    if not live():
        try:
            _preview_photo(what, path)
        except Exception as e:
            print(f"[stories] preview failed: {e}")
        return res
    photo_id = None
    try:
        res["facebook"], photo_id = fb_photo_story(path, page_token, s)
    except Exception as e:
        res["errors"].append(f"FB Story: {e}")
    if ig:
        try:
            if not photo_id:  # IG needs a public URL: upload to FB unpublished just for it
                page = os.environ["FB_PAGE_ID"]
                with open(path, "rb") as fh:
                    photo_id = mp._check(s.post(f"{mp.GRAPH}/{page}/photos", data={"published": "false", "access_token": page_token},
                                                files={"source": fh}, timeout=mp.TIMEOUT), "IG story photo upload")["id"]
            res["instagram"] = ig_image_story(_photo_url(photo_id, page_token, s), ig, page_token, s, sleep)
        except Exception as e:
            res["errors"].append(f"IG Story: {e}")
    return res


def share_reel(what, video_path, page_token, ig, s=requests, sleep=time.sleep):
    """Reel just posted -> the same video as a Story (3-60 s only)."""
    res = {"facebook": None, "instagram": None, "errors": []}
    secs = video_seconds(video_path)
    if secs is not None and not (VIDEO_MIN <= secs <= VIDEO_MAX):
        print(f"[stories] {what}: {secs:.0f}s is outside Meta's {VIDEO_MIN}-{VIDEO_MAX}s Story limit, no Story")
        res["skipped"] = f"{secs:.0f}s"
        return res
    if not live():
        try:
            from notify import send_telegram_alert
            send_telegram_alert(f"STORY PREVIEW: {what} ({secs:.0f}s) bhi FB + IG Story par jayega jab STORIES_LIVE=1 hoga."
                                if secs else f"STORY PREVIEW: {what} bhi FB + IG Story par jayega jab STORIES_LIVE=1 hoga.")
        except Exception as e:
            print(f"[stories] preview failed: {e}")
        return res
    try:
        res["facebook"] = fb_video_story(video_path, page_token, s)
    except Exception as e:
        res["errors"].append(f"FB Story: {e}")
    if ig:
        try:
            res["instagram"] = ig_video_story(video_path, ig, page_token, s, sleep)
        except Exception as e:
            res["errors"].append(f"IG Story: {e}")
    return res
