"""
Serviço de push notifications para a PWA do Morgan.
Guarda subscrições em JSON e envia via Web Push Protocol (VAPID).
"""
import json
import os
from pathlib import Path
from pywebpush import webpush, WebPushException

BASE_DIR  = Path(__file__).parent
SUBS_FILE = BASE_DIR / "memory" / "push_subscriptions.json"
VAPID_PEM = BASE_DIR / "vapid_private.pem"

VAPID_PUBLIC_KEY = os.getenv(
    "VAPID_PUBLIC_KEY",
    "BM_4MZx5fCE7-Q0W_00gJzuSFOvYL7DMHL8N-AaYfNB-AAm2VgDB_1c2p68yezpFo_l_govnRshnzgpMYmjOYiE"
)
VAPID_CLAIMS = {"sub": "mailto:morganceoai@gmail.com"}


# ── persistência ─────────────────────────────────────────────────────────────

def _load_subs() -> list:
    if not SUBS_FILE.exists():
        return []
    try:
        return json.loads(SUBS_FILE.read_text())
    except Exception:
        return []


def _save_subs(subs: list):
    SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBS_FILE.write_text(json.dumps(subs, indent=2, ensure_ascii=False))


def save_subscription(sub: dict):
    """Guarda ou actualiza uma subscrição (identificada pelo endpoint)."""
    subs = _load_subs()
    endpoint = sub.get("endpoint", "")
    subs = [s for s in subs if s.get("endpoint") != endpoint]
    subs.append(sub)
    _save_subs(subs)


def remove_subscription(endpoint: str):
    subs = [s for s in _load_subs() if s.get("endpoint") != endpoint]
    _save_subs(subs)


# ── envio ────────────────────────────────────────────────────────────────────

def send_push(title: str, body: str, url: str = "/pwa/") -> dict:
    """
    Envia uma notificação push a todas as subscrições guardadas.
    Devolve {"sent": N, "failed": M}.
    """
    subs = _load_subs()
    if not subs:
        return {"sent": 0, "failed": 0}

    payload = json.dumps({"title": title, "body": body, "url": url})
    sent = failed = 0
    to_remove = []

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=str(VAPID_PEM),
                vapid_claims=VAPID_CLAIMS,
            )
            sent += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None) if e.response else None
            if status in (404, 410):
                # subscrição expirou ou foi revogada
                to_remove.append(sub.get("endpoint", ""))
            else:
                failed += 1
        except Exception:
            failed += 1

    for ep in to_remove:
        remove_subscription(ep)

    return {"sent": sent, "failed": failed}
