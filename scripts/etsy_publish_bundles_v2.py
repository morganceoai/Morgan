"""
Apaga 3 bundles antigos (multi-língua) e cria 12 novos (3 bundles × 4 línguas).
"""

import sys, os, json, time, zipfile, requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv()

TOKENS_FILE = ROOT / "memory" / "etsy_tokens.json"
SCRIPTS_DIR = ROOT / "scripts"
PREMIUM_DIR = ROOT / "premium"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY = f"{KEYSTRING}:{SHARED_SECRET}"
BUNDLES_DIR = SCRIPTS_DIR / "_bundles"
BUNDLES_DIR.mkdir(exist_ok=True)

DELETE_IDS = [4547714221, 4547714311, 4547727224]

LANG_META = {
    "EN": {
        "productivity": {
            "title": "Productivity Planner Bundle PDF | Weekly + Daily + Habit Tracker | Undated | Instant Download | A4",
            "description": """✨ PRODUCTIVITY PLANNER BUNDLE — 3 Premium Planners · Instant Download

Everything you need to plan your week, structure your days, and build lasting habits.

📦 INCLUDED (3 PDFs):

🗓 WEEKLY PLANNER: Annual & Monthly Overview · Weekly Planner × 4 · Habit & Mood Tracker · Goals & Intentions · Notes × 2
☀️ DAILY PLANNER: Monthly Overview · Daily Pages × 10 (hourly schedule) · Top 3 Priorities · Morning Routine + Evening Reflection · Notes × 2
✅ HABIT TRACKER: How to Use Guide · Monthly Habit Tracker × 12 · Habit Review × 2 · Notes × 2

📐 A4 PDF · Print at home or at a print shop
⬇️ Instant download — access immediately after purchase

~~€23.97~~ → Save 37%

© PlannerAtlas — Personal use only.""",
            "tags": ["planner bundle pdf","productivity bundle","weekly planner pdf","daily planner pdf","habit tracker pdf","instant download","printable bundle","planner set","luxury planner","undated planner"],
        },
        "finance": {
            "title": "Finance & Meal Planner Bundle PDF | Budget Tracker + Weekly Meal Planner | Instant Download | A4",
            "description": """✨ FINANCE & MEAL PLANNER BUNDLE — 2 Premium Planners · Instant Download

Take control of your money and your meals with our elegantly designed bundle.

📦 INCLUDED (2 PDFs):

💰 BUDGET PLANNER: Annual Financial Overview · Monthly Budget × 12 · Debt Tracker · Savings Goals · Notes × 2
🍽 MEAL PLANNER: Weekly Meal Planner × 4 · Grocery List × 4 · Pantry Inventory · Favourite Recipes · Notes × 2

📐 A4 PDF · Print at home or at a print shop
⬇️ Instant download — access immediately after purchase

~~€15.98~~ → Save 25%

© PlannerAtlas — Personal use only.""",
            "tags": ["budget planner bundle","meal planner bundle","finance planner pdf","grocery list pdf","instant download","printable bundle","budget tracker","meal prep planner","luxury planner","expense tracker"],
        },
        "complete": {
            "title": "Complete Planner Bundle PDF | All 6 Planners | Weekly Monthly Daily Habit Budget Meal | Instant Download | A4",
            "description": """✨ COMPLETE PLANNERATLAS BUNDLE — 6 Premium Planners · Instant Download

The ultimate planning system. Every planner you need to organise your life.

📦 INCLUDED (6 PDFs):
🗓 Weekly Planner · 📅 Monthly Planner · ☀️ Daily Planner
✅ Habit Tracker · 💰 Budget Planner · 🍽 Meal Planner

📐 A4 PDF · Print at home or at a print shop
⬇️ Instant download — 6 files, access immediately after purchase

~~€47.94~~ → Save 48%

© PlannerAtlas — Personal use only.""",
            "tags": ["complete planner bundle","planner bundle pdf","all planners set","instant download","weekly monthly daily","habit budget meal","printable bundle","luxury planner set","productivity bundle","planner collection"],
        },
    },
    "DE": {
        "productivity": {
            "title": "Produktivitäts-Planer Bundle PDF | Wochen- + Tages- + Gewohnheitstracker | Undatiert | Sofort-Download | A4",
            "description": """✨ PRODUKTIVITÄTS-BUNDLE — 3 Premium Planer · Sofort-Download

Alles, was du brauchst, um deine Woche zu planen, deine Tage zu strukturieren und nachhaltige Gewohnheiten aufzubauen.

📦 ENTHALTEN (3 PDFs):

🗓 WOCHENPLANER: Jahres- & Monatsübersicht · Wochenplaner × 4 · Gewohnheits- & Stimmungstracker · Ziele & Vorsätze · Notizen × 2
☀️ TAGESPLANER: Monatsübersicht · Tagesseiten × 10 (Stundenplan) · Top 3 Prioritäten · Morgenroutine + Abendrückblick · Notizen × 2
✅ GEWOHNHEITSTRACKER: Anleitung · Monatlicher Tracker × 12 · Gewohnheitsrückblick × 2 · Notizen × 2

📐 A4 PDF · Zuhause oder im Copyshop drucken
⬇️ Sofort-Download — direkt nach dem Kauf verfügbar

~~€23,97~~ → 37% sparen

© PlannerAtlas — Nur für den persönlichen Gebrauch.""",
            "tags": ["planer bundle pdf","produktivitaet bundle","wochenplaner pdf","tagesplaner pdf","gewohnheitstracker pdf","sofortdownload","druckbares bundle","planer set","luxus planer","undatiert"],
        },
        "finance": {
            "title": "Finanz- & Mahlzeiten-Bundle PDF | Budgetplaner + Mahlzeitenplaner | Sofort-Download | A4",
            "description": """✨ FINANZ- & MAHLZEITEN-BUNDLE — 2 Premium Planer · Sofort-Download

Behalte deine Finanzen und deine Mahlzeiten mit unserem eleganten Bundle im Griff.

📦 ENTHALTEN (2 PDFs):

💰 BUDGETPLANER: Jahresfinanzübersicht · Monatsbudget × 12 · Schuldentracker · Sparziele · Notizen × 2
🍽 MAHLZEITENPLANER: Wochenspeiseplan × 4 · Einkaufsliste × 4 · Vorratsbestand · Lieblingsrezepte · Notizen × 2

📐 A4 PDF · Zuhause oder im Copyshop drucken
⬇️ Sofort-Download — direkt nach dem Kauf verfügbar

~~€15,98~~ → 25% sparen

© PlannerAtlas — Nur für den persönlichen Gebrauch.""",
            "tags": ["budgetplaner bundle","mahlzeitenplaner bundle","finanzplaner pdf","einkaufsliste pdf","sofortdownload","druckbares bundle","ausgaben tracker","meal prep planer","luxus planer","haushaltsplaner"],
        },
        "complete": {
            "title": "Komplettes Planer-Bundle PDF | Alle 6 Planer | Wochen- Monats- Tages- Gewohnheits- Budget- Mahlzeiten | Sofort-Download",
            "description": """✨ KOMPLETTES PLANNERATLAS-BUNDLE — 6 Premium Planer · Sofort-Download

Das ultimative Planungssystem. Alle Planer, die du für ein organisiertes Leben brauchst.

📦 ENTHALTEN (6 PDFs):
🗓 Wochenplaner · 📅 Monatsplaner · ☀️ Tagesplaner
✅ Gewohnheitstracker · 💰 Budgetplaner · 🍽 Mahlzeitenplaner

📐 A4 PDF · Zuhause oder im Copyshop drucken
⬇️ Sofort-Download — 6 Dateien, direkt nach dem Kauf verfügbar

~~€47,94~~ → 48% sparen

© PlannerAtlas — Nur für den persönlichen Gebrauch.""",
            "tags": ["komplettes planer bundle","planer bundle pdf","alle planer set","sofortdownload","wochen monats tages","gewohnheit budget","druckbares bundle","luxus planer set","produktivitaet bundle","planer kollektion"],
        },
    },
    "ES": {
        "productivity": {
            "title": "Bundle Planificador de Productividad PDF | Semanal + Diario + Hábitos | Sin Fecha | Descarga Inmediata | A4",
            "description": """✨ BUNDLE DE PRODUCTIVIDAD — 3 Planificadores Premium · Descarga Inmediata

Todo lo que necesitas para planificar tu semana, estructurar tus días y construir hábitos duraderos.

📦 INCLUIDO (3 PDFs):

🗓 PLANIFICADOR SEMANAL: Resumen anual y mensual · Planeador semanal × 4 · Rastreador de hábitos y humor · Objetivos e intenciones · Notas × 2
☀️ PLANIFICADOR DIARIO: Vista mensual · Páginas diarias × 10 (horario por horas) · Top 3 prioridades · Rutina matutina + reflexión nocturna · Notas × 2
✅ RASTREADOR DE HÁBITOS: Cómo usar · Tracker mensual × 12 · Revisión de hábitos × 2 · Notas × 2

📐 PDF A4 · Imprime en casa o en una copistería
⬇️ Descarga inmediata — accede justo después de la compra

~~€23,97~~ → Ahorra un 37%

© PlannerAtlas — Solo para uso personal.""",
            "tags": ["bundle planificador","productividad bundle","planificador semanal pdf","planificador diario pdf","rastreador habitos pdf","descarga inmediata","bundle imprimible","set planificadores","planner lujo","sin fecha"],
        },
        "finance": {
            "title": "Bundle Finanzas y Comidas PDF | Presupuesto + Planificador de Comidas | Descarga Inmediata | A4",
            "description": """✨ BUNDLE FINANZAS & COMIDAS — 2 Planificadores Premium · Descarga Inmediata

Toma el control de tu dinero y tus comidas con nuestro elegante bundle.

📦 INCLUIDO (2 PDFs):

💰 PLANIFICADOR DE PRESUPUESTO: Resumen financiero anual · Presupuesto mensual × 12 · Control de deudas · Objetivos de ahorro · Notas × 2
🍽 PLANIFICADOR DE COMIDAS: Menú semanal × 4 · Lista de compras × 4 · Inventario despensa · Recetas favoritas · Notas × 2

📐 PDF A4 · Imprime en casa o en una copistería
⬇️ Descarga inmediata — accede justo después de la compra

~~€15,98~~ → Ahorra un 25%

© PlannerAtlas — Solo para uso personal.""",
            "tags": ["bundle presupuesto","bundle comidas","finanzas planificador pdf","lista compras pdf","descarga inmediata","bundle imprimible","control gastos","meal prep planner","planner lujo","ahorro dinero"],
        },
        "complete": {
            "title": "Bundle Completo Planificadores PDF | Los 6 Planificadores | Semanal Mensual Diario Hábitos Presupuesto | Descarga Inmediata",
            "description": """✨ BUNDLE COMPLETO PLANNERATLAS — 6 Planificadores Premium · Descarga Inmediata

El sistema de planificación definitivo. Todos los planificadores que necesitas para organizar tu vida.

📦 INCLUIDO (6 PDFs):
🗓 Semanal · 📅 Mensual · ☀️ Diario
✅ Hábitos · 💰 Presupuesto · 🍽 Comidas

📐 PDF A4 · Imprime en casa o en una copistería
⬇️ Descarga inmediata — 6 archivos, accede justo después de la compra

~~€47,94~~ → Ahorra un 48%

© PlannerAtlas — Solo para uso personal.""",
            "tags": ["bundle completo planners","bundle planificadores pdf","todos los planners","descarga inmediata","semanal mensual diario","habitos presupuesto","bundle imprimible","planner lujo set","productividad bundle","coleccion planners"],
        },
    },
    "PT": {
        "productivity": {
            "title": "Bundle Planificador de Produtividade PDF | Semanal + Diário + Hábitos | Sem Data | Download Imediato | A4",
            "description": """✨ BUNDLE DE PRODUTIVIDADE — 3 Planificadores Premium · Download Imediato

Tudo o que precisas para planear a tua semana, estruturar os teus dias e construir hábitos duradouros.

📦 INCLUÍDO (3 PDFs):

🗓 PLANIFICADOR SEMANAL: Vista anual e mensal · Planeador semanal × 4 · Rastreador de hábitos e humor · Objetivos e intenções · Notas × 2
☀️ PLANIFICADOR DIÁRIO: Vista mensal · Páginas diárias × 10 (horário por horas) · Top 3 prioridades · Rotina matinal + reflexão noturna · Notas × 2
✅ RASTREADOR DE HÁBITOS: Como usar · Tracker mensal × 12 · Revisão de hábitos × 2 · Notas × 2

📐 PDF A4 · Imprime em casa ou numa papelaria
⬇️ Download imediato — acesso imediato após a compra

~~€23,97~~ → Poupa 37%

© PlannerAtlas — Apenas para uso pessoal.""",
            "tags": ["bundle planificador","produtividade bundle","planificador semanal pdf","planificador diario pdf","rastreador habitos pdf","download imediato","bundle imprimivel","set planificadores","planner luxo","sem data"],
        },
        "finance": {
            "title": "Bundle Finanças e Refeições PDF | Orçamento + Planeador de Refeições | Download Imediato | A4",
            "description": """✨ BUNDLE FINANÇAS & REFEIÇÕES — 2 Planificadores Premium · Download Imediato

Toma o controlo das tuas finanças e das tuas refeições com o nosso elegante bundle.

📦 INCLUÍDO (2 PDFs):

💰 PLANIFICADOR DE ORÇAMENTO: Vista financeira anual · Orçamento mensal × 12 · Controlo de dívidas · Objetivos de poupança · Notas × 2
🍽 PLANIFICADOR DE REFEIÇÕES: Planeador semanal × 4 · Lista de compras × 4 · Inventário da despensa · Receitas favoritas · Notas × 2

📐 PDF A4 · Imprime em casa ou numa papelaria
⬇️ Download imediato — acesso imediato após a compra

~~€15,98~~ → Poupa 25%

© PlannerAtlas — Apenas para uso pessoal.""",
            "tags": ["bundle orcamento","bundle refeicoes","financas planificador pdf","lista compras pdf","download imediato","bundle imprimivel","controlo despesas","meal prep planner","planner luxo","poupar dinheiro"],
        },
        "complete": {
            "title": "Bundle Completo Planificadores PDF | Os 6 Planificadores | Semanal Mensal Diário Hábitos Orçamento | Download Imediato",
            "description": """✨ BUNDLE COMPLETO PLANNERATLAS — 6 Planificadores Premium · Download Imediato

O sistema de planeamento definitivo. Todos os planificadores que precisas para organizar a tua vida.

📦 INCLUÍDO (6 PDFs):
🗓 Semanal · 📅 Mensal · ☀️ Diário
✅ Hábitos · 💰 Orçamento · 🍽 Refeições

📐 PDF A4 · Imprime em casa ou numa papelaria
⬇️ Download imediato — 6 ficheiros, acesso imediato após a compra

~~€47,94~~ → Poupa 48%

© PlannerAtlas — Apenas para uso pessoal.""",
            "tags": ["bundle completo planners","bundle planificadores pdf","todos os planners","download imediato","semanal mensal diario","habitos orcamento","bundle imprimivel","planner luxo set","produtividade bundle","colecao planners"],
        },
    },
}

