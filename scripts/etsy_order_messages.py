"""
Auto-mensagens pós-compra no Etsy — língua detectada pelo listing comprado.
Corre a cada hora via Operator Agent.
Guarda ordens já processadas em memory/etsy_messaged_orders.json
"""

import sys, os, json, time, requests
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv()

TOKENS_FILE = ROOT / "memory" / "etsy_tokens.json"
MESSAGED_FILE = ROOT / "memory" / "etsy_messaged_orders.json"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY = f"{KEYSTRING}:{SHARED_SECRET}"

# ── Mapeamento listing_id → língua ────────────────────────────────────────────
LISTING_LANG = {}
for lid in [4535134826, 4535131460, 4535117850, 4535122246, 4535113942, 4535113125,
            4546792825, 4546807058, 4546893556, 4546807140, 4546807228, 4546878659]:
    LISTING_LANG[lid] = "EN"
for lid in [4535122419, 4535118477, 4535118376, 4535123160, 4535101803, 4535115041,
            4546893756, 4546878887, 4546879013, 4546879277, 4546879437, 4546894114]:
    LISTING_LANG[lid] = "DE"
for lid in [4535133850, 4535117293, 4535117246, 4535108575, 4535100131, 4535125050,
            4546894554, 4546879695, 4546879847, 4546880181, 4546895218, 4546879995]:
    LISTING_LANG[lid] = "ES"
for lid in [4535133344, 4535130242, 4535116440, 4535120410, 4535112532, 4535110809,
            4546880439, 4546895486, 4546880655, 4546895900, 4546880999, 4546880797]:
    LISTING_LANG[lid] = "PT"

# ── Mensagens por língua ──────────────────────────────────────────────────────
MESSAGES = {
    "EN": """Thank you so much for your purchase! 🌿

Your PlannerAtlas planner is ready to download — go to your Etsy account, click "You" → "Purchases and Reviews" and you'll find it there.

Tips to get started:
• Print on A4 paper, best quality setting
• Works perfectly at any print shop too
• The PDF is ready to use — no editing needed

If you're enjoying your planner, a quick review in "Purchases and Reviews" would mean the world to us — it helps us keep creating beautiful planners! ⭐

Any questions? Just reply here and we'll get back to you within 24h.

Happy planning! ✨
— The PlannerAtlas Team""",

    "DE": """Vielen Dank für deinen Kauf! 🌿

Dein PlannerAtlas Planer ist zum Download bereit — gehe in deinem Etsy-Konto auf "Du" → "Käufe und Bewertungen", dort findest du ihn.

Tipps für den Start:
• Drucke auf A4-Papier mit der besten Qualitätseinstellung
• Funktioniert auch hervorragend in jedem Copyshop
• Die PDF ist sofort einsatzbereit — kein Bearbeiten nötig

Wenn dir dein Planer gefällt, würde eine kurze Bewertung unter "Käufe und Bewertungen" viel für uns bedeuten — sie hilft uns, weiterhin schöne Planer zu erstellen! ⭐

Fragen? Einfach hier antworten, wir melden uns innerhalb von 24h.

Viel Spaß beim Planen! ✨
— Das PlannerAtlas Team""",

    "ES": """¡Muchísimas gracias por tu compra! 🌿

Tu planificador PlannerAtlas está listo para descargar — ve a tu cuenta de Etsy, haz clic en "Tú" → "Compras y reseñas" y lo encontrarás allí.

Consejos para empezar:
• Imprime en papel A4 con la mejor configuración de calidad
• También funciona perfectamente en cualquier copistería
• El PDF está listo para usar — no necesita edición

Si estás disfrutando tu planificador, una reseña rápida en "Compras y reseñas" significaría mucho para nosotros — ¡nos ayuda a seguir creando planificadores bonitos! ⭐

¿Alguna pregunta? Responde aquí y te contestamos en menos de 24h.

¡Feliz planificación! ✨
— El Equipo PlannerAtlas""",

    "PT": """Muito obrigado pela tua compra! 🌿

O teu planeador PlannerAtlas está pronto para descarregar — vai à tua conta Etsy, clica em "Tu" → "Compras e avaliações" e encontras lá.

Dicas para começar:
• Imprime em papel A4 com a melhor definição de qualidade
• Funciona perfeitamente em qualquer gráfica ou loja de impressão
• O PDF está pronto a usar — não precisa de edição

Se estás a gostar do teu planeador, uma avaliação rápida em "Compras e avaliações" significaria muito para nós — ajuda-nos a continuar a criar planeadores bonitos! ⭐

Alguma dúvida? Responde aqui e respondemos em menos de 24h.

Bom planeamento! ✨
— A Equipa PlannerAtlas""",
}

