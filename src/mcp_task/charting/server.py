import http.server
import shutil
import socket
import tempfile
import threading
import uuid
from pathlib import Path

# Charts live in a dedicated temp folder for this process only, so it's safe
# to wipe it clean on every server startup instead of accumulating files
# forever across restarts.
_CHARTS_DIR = Path(tempfile.gettempdir()) / "mcp_task_charts"

_lock = threading.Lock()
_port: int | None = None


class _ChartRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_CHARTS_DIR), **kwargs)

    def log_message(self, _format: str, *_args) -> None:
        pass  # keep the MCP server's stdio quiet


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _ensure_server_running() -> int:
    """Start the local, loopback-only chart file server once per process."""
    global _port
    with _lock:
        if _port is not None:
            return _port

        shutil.rmtree(_CHARTS_DIR, ignore_errors=True)
        _CHARTS_DIR.mkdir(parents=True, exist_ok=True)

        port = _pick_free_port()
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), _ChartRequestHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        _port = port
        return port


def publish_html(html_bytes: bytes) -> str:
    """Save an HTML page and return a clickable http://127.0.0.1 URL for it."""
    port = _ensure_server_running()
    filename = f"{uuid.uuid4().hex}.html"
    (_CHARTS_DIR / filename).write_bytes(html_bytes)
    return f"http://127.0.0.1:{port}/{filename}"
