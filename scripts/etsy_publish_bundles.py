"""
Cria e publica 3 bundle listings no Etsy PlannerAtlas.
Cada bundle = ZIP com todos os PDFs das 4 línguas.
"""

import sys, os, json, time, zipfile, requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv()

TOKENS_FILE = ROOT / "memory" / "etsy_tokens.json"
SCRIPTS_DIR = ROOT / "scripts"
PREMIUM_DIR = ROOT / "premium"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY = f"{KEYSTRING}:{SHARED_SECRET}"
BUNDLES_DIR = SCRIPTS_DIR / "_bundles"
BUNDLES_DIR.mkdir(exist_ok=True)

LANGS = ["EN", "DE", "ES", "PT"]

PRODUCTS = {
    "weekly_planner":  "weekly_planner",
    "monthly_planner": "monthly_planner",
    "daily_planner":   "daily_planner",
    "habit_tracker":   "habit_tracker",
    "budget_planner":  "budget_planner",
    "meal_planner":    "meal_planner",
}

BUNDLES = [
    {
        "name": "productivity_pack",
        "zip": "PlannerAtlas_Productivity_Pack.zip",
        "products": ["weekly_planner", "daily_planner", "habit_tracker"],
        "price": 14.99,
        "title": "Productivity Planner Bundle PDF | Weekly Planner + Daily Planner + Habit Tracker | 4 Languages | Instant Download | A4",
        "description": """✨ PRODUCTIVITY PLANNER BUNDLE — 3 Premium Planners · 4 Languages · Instant Download

Everything you need to plan your week, structure your days, and build lasting habits — in one elegant bundle.

📦 INCLUDED (12 PDFs total):

🗓 WEEKLY PLANNER:
• Annual & Monthly Overview · Weekly Planner × 4 · Habit Tracker · Mood Tracker · Goals & Intentions · Notes × 2

📅 DAILY PLANNER:
• Monthly Overview · Daily Pages × 10 (with time schedule) · Top 3 Priorities · Morning Routine + Evening Reflection · Notes × 2

✅ HABIT TRACKER:
• How to Use Guide · Monthly Habit Tracker × 12 · Habit Review × 2 · Notes × 2

🌍 LANGUAGES INCLUDED: English · Deutsch · Español · Português
📐 FORMAT: A4 PDF · Print at home or send to print shop
⬇️ INSTANT DOWNLOAD — Access immediately after purchase

~~€23.97~~ → Save 37%

© PlannerAtlas — All rights reserved. Personal use only.""",
        "tags": ["planner bundle pdf", "productivity bundle", "weekly planner pdf", "daily planner pdf", "habit tracker pdf", "instant download", "printable bundle", "planner set", "luxury planner", "4 languages"],
        "img_keys": ["weekly_planner", "daily_planner", "habit_tracker"],
    },
    {
        "name": "finance_meal_pack",
        "zip": "PlannerAtlas_Finance_Meal_Pack.zip",
        "products": ["budget_planner", "meal_planner"],
        "price": 11.99,
        "title": "Budget & Meal Planner Bundle PDF | Finance Tracker + Weekly Meal Planner | 4 Languages | Instant Download | A4",
        "description": """✨ FINANCE & MEAL PLANNER BUNDLE — 2 Premium Planners · 4 Languages · Instant Download

Take control of your money and your meals with our elegantly designed bundle.

📦 INCLUDED (8 PDFs total):

💰 BUDGET PLANNER:
• Annual Financial Overview · Monthly Budget × 12 · Debt Tracker · Savings Goals · Notes × 2

🍽 MEAL PLANNER:
• Weekly Meal Planner × 4 · Grocery List × 4 · Pantry Inventory · Favourite Recipes · Notes × 2

🌍 LANGUAGES INCLUDED: English · Deutsch · Español · Português
📐 FORMAT: A4 PDF · Print at home or send to print shop
⬇️ INSTANT DOWNLOAD — Access immediately after purchase

~~€15.98~~ → Save 25%

© PlannerAtlas — All rights reserved. Personal use only.""",
        "tags": ["budget planner bundle", "meal planner bundle", "finance planner pdf", "grocery list pdf", "instant download", "printable bundle", "budget tracker", "meal prep planner", "luxury planner", "4 languages"],
        "img_keys": ["budget_tracker", "meal_planner"],
    },
    {
        "name": "complete_bundle",
        "zip": "PlannerAtlas_Complete_Bundle.zip",
        "products": ["weekly_planner", "monthly_planner", "daily_planner", "habit_tracker", "budget_planner", "meal_planner"],
        "price": 24.99,
        "title": "Complete Planner Bundle PDF | All 6 Planners · Weekly Monthly Daily Habit Budget Meal | 4 Languages | Instant Download",
        "description": """✨ COMPLETE PLANNERATLAS BUNDLE — 6 Premium Planners · 4 Languages · Instant Download

The ultimate planning system. Every planner you need to organise your life — beautifully designed in sage green and cream.

📦 INCLUDED (24 PDFs total):

🗓 Weekly Planner — Annual overview · Weekly spreads · Habit & Mood tracker
📅 Monthly Planner — 12 monthly grids · Goals & Intentions
☀️ Daily Planner — Hourly schedule · Morning routine · Evening reflection
✅ Habit Tracker — 12-month tracker · Habit review pages
💰 Budget Planner — Annual overview · Monthly budgets · Debt & Savings tracker
🍽 Meal Planner — Weekly meal grid · Grocery list · Pantry & Recipes

🌍 LANGUAGES INCLUDED: English · Deutsch · Español · Português
📐 FORMAT: A4 PDF · Print at home or send to print shop
⬇️ INSTANT DOWNLOAD — 24 files, access immediately after purchase

~~€47.94~~ → Save 48%

© PlannerAtlas — All rights reserved. Personal use only.""",
        "tags": ["complete planner bundle", "planner bundle pdf", "all planners set", "instant download", "weekly monthly daily", "habit budget meal", "printable bundle", "luxury planner set", "4 languages", "productivity bundle"],
        "img_keys": ["weekly_planner", "monthly_planner", "daily_planner", "habit_tracker", "budget_tracker", "meal_planner"],
    },
]


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


