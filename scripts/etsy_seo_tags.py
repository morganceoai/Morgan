"""
Actualiza títulos e tags de todos os 48 listings individuais.
Low-cost → keywords de volume/descoberta
Premium → keywords de qualidade/luxo/intenção de compra
"""

import sys, os, json, time, requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv()

TOKENS_FILE = ROOT / "memory" / "etsy_tokens.json"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY = f"{KEYSTRING}:{SHARED_SECRET}"


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


def hdrs(token):
    return {"Authorization": f"Bearer {token}", "x-api-key": API_KEY, "Content-Type": "application/json"}


def update(token, lid, title, tags):
    r = requests.patch(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
        headers=hdrs(token),
        json={"title": title[:140], "tags": [t[:20] for t in tags[:13]]},
    )
    return r.ok, r.status_code


# ── LOW-COST listings ─────────────────────────────────────────────────────────
LOWCOST = {
    4535134826: {"title": "Printable Weekly Planner PDF | Simple Undated Weekly Schedule | Habit Tracker | A4 Letter | Instant Download", "tags": ["printable planner","weekly planner pdf","simple planner","undated planner","instant download","planner template","weekly schedule","habit tracker","a4 planner","printable weekly"]},
    4535131460: {"title": "Printable Monthly Planner PDF | Simple Undated Monthly Calendar | Goals & Notes | A4 Letter | Instant Download", "tags": ["printable planner","monthly planner pdf","monthly calendar","undated planner","instant download","planner template","monthly goals","simple planner","a4 planner","printable monthly"]},
    4535117850: {"title": "Printable Daily Planner PDF | Simple Undated Daily Schedule | Time Blocking | A4 Letter | Instant Download", "tags": ["printable planner","daily planner pdf","daily schedule","time blocking","undated planner","instant download","planner template","hourly planner","simple planner","a4 planner"]},
    4535122246: {"title": "Printable Habit Tracker PDF | Simple Monthly Habit Tracker | 66 Day Challenge | A4 Letter | Instant Download", "tags": ["habit tracker pdf","printable tracker","monthly habits","66 day challenge","instant download","habit tracker","routine tracker","simple tracker","a4 tracker","habit journal"]},
    4535113942: {"title": "Printable Budget Planner PDF | Simple Monthly Budget Tracker | Expense Tracker | A4 Letter | Instant Download", "tags": ["budget planner pdf","printable budget","expense tracker","monthly budget","instant download","budget tracker","money planner","simple budget","a4 planner","finance tracker"]},
    4535113125: {"title": "Printable Meal Planner PDF | Simple Weekly Meal Plan | Grocery List | A4 Letter | Instant Download", "tags": ["meal planner pdf","printable meal plan","grocery list","weekly meal plan","instant download","meal prep planner","simple planner","food planner","a4 planner","shopping list"]},
    4535122419: {"title": "Druckbarer Wochenplaner PDF | Einfacher Undatierter Wochenplan | Gewohnheitstracker | A4 | Sofort-Download", "tags": ["wochenplaner pdf","druckbarer planer","einfacher planer","undatiert","sofortdownload","planer vorlage","wochenplan","gewohnheitstracker","a4 planer","druckbar"]},
    4535118477: {"title": "Druckbarer Monatsplaner PDF | Einfacher Undatierter Monatskalender | Ziele | A4 | Sofort-Download", "tags": ["monatsplaner pdf","druckbarer planer","monatskalender","undatiert","sofortdownload","planer vorlage","monatsziele","einfacher planer","a4 planer","druckbar"]},
    4535118376: {"title": "Druckbarer Tagesplaner PDF | Einfacher Undatierter Tagesplan | Stundenplan | A4 | Sofort-Download", "tags": ["tagesplaner pdf","druckbarer planer","stundenplan","zeitplanung","sofortdownload","planer vorlage","tagesplan","einfacher planer","a4 planer","druckbar"]},
    4535123160: {"title": "Druckbarer Gewohnheitstracker PDF | Einfacher Monatlicher Habit Tracker | A4 | Sofort-Download", "tags": ["gewohnheitstracker pdf","druckbarer tracker","monatlicher tracker","sofortdownload","gewohnheiten","habit tracker","routine tracker","einfacher tracker","a4 tracker","druckbar"]},
    4535101803: {"title": "Druckbarer Budgetplaner PDF | Einfacher Monatlicher Haushaltsplan | Ausgaben Tracker | A4 | Sofort-Download", "tags": ["budgetplaner pdf","druckbarer planer","haushaltsplan","ausgaben tracker","sofortdownload","budget tracker","geldverwaltung","einfacher planer","a4 planer","druckbar"]},
    4535115041: {"title": "Druckbarer Mahlzeitenplaner PDF | Einfacher Wochenspeiseplan | Einkaufsliste | A4 | Sofort-Download", "tags": ["mahlzeitenplaner pdf","druckbarer planer","wochenspeiseplan","einkaufsliste","sofortdownload","meal prep","ernaehrungsplan","einfacher planer","a4 planer","druckbar"]},
    4535133850: {"title": "Planificador Semanal Imprimible PDF | Simple Sin Fecha | Horario Semanal | A4 | Descarga Inmediata", "tags": ["planificador semanal","imprimible pdf","planner simple","sin fecha","descarga inmediata","plantilla planner","horario semanal","habitos","a4 planner","imprimible"]},
    4535117293: {"title": "Planificador Mensual Imprimible PDF | Simple Sin Fecha | Calendario Mensual | A4 | Descarga Inmediata", "tags": ["planificador mensual","imprimible pdf","planner simple","sin fecha","descarga inmediata","plantilla planner","calendario mensual","metas","a4 planner","imprimible"]},
    4535117246: {"title": "Planificador Diario Imprimible PDF | Simple Sin Fecha | Horario por Horas | A4 | Descarga Inmediata", "tags": ["planificador diario","imprimible pdf","planner simple","sin fecha","descarga inmediata","plantilla planner","horario horas","bloque tiempo","a4 planner","imprimible"]},
    4535108575: {"title": "Rastreador de Hábitos Imprimible PDF | Simple Mensual | Reto 66 Días | A4 | Descarga Inmediata", "tags": ["rastreador habitos","imprimible pdf","tracker simple","mensual","descarga inmediata","habitos diarios","reto 66 dias","rutinas","a4 tracker","imprimible"]},
    4535100131: {"title": "Planificador de Presupuesto Imprimible PDF | Simple Mensual | Control de Gastos | A4 | Descarga Inmediata", "tags": ["planificador presupuesto","imprimible pdf","control gastos","mensual","descarga inmediata","tracker gastos","dinero","planner simple","a4 planner","imprimible"]},
    4535125050: {"title": "Planificador de Comidas Imprimible PDF | Simple | Plan Semanal | Lista Compras | A4 | Descarga Inmediata", "tags": ["planificador comidas","imprimible pdf","plan alimentacion","lista compras","descarga inmediata","meal prep","comida semana","planner simple","a4 planner","imprimible"]},
    4535133344: {"title": "Planeador Semanal Imprimível PDF | Simples Sem Data | Horário Semanal | Hábitos | A4 | Download Imediato", "tags": ["planeador semanal","imprimivel pdf","planner simples","sem data","download imediato","modelo planner","horario semanal","habitos","a4 planner","imprimivel"]},
    4535130242: {"title": "Planeador Mensal Imprimível PDF | Simples Sem Data | Calendário Mensal | A4 | Download Imediato", "tags": ["planeador mensal","imprimivel pdf","planner simples","sem data","download imediato","modelo planner","calendario mensal","metas","a4 planner","imprimivel"]},
    4535116440: {"title": "Planeador Diário Imprimível PDF | Simples Sem Data | Horário por Horas | A4 | Download Imediato", "tags": ["planeador diario","imprimivel pdf","planner simples","sem data","download imediato","modelo planner","horario horas","blocos tempo","a4 planner","imprimivel"]},
    4535120410: {"title": "Rastreador de Hábitos Imprimível PDF | Simples Mensal | Desafio 66 Dias | A4 | Download Imediato", "tags": ["rastreador habitos","imprimivel pdf","tracker simples","mensal","download imediato","habitos diarios","desafio 66 dias","rotinas","a4 tracker","imprimivel"]},
    4535112532: {"title": "Planeador de Orçamento Imprimível PDF | Simples Mensal | Controlo de Despesas | A4 | Download Imediato", "tags": ["planeador orcamento","imprimivel pdf","controlo despesas","mensal","download imediato","tracker despesas","dinheiro","planner simples","a4 planner","imprimivel"]},
    4535110809: {"title": "Planeador de Refeições Imprimível PDF | Simples | Plano Semanal | Lista de Compras | A4 | Download Imediato", "tags": ["planeador refeicoes","imprimivel pdf","plano alimentar","lista compras","download imediato","meal prep","refeicoes semana","planner simples","a4 planner","imprimivel"]},
}

