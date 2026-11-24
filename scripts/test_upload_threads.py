"""python scripts/test_upload_threads.py — offline checks: token refresh/cache, Threads chained after Instagram."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import publish  # noqa: E402
from upload_threads import REFRESH_AFTER, current_token  # noqa: E402

quiet = lambda *_: None  # noqa: E731
DAY = 86400

with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "t.json")
    calls = []

    def refresh(t):
        calls.append(t)
        return t + "+r"

    # First run: refresh and cache.
    assert current_token("A", path, 100 * DAY, refresh, quiet) == "A+r"
    # Within 50 days: use cache, no refresh.
    assert current_token("A", path, 120 * DAY, refresh, quiet) == "A+r" and len(calls) == 1
    # After 50 days: refresh the cached token.
    assert current_token("A", path, 100 * DAY + REFRESH_AFTER + 1, refresh, quiet) == "A+r+r"
    # New token pasted into .env replaces the cache.
    assert current_token("B", path, 200 * DAY, refresh, quiet) == "B+r"
    assert json.load(open(path))["source"] == "B"

    # Refresh failing (token < 24h old) still returns a usable token.
    def boom(_):
        raise RuntimeError("too new")
    assert current_token("C", os.path.join(d, "u.json"), 0, boom, quiet) == "C"

# Threads runs as its own job on the local file; one platform failing doesn't affect the others.
seen = {}
publish.upload_youtube = lambda *a, **k: {"url": "yt"}
publish.upload_threads = lambda env, video, text, *a, **k: seen.setdefault("video", video) and {"url": "th"}


def ig_fail(*a, **k):
    raise RuntimeError("ig down")


publish.upload_instagram = ig_fail
env = {"THREADS_ACCESS_TOKEN": "x"}
r = publish.publish_all(env, "v.mp4", "title", log=quiet)
assert r["threads"] == (True, {"url": "th"}) and seen["video"] == "v.mp4", r
assert r["instagram"][0] is False and r["youtube"][0] is True, r
assert set(publish.publish_all(env, "v.mp4", "t", only="threads", log=quiet)) == {"threads"}

# No Threads token: Threads isn't attempted at all.
assert "threads" not in publish.publish_all({}, "v.mp4", "title", log=quiet)

# The local server exposes only the one file, only at its random path.
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from public_file import local_server  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    f = os.path.join(d, "v.mp4")
    open(f, "wb").write(b"video-bytes")
    with local_server(f) as (port, name):
        assert urllib.request.urlopen(f"http://127.0.0.1:{port}{name}").read() == b"video-bytes"
        for bad in ("/", "/v.mp4", "/../v.mp4", name + "x"):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{bad}")
                raise AssertionError(f"{bad} should be 404")
            except urllib.error.HTTPError as e:
                assert e.code == 404
print("ok")