BUNDLE_PRODUCTS = {
    "productivity": ["weekly_planner", "daily_planner", "habit_tracker"],
    "finance":      ["budget_planner", "meal_planner"],
    "complete":     ["weekly_planner", "monthly_planner", "daily_planner", "habit_tracker", "budget_planner", "meal_planner"],
}

BUNDLE_PRICES = {"productivity": 14.99, "finance": 11.99, "complete": 24.99}

BUNDLE_IMG_KEYS = {
    "productivity": ["weekly_planner", "daily_planner", "habit_tracker"],
    "finance":      ["budget_tracker", "meal_planner"],
    "complete":     ["weekly_planner", "monthly_planner", "daily_planner"],
}


def get_token():
    data = json.loads(TOKENS_FILE.read_text())
    from datetime import datetime, timezone, timedelta
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


def delete_listing(token, lid):
    requests.patch(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                   headers=hdrs(token, True), json={"state": "inactive"})
    time.sleep(0.3)
    r = requests.delete(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                        headers=hdrs(token))
    return r.ok or r.status_code == 404


def create_zip(bundle_type, lang):
    zip_name = f"PlannerAtlas_{bundle_type}_{lang}.zip"
    zip_path = BUNDLES_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for product in BUNDLE_PRODUCTS[bundle_type]:
            pdf = SCRIPTS_DIR / f"{product}_{lang}.pdf"
            if pdf.exists():
                zf.write(pdf, pdf.name)
    return zip_path


