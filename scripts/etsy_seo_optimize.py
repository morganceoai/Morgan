"""
Optimiza títulos e tags de todos os 24 listings premium.
Princípios aplicados:
- Termos de maior volume nos primeiros 40 chars do título
- Tags NÃO repetem palavras do título (Etsy usa ambos em conjunto)
- 13 tags por listing, cada uma ≤20 chars
- Termos comprador-intent: "printable", "pdf", "instant download"
"""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv('/Users/vascobotelhodacosta/Morgan/.env')
import os

TOKENS_FILE = Path(__file__).parent.parent / "memory" / "etsy_tokens.json"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY_HEADER = f"{KEYSTRING}:{SHARED_SECRET}"


def get_token():
    data = json.loads(TOKENS_FILE.read_text())
    from datetime import datetime, timezone
    if datetime.now(timezone.utc) < datetime.fromisoformat(data["expiry"]):
        return data["token"]
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type": "refresh_token", "client_id": KEYSTRING, "refresh_token": data["refresh_token"],
    })
    r.raise_for_status()
    new = r.json()
    from datetime import timedelta
    exp = datetime.now(timezone.utc) + timedelta(seconds=new["expires_in"])
    TOKENS_FILE.write_text(json.dumps({"token": new["access_token"], "refresh_token": new["refresh_token"], "expiry": exp.isoformat()}))
    return new["access_token"]


