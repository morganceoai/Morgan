"""
Morgan Desktop — lançador da interface JARVIS no Mac.
Corre: python3 run_desktop.py
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import uvicorn
import webview
from desktop_server import app as fastapi_app

SERVER_PORT = 8765
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"

MINI_W, MINI_H = 220, 220
FULL_W, FULL_H = 1200, 760


def get_screen_size():
    try:
        from AppKit import NSScreen
        f = NSScreen.mainScreen().frame()
        return int(f.size.width), int(f.size.height)
    except Exception:
        return 1440, 900


def start_server():
    uvicorn.run(fastapi_app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")


def wait_for_server(timeout=10):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(SERVER_URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


class Api:
    """Bridge JS → Python para controlo da janela."""
    _window = None

    def set_window(self, w):
        self._window = w

    def close_app(self):
        import os
        os._exit(0)

    def sleep_app(self):
        self._window.minimize()

    def enter_mini(self):
        sw, sh = get_screen_size()
        self._window.resize(MINI_W, MINI_H)
        self._window.move(sw - MINI_W - 20, 45)

    def exit_mini(self):
        sw, sh = get_screen_size()
        self._window.resize(FULL_W, FULL_H)
        self._window.move((sw - FULL_W) // 2, (sh - FULL_H) // 2)


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("A arrancar Morgan Desktop...")
    if not wait_for_server():
        print("Erro: servidor não arrancou.")
        sys.exit(1)

    print(f"Servidor ativo em {SERVER_URL}")

    api = Api()

    window = webview.create_window(
        title="Morgan",
        url=SERVER_URL,
        width=FULL_W,
        height=FULL_H,
        resizable=True,
        frameless=True,
        on_top=False,
        background_color="#020b18",
        js_api=api,
    )

    api.set_window(window)

    def on_minimized():
        window.evaluate_js("pauseConvai()")

    def on_restored():
        window.evaluate_js("resumeConvai()")

    window.events.minimized += on_minimized
    window.events.restored += on_restored

    try:
        webview.start(debug=False)
    except Exception as e:
        print(f"Erro pywebview: {e}")
        import traceback; traceback.print_exc()
