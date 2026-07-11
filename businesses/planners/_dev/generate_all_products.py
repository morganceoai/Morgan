#!/usr/bin/env python3
"""
PlannerAtlas — Master generator
Products: daily_planner, budget_tracker, habit_tracker, meal_planner, monthly_planner
Languages: DE, ES, PT, EN  |  Colors: indigo, sage, terracotta
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

HN = '/System/Library/Fonts/HelveticaNeue.ttc'
pdfmetrics.registerFont(TTFont("HN",   HN, subfontIndex=0))
pdfmetrics.registerFont(TTFont("HN-B", HN, subfontIndex=1))
pdfmetrics.registerFont(TTFont("HN-M", HN, subfontIndex=10))
pdfmetrics.registerFont(TTFont("HN-L", HN, subfontIndex=7))

PLAYFAIR = os.path.join(os.path.dirname(__file__), "../_assets/fonts/PlayfairDisplay-Bold.ttf")
pdfmetrics.registerFont(TTFont("PF-B", PLAYFAIR))

W, H = A4
mm = 2.8346456692913385
MB = 13 * mm

THEMES = {
    "indigo": {
        "P":  colors.HexColor("#1a4f7a"),
        "Pd": colors.HexColor("#0f3557"),
        "Pl": colors.HexColor("#e8f2f9"),
        "A":  colors.HexColor("#0099cc"),
        "R":  colors.HexColor("#c0d8e8"),
        "BG": colors.HexColor("#f4f9fc"),
        "TX": colors.HexColor("#0d2035"),
        "MU": colors.HexColor("#6a98b8"),
        "WE": colors.HexColor("#dff0f7"),
        "WA": colors.HexColor("#0099cc"),
    },
    "sage": {
        "P":  colors.HexColor("#2e7d5a"),
        "Pd": colors.HexColor("#1f5e42"),
        "Pl": colors.HexColor("#e8f5ee"),
        "A":  colors.HexColor("#c97b4b"),
        "R":  colors.HexColor("#bee0d0"),
        "BG": colors.HexColor("#f4fbf7"),
        "TX": colors.HexColor("#162a1e"),
        "MU": colors.HexColor("#6aa48a"),
        "WE": colors.HexColor("#fdf0e8"),
        "WA": colors.HexColor("#c97b4b"),
    },
    "terracotta": {
        "P":  colors.HexColor("#b84e28"),
        "Pd": colors.HexColor("#923c1a"),
        "Pl": colors.HexColor("#fceee6"),
        "A":  colors.HexColor("#e8a22e"),
        "R":  colors.HexColor("#f0c8b4"),
        "BG": colors.HexColor("#fdf7f3"),
        "TX": colors.HexColor("#2c1606"),
        "MU": colors.HexColor("#c28570"),
        "WE": colors.HexColor("#fffbee"),
        "WA": colors.HexColor("#e8a22e"),
    },
}

# ── Language config ───────────────────────────────────────────────────────────

LANGS = {
    "DE": {
        "flag": "🇩🇪",
        "brand": "PlannerAtlas",
        "site": "planneratlas.etsy.com",
        "daily": {
            "title": "Tagesplaner",
            "subtitle": "Undatiert  ·  Für jeden Tag",
            "filename": "tagesplaner_DE",
            "cover_tip": "Tipp: Drucke diese Seite täglich — so viele Male, wie du brauchst.",
            "cover_items": ["Datum & Prioritäten", "Stündlicher Zeitplan", "Notizen & Reflexion", "Dankbarkeit"],
            "date_label": "Datum",
            "time_label": "ZEITPLAN",
            "priorities_label": "Top 3 Prioritäten",
            "notes_label": "Notizen",
            "reflection_label": "Reflexion",
            "gratitude_label": "Dankbar für...",
            "footer": "Tagesplaner Undatiert",
        },
        "budget": {
            "title": "Haushaltsplaner",
            "subtitle": "Monatlicher Budgetplaner",
            "filename": "haushaltsplaner_DE",
            "cover_tip": "Tipp: Drucke diesen Planer einmal pro Monat — für das ganze Jahr.",
            "cover_items": ["Monatliches Einkommen", "Fixkosten & variable Kosten", "Wöchentliche Ausgaben", "Spar- & Schulden-Tracker"],
            "income_label": "EINNAHMEN",
            "income_source": "Einkommensquelle",
            "income_amount": "Betrag (€)",
            "income_rows": ["Gehalt / Lohn", "Nebeneinkommen", "Zinsen / Dividenden", "Sonstiges", "Sonstiges"],
            "income_total": "GESAMT EINNAHMEN",
            "fixed_label": "FIXKOSTEN",
            "fixed_items": ["Miete / Hypothek", "Strom & Gas", "Internet & Telefon", "Versicherungen", "Kredite", "Abonnements", "Sonstiges"],
            "var_label": "VARIABLE KOSTEN",
            "var_items": ["Lebensmittel", "Transport", "Restaurant / Takeaway", "Kleidung", "Gesundheit", "Freizeit", "Sonstiges"],
            "balance_label": "BILANZ DES MONATS",
            "total_in": "Gesamt Einnahmen",
            "total_out": "Gesamt Ausgaben",
            "balance": "Saldo",
            "savings_label": "SPARZIELE",
            "savings_goal": "Ziel",
            "savings_target": "Zielbetrag",
            "savings_current": "Aktuell",
            "savings_rows": ["Notgroschen", "Urlaub", "Anschaffung", "Rente / Zukunft", "Sonstiges"],
            "footer": "Haushaltsplaner",
        },
        "habit": {
            "title": "Habit Tracker",
            "subtitle": "Monatlicher Gewohnheits-Tracker",
            "filename": "habit_tracker_DE",
            "cover_tip": "Tipp: Drucke einen Tracker pro Monat — wähle deine Gewohnheiten neu.",
            "cover_items": ["31 Tage Habit Tracker", "Monatsübersicht", "Eigene Gewohnheiten eintragen", "Monatsziel & Reflexion"],
            "month_label": "Monat",
            "habit_label": "GEWOHNHEIT",
            "habit_rows": [
                "Sport / Bewegung", "Wasser (2 Liter)", "Gesund ernähren",
                "Lesen (30 Min.)", "Meditation", "Früh aufstehen",
                "Kein Social Media", "Journaling", "Dankbarkeit", "Eigenes Ziel: ___"
            ],
            "quote": "\"Kleine Schritte täglich führen zu großen Veränderungen.\"",
            "goal_label": "Mein Monatsziel",
            "reflection_label": "Monatsreflexion",
            "footer": "Habit Tracker",
        },
        "meal": {
            "title": "Mahlzeitenplaner",
            "subtitle": "Wöchentlicher Essensplan",
            "filename": "mahlzeitenplaner_DE",
            "cover_tip": "Tipp: Drucke diesen Planer jede Woche — spare Zeit & Geld beim Einkaufen.",
            "cover_items": ["Wöchentlicher Essensplan", "Frühstück, Mittagessen, Abendessen", "Snacks & Getränke", "Einkaufsliste"],
            "days": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
            "meals": ["Frühstück", "Mittagessen", "Abendessen", "Snacks"],
            "shopping_label": "EINKAUFSLISTE",
            "shopping_cols": ["Lebensmittel", "Menge", "✓"],
            "notes_label": "Notizen",
            "week_label": "Woche",
            "footer": "Mahlzeitenplaner",
        },
        "monthly": {
            "title": "Monatsplaner",
            "subtitle": "Undatiert  ·  Für jeden Monat",
            "filename": "monatsplaner_DE",
            "cover_tip": "Tipp: Drucke einen Kalender pro Monat — trage einfach das Datum ein.",
            "cover_items": ["Monatskalender (undatiert)", "Monatsziele", "Wichtige Termine", "Notizen & Reflexion"],
            "days_header": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
            "month_label": "Monat & Jahr",
            "goals_label": "Monatsziele",
            "events_label": "Wichtige Termine",
            "notes_label": "Notizen",
            "reflection_label": "Monatsreflexion",
            "footer": "Monatsplaner Undatiert",
        },
    },
    "ES": {
        "flag": "🇪🇸",
        "brand": "PlannerAtlas",
        "site": "planneratlas.etsy.com",
        "daily": {
            "title": "Planificador Diario",
            "subtitle": "Sin fecha  ·  Para cada día",
            "filename": "planificador_diario_ES",
            "cover_tip": "Consejo: Imprime esta página cada día — tantas veces como necesites.",
            "cover_items": ["Fecha y prioridades", "Horario por horas", "Notas y reflexión", "Gratitud"],
            "date_label": "Fecha",
            "time_label": "HORARIO",
            "priorities_label": "Top 3 Prioridades",
            "notes_label": "Notas",
            "reflection_label": "Reflexión",
            "gratitude_label": "Agradecimiento...",
            "footer": "Planificador Diario Sin Fecha",
        },
        "budget": {
            "title": "Control de Gastos",
            "subtitle": "Planificador Mensual de Presupuesto",
            "filename": "control_gastos_ES",
            "cover_tip": "Consejo: Imprime este planificador una vez al mes — para todo el año.",
            "cover_items": ["Ingresos mensuales", "Gastos fijos y variables", "Registro semanal de gastos", "Control de ahorro y deudas"],
            "income_label": "INGRESOS",
            "income_source": "Fuente de ingresos",
            "income_amount": "Importe (€)",
            "income_rows": ["Salario", "Ingresos extra", "Intereses / Dividendos", "Otros", "Otros"],
            "income_total": "TOTAL INGRESOS",
            "fixed_label": "GASTOS FIJOS",
            "fixed_items": ["Alquiler / Hipoteca", "Luz y gas", "Internet y teléfono", "Seguros", "Préstamos", "Suscripciones", "Otros"],
            "var_label": "GASTOS VARIABLES",
            "var_items": ["Alimentación", "Transporte", "Restaurantes", "Ropa", "Salud", "Ocio", "Otros"],
            "balance_label": "BALANCE DEL MES",
            "total_in": "Total Ingresos",
            "total_out": "Total Gastos",
            "balance": "Saldo",
            "savings_label": "OBJETIVOS DE AHORRO",
            "savings_goal": "Objetivo",
            "savings_target": "Meta (€)",
            "savings_current": "Actual (€)",
            "savings_rows": ["Fondo de emergencia", "Vacaciones", "Compra importante", "Jubilación", "Otros"],
            "footer": "Control de Gastos",
        },
        "habit": {
            "title": "Rastreador de Hábitos",
            "subtitle": "Seguimiento mensual de hábitos",
            "filename": "habitos_ES",
            "cover_tip": "Consejo: Imprime un tracker por mes — elige tus hábitos cada vez.",
            "cover_items": ["31 días de seguimiento", "Vista mensual", "Hábitos personalizables", "Meta y reflexión mensual"],
            "month_label": "Mes",
            "habit_label": "HÁBITO",
            "habit_rows": [
                "Ejercicio físico", "Agua (2 litros)", "Alimentación sana",
                "Lectura (30 min.)", "Meditación", "Madrugar",
                "Sin redes sociales", "Journaling", "Gratitud", "Mi objetivo: ___"
            ],
            "quote": "\"Pequeños pasos cada día llevan a grandes cambios.\"",
            "goal_label": "Mi objetivo del mes",
            "reflection_label": "Reflexión mensual",
            "footer": "Rastreador de Hábitos",
        },
        "meal": {
            "title": "Planificador de Comidas",
            "subtitle": "Plan semanal de alimentación",
            "filename": "comidas_ES",
            "cover_tip": "Consejo: Imprime este planificador cada semana — ahorra tiempo y dinero.",
            "cover_items": ["Plan semanal de comidas", "Desayuno, almuerzo, cena", "Snacks y bebidas", "Lista de la compra"],
            "days": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            "meals": ["Desayuno", "Almuerzo", "Cena", "Snacks"],
            "shopping_label": "LISTA DE LA COMPRA",
            "shopping_cols": ["Producto", "Cantidad", "✓"],
            "notes_label": "Notas",
            "week_label": "Semana",
            "footer": "Planificador de Comidas",
        },
        "monthly": {
            "title": "Planificador Mensual",
            "subtitle": "Sin fecha  ·  Para cada mes",
            "filename": "planificador_mensual_ES",
            "cover_tip": "Consejo: Imprime un calendario por mes — añade la fecha tú mismo.",
            "cover_items": ["Calendario mensual (sin fecha)", "Objetivos del mes", "Fechas importantes", "Notas y reflexión"],
            "days_header": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            "month_label": "Mes y año",
            "goals_label": "Objetivos del mes",
            "events_label": "Fechas importantes",
            "notes_label": "Notas",
            "reflection_label": "Reflexión mensual",
            "footer": "Planificador Mensual Sin Fecha",
        },
    },
    "PT": {
        "flag": "🇵🇹",
        "brand": "PlannerAtlas",
        "site": "planneratlas.etsy.com",
        "daily": {
            "title": "Planeador Diário",
            "subtitle": "Sem data  ·  Para cada dia",
            "filename": "planeador_diario_PT",
            "cover_tip": "Dica: Imprime esta página diariamente — tantas vezes quantas precisares.",
            "cover_items": ["Data e prioridades", "Horário hora a hora", "Notas e reflexão", "Gratidão"],
            "date_label": "Data",
            "time_label": "HORÁRIO",
            "priorities_label": "Top 3 Prioridades",
            "notes_label": "Notas",
            "reflection_label": "Reflexão",
            "gratitude_label": "Grato por...",
            "footer": "Planeador Diário Sem Data",
        },
        "budget": {
            "title": "Controlo de Despesas",
            "subtitle": "Orçamento Mensal",
            "filename": "despesas_PT",
            "cover_tip": "Dica: Imprime este planeador uma vez por mês — para o ano inteiro.",
            "cover_items": ["Rendimentos mensais", "Despesas fixas e variáveis", "Registo semanal de gastos", "Controlo de poupança e dívidas"],
            "income_label": "RENDIMENTOS",
            "income_source": "Fonte de rendimento",
            "income_amount": "Valor (€)",
            "income_rows": ["Salário", "Rendimento extra", "Juros / Dividendos", "Outros", "Outros"],
            "income_total": "TOTAL RENDIMENTOS",
            "fixed_label": "DESPESAS FIXAS",
            "fixed_items": ["Renda / Hipoteca", "Eletricidade e gás", "Internet e telemóvel", "Seguros", "Empréstimos", "Subscrições", "Outros"],
            "var_label": "DESPESAS VARIÁVEIS",
            "var_items": ["Alimentação", "Transportes", "Restaurantes", "Vestuário", "Saúde", "Lazer", "Outros"],
            "balance_label": "BALANÇO DO MÊS",
            "total_in": "Total Rendimentos",
            "total_out": "Total Despesas",
            "balance": "Saldo",
            "savings_label": "OBJETIVOS DE POUPANÇA",
            "savings_goal": "Objetivo",
            "savings_target": "Meta (€)",
            "savings_current": "Atual (€)",
            "savings_rows": ["Fundo de emergência", "Férias", "Compra importante", "Reforma", "Outros"],
            "footer": "Controlo de Despesas",
        },
        "habit": {
            "title": "Rastreador de Hábitos",
            "subtitle": "Acompanhamento mensal de hábitos",
            "filename": "habitos_PT",
            "cover_tip": "Dica: Imprime um tracker por mês — escolhe os teus hábitos de novo.",
            "cover_items": ["31 dias de acompanhamento", "Vista mensal", "Hábitos personalizáveis", "Objetivo e reflexão mensal"],
            "month_label": "Mês",
            "habit_label": "HÁBITO",
            "habit_rows": [
                "Exercício físico", "Água (2 litros)", "Alimentação saudável",
                "Leitura (30 min.)", "Meditação", "Acordar cedo",
                "Sem redes sociais", "Journaling", "Gratidão", "O meu objetivo: ___"
            ],
            "quote": "\"Pequenos passos diários levam a grandes mudanças.\"",
            "goal_label": "O meu objetivo do mês",
            "reflection_label": "Reflexão mensal",
            "footer": "Rastreador de Hábitos",
        },
        "meal": {
            "title": "Planeador de Refeições",
            "subtitle": "Plano semanal de alimentação",
            "filename": "refeicoes_PT",
            "cover_tip": "Dica: Imprime este planeador cada semana — poupa tempo e dinheiro.",
            "cover_items": ["Plano semanal de refeições", "Pequeno-almoço, almoço, jantar", "Snacks e bebidas", "Lista de compras"],
            "days": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
            "meals": ["Pequeno-almoço", "Almoço", "Jantar", "Snacks"],
            "shopping_label": "LISTA DE COMPRAS",
            "shopping_cols": ["Produto", "Qtd.", "✓"],
            "notes_label": "Notas",
            "week_label": "Semana",
            "footer": "Planeador de Refeições",
        },
        "monthly": {
            "title": "Planeador Mensal",
            "subtitle": "Sem data  ·  Para cada mês",
            "filename": "planeador_mensal_PT",
            "cover_tip": "Dica: Imprime um calendário por mês — adiciona a data tu mesmo.",
            "cover_items": ["Calendário mensal (sem data)", "Objetivos do mês", "Datas importantes", "Notas e reflexão"],
            "days_header": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
            "month_label": "Mês e ano",
            "goals_label": "Objetivos do mês",
            "events_label": "Datas importantes",
            "notes_label": "Notas",
            "reflection_label": "Reflexão mensal",
            "footer": "Planeador Mensal Sem Data",
        },
    },
    "EN": {
        "flag": "🇬🇧",
        "brand": "PlannerAtlas",
        "site": "planneratlas.etsy.com",
        "daily": {
            "title": "Daily Planner",
            "subtitle": "Undated  ·  For Every Day",
            "filename": "daily_planner_EN",
            "cover_tip": "Tip: Print this page daily — as many times as you need.",
            "cover_items": ["Date & priorities", "Hour-by-hour schedule", "Notes & reflection", "Gratitude"],
            "date_label": "Date",
            "time_label": "SCHEDULE",
            "priorities_label": "Top 3 Priorities",
            "notes_label": "Notes",
            "reflection_label": "Reflection",
            "gratitude_label": "Grateful for...",
            "footer": "Daily Planner Undated",
        },
        "budget": {
            "title": "Budget Tracker",
            "subtitle": "Monthly Budget Planner",
            "filename": "budget_tracker_EN",
            "cover_tip": "Tip: Print this planner once a month — for the entire year.",
            "cover_items": ["Monthly income overview", "Fixed & variable expenses", "Weekly expense log", "Savings & debt tracker"],
            "income_label": "INCOME",
            "income_source": "Income source",
            "income_amount": "Amount (€)",
            "income_rows": ["Salary / Wages", "Side income", "Interest / Dividends", "Other", "Other"],
            "income_total": "TOTAL INCOME",
            "fixed_label": "FIXED EXPENSES",
            "fixed_items": ["Rent / Mortgage", "Electricity & gas", "Internet & phone", "Insurance", "Loans", "Subscriptions", "Other"],
            "var_label": "VARIABLE EXPENSES",
            "var_items": ["Groceries", "Transport", "Restaurants", "Clothing", "Health", "Entertainment", "Other"],
            "balance_label": "MONTHLY BALANCE",
            "total_in": "Total Income",
            "total_out": "Total Expenses",
            "balance": "Balance",
            "savings_label": "SAVINGS GOALS",
            "savings_goal": "Goal",
            "savings_target": "Target (€)",
            "savings_current": "Current (€)",
            "savings_rows": ["Emergency fund", "Vacation", "Big purchase", "Retirement", "Other"],
            "footer": "Budget Tracker",
        },
        "habit": {
            "title": "Habit Tracker",
            "subtitle": "Monthly Habit Tracker",
            "filename": "habit_tracker_EN",
            "cover_tip": "Tip: Print one tracker per month — choose your habits fresh each time.",
            "cover_items": ["31-day habit tracker", "Monthly overview", "Customizable habits", "Monthly goal & reflection"],
            "month_label": "Month",
            "habit_label": "HABIT",
            "habit_rows": [
                "Exercise / Movement", "Water (2 litres)", "Healthy eating",
                "Reading (30 min.)", "Meditation", "Early rising",
                "No social media", "Journaling", "Gratitude", "My own goal: ___"
            ],
            "quote": "\"Small daily steps lead to big changes.\"",
            "goal_label": "My monthly goal",
            "reflection_label": "Monthly reflection",
            "footer": "Habit Tracker",
        },
        "meal": {
            "title": "Meal Planner",
            "subtitle": "Weekly Meal Plan",
            "filename": "meal_planner_EN",
            "cover_tip": "Tip: Print this planner every week — save time and money on groceries.",
            "cover_items": ["Weekly meal plan", "Breakfast, lunch, dinner", "Snacks & drinks", "Shopping list"],
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "meals": ["Breakfast", "Lunch", "Dinner", "Snacks"],
            "shopping_label": "SHOPPING LIST",
            "shopping_cols": ["Item", "Qty.", "✓"],
            "notes_label": "Notes",
            "week_label": "Week",
            "footer": "Meal Planner",
        },
        "monthly": {
            "title": "Monthly Planner",
            "subtitle": "Undated  ·  For Every Month",
            "filename": "monthly_planner_EN",
            "cover_tip": "Tip: Print one calendar per month — simply fill in the date yourself.",
            "cover_items": ["Monthly calendar (undated)", "Monthly goals", "Important dates", "Notes & reflection"],
            "days_header": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "month_label": "Month & Year",
            "goals_label": "Monthly goals",
            "events_label": "Important dates",
            "notes_label": "Notes",
            "reflection_label": "Monthly reflection",
            "footer": "Monthly Planner Undated",
        },
    },
}

# ── Shared page components ────────────────────────────────────────────────────

def bg(cv, t):
    cv.setFillColor(t["BG"])
    cv.rect(0, 0, W, H, fill=1, stroke=0)

def hdr(cv, t, title, sub=""):
    hh = 27 * mm
    cv.setFillColor(t["P"]); cv.rect(0, H - hh, W, hh, fill=1, stroke=0)
    cv.setFillColor(t["A"]); cv.rect(0, H - hh, 5 * mm, hh, fill=1, stroke=0)
    cv.setFillColor(t["Pd"]); cv.circle(W - 18 * mm, H - hh / 2, 15 * mm, fill=1, stroke=0)
    cv.setFillColor(t["A"]);  cv.circle(W - 18 * mm, H - hh / 2,  7 * mm, fill=1, stroke=0)
    cv.setFillColor(colors.white)
    cv.setFont("HN-B", 21); cv.drawString(14 * mm, H - 11 * mm, title)
    if sub:
        cv.setFont("HN-L", 9); cv.setFillColor(colors.HexColor("#ffffffaa"))
        cv.drawString(14 * mm, H - 20 * mm, sub)

def ftr(cv, t, label, lang_obj):
    fh = MB - 2 * mm
    cv.setFillColor(t["P"]); cv.rect(0, 0, W, fh, fill=1, stroke=0)
    cv.setFillColor(t["A"]); cv.rect(0, 0, 5 * mm, fh, fill=1, stroke=0)
    cv.setFillColor(colors.HexColor("#ffffffaa")); cv.setFont("HN", 7.5)
    cv.drawString(14 * mm, 4 * mm, f"{lang_obj['brand']}  ·  {label}  ·  {lang_obj['site']}")
    cv.setFillColor(colors.white); cv.setFont("HN-B", 7.5)
    cv.drawRightString(W - 12 * mm, 4 * mm, lang_obj['site'])

def cover_page(cv, t, cfg, lang_obj, tname):
    bg(cv, t)
    split = H * 0.40

    # Primary colored upper block
    cv.setFillColor(t["P"]); cv.rect(0, split, W, H - split, fill=1, stroke=0)

    # Large decorative circle (dark) — top right
    cx_circ = W * 0.88; cy_circ = split + (H - split) * 0.68
    cv.setFillColor(t["Pd"]); cv.circle(cx_circ, cy_circ, 60 * mm, fill=1, stroke=0)

    # PA monogram — elegant serif on accent circle
    cv.setFillColor(t["A"]); cv.circle(cx_circ, cy_circ, 32 * mm, fill=1, stroke=0)
    # double-ring detail
    cv.setStrokeColor(colors.HexColor("#ffffff40")); cv.setLineWidth(2)
    cv.circle(cx_circ, cy_circ, 28.5 * mm, fill=0, stroke=1)
    cv.setStrokeColor(colors.HexColor("#ffffff20")); cv.setLineWidth(0.7)
    cv.circle(cx_circ, cy_circ, 26 * mm, fill=0, stroke=1)
    # "PA" in Playfair Display — serif monogram, tight spacing
    cv.setFillColor(colors.white)
    cv.setFont("PF-B", 40)
    # Draw P and A as separate calls with tight kerning (no built-in kern control in reportlab)
    # Measure widths to manually center
    p_w = cv.stringWidth("P", "PF-B", 40)
    a_w = cv.stringWidth("A", "PF-B", 40)
    gap = -3 * mm   # negative gap = overlap for ligature feel
    total_w = p_w + gap + a_w
    start_x = cx_circ - total_w / 2
    baseline = cy_circ - 7 * mm
    cv.drawString(start_x, baseline, "P")
    cv.drawString(start_x + p_w + gap, baseline, "A")
    # thin gold/white dividing stroke between letters (vertical hairline)
    mid_x = start_x + p_w + gap / 2
    cv.setStrokeColor(colors.HexColor("#ffffff60")); cv.setLineWidth(0.6)
    cv.line(mid_x, baseline - 2 * mm, mid_x, baseline + 14 * mm)
    # thin rules above and below text
    pad = 6 * mm
    rule_y_top = baseline + 17 * mm
    rule_y_bot = baseline - 6 * mm
    cv.setStrokeColor(colors.HexColor("#ffffffaa")); cv.setLineWidth(0.8)
    cv.line(cx_circ - 18 * mm, rule_y_top, cx_circ + 18 * mm, rule_y_top)
    cv.line(cx_circ - 18 * mm, rule_y_bot, cx_circ + 18 * mm, rule_y_bot)
    # small diamond ornament between rules
    diam_x, diam_y = cx_circ, rule_y_top + 3.5 * mm
    cv.setFillColor(colors.HexColor("#ffffffcc"))
    p = cv.beginPath()
    s = 2.2 * mm
    p.moveTo(diam_x, diam_y + s); p.lineTo(diam_x + s, diam_y)
    p.lineTo(diam_x, diam_y - s); p.lineTo(diam_x - s, diam_y)
    p.close(); cv.drawPath(p, fill=1, stroke=0)

    # Small accent circle top-left edge
    cv.setFillColor(t["A"]); cv.circle(-8 * mm, H - 10 * mm, 32 * mm, fill=1, stroke=0)
    # Left accent stripe
    cv.setFillColor(t["A"]); cv.rect(0, split, 5 * mm, H - split, fill=1, stroke=0)

    # Title — clean, no subtitle
    cv.setFillColor(colors.white)
    cv.setFont("HN-B", 42); cv.drawString(18 * mm, split + 92 * mm, cfg["title"])

    # Thin accent line under title
    cv.setStrokeColor(t["A"]); cv.setLineWidth(2.5)
    cv.line(18 * mm, split + 83 * mm, 78 * mm, split + 83 * mm)

    # Contents list — lower white section
    contents_label = {"DE": "Inhalt", "ES": "Contenido", "PT": "Conteúdo", "EN": "Contents"}
    lang_key = next((k for k, v in LANGS.items() if v is lang_obj), "EN")
    cv.setFillColor(t["TX"]); cv.setFont("HN-B", 12)
    cv.drawString(18 * mm, split - 14 * mm, contents_label.get(lang_key, "Contents") + ":")
    cv.setFont("HN", 10.5); cv.setFillColor(t["MU"])
    for i, item in enumerate(cfg["cover_items"]):
        cv.drawString(20 * mm, split - 26 * mm - i * 9 * mm, f"  ●  {item}")

    # Brand footer
    cv.setFillColor(t["MU"]); cv.setFont("HN-L", 8)
    cv.drawCentredString(W / 2, MB + 5 * mm,
                         f"PlannerAtlas  ·  {tname.capitalize()} Edition  ·  planneratlas.etsy.com")
    cv.showPage()

# ── DAILY PLANNER page ────────────────────────────────────────────────────────

def daily_page(cv, t, cfg, lang_obj):
    bg(cv, t)
    hdr(cv, t, cfg["title"], "")
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    # Date bar — more prominent
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, yt + 2 * mm, W - 28 * mm, 9 * mm, 4, fill=1, stroke=0)
    cv.setFillColor(t["P"]); cv.setFont("HN-B", 8)
    cv.drawString(lx + 3 * mm, yt + 6 * mm, cfg["date_label"] + ":")
    cv.setFillColor(t["MU"]); cv.setFont("HN", 8)
    cv.drawString(lx + 24 * mm, yt + 6 * mm, "________________________________________________")

    # Left column: time schedule (wider, more breathing room)
    col_split = lx + 68 * mm
    time_start = 6; time_end = 22
    n_slots = time_end - time_start
    slot_h = (yt - yb - 16 * mm) / n_slots

    # Schedule label
    cv.setFillColor(t["A"]); cv.setFont("HN-B", 7.5)
    cv.drawString(lx, yt - 8 * mm, cfg["time_label"])

    for i in range(n_slots):
        hour = time_start + i
        sy = yt - 16 * mm - i * slot_h
        is_lunch = hour == 12
        is_end_of_work = hour == 18

        # Hour background chip
        if is_lunch or is_end_of_work:
            cv.setFillColor(t["WE"] if not is_lunch else t["Pl"])
            cv.roundRect(lx, sy - slot_h * 0.7, col_split - lx - 2 * mm, slot_h * 0.85, 2, fill=1, stroke=0)

        cv.setFillColor(t["A"] if is_lunch else t["P"])
        cv.setFont("HN-B" if is_lunch else "HN-M", 8)
        cv.drawString(lx + 1 * mm, sy, f"{hour:02d}:00")

        cv.setStrokeColor(t["A"] if is_lunch else t["R"])
        cv.setLineWidth(1.2 if is_lunch else 0.4)
        cv.line(lx + 14 * mm, sy, col_split - 3 * mm, sy)

        if i < n_slots - 1:
            hy = sy - slot_h / 2
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.2)
            cv.line(lx + 14 * mm, hy, col_split - 3 * mm, hy)

    # Right column sections
    lx2 = col_split + 5 * mm; rw = rx - lx2
    sections = [
        (cfg["priorities_label"], 3, 11 * mm, True),
        (cfg["notes_label"],      5, 9 * mm,  False),
        (cfg["reflection_label"], 3, 9 * mm,  False),
        (cfg["gratitude_label"],  2, 9 * mm,  False),
    ]
    sy2 = yt - 6 * mm
    for label, nlines, lh, has_circles in sections:
        sh = 10 * mm + nlines * lh
        if sy2 - sh < yb:
            break
        # Card
        cv.setFillColor(colors.white)
        cv.roundRect(lx2, sy2 - sh, rw, sh, 6, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4)
        cv.roundRect(lx2, sy2 - sh, rw, sh, 6, fill=0, stroke=1)
        # Header bar
        cv.setFillColor(t["P"])
        cv.roundRect(lx2, sy2 - 9 * mm, rw, 9 * mm, 6, fill=1, stroke=0)
        cv.rect(lx2, sy2 - 9 * mm, rw, 4.5 * mm, fill=1, stroke=0)
        # Accent dot in header
        cv.setFillColor(t["A"])
        cv.circle(lx2 + 5 * mm, sy2 - 4.5 * mm, 1.8 * mm, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 9)
        cv.drawString(lx2 + 10 * mm, sy2 - 6.5 * mm, label)

        for k in range(nlines):
            ly = sy2 - 9 * mm - (k + 1) * lh + 2.5 * mm
            if ly > sy2 - sh + 2 * mm:
                if has_circles:
                    # Numbered priority circles
                    cv.setFillColor(t["Pl"])
                    cv.circle(lx2 + 5 * mm, ly + 2 * mm, 3.2 * mm, fill=1, stroke=0)
                    cv.setStrokeColor(t["P"]); cv.setLineWidth(0.8)
                    cv.circle(lx2 + 5 * mm, ly + 2 * mm, 3.2 * mm, fill=0, stroke=1)
                    cv.setFillColor(t["P"]); cv.setFont("HN-B", 7.5)
                    cv.drawCentredString(lx2 + 5 * mm, ly + 0.5 * mm, str(k + 1))
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4)
                cv.line(lx2 + (12 * mm if has_circles else 4 * mm), ly,
                        lx2 + rw - 4 * mm, ly)
        sy2 -= sh + 4 * mm

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

# ── BUDGET TRACKER pages ──────────────────────────────────────────────────────

def budget_overview(cv, t, cfg, lang_obj):
    """Page 1: Income + Fixed + Variable expenses + Balance"""
    bg(cv, t)
    hdr(cv, t, cfg["title"], cfg["subtitle"])
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    # Month field
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, yt + 2 * mm, 80 * mm, 8 * mm, 3, fill=1, stroke=0)
    cv.setFillColor(t["MU"]); cv.setFont("HN", 7.5)
    cv.drawString(lx + 2 * mm, yt + 5.5 * mm, cfg.get("month_label", "Monat") + ": ___________________________")

    mid = lx + (rx - lx) / 2 - 2 * mm
    rh = 7.5 * mm
    label_w = 65 * mm
    amt_w = 25 * mm

    def section_header(y, label, width):
        cv.setFillColor(t["P"])
        cv.roundRect(lx, y - 7 * mm, width, 7 * mm, 3, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8.5)
        cv.drawString(lx + 3 * mm, y - 5 * mm, label)
        cv.setFillColor(colors.HexColor("#ffffff55")); cv.setFont("HN", 7)
        cv.drawRightString(lx + width - 3 * mm, y - 5 * mm, cfg["income_amount"] if "income" in label.lower() or label == cfg["income_label"] else "Betrag (€)" if lang_obj == LANGS["DE"] else "Importe (€)" if lang_obj == LANGS["ES"] else "Valor (€)" if lang_obj == LANGS["PT"] else "Amount (€)")

    def table_row(y, label, alt=False, bold=False):
        w = mid - lx
        cv.setFillColor(t["Pl"] if alt else colors.white)
        cv.rect(lx, y - rh, w, rh, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.3)
        cv.rect(lx, y - rh, w, rh, fill=0, stroke=1)
        cv.setFillColor(t["TX"] if bold else t["MU"])
        cv.setFont("HN-B" if bold else "HN", 8)
        cv.drawString(lx + 3 * mm, y - rh / 2 - 2 * mm, label)
        # Amount box
        cv.setFillColor(colors.white)
        cv.rect(lx + label_w, y - rh, amt_w, rh, fill=1, stroke=0)
        cv.setStrokeColor(t["A"] if bold else t["R"]); cv.setLineWidth(0.5 if bold else 0.3)
        cv.rect(lx + label_w, y - rh, amt_w, rh, fill=0, stroke=1)

    # INCOME section
    sy = yt - 14 * mm
    section_header(sy, cfg["income_label"], mid - lx)
    for i, row in enumerate(cfg["income_rows"]):
        sy -= rh
        table_row(sy, row, alt=i % 2 == 0)
    sy -= rh
    table_row(sy, cfg["income_total"], bold=True)

    # FIXED EXPENSES - right column
    ry = yt - 14 * mm
    rx_col = rx
    label_w2 = 65 * mm
    col_start = mid + 4 * mm

    def section_header_r(y, label):
        w = rx_col - col_start
        cv.setFillColor(t["P"])
        cv.roundRect(col_start, y - 7 * mm, w, 7 * mm, 3, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8.5)
        cv.drawString(col_start + 3 * mm, y - 5 * mm, label)

    def table_row_r(y, label, alt=False, bold=False):
        w = rx_col - col_start
        cv.setFillColor(t["Pl"] if alt else colors.white)
        cv.rect(col_start, y - rh, w, rh, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.3)
        cv.rect(col_start, y - rh, w, rh, fill=0, stroke=1)
        cv.setFillColor(t["TX"] if bold else t["MU"])
        cv.setFont("HN-B" if bold else "HN", 8)
        cv.drawString(col_start + 3 * mm, y - rh / 2 - 2 * mm, label)
        ax = col_start + (rx_col - col_start) - amt_w
        cv.setFillColor(colors.white)
        cv.rect(ax, y - rh, amt_w, rh, fill=1, stroke=0)
        cv.setStrokeColor(t["A"] if bold else t["R"]); cv.setLineWidth(0.5 if bold else 0.3)
        cv.rect(ax, y - rh, amt_w, rh, fill=0, stroke=1)

    section_header_r(ry, cfg["fixed_label"])
    for i, item in enumerate(cfg["fixed_items"]):
        ry -= rh
        table_row_r(ry, item, alt=i % 2 == 0)

    ry -= (rh + 10 * mm)   # below last row + visual gap
    section_header_r(ry, cfg["var_label"])
    for i, item in enumerate(cfg["var_items"]):
        ry -= rh
        table_row_r(ry, item, alt=i % 2 == 0)

    # BALANCE box
    bal_y = min(sy - 8 * mm, ry - 8 * mm)
    bal_h = 28 * mm
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, bal_y - bal_h, rx - lx, bal_h, 5, fill=1, stroke=0)
    cv.setStrokeColor(t["P"]); cv.setLineWidth(3)
    cv.line(lx, bal_y - bal_h, lx, bal_y)
    cv.setFillColor(t["P"]); cv.setFont("HN-B", 9.5)
    cv.drawString(lx + 5 * mm, bal_y - 8 * mm, cfg["balance_label"])
    bw = (rx - lx - 10 * mm) / 3
    for i, (lbl, val) in enumerate([
        (cfg["total_in"], "+ ___________"),
        (cfg["total_out"], "- ___________"),
        (cfg["balance"], "= ___________"),
    ]):
        bx = lx + 5 * mm + i * bw
        cv.setFillColor(t["MU"]); cv.setFont("HN", 8)
        cv.drawString(bx, bal_y - 16 * mm, lbl)
        cv.setFillColor(t["TX"]); cv.setFont("HN-M", 9)
        cv.drawString(bx, bal_y - 24 * mm, val)

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

def budget_savings(cv, t, cfg, lang_obj):
    """Page 2: Savings goals + weekly expense log"""
    bg(cv, t)
    hdr(cv, t, cfg["title"], cfg["savings_label"])
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    # Savings table
    col_w = (rx - lx) / 4
    headers = [cfg["savings_goal"], cfg["savings_target"], cfg["savings_current"], "% "]
    rh = 8 * mm
    sh = 7 * mm
    # Header row
    for i, h in enumerate(headers):
        cx2 = lx + i * col_w
        cv.setFillColor(t["P"])
        cv.rect(cx2, yt - sh, col_w, sh, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8)
        cv.drawCentredString(cx2 + col_w / 2, yt - sh / 2 - 2 * mm, h)

    for r, row_label in enumerate(cfg["savings_rows"]):
        ry2 = yt - sh - r * rh
        for i in range(4):
            cx2 = lx + i * col_w
            cv.setFillColor(t["Pl"] if r % 2 == 0 else colors.white)
            cv.rect(cx2, ry2 - rh, col_w, rh, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.3)
            cv.rect(cx2, ry2 - rh, col_w, rh, fill=0, stroke=1)
            if i == 0:
                cv.setFillColor(t["MU"]); cv.setFont("HN", 8)
                cv.drawString(cx2 + 2 * mm, ry2 - rh / 2 - 2 * mm, row_label)

    # Progress bar placeholder
    bar_y = yt - sh - len(cfg["savings_rows"]) * rh - 5 * mm
    for r in range(len(cfg["savings_rows"])):
        by = yt - sh - r * rh - rh / 2
        bx = lx + 3 * col_w + 3 * mm
        bw = col_w - 6 * mm
        cv.setFillColor(t["R"])
        cv.roundRect(bx, by - 2 * mm, bw, 4 * mm, 2, fill=1, stroke=0)
        cv.setFillColor(t["A"])
        cv.roundRect(bx, by - 2 * mm, bw * 0.3, 4 * mm, 2, fill=1, stroke=0)

    # Weekly expense log below
    we_y = bar_y - 8 * mm
    we_h = 6.5 * mm
    wcols = [30 * mm, (rx - lx - 30 * mm - 25 * mm - 18 * mm), 25 * mm, 18 * mm]
    wheaders = ["Datum" if lang_obj == LANGS["DE"] else "Fecha" if lang_obj == LANGS["ES"] else "Data" if lang_obj == LANGS["PT"] else "Date",
                "Beschreibung" if lang_obj == LANGS["DE"] else "Descripción" if lang_obj == LANGS["ES"] else "Descrição" if lang_obj == LANGS["PT"] else "Description",
                "Kategorie" if lang_obj == LANGS["DE"] else "Categoría" if lang_obj == LANGS["ES"] else "Categoria" if lang_obj == LANGS["PT"] else "Category",
                "€"]
    # Section title
    cv.setFillColor(t["P"]); cv.setFont("HN-B", 9.5)
    cv.drawString(lx, we_y, "Wöchentliche Ausgaben" if lang_obj == LANGS["DE"] else
                  "Gastos semanales" if lang_obj == LANGS["ES"] else
                  "Despesas semanais" if lang_obj == LANGS["PT"] else "Weekly Expenses")
    we_y -= 3 * mm
    # Header
    cx2 = lx
    for i, (wh, ww) in enumerate(zip(wheaders, wcols)):
        cv.setFillColor(t["P"]); cv.rect(cx2, we_y - we_h, ww, we_h, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 7.5)
        cv.drawCentredString(cx2 + ww / 2, we_y - we_h / 2 - 2 * mm, wh)
        cx2 += ww
    # Data rows
    n_rows = max(5, int((we_y - we_h - yb) / we_h))
    for r in range(n_rows):
        ry3 = we_y - we_h - r * we_h
        if ry3 - we_h < yb:
            break
        cx3 = lx
        for i, ww in enumerate(wcols):
            cv.setFillColor(t["Pl"] if r % 2 == 0 else colors.white)
            cv.rect(cx3, ry3 - we_h, ww, we_h, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.25)
            cv.rect(cx3, ry3 - we_h, ww, we_h, fill=0, stroke=1)
            cx3 += ww

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

# ── HABIT TRACKER page ────────────────────────────────────────────────────────

def habit_page(cv, t, cfg, lang_obj):
    bg(cv, t)
    hdr(cv, t, cfg["title"], cfg["subtitle"])
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    # Month label
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, yt + 2 * mm, 60 * mm, 8 * mm, 3, fill=1, stroke=0)
    cv.setFillColor(t["MU"]); cv.setFont("HN", 7.5)
    cv.drawString(lx + 2 * mm, yt + 5.5 * mm, cfg["month_label"] + ": ________________________")

    nh = 10; nd = 31
    hlw = 50 * mm
    cw = (rx - lx - hlw) / nd
    avail_h = yt - yb - 22 * mm
    rh = avail_h / (nh + 1)

    # Day headers
    for d in range(nd):
        dx = lx + hlw + d * cw
        iw = d % 7 >= 5
        cv.setFillColor(t["WA"] if iw else t["P"])
        cv.roundRect(dx + 0.3 * mm, yt - rh + 0.5 * mm, cw - 0.6 * mm, rh - 1 * mm, 2, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 6)
        cv.drawCentredString(dx + cw / 2, yt - rh / 2 - 2 * mm, str(d + 1))

    for h, hab in enumerate(cfg["habit_rows"]):
        hy = yt - (h + 1) * rh
        alt = t["Pl"] if h % 2 == 0 else colors.white
        cv.setFillColor(alt); cv.rect(lx, hy - rh + 0.5 * mm, hlw, rh - 1 * mm, fill=1, stroke=0)
        cv.setFillColor(t["TX"] if h < 9 else t["MU"])
        cv.setFont("HN-M" if h < 9 else "HN", 7.5)
        cv.drawString(lx + 2.5 * mm, hy - rh / 2 - 2 * mm, hab)
        for d in range(nd):
            dx = lx + hlw + d * cw
            cv.setFillColor(alt); cv.rect(dx + 0.3 * mm, hy - rh + 0.5 * mm, cw - 0.6 * mm, rh - 1 * mm, fill=1, stroke=0)
            r2 = min(cw, rh) * 0.28
            cv.setStrokeColor(t["R"]); cv.setFillColor(colors.white); cv.setLineWidth(0.4)
            cv.circle(dx + cw / 2, hy - rh / 2, r2, fill=1, stroke=1)

    cv.setStrokeColor(t["P"]); cv.setLineWidth(0.9)
    cv.rect(lx, yt - rh * (nh + 1), rx - lx, rh * (nh + 1), fill=0, stroke=1)

    # Goal + quote box
    qy = yt - rh * (nh + 1) - 4 * mm
    box_h = qy - yb
    if box_h > 15 * mm:
        cv.setFillColor(t["Pl"])
        cv.roundRect(lx, yb, rx - lx, box_h, 6, fill=1, stroke=0)
        cv.setStrokeColor(t["A"]); cv.setLineWidth(4)
        cv.line(lx, yb, lx, qy)
        cv.setFillColor(t["P"]); cv.setFont("HN-B", 8.5)
        cv.drawString(lx + 5 * mm, qy - 8 * mm, cfg["quote"])
        cv.setFillColor(t["MU"]); cv.setFont("HN", 8)
        cv.drawString(lx + 5 * mm, qy - 16 * mm,
                      cfg["goal_label"] + ":  _________________________________________")
        if box_h > 26 * mm:
            cv.drawString(lx + 5 * mm, qy - 24 * mm,
                          cfg["reflection_label"] + ":  ___________________________________")

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

# ── MEAL PLANNER page ─────────────────────────────────────────────────────────

def meal_plan_page(cv, t, cfg, lang_obj):
    bg(cv, t)
    hdr(cv, t, cfg["title"], cfg["subtitle"])
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    # Week label
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, yt + 2 * mm, 80 * mm, 8 * mm, 3, fill=1, stroke=0)
    cv.setFillColor(t["MU"]); cv.setFont("HN", 7.5)
    cv.drawString(lx + 2 * mm, yt + 5.5 * mm, cfg["week_label"] + ": ________________________")

    days = cfg["days"]
    meals = cfg["meals"]
    nd = len(days); nm = len(meals)
    day_col_w = 14 * mm
    meal_col_w = (rx - lx - day_col_w) / nd
    header_h = 8 * mm
    avail = yt - yb - header_h
    row_h = avail / nm

    # Day headers
    for d, day in enumerate(days):
        dx = lx + day_col_w + d * meal_col_w
        iw = d >= 5
        cv.setFillColor(t["WA"] if iw else t["P"])
        cv.rect(dx, yt - header_h, meal_col_w, header_h, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8.5)
        cv.drawCentredString(dx + meal_col_w / 2, yt - header_h / 2 - 2 * mm, day)

    # Meal rows
    for m, meal in enumerate(meals):
        my = yt - header_h - m * row_h
        cv.setFillColor(t["Pl"])
        cv.rect(lx, my - row_h, day_col_w, row_h, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.3)
        cv.rect(lx, my - row_h, day_col_w, row_h, fill=0, stroke=1)
        # Meal label (rotated)
        cv.saveState()
        cx2 = lx + day_col_w / 2
        cy2 = my - row_h / 2
        cv.translate(cx2, cy2)
        cv.rotate(90)
        cv.setFillColor(t["P"]); cv.setFont("HN-B", 7)
        cv.drawCentredString(0, -2.5 * mm, meal)
        cv.restoreState()
        for d in range(nd):
            dx = lx + day_col_w + d * meal_col_w
            iw = d >= 5
            cv.setFillColor(t["WE"] if iw else colors.white)
            cv.rect(dx, my - row_h, meal_col_w, row_h, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.25)
            cv.rect(dx, my - row_h, meal_col_w, row_h, fill=0, stroke=1)
            # Writing lines inside cell
            n_inner = 3
            inner_h = row_h / (n_inner + 1)
            for li in range(n_inner):
                ly2 = my - inner_h * (li + 1)
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.2)
                cv.line(dx + 2 * mm, ly2, dx + meal_col_w - 2 * mm, ly2)

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

def meal_shopping_page(cv, t, cfg, lang_obj):
    bg(cv, t)
    hdr(cv, t, cfg["title"], cfg["shopping_label"])
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    mid = lx + (rx - lx) / 2 - 2 * mm
    rh = 7.5 * mm
    n_rows = int((yt - yb - 15 * mm) / rh)

    for col, col_lx in enumerate([lx, mid + 4 * mm]):
        col_rx = mid if col == 0 else rx
        col_w = col_rx - col_lx
        item_w = col_w - 20 * mm - 8 * mm
        qty_w = 18 * mm
        chk_w = 8 * mm

        # Header
        cv.setFillColor(t["P"]); cv.rect(col_lx, yt - 7 * mm, col_w, 7 * mm, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8)
        cx_label = [col_lx + item_w / 2, col_lx + item_w + qty_w / 2, col_lx + item_w + qty_w + chk_w / 2]
        for i, h in enumerate(cfg["shopping_cols"]):
            cv.drawCentredString(cx_label[i], yt - 4.5 * mm, h)

        for r in range(n_rows):
            ry2 = yt - 7 * mm - r * rh
            cv.setFillColor(t["Pl"] if r % 2 == 0 else colors.white)
            cv.rect(col_lx, ry2 - rh, col_w, rh, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.25)
            cv.rect(col_lx, ry2 - rh, col_w, rh, fill=0, stroke=1)
            # Checkbox circle
            cv.setFillColor(colors.white); cv.setStrokeColor(t["R"]); cv.setLineWidth(0.5)
            cv.circle(col_lx + item_w + qty_w + chk_w / 2, ry2 - rh / 2, 2.5 * mm, fill=1, stroke=1)
            # Qty divider
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.3)
            cv.line(col_lx + item_w, ry2 - rh, col_lx + item_w, ry2)

    # Notes section
    note_y = yt - 7 * mm - n_rows * rh - 4 * mm
    if note_y - yb > 15 * mm:
        cv.setFillColor(t["Pl"])
        cv.roundRect(lx, yb, rx - lx, note_y - yb, 5, fill=1, stroke=0)
        cv.setFillColor(t["P"]); cv.setFont("HN-B", 9)
        cv.drawString(lx + 3 * mm, note_y - 7 * mm, cfg["notes_label"])
        ly = note_y - 13 * mm
        while ly > yb + 4 * mm:
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
            cv.line(lx + 3 * mm, ly, rx - 3 * mm, ly)
            ly -= 8 * mm

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

# ── MONTHLY PLANNER page ──────────────────────────────────────────────────────

def monthly_calendar(cv, t, cfg, lang_obj):
    bg(cv, t)
    hdr(cv, t, cfg["title"], "")
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm

    # Month field
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, yt + 2 * mm, 80 * mm, 8 * mm, 3, fill=1, stroke=0)
    cv.setFillColor(t["MU"]); cv.setFont("HN", 7.5)
    cv.drawString(lx + 2 * mm, yt + 5.5 * mm, cfg["month_label"] + ": ________________________")

    grid_top = yt - 2 * mm
    days_h = 8 * mm
    grid_h = grid_top - yb - 50 * mm  # leave bottom for notes
    cw = (rx - lx) / 7
    row_h = grid_h / 6

    # Day headers
    for d, day in enumerate(cfg["days_header"]):
        dx = lx + d * cw
        iw = d >= 5
        cv.setFillColor(t["WA"] if iw else t["P"])
        cv.rect(dx, grid_top - days_h, cw, days_h, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 9)
        cv.drawCentredString(dx + cw / 2, grid_top - days_h / 2 - 2 * mm, day)

    # Calendar cells
    for row in range(6):
        for col in range(7):
            cx2 = lx + col * cw
            cy2 = grid_top - days_h - row * row_h
            iw = col >= 5
            cv.setFillColor(t["WE"] if iw else colors.white)
            cv.rect(cx2, cy2 - row_h, cw, row_h, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4)
            cv.rect(cx2, cy2 - row_h, cw, row_h, fill=0, stroke=1)
            # Date number circle placeholder
            cv.setFillColor(t["Pl"])
            cv.circle(cx2 + 5 * mm, cy2 - 5 * mm, 3.5 * mm, fill=1, stroke=0)
            cv.setFillColor(t["P"]); cv.setFont("HN-B", 7.5)
            cv.drawCentredString(cx2 + 5 * mm, cy2 - 6.5 * mm, "__")
            # Inner lines for notes
            ly = cy2 - 12 * mm
            while ly > cy2 - row_h + 3 * mm:
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.2)
                cv.line(cx2 + 2 * mm, ly, cx2 + cw - 2 * mm, ly)
                ly -= (row_h - 12 * mm) / 3

    # Notes + goals below calendar
    notes_y = grid_top - days_h - 6 * row_h - 4 * mm
    notes_h = notes_y - yb
    half = (rx - lx - 4 * mm) / 2

    for i, (label, x_start) in enumerate([
        (cfg["goals_label"], lx),
        (cfg["notes_label"], lx + half + 4 * mm),
    ]):
        cv.setFillColor(colors.white)
        cv.roundRect(x_start, yb, half, notes_h, 5, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.5)
        cv.roundRect(x_start, yb, half, notes_h, 5, fill=0, stroke=1)
        cv.setFillColor(t["P"])
        cv.roundRect(x_start, yb + notes_h - 8 * mm, half, 8 * mm, 5, fill=1, stroke=0)
        cv.rect(x_start, yb + notes_h - 8 * mm, half, 4 * mm, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8.5)
        cv.drawString(x_start + 3 * mm, yb + notes_h - 6 * mm, label)
        ly = yb + notes_h - 14 * mm
        while ly > yb + 4 * mm:
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.3)
            cv.line(x_start + 3 * mm, ly, x_start + half - 3 * mm, ly)
            ly -= 8 * mm

    ftr(cv, t, cfg["footer"], lang_obj)
    cv.showPage()

# ── GENERATE ALL ──────────────────────────────────────────────────────────────

BASE = "/Users/vascobotelhodacosta/Morgan/businesses/planners"

PRODUCTS = [
    ("daily_planner",   "daily"),
    ("budget_tracker",  "budget"),
    ("habit_tracker",   "habit"),
    ("meal_planner",    "meal"),
    ("monthly_planner", "monthly"),
]

for lang_code, lang_obj in LANGS.items():
    for product_dir, cfg_key in PRODUCTS:
        cfg = lang_obj[cfg_key]
        out_dir = f"{BASE}/{product_dir}/{lang_code}"
        os.makedirs(out_dir, exist_ok=True)

        for tname, tp in THEMES.items():
            out_path = f"{out_dir}/{cfg['filename']}_{tname}.pdf"
            cv = canvas.Canvas(out_path, pagesize=A4)

            cover_page(cv, tp, cfg, lang_obj, tname)

            if cfg_key == "daily":
                daily_page(cv, tp, cfg, lang_obj)

            elif cfg_key == "budget":
                budget_overview(cv, tp, cfg, lang_obj)
                budget_savings(cv, tp, cfg, lang_obj)

            elif cfg_key == "habit":
                habit_page(cv, tp, cfg, lang_obj)

            elif cfg_key == "meal":
                meal_plan_page(cv, tp, cfg, lang_obj)
                meal_shopping_page(cv, tp, cfg, lang_obj)

            elif cfg_key == "monthly":
                monthly_calendar(cv, tp, cfg, lang_obj)

            cv.save()
            print(f"OK  {lang_code}/{product_dir}/{tname}")

print("\nTodos os PDFs gerados.")
