import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


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
            "containsSyntheticMedia": True,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Video live: https://youtu.be/{video_id}")

    if thumbnail_path:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
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
    channel_id = youtube.channels().list(part="id", mine=True).execute()["items"][0]["id"]
    youtube.commentThreads().insert(
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
    ).execute()
