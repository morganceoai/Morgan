"""
Publica os 18 listings multilingua no Etsy PlannerAtlas.
DE × 6 + ES × 6 + PT × 6
PDFs: scripts/{product}_{lang}.pdf
Imagens/vídeos: reutiliza EN do diretório premium/
"""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv('/Users/vascobotelhodacosta/Morgan/.env')
import os

TOKENS_FILE = Path(__file__).parent.parent / "memory" / "etsy_tokens.json"
SCRIPTS_DIR = Path(__file__).parent
PREMIUM_DIR = Path(__file__).parent.parent / "premium"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY_HEADER = f"{KEYSTRING}:{SHARED_SECRET}"


def get_token():
    data = json.loads(TOKENS_FILE.read_text())
    from datetime import datetime, timezone
    expiry = datetime.fromisoformat(data["expiry"])
    if datetime.now(timezone.utc) < expiry:
        return data["token"]
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": KEYSTRING,
        "refresh_token": data["refresh_token"],
    })
    r.raise_for_status()
    new = r.json()
    from datetime import timedelta
    exp = datetime.now(timezone.utc) + timedelta(seconds=new["expires_in"])
    data2 = {"token": new["access_token"], "refresh_token": new["refresh_token"], "expiry": exp.isoformat()}
    TOKENS_FILE.write_text(json.dumps(data2))
    print("Token renovado")
    return new["access_token"]


def imgs(product_key):
    """Imagens EN partilhadas (sem texto — universais)."""
    p = PREMIUM_DIR / product_key / "EN" / "images"
    files = sorted(p.glob("*.png")) if p.exists() else []
    return files[:3]

def vid(product_key):
    v = PREMIUM_DIR / product_key / "EN" / "video"
    files = sorted(v.glob("*.mp4")) if v.exists() else []
    return files[0] if files else None


