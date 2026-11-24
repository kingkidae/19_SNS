"""python scripts/test_bot.py — offline checks for scheduling, scenario clamping, chat-id gate, approval flow."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import content  # noqa: E402
from bot import Bot, is_due  # noqa: E402
from content import music_credit, sanitize  # noqa: E402

d = dt.date(2026, 11, 24)
assert not is_due(dt.datetime(2026, 11, 24, 8, 49), None)
assert is_due(dt.datetime(2026, 11, 24, 8, 50), None)
assert not is_due(dt.datetime(2026, 11, 24, 9, 0), d)  # already sent today
assert is_due(dt.datetime(2026, 11, 25, 8, 50), d)


def scene(**kw):
    return {"type": "text", "seconds": 3, "heading": "", "body": "", "emphasis": "", "items": [], "messages": [],
            "number": "", **kw}


raw = {"title": "t" * 200, "description": "", "caption": "c" * 400, "tags": [], "theme": "bogus", "music": "jazzy",
       "scenes": [scene(body="짧은 문장", seconds=0.5),  # too short to read -> raised
                  scene(type="list", heading="목록", items=[]),  # empty list -> text
                  scene(),  # empty -> dropped
                  scene(type="chat", messages=[{"side": "left", "text": "안녕"}] * 10)]
       + [scene(body="가나다라마바사아자차카타파하" * 2, seconds=8)] * 20}
s = sanitize(raw)
assert len(s["title"]) == 90 and len(s["caption"]) == 300
assert s["theme"] == "minimal" and s["music"] == "jazzy"
assert s["scenes"][0]["seconds"] >= 2.0
assert s["scenes"][1]["type"] == "text"
assert len(s["scenes"][2]["messages"]) == 7
assert sum(x["seconds"] for x in s["scenes"]) <= 58
# Long text gets enough reading time.
assert sanitize({**raw, "scenes": [scene(body="가" * 40, seconds=2)]})["scenes"][0]["seconds"] >= 6
# CC BY credit names the track; no music -> no credit; credit + caption fits Threads' 500 chars.
assert "Hyperfun" in music_credit("energetic") and music_credit("none") == ""
assert 300 + 2 + max(len(music_credit(m)) for m in content.MUSIC) <= 500

# Font choices: unknown -> "" (theme default); Python catalog matches the TSX registry exactly.
assert sanitize({**raw, "headFont": "Comic Sans", "bodyFont": "Pretendard"})["headFont"] == ""
assert sanitize({**raw, "headFont": "Jua", "bodyFont": "Pretendard"})["bodyFont"] == "Pretendard"
import re  # noqa: E402

tsx = open(os.path.join(content.ROOT, "src", "fonts.ts"), encoding="utf-8").read()
block = tsx[tsx.index("const REGISTRY"):tsx.index("export const FONT_NAMES")]
tsx_names = re.findall(r'^\s+(?:"([^"]+)"|(\w+)):\s*\{', block, re.M)
assert [a or b for a, b in tsx_names] == list(content.FONTS), "fonts.ts REGISTRY and content.FONTS differ"

# Only the configured chat can drive the bot.
b = Bot({"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "111"})
seen = []
b.on_message = seen.append
b.handle({"message": {"chat": {"id": 222}, "text": "/topic"}})
assert seen == []
b.handle({"message": {"chat": {"id": 111}, "text": "/topic"}})
assert len(seen) == 1

# Flow: topic -> scenario (approval buttons) -> approve -> render -> upload, no second approval.
calls = []
b = Bot({"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "111"})
b.tg.call = lambda method, **p: calls.append((method, p))
b.job = lambda fn, *a: fn(*a)  # run inline
sc = {"title": "T", "caption": "C", "theme": "night", "music": "calm", "scenes": [scene(body="문장")]}
content.write_scenario = lambda env, t: sc
content.render = lambda s: "out/x.mp4"
uploaded = []
b.upload = uploaded.append
b.topics["bt"] = [{"title": "주제", "hook": "훅"}]
cb = lambda data: {"id": "1", "data": data, "message": {"chat": {"id": 111}, "message_id": 5}}  # noqa: E731
b.on_callback(cb("t:bt:0"))
key = next(iter(b.scenarios))
msg = [p for m, p in calls if m == "sendMessage"][-1]
assert "night" in msg["text"] and "Peace of Mind" in msg["text"]
assert [x["callback_data"] for x in msg["reply_markup"]["inline_keyboard"][0]] == [f"sok:{key}", f"sno:{key}"]
assert uploaded == []  # nothing rendered/uploaded before approval
b.on_callback(cb(f"sok:{key}"))
assert uploaded == ["out/x.mp4"] and not b.scenarios
b.on_callback(cb(f"sok:{key}"))  # second tap on a used button does nothing
assert uploaded == ["out/x.mp4"]

# Cancel drops the scenario without rendering.
b.scenarios["k2"] = sc
b.on_callback(cb("sno:k2"))
assert "k2" not in b.scenarios and uploaded == ["out/x.mp4"]

print("ok")
