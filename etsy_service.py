"""
Etsy API v3 — serviço OAuth2 para o Morgan Operator.
Usa a biblioteca etsyv3 com refresh automático de tokens.

Setup (uma vez):
1. Criar app em etsy.com/developers com scopes: listings_r transactions_r shops_r
2. Correr: python3 etsy_service.py --setup
3. Autorizar no browser e colar o code
4. Tokens guardados em memory/etsy_tokens.json
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

TOKENS_FILE = Path(__file__).parent / "memory" / "etsy_tokens.json"
ETSY_KEYSTRING = os.getenv("ETSY_KEYSTRING", "")
ETSY_SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET", "")
ETSY_SHOP_ID = os.getenv("ETSY_SHOP_ID", "")


def _save_tokens(token: str, refresh_token: str, expiry):
    TOKENS_FILE.parent.mkdir(exist_ok=True)
    expiry_str = expiry.isoformat() if hasattr(expiry, "isoformat") else str(expiry)
    TOKENS_FILE.write_text(json.dumps({
        "token": token,
        "refresh_token": refresh_token,
        "expiry": expiry_str,
    }, ensure_ascii=False), encoding="utf-8")
    logger.info("etsy_tokens: guardados")


def _get_token() -> str:
    """Devolve access_token válido, fazendo refresh se necessário."""
    if not TOKENS_FILE.exists():
        return ""
    data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    expiry = datetime.fromisoformat(data["expiry"])
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < expiry:
        return data["token"]
    # Refresh
    try:
        import requests as _req
        r = _req.post("https://api.etsy.com/v3/public/oauth/token", data={
            "grant_type": "refresh_token",
            "client_id": ETSY_KEYSTRING,
            "refresh_token": data["refresh_token"],
        }, timeout=10)
        if r.status_code == 200:
            new = r.json()
            from datetime import timedelta
            exp = datetime.now(timezone.utc) + timedelta(seconds=new.get("expires_in", 3600))
            _save_tokens(new["access_token"], new["refresh_token"], exp)
            return new["access_token"]
    except Exception as e:
        logger.warning("etsy: refresh falhou — %s", e)
    return data["token"]


def _etsy_get(path: str, params: dict | None = None) -> dict:
    """GET autenticado à Etsy API v3. Devolve {} em caso de erro."""
    import requests as _req
    token = _get_token()
    if not token:
        return {}
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": f"{ETSY_KEYSTRING}:{ETSY_SHARED_SECRET}" if ETSY_SHARED_SECRET else ETSY_KEYSTRING,
    }
    try:
        r = _req.get(f"https://openapi.etsy.com/v3/application{path}",
                     headers=headers, params=params or {}, timeout=10)
        if r.status_code == 200:
            return r.json()
        logger.warning("etsy GET %s → %s %s", path, r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("etsy GET %s erro: %s", path, e)
    return {}


def _etsy_patch(path: str, payload: dict) -> dict:
    """PATCH autenticado à Etsy API v3."""
    import requests as _req
    token = _get_token()
    if not token:
        return {}
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": f"{ETSY_KEYSTRING}:{ETSY_SHARED_SECRET}" if ETSY_SHARED_SECRET else ETSY_KEYSTRING,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        r = _req.patch(f"https://openapi.etsy.com/v3/application{path}",
                       headers=headers, data=payload, timeout=10)
        if r.status_code in (200, 204):
            return r.json() if r.content else {}
        logger.warning("etsy PATCH %s → %s %s", path, r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("etsy PATCH %s erro: %s", path, e)
    return {}


def get_api():
    """Compatibilidade retroactiva — preferir _etsy_get/_etsy_patch directamente."""
    return bool(_get_token())


def is_configured() -> bool:
    return bool(ETSY_KEYSTRING and TOKENS_FILE.exists())


def obter_vendas(dias: int = 30) -> list:
    """Lista vendas dos últimos N dias."""
    data = _etsy_get(f"/shops/{ETSY_SHOP_ID}/receipts", {"limit": 100, "was_paid": "true"})
    return data.get("results", [])


def obter_listings() -> list:
    """Lista todos os anúncios activos."""
    data = _etsy_get(f"/shops/{ETSY_SHOP_ID}/listings/active", {"limit": 100})
    return data.get("results", [])


def pausar_listing(listing_id: int) -> bool:
    """Pausa um listing (state → inactive)."""
    r = _etsy_patch(f"/shops/{ETSY_SHOP_ID}/listings/{listing_id}", {"state": "inactive"})
    return bool(r)


def activar_listing(listing_id: int) -> bool:
    """Activa um listing pausado (state → active)."""
    r = _etsy_patch(f"/shops/{ETSY_SHOP_ID}/listings/{listing_id}", {"state": "active"})
    return bool(r)


def actualizar_preco(listing_id: int, preco: float) -> bool:
    """Actualiza o preço de um listing (em EUR, sem centavos de arredondamento)."""
    r = _etsy_patch(f"/shops/{ETSY_SHOP_ID}/listings/{listing_id}",
                    {"price": str(round(preco, 2))})
    return bool(r)


def resumo_loja() -> dict:
    """Resumo rápido: vendas totais, receita, nº listings."""
    vendas = obter_vendas()
    listings = obter_listings()

    receita_total = sum(
        float(v.get("grandtotal", {}).get("amount", 0)) / 100
        for v in vendas
        if isinstance(v.get("grandtotal"), dict)
    )
    return {
        "listings_activos": len(listings),
        "vendas_periodo": len(vendas),
        "receita_estimada": round(receita_total, 2),
        "configurado": is_configured(),
    }


def estado_para_operador() -> str:
    """Texto formatado para o Operator usar no seu system prompt."""
    if not is_configured():
        return (
            "Etsy API: não configurada.\n"
            "Para activar: definir ETSY_KEYSTRING e ETSY_SHOP_ID no .env e correr "
            "'python3 etsy_service.py --setup' para OAuth2."
        )
    r = resumo_loja()
    return (
        f"Etsy PlannerAtlas (dados reais):\n"
        f"  Listings activos: {r['listings_activos']}\n"
        f"  Vendas (últimos 30 dias): {r['vendas_periodo']}\n"
        f"  Receita estimada: €{r['receita_estimada']:.2f}"
    )


# ── Setup OAuth2 (CLI, uma vez) ───────────────────────────────────────────────

def setup_oauth():
    """Fluxo PKCE com servidor local para capturar o callback automaticamente."""
    import base64
    import hashlib
    import secrets
    import urllib.parse
    import urllib.request
    import webbrowser
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from datetime import timedelta

    if not ETSY_KEYSTRING:
        print("ERRO: ETSY_KEYSTRING não definido no .env")
        return

    REDIRECT = "http://localhost:3456/callback"
    SCOPES = "listings_r listings_w listings_d transactions_r shops_r"

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    auth_url = (
        "https://www.etsy.com/oauth/connect?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "redirect_uri": REDIRECT,
            "scope": SCOPES,
            "client_id": ETSY_KEYSTRING,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
    )

    captured = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            captured["code"] = params.get("code", "")
            captured["state"] = params.get("state", "")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Autorizado! Podes fechar esta janela.</h2>")
            threading.Thread(target=self.server.shutdown).start()

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 3456), Handler)
    print(f"\nA abrir browser para autorização Etsy...")
    webbrowser.open(auth_url)
    print("Aguarda autorização no browser...\n")
    server.serve_forever()

    code = captured.get("code", "").strip()
    if not code:
        print("ERRO: código não recebido")
        return

    import requests
    r = requests.post(
        "https://api.etsy.com/v3/public/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": ETSY_KEYSTRING,
            "redirect_uri": REDIRECT,
            "code": code,
            "code_verifier": code_verifier,
        },
    )
    if r.status_code != 200:
        print(f"ERRO: {r.text}")
        return

    data = r.json()
    expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    _save_tokens(data["access_token"], data["refresh_token"], expiry)
    print(f"OK — tokens guardados em {TOKENS_FILE}")
    print(f"access_token expira: {expiry.isoformat()}")


if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        setup_oauth()
    else:
        print(estado_para_operador())