def create_zip(bundle):
    zip_path = BUNDLES_DIR / bundle["zip"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for product in bundle["products"]:
            for lang in LANGS:
                pdf = SCRIPTS_DIR / f"{product}_{lang}.pdf"
                if pdf.exists():
                    zf.write(pdf, f"{product}_{lang}.pdf")
                    print(f"  + {pdf.name}")
                else:
                    print(f"  ⚠️  Não encontrado: {pdf.name}")
    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"  ZIP criado: {zip_path.name} ({size_mb:.2f} MB)")
    return zip_path


def create_listing(token, b):
    r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings",
                      headers=hdrs(token, True), json={
        "quantity": 999, "title": b["title"][:140], "description": b["description"],
        "price": b["price"], "who_made": "i_did", "when_made": "2020_2026",
        "taxonomy_id": 2078, "tags": [t[:20] for t in b["tags"][:13]],
        "is_digital": True, "type": "download", "state": "draft",
    })
    if not r.ok:
        print(f"  ❌ {r.status_code} {r.text[:200]}")
        return None
    return r.json()["listing_id"]


def upload_zip(token, lid, zip_path):
    with open(zip_path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files",
                          headers=hdrs(token),
                          files={"file": (zip_path.name, f, "application/zip")},
                          data={"name": zip_path.name, "rank": 1})
    return r.ok, r.text[:150] if not r.ok else ""


def upload_image(token, lid, img_path, rank):
    with open(img_path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/images",
                          headers=hdrs(token),
                          files={"image": (img_path.name, f, "image/png")},
                          data={"rank": rank, "overwrite": True})
    return r.ok


def publish(token, lid):
    r = requests.patch(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                       headers=hdrs(token, True), json={"state": "active"})
    return r.ok


def main():
    print("=== ETSY BUNDLES — 3 LISTINGS ===\n")
    token = get_token()
    results = []

    for b in BUNDLES:
        print(f"\n📦 {b['name'].upper()}")

        # 1. Criar ZIP
        print("  Criar ZIP...")
        zip_path = create_zip(b)

        # 2. Criar listing draft
        lid = create_listing(token, b)
        if not lid:
            print("  ❌ Listing falhou")
            continue
        print(f"  Draft ID: {lid}")

        # 3. Upload ZIP
        ok, err = upload_zip(token, lid, zip_path)
        print(f"  ZIP upload ✓" if ok else f"  ❌ ZIP: {err}")
        time.sleep(1)

        # 4. Upload imagens (até 3, usando a 1ª imagem EN de cada produto)
        rank = 1
        for img_key in b["img_keys"][:3]:
            img_dir = PREMIUM_DIR / img_key / "EN" / "images"
            imgs = sorted(img_dir.glob("*.png")) if img_dir.exists() else []
            if imgs:
                ok_img = upload_image(token, lid, imgs[0], rank)
                print(f"  Img {rank} ({img_key}) ✓" if ok_img else f"  ⚠️  Img {rank} falhou")
                rank += 1
                time.sleep(0.5)

        # 5. Publicar
        time.sleep(1)
        ok_pub = publish(token, lid)
        url = f"https://www.etsy.com/listing/{lid}"
        if ok_pub:
            print(f"  ✅ Publicado: {url}")
            results.append({"bundle": b["name"], "price": b["price"], "url": url})
        time.sleep(2)

    print("\n\n=== RESULTADO ===")
    for r in results:
        print(f"✅ {r['bundle']} (€{r['price']}): {r['url']}")
    print(f"\nTotal: {len(results)}/3")


if __name__ == "__main__":
    main()