MESSAGES["BUNDLE"] = MESSAGES["EN"]  # bundles em inglês


def get_token():
    data = json.loads(TOKENS_FILE.read_text())
    from datetime import timedelta
    if datetime.now(timezone.utc) < datetime.fromisoformat(data["expiry"]):
        return data["token"]
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type": "refresh_token", "client_id": KEYSTRING, "refresh_token": data["refresh_token"],
    })
    r.raise_for_status()
    new = r.json()
    exp = datetime.now(timezone.utc) + timedelta(seconds=new["expires_in"])
    TOKENS_FILE.write_text(json.dumps({"token": new["access_token"], "refresh_token": new["refresh_token"], "expiry": exp.isoformat()}))
    return new["access_token"]


def hdrs(token, json_ct=False):
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY}
    if json_ct: h["Content-Type"] = "application/json"
    return h


def load_messaged():
    if MESSAGED_FILE.exists():
        return set(json.loads(MESSAGED_FILE.read_text()))
    return set()


def save_messaged(ids: set):
    MESSAGED_FILE.write_text(json.dumps(list(ids)))


def get_new_receipts(token):
    """Busca ordens pagas dos últimos 30 dias."""
    r = requests.get(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/receipts",
        headers=hdrs(token),
        params={"was_paid": True, "limit": 100, "sort_on": "created", "sort_order": "desc"},
    )
    if not r.ok:
        print(f"  ❌ Erro ao buscar ordens: {r.status_code} {r.text[:100]}")
        return []
    return r.json().get("results", [])


def detect_lang(receipt):
    """Detecta língua pela maioria dos listings comprados."""
    lang_count = {}
    for t in receipt.get("transactions", []):
        lid = t.get("listing_id")
        lang = LISTING_LANG.get(lid, "EN")
        lang_count[lang] = lang_count.get(lang, 0) + 1
    if not lang_count:
        return "EN"
    return max(lang_count, key=lang_count.get)


def send_message(token, receipt_id, buyer_user_id, message):
    """Envia mensagem via Etsy Conversations API."""
    # Tentar criar conversa nova com o comprador
    r = requests.post(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/conversations",
        headers=hdrs(token, True),
        json={
            "to_user_id": buyer_user_id,
            "subject": "Your PlannerAtlas Download",
            "message": message,
        },
    )
    if r.ok:
        return True, "conversation"

    # Fallback: tentar via receipt message endpoint
    r2 = requests.post(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/receipts/{receipt_id}/transactions",
        headers=hdrs(token, True),
        json={"message": message},
    )
    return r2.ok, f"receipt_fallback ({r2.status_code})"


def run():
    print(f"=== ETSY ORDER MESSAGES — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    token = get_token()
    messaged = load_messaged()
    receipts = get_new_receipts(token)
    print(f"Ordens encontradas: {len(receipts)}")

    sent = 0
    for receipt in receipts:
        receipt_id = receipt["receipt_id"]
        if receipt_id in messaged:
            continue

        buyer_id = receipt.get("buyer_user_id")
        lang = detect_lang(receipt)
        message = MESSAGES.get(lang, MESSAGES["EN"])

        print(f"\n  Ordem {receipt_id} — comprador {buyer_id} — língua {lang}")
        ok, method = send_message(token, receipt_id, buyer_id, message)
        print(f"  {'✅' if ok else '❌'} Mensagem enviada via {method}")

        if ok:
            messaged.add(receipt_id)
            sent += 1
        time.sleep(1)

    save_messaged(messaged)
    print(f"\nTotal enviadas esta execução: {sent}")
    return sent


if __name__ == "__main__":
    run()
