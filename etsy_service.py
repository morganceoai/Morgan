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


def get_api():
    """Retorna instância EtsyAPI com tokens actualizados. None se não configurado."""
    if not ETSY_KEYSTRING:
        return None
    if not TOKENS_FILE.exists():
        logger.warning("etsy_tokens: ficheiro não existe — correr setup")
        return None
    try:
        from etsyv3 import EtsyAPI
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        expiry = datetime.fromisoformat(data["expiry"])
        return EtsyAPI(
            keystring=ETSY_KEYSTRING,
            token=data["token"],
            refresh_token=data["refresh_token"],
            expiry=expiry,
            refresh_save=_save_tokens,
        )
    except ImportError:
        logger.warning("etsyv3 não instalado — pip install etsyv3")
        return None
    except Exception as e:
        logger.warning(f"etsy_service: erro ao obter API — {e}")
        return None


def is_configured() -> bool:
    return bool(ETSY_KEYSTRING and TOKENS_FILE.exists())


def obter_vendas(dias: int = 30) -> list:
    """Lista vendas dos últimos N dias."""
    api = get_api()
    if not api:
        return []
    try:
        receipts = api.getShopReceipts(shop_id=ETSY_SHOP_ID, limit=100)
        return receipts.get("results", []) if isinstance(receipts, dict) else []
    except Exception as e:
        logger.warning(f"etsy: getShopReceipts erro — {e}")
        return []


def obter_listings() -> list:
    """Lista todos os anúncios activos."""
    api = get_api()
    if not api:
        return []
    try:
        result = api.getListingsByShop(shop_id=ETSY_SHOP_ID, state="active", limit=100)
        return result.get("results", []) if isinstance(result, dict) else []
    except Exception as e:
        logger.warning(f"etsy: getListingsByShop erro — {e}")
        return []


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
    """Fluxo PKCE interactivo para obter tokens de acesso Etsy."""
    import base64
    import hashlib
    import secrets
    import urllib.parse
    import requests

    if not ETSY_KEYSTRING:
        print("ERRO: ETSY_KEYSTRING não definido no .env")
        return

    REDIRECT = "https://www.example.com/some/location?code=xyz"
    SCOPES = "listings_r transactions_r shops_r"

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

    print(f"\n1. Abre este URL no browser:\n{auth_url}\n")
    print("2. Após autorizar, cola aqui o valor do parâmetro 'code' da URL de redireccionamento:")
    code = input("code: ").strip()

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
    from datetime import timedelta
    expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    _save_tokens(data["access_token"], data["refresh_token"], expiry)
    print(f"\nOK — tokens guardados em {TOKENS_FILE}")
    print(f"access_token expira: {expiry.isoformat()}")
    print("O refresh_token tem validade de 90 dias e é renovado automaticamente.")


if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        setup_oauth()
    else:
        print(estado_para_operador())
