import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def upload_video(video_path, title, description, tags, thumbnail_path=None):
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

    return video_id