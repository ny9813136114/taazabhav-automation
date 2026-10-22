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


_URL = re.compile(r"(?:https?://|\b(?:www\.)?taazabhav\.com)[^\s?#]*\?[^\s#]*")


def _drop_utm(m):
    base, query = m.group(0).split("?", 1)
    keep = [p for p in query.split("&") if p and not p.startswith("utm_")]
    return base + ("?" + "&".join(keep) if keep else "")


def strip_utm(text):
    """Owner, 19 Oct 2026: no UTM tags in FB/IG post links for now."""
    return _URL.sub(_drop_utm, text)


# ---------- Link in the first comment (plan section 2 + 6) ----------
# Facebook shows posts with a link in the caption to fewer people; a link in
# the Page's own first comment is not held back. Instagram captions can't
# carry a clickable link anyway, so the Instagram caption stays as it is
# ("link bio mein"). Live only when the repo variable COMMENTS_LIVE is "1";
# until then the would-be Facebook caption and comment go to the owner's
# Telegram as a preview and posts go out as before.

_LINK = re.compile(r"(?:https?://|\b)(?:www\.)?(?:taazabhav\.com|t\.me|youtu\.be|youtube\.com)(?:/[^\s)।,]*)?|https?://[^\s)]+")
_BIO = re.compile(r"\s*\((?:लिंक बायो में|link in bio)\)", re.I)
_TAIL = re.compile(r"(?:^|(?<=[।.!?]))[^।.!?\n]{0,45}[:：]\s*$")
_EMPTY = re.compile(r"^[\W\s·|_-]*$")
COMMENT_MARK = "🔗 लिंक पहले कमेंट में 👇"
COMMENT_TRIES = 4
COMMENT_WAIT = 20


def comments_live():
    return os.environ.get("COMMENTS_LIVE", "").strip() == "1"


def links_in(text):
    out = []
    for m in _LINK.finditer(text):
        u = m.group(0).rstrip(".,।")
        u = u if u.startswith("http") else "https://" + u
        if u not in out:
            out.append(u)
    return out


def fb_caption(caption):
    """The caption with every link (and "(लिंक बायो में)") taken out, and one
    "link pehle comment mein" line before the hashtags. A line that was only
    a label for its link ("🌐 पूरी जानकारी: <link>") goes away."""
    lines, had = [], False
    for line in caption.split("\n"):
        if not _LINK.search(line):
            lines.append(line)
            continue
        had = True
        rest = _BIO.sub("", _LINK.sub("", line)).rstrip()
        rest = re.sub(r"[\s·|]*Telegram[\s:]*$", "", rest).rstrip()
        rest = _TAIL.sub("", rest).rstrip(" ·|-")
        if not _EMPTY.match(rest):
            lines.append(rest)
    if had:
        at = next((i for i, l in enumerate(lines) if l.lstrip().startswith("#")), len(lines))
        while at > 0 and not lines[at - 1].strip():
            at -= 1
        lines[at:at] = ["", COMMENT_MARK, ""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def default_comment(caption, label="पूरी जानकारी, मुफ़्त"):
    """First comment when the caller gives none: the first taazabhav.com
    link in the caption, with one line saying what it opens."""
    site = [u for u in links_in(caption) if "taazabhav.com" in u] or links_in(caption)
    return f"👉 {label}: {site[0]}" if site else None


def post_comment(object_id, message, token, s=requests, sleep=time.sleep):
    """Page's own comment on its FB post/Reel, or on an IG media. A Reel
    still processing can refuse comments for a short while: try again."""
    for i in range(COMMENT_TRIES):
        try:
            b = _check(s.post(f"{GRAPH}/{object_id}/comments", data={"message": message, "access_token": token},
                              timeout=TIMEOUT), "Comment")
            return b.get("id")
        except MetaError:
            if i == COMMENT_TRIES - 1:
                raise
            sleep(COMMENT_WAIT)


def restore_caption(object_id, caption, token, reel, s=requests):
    """The link comment failed: put the full caption (with its link) back,
    so the post never goes without a way to the site."""
    field = "description" if reel else "message"
    _check(s.post(f"{GRAPH}/{object_id}", data={field: caption, "access_token": token}, timeout=TIMEOUT),
           "Caption restore")


def link_comment(fb_id, caption, comment, token, reel, s=requests, sleep=time.sleep):
    """-> (comment id or None, error text or None)."""
    try:
        return post_comment(fb_id, comment, token, s, sleep), None
    except Exception as e:
        try:
            restore_caption(fb_id, caption, token, reel, s)
            return None, f"Facebook link comment failed, full caption put back: {e}"
        except Exception as e2:
            return None, f"Facebook link comment failed ({e}) and caption restore failed too: {e2}"


def preview_comment(what, caption, comment):
    """COMMENTS_LIVE off: show the owner what the Facebook side would be."""
    if not comment:
        return
    try:
        from notify import send_telegram_alert as send_telegram_message
        send_telegram_message(f"PREVIEW, link-in-comment ({what}). Abhi post pehle jaisa gaya.\n\n"
                              f"FB caption hoga:\n{fb_caption(caption)[:1500]}\n\nPage ka pehla comment:\n{comment}")
    except Exception as e:
        print(f"[meta] comment preview failed: {e}")


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


def publish_all(video_path, caption, s=requests, sleep=time.sleep, comment=None, what="Reel"):
    """Posts to Facebook and Instagram independently. Returns
    {"facebook": id|None, "instagram": id|None, "errors": [str]}.

    comment: the Page's first comment on the Facebook Reel (its link). With
    COMMENTS_LIVE=1 the link leaves the Facebook caption and goes there."""
    out = {"facebook": None, "instagram": None, "errors": []}
    caption = strip_utm(caption)
    comment = strip_utm(comment) if comment else default_comment(caption)
    live = comment and comments_live()
    page_token, ig = page_credentials(s)
    try:
        out["facebook"] = post_facebook_reel(video_path, fb_caption(caption) if live else caption, page_token, s)
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
    # Commented last: by now the Reel has had minutes to process.
    if live and out["facebook"]:
        out["comment"], err = link_comment(out["facebook"], caption, comment, page_token, True, s, sleep)
        if err:
            out["errors"].append(err)
    elif comment and out["facebook"]:
        preview_comment(what, caption, comment)
    return out
