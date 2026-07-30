"""
Publica os 4 listings premium EN no Etsy PlannerAtlas.
Requer: token OAuth válido em memory/etsy_tokens.json
"""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os

TOKENS_FILE = Path(__file__).parent.parent / "memory" / "etsy_tokens.json"
PREMIUM_DIR = Path(__file__).parent.parent / "premium"
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY_HEADER = f"{KEYSTRING}:{SHARED_SECRET}"

def get_token():
    data = json.loads(TOKENS_FILE.read_text())
    from datetime import datetime, timezone
    expiry = datetime.fromisoformat(data["expiry"])
    if datetime.now(timezone.utc) < expiry:
        return data["token"]
    # refresh
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": KEYSTRING,
        "refresh_token": data["refresh_token"],
    })
    r.raise_for_status()
    new = r.json()
    from datetime import timedelta
    exp = datetime.now(timezone.utc) + timedelta(seconds=new["expires_in"])
    data2 = {"token": new["access_token"], "refresh_token": new["refresh_token"], "expiry": exp.isoformat()}
    TOKENS_FILE.write_text(json.dumps(data2))
    print("Token renovado")
    return new["access_token"]


LISTINGS = [
    {
        "slug": "weekly_planner",
        "title": "Weekly Planner Printable | Luxury Undated Weekly Planner PDF | Minimalist Productivity Planner | Instant Download | A4 Letter",
        "description": """✨ WEEKLY PLANNER PREMIUM — Printable PDF Instant Download

Elevate your week with our luxury weekly planner, designed for the purposeful and ambitious. Featuring elegant serif typography, sage green accents, and a thoughtfully structured layout — this is not just a planner, it's a lifestyle upgrade.

🗓 WHAT'S INCLUDED:
• 12 pages — Undated weekly spreads (Mon–Sun)
• Time-blocked daily columns
• Priorities + goals section
• Notes & reflections space
• A4 + US Letter sizes in one file

✏️ HOW IT WORKS:
1. Purchase → Instant download
2. Print at home or at any print shop
3. Start your most intentional week ever

🖨 PRINT TIPS:
Best printed on 90–120gsm paper for a premium feel. Works beautifully in any ring binder or planner cover.

💛 WHY CHOOSE PREMIUM:
Unlike generic templates, our planners are designed with precision typography, thoughtful white space, and layouts tested for real productivity.

🌍 LANGUAGES AVAILABLE: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved. For personal use only.""",
        "price": 8.00,
        "tags": ["weekly planner pdf", "undated planner", "luxury planner", "productivity planner", "minimalist planner", "instant download", "digital planner", "weekly schedule", "work planner", "premium planner", "printable planner", "time blocking"],
        "pdf": PREMIUM_DIR / "weekly_planner/EN/pdf/weekly_planner_premium_EN.pdf",
        "images": [
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_01_marble_dark.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_02_closeup.png",
            PREMIUM_DIR / "weekly_planner/EN/images/weekly_03_hands.png",
        ],
    },
    {
        "slug": "monthly_planner",
        "title": "Monthly Planner Printable | Luxury Undated Monthly Calendar PDF | Minimalist Monthly Overview | Instant Download | A4 Letter",
        "description": """✨ MONTHLY PLANNER PREMIUM — Printable PDF Instant Download

See your entire month at a glance with our elegant undated monthly planner. Navy blue and cream design with generous writing space — built for those who think in months, not just days.

📅 WHAT'S INCLUDED:
• 10 pages — Undated monthly calendar spreads
• Full month grid with notes column
• Monthly goals & intentions page
• Key dates & important events tracker
• A4 + US Letter sizes in one file

✏️ HOW IT WORKS:
1. Purchase → Instant download
2. Print at home or at any print shop
3. Plan your most intentional month yet

💛 PREMIUM DESIGN:
Sophisticated navy and cream palette with elegant typography. Designed to inspire calm, purposeful planning.

🌍 LANGUAGES AVAILABLE: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved. For personal use only.""",
        "price": 8.00,
        "tags": ["monthly planner pdf", "undated planner", "monthly calendar", "luxury planner", "minimalist planner", "instant download", "digital planner", "monthly goals", "navy planner", "premium planner", "printable calendar", "goal planner"],
        "pdf": PREMIUM_DIR / "monthly_planner/EN/pdf/monthly_planner_premium_EN.pdf",
        "images": [
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_01_marble_dark.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_02_closeup.png",
            PREMIUM_DIR / "monthly_planner/EN/images/monthly_03_aerial_linen.png",
        ],
    },
    {
        "slug": "habit_tracker",
        "title": "Habit Tracker Printable | Luxury Monthly Habit Tracker PDF | 66-Day Challenge | Minimalist Habit Log | Instant Download",
        "description": """✨ HABIT TRACKER PREMIUM — Printable PDF Instant Download

Build the life you want, one habit at a time. Our luxury habit tracker features a clean monthly grid, progress bars, and reflective journaling space — designed in sophisticated forest green and cream.

✅ WHAT'S INCLUDED:
• 8 pages — Monthly habit tracking grids
• 66-day habit challenge tracker
• Weekly reflection prompts
• Habit streaks visualization
• A4 + US Letter sizes in one file

Track up to 20 habits per month. Works for fitness, sleep, mindfulness, reading, hydration — any goal you're building toward.

💛 PREMIUM DESIGN:
Forest green and cream palette. Sophisticated, calm, and built for consistency.

🌍 LANGUAGES AVAILABLE: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved. For personal use only.""",
        "price": 8.00,
        "tags": ["habit tracker pdf", "monthly habits", "66 day challenge", "habit tracker", "luxury planner", "minimalist tracker", "daily habits", "routine tracker", "self improvement", "wellness tracker", "premium planner", "productivity"],
        "pdf": PREMIUM_DIR / "habit_tracker/EN/pdf/habit_tracker_premium_EN.pdf",
        "images": [
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_aerial_green.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_02_closeup.png",
            PREMIUM_DIR / "habit_tracker/EN/images/habit_03_green_leather.png",
        ],
    },
    {
        "slug": "budget_tracker",
        "title": "Budget Tracker Printable | Luxury Monthly Budget Planner PDF | Income Expense Tracker | Financial Planner | Instant Download",
        "description": """✨ BUDGET TRACKER PREMIUM — Printable PDF Instant Download

Take control of your finances with clarity and elegance. Our luxury budget tracker features charcoal and gold accents, income vs. expense breakdowns, and savings goal tracking — because your financial future deserves beautiful tools.

💰 WHAT'S INCLUDED:
• 10 pages — Monthly budget spreads
• Income tracker (multiple income streams)
• Fixed & variable expense log
• Savings goals tracker
• Net worth overview page
• A4 + US Letter sizes in one file

Perfect for freelancers, entrepreneurs, and anyone serious about building wealth intentionally.

💛 PREMIUM DESIGN:
Sophisticated charcoal and gold palette. Executive aesthetic meets functional clarity.

🌍 LANGUAGES AVAILABLE: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved. For personal use only.""",
        "price": 8.00,
        "tags": ["budget tracker pdf", "monthly budget", "expense tracker", "financial planner", "luxury planner", "money management", "savings tracker", "expense log", "personal finance", "premium planner", "instant download", "debt payoff"],
        "pdf": PREMIUM_DIR / "budget_tracker/EN/pdf/budget_tracker_premium_EN.pdf",
        "images": [
            PREMIUM_DIR / "budget_tracker/EN/images/budget_01_walnut_moody.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_02_hands.png",
            PREMIUM_DIR / "budget_tracker/EN/images/budget_03_marble_aerial.png",
        ],
    },
]