LISTINGS = [
    # ── DE ───────────────────────────────────────────────────────────────────
    {
        "slug": "weekly_planner", "lang": "DE",
        "title": "Wochenplaner PDF | Luxus Wochenplaner zum Ausdrucken | Undatiert | Produktivität | Sofort-Download | A4",
        "description": """✨ WOCHENPLANER PREMIUM — Druckbarer PDF Sofort-Download

Gestalte deine Woche mit Eleganz und Intention. Unser luxuriöser Wochenplaner mit Salbeigrün-Akzenten.

🗓 INHALT:
• Jahres- & Monatsübersicht
• Wochenplaner × 4 (mit Zeiteinteilung)
• Gewohnheitstracker
• Stimmungstracker
• Ziele & Vorsätze
• Notizen × 2

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["wochenplaner pdf","wochenplaner drucken","undatiert planer","luxus planer","produktivitaet","sofortdownload","digital planer","wochenuebersicht","premium planer","printable planer"],
        "pdf": SCRIPTS_DIR / "weekly_planner_DE.pdf",
        "img_key": "weekly_planner",
    },
    {
        "slug": "monthly_planner", "lang": "DE",
        "title": "Monatsplaner PDF | Luxus Monatsplaner zum Ausdrucken | Undatiert | Monatskalender | Sofort-Download | A4",
        "description": """✨ MONATSPLANER PREMIUM — Druckbarer PDF Sofort-Download

Behalte den Überblick über deinen gesamten Monat mit unserem eleganten Monatsplaner.

📅 INHALT:
• Jahresübersicht
• Januar–Dezember (12 Seiten)
• Ziele & Vorsätze
• Notizen × 2

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["monatsplaner pdf","monatskalender","undatiert planer","luxus planer","monatsziele","sofortdownload","digital kalender","premium planer","printable planer","zeitmanagement"],
        "pdf": SCRIPTS_DIR / "monthly_planner_DE.pdf",
        "img_key": "monthly_planner",
    },
    {
        "slug": "daily_planner", "lang": "DE",
        "title": "Tagesplaner PDF | Luxus Tagesplaner zum Ausdrucken | Stundenplan | Morgenroutine | Sofort-Download | A4",
        "description": """✨ TAGESPLANER PREMIUM — Druckbarer PDF Sofort-Download

Gestalte jeden Tag mit Absicht. Strukturierter Stundenplan, Morgenroutine und Abendrückblick.

🗓 INHALT:
• Monatsübersicht
• Tagesseiten × 10 (mit Stundenplan)
• Top 3 Prioritäten
• Morgenroutine + Abendrückblick
• Gewohnheitstracker
• Notizen × 2

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["tagesplaner pdf","stundenplan","morgenroutine","luxus planer","undatiert","sofortdownload","tagesstruktur","premium planer","printable planer","produktivitaet"],
        "pdf": SCRIPTS_DIR / "daily_planner_DE.pdf",
        "img_key": "daily_planner",
    },
    {
        "slug": "habit_tracker", "lang": "DE",
        "title": "Gewohnheitstracker PDF | Luxus Habit Tracker zum Ausdrucken | Monatlich | Sofort-Download | A4",
        "description": """✨ GEWOHNHEITSTRACKER PREMIUM — Druckbarer PDF Sofort-Download

Baue nachhaltige Gewohnheiten auf mit unserem luxuriösen Tracker in Waldgrün und Creme.

✅ INHALT:
• Anleitung (How to Use)
• Monatlicher Gewohnheitstracker × 12
• Gewohnheitsrückblick × 2
• Notizen × 2

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["gewohnheitstracker pdf","habit tracker","luxus planer","routinen aufbauen","sofortdownload","selbstverbesserung","premium tracker","printable tracker","gewohnheiten","monatsplaner"],
        "pdf": SCRIPTS_DIR / "habit_tracker_DE.pdf",
        "img_key": "habit_tracker",
    },
    {
        "slug": "budget_planner", "lang": "DE",
        "title": "Budgetplaner PDF | Luxus Haushaltsplaner zum Ausdrucken | Ausgaben Tracker | Finanzplaner | Sofort-Download",
        "description": """✨ BUDGETPLANER PREMIUM — Druckbarer PDF Sofort-Download

Behalte deine Finanzen im Griff mit unserem eleganten Haushaltsplaner.

💰 INHALT:
• Jahresfinanzübersicht
• Monatsbudget × 12
• Schuldentracker
• Sparziele
• Notizen × 2

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["budgetplaner pdf","haushaltsplaner","ausgaben tracker","finanzplaner","luxus planer","sofortdownload","geldverwaltung","sparplan","premium planer","schulden abbauen"],
        "pdf": SCRIPTS_DIR / "budget_planner_DE.pdf",
        "img_key": "budget_tracker",
    },
    {
        "slug": "meal_planner", "lang": "DE",
        "title": "Mahlzeitenplaner PDF | Luxus Essensplaner zum Ausdrucken | Einkaufsliste | Meal Prep | Sofort-Download | A4",
        "description": """✨ MAHLZEITENPLANER PREMIUM — Druckbarer PDF Sofort-Download

Plane deine Mahlzeiten mit Leichtigkeit und Stil.

🍽 INHALT:
• Wochenspeiseplan × 4
• Einkaufsliste × 4
• Vorratsbestand
• Lieblingsrezepte
• Notizen × 2

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["mahlzeitenplaner pdf","essensplaner","einkaufsliste","meal prep","luxus planer","sofortdownload","ernaehrungsplan","wochenplan essen","premium planer","gesund essen"],
        "pdf": SCRIPTS_DIR / "meal_planner_DE.pdf",
        "img_key": "meal_planner",
    },

    # ── ES ───────────────────────────────────────────────────────────────────
    {
        "slug": "weekly_planner", "lang": "ES",
        "title": "Planificador Semanal PDF | Planificador de Lujo para Imprimir | Sin Fecha | Productividad | Descarga Inmediata | A4",
        "description": """✨ PLANIFICADOR SEMANAL PREMIUM — PDF Imprimible Descarga Inmediata

Eleva tu semana con nuestro planificador de lujo en verde salvia y crema.

🗓 INCLUYE:
• Resumen anual y mensual
• Planificador semanal × 4 (con horario)
• Rastreador de hábitos
• Rastreador de humor
• Objetivos e intenciones
• Notas × 2

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador semanal","agenda semanal pdf","planner sin fecha","planificador lujo","productividad","descarga inmediata","planner digital","organizador semana","premium planner","imprimible"],
        "pdf": SCRIPTS_DIR / "weekly_planner_ES.pdf",
        "img_key": "weekly_planner",
    },
    {
        "slug": "monthly_planner", "lang": "ES",
        "title": "Planificador Mensual PDF | Planificador de Lujo para Imprimir | Sin Fecha | Calendario Mensual | Descarga Inmediata",
        "description": """✨ PLANIFICADOR MENSUAL PREMIUM — PDF Imprimible Descarga Inmediata

Visualiza todo tu mes de un vistazo con nuestro elegante planificador.

📅 INCLUYE:
• Resumen anual
• Enero–Diciembre (12 páginas)
• Objetivos e intenciones
• Notas × 2

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador mensual","calendario mensual pdf","planner sin fecha","planificador lujo","metas mensuales","descarga inmediata","organizador mes","premium planner","imprimible","productividad"],
        "pdf": SCRIPTS_DIR / "monthly_planner_ES.pdf",
        "img_key": "monthly_planner",
    },
    {
        "slug": "daily_planner", "lang": "ES",
        "title": "Planificador Diario PDF | Planificador de Lujo para Imprimir | Bloques de Tiempo | Rutina Matutina | Descarga Inmediata",
        "description": """✨ PLANIFICADOR DIARIO PREMIUM — PDF Imprimible Descarga Inmediata

Toma el control de cada hora con nuestro planificador diario de lujo.

🗓 INCLUYE:
• Vista mensual
• Páginas diarias × 10 (con horario)
• Top 3 prioridades
• Rutina matutina + reflexión nocturna
• Rastreador de hábitos
• Notas × 2

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador diario","agenda diaria pdf","bloques de tiempo","rutina matutina","planner lujo","descarga inmediata","horario diario","premium planner","imprimible","productividad"],
        "pdf": SCRIPTS_DIR / "daily_planner_ES.pdf",
        "img_key": "daily_planner",
    },
    {
        "slug": "habit_tracker", "lang": "ES",
        "title": "Rastreador de Hábitos PDF | Habit Tracker de Lujo para Imprimir | Mensual | Descarga Inmediata | A4",
        "description": """✨ RASTREADOR DE HÁBITOS PREMIUM — PDF Imprimible Descarga Inmediata

Construye la vida que quieres, un hábito a la vez.

✅ INCLUYE:
• Cómo usar
• Rastreador mensual × 12
• Revisión de hábitos × 2
• Notas × 2

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["rastreador habitos","habit tracker pdf","planner lujo","rutinas diarias","descarga inmediata","seguimiento habitos","premium tracker","imprimible","autodisciplina","habitos saludables"],
        "pdf": SCRIPTS_DIR / "habit_tracker_ES.pdf",
        "img_key": "habit_tracker",
    },
    {
        "slug": "budget_planner", "lang": "ES",
        "title": "Planificador de Presupuesto PDF | Control Gastos de Lujo para Imprimir | Finanzas Personales | Descarga Inmediata",
        "description": """✨ PLANIFICADOR DE PRESUPUESTO PREMIUM — PDF Imprimible Descarga Inmediata

Toma el control de tus finanzas con claridad y elegancia.

💰 INCLUYE:
• Resumen financiero anual
• Presupuesto mensual × 12
• Control de deudas
• Objetivos de ahorro
• Notas × 2

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["presupuesto mensual","control gastos pdf","finanzas personales","planner lujo","ahorro dinero","descarga inmediata","registro gastos","tracker financiero","premium planner","deuda"],
        "pdf": SCRIPTS_DIR / "budget_planner_ES.pdf",
        "img_key": "budget_tracker",
    },
    {
        "slug": "meal_planner", "lang": "ES",
        "title": "Planificador de Comidas PDF | Menú Semanal de Lujo para Imprimir | Lista Compras | Meal Prep | Descarga Inmediata",
        "description": """✨ PLANIFICADOR DE COMIDAS PREMIUM — PDF Imprimible Descarga Inmediata

Planifica tus comidas con elegancia. Diseño en verde salvia y lino.

🍽 INCLUYE:
• Menú semanal × 4
• Lista de compras × 4
• Inventario de despensa
• Recetas favoritas
• Notas × 2

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador comidas","menu semanal pdf","lista de compras","meal prep","planner lujo","descarga inmediata","plan alimentacion","organizador comidas","premium planner","imprimible"],
        "pdf": SCRIPTS_DIR / "meal_planner_ES.pdf",
        "img_key": "meal_planner",
    },

    # ── PT ───────────────────────────────────────────────────────────────────
    {
        "slug": "weekly_planner", "lang": "PT",
        "title": "Planificador Semanal PDF | Agenda Semanal de Luxo para Imprimir | Sem Data | Produtividade | Download Imediato | A4",
        "description": """✨ PLANIFICADOR SEMANAL PREMIUM — PDF Imprimível Download Imediato

Eleva a tua semana com o nosso planificador de luxo em verde-sálvia e creme.

🗓 INCLUÍDO:
• Visão anual e mensal
• Planeador semanal × 4 (com horário)
• Rastreador de hábitos
• Rastreador de humor
• Objetivos e intenções
• Notas × 2

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador semanal","agenda semanal pdf","planner sem data","planner luxo","produtividade","download imediato","planner digital","organizador semana","premium planner","imprimivel"],
        "pdf": SCRIPTS_DIR / "weekly_planner_PT.pdf",
        "img_key": "weekly_planner",
    },
    {
        "slug": "monthly_planner", "lang": "PT",
        "title": "Planificador Mensal PDF | Agenda Mensal de Luxo para Imprimir | Sem Data | Calendário | Download Imediato | A4",
        "description": """✨ PLANIFICADOR MENSAL PREMIUM — PDF Imprimível Download Imediato

Visualiza todo o teu mês de uma só vez com o nosso elegante planificador.

📅 INCLUÍDO:
• Visão anual
• Janeiro–Dezembro (12 páginas)
• Objetivos e intenções
• Notas × 2

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador mensal","calendario mensal pdf","planner sem data","planner luxo","metas mensais","download imediato","organizador mes","premium planner","imprimivel","produtividade"],
        "pdf": SCRIPTS_DIR / "monthly_planner_PT.pdf",
        "img_key": "monthly_planner",
    },
    {
        "slug": "daily_planner", "lang": "PT",
        "title": "Planificador Diário PDF | Agenda Diária de Luxo para Imprimir | Blocos de Tempo | Rotina Matinal | Download Imediato",
        "description": """✨ PLANIFICADOR DIÁRIO PREMIUM — PDF Imprimível Download Imediato

Toma o controlo de cada hora com o nosso planificador diário de luxo.

🗓 INCLUÍDO:
• Vista mensal
• Páginas diárias × 10 (com horário)
• Top 3 prioridades
• Rotina matinal + reflexão noturna
• Rastreador de hábitos
• Notas × 2

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador diario","agenda diaria pdf","blocos de tempo","rotina matinal","planner luxo","download imediato","horario diario","premium planner","imprimivel","produtividade"],
        "pdf": SCRIPTS_DIR / "daily_planner_PT.pdf",
        "img_key": "daily_planner",
    },
    {
        "slug": "habit_tracker", "lang": "PT",
        "title": "Rastreador de Hábitos PDF | Habit Tracker de Luxo para Imprimir | Mensal | Download Imediato | A4",
        "description": """✨ RASTREADOR DE HÁBITOS PREMIUM — PDF Imprimível Download Imediato

Constrói a vida que queres, um hábito de cada vez.

✅ INCLUÍDO:
• Como usar
• Rastreador mensal × 12
• Revisão de hábitos × 2
• Notas × 2

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["registo habitos","habit tracker pdf","planner luxo","rotinas diarias","download imediato","seguimento habitos","premium tracker","imprimivel","autodisciplina","habitos saudaveis"],
        "pdf": SCRIPTS_DIR / "habit_tracker_PT.pdf",
        "img_key": "habit_tracker",
    },
    {
        "slug": "budget_planner", "lang": "PT",
        "title": "Planificador de Orçamento PDF | Controlo Despesas de Luxo para Imprimir | Finanças Pessoais | Download Imediato",
        "description": """✨ PLANIFICADOR DE ORÇAMENTO PREMIUM — PDF Imprimível Download Imediato

Toma o controlo das tuas finanças com clareza e elegância.

💰 INCLUÍDO:
• Visão financeira anual
• Orçamento mensal × 12
• Controlo de dívidas
• Objetivos de poupança
• Notas × 2

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["orcamento mensal","controlo despesas pdf","financas pessoais","planner luxo","poupar dinheiro","download imediato","registo despesas","tracker financeiro","premium planner","divida"],
        "pdf": SCRIPTS_DIR / "budget_planner_PT.pdf",
        "img_key": "budget_tracker",
    },
    {
        "slug": "meal_planner", "lang": "PT",
        "title": "Planificador de Refeições PDF | Planeador Semanal de Luxo para Imprimir | Lista Compras | Meal Prep | Download Imediato",
        "description": """✨ PLANIFICADOR DE REFEIÇÕES PREMIUM — PDF Imprimível Download Imediato

Planifica as tuas refeições com elegância. Design em verde-sálvia e linho.

🍽 INCLUÍDO:
• Planeador semanal × 4
• Lista de compras × 4
• Inventário da despensa
• Receitas favoritas
• Notas × 2

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador refeicoes","menu semanal pdf","lista de compras","meal prep","planner luxo","download imediato","plano alimentar","organizador comidas","premium planner","imprimivel"],
        "pdf": SCRIPTS_DIR / "meal_planner_PT.pdf",
        "img_key": "meal_planner",
    },
]


