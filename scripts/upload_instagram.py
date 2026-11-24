"""Publish a local video as an Instagram Reel via the Instagram API with Facebook Login.

Flow (Meta docs, content-publishing/resumable-uploads):
  1. POST graph.facebook.com/{v}/{ig-user-id}/media  media_type=REELS, upload_type=resumable  -> container id + rupload uri
  2. POST rupload uri with the raw file bytes (headers: offset, file_size)
  3. GET  {container}?fields=status_code until FINISHED
  4. POST {ig-user-id}/media_publish creation_id={container}
The video is re-encoded to the Reels spec first (temp file, deleted afterwards).
Needs IG_ACCESS_TOKEN (scopes: instagram_basic, instagram_content_publish, pages_show_list,
pages_read_engagement); IG_USER_ID is optional and looked up from the token's Pages when absent.
"""
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import imageio_ffmpeg

GRAPH = "https://graph.facebook.com"
MAX_BYTES = 300 * 1024 * 1024  # Reels limit


def to_reels_spec(src: str, dst: str) -> None:
    """Re-encode to the Reels spec. Remotion's default output (yuvj420p, ~320k audio) fails with
    rupload ProcessingFailedError; limited-range yuv420p, AAC 128k/48kHz and moov-first pass.
    Video with no audio track (e.g. silent scenario videos) also fails, so a silent track is added."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run([ff, "-hide_banner", "-i", src], capture_output=True, text=True,
                           encoding="utf-8", errors="replace").stderr
    audio = ["-map", "0:v:0", "-map", "0:a:0"] if "Audio:" in probe else \
        ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v:0", "-map", "1:a:0", "-shortest"]
    cmd = [ff, "-v", "error", "-y", "-i", src, *audio,
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
           "-g", "60", "-b:v", "8M", "-maxrate", "10M", "-bufsize", "16M",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", dst]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to convert video for Reels: {r.stderr.strip()[-500:]}")


def _call(method: str, url: str, token: str, params: dict | None = None,
          data: bytes | None = None, headers: dict | None = None) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    # Token goes in the header, never the URL, so it can't leak into error messages or logs.
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"OAuth {token}", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body).get("error") or {}
        except (ValueError, AttributeError):
            err = {}
        # rupload.facebook.com errors don't use Graph's {"error": {...}} shape; show them raw.
        msg = (f"{err['message']} (code {err.get('code')}, subcode {err.get('error_subcode')})"
               if err.get("message") else body[:500])
        raise RuntimeError(f"Instagram API {e.code}: {msg}") from None


def wait_until_finished(fetch_status, sleep=time.sleep, interval=10, timeout=600, log=print) -> None:
    """Poll the container until Instagram finishes processing. fetch_status() -> dict with status_code/status."""
    waited = 0
    while True:
        s = fetch_status()
        code = s.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"processing failed: {code} {s.get('status', '')}")
        if waited >= timeout:
            raise TimeoutError(f"processing still {code} after {timeout}s")
        log(f"processing: {code}")
        sleep(interval)
        waited += interval


def find_ig_user_id(token: str, v: str) -> str:
    """Instagram business account linked to the token's Facebook Page (user token or page token)."""
    pages = _call("GET", f"{GRAPH}/{v}/me/accounts", token, {"fields": "name,instagram_business_account"})
    for page in pages.get("data", []):
        if page.get("instagram_business_account"):
            return page["instagram_business_account"]["id"]
    me = _call("GET", f"{GRAPH}/{v}/me", token, {"fields": "instagram_business_account"})
    if me.get("instagram_business_account"):
        return me["instagram_business_account"]["id"]
    raise RuntimeError("No Instagram business account is linked to a Facebook Page this token can access")


def upload_instagram(env: dict, video: str, caption: str, log=print) -> dict:
    token = env.get("IG_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(".env is missing IG_ACCESS_TOKEN")
    if token.startswith("IG"):
        # Instagram Login tokens (IGAA...) only work on graph.instagram.com, which has no local-file upload.
        raise RuntimeError("IG_ACCESS_TOKEN is an Instagram Login token; local-file Reels upload needs a "
                           "Facebook Login (EAA...) token with instagram_content_publish")
    v = env.get("IG_API_VERSION", "v27.0")
    ig = env.get("IG_USER_ID") or env.get("IG_ID")
    if not ig:
        ig = find_ig_user_id(token, v)
        log(f"found Instagram account id {ig} (add IG_USER_ID={ig} to .env to skip this lookup)")
    if len(caption) > 2200:
        raise RuntimeError("Instagram caption max 2200 characters")

    fd, reels = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        log("converting to Reels spec")
        to_reels_spec(video, reels)
        return _publish(reels, caption, ig, token, v, log)
    finally:
        os.remove(reels)


def _publish(video: str, caption: str, ig: str, token: str, v: str, log) -> dict:
    size = os.path.getsize(video)
    if size > MAX_BYTES:
        raise RuntimeError(f"Reels max 300MB, file is {size / 1024 / 1024:.0f}MB")

    container = _call("POST", f"{GRAPH}/{v}/{ig}/media", token,
                      {"media_type": "REELS", "upload_type": "resumable", "caption": caption})
    cid = container["id"]
    log(f"container {cid}, uploading {size / 1024 / 1024:.1f}MB")

    # shortcut: whole file in memory (Reels cap 300MB); stream from disk if that ever matters.
    with open(video, "rb") as f:
        data = f.read()
    _call("POST", container["uri"], token, data=data,
          headers={"offset": "0", "file_size": str(size), "Content-Type": "application/octet-stream"})
    log("uploaded 100%, waiting for Instagram processing")

    wait_until_finished(lambda: _call("GET", f"{GRAPH}/{v}/{cid}", token, {"fields": "status_code,status"}), log=log)

    media_id = _call("POST", f"{GRAPH}/{v}/{ig}/media_publish", token, {"creation_id": cid})["id"]
    link = _call("GET", f"{GRAPH}/{v}/{media_id}", token, {"fields": "permalink"}).get("permalink")
    return {"id": media_id, "url": link}