def create_listing(token, listing_data):
    """Cria um listing digital no Etsy."""
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": API_KEY_HEADER,
        "Content-Type": "application/json",
    }

    payload = {
        "quantity": 999,
        "title": listing_data["title"][:140],
        "description": listing_data["description"],
        "price": listing_data["price"],
        "who_made": "i_did",
        "when_made": "2020_2026",
        "taxonomy_id": 2078,  # Paper & Party Supplies > Paper > Stationery
        "tags": listing_data["tags"][:13],
        "is_digital": True,
        "type": "download",
        "state": "draft",
    }

    r = requests.post(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings",
        headers=headers,
        json=payload,
    )
    if not r.ok:
        print(f"  ERRO criar listing: {r.status_code} {r.text[:300]}")
        return None
    return r.json()


def upload_digital_file(token, listing_id, pdf_path):
    """Faz upload do PDF como ficheiro digital."""
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": API_KEY_HEADER,
    }
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{listing_id}/files",
            headers=headers,
            files={"file": (pdf_path.name, f, "application/pdf")},
            data={"name": pdf_path.name, "rank": 1},
        )
    if not r.ok:
        print(f"  ERRO upload PDF: {r.status_code} {r.text[:300]}")
        return False
    print(f"  PDF carregado: {pdf_path.name}")
    return True


def upload_image(token, listing_id, image_path, rank):
    """Faz upload de imagem de listing."""
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": API_KEY_HEADER,
    }
    with open(image_path, "rb") as f:
        r = requests.post(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{listing_id}/images",
            headers=headers,
            files={"image": (image_path.name, f, "image/png")},
            data={"rank": rank, "overwrite": True},
        )
    if not r.ok:
        print(f"  ERRO upload imagem: {r.status_code} {r.text[:200]}")
        return False
    print(f"  Imagem {rank} carregada: {image_path.name}")
    return True


def publish_listing(token, listing_id):
    """Muda estado de draft para active."""
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": API_KEY_HEADER,
        "Content-Type": "application/json",
    }
    r = requests.patch(
        f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{listing_id}",
        headers=headers,
        json={"state": "active"},
    )
    if not r.ok:
        print(f"  ERRO publicar: {r.status_code} {r.text[:300]}")
        return False
    print(f"  ✅ Publicado!")
    return True


def main():
    print("=== ETSY PREMIUM PUBLISH ===\n")
    token = get_token()
    results = []

    for listing in LISTINGS:
        print(f"\n📦 {listing['slug'].upper()}")

        # 1. Criar listing em draft
        result = create_listing(token, listing)
        if not result:
            print("  ❌ Falhou criar listing")
            continue
        listing_id = result["listing_id"]
        print(f"  Draft criado: ID {listing_id}")

        # 2. Upload PDF
        if listing["pdf"].exists():
            upload_digital_file(token, listing_id, listing["pdf"])
        else:
            print(f"  ⚠️ PDF não encontrado: {listing['pdf']}")

        # 3. Upload imagens
        for i, img_path in enumerate(listing["images"], 1):
            if img_path.exists():
                upload_image(token, listing_id, img_path, i)
                time.sleep(0.5)
            else:
                print(f"  ⚠️ Imagem não encontrada: {img_path}")

        # 4. Publicar
        time.sleep(1)
        publish_listing(token, listing_id)

        results.append({
            "slug": listing["slug"],
            "listing_id": listing_id,
            "url": f"https://www.etsy.com/listing/{listing_id}",
        })
        time.sleep(2)

    print("\n\n=== RESULTADO FINAL ===")
    for r in results:
        print(f"✅ {r['slug']}: {r['url']}")

    return results


if __name__ == "__main__":
    main()