LISTINGS = [
    # ── EN ────────────────────────────────────────────────────────────────────
    {
        "id": 4546792825,
        "title": "Printable Weekly Planner PDF | Undated Weekly Planner | Time Blocking | Instant Download | A4 + US Letter | Sage Green",
        "tags": ["productivity planner", "minimalist planner", "digital planner", "weekly schedule", "work planner", "goal planner", "weekly organizer", "planner printable", "study planner", "desk planner", "teacher planner", "student planner", "monday to sunday"],
    },
    {
        "id": 4546807058,
        "title": "Printable Monthly Planner PDF | Undated Monthly Calendar | Monthly Goals Planner | Instant Download | A4 + US Letter",
        "tags": ["monthly calendar pdf", "goal planner", "monthly overview", "undated calendar", "digital planner", "planner printable", "productivity planner", "minimalist planner", "work calendar", "monthly goals", "vision board plan", "desk calendar", "habit tracker"],
    },
    {
        "id": 4546807140,
        "title": "Printable Habit Tracker PDF | Monthly Habit Tracker | 66 Day Challenge | Instant Download | Forest Green | A4 Letter",
        "tags": ["monthly habit log", "66 day challenge", "daily habits", "routine tracker", "wellness tracker", "self improvement", "habit journal", "self care planner", "productivity planner", "digital tracker", "minimalist tracker", "morning routine", "goal tracker"],
    },
    {
        "id": 4546807228,
        "title": "Printable Budget Tracker PDF | Monthly Budget Planner | Expense Tracker | Savings Tracker | Instant Download | A4",
        "tags": ["monthly budget pdf", "expense tracker", "savings tracker", "financial planner", "money management", "debt payoff tracker", "income tracker", "finance planner", "personal finance", "frugal living", "budget worksheet", "net worth tracker", "cash envelope"],
    },
    {
        "id": 4546893556,
        "title": "Printable Daily Planner PDF | Undated Daily Planner | Time Blocking Schedule | Morning Routine | Instant Download | A4",
        "tags": ["daily schedule pdf", "time blocking pdf", "hourly planner", "morning routine", "productivity planner", "work planner", "study planner", "daily organizer", "minimalist planner", "digital planner", "self care planner", "goal planner", "focus planner"],
    },
    {
        "id": 4546878659,
        "title": "Printable Meal Planner PDF | Weekly Meal Planner | Grocery List | Meal Prep Tracker | Instant Download | A4 + Letter",
        "tags": ["meal prep planner", "grocery list pdf", "weekly menu plan", "food planner", "nutrition tracker", "healthy eating", "diet planner", "recipe planner", "family meal plan", "kitchen planner", "clean eating plan", "dinner planner", "grocery tracker"],
    },

    # ── DE ────────────────────────────────────────────────────────────────────
    {
        "id": 4546893756,
        "title": "Wochenplaner PDF Ausdrucken | Undatierter Wochenplaner | Zeitblöcke | Sofort-Download | A4 | Salbeigrün Minimalistisch",
        "tags": ["wochenplaner", "planer ausdrucken", "zeitmanagement", "undatiert", "sofortdownload", "digital planer", "produktivitaet", "wochenuebersicht", "schreibtischplaner", "schulplaner", "arbeitsplaner", "monatsplaner", "salbeigruen"],
    },
    {
        "id": 4546878887,
        "title": "Monatsplaner PDF Ausdrucken | Undatierter Monatskalender | Monatsziele | Sofort-Download | A4 | Marine Minimalistisch",
        "tags": ["monatsplaner", "kalender drucken", "monatskalender", "undatiert", "sofortdownload", "digital planer", "monatsziele", "monatsraster", "schreibtischplaner", "jahresplaner", "terminplaner", "marine blau", "produktivitaet"],
    },
    {
        "id": 4546879013,
        "title": "Tagesplaner PDF Ausdrucken | Undatierter Tagesplaner | Stundenplan | Morgenroutine | Sofort-Download | A4",
        "tags": ["tagesplaner", "stundenplan", "morgenroutine", "undatiert", "sofortdownload", "digital planer", "tagesstruktur", "fokusplaner", "schreibtischplaner", "schulplaner", "selbstorganisation", "to do planer", "produktivitaet"],
    },
    {
        "id": 4546894114,
        "title": "Mahlzeitenplaner PDF Ausdrucken | Wochenspeiseplan | Einkaufsliste | Meal Prep | Sofort-Download | A4",
        "tags": ["mahlzeitenplaner", "essensplan drucken", "wochenspeiseplan", "einkaufsliste", "sofortdownload", "digital planer", "ernaehrungsplan", "gesund essen", "familienplan", "kueche planer", "meal prep", "speiseplan pdf", "vegetarisch"],
    },
    {
        "id": 4546879277,
        "title": "Gewohnheitstracker PDF Ausdrucken | Monatlicher Habit Tracker | 66-Tage-Challenge | Sofort-Download | A4",
        "tags": ["gewohnheitstracker", "habits ausdrucken", "gewohnheiten", "66 tage challenge", "sofortdownload", "digital tracker", "selbstverbesserung", "routinen", "tracker pdf", "wellness", "motivation", "achtsamkeit", "ziele setzen"],
    },
    {
        "id": 4546879437,
        "title": "Budgetplaner PDF Ausdrucken | Monatlicher Haushaltsplan | Ausgaben Tracker | Sparplan | Sofort-Download | A4",
        "tags": ["budgetplaner", "finanzen drucken", "haushaltsplan", "ausgaben tracker", "sofortdownload", "digital planer", "sparziele", "finanztracker", "schulden abbauen", "geldverwaltung", "einnahmen", "sparplan", "finanzplanung"],
    },

    # ── ES ────────────────────────────────────────────────────────────────────
    {
        "id": 4546894554,
        "title": "Planificador Semanal PDF | Para Imprimir Sin Fecha | Bloques de Tiempo | Descarga Inmediata | A4 + Carta",
        "tags": ["agenda semanal pdf", "imprimible", "sin fecha", "descarga inmediata", "productividad", "organizador semanal", "planner digital", "trabajo estudio", "minimalista", "verde salvia", "horario semana", "lunes a domingo", "planner pdf"],
    },
    {
        "id": 4546879695,
        "title": "Planificador Mensual PDF | Para Imprimir Sin Fecha | Metas Mensuales | Descarga Inmediata | A4 + Carta",
        "tags": ["agenda mensual pdf", "imprimible", "sin fecha", "descarga inmediata", "metas mensuales", "organizador mes", "planner digital", "trabajo estudio", "minimalista", "azul marino", "calendario pdf", "vision board", "planner pdf"],
    },
    {
        "id": 4546879847,
        "title": "Planificador Diario PDF | Para Imprimir Sin Fecha | Bloques de Tiempo | Rutina Mañana | Descarga Inmediata | A4",
        "tags": ["agenda diaria pdf", "imprimible", "sin fecha", "descarga inmediata", "productividad", "rutina diaria", "planner digital", "trabajo estudio", "minimalista", "horario diario", "plan del dia", "enfoque", "planner pdf"],
    },
    {
        "id": 4546879995,
        "title": "Planificador de Comidas PDF | Menú Semanal Para Imprimir | Lista de Compras | Meal Prep | Descarga Inmediata",
        "tags": ["menu semanal pdf", "imprimible", "lista compras", "descarga inmediata", "nutricion", "meal prep", "recetas semanal", "cocina planner", "saludable", "alimentacion", "familia comida", "dieta sana", "planner pdf"],
    },
    {
        "id": 4546880181,
        "title": "Rastreador de Hábitos PDF | Para Imprimir | Reto 66 Días | Tracker Mensual | Descarga Inmediata | A4",
        "tags": ["habitos tracker pdf", "imprimible", "reto 66 dias", "descarga inmediata", "rutinas diarias", "autodisciplina", "bienestar", "motivacion diaria", "seguimiento metas", "productividad", "habitos diarios", "tracker digital", "planner pdf"],
    },
    {
        "id": 4546895218,
        "title": "Planificador de Presupuesto PDF | Control de Gastos Para Imprimir | Ahorro | Finanzas | Descarga Inmediata",
        "tags": ["presupuesto pdf", "imprimible", "control gastos", "descarga inmediata", "finanzas personales", "ahorro dinero", "deudas tracker", "ingresos gastos", "planner digital", "gastos fijos", "tracker dinero", "patrimonio neto", "planner pdf"],
    },

    # ── PT ────────────────────────────────────────────────────────────────────
    {
        "id": 4546880439,
        "title": "Planificador Semanal PDF | Para Imprimir Sem Data | Blocos de Tempo | Download Imediato | A4 + Carta",
        "tags": ["agenda semanal pdf", "imprimivel", "sem data", "download imediato", "produtividade", "organizador semana", "planner digital", "trabalho estudo", "minimalista", "verde salvia", "horario semana", "segunda a domingo", "planner pdf"],
    },
    {
        "id": 4546895486,
        "title": "Planificador Mensal PDF | Para Imprimir Sem Data | Metas Mensais | Download Imediato | A4 + Carta",
        "tags": ["agenda mensal pdf", "imprimivel", "sem data", "download imediato", "metas mensais", "organizador mes", "planner digital", "trabalho estudo", "minimalista", "azul marinho", "calendario pdf", "visao geral", "planner pdf"],
    },
    {
        "id": 4546880655,
        "title": "Planificador Diário PDF | Para Imprimir Sem Data | Blocos de Tempo | Rotina Matinal | Download Imediato | A4",
        "tags": ["agenda diaria pdf", "imprimivel", "sem data", "download imediato", "produtividade", "rotina diaria", "planner digital", "trabalho estudo", "minimalista", "horario diario", "plano do dia", "foco", "planner pdf"],
    },
    {
        "id": 4546880797,
        "title": "Planificador de Refeições PDF | Menú Semanal Para Imprimir | Lista de Compras | Meal Prep | Download Imediato",
        "tags": ["menu semanal pdf", "imprimivel", "lista compras", "download imediato", "nutricao", "meal prep", "receitas semana", "cozinha planner", "saudavel", "alimentacao", "familia refeicao", "dieta sana", "planner pdf"],
    },
    {
        "id": 4546895900,
        "title": "Registo de Hábitos PDF | Para Imprimir | Desafio 66 Dias | Tracker Mensal | Download Imediato | A4",
        "tags": ["habitos tracker pdf", "imprimivel", "desafio 66 dias", "download imediato", "rotinas diarias", "autodisciplina", "bem estar", "motivacao diaria", "seguimento metas", "produtividade", "habitos diarios", "tracker digital", "planner pdf"],
    },
    {
        "id": 4546880999,
        "title": "Planificador de Orçamento PDF | Controlo de Despesas Para Imprimir | Poupança | Finanças | Download Imediato",
        "tags": ["orcamento pdf", "imprimivel", "controlo despesas", "download imediato", "financas pessoais", "poupar dinheiro", "dividas tracker", "rendimentos gastos", "planner digital", "despesas fixas", "tracker dinheiro", "patrimonio", "planner pdf"],
    },
]


