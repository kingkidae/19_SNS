"""Publish a video to Threads (graph.threads.net v1.0).

Threads only downloads from a public URL. We convert the video to spec and expose that one file through a
temporary Cloudflare quick tunnel (public_file.serve_public) until Threads has finished processing.
(Reusing the Instagram reel's CDN URL was tried: Threads fails it with ERROR UNKNOWN.)
Flow: POST /{user}/threads media_type=VIDEO -> wait ~30s, poll status until FINISHED -> POST /{user}/threads_publish.
Needs THREADS_ACCESS_TOKEN (long-lived, scopes threads_basic + threads_content_publish) and cloudflared.
"""
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from public_file import serve_public
from upload_instagram import to_reels_spec, wait_until_finished

API = "https://graph.threads.net"
REFRESH_AFTER = 50 * 86400  # long-lived tokens die after 60 days unless refreshed
MAX_TEXT = 500


def _call(method: str, path: str, token: str, params: dict | None = None) -> dict:
    q = urllib.parse.urlencode({**(params or {}), "access_token": token})
    url, data = (f"{API}{path}?{q}", None) if method == "GET" else (f"{API}{path}", q.encode())
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method), timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:  # message only: the URL can hold the token
        body = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body).get("error") or {}
        except (ValueError, AttributeError):
            err = {}
        raise RuntimeError(f"Threads API {e.code}: {err.get('message') or body[:300]}") from None


def _save(path: str, data: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.chmod(path, 0o600)


def current_token(env_token: str, token_path: str, now: float, refresh, log=print) -> str:
    """Token from the cache file (if it came from the same .env token), refreshed when it's 50+ days old."""
    state = {"source": env_token, "token": env_token, "refreshed_at": None}
    if os.path.exists(token_path):
        with open(token_path, encoding="utf-8") as f:
            saved = json.load(f)
        if saved.get("source") == env_token:  # a new token pasted into .env wins over the cache
            state = saved
    if state["refreshed_at"] is None or now - state["refreshed_at"] > REFRESH_AFTER:
        try:
            state = {**state, "token": refresh(state["token"]), "refreshed_at": now}
            _save(token_path, state)
            log("refreshed Threads token")
        except RuntimeError as e:  # e.g. token younger than 24h: still usable as is
            log(f"token refresh skipped: {e}")
    return state["token"]


def upload_threads(env: dict, video: str, text: str, token_path: str, log=print, sleep=time.sleep) -> dict:
    if not env.get("THREADS_ACCESS_TOKEN"):
        raise RuntimeError(".env is missing THREADS_ACCESS_TOKEN")
    token = current_token(
        env["THREADS_ACCESS_TOKEN"], token_path, time.time(),
        lambda t: _call("GET", "/refresh_access_token", t, {"grant_type": "th_refresh_token"})["access_token"], log)
    user = _call("GET", "/v1.0/me", token, {"fields": "id"})["id"]

    fd, spec = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        log("converting to Threads spec")
        to_reels_spec(video, spec)  # same spec as Reels: H.264 yuv420p, AAC-LC 128k/48k, moov first
        with serve_public(spec, log=log) as url:  # tunnel stays open until Threads has the file
            cid = _call("POST", f"/v1.0/{user}/threads", token,
                        {"media_type": "VIDEO", "video_url": url, "text": text[:MAX_TEXT]})["id"]
            log(f"container {cid}, waiting for Threads processing")
            sleep(30)  # Meta: give Threads ~30s before checking/publishing
            wait_until_finished(lambda: _status(cid, token), sleep=sleep, interval=15, timeout=300, log=log)
    finally:
        os.remove(spec)

    media_id = _call("POST", f"/v1.0/{user}/threads_publish", token, {"creation_id": cid})["id"]
    link = _call("GET", f"/v1.0/{media_id}", token, {"fields": "permalink"}).get("permalink")
    return {"id": media_id, "url": link}


def _status(cid: str, token: str) -> dict:
    r = _call("GET", f"/v1.0/{cid}", token, {"fields": "status,error_message"})
    return {"status_code": r.get("status"), "status": r.get("error_message", "")}
