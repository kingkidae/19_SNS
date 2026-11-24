"""Claude API (topics, scenario) + Remotion render for the Telegram bot."""
import datetime as dt
import json
import os
import subprocess
import tempfile

import anthropic
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
MODEL = "claude-opus-5-5"

# public/music/<mood>.mp3 — Kevin MacLeod (incompetech.com), CC BY 4.0: credit is required and added automatically.
MUSIC = {
    "calm": "Peace of Mind", "emotional": "Heartbreaking", "upbeat": "Happy Happy Game Show",
    "energetic": "Hyperfun", "epic": "Industrial Cinematic", "comedic": "Mischief Maker",
    "jazzy": "Backbay Lounge", "chill": "Chill Wave",
}
THEMES = ["retro", "minimal", "night", "pastel", "paper", "neon"]
# Same keys as REGISTRY in src/fonts.ts (checked by test_bot.py). Descriptions guide Claude's choice.
FONTS = {
    "Pretendard": "고딕 · 깔끔·모던, 가장 무난한 본문/제목",
    "Noto Sans KR": "고딕 · 표준적이고 단단함",
    "IBM Plex Sans KR": "고딕 · 기술적·지적인 느낌",
    "Gothic A1": "고딕 · 매우 굵게~매우 얇게, 대비 강조",
    "Asta Sans": "고딕 · 부드럽고 현대적",
    "Nanum Gothic": "고딕 · 친숙한 기본체",
    "Black Han Sans": "제목용 · 아주 굵고 각진 포스터체",
    "Do Hyeon": "제목용 · 좁고 굵은 간판체",
    "Bagel Fat One": "제목용 · 통통하고 귀여운 굵은체",
    "Gasoek One": "제목용 · 매우 두꺼운 임팩트체",
    "Dongle": "제목용 · 동글동글 귀여운 체",
    "Orbit": "제목용 · 얇은 기하학, 미래·테크",
    "Black And White Picture": "제목용 · 흑백 영화 같은 레트로",
    "Gugi": "제목용 · 게임·오락실 느낌",
    "Moirai One": "제목용 · 외곽선 장식체, 짧은 단어에만",
    "Noto Serif KR": "명조 · 단정하고 격조 있음",
    "Nanum Myeongjo": "명조 · 전통적·문학적",
    "Gowun Batang": "명조 · 따뜻하고 부드러운 바탕",
    "Hahmlet": "명조 · 현대적 세리프, 잡지 느낌",
    "Song Myung": "명조 · 붓맛이 있는 고전체",
    "Diphylleia": "명조 · 가늘고 섬세함",
    "Jua": "둥근체 · 귀엽고 친근함",
    "Gowun Dodum": "둥근체 · 순하고 담백함",
    "Sunflower": "둥근체 · 밝고 경쾌",
    "Cute Font": "손글씨 · 아기자기 귀여움",
    "Poor Story": "손글씨 · 동화책 느낌",
    "Nanum Pen Script": "손글씨 · 펜으로 쓴 메모",
    "Gaegu": "손글씨 · 장난스러운 낙서",
    "Hi Melody": "손글씨 · 가볍고 발랄",
    "Gamja Flower": "손글씨 · 소박하고 귀여움",
    "Single Day": "손글씨 · 다이어리 감성",
    "Yeon Sung": "손글씨 · 개성 있는 굵은 손글씨",
    "Kirang Haerang": "손글씨 · 레트로 간판 손글씨",
    "Stylish": "손글씨 · 세련된 필기체",
    "East Sea Dokdo": "붓글씨 · 거칠고 힘찬 붓",
    "Dokdo": "붓글씨 · 투박한 붓",
    "Nanum Brush Script": "붓글씨 · 자연스러운 붓펜",
}
SCENE_TYPES = ["title", "text", "typo", "chat", "list", "stat", "quote", "outro"]

TOPICS_SCHEMA = {
    "type": "object",
    "properties": {"topics": {"type": "array", "items": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "hook": {"type": "string"}},
        "required": ["title", "hook"], "additionalProperties": False}}},
    "required": ["topics"], "additionalProperties": False,
}
SCENARIO_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "caption": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "theme": {"type": "string", "enum": THEMES},
        "music": {"type": "string", "enum": ["none", *MUSIC]},
        "headFont": {"type": "string", "enum": list(FONTS)},
        "bodyFont": {"type": "string", "enum": list(FONTS)},
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": SCENE_TYPES},
                "seconds": {"type": "number"},
                "heading": {"type": "string"},
                "body": {"type": "string"},
                "emphasis": {"type": "string"},
                "items": {"type": "array", "items": {"type": "string"}},
                "messages": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"side": {"type": "string", "enum": ["left", "right"]}, "text": {"type": "string"}},
                    "required": ["side", "text"], "additionalProperties": False}},
                "number": {"type": "string"},
            },
            "required": ["type", "seconds", "heading", "body", "emphasis", "items", "messages", "number"],
            "additionalProperties": False}},
    },
    "required": ["title", "description", "caption", "tags", "theme", "music", "headFont", "bodyFont", "scenes"],
    "additionalProperties": False,
}

