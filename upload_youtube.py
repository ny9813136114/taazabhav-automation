import pickle
import socket
import time

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube sometimes answers a good request with a passing server error, e.g.
# 20 Oct 2026: playlistItems.insert -> 409 "The operation was aborted",
# reason SERVICE_UNAVAILABLE. These codes are retried; anything else (bad
# login, quota, bad request) fails at once.
RETRY_STATUS = {409, 429, 500, 502, 503, 504}
RETRY_WAITS = (5, 20, 60)


def _retryable(e):
    status = getattr(getattr(e, "resp", None), "status", None)
    if status is not None:
        return int(status) in RETRY_STATUS
    return isinstance(e, (socket.timeout, ConnectionError, TimeoutError))


def execute(request, waits=None, sleep=time.sleep):
    """request.execute(), retried on YouTube's passing errors."""
    for i, wait in enumerate((*(RETRY_WAITS if waits is None else waits), None)):
        try:
            return request.execute()
        except Exception as e:
            if wait is None or not _retryable(e):
                raise
            print(f"YouTube {type(e).__name__} ({getattr(getattr(e, 'resp', None), 'status', '')}), retry {i + 1} in {wait}s")
            sleep(wait)


def upload_video(video_path, title, description, tags, thumbnail_path=None, comment_text=None):
    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "25",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            # Generic TTS voice over graphics and real stock clips: no realistic
            # fake person or event, so the "altered or synthetic" label is not
            # required. Owner chose to drop it on 18 Oct 2026.
            "containsSyntheticMedia": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk(num_retries=5)
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Video live: https://youtu.be/{video_id}")

    if thumbnail_path:
        try:
            execute(youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ))
            print("Thumbnail set successfully.")
        except Exception as e:
            print(f"Thumbnail upload failed (video still published): {e}")

    if comment_text:
        try:
            post_comment(youtube, video_id, comment_text)
            print("Comment posted successfully. (YouTube's API has no pin endpoint -- "
                  "pin it manually in Studio if you want it pinned.)")
        except Exception as e:
            print(f"Comment post failed (video still published): {e}")

    return video_id


def post_comment(youtube, video_id, comment_text):
    """Posts comment_text as a new top-level comment on video_id, as the
    authenticated channel. NOTE: the YouTube Data API v3 has no "pin comment"
    endpoint at all -- Comments/CommentThreads only support list/insert/
    update/delete/setModerationStatus. This posts the comment; pinning it
    still needs one manual tap in YouTube Studio per video.

    Requires the token.pickle credentials to carry a scope that covers
    comment writes (the broad "https://www.googleapis.com/auth/youtube"
    scope, or the narrower ".../auth/youtube.force-ssl"). A token minted
    with only the upload scope will fail here with an insufficient-
    permissions error -- if that happens, add the scope to whatever script
    originally generated token.pickle and re-run that script's OAuth consent
    flow once to mint a new token.pickle.
    """
    channel_id = execute(youtube.channels().list(part="id", mine=True))["items"][0]["id"]
    execute(youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "channelId": channel_id,
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {"textOriginal": comment_text}
                },
            }
        },
    ))