def headers(token, json_ct=False):
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY_HEADER}
    if json_ct:
        h["Content-Type"] = "application/json"
    return h


def create_listing(token, d):
    payload = {
        "quantity": 999,
        "title": d["title"][:140],
        "description": d["description"],
        "price": 7.99,
        "who_made": "i_did",
        "when_made": "2020_2026",
        "taxonomy_id": 2078,
        "tags": [t[:20] for t in d["tags"][:13]],
        "is_digital": True,
        "type": "download",
        "state": "draft",
    }
    r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings",
                      headers=headers(token, True), json=payload)
    if not r.ok:
        print(f"  ERRO criar: {r.status_code} {r.text[:200]}")
        return None
    return r.json()["listing_id"]


def upload_pdf(token, lid, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files",
                          headers=headers(token), files={"file": (path.name, f, "application/pdf")},
                          data={"name": path.name, "rank": 1})
    if not r.ok:
        print(f"  ERRO pdf: {r.status_code} {r.text[:200]}")
    else:
        print(f"  PDF ✓")


def upload_image(token, lid, path, rank):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/images",
                          headers=headers(token), files={"image": (path.name, f, "image/png")},
                          data={"rank": rank, "overwrite": True})
    if not r.ok:
        print(f"  ERRO img{rank}: {r.status_code} {r.text[:100]}")
    else:
        print(f"  Img {rank} ✓")