SYSTEM = (
    "너는 한국어 숏폼(유튜브 쇼츠·인스타 릴스·스레드) 영상 기획자다. 영상은 세로형이고 음성 내레이션 없이 "
    "화면 글자와 배경음악으로 전달된다. 영어 자막이나 영어 단어는 쓰지 않는다."
)

SCENARIO_GUIDE = """
[영상 형식은 주제에 맞게 네가 판단해서 고른다. 매번 같은 형식을 쓰지 마라.]

theme (화면 분위기):
- minimal: 깔끔한 흰 배경, 정보·팁·생활 꿀팁·통계
- night: 짙은 남색 + 명조체, 위로·감성·새벽 감성·편지
- pastel: 부드러운 파스텔 + 둥근 글씨, 일상 공감·귀여운 상황극·가벼운 웃음
- paper: 종이 질감 + 바탕체, 이야기·회고·명언·책 구절
- neon: 검정 + 형광, 동기부여·도전·카운트다운·강한 메시지
- retro: 레트로 포스터 + 굵은 타이포, 리듬감 있는 선언·밈·강렬한 한마디

music (배경음악, 필요 없으면 none):
calm 잔잔함 / emotional 슬픔·감동 / upbeat 밝고 경쾌 / energetic 빠르고 신남 / epic 웅장·도전 /
comedic 장난스러움 / jazzy 재즈 라운지 / chill 로파이·느긋함

headFont / bodyFont (제목용 글꼴 / 본문용 글꼴, 주제의 분위기에 맞게 고른다):
""" + "\n".join(f"- {k}: {v}" for k, v in FONTS.items()) + """
- 제목에는 개성 있는 글꼴(제목용·손글씨·붓글씨·명조)을, 본문에는 읽기 쉬운 글꼴(고딕·명조·둥근체)을 짝지어라.
- 손글씨·붓글씨·장식체는 본문에 쓰지 마라. 매번 Pretendard만 고르지 말고 주제에 맞는 개성을 살려라.

scene type (장면마다 내용에 맞는 형식을 골라 섞어라):
- title: 첫 화면 훅. heading 큰 제목, body 짧은 부제
- text: 문장 2~4줄(body, 줄은 \\n으로 구분), emphasis로 핵심 단어 강조
- typo: 짧고 강한 단어들이 튀어나오는 키네틱 타이포(body 1~3줄, 줄당 1~3단어). 리듬감 있는 한마디에만
- chat: 메신저 대화 상황극(messages 3~6개, left=상대, right=나). heading에 대화 상대 이름
- list: 팁·방법·순위(heading 제목, items 3~5개, 한 항목 18자 이내)
- stat: 큰 숫자 하나(number 예: "73%", "3초", "1,200만"), heading은 무엇의 숫자인지, body는 해석 한 줄
- quote: 인용구·명언(body 인용문, heading 말한 사람)
- outro: 마지막 화면. 저장·공유·다음 행동을 유도하는 한마디(heading), body 짧게
쓰지 않는 필드는 빈 문자열("")이나 빈 배열([])로 둔다.

구성 규칙:
- scenes 5~9개, 전체 25~45초. 첫 장면은 title 또는 typo로 2초 안에 훅을 건다. 마지막은 outro.
- 같은 type을 연달아 3번 쓰지 마라. 주제가 정보형이면 list·stat 위주, 공감형이면 chat·text 위주처럼 내용에 맞춰라.
- 숫자·통계는 실제로 확인된 사실만 쓴다. 확실하지 않으면 stat을 쓰지 마라.
- seconds는 읽는 시간을 고려해 정한다(한 화면 2.5~7초).
- 화면 글자는 짧고 구어체로. 한 줄 16자 이내.
- title: 유튜브 제목(40자 이내). description: 2~3문장. caption: 인스타·스레드 캡션(해시태그 5개 포함, 250자 이내). tags: 5~10개.
""".strip()


def _ask(env: dict, prompt: str, schema: dict, effort: str) -> dict:
    client = anthropic.Anthropic(api_key=env.get("ANTHROPIC_API_KEY") or None)
    r = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    if r.stop_reason == "refusal":
        raise RuntimeError("Claude가 요청을 거절했습니다")
    if r.stop_reason == "max_tokens":
        raise RuntimeError("Claude 응답이 길이 제한에 걸려 잘렸습니다")
    return json.loads(next(b.text for b in r.content if b.type == "text"))


def suggest_topics(env: dict, hint: str = "") -> list[dict]:
    prompt = (f"오늘은 {dt.date.today():%Y-%m-%d}이다. 30~40초짜리 세로형 숏폼으로 만들기 좋은 주제 5개를 제안해라. "
              "정보형·공감형·감성형·동기부여형 등 성격이 서로 다른 주제를 섞어라. "
              "주제마다 짧은 제목(title)과 시청자를 붙잡을 한 줄 훅(hook)을 써라.")
    if hint:
        prompt += f" 이 방향을 반영해라: {hint}"
    return _ask(env, prompt, TOPICS_SCHEMA, "low")["topics"][:5]


