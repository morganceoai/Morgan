#!/usr/bin/env python3
"""
PlannerAtlas — Master mockup generator
Generates professional Etsy mockups for all products × languages × colors
"""

import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, random, os

BASE = "/Users/vascobotelhodacosta/Morgan/businesses/planners"
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
SIZE = 2400

THEMES = {
    "indigo":     {"P": (26,79,122),  "A": (0,153,204),  "Pl": (232,242,249)},
    "sage":       {"P": (46,125,90),  "A": (201,123,75), "Pl": (232,245,238)},
    "terracotta": {"P": (184,78,40),  "A": (232,162,46), "Pl": (252,238,230)},
}

PRODUCTS = {
    "weekly_planner": {
        "page_content": 3,   # weekly spread page
        "DE": {
            "label": "WOCHENPLANER",
            "title": "Planer",
            "bullets": ["Jahres & Monatsansicht", "52 Wochen · A4 · PDF", "Sofort-Download"],
            "badge": "🇩🇪 Deutsch",
            "filename": "wochenplaner_DE",
        },
        "ES": {
            "label": "PLANIF. SEMANAL",
            "title": "Planner",
            "bullets": ["Vista anual & mensual", "52 semanas · A4 · PDF", "Descarga instantánea"],
            "badge": "🇪🇸 Español",
            "filename": "planificador_ES",
        },
        "PT": {
            "label": "PLANEADOR SEMANAL",
            "title": "Planner",
            "bullets": ["Vista anual & mensal", "52 semanas · A4 · PDF", "Download imediato"],
            "badge": "🇵🇹 Português",
            "filename": "planeador_PT",
        },
        "EN": {
            "label": "WEEKLY PLANNER",
            "title": "Planner",
            "bullets": ["Yearly & monthly view", "52 weeks · A4 · PDF", "Instant download"],
            "badge": "🇬🇧 English",
            "filename": "weekly_planner_EN",
        },
    },
    "daily_planner": {
        "page_content": 1,
        "DE": {
            "label": "TAGESPLANER",
            "title": "Tagesplan",
            "bullets": ["Stundenplan 6–22 Uhr", "Top 3 Prioritäten", "Notizen & Reflexion"],
            "badge": "🇩🇪 Deutsch",
            "filename": "tagesplaner_DE",
        },
        "ES": {
            "label": "PLANIF. DIARIO",
            "title": "Día a Día",
            "bullets": ["Horario 6–22 h", "Top 3 Prioridades", "Notas & Reflexión"],
            "badge": "🇪🇸 Español",
            "filename": "planificador_diario_ES",
        },
        "PT": {
            "label": "PLANEADOR DIÁRIO",
            "title": "Dia a Dia",
            "bullets": ["Horário 6–22 h", "Top 3 Prioridades", "Notas & Reflexão"],
            "badge": "🇵🇹 Português",
            "filename": "planeador_diario_PT",
        },
        "EN": {
            "label": "DAILY PLANNER",
            "title": "Day by Day",
            "bullets": ["Hour schedule 6–10 pm", "Top 3 Priorities", "Notes & Reflection"],
            "badge": "🇬🇧 English",
            "filename": "daily_planner_EN",
        },
    },
    "budget_tracker": {
        "page_content": 1,
        "DE": {
            "label": "HAUSHALTSPLANER",
            "title": "Budget",
            "bullets": ["Einnahmen & Ausgaben", "Ausgaben-Log", "Sparziele"],
            "badge": "🇩🇪 Deutsch",
            "filename": "haushaltsplaner_DE",
        },
        "ES": {
            "label": "CONTROL DE GASTOS",
            "title": "Presupuesto",
            "bullets": ["Ingresos & Gastos", "Registro semanal", "Ahorro"],
            "badge": "🇪🇸 Español",
            "filename": "control_gastos_ES",
        },
        "PT": {
            "label": "CTRL. DESPESAS",
            "title": "Orçamento",
            "bullets": ["Rendimentos & Despesas", "Registo semanal", "Poupança"],
            "badge": "🇵🇹 Português",
            "filename": "despesas_PT",
        },
        "EN": {
            "label": "BUDGET TRACKER",
            "title": "Budget",
            "bullets": ["Income & Expenses", "Weekly expense log", "Savings goals"],
            "badge": "🇬🇧 English",
            "filename": "budget_tracker_EN",
        },
    },
    "habit_tracker": {
        "page_content": 1,
        "DE": {
            "label": "HABIT TRACKER",
            "title": "Gewohnheiten",
            "bullets": ["31 Tage Tracker", "10 Gewohnheiten", "Monatsziel & Reflexion"],
            "badge": "🇩🇪 Deutsch",
            "filename": "habit_tracker_DE",
        },
        "ES": {
            "label": "HABITS TRACKER",
            "title": "Hábitos",
            "bullets": ["31 días · 10 hábitos", "Personalizable", "Meta mensual"],
            "badge": "🇪🇸 Español",
            "filename": "habitos_ES",
        },
        "PT": {
            "label": "HABIT TRACKER",
            "title": "Hábitos",
            "bullets": ["31 dias · 10 hábitos", "Personalizável", "Objetivo mensal"],
            "badge": "🇵🇹 Português",
            "filename": "habitos_PT",
        },
        "EN": {
            "label": "HABIT TRACKER",
            "title": "Monthly Habits",
            "bullets": ["31-day tracker", "10 habits", "Monthly goal & reflection"],
            "badge": "🇬🇧 English",
            "filename": "habit_tracker_EN",
        },
    },
    "meal_planner": {
        "page_content": 1,
        "DE": {
            "label": "MAHLZEITENPLANER",
            "title": "Essensplan",
            "bullets": ["7 Tage Mahlzeiten", "Frühstück bis Snacks", "Einkaufsliste"],
            "badge": "🇩🇪 Deutsch",
            "filename": "mahlzeitenplaner_DE",
        },
        "ES": {
            "label": "PLAN DE COMIDAS",
            "title": "Comidas",
            "bullets": ["7 días de comidas", "Desayuno a snacks", "Lista de compra"],
            "badge": "🇪🇸 Español",
            "filename": "comidas_ES",
        },
        "PT": {
            "label": "PLAN. REFEIÇÕES",
            "title": "Refeições",
            "bullets": ["7 dias de refeições", "P.almoço a snacks", "Lista de compras"],
            "badge": "🇵🇹 Português",
            "filename": "refeicoes_PT",
        },
        "EN": {
            "label": "MEAL PLANNER",
            "title": "Weekly Meals",
            "bullets": ["7-day meal plan", "Breakfast to snacks", "Shopping list"],
            "badge": "🇬🇧 English",
            "filename": "meal_planner_EN",
        },
    },
    "monthly_planner": {
        "page_content": 1,
        "DE": {
            "label": "MONATSPLANER",
            "title": "Monatsplan",
            "bullets": ["Monatskalender", "Monatsziele", "Notizen & Termine"],
            "badge": "🇩🇪 Deutsch",
            "filename": "monatsplaner_DE",
        },
        "ES": {
            "label": "PLANIF. MENSUAL",
            "title": "Mes a Mes",
            "bullets": ["Calendario mensual", "Objetivos del mes", "Notas & Fechas"],
            "badge": "🇪🇸 Español",
            "filename": "planificador_mensual_ES",
        },
        "PT": {
            "label": "PLANEADOR MENSAL",
            "title": "Mês a Mês",
            "bullets": ["Calendário mensal", "Objetivos do mês", "Notas & Datas"],
            "badge": "🇵🇹 Português",
            "filename": "planeador_mensal_PT",
        },
        "EN": {
            "label": "MONTHLY PLANNER",
            "title": "Month by Month",
            "bullets": ["Monthly calendar", "Monthly goals", "Notes & key dates"],
            "badge": "🇬🇧 English",
            "filename": "monthly_planner_EN",
        },
    },
}

