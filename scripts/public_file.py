"""Expose ONE local file at an unguessable public URL for a few minutes (Cloudflare quick tunnel).

Threads only downloads media from public URLs. We serve just that file from 127.0.0.1 under a random
path, open `cloudflared tunnel --url` (no account needed), and close both when the `with` block ends.
"""
import glob
import http.server
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import urllib.request
from contextlib import contextmanager


def find_cloudflared() -> str:
    exe = os.environ.get("CLOUDFLARED") or shutil.which("cloudflared")
    if exe:
        return exe
    for pattern in (r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
                    r"C:\Program Files\cloudflared\cloudflared.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared*\cloudflared*.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe")):
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
    raise RuntimeError("cloudflared가 없습니다: winget install Cloudflare.cloudflared")


@contextmanager
def local_server(path: str):
    """Serve only `path` at http://127.0.0.1:<port>/<random>.mp4; every other path is 404."""
    name = f"/{secrets.token_urlsafe(24)}.mp4"
    size = os.path.getsize(path)

    class Handler(http.server.BaseHTTPRequestHandler):
        def _head(self) -> bool:
            if self.path != name:
                self.send_error(404)
                return False
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return True

        def do_HEAD(self):
            self._head()

        def do_GET(self):
            # shortcut: no Range support; Meta fetches the whole file. Add Range if a fetcher needs it.
            if self._head():
                with open(path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)

        def log_message(self, *args):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv.server_address[1], name
    finally:
        srv.shutdown()
        srv.server_close()


@contextmanager
def serve_public(path: str, log=print, wait: int = 60):
    with local_server(path) as (port, name):
        proc = subprocess.Popen([find_cloudflared(), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace")
        try:
            base, deadline = None, time.time() + wait
            while base is None and time.time() < deadline:
                line = proc.stderr.readline()
                if not line and proc.poll() is not None:
                    break
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if m:
                    base = m.group(0)
            if base is None:
                raise RuntimeError("cloudflared 터널 주소를 받지 못했습니다")
            threading.Thread(target=lambda: proc.stderr.read(), daemon=True).start()  # keep the pipe drained
            url = base + name
            # New quick-tunnel hostnames take a few seconds to resolve; don't hand Meta a dead link.
            while True:
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10) as r:
                        if r.status == 200:
                            break
                except Exception:
                    pass
                if time.time() > deadline:
                    raise RuntimeError("터널 주소가 외부에서 열리지 않습니다")
                time.sleep(2)
            log("public link open")
            yield url
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
