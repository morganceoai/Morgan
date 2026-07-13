"""
Morgan App — janela nativa macOS via pywebview
Abre a interface HTML sem restrições de browser (acesso total ao microfone).
O desktop_server.py tem de estar a correr na porta 8765.
"""
import subprocess
import sys
import time
import threading
import os
import signal
from pathlib import Path

import webview

SERVER_PORT = 8765
SERVER_URL = f"http://localhost:{SERVER_PORT}"
BASE_DIR = Path(__file__).parent


def start_server():
    """Inicia o desktop_server.py em background se não estiver a correr."""
    venv_python = BASE_DIR / "venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    server_script = str(BASE_DIR / "desktop_server.py")

    proc = subprocess.Popen(
        [python, server_script],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def wait_for_server(timeout=30):
    """Aguarda o servidor responder."""
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(SERVER_URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def check_server_running():
    """Verifica se o servidor já está a correr."""
    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen(SERVER_URL, timeout=1)
        return True
    except Exception:
        return False


def main():
    server_proc = None

    if not check_server_running():
        print("A iniciar servidor Morgan...")
        server_proc = start_server()
        if not wait_for_server(timeout=30):
            print("Erro: servidor não respondeu em 30 segundos.")
            if server_proc:
                server_proc.terminate()
            sys.exit(1)
        print("Servidor pronto.")
    else:
        print("Servidor já está a correr.")

    def on_closed():
        if server_proc:
            server_proc.terminate()

    window = webview.create_window(
        title="Morgan",
        url=SERVER_URL,
        width=1440,
        height=900,
        resizable=True,
        fullscreen=False,
        min_size=(800, 600),
        background_color="#000000",
    )
    window.events.closed += on_closed

    # gui="cocoa" usa WKWebView nativo — acesso completo ao microfone sem restrições HTTP
    webview.start(gui="cocoa", debug=False)


if __name__ == "__main__":
    main()
