"""Upload a video to the authorized user's YouTube channel (OAuth: GOOGLE_ID / GOOGLE_SECRET)."""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _credentials(env: dict, token_path: str) -> Credentials:
    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except ValueError:  # saved without refresh_token (or corrupt): log in again
            creds = None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(
            {"installed": {
                "client_id": env["GOOGLE_ID"],
                "client_secret": env["GOOGLE_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }},
            SCOPES,
        )
        # Fixed port: a "Web application" OAuth client only accepts redirect URIs registered in Cloud Console.
        # prompt=consent: Google only returns a refresh_token on consent; without it the saved token can't be reused.
        creds = flow.run_local_server(port=8765, open_browser=True, timeout_seconds=300,
                                      access_type="offline", prompt="consent")
        # Refresh token = channel access; keep it owner-only (mode is a no-op on Windows, enforced on macOS/Linux).
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        os.chmod(token_path, 0o600)
    return creds


def upload_youtube(env: dict, video: str, title: str, description: str, tags: list[str],
                   privacy: str, token_path: str, log=print) -> dict:
    yt = build("youtube", "v3", credentials=_credentials(env, token_path))
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "10",  # Music
            "defaultLanguage": "ko",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True),
    )
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            log(f"uploaded {int(status.progress() * 100)}%")
    return {"id": resp["id"], "url": f"https://youtu.be/{resp['id']}", "privacy": resp["status"]["privacyStatus"]}
