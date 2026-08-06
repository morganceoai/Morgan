"""
Gera imagens de preview dos PDFs e faz upload para os listings Etsy.
Mostra 65% do PDF + watermark diagonal "PlannerAtlas".
Upload como rank 4 e 5 em cada listing.
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv()

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io

from etsy_service import upload_listing_image, ETSY_SHOP_ID

PLANNERS_DIR = ROOT / "businesses" / "planners"
OUT_DIR = ROOT / "scripts" / "_preview_cache"
OUT_DIR.mkdir(exist_ok=True)

# Páginas a mostrar por produto (índice 0-based)
# Escolhemos as mais representativas do conteúdo real
PRODUCT_PAGES = {
    "weekly_planner":  [1, 2],   # weekly spread + goal page
    "monthly_planner": [0, 1],   # monthly overview (só 2 páginas)
    "daily_planner":   [0, 1],   # daily schedule + notes
    "meal_planner":    [0, 1],   # weekly meal + shopping list
    "habit_tracker":   [0, 1],   # habit grid + review
    "budget_tracker":  [0, 1],   # budget overview + tracker
}

# listing_id → (product, lang, color_prefix)
# Usamos o primeiro PDF disponível por idioma (qualquer cor)
LISTINGS = {
    # Weekly
    4535134826: ("weekly_planner",  "en"),
    4535122419: ("weekly_planner",  "de"),
    4535133850: ("weekly_planner",  "es"),
    4535133344: ("weekly_planner",  "pt"),
    # Monthly
    4535131460: ("monthly_planner", "en"),
    4535118477: ("monthly_planner", "de"),
    4535117293: ("monthly_planner", "es"),
    4535130242: ("monthly_planner", "pt"),
    # Meal
    4535113125: ("meal_planner",    "en"),
    4535115041: ("meal_planner",    "de"),
    4535125050: ("meal_planner",    "es"),
    4535110809: ("meal_planner",    "pt"),
    # Habit
    4535122246: ("habit_tracker",   "en"),
    4535123160: ("habit_tracker",   "de"),
    4535108575: ("habit_tracker",   "es"),
    4535120410: ("habit_tracker",   "pt"),
    # Daily
    4535117850: ("daily_planner",   "en"),
    4535118376: ("daily_planner",   "de"),
    4535117246: ("daily_planner",   "es"),
    4535116440: ("daily_planner",   "pt"),
    # Budget
    4535113942: ("budget_tracker",  "en"),
    4535101803: ("budget_tracker",  "de"),
    4535100131: ("budget_tracker",  "es"),
    4535112532: ("budget_tracker",  "pt"),
}


def find_pdf(product: str, lang: str) -> Path | None:
    """Encontra o primeiro PDF disponível para produto + idioma."""
    lang_dir = PLANNERS_DIR / product / lang.lower()
    if not lang_dir.exists():
        # tenta upper
        lang_dir = PLANNERS_DIR / product / lang.upper()
    if not lang_dir.exists():
        return None
    pdfs = sorted(lang_dir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def render_preview(pdf_path: Path, page_idx: int, out_path: Path) -> bool:
    """
    Extrai página, corta a 65% da altura, adiciona watermark diagonal.
    Guarda como JPEG em out_path.
    """
    doc = fitz.open(str(pdf_path))
    if page_idx >= len(doc):
        page_idx = len(doc) - 1
    page = doc[page_idx]

    # Render a 150 DPI (factor ~2.08 sobre 72dpi)
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Cortar 65% da altura
    crop_h = int(img.height * 0.65)
    img = img.crop((0, 0, img.width, crop_h))

    # Watermark diagonal
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    text = "PlannerAtlas"
    font_size = max(28, img.width // 18)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Calcular tamanho do texto
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Repetir o texto em diagonal
    step_x = tw + 80
    step_y = th + 60
    for y0 in range(-img.height, img.height * 2, step_y):
        for x0 in range(-img.width, img.width * 2, step_x):
            draw.text((x0, y0), text, font=font, fill=(120, 120, 120, 80))

    # Rodar overlay 30 graus
    overlay_rot = overlay.rotate(30, expand=False)
    # Recrop para tamanho original (rotate com expand=False mantém tamanho)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay_rot)
    img = img.convert("RGB")

    img.save(str(out_path), "JPEG", quality=85)
    return True


def main():
    print(f"PlannerAtlas Preview Uploader")
    print(f"================================")
    print(f"Shop ID: {ETSY_SHOP_ID}")
    print()

    total = 0
    ok = 0
    skip = 0

    for listing_id, (product, lang) in LISTINGS.items():
        pdf_path = find_pdf(product, lang)
        if not pdf_path:
            print(f"  ✗ {listing_id} — PDF não encontrado: {product}/{lang}")
            skip += 1
            continue

        pages = PRODUCT_PAGES.get(product, [0, 1])
        uploads_ok = 0

        for rank_offset, page_idx in enumerate(pages):
            rank = 4 + rank_offset  # rank 4 e 5
            cache_name = f"{listing_id}_p{page_idx}.jpg"
            out_path = OUT_DIR / cache_name

            # Gerar preview se não existir
            if not out_path.exists():
                try:
                    render_preview(pdf_path, page_idx, out_path)
                    print(f"  → Gerado: {cache_name}")
                except Exception as e:
                    print(f"  ✗ Erro ao gerar preview {cache_name}: {e}")
                    continue

            total += 1
            success = upload_listing_image(listing_id, str(out_path), rank=rank)
            if success:
                uploads_ok += 1
                print(f"  ✓ {listing_id} ({product}/{lang}) rank={rank} ← {cache_name}")
            else:
                print(f"  ✗ {listing_id} ({product}/{lang}) rank={rank} FALHOU upload")

        if uploads_ok == len(pages):
            ok += 1

    print()
    print(f"Concluído: {ok}/{len(LISTINGS) - skip} listings com previews completos, {skip} sem PDF.")


if __name__ == "__main__":
    main()
