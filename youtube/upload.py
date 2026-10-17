"""YouTube Data API v3 upload using a stored refresh token (no browser needed)."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
QUOTA_REASONS = {"quotaExceeded", "uploadLimitExceeded", "dailyLimitExceeded", "rateLimitExceeded"}


class QuotaError(Exception):
    pass


def configured():
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        # scopes verilmez: token hangi kapsamla alındıysa onu kullanır (youtube + force-ssl, 2026-10-17)
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


class WrongChannelError(Exception):
    pass


def current_channel():
    items = _client().channels().list(part="id,snippet", mine=True).execute().get("items", [])
    if not items:
        raise WrongChannelError("token has no YouTube channel")
    return items[0]["id"], items[0]["snippet"]["title"]


def check_channel():
    """Refuses to upload unless the token belongs to YT_CHANNEL_ID.

    The Gmail also owns another (viral) channel; a token made for the wrong
    channel must never upload there.
    """
    expected = (os.environ.get("YT_CHANNEL_ID") or "").strip()
    cid, title = current_channel()
    if not expected:
        raise WrongChannelError(f"YT_CHANNEL_ID secret is not set (token is for '{title}' {cid})")
    if cid != expected:
        raise WrongChannelError(f"token is for '{title}' ({cid}), expected {expected}")
    return title


def locked_videos(video_ids):
    """Public uploads that YouTube has since made private or rejected.

    Unaudited API projects can have their uploads forced to private; this is how
    we notice without anyone checking Studio.
    """
    if not video_ids:
        return []
    items = _client().videos().list(part="status", id=",".join(video_ids[:50])).execute().get("items", [])
    found = {i["id"]: i["status"] for i in items}
    bad = []
    for vid in video_ids:
        s = found.get(vid)
        if s is None:
            bad.append((vid, "removed"))
        elif s.get("uploadStatus") in ("rejected", "failed"):
            bad.append((vid, f"{s['uploadStatus']}: {s.get('rejectionReason') or s.get('failureReason')}"))
        elif s.get("privacyStatus") != "public":
            bad.append((vid, s.get("privacyStatus")))
    return bad


def add_to_playlist(playlist_id, video_id):
    _client().playlistItems().insert(part="snippet", body={
        "snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}},
    }).execute()


def clean(s):
    """YouTube rejects the upload (invalidTitle / invalidDescription) if these contain < or >."""
    return s.replace("->", "→").replace("<", "").replace(">", "")


def upload(path, title, description, tags, privacy):
    body = {
        "snippet": {
            "title": clean(title)[:100],
            "description": clean(description)[:4900],
            "tags": [clean(t) for t in tags],
            "categoryId": "27",  # Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=-1, resumable=True)
    try:
        req = _client().videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk(num_retries=3)
        return resp["id"]
    except HttpError as e:
        reasons = {d.get("reason") for d in (e.error_details or []) if isinstance(d, dict)}
        if reasons & QUOTA_REASONS or "quota" in str(e).lower():
            raise QuotaError(str(e)) from e
        raise
