"""python scripts/test_upload_instagram.py — offline checks for the Reels status polling."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from upload_instagram import upload_instagram, wait_until_finished  # noqa: E402

quiet = lambda *_: None  # noqa: E731

# Finishes after two IN_PROGRESS polls.
seq = iter([{"status_code": "IN_PROGRESS"}, {"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}])
slept = []
wait_until_finished(lambda: next(seq), sleep=slept.append, interval=5, log=quiet)
assert slept == [5, 5]

# ERROR surfaces Instagram's status text.
try:
    wait_until_finished(lambda: {"status_code": "ERROR", "status": "Error: 2207026"}, sleep=quiet, log=quiet)
    raise AssertionError("expected failure")
except RuntimeError as e:
    assert "2207026" in str(e)

# Never finishing hits the timeout instead of looping forever.
try:
    wait_until_finished(lambda: {"status_code": "IN_PROGRESS"}, sleep=quiet, interval=10, timeout=30, log=quiet)
    raise AssertionError("expected timeout")
except TimeoutError:
    pass

# Missing credentials fail before any network call.
try:
    upload_instagram({}, __file__, "x", log=quiet)
    raise AssertionError("expected missing-env error")
except RuntimeError as e:
    assert "IG_ACCESS_TOKEN" in str(e)

# Conversion: a Remotion-like source (full-range yuvj420p, 320k audio) comes out Reels-ready.
import subprocess  # noqa: E402
import tempfile  # noqa: E402

import imageio_ffmpeg  # noqa: E402
from upload_instagram import to_reels_spec  # noqa: E402

ff = imageio_ffmpeg.get_ffmpeg_exe()
with tempfile.TemporaryDirectory() as d:
    src, dst = os.path.join(d, "src.mp4"), os.path.join(d, "dst.mp4")
    subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc=s=108x192:d=1:r=30",
                    "-f", "lavfi", "-i", "sine=d=1", "-pix_fmt", "yuvj420p", "-b:a", "320k", src], check=True)
    to_reels_spec(src, dst)
    info = subprocess.run([ff, "-hide_banner", "-i", dst], capture_output=True, text=True).stderr
    assert "yuv420p" in info and "yuvj420p" not in info and "(pc" not in info, info
    assert "48000 Hz" in info, info
    head = open(dst, "rb").read()
    assert head.index(b"moov") < head.index(b"mdat"), "moov atom must come first"

    # Silent source (no audio stream, like scenario videos) gets an AAC track of the same length.
    silent = os.path.join(d, "silent.mp4")
    subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc=s=108x192:d=2:r=30", "-pix_fmt", "yuvj420p", silent],
                   check=True)
    to_reels_spec(silent, dst)
    info = subprocess.run([ff, "-hide_banner", "-i", dst], capture_output=True, text=True).stderr
    assert "Audio: aac" in info and "Duration: 00:00:02.0" in info, info

    try:
        to_reels_spec(os.path.join(d, "missing.mp4"), dst)
        raise AssertionError("expected ffmpeg failure")
    except RuntimeError as e:
        assert "ffmpeg failed" in str(e)

print("ok")