def upload_video(token, lid, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/videos",
                          headers=headers(token), files={"video": (path.name, f, "video/mp4")},
                          data={"name": path.stem})
    if not r.ok:
        print(f"  ERRO vídeo: {r.status_code} {r.text[:200]}")
    else:
        print(f"  Vídeo ✓")


def publish(token, lid):
    r = requests.patch(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                       headers=headers(token, True), json={"state": "active"})
    if not r.ok:
        print(f"  ERRO publicar: {r.status_code} {r.text[:200]}")
        return False
    return True


def main():
    print(f"=== ETSY MULTILANG — {len(LISTINGS)} LISTINGS ===\n")
    token = get_token()
    results = []

    for d in LISTINGS:
        label = f"{d['slug'].upper()} [{d['lang']}]"
        print(f"\n📦 {label}")

        lid = create_listing(token, d)
        if not lid:
            print("  ❌ Falhou")
            continue
        print(f"  Draft ID: {lid}")

        if d["pdf"].exists():
            upload_pdf(token, lid, d["pdf"])
        else:
            print(f"  ⚠️  PDF não existe: {d['pdf']}")

        for i, img in enumerate(imgs(d["img_key"]), 1):
            upload_image(token, lid, img, i)
            time.sleep(0.5)

        v = vid(d["img_key"])
        if v:
            upload_video(token, lid, v)

        time.sleep(1)
        ok = publish(token, lid)
        if ok:
            url = f"https://www.etsy.com/listing/{lid}"
            print(f"  ✅ Publicado: {url}")
            results.append({"produto": f"{d['slug']} {d['lang']}", "id": lid, "url": url})
        time.sleep(2)

    print("\n\n=== RESULTADO FINAL ===")
    for r in results:
        print(f"✅ {r['produto']}: {r['url']}")
    print(f"\nTotal publicados: {len(results)}/{len(LISTINGS)}")


if __name__ == "__main__":
    main()
