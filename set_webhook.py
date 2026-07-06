"""Regista o webhook do Telegram antes de arrancar o servidor. Corre no startCommand."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "morgan-production-0486.up.railway.app")
WEBHOOK_URL = f"https://{DOMAIN}/telegram/webhook"

if TOKEN:
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        json={"url": WEBHOOK_URL, "drop_pending_updates": True},
        timeout=10,
    )
    print(f"[set_webhook] {r.json()}")
else:
    print("[set_webhook] TELEGRAM_BOT_TOKEN não encontrado — webhook não registado")
