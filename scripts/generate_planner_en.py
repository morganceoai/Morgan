"""
PlannerAtlas — Weekly Planner EN (Premium)
Gera PDF A4 completo com 12 páginas.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import calendar
from datetime import date

# ── Paleta ──────────────────────────────────────────────────────────────────
GREEN     = HexColor("#1B4332")
GOLD      = HexColor("#C9A84C")
CREAM     = HexColor("#FAFAF5")
LGRID     = HexColor("#D4E8DC")
MINT      = HexColor("#F0FAF4")
WCREAM    = HexColor("#FFF9EE")
ALTROW    = HexColor("#EEF6F1")
WHITE     = HexColor("#FFFFFF")
DARKTEXT  = HexColor("#1B4332")
GRAYTEXT  = HexColor("#6B7280")

W, H = A4  # 595.28 x 841.89 pts
M = 18 * mm  # margem

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]


def draw_page_footer(c, page_label=""):
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAYTEXT)
    c.drawString(M, 10 * mm, "planneratlas.etsy.com")
    if page_label:
        c.drawRightString(W - M, 10 * mm, page_label)


def draw_section_header(c, title, y):
    """Barra verde topo com título em branco."""
    bar_h = 11 * mm
    c.setFillColor(GREEN)
    c.rect(0, y - bar_h, W, bar_h, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, y - bar_h + 3.5 * mm, title)
    return y - bar_h


# ── Página 1: Capa ───────────────────────────────────────────────────────────
def page_cover(c):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Sidebar esquerda verde
    c.setFillColor(GREEN)
    c.rect(0, 0, 10 * mm, H, fill=1, stroke=0)

    # Linha dourada
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.line(M + 2 * mm, H - 30 * mm, W - M, H - 30 * mm)

    # Logo PA
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M + 2 * mm, H - 22 * mm, "PA")

    # Título
    c.setFont("Helvetica-Bold", 42)
    c.drawString(M + 2 * mm, H * 0.55, "WEEKLY")
    c.drawString(M + 2 * mm, H * 0.55 - 48, "PLANNER")

    # Subtítulo
    c.setFillColor(GOLD)
    c.setFont("Helvetica", 8)
    c.drawString(M + 2 * mm, H * 0.55 - 64, "PREMIUM COLLECTION")

    c.setFillColor(GRAYTEXT)
    c.setFont("Helvetica", 7.5)
    c.drawString(M + 2 * mm, H * 0.55 - 76, "UNDATED  ·  A4")

    # Índice
    items = [
        "Yearly Overview",
        "Monthly Overview",
        "Weekly Planner × 4",
        "Habit Tracker",
        "Mood Tracker",
        "Goals & Intentions",
        "Notes × 2",
    ]
    y = H * 0.35
    c.setFillColor(GREEN)
    c.setFont("Helvetica", 8.5)
    for item in items:
        c.drawString(M + 2 * mm, y, item)
        y -= 14

    draw_page_footer(c)
    c.showPage()


# ── Página 2: Yearly Overview ────────────────────────────────────────────────
def page_yearly(c):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    y = draw_section_header(c, "YEARLY OVERVIEW", H - 14 * mm)

    # 4 colunas × 3 linhas de mini-calendários
    cell_w = (W - 2 * M) / 4
    grid_top = y - 16 * mm  # espaço após header
    cell_h = (grid_top - 24 * mm) / 3
    row_h_inner = cell_h - 16 * mm

    for i, month in enumerate(MONTHS):
        col = i % 4
        row = i // 4
        x0 = M + col * cell_w
        y0 = grid_top - (row + 1) * cell_h + 4 * mm

        # Estrutura interna: nome (6mm) + dias (5mm) + grelha (row_h_inner)
        name_h = 6 * mm
        days_h = 5 * mm
        total_h = name_h + days_h + row_h_inner
        box_x = x0 + 1 * mm
        box_w = cell_w - 4 * mm

        # Fundo caixa
        c.setFillColor(WHITE)
        c.rect(box_x, y0, box_w, total_h, fill=1, stroke=0)

        # Nome do mês — fundo verde, letra branca
        c.setFillColor(GREEN)
        c.rect(box_x, y0 + days_h + row_h_inner, box_w, name_h, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(box_x + 2 * mm, y0 + days_h + row_h_inner + 1.5 * mm, month.upper())

        # Cabeçalho dias — fundo verde
        day_labels = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        day_col_w = box_w / 7
        c.setFillColor(GREEN)
        c.rect(box_x, y0 + row_h_inner, box_w, days_h, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 5.5)
        for d, lbl in enumerate(day_labels):
            c.drawCentredString(box_x + d * day_col_w + day_col_w / 2, y0 + row_h_inner + 1.5 * mm, lbl)

        # Grelha semanas (6 linhas horizontais)
        week_row_h = row_h_inner / 6
        for week in range(6):
            wy = y0 + week * week_row_h
            c.setStrokeColor(LGRID)
            c.setLineWidth(0.3)
            c.line(box_x, wy, box_x + box_w, wy)

        # Linhas verticais colunas
        for d in range(1, 7):
            c.line(box_x + d * day_col_w, y0, box_x + d * day_col_w, y0 + row_h_inner)

        # Borda do mês
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.5)
        c.rect(box_x, y0, box_w, total_h, fill=0, stroke=1)

    draw_page_footer(c, "Yearly Overview")
    c.showPage()


# ── Página 3: Monthly Overview ───────────────────────────────────────────────
def page_monthly(c):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    y = draw_section_header(c, "MONTHLY OVERVIEW", H - 14 * mm)

    grid_top = y - 22 * mm

    # Linha "Month / Year:" entre header e grelha
    label_y = grid_top + 12 * mm
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, label_y, "Month / Year:")
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.5)
    c.line(M + 32 * mm, label_y + 1, W - M, label_y + 1)
    grid_h = grid_top - 72 * mm
    col_w = (W - 2 * M) / 7
    row_h = grid_h / 6

    # Cabeçalho dias da semana
    day_colors = [GREEN] * 5 + [GOLD] * 2
    for d, (day, col) in enumerate(zip(DAYS, day_colors)):
        x = M + d * col_w
        c.setFillColor(col)
        c.rect(x, grid_top, col_w, 9 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + col_w / 2, grid_top + 2.8 * mm, day)

    # Grelha 6 × 7
    for row in range(6):
        for col in range(7):
            x = M + col * col_w
            yy = grid_top - (row + 1) * row_h
            fill = WCREAM if col >= 5 else MINT
            c.setFillColor(fill)
            c.rect(x, yy, col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(LGRID)
            c.setLineWidth(0.4)
            c.rect(x, yy, col_w, row_h, fill=0, stroke=1)

    # Notas do mês
    notes_y = grid_top - 6 * row_h - 8 * mm
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, notes_y, "Notes & Goals of the Month")
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.5)
    footer_limit = 30 * mm
    for i in range(4):
        ly = notes_y - 10 * mm - i * 10 * mm
        if ly > footer_limit:
            c.line(M, ly, W - M, ly)

    draw_page_footer(c, "Monthly Overview")
    c.showPage()


# ── Páginas 4-7: Weekly Planner ──────────────────────────────────────────────
def page_weekly(c, week_num):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    title = f"WEEKLY PLANNER — WEEK {week_num}"
    y = draw_section_header(c, title, H - 14 * mm)

    # Linha "Week of: ___"
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(M, y - 9 * mm, "Week of:")
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.5)
    c.line(M + 24 * mm, y - 9 * mm + 1, M + 70 * mm, y - 9 * mm + 1)

    # Intention da semana
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(M + 80 * mm, y - 9 * mm, "Weekly Intention:")
    c.line(M + 116 * mm, y - 9 * mm + 1, W - M, y - 9 * mm + 1)

    grid_top = y - 20 * mm
    grid_h = grid_top - 55 * mm
    col_w = (W - 2 * M) / 7
    # Sidebar esquerda + 7 dias
    sidebar_w = 18 * mm
    day_col_w = (W - 2 * M - sidebar_w) / 7

    time_slots = [
        "6:00", "7:00", "8:00", "9:00", "10:00", "11:00",
        "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00", "21:00", "22:00",
    ]
    row_h = grid_h / len(time_slots)

    # Cabeçalhos dias
    day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    day_bg = [GREEN] * 5 + [GOLD] * 2
    for d in range(7):
        x = M + sidebar_w + d * day_col_w
        c.setFillColor(day_bg[d])
        c.rect(x, grid_top, day_col_w, 9 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + day_col_w / 2, grid_top + 2.8 * mm, day_names[d])

    # Sidebar hora + grelha
    for i, slot in enumerate(time_slots):
        yy = grid_top - (i + 1) * row_h
        # hora
        c.setFillColor(ALTROW if i % 2 == 0 else CREAM)
        c.rect(M, yy, sidebar_w, row_h, fill=1, stroke=0)
        c.setFillColor(GRAYTEXT)
        c.setFont("Helvetica", 6.5)
        c.drawString(M + 1.5 * mm, yy + row_h / 2 - 2, slot)
        # células
        for d in range(7):
            x = M + sidebar_w + d * day_col_w
            fill = WCREAM if d >= 5 else (ALTROW if i % 2 == 0 else MINT)
            c.setFillColor(fill)
            c.rect(x, yy, day_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(LGRID)
            c.setLineWidth(0.3)
            c.rect(x, yy, day_col_w, row_h, fill=0, stroke=1)

    # Borda sidebar
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.4)
    c.rect(M, grid_top - len(time_slots) * row_h, sidebar_w, len(time_slots) * row_h, fill=0, stroke=1)

    # Secção inferior: Priorities + Notes
    bottom_y = grid_top - len(time_slots) * row_h - 5 * mm
    half = (W - 2 * M) / 2
    footer_limit = 20 * mm

    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M, bottom_y, "TOP PRIORITIES")
    c.drawString(M + half + 4 * mm, bottom_y, "NOTES")

    c.setStrokeColor(LGRID)
    c.setLineWidth(0.4)
    for i in range(3):
        ly = bottom_y - 9 * mm - i * 9 * mm
        if ly > 30 * mm:
            c.line(M, ly, M + half - 4 * mm, ly)
            c.line(M + half + 4 * mm, ly, W - M, ly)

    draw_page_footer(c, f"Week {week_num}")
    c.showPage()


# ── Página 8: Habit Tracker ──────────────────────────────────────────────────
def page_habit_tracker(c):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    y = draw_section_header(c, "HABIT TRACKER", H - 14 * mm)

    habits = [
        "Exercise", "Meditation", "Reading", "Hydration (2L)",
        "Sleep 8h", "Journaling", "Gratitude", "No Sugar",
        "Walk 10k steps", "Vitamins",
    ]

    label_w = 45 * mm
    weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
    week_col_w = (W - 2 * M - label_w) / 4
    row_h = 11 * mm
    header_y = y - 10 * mm

    # Cabeçalho semanas
    c.setFillColor(GREEN)
    c.rect(M, header_y - 8 * mm, label_w, 8 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M + 2 * mm, header_y - 5.5 * mm, "HABIT")

    for i, wk in enumerate(weeks):
        x = M + label_w + i * week_col_w
        c.setFillColor(GREEN)
        c.rect(x, header_y - 8 * mm, week_col_w, 8 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(x + week_col_w / 2, header_y - 5.5 * mm, wk)

    # Linhas de hábitos
    for idx, habit in enumerate(habits):
        ry = header_y - 8 * mm - (idx + 1) * row_h
        bg = ALTROW if idx % 2 == 0 else CREAM

        # Label
        c.setFillColor(bg)
        c.rect(M, ry, label_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.4)
        c.rect(M, ry, label_w, row_h, fill=0, stroke=1)
        c.setFillColor(DARKTEXT)
        c.setFont("Helvetica", 8)
        c.drawString(M + 2 * mm, ry + row_h / 2 - 2, habit)

        # Células semanas (7 dias cada)
        for wi in range(4):
            wx = M + label_w + wi * week_col_w
            day_w = week_col_w / 7
            for di in range(7):
                dx = wx + di * day_w
                fill = WCREAM if di >= 5 else bg
                c.setFillColor(fill)
                c.rect(dx, ry, day_w, row_h, fill=1, stroke=0)
                c.setStrokeColor(LGRID)
                c.setLineWidth(0.3)
                c.rect(dx, ry, day_w, row_h, fill=0, stroke=1)

    # Linhas em branco para hábitos personalizados
    blank_start = header_y - 8 * mm - len(habits) * row_h
    blank_count = 0
    while blank_start - (blank_count + 1) * row_h > 22 * mm:
        blank_count += 1
    for idx in range(blank_count):
        ry = blank_start - (idx + 1) * row_h
        bg = ALTROW if (len(habits) + idx) % 2 == 0 else CREAM
        c.setFillColor(bg)
        c.rect(M, ry, label_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.4)
        c.rect(M, ry, label_w, row_h, fill=0, stroke=1)
        # linha pontilhada para escrever o hábito
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.3)
        c.line(M + 2 * mm, ry + row_h / 2, M + label_w - 2 * mm, ry + row_h / 2)
        for wi in range(4):
            wx = M + label_w + wi * week_col_w
            day_w = week_col_w / 7
            for di in range(7):
                dx = wx + di * day_w
                fill = WCREAM if di >= 5 else bg
                c.setFillColor(fill)
                c.rect(dx, ry, day_w, row_h, fill=1, stroke=0)
                c.setStrokeColor(LGRID)
                c.setLineWidth(0.3)
                c.rect(dx, ry, day_w, row_h, fill=0, stroke=1)

    # Legenda dias
    legend_y = header_y - 8 * mm - (len(habits) + blank_count + 0.3) * row_h
    c.setFillColor(GRAYTEXT)
    c.setFont("Helvetica", 6.5)
    for wi in range(4):
        wx = M + label_w + wi * week_col_w
        day_w = week_col_w / 7
        day_abbr = ["M", "T", "W", "T", "F", "S", "S"]
        for di, da in enumerate(day_abbr):
            c.drawCentredString(wx + di * day_w + day_w / 2, legend_y, da)

    draw_page_footer(c, "Habit Tracker")
    c.showPage()


# ── Página 9: Mood Tracker ───────────────────────────────────────────────────
def page_mood_tracker(c):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    y = draw_section_header(c, "MOOD TRACKER", H - 14 * mm)

    metrics = [
        "Morning Mood", "Evening Mood", "Energy Level",
        "Anxiety Level", "Motivation", "Social Wellbeing",
        "Physical Health", "Sleep Quality", "Productivity",
    ]

    label_w = 45 * mm
    weeks = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
    week_col_w = (W - 2 * M - label_w) / 5
    row_h = 10 * mm
    header_y = y - 10 * mm

    # Subtítulo
    c.setFillColor(GRAYTEXT)
    c.setFont("Helvetica", 7.5)
    c.drawString(M, header_y + 2 * mm, "Rate each metric 1–10 daily. Use the notes section for reflections.")

    # Cabeçalho
    c.setFillColor(GREEN)
    c.rect(M, header_y - 8 * mm, label_w, 8 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M + 2 * mm, header_y - 5.5 * mm, "METRIC")

    for i, wk in enumerate(weeks):
        x = M + label_w + i * week_col_w
        c.setFillColor(GREEN)
        c.rect(x, header_y - 8 * mm, week_col_w, 8 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(x + week_col_w / 2, header_y - 5.5 * mm, wk)

    # Linhas métricas
    for idx, metric in enumerate(metrics):
        ry = header_y - 8 * mm - (idx + 1) * row_h
        bg = ALTROW if idx % 2 == 0 else CREAM

        c.setFillColor(bg)
        c.rect(M, ry, label_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.4)
        c.rect(M, ry, label_w, row_h, fill=0, stroke=1)
        c.setFillColor(DARKTEXT)
        c.setFont("Helvetica", 8)
        c.drawString(M + 2 * mm, ry + row_h / 2 - 2, metric)

        for wi in range(5):
            wx = M + label_w + wi * week_col_w
            c.setFillColor(bg)
            c.rect(wx, ry, week_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(LGRID)
            c.setLineWidth(0.4)
            c.rect(wx, ry, week_col_w, row_h, fill=0, stroke=1)

    # Linhas em branco para métricas personalizadas
    blank_start = header_y - 8 * mm - len(metrics) * row_h
    blank_count = 0
    while blank_start - (blank_count + 1) * row_h > 60 * mm:
        blank_count += 1
    for idx in range(blank_count):
        ry = blank_start - (idx + 1) * row_h
        bg = ALTROW if (len(metrics) + idx) % 2 == 0 else CREAM
        c.setFillColor(bg)
        c.rect(M, ry, label_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.4)
        c.rect(M, ry, label_w, row_h, fill=0, stroke=1)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.3)
        c.line(M + 2 * mm, ry + row_h / 2, M + label_w - 2 * mm, ry + row_h / 2)
        for wi in range(5):
            wx = M + label_w + wi * week_col_w
            c.setFillColor(bg)
            c.rect(wx, ry, week_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(LGRID)
            c.setLineWidth(0.4)
            c.rect(wx, ry, week_col_w, row_h, fill=0, stroke=1)

    # Notes & Reflections
    notes_y = header_y - 8 * mm - (len(metrics) + blank_count + 0.5) * row_h
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, notes_y, "Notes & Reflections")
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.5)
    for i in range(5):
        c.line(M, notes_y - 9 * mm - i * 9 * mm, W - M, notes_y - 9 * mm - i * 9 * mm)

    draw_page_footer(c, "Mood Tracker")
    c.showPage()


# ── Página 10: Goals & Intentions ───────────────────────────────────────────
def page_goals(c):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    y = draw_section_header(c, "GOALS & INTENTIONS", H - 14 * mm)

    sections = [
        ("MONTHLY GOAL", "What is your main goal this month?"),
        ("WHY IT MATTERS", "Your deeper reason and motivation"),
        ("ACTION STEPS", "Break it down into weekly actions"),
        ("POTENTIAL OBSTACLES", "What might get in the way?"),
        ("HOW I'LL OVERCOME THEM", "Your strategy"),
        ("REWARD", "How will you celebrate success?"),
    ]

    box_h = (y - 30 * mm) / len(sections)

    for idx, (title, prompt) in enumerate(sections):
        by = y - (idx + 1) * box_h
        bg = ALTROW if idx % 2 == 0 else CREAM
        c.setFillColor(bg)
        c.rect(M, by, W - 2 * M, box_h, fill=1, stroke=0)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.4)
        c.rect(M, by, W - 2 * M, box_h, fill=0, stroke=1)

        c.setFillColor(GREEN)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(M + 3 * mm, by + box_h - 6 * mm, title)

        c.setFillColor(GRAYTEXT)
        c.setFont("Helvetica", 7)
        c.drawString(M + 3 * mm, by + box_h - 11 * mm, prompt)

        # Linhas de escrita
        lines = max(1, int((box_h - 14 * mm) / 7))
        for li in range(lines):
            ly = by + box_h - 15 * mm - li * 7 * mm
            if ly > by + 2 * mm:
                c.setStrokeColor(LGRID)
                c.setLineWidth(0.3)
                c.line(M + 3 * mm, ly, W - M - 3 * mm, ly)

    draw_page_footer(c, "Goals & Intentions")
    c.showPage()


# ── Páginas 11-12: Notes ────────────────────────────────────────────────────
def page_notes(c, page_num):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    y = draw_section_header(c, "NOTES", H - 14 * mm)

    # Área de título
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, y - 10 * mm, "Title / Topic:")
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.5)
    c.line(M + 32 * mm, y - 10 * mm + 1, W - M, y - 10 * mm + 1)

    # Linhas de notas
    line_start = y - 18 * mm
    line_spacing = 10 * mm
    num_lines = int((line_start - 22 * mm) / line_spacing)

    for i in range(num_lines):
        ly = line_start - i * line_spacing
        bg = ALTROW if i % 2 == 0 else CREAM
        c.setFillColor(bg)
        c.rect(M, ly - line_spacing + 1, W - 2 * M, line_spacing - 1, fill=1, stroke=0)
        c.setStrokeColor(LGRID)
        c.setLineWidth(0.4)
        c.line(M, ly, W - M, ly)

    # Última linha
    c.setStrokeColor(LGRID)
    c.setLineWidth(0.4)
    c.line(M, line_start - num_lines * line_spacing, W - M, line_start - num_lines * line_spacing)

    draw_page_footer(c, f"Notes {page_num}")
    c.showPage()


# ── Main ────────────────────────────────────────────────────────────────────
def generate():
    output = "scripts/weekly_planner_EN.pdf"
    c = canvas.Canvas(output, pagesize=A4)
    c.setTitle("Weekly Planner — Premium Collection")
    c.setAuthor("PlannerAtlas")

    page_cover(c)
    page_yearly(c)
    page_monthly(c)
    for w in range(1, 5):
        page_weekly(c, w)
    page_habit_tracker(c)
    page_mood_tracker(c)
    page_goals(c)
    page_notes(c, 1)
    page_notes(c, 2)

    c.save()
    print(f"✅ PDF gerado: {output}")


if __name__ == "__main__":
    generate()
