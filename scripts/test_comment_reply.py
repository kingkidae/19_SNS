"""python scripts/test_comment_reply.py — offline checks for the Instagram comment auto-reply."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from comment_reply import CommentWatcher, match  # noqa: E402

# Matching: exact keyword, tolerant of spaces and trailing punctuation/laughs only.
assert match("안녕") == ("DM 확인 부탁드립니다.", "안녕하세요")
for t in (" 안녕 ", "안녕!!", "안녕~", "안녕ㅎㅎ", "안녕?"):
    assert match(t), t
for t in ("안녕하세요", "다들 안녕", "", None, "ㅎㅇ"):
    assert match(t) is None, t

T0 = 1_800_000_000  # "now" for the watcher
iso = lambda ts: __import__("datetime").datetime.fromtimestamp(ts, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")  # noqa: E731

COMMENTS = [
    {"id": "c_old", "text": "안녕", "timestamp": iso(T0 - 60), "username": "past", "from": {"id": "u1"}},
    {"id": "c_new", "text": "안녕!", "timestamp": iso(T0 + 10), "username": "fan", "from": {"id": "u2"}},
    {"id": "c_other", "text": "멋져요", "timestamp": iso(T0 + 20), "username": "x", "from": {"id": "u3"}},
    {"id": "c_self", "text": "안녕", "timestamp": iso(T0 + 30), "username": "me", "from": {"id": "IG"}},
]
calls = []


def fake_call(method, url, token, params=None, data=None, headers=None):
    calls.append((method, url.split("/v27.0/")[1], token, params, json.loads(data) if data else None))
    if url.endswith("/me/accounts"):
        return {"data": [{"access_token": "PAGE", "instagram_business_account": {"id": "IG"}}]}
    if url.endswith("/IG/media"):
        return {"data": [{"id": "m1", "permalink": "https://ig/p/1"}]}
    if url.endswith("/m1/comments"):
        return {"data": COMMENTS}
    return {"id": "ok"}


with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "s.json")
    env = {"IG_ACCESS_TOKEN": "USER", "IG_USER_ID": "IG"}
    w = CommentWatcher(env, state, call=fake_call, now=lambda: T0, log=lambda *_: None)
    done = w.poll_once()
    # Only the new matching comment from someone else is handled.
    assert [r["comment_id"] for r in done] == ["c_new"], done
    assert done[0]["reply"] == "ok" and done[0]["dm"] == "ok" and done[0]["username"] == "fan"
    posts = [c for c in calls if c[0] == "POST"]
    assert posts[0][:4] == ("POST", "c_new/replies", "USER", {"message": "DM 확인 부탁드립니다."})
    assert posts[1][1:3] == ("IG/messages", "PAGE")  # DM with the linked Page token
    assert posts[1][4] == {"recipient": {"comment_id": "c_new"}, "message": {"text": "안녕하세요"}}

    # Second poll (and a restarted watcher reading the saved state) does nothing again.
    calls.clear()
    assert w.poll_once() == []
    assert CommentWatcher(env, state, call=fake_call, now=lambda: T0 + 999, log=lambda *_: None).poll_once() == []
    assert not [c for c in calls if c[0] == "POST"]

    # A failing DM is reported, and the comment is still marked handled (no duplicate public reply).
    COMMENTS.append({"id": "c_fail", "text": "안녕", "timestamp": iso(T0 + 40), "username": "y", "from": {"id": "u4"}})

    def failing(method, url, *a, **k):
        if url.endswith("/messages"):
            raise RuntimeError("Instagram API 400: outside window")
        return fake_call(method, url, *a, **k)

    w2 = CommentWatcher(env, state, call=failing, now=lambda: T0, log=lambda *_: None)
    r = w2.poll_once()
    assert r[0]["reply"] == "ok" and "outside window" in r[0]["dm"]
    assert w2.poll_once() == []
print("ok")
