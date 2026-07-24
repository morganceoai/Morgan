"""
Pinterest API v5 — publicação autónoma de pins para PlannerAtlas.
OAuth 2.0 com refresh automático. Tokens em memory/pinterest_tokens.json.
"""
import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

TOKENS_FILE = Path(__file__).parent / "memory" / "pinterest_tokens.json"
API_BASE = "https://api.pinterest.com/v5"

APP_ID     = os.getenv("PINTEREST_APP_ID", "")
APP_SECRET = os.getenv("PINTEREST_APP_SECRET", "")
REDIRECT   = os.getenv("PINTEREST_REDIRECT_URI", "https://localhost:8080/callback")


# ── tokens ──────────────────────────────────────────────────────────────────

def _save_tokens(access_token: str, refresh_token: str, expires_in: int):
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)).isoformat()
    TOKENS_FILE.write_text(json.dumps({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expiry": expiry,
    }))


def _get_token() -> str:
    """Devolve access_token válido, fazendo refresh se necessário."""
    if not TOKENS_FILE.exists():
        raise RuntimeError("Pinterest não autenticado — corre pinterest_service.py --setup")
    data = json.loads(TOKENS_FILE.read_text())
    expiry = datetime.fromisoformat(data["expiry"])
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < expiry:
        return data["access_token"]
    # refresh
    r = requests.post("https://api.pinterest.com/v5/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": data["refresh_token"],
    }, auth=(APP_ID, APP_SECRET))
    r.raise_for_status()
    new = r.json()
    _save_tokens(new["access_token"], new.get("refresh_token", data["refresh_token"]), new.get("expires_in", 3600))
    return new["access_token"]


def is_configured() -> bool:
    return bool(APP_ID and APP_SECRET and TOKENS_FILE.exists())


# ── boards ───────────────────────────────────────────────────────────────────

def listar_boards() -> list[dict]:
    """Lista todos os boards da conta."""
    token = _get_token()
    r = requests.get(f"{API_BASE}/boards", headers={"Authorization": f"Bearer {token}"}, params={"page_size": 50})
    r.raise_for_status()
    return r.json().get("items", [])


def criar_board(nome: str, descricao: str = "", privado: bool = False) -> dict:
    """Cria um board novo."""
    token = _get_token()
    r = requests.post(f"{API_BASE}/boards", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json={"name": nome, "description": descricao, "privacy": "SECRET" if privado else "PUBLIC"})
    r.raise_for_status()
    return r.json()


# ── pins ────────────────────────────────────────────────────────────────────

def publicar_pin(board_id: str, titulo: str, descricao: str, url_destino: str,
                 imagem_url: str = "", alt_text: str = "") -> dict:
    """
    Publica um pin num board.
    imagem_url: URL pública da imagem (se vazio, Pinterest usa a imagem do url_destino).
    """
    token = _get_token()
    media = {"source_type": "image_url", "url": imagem_url} if imagem_url else \
            {"source_type": "image_url", "url": f"https://www.etsy.com/listing/{url_destino.split('/')[-1]}/images/0"}
    payload = {
        "board_id": board_id,
        "title": titulo[:100],
        "description": descricao[:500],
        "link": url_destino,
        "alt_text": alt_text[:500] if alt_text else titulo[:100],
        "media_source": media,
    }
    r = requests.post(f"{API_BASE}/pins", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json=payload)
    r.raise_for_status()
    return r.json()


def obter_analytics_pin(pin_id: str, dias: int = 7) -> dict:
    """Obtém métricas de um pin (impressões, cliques, saves)."""
    token = _get_token()
    fim = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inicio = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
    r = requests.get(f"{API_BASE}/pins/{pin_id}/analytics", headers={"Authorization": f"Bearer {token}"},
                     params={"start_date": inicio, "end_date": fim,
                             "metric_types": "IMPRESSION,OUTBOUND_CLICK,SAVE,PIN_CLICK"})
    r.raise_for_status()
    return r.json()


# ── setup OAuth ──────────────────────────────────────────────────────────────

def setup_oauth():
    """Flow OAuth interactivo — corre uma vez para autenticar."""
    if not APP_ID or not APP_SECRET:
        print("❌ PINTEREST_APP_ID e PINTEREST_APP_SECRET em falta no .env")
        return

    scope = "boards:read,boards:write,pins:read,pins:write"
    auth_url = (
        f"https://www.pinterest.com/oauth/?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT}&response_type=code&scope={scope}"
    )
    print(f"\n🔗 Abre este URL no browser (com morganceoai@gmail.com):\n\n{auth_url}\n")
    print("Depois de autorizar, copia o parâmetro 'code' do URL de redirect e cola aqui:")
    code = input("code: ").strip()

    r = requests.post("https://api.pinterest.com/v5/oauth/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT,
    }, auth=(APP_ID, APP_SECRET))
    if r.status_code != 200:
        print(f"❌ Erro: {r.text}")
        return
    data = r.json()
    _save_tokens(data["access_token"], data.get("refresh_token", ""), data.get("expires_in", 3600))
    print("✅ Pinterest autenticado! Tokens guardados em memory/pinterest_tokens.json")

    # verificar conta
    me = requests.get(f"{API_BASE}/user_account", headers={"Authorization": f"Bearer {data['access_token']}"})
    if me.ok:
        u = me.json()
        print(f"   Conta: {u.get('username')} ({u.get('account_type')})")


if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        setup_oauth()
    elif "--boards" in sys.argv:
        for b in listar_boards():
            print(b["id"], "|", b["name"])
    else:
        print("Uso: python pinterest_service.py --setup | --boards")
