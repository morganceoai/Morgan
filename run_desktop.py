"""
Morgan Desktop — lançador da interface JARVIS no Mac.
Corre: python3 run_desktop.py
"""
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Garantir imports do Morgan
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import uvicorn
import webview
from desktop_server import app as fastapi_app

SERVER_PORT = 8765
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


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


if __name__ == "__main__":
    # Arrancar FastAPI em thread de background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("A arrancar Morgan Desktop...")
    if not wait_for_server():
        print("Erro: servidor não arrancou.")
        sys.exit(1)

    print(f"Servidor ativo em {SERVER_URL}")

    # Abrir janela nativa com pywebview
    window = webview.create_window(
        title="Morgan",
        url=SERVER_URL,
        width=1200,
        height=760,
        resizable=True,
        frameless=False,
        on_top=False,
        background_color="#020b18",
    )

    webview.start(debug=False)