# ── PREMIUM listings ──────────────────────────────────────────────────────────
PREMIUM = {
    4546792825: {"title": "Luxury Weekly Planner PDF | Premium Undated Weekly Planner | Habit Tracker | Sage Green | Instant Download | A4", "tags": ["luxury planner pdf","premium weekly","aesthetic planner","undated planner","instant download","sage green planner","elegant planner","weekly spread","premium printable","minimalist planner"]},
    4546807058: {"title": "Luxury Monthly Planner PDF | Premium Undated Monthly Calendar | Goals & Intentions | Sage Green | Instant Download | A4", "tags": ["luxury planner pdf","premium monthly","aesthetic planner","undated planner","instant download","sage green planner","elegant planner","monthly goals","premium printable","minimalist planner"]},
    4546893556: {"title": "Luxury Daily Planner PDF | Premium Undated Daily Planner | Time Blocking | Morning Routine | Instant Download | A4", "tags": ["luxury planner pdf","premium daily","aesthetic planner","time blocking","instant download","morning routine","elegant planner","hourly schedule","premium printable","productivity planner"]},
    4546807140: {"title": "Luxury Habit Tracker PDF | Premium Monthly Habit Tracker | Mood Tracker | Sage Green | Instant Download | A4", "tags": ["luxury tracker pdf","premium habit","aesthetic tracker","mood tracker","instant download","sage green planner","elegant tracker","habit journal","premium printable","self improvement"]},
    4546807228: {"title": "Luxury Budget Planner PDF | Premium Monthly Budget Tracker | Savings Goals | Sage Green | Instant Download | A4", "tags": ["luxury budget pdf","premium budget","aesthetic planner","savings goals","instant download","sage green planner","elegant planner","finance tracker","premium printable","debt tracker"]},
    4546878659: {"title": "Luxury Meal Planner PDF | Premium Weekly Meal Planner | Grocery List | Sage Green | Instant Download | A4", "tags": ["luxury meal planner","premium meal","aesthetic planner","grocery list","instant download","sage green planner","elegant planner","meal prep tracker","premium printable","recipe journal"]},
    4546893756: {"title": "Luxus Wochenplaner PDF | Premium Undatierter Wochenplaner | Gewohnheitstracker | Salbeigrün | Sofort-Download | A4", "tags": ["luxus wochenplaner","premium planer pdf","aesthetic planer","undatiert","sofortdownload","salbeigruen planer","eleganter planer","wochenplan premium","premium druckbar","minimalismus"]},
    4546878887: {"title": "Luxus Monatsplaner PDF | Premium Undatierter Monatskalender | Ziele & Vorsätze | Salbeigrün | Sofort-Download | A4", "tags": ["luxus monatsplaner","premium planer pdf","aesthetic planer","undatiert","sofortdownload","salbeigruen planer","eleganter planer","monatsziele premium","premium druckbar","minimalismus"]},
    4546879013: {"title": "Luxus Tagesplaner PDF | Premium Undatierter Tagesplaner | Stundenplan | Morgenroutine | Sofort-Download | A4", "tags": ["luxus tagesplaner","premium planer pdf","aesthetic planer","stundenplan","sofortdownload","morgenroutine","eleganter planer","tagesplan premium","premium druckbar","produktivitaet"]},
    4546879277: {"title": "Luxus Gewohnheitstracker PDF | Premium Monatlicher Habit Tracker | Stimmungstracker | Sofort-Download | A4", "tags": ["luxus tracker pdf","premium habit tracker","aesthetic tracker","stimmungstracker","sofortdownload","salbeigruen","eleganter tracker","gewohnheiten premium","premium druckbar","selbstverbesserung"]},
    4546879437: {"title": "Luxus Budgetplaner PDF | Premium Monatlicher Haushaltsplan | Sparziele | Salbeigrün | Sofort-Download | A4", "tags": ["luxus budgetplaner","premium planer pdf","aesthetic planer","sparziele","sofortdownload","salbeigruen planer","eleganter planer","budget premium","premium druckbar","finanzplanung"]},
    4546894114: {"title": "Luxus Mahlzeitenplaner PDF | Premium Wochenspeiseplan | Einkaufsliste | Salbeigrün | Sofort-Download | A4", "tags": ["luxus mahlzeitenplaner","premium planer pdf","aesthetic planer","einkaufsliste","sofortdownload","salbeigruen planer","eleganter planer","meal prep premium","premium druckbar","ernaehrung"]},
    4546894554: {"title": "Planificador Semanal de Lujo PDF | Premium Sin Fecha | Rastreador Hábitos | Verde Salvia | Descarga Inmediata | A4", "tags": ["planificador lujo pdf","premium semanal","aesthetic planner","sin fecha","descarga inmediata","verde salvia","planificador elegante","semanal premium","premium imprimible","minimalista"]},
    4546879695: {"title": "Planificador Mensual de Lujo PDF | Premium Sin Fecha | Objetivos e Intenciones | Verde Salvia | Descarga Inmediata | A4", "tags": ["planificador lujo pdf","premium mensual","aesthetic planner","sin fecha","descarga inmediata","verde salvia","planificador elegante","mensual premium","premium imprimible","minimalista"]},
    4546879847: {"title": "Planificador Diario de Lujo PDF | Premium Sin Fecha | Bloques de Tiempo | Rutina Matutina | Descarga Inmediata | A4", "tags": ["planificador lujo pdf","premium diario","aesthetic planner","bloques tiempo","descarga inmediata","rutina matutina","planificador elegante","diario premium","premium imprimible","productividad"]},
    4546880181: {"title": "Rastreador de Hábitos de Lujo PDF | Premium Mensual | Rastreador Humor | Verde Salvia | Descarga Inmediata | A4", "tags": ["rastreador lujo pdf","premium habitos","aesthetic tracker","rastreador humor","descarga inmediata","verde salvia","tracker elegante","habitos premium","premium imprimible","autodisciplina"]},
    4546895218: {"title": "Planificador Presupuesto de Lujo PDF | Premium Mensual | Objetivos Ahorro | Verde Salvia | Descarga Inmediata | A4", "tags": ["planificador lujo pdf","premium presupuesto","aesthetic planner","objetivos ahorro","descarga inmediata","verde salvia","planificador elegante","presupuesto premium","premium imprimible","finanzas"]},
    4546879995: {"title": "Planificador de Comidas de Lujo PDF | Premium Semanal | Lista Compras | Verde Salvia | Descarga Inmediata | A4", "tags": ["planificador lujo pdf","premium comidas","aesthetic planner","lista compras","descarga inmediata","verde salvia","planificador elegante","comidas premium","premium imprimible","meal prep"]},
    4546880439: {"title": "Planeador Semanal de Luxo PDF | Premium Sem Data | Rastreador Hábitos | Verde-Sálvia | Download Imediato | A4", "tags": ["planeador luxo pdf","premium semanal","aesthetic planner","sem data","download imediato","verde salvia","planeador elegante","semanal premium","premium imprimivel","minimalista"]},
    4546895486: {"title": "Planeador Mensal de Luxo PDF | Premium Sem Data | Objetivos e Intenções | Verde-Sálvia | Download Imediato | A4", "tags": ["planeador luxo pdf","premium mensal","aesthetic planner","sem data","download imediato","verde salvia","planeador elegante","mensal premium","premium imprimivel","minimalista"]},
    4546880655: {"title": "Planeador Diário de Luxo PDF | Premium Sem Data | Blocos de Tempo | Rotina Matinal | Download Imediato | A4", "tags": ["planeador luxo pdf","premium diario","aesthetic planner","blocos tempo","download imediato","rotina matinal","planeador elegante","diario premium","premium imprimivel","produtividade"]},
    4546895900: {"title": "Rastreador de Hábitos de Luxo PDF | Premium Mensal | Rastreador Humor | Verde-Sálvia | Download Imediato | A4", "tags": ["rastreador luxo pdf","premium habitos","aesthetic tracker","rastreador humor","download imediato","verde salvia","tracker elegante","habitos premium","premium imprimivel","autodisciplina"]},
    4546880999: {"title": "Planeador de Orçamento de Luxo PDF | Premium Mensal | Objetivos Poupança | Verde-Sálvia | Download Imediato | A4", "tags": ["planeador luxo pdf","premium orcamento","aesthetic planner","objetivos poupanca","download imediato","verde salvia","planeador elegante","orcamento premium","premium imprimivel","financas"]},
    4546880797: {"title": "Planeador de Refeições de Luxo PDF | Premium Semanal | Lista Compras | Verde-Sálvia | Download Imediato | A4", "tags": ["planeador luxo pdf","premium refeicoes","aesthetic planner","lista compras","download imediato","verde salvia","planeador elegante","refeicoes premium","premium imprimivel","meal prep"]},
}


def main():
    token = get_token()
    ok = 0

    print(f"=== SEO UPDATE — {len(LOWCOST) + len(PREMIUM)} listings ===\n")
    print(f"LOW-COST ({len(LOWCOST)}):")
    for lid, d in LOWCOST.items():
        success, code = update(token, lid, d["title"], d["tags"])
        print(f"  {'✅' if success else '❌'} {lid} ({code})")
        time.sleep(0.4)
        if success: ok += 1

    print(f"\nPREMIUM ({len(PREMIUM)}):")
    for lid, d in PREMIUM.items():
        success, code = update(token, lid, d["title"], d["tags"])
        print(f"  {'✅' if success else '❌'} {lid} ({code})")
        time.sleep(0.4)
        if success: ok += 1

    print(f"\n=== {ok}/{len(LOWCOST) + len(PREMIUM)} actualizados ===")


if __name__ == "__main__":
    main()
