"""Instagram comment auto-reply: when a new top-level comment matches a keyword, reply publicly and send
the commenter a private reply (DM).

Polling instead of webhooks: webhooks need a stable public HTTPS endpoint, which this PC setup doesn't have.
Endpoints (Instagram API with Facebook Login, graph.facebook.com):
  GET  /{ig-user-id}/media                 recent posts
  GET  /{media-id}/comments                top-level comments (id, text, timestamp, username, from)
  POST /{comment-id}/replies  message=…    public reply
  POST /{ig-user-id}/messages {"recipient":{"comment_id":…},"message":{"text":…}}  private reply:
       allowed within 7 days of the comment, one per comment.
Token needs: instagram_basic, instagram_manage_comments, instagram_manage_messages, pages_show_list,
pages_read_engagement, with the IG account's Facebook Page selected when the token is generated.
"""
import datetime as dt
import json
import os
import re
import time

from upload_instagram import GRAPH, _call

# keyword -> (public reply, DM). Matching ignores surrounding spaces and trailing punctuation/laughs ("안녕!!", "안녕ㅎㅎ").
RULES = {"안녕": ("DM 확인 부탁드립니다.", "안녕하세요")}
POLL_SECONDS = 120  # ~6 media/comment reads per poll; keeps well under Graph API rate limits
MEDIA_TO_WATCH = 5
KEEP_HANDLED = 5000


def match(text: str) -> tuple[str, str] | None:
    core = re.sub(r"[\s!~.?,ㅎㅋㅠㅜ^♡♥❤️😊😀🙂👋]+$", "", (text or "").strip())
    return RULES.get(core)


def _ts(s: str) -> float:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z").timestamp()


class CommentWatcher:
    def __init__(self, env: dict, state_path: str, notify=print, log=print, call=_call, now=time.time):
        self.token = env["IG_ACCESS_TOKEN"]
        self.ig = env["IG_USER_ID"]
        self.v = env.get("IG_API_VERSION", "v27.0")
        self.path, self.notify, self.log, self.call, self.now = state_path, notify, log, call, now
        self.state = self._load()
        self._page_token = None
        self._last_error = None

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        # First run: only react to comments written from now on, not the whole history.
        return {"since": self.now(), "handled": []}

    def _save(self):
        self.state["handled"] = self.state["handled"][-KEEP_HANDLED:]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f)

    def _messages_token(self) -> str:
        """Facebook Login sends DMs with the Page token of the Page linked to the IG account; fall back to ours."""
        if self._page_token is None:
            self._page_token = self.token
            try:
                pages = self.call("GET", f"{GRAPH}/{self.v}/me/accounts", self.token,
                                  {"fields": "access_token,instagram_business_account"}).get("data", [])
                for p in pages:
                    if (p.get("instagram_business_account") or {}).get("id") == self.ig and p.get("access_token"):
                        self._page_token = p["access_token"]
            except RuntimeError as e:
                self.log(f"page token lookup failed, using IG token: {e}")
        return self._page_token

    def poll_once(self) -> list[dict]:
        """Handle new matching comments once. Returns what was done (for notifications/tests)."""
        done = []
        media = self.call("GET", f"{GRAPH}/{self.v}/{self.ig}/media", self.token,
                          {"fields": "id,permalink", "limit": MEDIA_TO_WATCH}).get("data", [])
        handled = set(self.state["handled"])
        for m in media:
            comments = self.call("GET", f"{GRAPH}/{self.v}/{m['id']}/comments", self.token,
                                 {"fields": "id,text,timestamp,username,from", "limit": 50}).get("data", [])
            for c in comments:
                if c["id"] in handled or _ts(c["timestamp"]) < self.state["since"]:
                    continue
                handled.add(c["id"])
                self.state["handled"].append(c["id"])
                if (c.get("from") or {}).get("id") == self.ig:  # our own comment
                    continue
                rule = match(c.get("text", ""))
                if not rule:
                    continue
                reply, dm = rule
                result = {"comment_id": c["id"], "username": c.get("username") or (c.get("from") or {}).get("username"),
                          "text": c.get("text"), "post": m.get("permalink"), "reply": None, "dm": None}
                try:
                    self.call("POST", f"{GRAPH}/{self.v}/{c['id']}/replies", self.token, {"message": reply})
                    result["reply"] = "ok"
                except RuntimeError as e:
                    result["reply"] = str(e)
                try:
                    body = json.dumps({"recipient": {"comment_id": c["id"]}, "message": {"text": dm}}).encode()
                    self.call("POST", f"{GRAPH}/{self.v}/{self.ig}/messages", self._messages_token(), data=body,
                              headers={"Content-Type": "application/json"})
                    result["dm"] = "ok"
                except RuntimeError as e:
                    result["dm"] = str(e)
                # Mark handled even on failure: a retry would post the public reply twice.
                self._save()
                done.append(result)
        self._save()
        return done

    def run(self):
        self.log("comment watcher running")
        while True:
            try:
                for r in self.poll_once():
                    ok = r["reply"] == "ok" and r["dm"] == "ok"
                    self.notify(f"{'💬' if ok else '⚠️'} @{r['username']} 댓글 \"{r['text']}\"\n"
                                f"대댓글: {'완료' if r['reply'] == 'ok' else r['reply']}\n"
                                f"DM: {'완료' if r['dm'] == 'ok' else r['dm']}")
                self._last_error = None
            except Exception as e:  # keep watching; report each distinct error once
                if str(e) != self._last_error:
                    self._last_error = str(e)
                    self.notify(f"⚠️ 댓글 확인 실패: {e}")
            time.sleep(POLL_SECONDS)