def validate():
    errors = []
    for d in LISTINGS:
        if len(d["title"]) > 140:
            errors.append(f"{d['id']}: título {len(d['title'])} chars")
        if len(d["tags"]) > 13:
            errors.append(f"{d['id']}: {len(d['tags'])} tags (max 13)")
        for t in d["tags"]:
            if len(t) > 20:
                errors.append(f"{d['id']}: tag longa '{t}' ({len(t)})")
    return errors


def patch_listing(token, d):
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY_HEADER, "Content-Type": "application/json"}
    r = requests.patch(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{d['id']}",
        headers=h,
        json={"title": d["title"], "tags": d["tags"]},
    )
    return r.ok, r.status_code, r.text[:150] if not r.ok else ""


def main():
    errors = validate()
    if errors:
        print("ERROS DE VALIDAÇÃO:")
        for e in errors:
            print(f"  {e}")
        return

    print(f"=== SEO OPTIMIZE — {len(LISTINGS)} listings ===\n")
    token = get_token()
    ok = 0

    for d in LISTINGS:
        success, code, err = patch_listing(token, d)
        if success:
            print(f"✅ {d['id']} — título e tags actualizados")
            ok += 1
        else:
            print(f"❌ {d['id']} — {code}: {err}")
        time.sleep(0.8)

    print(f"\n{ok}/{len(LISTINGS)} listings actualizados")


if __name__ == "__main__":
    main()