def get_page(doc, idx, scale=3.5):
    pg = doc[idx]
    mat = fitz.Matrix(scale, scale)
    pix = pg.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

BG_STATIONERY = f"{BASE}/_assets/backgrounds/bg_stationery.jpg"
BG_FOOD       = f"{BASE}/_assets/backgrounds/bg_food.jpg"
BG_MARBLE     = f"{BASE}/_assets/backgrounds/bg_marble2.jpg"
BG_WOOD       = f"{BASE}/_assets/backgrounds/wood.jpg"

# Background per product — themed to feel natural
PRODUCT_BG = {
    "weekly_planner":  BG_STATIONERY,
    "daily_planner":   BG_STATIONERY,
    "monthly_planner": BG_STATIONERY,
    "budget_tracker":  f"{BASE}/_assets/backgrounds/bg_budget.jpg",
    "habit_tracker":   BG_STATIONERY,
    "meal_planner":    BG_FOOD,
}

def load_background(path, tname):
    """Load real stock photo, crop to square, apply subtle warmth + vignette."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    # Use upper-third crop for marble (more texture, less flat center)
    # Use center crop for wood
    if "marble" in path:
        top = max(0, (h - side) // 4)
    else:
        top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((SIZE, SIZE), Image.LANCZOS)

    # Subtle warm overlay to unify with planner color
    warm = Image.new("RGB", (SIZE, SIZE), (255, 248, 240))
    img = Image.blend(img, warm, 0.08)

    # Vignette
    v = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    vd = ImageDraw.Draw(v)
    cx, cy = SIZE // 2, SIZE // 2
    for r in range(SIZE // 2, 0, -1):
        alpha = int(80 * (1 - (r / (SIZE / 2))) ** 2.2)
        vd.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(0, 0, 0, alpha))
    c = img.convert("RGBA")
    return Image.alpha_composite(c, v).convert("RGB")

def make_linen(size, base=(238, 232, 220)):
    random.seed(7)
    img = Image.new("RGB", (size, size), base)
    px = img.load()
    for y in range(size):
        for x in range(size):
            grain = math.sin(y * 0.8 + x * 0.05) * 4 + math.sin(x * 0.6 + y * 0.03) * 3
            noise = random.gauss(0, 6)
            r = max(0, min(255, int(base[0] + grain + noise)))
            g = max(0, min(255, int(base[1] + grain * 0.9 + noise * 0.9)))
            b = max(0, min(255, int(base[2] + grain * 0.8 + noise * 0.8)))
            px[x, y] = (r, g, b)
    return img.filter(ImageFilter.GaussianBlur(0.6))

def add_vignette(canvas):
    v = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    vd = ImageDraw.Draw(v)
    cx, cy = SIZE // 2, SIZE // 2
    for r in range(SIZE // 2, 0, -1):
        alpha = int(60 * (1 - (r / (SIZE / 2))) ** 2)
        vd.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(0, 0, 0, alpha))
    c = canvas.convert("RGBA")
    return Image.alpha_composite(c, v).convert("RGB")

def cast_shadow(canvas, page_img, pcx, pcy, angle_deg, shadow_alpha=140, blur=45, offset=(28, 32)):
    rot = page_img.rotate(angle_deg, expand=True, resample=Image.BICUBIC)
    x = pcx - rot.width // 2
    y = pcy - rot.height // 2
    ox, oy = offset
    shadow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_card  = Image.new("RGBA", rot.size, (20, 16, 10, shadow_alpha))
    shadow_layer.paste(shadow_card, (x + ox, y + oy))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur))
    c_rgba = canvas.convert("RGBA")
    c_rgba = Image.alpha_composite(c_rgba, shadow_layer)
    rot_rgba = rot.convert("RGBA")
    c_rgba.paste(rot_rgba, (x, y))
    return c_rgba.convert("RGB")

def fit(img, w):
    r = w / img.width
    return img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)

def load_fonts():
    try:
        return {
            "label": ImageFont.truetype(HN, 34, index=10),   # Medium
            "title": ImageFont.truetype(HN, 80, index=1),    # Bold
            "bullet": ImageFont.truetype(HN, 36, index=0),   # Regular
            "brand": ImageFont.truetype(HN, 28, index=7),    # Light
            "badge": ImageFont.truetype(HN, 30, index=10),   # Medium
        }
    except Exception:
        f = ImageFont.load_default()
        return {k: f for k in ["label", "title", "bullet", "brand", "badge"]}

def fit_text_font(text, max_width, font_path, index, start_size=80):
    """Return a font that fits text within max_width, scaling down if needed."""
    size = start_size
    while size >= 24:
        try:
            f = ImageFont.truetype(font_path, size, index=index)
        except Exception:
            return ImageFont.load_default()
        bb = f.getbbox(text)
        if (bb[2] - bb[0]) <= max_width:
            return f
        size -= 4
    return ImageFont.truetype(font_path, 24, index=index)

def make_mockup(pdf_path, out_path, theme_name, lang_cfg, product_dir=""):
    t = THEMES[theme_name]
    P = t["P"]; A = t["A"]; Pl = t["Pl"]
    WHITE = (255, 255, 255)
    NAVY = (15, 35, 65)
    MID = (70, 90, 110)

    bg_path = PRODUCT_BG.get(product_dir, BG_STATIONERY)
    print(f"  Photo bg…", end=" ", flush=True)
    if os.path.exists(bg_path):
        canvas = load_background(bg_path, theme_name)
    else:
        canvas = make_linen(SIZE)
        canvas = add_vignette(canvas)

    doc = fitz.open(pdf_path)
    cover_img = get_page(doc, 0)
    content_img = get_page(doc, min(1, len(doc) - 1))

    cover_s   = fit(cover_img, 870)
    content_s = fit(content_img, 930)

    canvas = cast_shadow(canvas, content_s, 1060, 1300, angle_deg=3.0,  shadow_alpha=120, offset=(24, 28))
    canvas = cast_shadow(canvas, cover_s,   1340, 1110, angle_deg=-4.0, shadow_alpha=145, offset=(30, 36))

    draw = ImageDraw.Draw(canvas)
    fonts = load_fonts()

    # Info card (top-left)
    cx1, cy1 = 80, 80
    cw, ch = 620, 440

    # Card shadow
    for i in range(20, 0, -1):
        alpha = int(18 * (1 - i / 20))
        sh = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle([(cx1 + i, cy1 + i), (cx1 + cw + i, cy1 + ch + i)],
                              radius=24, fill=(120, 110, 95, alpha))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), sh).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Card body
    draw.rounded_rectangle([(cx1, cy1), (cx1 + cw, cy1 + ch)], radius=24, fill=WHITE)
    # Left stripe
    draw.rounded_rectangle([(cx1, cy1), (cx1 + 16, cy1 + ch)], radius=4, fill=P)
    # Top bar
    draw.rounded_rectangle([(cx1, cy1), (cx1 + cw, cy1 + 10)], radius=4, fill=P)

    tx = cx1 + 44
    ty = cy1 + 52
    max_text_w = cw - 60  # card width minus left stripe and right margin

    label_font = fonts["label"]
    label_bb = label_font.getbbox(lang_cfg["label"])
    if (label_bb[2] - label_bb[0]) > max_text_w:
        label_font = fit_text_font(lang_cfg["label"], max_text_w, HN, 10, start_size=34)

    title_font = fit_text_font(lang_cfg["title"], max_text_w, HN, 1, start_size=80)

    draw.text((tx, ty), lang_cfg["label"], font=label_font, fill=MID)
    draw.text((tx, ty + 50), lang_cfg["title"], font=title_font, fill=NAVY)

    # Divider
    div_y = ty + 150
    draw.line([(tx, div_y), (cx1 + cw - 30, div_y)], fill=(210, 200, 185), width=2)

    # Bullets
    for i, bullet in enumerate(lang_cfg["bullets"]):
        by = div_y + 40 + i * 60
        draw.ellipse([(tx, by + 10), (tx + 16, by + 26)], fill=A)
        draw.text((tx + 28, by), bullet, font=fonts["bullet"], fill=MID)

    # Brand watermark
    draw.text((SIZE // 2, SIZE - 52), "PlannerAtlas", font=fonts["brand"],
              fill=(175, 162, 140), anchor="mm")

    # Language badge (bottom-right of card)
    badge_text = lang_cfg["badge"]
    bbox = fonts["badge"].getbbox(badge_text)
    bw = bbox[2] - bbox[0] + 32
    bh = 44
    bx = cx1 + cw - bw - 16
    by2 = cy1 + ch - bh - 16
    draw.rounded_rectangle([(bx, by2), (bx + bw, by2 + bh)], radius=22, fill=P)
    draw.text((bx + bw // 2, by2 + bh // 2), badge_text, font=fonts["badge"],
              fill=WHITE, anchor="mm")

    # Instant Download tag (bottom-right corner of image)
    tag_text = "✦ Instant Download  ·  PDF  ·  A4"
    draw.text((SIZE - 60, SIZE - 52), tag_text, font=fonts["brand"],
              fill=(155, 145, 128), anchor="rm")

    canvas.save(out_path, "JPEG", quality=95, dpi=(300, 300))
    print(f"✅")

# ── Run ────────────────────────────────────────────────────────────────────────

fonts = load_fonts()  # pre-load once

total = 0
for product_dir, product_cfg in PRODUCTS.items():
    content_page_idx = product_cfg["page_content"]
    for lang in ["DE", "ES", "PT", "EN"]:
        lang_cfg = product_cfg[lang]
        for tname in ["indigo", "sage", "terracotta"]:
            pdf_path = f"{BASE}/{product_dir}/{lang}/{lang_cfg['filename']}_{tname}.pdf"
            out_path = f"{BASE}/{product_dir}/{lang}/mockup_{lang}_{tname}.jpg"
            if not os.path.exists(pdf_path):
                print(f"SKIP (PDF not found): {pdf_path}")
                continue
            print(f"[{product_dir}/{lang}/{tname}]", end=" ")
            make_mockup(pdf_path, out_path, tname, lang_cfg, product_dir)
            total += 1

print(f"\n✅ {total} mockups gerados.")
