"""Telegram bot: topic suggestions (daily 08:50 or /topic) -> scenario -> Remotion render -> approval -> upload.

  python scripts/bot.py

.env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (only this chat may control the bot), ANTHROPIC_API_KEY,
plus the YouTube/Instagram keys used by publish.py.
Commands: /topic [방향], /upload, /help
"""
import datetime as dt
import glob
import json
import os
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import content  # noqa: E402
from comment_reply import CommentWatcher  # noqa: E402
from publish import ROOT, load_env, publish_all  # noqa: E402

DAILY_AT = (8, 50)  # PC local time
HELP = ("/topic — 오늘의 주제 추천 (예: /topic 직장인 공감)\n"
        "/upload — out 폴더의 영상을 골라 유튜브·인스타·스레드에 업로드\n"
        "매일 08:50에 주제를 자동으로 보내드립니다.")


def is_due(now: dt.datetime, last_sent: dt.date | None, at=DAILY_AT) -> bool:
    return now.time() >= dt.time(*at) and last_sent != now.date()


class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}/"

    def call(self, method: str, http_timeout: int = 30, **params):
        req = urllib.request.Request(self.base + method, data=json.dumps(params).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=http_timeout) as r:
                return json.loads(r.read())["result"]
        except urllib.error.HTTPError as e:  # message only: the URL holds the bot token
            raise RuntimeError(f"Telegram {method} {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None

    def send_video(self, chat_id: int, path: str, caption: str, markup: dict):
        boundary = uuid.uuid4().hex
        fields = {"chat_id": str(chat_id), "caption": caption[:1024], "supports_streaming": "true",
                  "reply_markup": json.dumps(markup)}
        body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                        for k, v in fields.items())
        with open(path, "rb") as f:
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="preview.mp4"\r\n'
                     f"Content-Type: video/mp4\r\n\r\n").encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(self.base + "sendVideo", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())["result"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Telegram sendVideo {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None


def buttons(rows: list[list[tuple[str, str]]]) -> dict:
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}


class Bot:
    def __init__(self, env: dict):
        self.env = env
        self.tg = Telegram(env["TELEGRAM_BOT_TOKEN"])
        self.chat_id = int(env["TELEGRAM_CHAT_ID"]) if env.get("TELEGRAM_CHAT_ID") else None
        self.work = ThreadPoolExecutor(max_workers=1)  # Claude/render/upload one at a time
        self.topics: dict[str, list[dict]] = {}  # batch id -> topics
        self.files: dict[str, list[str]] = {}  # batch id -> videos offered by /upload
        self.pending: dict[str, str] = {}  # approval id -> video path (/upload)
        self.scenarios: dict[str, dict] = {}  # approval id -> scenario awaiting approval
        self.lock = threading.Lock()

    def say(self, text: str, markup: dict | None = None):
        params = {"chat_id": self.chat_id, "text": text}
        if markup:
            params["reply_markup"] = markup
        return self.tg.call("sendMessage", **params)

    def job(self, fn, *args):
        def run():
            try:
                fn(*args)
            except Exception as e:
                traceback.print_exc()
                self.say(f"⚠️ 실패: {e}")
        self.work.submit(run)

    # --- flows ---
    def send_topics(self, hint: str = ""):
        self.say("🤔 주제를 고르는 중…")
        topics = content.suggest_topics(self.env, hint)
        batch = uuid.uuid4().hex[:8]
        self.topics[batch] = topics
        text = "오늘의 주제 추천입니다. 하나를 골라주세요.\n\n" + "\n".join(
            f"{i + 1}. {t['title']}\n   {t['hook']}" for i, t in enumerate(topics))
        self.say(text, buttons([[(f"{i + 1}. {t['title'][:30]}", f"t:{batch}:{i}")] for i, t in enumerate(topics)]))

    def platforms(self) -> str:
        return "유튜브·인스타그램·스레드" if self.env.get("THREADS_ACCESS_TOKEN") else "유튜브·인스타그램"

    def write_scenario(self, topic: dict):
        """Topic -> scenario -> ask approval. Approving renders and uploads with no further step."""
        self.say(f"✍️ 「{topic['title']}」 시나리오를 쓰는 중…")
        scenario = content.write_scenario(self.env, topic)
        total = sum(s["seconds"] for s in scenario["scenes"])
        music = content.MUSIC.get(scenario["music"], "없음")
        key = uuid.uuid4().hex[:8]
        self.scenarios[key] = scenario
        self.say(f"📝 시나리오 ({len(scenario['scenes'])}장면, {total:.0f}초)\n제목: {scenario['title']}\n"
                 f"스타일: {scenario['theme']} · 음악: {scenario['music']} ({music})\n"
                 f"글꼴: 제목 {scenario.get('headFont') or '테마 기본'} / 본문 {scenario.get('bodyFont') or '테마 기본'}\n\n"
                 f"{content.describe(scenario)}\n\n"
                 f"캡션:\n{scenario['caption']}\n\n승인하면 영상을 만들어 {self.platforms()}에 바로 업로드합니다.",
                 buttons([[("✅ 승인 (렌더+업로드)", f"sok:{key}"), ("❌ 취소", f"sno:{key}")]]))

    def render_and_upload(self, scenario: dict):
        self.say("🎬 렌더링 중… (수 분 걸립니다)")
        video = content.render(scenario)
        self.upload(video)

    def ask_approval(self, video: str):
        meta = content.load_meta(video)
        key = uuid.uuid4().hex[:8]
        self.pending[key] = video
        caption = f"제목: {meta['title']}\n\n{meta['caption']}\n\n{self.platforms()}에 업로드할까요?"
        markup = buttons([[("✅ 업로드", f"ok:{key}"), ("❌ 취소", f"no:{key}")]])
        prev = content.preview(video)
        try:
            self.tg.send_video(self.chat_id, prev, caption, markup)
        finally:
            os.remove(prev)

    def upload(self, video: str):
        meta = content.load_meta(video)
        self.say(f"⬆️ {os.path.basename(video)} 업로드 중…")
        title = meta["title"] if "#shorts" in meta["title"].lower() else f"{meta['title']} #Shorts"
        results = publish_all(self.env, video, title, meta.get("description", ""), meta.get("caption"),
                              meta.get("tags", []), log=print)
        lines = [f"{'✅' if ok else '❌'} {name}: {res['url'] if ok else res}" for name, (ok, res) in results.items()]
        self.say("\n".join(lines))

    def list_uploads(self):
        vids = sorted((p for p in glob.glob(os.path.join(content.OUT, "*.mp4"))), key=os.path.getmtime, reverse=True)[:8]
        if not vids:
            self.say("out 폴더에 영상이 없습니다.")
            return
        batch = uuid.uuid4().hex[:8]
        self.files[batch] = vids
        self.say("업로드할 영상을 고르세요.",
                 buttons([[(os.path.basename(v)[:40], f"u:{batch}:{i}")] for i, v in enumerate(vids)]))

    # --- dispatch ---
    def on_message(self, msg: dict):
        text = (msg.get("text") or "").strip()
        if text.startswith("/topic"):
            self.job(self.send_topics, text[len("/topic"):].strip())
        elif text.startswith("/upload"):
            self.list_uploads()
        else:
            self.say(HELP)

    def on_callback(self, cq: dict):
        self.tg.call("answerCallbackQuery", callback_query_id=cq["id"])
        msg = cq["message"]
        # Drop the buttons so a second tap can't trigger the same action twice.
        self.tg.call("editMessageReplyMarkup", chat_id=msg["chat"]["id"], message_id=msg["message_id"],
                     reply_markup={"inline_keyboard": []})
        kind, *rest = cq["data"].split(":")
        with self.lock:
            if kind == "t" and rest[0] in self.topics:
                topic = self.topics.pop(rest[0])[int(rest[1])]
                self.job(self.write_scenario, topic)
            elif kind == "sok" and rest[0] in self.scenarios:
                self.job(self.render_and_upload, self.scenarios.pop(rest[0]))
            elif kind == "sno" and rest[0] in self.scenarios:
                self.scenarios.pop(rest[0])
                self.say("시나리오를 취소했습니다. /topic 으로 다시 시작할 수 있습니다.")
            elif kind == "u" and rest[0] in self.files:
                self.job(self.ask_approval, self.files.pop(rest[0])[int(rest[1])])
            elif kind == "ok" and rest[0] in self.pending:
                self.job(self.upload, self.pending.pop(rest[0]))
            elif kind == "no" and rest[0] in self.pending:
                video = self.pending.pop(rest[0])
                self.say(f"취소했습니다. 영상은 남겨뒀습니다: {os.path.basename(video)}")
            else:
                self.say("만료된 버튼입니다. 다시 시도해주세요.")

    def scheduler(self):
        now = dt.datetime.now()
        last = now.date() if now.time() >= dt.time(*DAILY_AT) else None  # no burst on restart after 08:50
        while True:
            now = dt.datetime.now()
            if is_due(now, last):
                last = now.date()
                self.job(self.send_topics, "")
            time.sleep(20)

    def run(self):
        print("bot running. Ctrl+C to stop.", flush=True)
        if self.chat_id:
            threading.Thread(target=self.scheduler, daemon=True).start()
            if self.env.get("IG_ACCESS_TOKEN") and self.env.get("IG_USER_ID"):
                watcher = CommentWatcher(self.env, os.path.join(ROOT, ".comment_state.json"), notify=self.say)
                threading.Thread(target=watcher.run, daemon=True).start()
        offset = 0
        while True:
            try:
                updates = self.tg.call("getUpdates", http_timeout=60, offset=offset, timeout=50)
            except Exception as e:
                print("getUpdates failed:", e, flush=True)
                time.sleep(5)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    self.handle(u)
                except Exception:
                    traceback.print_exc()

    def handle(self, u: dict):
        src = u.get("message") or (u.get("callback_query") or {}).get("message")
        if not src:
            return
        chat = src["chat"]["id"]
        if self.chat_id is None:  # first-time setup: tell the owner their chat id
            self.tg.call("sendMessage", chat_id=chat,
                         text=f"이 채팅의 ID는 {chat} 입니다. .env에 TELEGRAM_CHAT_ID={chat} 를 넣고 봇을 다시 실행하세요.")
            return
        if chat != self.chat_id:  # trust boundary: ignore everyone else
            return
        if "callback_query" in u:
            self.on_callback(u["callback_query"])
        else:
            self.on_message(u["message"])


if __name__ == "__main__":
    env = load_env(os.path.join(ROOT, ".env"))
    if not env.get("TELEGRAM_BOT_TOKEN"):
        sys.exit(".env에 TELEGRAM_BOT_TOKEN이 없습니다 (텔레그램 @BotFather에서 발급)")
    Bot(env).run()
