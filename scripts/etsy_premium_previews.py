"""
Gera previews com watermark dos 24 PDFs premium e faz upload como rank 2.
Mesma lógica do etsy_preview_images.py dos low-cost.
"""
import sys, json, time, requests, io
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
import os

import fitz
from PIL import Image, ImageDraw, ImageFont

TOKENS_FILE = ROOT / "memory" / "etsy_tokens.json"
PREMIUM_DIR = ROOT / "premium"
OUT_DIR = ROOT / "scripts" / "_preview_cache"
OUT_DIR.mkdir(exist_ok=True)
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY_HEADER = f"{KEYSTRING}:{SHARED_SECRET}"


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


LISTINGS = [
    (4546792825, "weekly_planner",  "EN"),
    (4546807058, "monthly_planner", "EN"),
    (4546807140, "habit_tracker",   "EN"),
    (4546807228, "budget_tracker",  "EN"),
    (4546893556, "daily_planner",   "EN"),
    (4546878659, "meal_planner",    "EN"),
    (4546893756, "weekly_planner",  "DE"),
    (4546878887, "monthly_planner", "DE"),
    (4546879013, "daily_planner",   "DE"),
    (4546894114, "meal_planner",    "DE"),
    (4546879277, "habit_tracker",   "DE"),
    (4546879437, "budget_tracker",  "DE"),
    (4546894554, "weekly_planner",  "ES"),
    (4546879695, "monthly_planner", "ES"),
    (4546879847, "daily_planner",   "ES"),
    (4546879995, "meal_planner",    "ES"),
    (4546880181, "habit_tracker",   "ES"),
    (4546895218, "budget_tracker",  "ES"),
    (4546880439, "weekly_planner",  "PT"),
    (4546895486, "monthly_planner", "PT"),
    (4546880655, "daily_planner",   "PT"),
    (4546880797, "meal_planner",    "PT"),
    (4546895900, "habit_tracker",   "PT"),
    (4546880999, "budget_tracker",  "PT"),
]


def render_preview(pdf_path: Path, out_path: Path):
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Cortar 65% da altura (mostra o produto sem revelar tudo)
    crop_h = int(img.height * 0.65)
    img = img.crop((0, 0, img.width, crop_h))

    # Watermark diagonal — igual ao low-cost
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = "PlannerAtlas"
    font_size = max(28, img.width // 18)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    step_x = tw + 80
    step_y = th + 60
    for y0 in range(-img.height, img.height * 2, step_y):
        for x0 in range(-img.width, img.width * 2, step_x):
            draw.text((x0, y0), text, font=font, fill=(120, 120, 120, 80))

    overlay_rot = overlay.rotate(30, expand=False)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay_rot)
    img = img.convert("RGB")
    img.save(str(out_path), "JPEG", quality=85)


def upload_image(token, lid, img_path, rank=2):
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY_HEADER}
    with open(img_path, "rb") as f:
        r = requests.post(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/images",
            headers=h,
            files={"image": (img_path.name, f, "image/jpeg")},
            data={"rank": rank, "overwrite": False},
        )
    return r.ok, r.status_code, r.text[:150] if not r.ok else ""


def main():
    print(f"=== PREMIUM PREVIEWS — {len(LISTINGS)} listings ===\n")
    token = get_token()
    ok = 0

    for lid, product, lang in LISTINGS:
        pdf = PREMIUM_DIR / product / lang / "pdf" / f"{product}_premium_{lang}.pdf"
        if not pdf.exists():
            print(f"❌ {lid} — PDF não existe: {pdf}")
            continue

        cache = OUT_DIR / f"premium_{lid}_p0.jpg"
        if not cache.exists():
            try:
                render_preview(pdf, cache)
            except Exception as e:
                print(f"❌ {lid} — erro render: {e}")
                continue

        success, code, err = upload_image(token, lid, cache, rank=2)
        if success:
            print(f"✅ {lid} ({product} {lang}) — preview rank 2 adicionado")
            ok += 1
        else:
            print(f"❌ {lid} — {code}: {err}")
        time.sleep(0.8)

    print(f"\n{ok}/{len(LISTINGS)} previews publicados")


if __name__ == "__main__":
    main()
