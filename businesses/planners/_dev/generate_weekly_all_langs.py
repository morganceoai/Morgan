#!/usr/bin/env python3
"""
PlannerAtlas — Weekly Planner for all 4 languages
DE / ES / PT / EN — fixed: no subtitle on cover, PA monogram, no tip box, footer clearance
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

import os as _os
PLAYFAIR = _os.path.join(_os.path.dirname(__file__), "../_assets/fonts/PlayfairDisplay-Bold.ttf")
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

LANGS = {
    "DE": {
        "title": "Wochenplaner",
        "filename": "wochenplaner_DE",
        "outdir": "weekly_planner/DE",
        "contents_label": "Inhalt",
        "cover_items": ["Jahresübersicht", "Monatsübersicht", "Wochenplaner", "Habit Tracker", "Notizseiten"],
        "months": ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"],
        "days": [("Mo","Montag"),("Di","Dienstag"),("Mi","Mittwoch"),("Do","Donnerstag"),("Fr","Freitag"),("Sa","Samstag"),("So","Sonntag")],
        "week_header": "Wochenplaner",
        "week_sub": "KW ____  ·  ____. _______________ ______",
        "month_header": "Monatsübersicht",
        "year_header": "Jahresübersicht",
        "sidebar": [("Diese Woche", 3), ("Ziele der Woche", 4), ("Notizen", 7), ("Reflexion", 3)],
        "notes_label": "Notizen & Ziele des Monats",
        "habit_header": "Habit Tracker",
        "habit_sub": "_______________ · ______",
        "habit_rows": ["Sport / Bewegung","Wasser (2 Liter)","Gesund ernähren","Lesen (30 Min.)","Meditation","Früh aufstehen","Kein Social Media","Journaling","Dankbarkeit","Eigenes Ziel: ___"],
        "habit_quote": "\"Kleine Schritte täglich führen zu großen Veränderungen.\"",
        "habit_goal": "Mein Monatsziel",
        "notes_page": "Notizen",
        "priority_label": "Priorität des Tages",
        "footer_week": "Wochenplaner",
        "footer_month": "Monatsübersicht",
        "footer_year": "Jahresübersicht",
        "footer_habit": "Habit Tracker",
        "footer_notes": "Notizen",
    },
    "ES": {
        "title": "Planificador Semanal",
        "filename": "planificador_ES",
        "outdir": "weekly_planner/ES",
        "contents_label": "Contenido",
        "cover_items": ["Vista anual", "Vista mensual", "Planificador semanal", "Rastreador de hábitos", "Páginas de notas"],
        "months": ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"],
        "days": [("Lun","Lunes"),("Mar","Martes"),("Mié","Miércoles"),("Jue","Jueves"),("Vie","Viernes"),("Sáb","Sábado"),("Dom","Domingo")],
        "week_header": "Planificador Semanal",
        "week_sub": "Sem. ____  ·  ____. _______________ ______",
        "month_header": "Vista Mensual",
        "year_header": "Vista Anual",
        "sidebar": [("Esta semana", 3), ("Objetivos de la semana", 4), ("Notas", 7), ("Reflexión", 3)],
        "notes_label": "Notas y objetivos del mes",
        "habit_header": "Rastreador de Hábitos",
        "habit_sub": "_______________ · ______",
        "habit_rows": ["Ejercicio físico","Agua (2 litros)","Alimentación sana","Lectura (30 min.)","Meditación","Madrugar","Sin redes sociales","Journaling","Gratitud","Mi objetivo: ___"],
        "habit_quote": "\"Pequeños pasos cada día llevan a grandes cambios.\"",
        "habit_goal": "Mi objetivo del mes",
        "notes_page": "Notas",
        "priority_label": "Prioridad del día",
        "footer_week": "Planificador Semanal",
        "footer_month": "Vista Mensual",
        "footer_year": "Vista Anual",
        "footer_habit": "Rastreador de Hábitos",
        "footer_notes": "Notas",
    },
    "PT": {
        "title": "Planeador Semanal",
        "filename": "planeador_PT",
        "outdir": "weekly_planner/PT",
        "contents_label": "Conteúdo",
        "cover_items": ["Vista anual", "Vista mensal", "Planeador semanal", "Rastreador de hábitos", "Páginas de notas"],
        "months": ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"],
        "days": [("Seg","Segunda"),("Ter","Terça"),("Qua","Quarta"),("Qui","Quinta"),("Sex","Sexta"),("Sáb","Sábado"),("Dom","Domingo")],
        "week_header": "Planeador Semanal",
        "week_sub": "Sem. ____  ·  ____. _______________ ______",
        "month_header": "Vista Mensal",
        "year_header": "Vista Anual",
        "sidebar": [("Esta semana", 3), ("Objetivos da semana", 4), ("Notas", 7), ("Reflexão", 3)],
        "notes_label": "Notas e objetivos do mês",
        "habit_header": "Rastreador de Hábitos",
        "habit_sub": "_______________ · ______",
        "habit_rows": ["Exercício físico","Água (2 litros)","Alimentação saudável","Leitura (30 min.)","Meditação","Acordar cedo","Sem redes sociais","Journaling","Gratidão","O meu objetivo: ___"],
        "habit_quote": "\"Pequenos passos diários levam a grandes mudanças.\"",
        "habit_goal": "O meu objetivo do mês",
        "notes_page": "Notas",
        "priority_label": "Prioridade do dia",
        "footer_week": "Planeador Semanal",
        "footer_month": "Vista Mensal",
        "footer_year": "Vista Anual",
        "footer_habit": "Rastreador de Hábitos",
        "footer_notes": "Notas",
    },
    "EN": {
        "title": "Weekly Planner",
        "filename": "weekly_planner_EN",
        "outdir": "weekly_planner/EN",
        "contents_label": "Contents",
        "cover_items": ["Yearly overview", "Monthly overview", "Weekly planner", "Habit tracker", "Notes pages"],
        "months": ["January","February","March","April","May","June","July","August","September","October","November","December"],
        "days": [("Mon","Monday"),("Tue","Tuesday"),("Wed","Wednesday"),("Thu","Thursday"),("Fri","Friday"),("Sat","Saturday"),("Sun","Sunday")],
        "week_header": "Weekly Planner",
        "week_sub": "Week ____  ·  ____. _______________ ______",
        "month_header": "Monthly Overview",
        "year_header": "Yearly Overview",
        "sidebar": [("This week", 3), ("Weekly goals", 4), ("Notes", 7), ("Reflection", 3)],
        "notes_label": "Notes & goals of the month",
        "habit_header": "Habit Tracker",
        "habit_sub": "_______________ · ______",
        "habit_rows": ["Exercise / Movement","Water (2 litres)","Healthy eating","Reading (30 min.)","Meditation","Early rising","No social media","Journaling","Gratitude","My own goal: ___"],
        "habit_quote": "\"Small daily steps lead to big changes.\"",
        "habit_goal": "My monthly goal",
        "notes_page": "Notes",
        "priority_label": "Priority of the day",
        "footer_week": "Weekly Planner",
        "footer_month": "Monthly Overview",
        "footer_year": "Yearly Overview",
        "footer_habit": "Habit Tracker",
        "footer_notes": "Notes",
    },
}

BASE = "/Users/vascobotelhodacosta/Morgan/businesses/planners"

def bg(cv, t):
    cv.setFillColor(t["BG"]); cv.rect(0, 0, W, H, fill=1, stroke=0)

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

def ftr(cv, t, label):
    fh = MB - 2 * mm
    cv.setFillColor(t["P"]); cv.rect(0, 0, W, fh, fill=1, stroke=0)
    cv.setFillColor(t["A"]); cv.rect(0, 0, 5 * mm, fh, fill=1, stroke=0)
    cv.setFillColor(colors.HexColor("#ffffffaa")); cv.setFont("HN", 7.5)
    cv.drawString(14 * mm, 4 * mm, f"PlannerAtlas  ·  {label}  ·  planneratlas.etsy.com")
    cv.setFillColor(colors.white); cv.setFont("HN-B", 7.5)
    cv.drawRightString(W - 12 * mm, 4 * mm, "planneratlas.etsy.com")

def cover(cv, t, L, tname):
    bg(cv, t)
    split = H * 0.40
    cv.setFillColor(t["P"]); cv.rect(0, split, W, H - split, fill=1, stroke=0)

    # Decorative circles
    cx_c = W * 0.88; cy_c = split + (H - split) * 0.68
    cv.setFillColor(t["Pd"]); cv.circle(cx_c, cy_c, 60 * mm, fill=1, stroke=0)

    # PA monogram — elegant serif on accent circle
    cv.setFillColor(t["A"]); cv.circle(cx_c, cy_c, 32 * mm, fill=1, stroke=0)
    cv.setStrokeColor(colors.HexColor("#ffffff40")); cv.setLineWidth(2)
    cv.circle(cx_c, cy_c, 28.5 * mm, fill=0, stroke=1)
    cv.setStrokeColor(colors.HexColor("#ffffff20")); cv.setLineWidth(0.7)
    cv.circle(cx_c, cy_c, 26 * mm, fill=0, stroke=1)
    cv.setFillColor(colors.white); cv.setFont("PF-B", 40)
    p_w = cv.stringWidth("P", "PF-B", 40)
    a_w = cv.stringWidth("A", "PF-B", 40)
    gap = -3 * mm
    total_w = p_w + gap + a_w
    start_x = cx_c - total_w / 2
    baseline = cy_c - 7 * mm
    cv.drawString(start_x, baseline, "P")
    cv.drawString(start_x + p_w + gap, baseline, "A")
    mid_x = start_x + p_w + gap / 2
    cv.setStrokeColor(colors.HexColor("#ffffff60")); cv.setLineWidth(0.6)
    cv.line(mid_x, baseline - 2 * mm, mid_x, baseline + 14 * mm)
    rule_y_top = baseline + 17 * mm
    rule_y_bot = baseline - 6 * mm
    cv.setStrokeColor(colors.HexColor("#ffffffaa")); cv.setLineWidth(0.8)
    cv.line(cx_c - 18 * mm, rule_y_top, cx_c + 18 * mm, rule_y_top)
    cv.line(cx_c - 18 * mm, rule_y_bot, cx_c + 18 * mm, rule_y_bot)
    diam_x, diam_y = cx_c, rule_y_top + 3.5 * mm
    cv.setFillColor(colors.HexColor("#ffffffcc"))
    p = cv.beginPath()
    s = 2.2 * mm
    p.moveTo(diam_x, diam_y + s); p.lineTo(diam_x + s, diam_y)
    p.lineTo(diam_x, diam_y - s); p.lineTo(diam_x - s, diam_y)
    p.close(); cv.drawPath(p, fill=1, stroke=0)

    cv.setFillColor(t["A"]); cv.circle(-8 * mm, H - 10 * mm, 32 * mm, fill=1, stroke=0)
    cv.setFillColor(t["A"]); cv.rect(0, split, 5 * mm, H - split, fill=1, stroke=0)

    # Title — no subtitle
    cv.setFillColor(colors.white)
    cv.setFont("HN-B", 42); cv.drawString(18 * mm, split + 92 * mm, L["title"])
    cv.setStrokeColor(t["A"]); cv.setLineWidth(2.5)
    cv.line(18 * mm, split + 83 * mm, 78 * mm, split + 83 * mm)

    # Contents
    cv.setFillColor(t["TX"]); cv.setFont("HN-B", 12)
    cv.drawString(18 * mm, split - 14 * mm, L["contents_label"] + ":")
    cv.setFont("HN", 10.5); cv.setFillColor(t["MU"])
    for i, item in enumerate(L["cover_items"]):
        cv.drawString(20 * mm, split - 26 * mm - i * 9 * mm, f"  ●  {item}")

    # Brand footer — no tip box
    cv.setFillColor(t["MU"]); cv.setFont("HN-L", 8)
    cv.drawCentredString(W / 2, MB + 5 * mm,
                         f"PlannerAtlas  ·  {tname.capitalize()} Edition  ·  planneratlas.etsy.com")
    cv.showPage()

def jahres(cv, t, L):
    bg(cv, t); hdr(cv, t, L["year_header"], "")
    gx = 14 * mm; gy = H - 38 * mm
    cw = (W - 28 * mm) / 3; rh = (gy - MB - 6 * mm) / 4
    dl = [d[0] for d in L["days"]]
    for idx, month in enumerate(L["months"]):
        col = idx % 3; row = idx // 3
        mx = gx + col * cw; my = gy - row * rh
        cv.setFillColor(colors.white)
        cv.roundRect(mx + 1.5 * mm, my - rh + 2 * mm, cw - 3 * mm, rh - 3 * mm, 6, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.6)
        cv.roundRect(mx + 1.5 * mm, my - rh + 2 * mm, cw - 3 * mm, rh - 3 * mm, 6, fill=0, stroke=1)
        cv.setFillColor(t["P"])
        cv.roundRect(mx + 1.5 * mm, my - 9 * mm, cw - 3 * mm, 8 * mm, 6, fill=1, stroke=0)
        cv.rect(mx + 1.5 * mm, my - 9 * mm, cw - 3 * mm, 4 * mm, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 9)
        cv.drawString(mx + 4 * mm, my - 6.5 * mm, month)
        cw2 = (cw - 5 * mm) / 7
        for d, dl2 in enumerate(dl):
            dx = mx + 2.5 * mm + d * cw2
            cv.setFillColor(t["WA"] if d >= 5 else t["MU"]); cv.setFont("HN-M", 6.5)
            cv.drawCentredString(dx + cw2 / 2, my - 13.5 * mm, dl2)
        for r in range(6):
            for d in range(7):
                dx = mx + 2.5 * mm + d * cw2; dy = my - 18 * mm - r * 5.2 * mm
                cv.setFillColor(t["WE"] if d >= 5 else t["Pl"])
                cv.roundRect(dx + 0.3, dy, cw2 - 0.6, 4.5 * mm, 1.5, fill=1, stroke=0)
                cv.setFillColor(t["R"]); cv.circle(dx + cw2 / 2, dy + 2.2 * mm, 0.7 * mm, fill=1, stroke=0)
    ftr(cv, t, L["footer_year"]); cv.showPage()

def monats(cv, t, L):
    bg(cv, t); hdr(cv, t, L["month_header"], "")
    lx = 14 * mm; rx = W - 14 * mm; gw = rx - lx; yt = H - 39 * mm
    dlw = 13 * mm; wcw = (gw - dlw) / 4; rh = 10.5 * mm
    dl = [d[0] for d in L["days"]]
    for wk in range(4):
        wx = lx + dlw + wk * wcw
        cv.setFillColor(t["P"]); cv.roundRect(wx + 1 * mm, yt - 7.5 * mm, wcw - 2 * mm, 6.5 * mm, 3, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8)
        wk_label = f"Woche {wk+1}" if L == LANGS["DE"] else f"Semana {wk+1}" if L in (LANGS["ES"], LANGS["PT"]) else f"Week {wk+1}"
        cv.drawCentredString(wx + wcw / 2, yt - 5 * mm, wk_label)
        for d, day in enumerate(dl):
            dy2 = yt - 11 * mm - d * rh; iw = d >= 5
            if wk == 0:
                cv.setFillColor(t["Pl"]); cv.rect(lx, dy2 - rh + 0.5 * mm, dlw, rh - 1 * mm, fill=1, stroke=0)
                cv.setFillColor(t["P"]); cv.setFont("HN-B", 8.5)
                cv.drawCentredString(lx + dlw / 2, dy2 - rh / 2 - 1.5 * mm, day)
            cv.setFillColor(t["WE"] if iw else colors.white)
            cv.rect(wx + 0.5 * mm, dy2 - rh + 0.5 * mm, wcw - 1 * mm, rh - 1 * mm, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
            cv.rect(wx + 0.5 * mm, dy2 - rh + 0.5 * mm, wcw - 1 * mm, rh - 1 * mm, fill=0, stroke=1)
            cv.setFillColor(t["Pl"]); cv.roundRect(wx + 1.5 * mm, dy2 - 3.5 * mm, 5.5 * mm, 4 * mm, 2, fill=1, stroke=0)
            cv.setFillColor(t["MU"]); cv.setFont("HN", 7.5)
            cv.drawCentredString(wx + 4.25 * mm, dy2 - 1.5 * mm, "__")
    cv.setStrokeColor(t["P"]); cv.setLineWidth(0.8)
    cv.rect(lx, yt - 11 * mm - 7 * rh, gw, 7 * rh + 8 * mm, fill=0, stroke=1)

    # Notes section — ensure clearance above footer
    ny = yt - 11 * mm - 7 * rh - 10 * mm  # extra gap from grid
    min_y = MB + 20 * mm                    # never go below this
    if ny < min_y:
        ny = min_y
    cv.setFillColor(t["P"]); cv.setFont("HN-B", 9.5)
    cv.drawString(lx, ny, L["notes_label"])
    cv.setStrokeColor(t["A"]); cv.setLineWidth(2)
    cv.line(lx, ny - 2.5 * mm, lx + 58 * mm, ny - 2.5 * mm)
    ly = ny - 10 * mm
    while ly > MB + 10 * mm:   # stop well above footer
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4); cv.line(lx, ly, rx, ly); ly -= 7.5 * mm
    ftr(cv, t, L["footer_month"]); cv.showPage()

def woche(cv, t, L):
    bg(cv, t); hdr(cv, t, L["week_header"], L["week_sub"])
    yt = H - 39 * mm; yb = MB + 12 * mm; ch = yt - yb
    lx = 14 * mm; rx = W - 14 * mm; tw = rx - lx
    dw = tw * 0.67; gap = 4 * mm; sw = tw - dw - gap; sx = lx + dw + gap
    dh = ch / 7; lpd = 5; lg = (dh - 10.5 * mm) / lpd

    for i, (ab, full) in enumerate(L["days"]):
        yt2 = yt - i * dh; yb2 = yt2 - dh; iw = i >= 5
        tc = t["WA"] if iw else t["P"]
        cv.setFillColor(t["WE"] if iw else t["Pl"])
        cv.rect(lx, yb2, dw, dh, fill=1, stroke=0)
        cv.setFillColor(tc); cv.rect(lx, yb2, 11 * mm, dh, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 10.5)
        cv.drawCentredString(lx + 5.5 * mm, yb2 + dh / 2 - 2 * mm, ab)
        cv.setFillColor(t["TX"]); cv.setFont("HN-B", 9)
        cv.drawString(lx + 14 * mm, yt2 - 6 * mm, full)
        cv.setFillColor(t["MU"]); cv.setFont("HN", 8)
        cv.drawString(lx + 44 * mm, yt2 - 6 * mm, "__.__")
        cv.setFillColor(tc)
        cv.roundRect(lx + dw - 23 * mm, yt2 - 7.5 * mm, 21 * mm, 5.5 * mm, 2.5, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN", 6.5)
        cv.drawCentredString(lx + dw - 12.5 * mm, yt2 - 5 * mm, L["priority_label"])
        for l in range(lpd):
            ly2 = yt2 - 11 * mm - l * lg
            if ly2 > yb2 + 2 * mm:
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
                cv.line(lx + 14 * mm, ly2, lx + dw - 2 * mm, ly2)
        if i < 6:
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.7)
            cv.line(lx, yb2, lx + dw, yb2)

    cv.setStrokeColor(t["P"]); cv.setLineWidth(1)
    cv.rect(lx, yb, dw, ch, fill=0, stroke=1)

    secs = L["sidebar"]
    sy = yt; lh = 8 * mm; lhs = 6.2 * mm; sg = 3.5 * mm
    for label, n in secs:
        sh = lh + n * lhs; secy = sy - sh
        cv.setFillColor(colors.white); cv.roundRect(sx, secy, sw, sh, 6, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.5)
        cv.roundRect(sx, secy, sw, sh, 6, fill=0, stroke=1)
        cv.setFillColor(t["P"]); cv.roundRect(sx, secy + sh - lh, sw, lh, 6, fill=1, stroke=0)
        cv.rect(sx, secy + sh - lh, sw, lh / 2, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 9)
        cv.drawString(sx + 3.5 * mm, secy + sh - lh + 2.5 * mm, label)
        for l in range(n):
            ly2 = secy + sh - lh - (l + 1) * lhs + 1.5 * mm
            if ly2 > secy + 1.5 * mm:
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
                cv.line(sx + 2.5 * mm, ly2, sx + sw - 2.5 * mm, ly2)
        sy = secy - sg

    ftr(cv, t, L["footer_week"]); cv.showPage()

def habit(cv, t, L):
    bg(cv, t); hdr(cv, t, L["habit_header"], L["habit_sub"])
    lx = 14 * mm; rx = W - 14 * mm
    yt = H - 39 * mm; yb = MB + 10 * mm
    nh = 10; nd = 31
    hlw = 50 * mm
    cw = (rx - lx - hlw) / nd
    avail_h = yt - yb - 22 * mm
    rh = avail_h / (nh + 1)

    for d in range(nd):
        dx = lx + hlw + d * cw; iw = d % 7 >= 5
        cv.setFillColor(t["WA"] if iw else t["P"])
        cv.roundRect(dx + 0.3 * mm, yt - rh + 0.5 * mm, cw - 0.6 * mm, rh - 1 * mm, 2, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 6)
        cv.drawCentredString(dx + cw / 2, yt - rh / 2 - 2 * mm, str(d + 1))

    for h, hab in enumerate(L["habit_rows"]):
        hy = yt - (h + 1) * rh; alt = t["Pl"] if h % 2 == 0 else colors.white
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

    qy = yt - rh * (nh + 1) - 4 * mm
    box_h = qy - yb
    if box_h > 12 * mm:
        cv.setFillColor(t["Pl"])
        cv.roundRect(lx, yb, rx - lx, box_h, 6, fill=1, stroke=0)
        cv.setStrokeColor(t["A"]); cv.setLineWidth(4)
        cv.line(lx, yb, lx, qy)
        cv.setFillColor(t["P"]); cv.setFont("HN-B", 8.5)
        cv.drawString(lx + 5 * mm, qy - 8 * mm, L["habit_quote"])
        if box_h > 20 * mm:
            cv.setFillColor(t["MU"]); cv.setFont("HN", 8)
            cv.drawString(lx + 5 * mm, qy - 16 * mm,
                          L["habit_goal"] + ":  _________________________________________")

    ftr(cv, t, L["footer_habit"]); cv.showPage()

def notizen(cv, t, L):
    bg(cv, t); hdr(cv, t, L["notes_page"], "")
    lx = 14 * mm; rx = W - 14 * mm; y = H - 43 * mm
    while y > MB + 10 * mm:
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4); cv.line(lx, y, rx, y); y -= 9 * mm
    ftr(cv, t, L["footer_notes"]); cv.showPage()

# ── Generate ──────────────────────────────────────────────────────────────────

for lang_code, L in LANGS.items():
    out_dir = f"{BASE}/{L['outdir']}"
    os.makedirs(out_dir, exist_ok=True)
    for tname, tp in THEMES.items():
        out_path = f"{out_dir}/{L['filename']}_{tname}.pdf"
        cv = canvas.Canvas(out_path, pagesize=A4)
        cover(cv, tp, L, tname)
        jahres(cv, tp, L)
        monats(cv, tp, L)
        woche(cv, tp, L)
        habit(cv, tp, L)
        notizen(cv, tp, L)
        cv.save()
        print(f"OK  {lang_code}/{tname} → {out_path}")

print("\nTodos os weekly planners gerados.")
