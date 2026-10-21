# -*- coding: utf-8 -*-
"""Batch 6 (27 Sep 2026): posts each "भाव फ्लैश" Short as a Reel on the
TaazaBhav Facebook Page and the linked Instagram account.

Free: Meta Graph API (Pages API video_reels + Instagram Content Publishing,
resumable upload -- no public video URL needed).

Secrets (GitHub):
  META_TOKEN  -- System User token (never expires) with pages_show_list,
                 pages_read_engagement, pages_manage_posts, instagram_basic,
                 instagram_content_publish.
  FB_PAGE_ID  -- the Page's numeric id.

Called by main.py ONLY after the YouTube upload succeeded. Any error here is
reported (Telegram alert) but never changes the YouTube result.
"""
import os
import re
import time

import requests

from hindi_names import page_url

GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIMEOUT = 60
IG_POLL_SECONDS = 10
IG_POLL_MAX = 60  # 10 minutes: longer Reels (series C, ~45 s) can take over 5
IG_TRIES = 2  # a failed IG Reel is tried once more from a new container
IG_PUBLISH_TRIES = 3


class MetaError(RuntimeError):
    pass


_URL = re.compile(r"https?://[^\s?#]+\?[^\s#]*")


def _drop_utm(m):
    base, query = m.group(0).split("?", 1)
    keep = [p for p in query.split("&") if p and not p.startswith("utm_")]
    return base + ("?" + "&".join(keep) if keep else "")


def strip_utm(text):
    """Owner, 19 Oct 2026: no UTM tags in FB/IG post links for now."""
    return _URL.sub(_drop_utm, text)


def enabled():
    return bool(os.environ.get("META_TOKEN") and os.environ.get("FB_PAGE_ID"))


def _check(resp, what):
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:300]}
    if resp.status_code != 200 or (isinstance(body, dict) and "error" in body):
        err = body.get("error", body) if isinstance(body, dict) else body
        msg = err.get("message", err) if isinstance(err, dict) else err
        raise MetaError(f"{what} failed: HTTP {resp.status_code} -- {msg}")
    return body


def page_credentials(s=requests):
    """-> (page_token, ig_user_id or None)"""
    r = s.get(f"{GRAPH}/{os.environ['FB_PAGE_ID']}",
              params={"fields": "access_token,instagram_business_account",
                      "access_token": os.environ["META_TOKEN"]}, timeout=TIMEOUT)
    b = _check(r, "Page token lookup")
    if "access_token" not in b:
        raise MetaError("Page token lookup returned no access_token -- is the Page assigned to the system user?")
    ig = (b.get("instagram_business_account") or {}).get("id")
    return b["access_token"], ig


def _upload_bytes(s, url, token, path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        r = s.post(url, headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
                   data=fh, timeout=300)
    return _check(r, "Video upload")


def post_facebook_reel(video_path, caption, page_token, s=requests):
    page = os.environ["FB_PAGE_ID"]
    b = _check(s.post(f"{GRAPH}/{page}/video_reels",
                      params={"upload_phase": "start", "access_token": page_token}, timeout=TIMEOUT), "FB reel start")
    vid = b["video_id"]
    upload_url = b.get("upload_url") or f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}/{vid}"
    _upload_bytes(s, upload_url, page_token, video_path)
    _check(s.post(f"{GRAPH}/{page}/video_reels",
                  params={"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
                          "description": caption, "access_token": page_token}, timeout=TIMEOUT), "FB reel publish")
    return vid


def post_instagram_reel(video_path, caption, ig_user_id, token, s=requests, sleep=time.sleep):
    b = _check(s.post(f"{GRAPH}/{ig_user_id}/media",
                      params={"media_type": "REELS", "upload_type": "resumable", "caption": caption,
                              "share_to_feed": "true", "access_token": token}, timeout=TIMEOUT), "IG container")
    cid = b["id"]
    upload_url = b.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{cid}"
    _upload_bytes(s, upload_url, token, video_path)
    for _ in range(IG_POLL_MAX):
        b = _check(s.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": token},
                         timeout=TIMEOUT), "IG status")
        st = b.get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise MetaError(f"IG processing {st}: {b.get('status') or 'no reason given'}")
        sleep(IG_POLL_SECONDS)
    else:
        raise MetaError(f"IG processing did not finish in {IG_POLL_MAX * IG_POLL_SECONDS // 60} minutes")
    # Right after FINISHED, media_publish sometimes answers "media not ready";
    # a short wait fixes it.
    for i in range(IG_PUBLISH_TRIES):
        try:
            b = _check(s.post(f"{GRAPH}/{ig_user_id}/media_publish",
                              params={"creation_id": cid, "access_token": token}, timeout=TIMEOUT), "IG publish")
            return b.get("id")
        except MetaError:
            if i == IG_PUBLISH_TRIES - 1:
                raise
            sleep(20)


def build_caption(title, description, commodity, state):
    """Instagram/Facebook caption: search line, the fact line, CTA, hashtags.

    Plan P1-9 (7 Oct 2026): the first line is the exact Hindi search query
    ("प्याज का भाव आज 8 अक्टूबर 2026 | नीमच मंडी"), which the daily
    descriptions now carry as their own first line; older descriptions
    without it fall back to the title's hook as before."""
    lines = [l.strip() for l in description.split("\n")]
    if lines and " का भाव आज " in lines[0] and len(lines) > 1:
        hook, fact = lines[0], lines[1]
    else:
        hook, fact = title.split("|")[0].strip(), lines[0] if lines else ""
    tag_c = commodity.lower().replace(" ", "")
    tag_s = state.lower().replace(" ", "")
    link = page_url(commodity, state, source=None, hi=True).replace("https://", "")
    return (
        f"{hook}\n\n{fact}\n\n"
        f"🌐 हर मंडी का पूरा भाव: {link} (लिंक बायो में)\n"
        "🔔 रोज़ सुबह का ताज़ा भाव पाने के लिए फॉलो करें\n"
        "💬 आपकी मंडी में आज क्या भाव है? कमेंट करें\n\n"
        "स्रोत: Agmarknet (भारत सरकार) · थोक भाव\n\n"
        f"#mandibhav #{tag_c}price #{tag_c}ratetoday #{tag_s} #kisan #मंडीभाव #आजकाभाव #taazabhav"
    )[:2200]


def publish_all(video_path, caption, s=requests, sleep=time.sleep):
    """Posts to Facebook and Instagram independently. Returns
    {"facebook": id|None, "instagram": id|None, "errors": [str]}."""
    out = {"facebook": None, "instagram": None, "errors": []}
    caption = strip_utm(caption)
    page_token, ig = page_credentials(s)
    try:
        out["facebook"] = post_facebook_reel(video_path, caption, page_token, s)
    except Exception as e:
        out["errors"].append(f"Facebook: {e}")
    if ig:
        for i in range(IG_TRIES):
            try:
                out["instagram"] = post_instagram_reel(video_path, caption, ig, page_token, s, sleep)
                break
            except Exception as e:
                print(f"[meta] Instagram try {i + 1} failed: {e}")
                if i == IG_TRIES - 1:
                    out["errors"].append(f"Instagram: {e}")
    else:
        out["errors"].append("Instagram: no Instagram account linked to the Page")
    return out