def write_scenario(env: dict, topic: dict) -> dict:
    prompt = f"주제: {topic['title']} — {topic['hook']}\n\n이 주제로 세로형 숏폼 시나리오를 써라.\n\n{SCENARIO_GUIDE}"
    return sanitize(_ask(env, prompt, SCENARIO_SCHEMA, "medium"))


def reading_seconds(scene: dict) -> float:
    """Minimum on-screen time so viewers can read it (~7 Korean chars/sec + entrance)."""
    text = scene["heading"] + scene["body"] + scene["number"] + "".join(scene["items"]) \
        + "".join(m["text"] for m in scene["messages"])
    extra = 0.6 * len(scene["messages"]) + 0.3 * len(scene["items"])
    return 1.2 + len(text.replace(" ", "").replace("\n", "")) / 7 + extra


def sanitize(s: dict) -> dict:
    """Clamp what the schema can't: scene count, durations (min = reading time), list/chat sizes, total length."""
    scenes = []
    for sc in s["scenes"][:12]:
        sc = {**sc, "items": sc["items"][:5], "messages": sc["messages"][:7]}
        if sc["type"] == "list" and not sc["items"] or sc["type"] == "chat" and not sc["messages"]:
            sc["type"] = "text"
        if not (sc["heading"] or sc["body"] or sc["items"] or sc["messages"] or sc["number"]):
            continue
        sc["seconds"] = round(min(8.0, max(float(sc["seconds"] or 0), reading_seconds(sc), 2.0)), 1)
        scenes.append(sc)
    if not scenes:
        raise RuntimeError("시나리오에 화면에 띄울 내용이 없습니다")
    total, kept = 0.0, []
    for sc in scenes:  # cap at 58s so it stays a Short/Reel
        if total + sc["seconds"] > 58:
            break
        kept.append(sc)
        total += sc["seconds"]
    theme = s["theme"] if s["theme"] in THEMES else "minimal"
    music = s["music"] if s["music"] in MUSIC else "none"
    # Unknown fonts -> "" so the composition falls back to the theme's own pair.
    fonts = {k: s.get(k) if s.get(k) in FONTS else "" for k in ("headFont", "bodyFont")}
    return {**s, "title": s["title"][:90], "caption": s["caption"][:300], "tags": s["tags"][:15],
            "theme": theme, "music": music, **fonts, "scenes": kept}


def music_credit(music: str) -> str:
    if music not in MUSIC:
        return ""
    return (f'음악: "{MUSIC[music]}" Kevin MacLeod (incompetech.com)\n'
            "Licensed under Creative Commons: By Attribution 4.0\nhttps://creativecommons.org/licenses/by/4.0/")


PROPS = ("theme", "music", "headFont", "bodyFont", "scenes")  # what the Short composition reads


def render(scenario: dict) -> str:
    """Render the Short composition; writes out/<stamp>.mp4 plus <stamp>.json (upload metadata)."""
    os.makedirs(OUT, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    video = os.path.join(OUT, f"short-{stamp}.mp4")
    credit = music_credit(scenario["music"])
    meta = {
        "title": scenario["title"],
        "description": "\n\n".join(x for x in (scenario["description"], credit) if x),
        "caption": "\n\n".join(x for x in (scenario["caption"], credit) if x),  # caption <=300 + credit <500 (Threads)
        "tags": scenario["tags"],
    }
    with open(os.path.join(OUT, f"short-{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump({**meta, **{k: scenario.get(k, "") for k in PROPS}}, f, ensure_ascii=False, indent=1)
    props = os.path.join(OUT, f"short-{stamp}.props.json")
    with open(props, "w", encoding="utf-8") as f:
        json.dump({k: scenario.get(k, "") for k in PROPS}, f, ensure_ascii=False)
    npx = "npx.cmd" if os.name == "nt" else "npx"
    r = subprocess.run([npx, "remotion", "render", "Short", video, f"--props={props}", "--log=error"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    os.remove(props)
    if r.returncode != 0 or not os.path.exists(video):
        raise RuntimeError(f"렌더 실패: {(r.stderr or r.stdout).strip()[-500:]}")
    return video


def describe(scenario: dict) -> str:
    """Human-readable scenario for the Telegram approval message."""
    lines = []
    for i, sc in enumerate(scenario["scenes"], 1):
        parts = [sc["heading"], sc["number"], sc["body"].replace("\n", " / ")]
        parts += [f"• {x}" for x in sc["items"]]
        parts += [f"{'나' if m['side'] == 'right' else '상대'}: {m['text']}" for m in sc["messages"]]
        lines.append(f"{i}. [{sc['type']}·{sc['seconds']}초] " + " | ".join(p for p in parts if p))
    return "\n".join(lines)


def preview(video: str) -> str:
    """Small copy for Telegram (bots can send at most 50MB). Caller deletes it."""
    fd, dst = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", video, "-vf", "scale=540:-2",
                    "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart", dst], check=True, capture_output=True)
    return dst


def load_meta(video: str) -> dict:
    path = os.path.splitext(video)[0] + ".json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    name = os.path.splitext(os.path.basename(video))[0]
    return {"title": name, "description": "", "caption": name, "tags": []}
