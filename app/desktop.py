from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.main import app  # noqa: E402
from server.paths import PORT, ensure_dirs  # noqa: E402


def run_server() -> None:
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


def wait_until_up(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{PORT}/api/health"
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=0.5).json().get("ok"):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("本地服务启动超时")


def main() -> None:
    import os

    os.chdir(ROOT)
    ensure_dirs()
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    wait_until_up()
    url = f"http://127.0.0.1:{PORT}/"
    try:
        import webview

        webview.create_window("AutoApply", url, width=1280, height=860)
        webview.start()
    except Exception as exc:
        print(f"无法打开桌面窗口（{exc}）。请直接用浏览器打开 {url}")
        thread.join()


if __name__ == "__main__":
    main()