def create_listing(token, meta, price):
    r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings",
                      headers=hdrs(token, True), json={
        "quantity": 999, "title": meta["title"][:140], "description": meta["description"],
        "price": price, "who_made": "i_did", "when_made": "2020_2026",
        "taxonomy_id": 2078, "tags": [t[:20] for t in meta["tags"][:13]],
        "is_digital": True, "type": "download", "state": "draft",
    })
    if not r.ok:
        print(f"  ❌ {r.status_code} {r.text[:200]}")
        return None
    return r.json()["listing_id"]


def upload_zip(token, lid, zip_path):
    with open(zip_path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files",
                          headers=hdrs(token),
                          files={"file": (zip_path.name, f, "application/zip")},
                          data={"name": zip_path.name, "rank": 1})
    return r.ok


def upload_image(token, lid, img_path, rank):
    with open(img_path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/images",
                          headers=hdrs(token),
                          files={"image": (img_path.name, f, "image/png")},
                          data={"rank": rank, "overwrite": True})
    return r.ok


def publish(token, lid):
    r = requests.patch(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                       headers=hdrs(token, True), json={"state": "active"})
    return r.ok


def main():
    token = get_token()

    # Apagar os 3 antigos
    print("=== APAGAR 3 BUNDLES ANTIGOS ===")
    for lid in DELETE_IDS:
        ok = delete_listing(token, lid)
        print(f"  {'✅' if ok else '❌'} {lid}")
        time.sleep(0.5)

    # Criar 12 novos
    print(f"\n=== CRIAR 12 BUNDLES (3 × 4 línguas) ===")
    results = []

    for lang in ["EN", "DE", "ES", "PT"]:
        for bundle_type in ["productivity", "finance", "complete"]:
            meta = LANG_META[lang][bundle_type]
            price = BUNDLE_PRICES[bundle_type]
            label = f"{bundle_type.upper()} [{lang}]"
            print(f"\n📦 {label}")

            zip_path = create_zip(bundle_type, lang)
            size_kb = zip_path.stat().st_size / 1024
            print(f"  ZIP: {zip_path.name} ({size_kb:.0f} KB)")

            lid = create_listing(token, meta, price)
            if not lid:
                continue
            print(f"  Draft: {lid}")

            if upload_zip(token, lid, zip_path):
                print(f"  ZIP ✓")
            time.sleep(0.5)

            # Imagens EN (mockups são universais)
            for rank, img_key in enumerate(BUNDLE_IMG_KEYS[bundle_type][:3], 1):
                img_dir = PREMIUM_DIR / img_key / "EN" / "images"
                imgs = sorted(img_dir.glob("*.png")) if img_dir.exists() else []
                if imgs:
                    if upload_image(token, lid, imgs[0], rank):
                        print(f"  Img {rank} ✓")
                    time.sleep(0.4)

            time.sleep(0.8)
            if publish(token, lid):
                url = f"https://www.etsy.com/listing/{lid}"
                print(f"  ✅ {url}")
                results.append(f"{label}: {url} (€{price})")
            time.sleep(1.5)

    print(f"\n=== RESULTADO: {len(results)}/12 ===")
    for r in results:
        print(f"  ✅ {r}")


if __name__ == "__main__":
    main()
