#!/usr/bin/env python3
"""
PlannerAtlas — Generate Etsy listing copy for all 5 products × 4 languages
"""

import os

BASE = "/Users/vascobotelhodacosta/Morgan/businesses/planners"

LISTINGS = {
    "daily_planner": {
        "DE": {
            "title": "Tagesplaner Druckbar Undatiert | Stündlicher Zeitplan PDF | Tagesplaner A4 | Sofort Download | 3 Farben",
            "price": "4.99",
            "description": """📥 SOFORT-DOWNLOAD — keine Wartezeit, keine Lieferung.

Strukturiere deinen Tag von morgens bis abends mit diesem eleganten, undatierten Tagesplaner. Perfekt für alle, die Klarheit und Fokus in ihren Alltag bringen möchten.

──────────────────────────────
📋 WAS IST ENTHALTEN
──────────────────────────────
✔ Stündlicher Zeitplan (6:00–22:00 Uhr)
✔ Top 3 Prioritäten des Tages
✔ Notizen & Reflexion
✔ Dankbarkeit-Abschnitt
✔ 3 Farboptionen: Indigo, Sage, Terrakotta
✔ Format: A4 | PDF

──────────────────────────────
🖨 SO FUNKTIONIERT'S
──────────────────────────────
1. Kaufe und lade die 3 PDF-Dateien sofort herunter
2. Drucke so viele Seiten, wie du brauchst — täglich
3. Starte organisiert in jeden Tag

──────────────────────────────
💡 WARUM TAGESPLANER?
──────────────────────────────
● Undatiert — du startest jederzeit im Jahr
● Druckbar zuhause — kein teures Notizbuch nötig
● Klar strukturiert — Zeitblöcke + Prioritäten + Reflexion
● 3 Farben inklusive — wähle deine Lieblingsfarbe

──────────────────────────────
📦 NACH DEM KAUF
──────────────────────────────
Du erhältst 3 PDF-Dateien (eine pro Farbe). Öffne mit Adobe Reader oder Preview und drucke auf A4-Papier.

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["tagesplaner pdf", "tagesplaner a4", "planer druckbar", "stunden zeitplan", "tagesplan vorlage", "sofort download", "daily planner de", "organizer druckbar", "zeit planer pdf", "produktivitaet pdf", "tagesplaner vorlage", "druckbar planer"],
        },
        "ES": {
            "title": "Planificador Diario Imprimible Sin Fecha | Horario por Horas PDF | A4 | Descarga Instantánea | 3 Colores",
            "price": "4.99",
            "description": """📥 DESCARGA INSTANTÁNEA — sin esperas, sin envío.

Organiza tu día de la mañana a la noche con este elegante planificador diario sin fecha. Ideal para quienes quieren claridad y enfoque en su rutina diaria.

──────────────────────────────
📋 QUÉ INCLUYE
──────────────────────────────
✔ Horario por horas (6:00–22:00 h)
✔ Top 3 Prioridades del día
✔ Notas & Reflexión
✔ Sección de Agradecimiento
✔ 3 opciones de color: Índigo, Salvia, Terracota
✔ Formato: A4 | PDF

──────────────────────────────
🖨 CÓMO FUNCIONA
──────────────────────────────
1. Compra y descarga los 3 archivos PDF al instante
2. Imprime tantas páginas como necesites — cada día
3. Empieza cada jornada organizado

──────────────────────────────
💡 ¿POR QUÉ ESTE PLANIFICADOR?
──────────────────────────────
● Sin fecha — empieza cualquier día del año
● Imprimible en casa — sin necesidad de agendas caras
● Estructura clara — bloques horarios + prioridades + reflexión
● 3 colores incluidos — elige tu favorito

──────────────────────────────
📦 TRAS LA COMPRA
──────────────────────────────
Recibirás 3 archivos PDF (uno por color). Abre con Adobe Reader y imprime en papel A4.

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["planner diario pdf", "horario diario pdf", "organizador a4", "planner imprimible", "agenda diaria pdf", "planner product", "descarga planner", "daily planner es", "organizer imprimible", "plantilla diaria", "planer sin fecha", "rutina diaria pdf"],
        },
        "PT": {
            "title": "Planeador Diário Imprimível Sem Data | Horário por Horas PDF | A4 | Download Imediato | 3 Cores",
            "price": "4.99",
            "description": """📥 DOWNLOAD IMEDIATO — sem esperas, sem envio.

Organiza o teu dia da manhã à noite com este planeador diário elegante e sem data. Perfeito para quem quer clareza e foco na sua rotina diária.

──────────────────────────────
📋 O QUE INCLUI
──────────────────────────────
✔ Horário por horas (6:00–22:00 h)
✔ Top 3 Prioridades do dia
✔ Notas & Reflexão
✔ Secção de Gratidão
✔ 3 opções de cor: Índigo, Sage, Terracota
✔ Formato: A4 | PDF

──────────────────────────────
🖨 COMO FUNCIONA
──────────────────────────────
1. Compra e faz download dos 3 ficheiros PDF imediatamente
2. Imprime tantas páginas quantas precisares — todos os dias
3. Começa cada dia organizado

──────────────────────────────
💡 PORQUÊ ESTE PLANEADOR?
──────────────────────────────
● Sem data — começas quando quiseres
● Imprimível em casa — sem necessidade de agendas caras
● Estrutura clara — blocos horários + prioridades + reflexão
● 3 cores incluídas — escolhe a tua favorita

──────────────────────────────
📦 APÓS A COMPRA
──────────────────────────────
Recebes 3 ficheiros PDF (um por cor). Abre com Adobe Reader e imprime em papel A4.

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["planner diario pdf", "horario diario pdf", "organizador a4", "planner imprimivel", "agenda diaria pdf", "planer produtividade", "download planner", "daily planner pt", "organizer imprimivel", "planer sem data", "rotina diaria pdf", "planeador diario"],
        },
        "EN": {
            "title": "Daily Planner Printable Undated | Hourly Schedule PDF | A4 | Instant Download | 3 Colors",
            "price": "4.99",
            "description": """📥 INSTANT DOWNLOAD — no waiting, no shipping.

Structure your day from morning to night with this elegant, undated daily planner. Perfect for anyone who wants clarity and focus in their daily routine.

──────────────────────────────
📋 WHAT'S INCLUDED
──────────────────────────────
✔ Hourly schedule (6:00 AM–10:00 PM)
✔ Top 3 Priorities of the day
✔ Notes & Reflection sections
✔ Gratitude section
✔ 3 color options: Indigo, Sage, Terracotta
✔ Format: A4 | PDF

──────────────────────────────
🖨 HOW IT WORKS
──────────────────────────────
1. Purchase and download all 3 PDF files instantly
2. Print as many pages as you need — every day
3. Start each day with intention and clarity

──────────────────────────────
💡 WHY THIS PLANNER?
──────────────────────────────
● Undated — start any day of the year
● Printable at home — no expensive notebook needed
● Clear structure — time blocks + priorities + reflection
● 3 colors included — choose your favourite

──────────────────────────────
📦 AFTER PURCHASE
──────────────────────────────
You'll receive 3 PDF files (one per color). Open with Adobe Reader or Preview and print on A4 paper.

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["daily planner pdf", "hourly planner pdf", "daily schedule pdf", "undated planner", "a4 daily planner", "planner download", "productivity planner", "daily organizer pdf", "planner printable", "time blocking pdf", "daily planner a4", "focus planner pdf"],
        },
    },

    "budget_tracker": {
        "DE": {
            "title": "Haushaltsplaner Druckbar | Budgetplaner PDF | Ausgaben Tracker A4 | Sofort Download | 3 Farben",
            "price": "4.99",
            "description": """📥 SOFORT-DOWNLOAD — keine Wartezeit, keine Lieferung.

Behalte deine Finanzen im Griff mit diesem übersichtlichen, monatlichen Budgetplaner. Einnahmen, Fixkosten, variable Ausgaben, Sparziele — alles auf einen Blick.

──────────────────────────────
📋 WAS IST ENTHALTEN
──────────────────────────────
✔ Monatliche Einnahmen-Übersicht
✔ Fixkosten & variable Ausgaben (je 7 Kategorien)
✔ Monatliche Bilanz (Einnahmen – Ausgaben = Saldo)
✔ Sparziele-Tracker mit Fortschrittsbalken
✔ Wöchentliches Ausgaben-Log (Datum, Beschreibung, Kategorie, Betrag)
✔ 3 Farboptionen: Indigo, Sage, Terrakotta
✔ Format: A4 | PDF (2 Seiten pro Monat)

──────────────────────────────
🖨 SO FUNKTIONIERT'S
──────────────────────────────
1. Kaufe und lade die 3 PDF-Dateien sofort herunter
2. Drucke einmal pro Monat — für das ganze Jahr
3. Fülle Einnahmen, Ausgaben und Sparziele aus

──────────────────────────────
💡 WARUM DIESER PLANER?
──────────────────────────────
● Klar strukturiert — alle Finanzen auf 2 Seiten
● Sparziele mit Fortschritt — motiviert zum Sparen
● Wöchentliches Log — jede Ausgabe im Blick
● Druckbar zuhause — starte sofort

──────────────────────────────
📦 NACH DEM KAUF
──────────────────────────────
Du erhältst 3 PDF-Dateien (je 2 Seiten pro Farbe). Drucke auf A4-Papier, einmal monatlich.

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["budgetplaner pdf", "ausgaben tracker", "finanzplaner pdf", "haushaltsbuch pdf", "budget planer a4", "sparziele tracker", "finanzuebersicht pdf", "monatsbudget pdf", "haushaltsplan pdf", "geld planer pdf", "ausgaben vorlage", "budget druckbar"],
        },
        "ES": {
            "title": "Control de Gastos Imprimible | Planificador de Presupuesto Mensual PDF | A4 | Descarga Instantánea | 3 Colores",
            "price": "4.99",
            "description": """📥 DESCARGA INSTANTÁNEA — sin esperas, sin envío.

Toma el control de tus finanzas con este planificador de presupuesto mensual. Ingresos, gastos fijos, gastos variables, objetivos de ahorro — todo en un vistazo.

──────────────────────────────
📋 QUÉ INCLUYE
──────────────────────────────
✔ Resumen mensual de ingresos
✔ Gastos fijos & variables (7 categorías cada uno)
✔ Balance mensual (Ingresos – Gastos = Saldo)
✔ Tracker de objetivos de ahorro con barra de progreso
✔ Registro semanal de gastos (fecha, descripción, categoría, importe)
✔ 3 opciones de color: Índigo, Salvia, Terracota
✔ Formato: A4 | PDF (2 páginas por mes)

──────────────────────────────
💡 ¿POR QUÉ ESTE PLANIFICADOR?
──────────────────────────────
● Estructura clara — todas tus finanzas en 2 páginas
● Objetivos de ahorro con progreso — te mantiene motivado
● Registro semanal — ningún gasto se escapa
● Imprimible en casa — empieza hoy mismo

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["presupuesto pdf", "tracker gastos pdf", "finanzas pdf", "presupuesto mensual", "planner financiero", "ahorro tracker pdf", "gastos plantilla", "organizador finanzas", "budget planner es", "planner gastos a4", "control gastos pdf", "gastos mensuales"],
        },
        "PT": {
            "title": "Controlo de Despesas Imprimível | Orçamento Mensal PDF | A4 | Download Imediato | 3 Cores",
            "price": "4.99",
            "description": """📥 DOWNLOAD IMEDIATO — sem esperas, sem envio.

Toma controlo das tuas finanças com este planeador de orçamento mensal. Rendimentos, despesas fixas, despesas variáveis, objetivos de poupança — tudo de um relance.

──────────────────────────────
📋 O QUE INCLUI
──────────────────────────────
✔ Resumo mensal de rendimentos
✔ Despesas fixas & variáveis (7 categorias cada)
✔ Balanço mensal (Rendimentos – Despesas = Saldo)
✔ Tracker de poupança com barra de progresso
✔ Registo semanal de despesas
✔ 3 opções de cor: Índigo, Sage, Terracota
✔ Formato: A4 | PDF (2 páginas por mês)

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["orcamento mensal pdf", "tracker despesas", "financas pdf", "planer financ pdf", "poupanca tracker", "despesas mensais pdf", "download financas", "budget planner pt", "planner gastos a4", "organizador financas", "gestao financeira", "ctrl despesas pdf"],
        },
        "EN": {
            "title": "Budget Tracker Printable | Monthly Budget Planner PDF | Expense Tracker A4 | Instant Download | 3 Colors",
            "price": "4.99",
            "description": """📥 INSTANT DOWNLOAD — no waiting, no shipping.

Take control of your finances with this clear, monthly budget planner. Income, fixed expenses, variable costs, savings goals — all at a glance.

──────────────────────────────
📋 WHAT'S INCLUDED
──────────────────────────────
✔ Monthly income overview
✔ Fixed & variable expenses (7 categories each)
✔ Monthly balance (Income – Expenses = Balance)
✔ Savings goals tracker with progress bar
✔ Weekly expense log (date, description, category, amount)
✔ 3 color options: Indigo, Sage, Terracotta
✔ Format: A4 | PDF (2 pages per month)

──────────────────────────────
💡 WHY THIS PLANNER?
──────────────────────────────
● Clear structure — all finances on 2 pages
● Savings goals with progress — stay motivated
● Weekly log — track every expense
● Printable at home — start today

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["budget tracker pdf", "expense tracker pdf", "budget planner pdf", "monthly budget pdf", "savings tracker pdf", "finance planner", "budget worksheet pdf", "budget download", "money planner pdf", "spending tracker a4", "budget printable", "finance tracker a4"],
        },
    },

    "habit_tracker": {
        "DE": {
            "title": "Habit Tracker Druckbar | Gewohnheiten Tracker PDF Monatlich | A4 | Sofort Download | 3 Farben",
            "price": "3.99",
            "description": """📥 SOFORT-DOWNLOAD — keine Wartezeit, keine Lieferung.

Baue positive Gewohnheiten auf mit diesem übersichtlichen, monatlichen Habit Tracker. 31 Tage, 10 Gewohnheiten, 3 Farben — einfach, effektiv, schön.

──────────────────────────────
📋 WAS IST ENTHALTEN
──────────────────────────────
✔ 31-Tage Habit Tracker (Kreise zum Ankreuzen)
✔ 10 vorausgefüllte + 1 eigene Gewohnheit
✔ Monatsziels-Feld
✔ Reflexion des Monats
✔ Motivierendes Zitat
✔ 3 Farboptionen: Indigo, Sage, Terrakotta
✔ Format: A4 | PDF

──────────────────────────────
💡 WARUM DIESER TRACKER?
──────────────────────────────
● Wissenschaftlich belegt — Gewohnheiten brauchen 21–66 Tage
● Druckbar und anpassbar — wähle deine eigenen Ziele
● Jeden Monat neu starten — einfach erneut drucken
● Kleines Format, große Wirkung

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["habit tracker pdf", "gewohnheiten pdf", "habit tracker a4", "routinen tracker", "habit tracker de", "gewohnheitstracker", "produktivitaet pdf", "ziele tracker pdf", "habit vorlage pdf", "gewohnheiten ziele", "tracker druckbar", "monat tracker pdf"],
        },
        "ES": {
            "title": "Rastreador de Hábitos Imprimible | Tracker de Hábitos PDF Mensual | A4 | Descarga Instantánea | 3 Colores",
            "price": "3.99",
            "description": """📥 DESCARGA INSTANTÁNEA — sin esperas, sin envío.

Construye hábitos positivos con este tracker mensual claro y motivador. 31 días, 10 hábitos, 3 colores — simple, efectivo y bonito.

──────────────────────────────
📋 QUÉ INCLUYE
──────────────────────────────
✔ Tracker de 31 días (círculos para marcar)
✔ 10 hábitos preestablecidos + 1 personalizable
✔ Campo de objetivo mensual
✔ Reflexión del mes
✔ Cita motivadora
✔ 3 opciones de color: Índigo, Salvia, Terracota
✔ Formato: A4 | PDF

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["tracker habitos pdf", "habitos mensuales", "rutinas tracker pdf", "planner habitos a4", "habit tracker es", "seguimiento habitos", "tracker mensual pdf", "habitos diarios pdf", "rutinas pdf", "habitos tracker", "planer rutinas pdf", "habitos 31 dias"],
        },
        "PT": {
            "title": "Rastreador de Hábitos Imprimível | Tracker de Hábitos PDF Mensal | A4 | Download Imediato | 3 Cores",
            "price": "3.99",
            "description": """📥 DOWNLOAD IMEDIATO — sem esperas, sem envio.

Constrói hábitos positivos com este tracker mensal claro e motivador. 31 dias, 10 hábitos, 3 cores — simples, eficaz e bonito.

──────────────────────────────
📋 O QUE INCLUI
──────────────────────────────
✔ Tracker de 31 dias (círculos para marcar)
✔ 10 hábitos pré-definidos + 1 personalizável
✔ Campo de objetivo mensal
✔ Reflexão do mês
✔ Citação motivadora
✔ 3 opções de cor: Índigo, Sage, Terracota
✔ Formato: A4 | PDF

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["tracker habitos pdf", "habitos mensal pdf", "rotinas tracker pdf", "planner habitos a4", "habit tracker pt", "habitos diarios pdf", "tracker mensal pdf", "planer rotinas pdf", "tracker produt", "habitos 31 dias", "rotinas pdf", "habitos tracker"],
        },
        "EN": {
            "title": "Habit Tracker Printable | Monthly Habit Tracker PDF | A4 | Instant Download | 3 Colors",
            "price": "3.99",
            "description": """📥 INSTANT DOWNLOAD — no waiting, no shipping.

Build positive habits with this clean, monthly habit tracker. 31 days, 10 habits, 3 colors — simple, effective, and beautiful.

──────────────────────────────
📋 WHAT'S INCLUDED
──────────────────────────────
✔ 31-day habit tracker (circles to fill in)
✔ 10 pre-filled habits + 1 custom habit slot
✔ Monthly goal field
✔ Monthly reflection section
✔ Motivating quote
✔ 3 color options: Indigo, Sage, Terracotta
✔ Format: A4 | PDF

──────────────────────────────
💡 WHY THIS TRACKER?
──────────────────────────────
● Science-backed — habits take 21–66 days to form
● Printable and customizable — choose your own goals
● Fresh start each month — just print again
● Small effort, big results

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["habit tracker pdf", "habit tracker 31d", "habit tracker a4", "daily habit tracker", "routine tracker pdf", "productivity tracker", "habit log printable", "30 day tracker pdf", "wellness tracker pdf", "habit download", "habit planner pdf", "tracker printable"],
        },
    },

    "meal_planner": {
        "DE": {
            "title": "Mahlzeitenplaner Druckbar | Wöchentlicher Essensplan PDF + Einkaufsliste | A4 | Sofort Download | 3 Farben",
            "price": "3.99",
            "description": """📥 SOFORT-DOWNLOAD — keine Wartezeit, keine Lieferung.

Plane deine Mahlzeiten für die ganze Woche und spare Zeit & Geld beim Einkaufen. Mit integrierter Einkaufsliste — alles auf einen Blick.

──────────────────────────────
📋 WAS IST ENTHALTEN
──────────────────────────────
✔ Wöchentlicher Mahlzeitenplan (Mo–So)
✔ 4 Mahlzeiten: Frühstück, Mittagessen, Abendessen, Snacks
✔ Integrierte Einkaufsliste mit Menge & Checkbox
✔ Notizenfeld
✔ 3 Farboptionen: Indigo, Sage, Terrakotta
✔ Format: A4 | PDF (2 Seiten)

──────────────────────────────
💡 WARUM DIESER PLANER?
──────────────────────────────
● Weniger Lebensmittelverschwendung — du planst was du brauchst
● Gesünder essen — bewusste Mahlzeitenplanung
● Einkaufszeit halbieren — mit integrierter Liste
● Jede Woche neu ausdrucken — immer frisch

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["essensplan pdf", "mahlzeiten pdf", "wochenplan essen", "meal planner de", "einkaufsliste pdf", "ernaehrungsplan pdf", "speiseplan pdf", "mahlzeiten a4", "meal prep pdf", "speiseplan vorlage", "einkaufszettel pdf", "wochenessen planer"],
        },
        "ES": {
            "title": "Planificador de Comidas Imprimible | Plan Semanal Alimentación PDF + Lista Compra | A4 | Descarga Instantánea",
            "price": "3.99",
            "description": """📥 DESCARGA INSTANTÁNEA — sin esperas, sin envío.

Planifica tus comidas para toda la semana y ahorra tiempo y dinero en el supermercado. Con lista de la compra integrada — todo a la vista.

──────────────────────────────
📋 QUÉ INCLUYE
──────────────────────────────
✔ Plan semanal de comidas (Lun–Dom)
✔ 4 comidas: Desayuno, Almuerzo, Cena, Snacks
✔ Lista de la compra integrada con cantidad & checkbox
✔ Campo de notas
✔ 3 opciones de color: Índigo, Salvia, Terracota
✔ Formato: A4 | PDF (2 páginas)

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["menu semanal pdf", "plan comidas pdf", "meal planner es", "lista compra pdf", "alimentacion pdf", "planer comidas pdf", "meal prep es", "dieta semanal pdf", "compra semanal pdf", "menu imprimible a4", "comidas semana pdf", "plan alimentacion"],
        },
        "PT": {
            "title": "Planeador de Refeições Imprimível | Plano Semanal Alimentação PDF + Lista Compras | A4 | Download Imediato",
            "price": "3.99",
            "description": """📥 DOWNLOAD IMEDIATO — sem esperas, sem envio.

Planeia as tuas refeições para a semana inteira e poupa tempo e dinheiro nas compras. Com lista de compras integrada — tudo à vista.

──────────────────────────────
📋 O QUE INCLUI
──────────────────────────────
✔ Plano semanal de refeições (Seg–Dom)
✔ 4 refeições: Pequeno-almoço, Almoço, Jantar, Snacks
✔ Lista de compras integrada com quantidade & checkbox
✔ Campo de notas
✔ 3 opções de cor: Índigo, Sage, Terracota
✔ Formato: A4 | PDF (2 páginas)

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["refeicoes pdf", "plano refeicoes pdf", "meal planner pt", "lista compras pdf", "alimentacao pdf", "planer refeicoes pdf", "meal prep pt", "dieta semanal pdf", "compras semanais pdf", "menu imprimivel a4", "refeicoes semana", "plano alimentacao"],
        },
        "EN": {
            "title": "Meal Planner Printable | Weekly Meal Plan PDF + Grocery List | A4 | Instant Download | 3 Colors",
            "price": "3.99",
            "description": """📥 INSTANT DOWNLOAD — no waiting, no shipping.

Plan your meals for the whole week and save time & money on groceries. Integrated shopping list included — everything at a glance.

──────────────────────────────
📋 WHAT'S INCLUDED
──────────────────────────────
✔ Weekly meal plan (Mon–Sun)
✔ 4 meals: Breakfast, Lunch, Dinner, Snacks
✔ Integrated grocery list with quantity & checkbox
✔ Notes field
✔ 3 color options: Indigo, Sage, Terracotta
✔ Format: A4 | PDF (2 pages)

──────────────────────────────
💡 WHY THIS PLANNER?
──────────────────────────────
● Less food waste — plan what you actually need
● Eat healthier — intentional meal planning
● Half your shopping time — with integrated list
● Print fresh every week

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["meal planner pdf", "weekly meal plan pdf", "meal plan printable", "grocery list pdf", "meal planner a4", "meal plan template", "meal prep pdf", "food planner pdf", "dinner plan pdf", "shopping list pdf", "meal tracker pdf", "weekly food planner"],
        },
    },

    "monthly_planner": {
        "DE": {
            "title": "Monatsplaner Druckbar Undatiert | Monatskalender PDF | Monatsziele & Notizen | A4 | Sofort Download | 3 Farben",
            "price": "3.99",
            "description": """📥 SOFORT-DOWNLOAD — keine Wartezeit, keine Lieferung.

Behalte den Überblick über jeden Monat mit diesem eleganten, undatierten Monatsplaner. Kalenderraster + Monatsziele + Notizen — alles auf einer Seite.

──────────────────────────────
📋 WAS IST ENTHALTEN
──────────────────────────────
✔ Undatierter Monatskalender (6 Wochen × 7 Tage)
✔ Datumsfelder zum selbst Eintragen
✔ Monatsziele-Bereich
✔ Wichtige Termine & Notizen
✔ 3 Farboptionen: Indigo, Sage, Terrakotta
✔ Format: A4 | PDF

──────────────────────────────
💡 WARUM DIESER KALENDER?
──────────────────────────────
● Undatiert — passt für jeden Monat, jedes Jahr
● Übersicht + Ziele auf einer Seite
● Druckbar zuhause — kein Kalender kaufen nötig
● Minimalistisches Design — klar und fokussiert

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["monatsplaner pdf", "monatskalender pdf", "kalender druckbar a4", "monatlicher planer", "monat uebersicht pdf", "ziele monat pdf", "monatsplaner vorlage", "kalender vorlage pdf", "kalender download", "monat planer pdf", "kalender pdf a4", "jahresplaner pdf"],
        },
        "ES": {
            "title": "Planificador Mensual Imprimible Sin Fecha | Calendario Mensual PDF | Objetivos & Notas | A4 | Descarga Instantánea",
            "price": "3.99",
            "description": """📥 DESCARGA INSTANTÁNEA — sin esperas, sin envío.

Mantén el control de cada mes con este elegante planificador mensual sin fecha. Cuadrícula de calendario + objetivos mensuales + notas — todo en una página.

──────────────────────────────
📋 QUÉ INCLUYE
──────────────────────────────
✔ Calendario mensual sin fecha (6 semanas × 7 días)
✔ Casillas de fecha para rellenar
✔ Sección de objetivos del mes
✔ Fechas importantes & notas
✔ 3 opciones de color: Índigo, Salvia, Terracota
✔ Formato: A4 | PDF

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["cal mensual pdf", "planner mensual pdf", "calendario a4 pdf", "planer mensual pdf", "vista mensual pdf", "objetivos mes pdf", "planer mes plantilla", "calendario plantilla", "calendario descarga", "mes planner pdf", "calendario sin fecha", "agenda mensual pdf"],
        },
        "PT": {
            "title": "Planeador Mensal Imprimível Sem Data | Calendário Mensal PDF | Objetivos & Notas | A4 | Download Imediato",
            "price": "3.99",
            "description": """📥 DOWNLOAD IMEDIATO — sem esperas, sem envio.

Mantém o controlo de cada mês com este elegante planeador mensal sem data. Grelha de calendário + objetivos mensais + notas — tudo numa página.

──────────────────────────────
📋 O QUE INCLUI
──────────────────────────────
✔ Calendário mensal sem data (6 semanas × 7 dias)
✔ Campos de data para preencher
✔ Secção de objetivos do mês
✔ Datas importantes & notas
✔ 3 opções de cor: Índigo, Sage, Terracota
✔ Formato: A4 | PDF

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["cal mensal pdf", "planner mensal pdf", "calendario a4 pdf", "planer mensal pdf", "vista mensal pdf", "objetivos mes pdf", "planer mes modelo", "calendario modelo", "calendario download", "mes planner pdf", "calendario sem data", "agenda mensal pdf"],
        },
        "EN": {
            "title": "Monthly Planner Printable Undated | Monthly Calendar PDF | Goals & Notes | A4 | Instant Download | 3 Colors",
            "price": "3.99",
            "description": """📥 INSTANT DOWNLOAD — no waiting, no shipping.

Keep track of every month with this elegant, undated monthly planner. Calendar grid + monthly goals + notes — all on one page.

──────────────────────────────
📋 WHAT'S INCLUDED
──────────────────────────────
✔ Undated monthly calendar (6 weeks × 7 days)
✔ Date fields to fill in yourself
✔ Monthly goals section
✔ Important dates & notes
✔ 3 color options: Indigo, Sage, Terracotta
✔ Format: A4 | PDF

──────────────────────────────
💡 WHY THIS PLANNER?
──────────────────────────────
● Undated — works for any month, any year
● Overview + goals on one page
● Printable at home — no calendar purchase needed
● Minimal design — clean and focused

PlannerAtlas · planneratlas.etsy.com""",
            "tags": ["monthly planner pdf", "monthly calendar pdf", "calendar a4 pdf", "monthly overview pdf", "goals monthly pdf", "cal template pdf", "monthly template pdf", "cal download pdf", "undated planner pdf", "month planner pdf", "monthly goals pdf", "planner a4 pdf"],
        },
    },
}


def write_listing(product_dir, lang, data):
    out_dir = f"{BASE}/{product_dir}/{lang}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/listing_{lang}.md"

    tags_str = ", ".join(data["tags"])
    content = f"""# Etsy Listing — {product_dir.replace('_', ' ').title()} ({lang})

## Título
{data['title']}

## Preço
€{data['price']}

## Categoria
Crafts & Supplies > Patterns & How To > Patterns

## Quando foi feito?
2020–2026

## Quem o fez?
Eu próprio

## É um produto físico?
Não — Ficheiro digital

## Descrição
{data['description']}

## Tags (máx. 13)
{tags_str}

## Renovação automática
Sim

## Ficheiros a fazer upload
- {product_dir.split('_')[0]}_{lang.lower()}_indigo.pdf
- {product_dir.split('_')[0]}_{lang.lower()}_sage.pdf
- {product_dir.split('_')[0]}_{lang.lower()}_terracotta.pdf

## Mockup principal
mockup_{lang}_indigo.jpg

## Mockups adicionais
mockup_{lang}_sage.jpg
mockup_{lang}_terracotta.jpg
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK  {product_dir}/{lang}/listing_{lang}.md")


for product_dir, langs in LISTINGS.items():
    print(f"\n[{product_dir}]")
    for lang, data in langs.items():
        write_listing(product_dir, lang, data)

print("\nTodos os listings gerados.")

# ── Weekly Planner listings (separate run) ────────────────────────────────────

WEEKLY_LISTINGS = {
    "PT": {
        "title": "Planeador Semanal Imprimível | 52 Semanas PDF + Vista Anual & Mensal | A4 | Download Imediato | 3 Cores",
        "price": "4.99",
        "description": """📥 DOWNLOAD IMEDIATO — sem esperas, sem envio.

Organiza a tua semana, o teu mês e o teu ano com este planeador semanal completo. 52 semanas, vista anual, vista mensal — tudo num único PDF.

──────────────────────────────
📋 O QUE INCLUI
──────────────────────────────
✔ Vista anual (calendário do ano)
✔ Vista mensal (objetivos & notas do mês)
✔ 52 semanas (Seg–Dom com blocos de tarefas)
✔ Espaço para objetivo da semana
✔ 3 opções de cor: Índigo, Sage, Terracota
✔ Formato: A4 | PDF

──────────────────────────────
💡 PORQUÊ ESTE PLANEADOR?
──────────────────────────────
● Visão completa do ano numa só compra
● Sem data — usar em qualquer ano
● Imprimível em casa — sem agendas caras
● 3 cores incluídas — escolhe a tua favorita

──────────────────────────────
📦 APÓS A COMPRA
──────────────────────────────
Recebes 3 ficheiros PDF (um por cor). Imprime em papel A4.

PlannerAtlas · planneratlas.etsy.com""",
        "tags": ["planeador semanal pdf", "planner semanal a4", "52 semanas pdf", "agenda semanal pdf", "planer semanal pt", "vista semanal pdf", "planner imprimivel", "agenda 2025 pdf", "semanal download", "planer sem data", "organizador semanal", "weekly planner pt"],
        "filename": "planeador_PT",
    },
    "ES": {
        "title": "Planificador Semanal Imprimible | 52 Semanas PDF + Vista Anual & Mensual | A4 | Descarga Instantánea | 3 Colores",
        "price": "4.99",
        "description": """📥 DESCARGA INSTANTÁNEA — sin esperas, sin envío.

Organiza tu semana, tu mes y tu año con este planificador semanal completo. 52 semanas, vista anual, vista mensual — todo en un único PDF.

──────────────────────────────
📋 QUÉ INCLUYE
──────────────────────────────
✔ Vista anual (calendario del año)
✔ Vista mensual (objetivos & notas del mes)
✔ 52 semanas (Lun–Dom con bloques de tareas)
✔ Espacio para objetivo de la semana
✔ 3 opciones de color: Índigo, Salvia, Terracota
✔ Formato: A4 | PDF

──────────────────────────────
💡 ¿POR QUÉ ESTE PLANIFICADOR?
──────────────────────────────
● Visión completa del año en una sola compra
● Sin fecha — válido para cualquier año
● Imprimible en casa — sin agendas caras
● 3 colores incluidos — elige tu favorito

PlannerAtlas · planneratlas.etsy.com""",
        "tags": ["planner semanal pdf", "planificador a4", "52 semanas pdf", "agenda semanal pdf", "planer semanal es", "vista semanal pdf", "planner imprimible", "agenda 2025 pdf", "semanal descarga", "planer sin fecha", "organizador semanal", "weekly planner es"],
        "filename": "planificador_ES",
    },
    "DE": {
        "title": "Wochenplaner Druckbar | 52 Wochen PDF + Jahres- & Monatsansicht | A4 | Sofort Download | 3 Farben",
        "price": "4.99",
        "description": """📥 SOFORT-DOWNLOAD — keine Wartezeit, keine Lieferung.

Plane deine Woche, deinen Monat und dein Jahr mit diesem vollständigen Wochenplaner. 52 Wochen, Jahresansicht, Monatsansicht — alles in einem PDF.

──────────────────────────────
📋 WAS IST ENTHALTEN
──────────────────────────────
✔ Jahresansicht (Kalender des Jahres)
✔ Monatsansicht (Ziele & Notizen des Monats)
✔ 52 Wochen (Mo–So mit Aufgabenblöcken)
✔ Feld für Wochenziel
✔ 3 Farboptionen: Indigo, Sage, Terrakotta
✔ Format: A4 | PDF

──────────────────────────────
💡 WARUM DIESER PLANER?
──────────────────────────────
● Vollständige Jahresübersicht in einem Kauf
● Undatiert — für jedes Jahr verwendbar
● Druckbar zuhause — kein teures Notizbuch
● 3 Farben inklusive — wähle deine Lieblingsfarbe

PlannerAtlas · planneratlas.etsy.com""",
        "tags": ["wochenplaner pdf", "wochenplaner a4", "52 wochen pdf", "agenda woche pdf", "planer wochen de", "jahresplaner pdf", "planer druckbar", "kalender 2025 pdf", "wochen download", "undatiert planer", "organizer wochen", "weekly planner de"],
        "filename": "wochenplaner_DE",
    },
    "EN": {
        "title": "Weekly Planner Printable | 52 Weeks PDF + Yearly & Monthly View | A4 | Instant Download | 3 Colors",
        "price": "4.99",
        "description": """📥 INSTANT DOWNLOAD — no waiting, no shipping.

Plan your week, your month and your year with this complete weekly planner. 52 weeks, yearly view, monthly view — all in one PDF.

──────────────────────────────
📋 WHAT'S INCLUDED
──────────────────────────────
✔ Yearly view (full year calendar)
✔ Monthly view (goals & notes for the month)
✔ 52 weeks (Mon–Sun with task blocks)
✔ Weekly goal field
✔ 3 color options: Indigo, Sage, Terracotta
✔ Format: A4 | PDF

──────────────────────────────
💡 WHY THIS PLANNER?
──────────────────────────────
● Complete year overview in one purchase
✔ Undated — use for any year
● Printable at home — no expensive notebooks
● 3 colors included — choose your favourite

PlannerAtlas · planneratlas.etsy.com""",
        "tags": ["weekly planner pdf", "weekly planner a4", "52 weeks planner", "undated planner pdf", "yearly planner pdf", "planner download", "weekly agenda pdf", "planner printable", "annual planner pdf", "week planner pdf", "productivity pdf", "weekly organizer"],
        "filename": "weekly_planner_EN",
    },
}

print("\n[weekly_planner]")
for lang, data in WEEKLY_LISTINGS.items():
    out_dir = f"{BASE}/weekly_planner/{lang}"
    os.makedirs(out_dir, exist_ok=True)
    tags_str = ", ".join(data["tags"])
    content = f"""# Etsy Listing — Weekly Planner ({lang})

## Título
{data['title']}

## Preço
€{data['price']}

## Categoria
Crafts & Supplies > Patterns & How To > Patterns

## Quando foi feito?
2020–2026

## Quem o fez?
Eu próprio

## É um produto físico?
Não — Ficheiro digital

## Descrição
{data['description']}

## Tags (máx. 13)
{tags_str}

## Renovação automática
Sim

## Ficheiros a fazer upload
- {data['filename']}_indigo.pdf
- {data['filename']}_sage.pdf
- {data['filename']}_terracotta.pdf

## Mockup principal
mockup_{lang}_indigo.jpg

## Mockups adicionais
mockup_{lang}_sage.jpg
mockup_{lang}_terracotta.jpg
"""
    with open(f"{out_dir}/listing_{lang}.md", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK  weekly_planner/{lang}/listing_{lang}.md")
