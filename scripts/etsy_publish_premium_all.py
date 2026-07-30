"""
Publica os 20 listings premium restantes no Etsy PlannerAtlas.
DE (6) + ES (6) + PT (6) + EN Daily + EN Meal = 20 listings
Reutiliza imagens e vídeos EN (sem texto — universais).
"""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv('/Users/vascobotelhodacosta/Morgan/.env')
import os

TOKENS_FILE = Path(__file__).parent.parent / "memory" / "etsy_tokens.json"
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


LISTINGS = [
    # ── EN (2 em falta) ──────────────────────────────────────────────────────
    {
        "slug": "daily_planner", "lang": "EN",
        "title": "Daily Planner Printable | Luxury Undated Daily Planner PDF | Time Blocking | Morning Routine | Instant Download | A4 Letter",
        "description": """✨ DAILY PLANNER PREMIUM — Printable PDF Instant Download

Take control of every hour with our luxury daily planner. Featuring elegant serif typography, warm burgundy accents, and a thoughtfully structured layout — designed for ambitious professionals who live with intention.

🗓 WHAT'S INCLUDED:
• 10 pages — Undated daily spreads
• Time-blocked schedule (5am–11pm)
• Top 3 priorities section
• Morning intention + evening reflection
• Water intake & mood tracker
• A4 + US Letter sizes in one file

🌍 LANGUAGES AVAILABLE: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved. For personal use only.""",
        "tags": ["daily planner pdf", "time blocking", "undated planner", "luxury planner", "morning routine", "instant download", "productivity planner", "daily schedule", "premium planner", "printable planner"],
        "pdf": PREMIUM_DIR / "daily_planner/EN/pdf/daily_planner_premium_EN.pdf",
        "images": [
            PREMIUM_DIR / "daily_planner/EN/images/daily_01_rose_velvet.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_02_hands_aerial.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_03_closeup.png",
        ],
        "video": PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4",
    },
    {
        "slug": "meal_planner", "lang": "EN",
        "title": "Meal Planner Printable | Luxury Weekly Meal Planner PDF | Grocery List | Meal Prep Tracker | Instant Download | A4 Letter",
        "description": """✨ MEAL PLANNER PREMIUM — Printable PDF Instant Download

Plan your meals with clarity and elegance. Our luxury meal planner features sage green and linen tones, a weekly meal grid, grocery list, and meal prep notes — because nourishing yourself deserves beautiful tools.

🍽 WHAT'S INCLUDED:
• 10 pages — Weekly meal planning spreads
• Breakfast / Lunch / Dinner / Snacks for 7 days
• Grocery shopping list
• Meal prep notes & nutrition tracker
• A4 + US Letter sizes in one file

🌍 LANGUAGES AVAILABLE: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved. For personal use only.""",
        "tags": ["meal planner pdf", "weekly meal plan", "grocery list", "meal prep tracker", "luxury planner", "instant download", "nutrition tracker", "food planner", "premium planner", "printable planner"],
        "pdf": PREMIUM_DIR / "meal_planner/EN/pdf/meal_planner_premium_EN.pdf",
        "images": [
            PREMIUM_DIR / "meal_planner/EN/images/meal_01_marble_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_02_oak_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_03_italian_kitchen.png",
        ],
        "video": PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4",
    },

    # ── DE ────────────────────────────────────────────────────────────────────
    {
        "slug": "weekly_planner", "lang": "DE",
        "title": "Wochenplaner PDF | Luxus Wochenplaner zum Ausdrucken | Undatiert | Produktivität | Sofort-Download | A4",
        "description": """✨ WOCHENPLANER PREMIUM — Druckbarer PDF Sofort-Download

Gestalte deine Woche mit Eleganz und Intention. Unser luxuriöser Wochenplaner mit Salbeigrün-Akzenten und edler Serifenschrift.

🗓 INHALT:
• 12 Seiten — Undatierte Wochenspreads (Mo–So)
• Tagesblöcke mit Zeiteinteilung
• Prioritäten- und Zielbereich
• Notizen & Reflexion
• A4 + US Letter in einer Datei

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten. Nur für den persönlichen Gebrauch.""",
        "tags": ["wochenplaner pdf", "wochenplaner drucken", "undatiert planer", "luxus planer", "produktivitaet", "sofortdownload", "digital planer", "wochenuebersicht", "premium planer", "printable planer"],
        "pdf": PREMIUM_DIR / "weekly_planner/DE/pdf/weekly_planner_premium_DE.pdf",
        "images": [
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_01_marble_dark.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_02_closeup.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_03_hands.png",
        ],
        "video": PREMIUM_DIR / "weekly_planner/EN/video/weekly_premium_EN.mp4",
    },
    {
        "slug": "monthly_planner", "lang": "DE",
        "title": "Monatsplaner PDF | Luxus Monatsplaner zum Ausdrucken | Undatiert | Monatskalender | Sofort-Download | A4",
        "description": """✨ MONATSPLANER PREMIUM — Druckbarer PDF Sofort-Download

Behalte den Überblick über deinen gesamten Monat mit unserem eleganten Monatsplaner in Marineblau und Creme.

📅 INHALT:
• 10 Seiten — Undatierte Monatsraster
• Vollständiges Monatsgitter mit Notizenspalte
• Monatsziele & Vorsätze
• Wichtige Termine & Ereignisse
• A4 + US Letter in einer Datei

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["monatsplaner pdf", "monatskalender", "undatiert planer", "luxus planer", "monatsziele", "sofortdownload", "digital kalender", "premium planer", "printable planer", "zeitmanagement"],
        "pdf": PREMIUM_DIR / "monthly_planner/DE/pdf/monthly_planner_premium_DE.pdf",
        "images": [
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_01_marble_dark.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_02_closeup.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_03_aerial_linen.png",
        ],
        "video": PREMIUM_DIR / "monthly_planner/EN/video/monthly_premium_EN.mp4",
    },
    {
        "slug": "daily_planner", "lang": "DE",
        "title": "Tagesplaner PDF | Luxus Tagesplaner zum Ausdrucken | Stundenplan | Morgenroutine | Sofort-Download | A4",
        "description": """✨ TAGESPLANER PREMIUM — Druckbarer PDF Sofort-Download

Gestalte jeden Tag mit Absicht. Unser luxuriöser Tagesplaner mit Burgunderrot-Akzenten und strukturiertem Stundenplan.

🗓 INHALT:
• 10 Seiten — Undatierte Tagesseiten
• Stundenplan 5–23 Uhr
• Top 3 Prioritäten
• Morgenintention + Abendrückblick
• Wasser- & Stimmungstracker
• A4 + US Letter in einer Datei

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["tagesplaner pdf", "stundenplan", "morgenroutine", "luxus planer", "undatiert", "sofortdownload", "tagesstruktur", "premium planer", "printable planer", "produktivitaet"],
        "pdf": PREMIUM_DIR / "daily_planner/DE/pdf/daily_planner_premium_DE.pdf",
        "images": [
            PREMIUM_DIR / "daily_planner/EN/images/daily_01_rose_velvet.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_02_hands_aerial.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_03_closeup.png",
        ],
        "video": PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4",
    },
    {
        "slug": "meal_planner", "lang": "DE",
        "title": "Mahlzeitenplaner PDF | Luxus Essensplaner zum Ausdrucken | Einkaufsliste | Meal Prep | Sofort-Download | A4",
        "description": """✨ MAHLZEITENPLANER PREMIUM — Druckbarer PDF Sofort-Download

Plane deine Mahlzeiten mit Leichtigkeit und Stil. Salbeigrün und Leinen-Design für bewusste Ernährung.

🍽 INHALT:
• 10 Seiten — Wöchentliche Mahlzeitenplanung
• Frühstück / Mittagessen / Abendessen / Snacks (7 Tage)
• Einkaufsliste
• Meal-Prep Notizen
• A4 + US Letter in einer Datei

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["mahlzeitenplaner pdf", "essensplaner", "einkaufsliste", "meal prep", "luxus planer", "sofortdownload", "ernaehrungsplan", "wochenplan essen", "premium planer", "gesund essen"],
        "pdf": PREMIUM_DIR / "meal_planner/DE/pdf/meal_planner_premium_DE.pdf",
        "images": [
            PREMIUM_DIR / "meal_planner/EN/images/meal_01_marble_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_02_oak_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_03_italian_kitchen.png",
        ],
        "video": PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4",
    },
    {
        "slug": "habit_tracker", "lang": "DE",
        "title": "Gewohnheitstracker PDF | Luxus Habit Tracker zum Ausdrucken | 66-Tage-Challenge | Sofort-Download | A4",
        "description": """✨ GEWOHNHEITSTRACKER PREMIUM — Druckbarer PDF Sofort-Download

Baue nachhaltige Gewohnheiten auf mit unserem luxuriösen Tracker in Waldgrün und Creme.

✅ INHALT:
• 8 Seiten — Monatliche Gewohnheitsraster
• Bis zu 20 Gewohnheiten pro Monat
• 66-Tage-Challenge-Tracker
• Wöchentliche Reflexion
• A4 + US Letter in einer Datei

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["gewohnheitstracker pdf", "habit tracker", "66 tage challenge", "luxus planer", "routinen aufbauen", "sofortdownload", "selbstverbesserung", "premium tracker", "printable tracker", "gewohnheiten"],
        "pdf": PREMIUM_DIR / "habit_tracker/DE/pdf/habit_tracker_premium_DE.pdf",
        "images": [
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_aerial_green.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_closeup.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_03_green_leather.png",
        ],
        "video": PREMIUM_DIR / "habit_tracker/EN/video/habit_premium_EN.mp4",
    },
    {
        "slug": "budget_tracker", "lang": "DE",
        "title": "Budgetplaner PDF | Luxus Haushaltsplaner zum Ausdrucken | Ausgaben Tracker | Finanzplaner | Sofort-Download",
        "description": """✨ BUDGETPLANER PREMIUM — Druckbarer PDF Sofort-Download

Behalte deine Finanzen im Griff mit unserem eleganten Budgetplaner in Anthrazit und Gold.

💰 INHALT:
• 10 Seiten — Monatliche Budgetseiten
• Einkommenserfassung (mehrere Quellen)
• Feste & variable Ausgaben
• Sparziele-Tracker
• Nettovermögensübersicht
• A4 + US Letter in einer Datei

🌍 SPRACHEN: Englisch · Deutsch · Spanisch · Portugiesisch

© PlannerAtlas — Alle Rechte vorbehalten.""",
        "tags": ["budgetplaner pdf", "haushaltsplaner", "ausgaben tracker", "finanzplaner", "luxus planer", "sofortdownload", "geldverwaltung", "sparplan", "premium planer", "schulden abbauen"],
        "pdf": PREMIUM_DIR / "budget_tracker/DE/pdf/budget_tracker_premium_DE.pdf",
        "images": [
            PREMIUM_DIR / "budget_tracker/EN/images/budget_01_walnut_moody.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_02_hands.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_03_marble_aerial.png",
        ],
        "video": PREMIUM_DIR / "budget_tracker/EN/video/budget_premium_EN.mp4",
    },

    # ── ES ────────────────────────────────────────────────────────────────────
    {
        "slug": "weekly_planner", "lang": "ES",
        "title": "Planificador Semanal PDF | Planificador de Lujo para Imprimir | Sin Fecha | Productividad | Descarga Inmediata | A4",
        "description": """✨ PLANIFICADOR SEMANAL PREMIUM — PDF Imprimible Descarga Inmediata

Eleva tu semana con nuestro planificador de lujo. Diseño minimalista en verde salvia y crema con tipografía serif elegante.

🗓 INCLUYE:
• 12 páginas — Spreads semanales sin fecha (Lun–Dom)
• Columnas de tiempo bloqueado
• Sección de prioridades y metas
• Notas y reflexiones
• A4 + Carta US en un archivo

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados. Solo para uso personal.""",
        "tags": ["planificador semanal", "agenda semanal pdf", "planner sin fecha", "planificador lujo", "productividad", "descarga inmediata", "planner digital", "organizador semana", "premium planner", "imprimible"],
        "pdf": PREMIUM_DIR / "weekly_planner/ES/pdf/weekly_planner_premium_ES.pdf",
        "images": [
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_01_marble_dark.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_02_closeup.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_03_hands.png",
        ],
        "video": PREMIUM_DIR / "weekly_planner/EN/video/weekly_premium_EN.mp4",
    },
    {
        "slug": "monthly_planner", "lang": "ES",
        "title": "Planificador Mensual PDF | Planificador de Lujo para Imprimir | Sin Fecha | Calendario Mensual | Descarga Inmediata",
        "description": """✨ PLANIFICADOR MENSUAL PREMIUM — PDF Imprimible Descarga Inmediata

Visualiza todo tu mes de un vistazo con nuestro elegante planificador en azul marino y crema.

📅 INCLUYE:
• 10 páginas — Cuadrículas mensuales sin fecha
• Cuadrícula completa con columna de notas
• Página de metas mensuales
• Fechas importantes y eventos
• A4 + Carta US en un archivo

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador mensual", "calendario mensual pdf", "planner sin fecha", "planificador lujo", "metas mensuales", "descarga inmediata", "organizador mes", "premium planner", "imprimible", "productividad"],
        "pdf": PREMIUM_DIR / "monthly_planner/ES/pdf/monthly_planner_premium_ES.pdf",
        "images": [
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_01_marble_dark.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_02_closeup.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_03_aerial_linen.png",
        ],
        "video": PREMIUM_DIR / "monthly_planner/EN/video/monthly_premium_EN.mp4",
    },
    {
        "slug": "daily_planner", "lang": "ES",
        "title": "Planificador Diario PDF | Planificador de Lujo para Imprimir | Bloques de Tiempo | Rutina Matutina | Descarga Inmediata",
        "description": """✨ PLANIFICADOR DIARIO PREMIUM — PDF Imprimible Descarga Inmediata

Toma el control de cada hora con nuestro planificador diario de lujo en burdeos y crema.

🗓 INCLUYE:
• 10 páginas — Spreads diarios sin fecha
• Horario por horas (5am–11pm)
• Top 3 prioridades
• Intención matutina + reflexión nocturna
• Registro de agua y estado de ánimo
• A4 + Carta US en un archivo

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador diario", "agenda diaria pdf", "bloques de tiempo", "rutina matutina", "planner lujo", "descarga inmediata", "horario diario", "premium planner", "imprimible", "productividad"],
        "pdf": PREMIUM_DIR / "daily_planner/ES/pdf/daily_planner_premium_ES.pdf",
        "images": [
            PREMIUM_DIR / "daily_planner/EN/images/daily_01_rose_velvet.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_02_hands_aerial.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_03_closeup.png",
        ],
        "video": PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4",
    },
    {
        "slug": "meal_planner", "lang": "ES",
        "title": "Planificador de Comidas PDF | Menú Semanal de Lujo para Imprimir | Lista Compras | Meal Prep | Descarga Inmediata",
        "description": """✨ PLANIFICADOR DE COMIDAS PREMIUM — PDF Imprimible Descarga Inmediata

Planifica tus comidas con elegancia. Diseño en verde salvia y lino para una alimentación consciente.

🍽 INCLUYE:
• 10 páginas — Planificación semanal de comidas
• Desayuno / Almuerzo / Cena / Snacks (7 días)
• Lista de compras
• Notas de preparación y nutrición
• A4 + Carta US en un archivo

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["planificador comidas", "menu semanal pdf", "lista de compras", "meal prep", "planner lujo", "descarga inmediata", "plan alimentacion", "organizador comidas", "premium planner", "imprimible"],
        "pdf": PREMIUM_DIR / "meal_planner/ES/pdf/meal_planner_premium_ES.pdf",
        "images": [
            PREMIUM_DIR / "meal_planner/EN/images/meal_01_marble_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_02_oak_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_03_italian_kitchen.png",
        ],
        "video": PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4",
    },
    {
        "slug": "habit_tracker", "lang": "ES",
        "title": "Rastreador de Hábitos PDF | Habit Tracker de Lujo para Imprimir | Reto 66 Días | Descarga Inmediata | A4",
        "description": """✨ RASTREADOR DE HÁBITOS PREMIUM — PDF Imprimible Descarga Inmediata

Construye la vida que quieres, un hábito a la vez. Diseño en verde bosque y crema.

✅ INCLUYE:
• 8 páginas — Cuadrículas mensuales de hábitos
• Hasta 20 hábitos por mes
• Reto de 66 días
• Reflexión semanal y rachas
• A4 + Carta US en un archivo

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["rastreador habitos", "habit tracker pdf", "reto 66 dias", "planner lujo", "rutinas diarias", "descarga inmediata", "seguimiento habitos", "premium tracker", "imprimible", "autodisciplina"],
        "pdf": PREMIUM_DIR / "habit_tracker/ES/pdf/habit_tracker_premium_ES.pdf",
        "images": [
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_aerial_green.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_closeup.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_03_green_leather.png",
        ],
        "video": PREMIUM_DIR / "habit_tracker/EN/video/habit_premium_EN.mp4",
    },
    {
        "slug": "budget_tracker", "lang": "ES",
        "title": "Planificador de Presupuesto PDF | Control Gastos de Lujo para Imprimir | Finanzas Personales | Descarga Inmediata",
        "description": """✨ PLANIFICADOR DE PRESUPUESTO PREMIUM — PDF Imprimible Descarga Inmediata

Toma el control de tus finanzas con claridad y elegancia. Diseño en antracita y dorado.

💰 INCLUYE:
• 10 páginas — Spreads mensuales de presupuesto
• Registro de ingresos (múltiples fuentes)
• Gastos fijos y variables
• Seguimiento de metas de ahorro
• Resumen de patrimonio neto
• A4 + Carta US en un archivo

🌍 IDIOMAS: Inglés · Alemán · Español · Portugués

© PlannerAtlas — Todos los derechos reservados.""",
        "tags": ["presupuesto mensual", "control gastos pdf", "finanzas personales", "planner lujo", "ahorro dinero", "descarga inmediata", "registro gastos", "tracker financiero", "premium planner", "deuda"],
        "pdf": PREMIUM_DIR / "budget_tracker/ES/pdf/budget_tracker_premium_ES.pdf",
        "images": [
            PREMIUM_DIR / "budget_tracker/EN/images/budget_01_walnut_moody.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_02_hands.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_03_marble_aerial.png",
        ],
        "video": PREMIUM_DIR / "budget_tracker/EN/video/budget_premium_EN.mp4",
    },

    # ── PT ────────────────────────────────────────────────────────────────────
    {
        "slug": "weekly_planner", "lang": "PT",
        "title": "Planificador Semanal PDF | Agenda Semanal de Luxo para Imprimir | Sem Data | Produtividade | Download Imediato | A4",
        "description": """✨ PLANIFICADOR SEMANAL PREMIUM — PDF Imprimível Download Imediato

Eleva a tua semana com o nosso planificador de luxo. Design minimalista em verde-sálvia e creme com tipografia serif elegante.

🗓 INCLUÍDO:
• 12 páginas — Spreads semanais sem data (Seg–Dom)
• Colunas de tempo bloqueado
• Secção de prioridades e metas
• Notas e reflexões
• A4 + Carta US num único ficheiro

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados. Apenas para uso pessoal.""",
        "tags": ["planificador semanal", "agenda semanal pdf", "planner sem data", "planner luxo", "produtividade", "download imediato", "planner digital", "organizador semana", "premium planner", "imprimivel"],
        "pdf": PREMIUM_DIR / "weekly_planner/PT/pdf/weekly_planner_premium_PT.pdf",
        "images": [
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_01_marble_dark.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_02_closeup.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_03_hands.png",
        ],
        "video": PREMIUM_DIR / "weekly_planner/EN/video/weekly_premium_EN.mp4",
    },
    {
        "slug": "monthly_planner", "lang": "PT",
        "title": "Planificador Mensal PDF | Agenda Mensal de Luxo para Imprimir | Sem Data | Calendário | Download Imediato | A4",
        "description": """✨ PLANIFICADOR MENSAL PREMIUM — PDF Imprimível Download Imediato

Visualiza todo o teu mês de uma só vez com o nosso elegante planificador em azul-marinho e creme.

📅 INCLUÍDO:
• 10 páginas — Grelhas mensais sem data
• Grelha completa com coluna de notas
• Página de metas mensais
• Datas importantes e eventos
• A4 + Carta US num único ficheiro

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador mensal", "calendario mensal pdf", "planner sem data", "planner luxo", "metas mensais", "download imediato", "organizador mes", "premium planner", "imprimivel", "produtividade"],
        "pdf": PREMIUM_DIR / "monthly_planner/PT/pdf/monthly_planner_premium_PT.pdf",
        "images": [
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_01_marble_dark.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_02_closeup.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_03_aerial_linen.png",
        ],
        "video": PREMIUM_DIR / "monthly_planner/EN/video/monthly_premium_EN.mp4",
    },
    {
        "slug": "daily_planner", "lang": "PT",
        "title": "Planificador Diário PDF | Agenda Diária de Luxo para Imprimir | Blocos de Tempo | Rotina Matinal | Download Imediato",
        "description": """✨ PLANIFICADOR DIÁRIO PREMIUM — PDF Imprimível Download Imediato

Toma o controlo de cada hora com o nosso planificador diário de luxo em bordô e creme.

🗓 INCLUÍDO:
• 10 páginas — Spreads diários sem data
• Horário por horas (5h–23h)
• Top 3 prioridades
• Intenção matinal + reflexão noturna
• Registo de água e estado de espírito
• A4 + Carta US num único ficheiro

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador diario", "agenda diaria pdf", "blocos de tempo", "rotina matinal", "planner luxo", "download imediato", "horario diario", "premium planner", "imprimivel", "produtividade"],
        "pdf": PREMIUM_DIR / "daily_planner/PT/pdf/daily_planner_premium_PT.pdf",
        "images": [
            PREMIUM_DIR / "daily_planner/EN/images/daily_01_rose_velvet.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_02_hands_aerial.png",
            PREMIUM_DIR / "daily_planner/EN/images/daily_03_closeup.png",
        ],
        "video": PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4",
    },
    {
        "slug": "meal_planner", "lang": "PT",
        "title": "Planificador de Refeições PDF | Menu Semanal de Luxo para Imprimir | Lista Compras | Meal Prep | Download Imediato",
        "description": """✨ PLANIFICADOR DE REFEIÇÕES PREMIUM — PDF Imprimível Download Imediato

Planifica as tuas refeições com elegância. Design em verde-sálvia e linho para uma alimentação consciente.

🍽 INCLUÍDO:
• 10 páginas — Planeamento semanal de refeições
• Pequeno-almoço / Almoço / Jantar / Snacks (7 dias)
• Lista de compras
• Notas de preparação e nutrição
• A4 + Carta US num único ficheiro

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["planificador refeicoes", "menu semanal pdf", "lista de compras", "meal prep", "planner luxo", "download imediato", "plano alimentar", "organizador comidas", "premium planner", "imprimivel"],
        "pdf": PREMIUM_DIR / "meal_planner/PT/pdf/meal_planner_premium_PT.pdf",
        "images": [
            PREMIUM_DIR / "meal_planner/EN/images/meal_01_marble_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_02_oak_kitchen.png",
            PREMIUM_DIR / "meal_planner/EN/images/meal_03_italian_kitchen.png",
        ],
        "video": PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4",
    },
    {
        "slug": "habit_tracker", "lang": "PT",
        "title": "Registo de Hábitos PDF | Habit Tracker de Luxo para Imprimir | Desafio 66 Dias | Download Imediato | A4",
        "description": """✨ REGISTO DE HÁBITOS PREMIUM — PDF Imprimível Download Imediato

Constrói a vida que queres, um hábito de cada vez. Design em verde-floresta e creme.

✅ INCLUÍDO:
• 8 páginas — Grelhas mensais de hábitos
• Até 20 hábitos por mês
• Desafio de 66 dias
• Reflexão semanal e sequências
• A4 + Carta US num único ficheiro

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["registo habitos", "habit tracker pdf", "desafio 66 dias", "planner luxo", "rotinas diarias", "download imediato", "seguimento habitos", "premium tracker", "imprimivel", "autodisciplina"],
        "pdf": PREMIUM_DIR / "habit_tracker/PT/pdf/habit_tracker_premium_PT.pdf",
        "images": [
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_aerial_green.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_closeup.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_03_green_leather.png",
        ],
        "video": PREMIUM_DIR / "habit_tracker/EN/video/habit_premium_EN.mp4",
    },
    {
        "slug": "budget_tracker", "lang": "PT",
        "title": "Planificador de Orçamento PDF | Controlo Despesas de Luxo para Imprimir | Finanças Pessoais | Download Imediato",
        "description": """✨ PLANIFICADOR DE ORÇAMENTO PREMIUM — PDF Imprimível Download Imediato

Toma o controlo das tuas finanças com clareza e elegância. Design em antracite e dourado.

💰 INCLUÍDO:
• 10 páginas — Spreads mensais de orçamento
• Registo de rendimentos (múltiplas fontes)
• Despesas fixas e variáveis
• Acompanhamento de metas de poupança
• Visão geral do património líquido
• A4 + Carta US num único ficheiro

🌍 IDIOMAS: Inglês · Alemão · Espanhol · Português

© PlannerAtlas — Todos os direitos reservados.""",
        "tags": ["orcamento mensal", "controlo despesas pdf", "financas pessoais", "planner luxo", "poupar dinheiro", "download imediato", "registo despesas", "tracker financeiro", "premium planner", "divida"],
        "pdf": PREMIUM_DIR / "budget_tracker/PT/pdf/budget_tracker_premium_PT.pdf",
        "images": [
            PREMIUM_DIR / "budget_tracker/EN/images/budget_01_walnut_moody.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_02_hands.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_03_marble_aerial.png",
        ],
        "video": PREMIUM_DIR / "budget_tracker/EN/video/budget_premium_EN.mp4",
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
    print(f"=== ETSY PREMIUM — {len(LISTINGS)} LISTINGS ===\n")
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

        for i, img in enumerate(d["images"], 1):
            if img.exists():
                upload_image(token, lid, img, i)
                time.sleep(0.5)
            else:
                print(f"  ⚠️  Img não existe: {img}")

        if d.get("video") and d["video"].exists():
            upload_video(token, lid, d["video"])

        time.sleep(1)
        ok = publish(token, lid)
        if ok:
            print(f"  ✅ Publicado: https://www.etsy.com/listing/{lid}")
            results.append({"produto": f"{d['slug']} {d['lang']}", "id": lid,
                            "url": f"https://www.etsy.com/listing/{lid}"})
        time.sleep(2)

    print("\n\n=== RESULTADO FINAL ===")
    for r in results:
        print(f"✅ {r['produto']}: {r['url']}")
    print(f"\nTotal publicados: {len(results)}/{len(LISTINGS)}")
    return results


if __name__ == "__main__":
    main()
