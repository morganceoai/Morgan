"""
Passo 1: Apaga os 22 listings novos duplicados (4547xxx)
Passo 2: Gera preview do PDF novo + watermark para os 24 premium antigos
Passo 3: Upload como imagem rank 2 nos 24 premium antigos
"""

import sys, os, time, json, io, requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv()

import fitz
from PIL import Image, ImageDraw, ImageFont

TOKENS_FILE = ROOT / "memory" / "etsy_tokens.json"
SCRIPTS_DIR = ROOT / "scripts"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY = f"{KEYSTRING}:{SHARED_SECRET}"
OUT_DIR = SCRIPTS_DIR / "_preview_cache_premium"
OUT_DIR.mkdir(exist_ok=True)


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


def hdrs(token, json_ct=False):
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY}
    if json_ct: h["Content-Type"] = "application/json"
    return h


# ── 22 listings duplicados a apagar ──────────────────────────────────────────
DELETE_IDS = [
    4547664433, 4547664323, 4547664177, 4547677876,   # EN
    4547668828, 4547654697, 4547668600, 4547668428, 4547668276, 4547654093,  # PT
    4547668012, 4547653797, 4547667768, 4547653537, 4547667522, 4547653261,  # ES
    4547653137, 4547653023, 4547666960, 4547666828, 4547652577, 4547666552,  # DE
]

# ── 24 listings premium antigos → PDF novo ───────────────────────────────────
PREMIUM = {
    4546792825: SCRIPTS_DIR / "weekly_planner_EN.pdf",
    4546807058: SCRIPTS_DIR / "monthly_planner_EN.pdf",
    4546893556: SCRIPTS_DIR / "daily_planner_EN.pdf",
    4546807140: SCRIPTS_DIR / "habit_tracker_EN.pdf",
    4546807228: SCRIPTS_DIR / "budget_planner_EN.pdf",
    4546878659: SCRIPTS_DIR / "meal_planner_EN.pdf",
    4546893756: SCRIPTS_DIR / "weekly_planner_DE.pdf",
    4546878887: SCRIPTS_DIR / "monthly_planner_DE.pdf",
    4546879013: SCRIPTS_DIR / "daily_planner_DE.pdf",
    4546879277: SCRIPTS_DIR / "habit_tracker_DE.pdf",
    4546879437: SCRIPTS_DIR / "budget_planner_DE.pdf",
    4546894114: SCRIPTS_DIR / "meal_planner_DE.pdf",
    4546894554: SCRIPTS_DIR / "weekly_planner_ES.pdf",
    4546879695: SCRIPTS_DIR / "monthly_planner_ES.pdf",
    4546879847: SCRIPTS_DIR / "daily_planner_ES.pdf",
    4546880181: SCRIPTS_DIR / "habit_tracker_ES.pdf",
    4546895218: SCRIPTS_DIR / "budget_planner_ES.pdf",
    4546879995: SCRIPTS_DIR / "meal_planner_ES.pdf",
    4546880439: SCRIPTS_DIR / "weekly_planner_PT.pdf",
    4546895486: SCRIPTS_DIR / "monthly_planner_PT.pdf",
    4546880655: SCRIPTS_DIR / "daily_planner_PT.pdf",
    4546895900: SCRIPTS_DIR / "habit_tracker_PT.pdf",
    4546880999: SCRIPTS_DIR / "budget_planner_PT.pdf",
    4546880797: SCRIPTS_DIR / "meal_planner_PT.pdf",
}


def render_preview(pdf_path: Path, out_path: Path):
    """Página 1 do PDF, corte 65%, watermark diagonal PlannerAtlas."""
    doc = fitz.open(str(pdf_path))
    page_idx = 1 if len(doc) > 1 else 0
    page = doc[page_idx]
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    crop_h = int(img.height * 0.65)
    img = img.crop((0, 0, img.width, crop_h))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = "PlannerAtlas"
    font_size = max(28, img.width // 18)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    for y0 in range(-img.height, img.height * 2, th + 60):
        for x0 in range(-img.width, img.width * 2, tw + 80):
            draw.text((x0, y0), text, font=font, fill=(120, 120, 120, 80))

    overlay_rot = overlay.rotate(30, expand=False)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay_rot).convert("RGB")
    img.save(str(out_path), "JPEG", quality=85)


def upload_image_rank2(token, lid, img_path: Path):
    with open(img_path, "rb") as f:
        r = requests.post(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/images",
            headers=hdrs(token),
            files={"image": (img_path.name, f, "image/jpeg")},
            data={"rank": 2, "overwrite": True},
        )
    return r.ok, r.text[:150] if not r.ok else ""


def main():
    token = get_token()

    # ── PASSO 1: Apagar 22 duplicados ────────────────────────────────────────
    print(f"\n=== PASSO 1: Apagar {len(DELETE_IDS)} listings duplicados ===\n")
    deleted = 0
    for lid in DELETE_IDS:
        # Tornar inativo primeiro (necessário para delete em alguns casos)
        requests.patch(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
            headers=hdrs(token, True), json={"state": "inactive"}
        )
        time.sleep(0.3)
        r = requests.delete(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
            headers=hdrs(token)
        )
        if r.ok or r.status_code == 404:
            print(f"  ✅ Apagado {lid}")
            deleted += 1
        else:
            print(f"  ❌ {lid}: {r.status_code} {r.text[:100]}")
        time.sleep(0.5)
    print(f"\nApagados: {deleted}/{len(DELETE_IDS)}")

    # ── PASSO 2+3: Preview + upload rank 2 nos 24 premium ────────────────────
    print(f"\n=== PASSO 2+3: Preview + upload rank 2 — {len(PREMIUM)} listings ===\n")
    ok_count = 0
    for lid, pdf_path in PREMIUM.items():
        label = pdf_path.stem
        print(f"\n📦 {lid} — {label}")

        if not pdf_path.exists():
            print(f"  ⚠️  PDF não existe")
            continue

        out_path = OUT_DIR / f"{lid}_preview.jpg"
        try:
            render_preview(pdf_path, out_path)
            print(f"  Preview gerado ✓")
        except Exception as e:
            print(f"  ❌ Erro preview: {e}")
            continue

        ok, err = upload_image_rank2(token, lid, out_path)
        if ok:
            print(f"  Imagem rank 2 ✓")
            ok_count += 1
        else:
            print(f"  ❌ Upload: {err}")
        time.sleep(1)

    print(f"\n=== RESULTADO FINAL ===")
    print(f"Duplicados apagados: {deleted}/{len(DELETE_IDS)}")
    print(f"Previews carregados: {ok_count}/{len(PREMIUM)}")


if __name__ == "__main__":
    main()
