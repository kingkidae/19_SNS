"""Upload a rendered video to YouTube and Instagram (Reels) at the same time.

  python scripts/publish.py out/seoul-moon-shorts.mp4 --title "..." --caption "..."
  python scripts/publish.py out/x.mp4 --only instagram

One platform failing does not stop the other; exit code is 1 if any failed.
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from upload_instagram import upload_instagram  # noqa: E402
from upload_youtube import upload_youtube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path: str) -> dict:
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--title", required=True, help="YouTube title")
    p.add_argument("--description", default="", help="YouTube description")
    p.add_argument("--caption", help="Instagram caption (default: title + description)")
    p.add_argument("--tags", default="", help="comma-separated YouTube tags")
    p.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    p.add_argument("--only", choices=["youtube", "instagram"])
    a = p.parse_args()

    if not os.path.isfile(a.video):
        p.error(f"no such file: {a.video}")
    env = load_env(os.path.join(ROOT, ".env"))
    caption = a.caption or "\n\n".join(x for x in (a.title, a.description) if x)

    jobs = {
        "youtube": lambda: upload_youtube(
            env, a.video, a.title, a.description, [t.strip() for t in a.tags.split(",") if t.strip()],
            a.privacy, os.path.join(ROOT, ".yt_token.json"), log=lambda m: print(f"[youtube] {m}", flush=True)),
        "instagram": lambda: upload_instagram(
            env, a.video, caption, log=lambda m: print(f"[instagram] {m}", flush=True)),
    }
    if a.only:
        jobs = {a.only: jobs[a.only]}

    failed = False
    with ThreadPoolExecutor() as pool:
        futures = {name: pool.submit(fn) for name, fn in jobs.items()}
        for name, fut in futures.items():
            try:
                print(f"[{name}] OK {fut.result()}", flush=True)
            except Exception as e:  # report each platform independently
                failed = True
                print(f"[{name}] FAILED {type(e).__name__}: {e}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
