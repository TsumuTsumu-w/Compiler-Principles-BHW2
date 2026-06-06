"""One-click server: serves the built Vue frontend + analyzer API.

Usage:
    python server.py              # starts on http://127.0.0.1:8080
    python server.py --port 9090  # custom port
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import signal
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Path helpers — works both in development and inside a PyInstaller bundle
# ---------------------------------------------------------------------------

def _get_base_dir() -> Path:
    """Return the directory that contains this script (or the PyInstaller bundle)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def _get_static_dir() -> Path:
    """Locate the built frontend dist/ directory."""
    base = _get_base_dir()
    # When bundled by PyInstaller, dist files are placed under "frontend_dist/"
    bundled = base / "frontend_dist"
    if bundled.is_dir():
        return bundled
    # Development: bighw1/server.py → ../frontend/dist
    dev = base.parent / "frontend" / "dist"
    if dev.is_dir():
        return dev
    raise FileNotFoundError(
        "找不到前端静态文件。请先在 frontend/ 目录运行 pnpm build。"
    )


# ---------------------------------------------------------------------------
# Import the analyzer (same process — no subprocess overhead)
# ---------------------------------------------------------------------------

# Ensure the bighw1 package directory is on sys.path so imports work when
# running from a PyInstaller bundle where CWD may differ.
_bighw1_dir = str(_get_base_dir())
if _bighw1_dir not in sys.path:
    sys.path.insert(0, _bighw1_dir)

from analyze_source import analyze_source  # noqa: E402


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

# Extra MIME types that Python's mimetypes module may not know by default
_EXTRA_MIME: dict[str, str] = {
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".json": "application/json",
    ".wasm": "application/wasm",
}


class Handler(BaseHTTPRequestHandler):
    """Routes requests to either the analyzer API or static files."""

    static_dir: Path

    # Silence per-request log lines (uncomment for debugging)
    # def log_message(self, fmt, *args): ...

    # --- routing -----------------------------------------------------------

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "":
            self._serve_file(self.static_dir / "index.html")
            return
        # Strip query string for file lookup
        clean = unquote(self.path.split("?", 1)[0].split("#", 1)[0])
        file_path = (self.static_dir / clean.lstrip("/")).resolve()
        # Prevent directory traversal
        if not str(file_path).startswith(str(self.static_dir.resolve())):
            self._send_json(403, {"message": "Forbidden"})
            return
        if file_path.is_file():
            self._serve_file(file_path)
        else:
            # SPA fallback — serve index.html for client-side routing
            self._serve_file(self.static_dir / "index.html")

    def do_POST(self) -> None:
        if self.path.startswith("/api/analyze"):
            self._handle_analyze()
        else:
            self._send_json(404, {"message": "Not Found"})

    # --- API handlers ------------------------------------------------------

    def _handle_analyze(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body) if body else {}
            source = payload.get("source", "")
            result = analyze_source(source)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {"message": str(exc)})

    # --- response helpers --------------------------------------------------

    def _send_json(self, code: int, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json(404, {"message": "File not found"})
            return
        mime = _EXTRA_MIME.get(path.suffix) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        # Cache static assets aggressively; index.html should revalidate
        if path.name == "index.html":
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="类 Rust 词法/语法分析演示台")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    static_dir = _get_static_dir()
    Handler.static_dir = static_dir

    server = HTTPServer((args.host, args.port), Handler)

    url = f"http://{args.host}:{args.port}"
    print(f"\n  [OK] 分析器已启动: {url}\n  按 Ctrl+C 停止服务器。\n")

    # Graceful shutdown on Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: (print("\n  服务器已停止。"), server.shutdown()))

    # Auto-open browser
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("  服务器已停止。")


if __name__ == "__main__":
    main()
