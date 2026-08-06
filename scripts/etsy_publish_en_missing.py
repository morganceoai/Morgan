"""Publica os 4 EN que faltam: Weekly, Monthly, Habit, Budget"""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv('/Users/vascobotelhodacosta/Morgan/.env')
import os

TOKENS_FILE = Path(__file__).parent.parent / "memory" / "etsy_tokens.json"
SCRIPTS_DIR = Path(__file__).parent
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
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type": "refresh_token", "client_id": KEYSTRING, "refresh_token": data["refresh_token"],
    })
    r.raise_for_status()
    new = r.json()
    from datetime import timedelta
    exp = datetime.now(timezone.utc) + timedelta(seconds=new["expires_in"])
    TOKENS_FILE.write_text(json.dumps({"token": new["access_token"], "refresh_token": new["refresh_token"], "expiry": exp.isoformat()}))
    return new["access_token"]


def imgs(key):
    p = PREMIUM_DIR / key / "EN" / "images"
    return sorted(p.glob("*.png"))[:3] if p.exists() else []

def vid(key):
    v = PREMIUM_DIR / key / "EN" / "video"
    files = sorted(v.glob("*.mp4")) if v.exists() else []
    return files[0] if files else None

def hdrs(token, json_ct=False):
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY_HEADER}
    if json_ct: h["Content-Type"] = "application/json"
    return h

def create_listing(token, d):
    r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings",
                      headers=hdrs(token, True), json={
        "quantity": 999, "title": d["title"][:140], "description": d["description"],
        "price": 7.99, "who_made": "i_did", "when_made": "2020_2026",
        "taxonomy_id": 2078, "tags": [t[:20] for t in d["tags"][:13]],
        "is_digital": True, "type": "download", "state": "draft",
    })
    if not r.ok: print(f"  ERRO: {r.status_code} {r.text[:200]}"); return None
    return r.json()["listing_id"]

def upload_pdf(token, lid, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files",
                          headers=hdrs(token), files={"file": (path.name, f, "application/pdf")},
                          data={"name": path.name, "rank": 1})
    print("  PDF ✓" if r.ok else f"  ERRO pdf: {r.text[:100]}")

def upload_image(token, lid, path, rank):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/images",
                          headers=hdrs(token), files={"image": (path.name, f, "image/png")},
                          data={"rank": rank, "overwrite": True})
    print(f"  Img {rank} ✓" if r.ok else f"  ERRO img{rank}: {r.text[:100]}")

def upload_video(token, lid, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/videos",
                          headers=hdrs(token), files={"video": (path.name, f, "video/mp4")},
                          data={"name": path.stem})
    print("  Vídeo ✓" if r.ok else f"  ERRO vídeo: {r.text[:100]}")

def publish(token, lid):
    r = requests.patch(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                       headers=hdrs(token, True), json={"state": "active"})
    return r.ok


LISTINGS = [
    {
        "slug": "weekly_planner", "lang": "EN",
        "title": "Weekly Planner Printable | Luxury Undated Weekly Planner PDF | Habit Tracker | Mood Tracker | Instant Download | A4",
        "description": """✨ WEEKLY PLANNER PREMIUM — Printable PDF Instant Download

Elevate your week with our luxury weekly planner in sage green and cream. Designed for ambitious professionals who live with intention.

🗓 INCLUDES:
• Annual & Monthly Overview
• Weekly Planner × 4 (with time schedule)
• Habit Tracker
• Mood Tracker
• Goals & Intentions
• Notes × 2

🌍 LANGUAGES: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved.""",
        "tags": ["weekly planner pdf","undated planner","printable planner","luxury planner","productivity","instant download","digital planner","weekly spread","premium planner","habit tracker"],
        "pdf": SCRIPTS_DIR / "weekly_planner_EN.pdf",
        "img_key": "weekly_planner",
    },
    {
        "slug": "monthly_planner", "lang": "EN",
        "title": "Monthly Planner Printable | Luxury Undated Monthly Planner PDF | Monthly Calendar | Goals | Instant Download | A4",
        "description": """✨ MONTHLY PLANNER PREMIUM — Printable PDF Instant Download

Visualise your entire month at a glance with our elegant monthly planner in sage green and cream.

📅 INCLUDES:
• Annual Overview
• January–December (12 pages)
• Goals & Intentions
• Notes × 2

🌍 LANGUAGES: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved.""",
        "tags": ["monthly planner pdf","undated planner","printable planner","luxury planner","monthly calendar","instant download","digital planner","monthly goals","premium planner","productivity"],
        "pdf": SCRIPTS_DIR / "monthly_planner_EN.pdf",
        "img_key": "monthly_planner",
    },
    {
        "slug": "habit_tracker", "lang": "EN",
        "title": "Habit Tracker Printable | Luxury Monthly Habit Tracker PDF | Mood Tracker | Self Improvement | Instant Download | A4",
        "description": """✨ HABIT TRACKER PREMIUM — Printable PDF Instant Download

Build the life you want, one habit at a time. Our luxury tracker in forest green and cream.

✅ INCLUDES:
• How to Use guide
• Monthly Habit Tracker × 12
• Habit Review × 2
• Notes × 2

🌍 LANGUAGES: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved.""",
        "tags": ["habit tracker pdf","monthly habit tracker","printable tracker","luxury planner","self improvement","instant download","routine tracker","premium tracker","mood tracker","habit journal"],
        "pdf": SCRIPTS_DIR / "habit_tracker_EN.pdf",
        "img_key": "habit_tracker",
    },
    {
        "slug": "budget_planner", "lang": "EN",
        "title": "Budget Planner Printable | Luxury Monthly Budget Planner PDF | Expense Tracker | Personal Finance | Instant Download",
        "description": """✨ BUDGET PLANNER PREMIUM — Printable PDF Instant Download

Take control of your finances with clarity and elegance.

💰 INCLUDES:
• Annual Financial Overview
• Monthly Budget × 12
• Debt Tracker
• Savings Goals
• Notes × 2

🌍 LANGUAGES: English · German · Spanish · Portuguese

© PlannerAtlas — All rights reserved.""",
        "tags": ["budget planner pdf","expense tracker","monthly budget","personal finance","luxury planner","instant download","money tracker","savings planner","premium planner","debt tracker"],
        "pdf": SCRIPTS_DIR / "budget_planner_EN.pdf",
        "img_key": "budget_tracker",
    },
]


def main():
    print(f"=== EN MISSING — {len(LISTINGS)} LISTINGS ===\n")
    token = get_token()
    results = []
    for d in LISTINGS:
        print(f"\n📦 {d['slug'].upper()} [EN]")
        lid = create_listing(token, d)
        if not lid: print("  ❌ Falhou"); continue
        print(f"  Draft ID: {lid}")
        if d["pdf"].exists(): upload_pdf(token, lid, d["pdf"])
        for i, img in enumerate(imgs(d["img_key"]), 1):
            upload_image(token, lid, img, i); time.sleep(0.5)
        v = vid(d["img_key"])
        if v: upload_video(token, lid, v)
        time.sleep(1)
        ok = publish(token, lid)
        url = f"https://www.etsy.com/listing/{lid}"
        if ok: print(f"  ✅ {url}"); results.append({"produto": d["slug"], "url": url})
        time.sleep(2)
    print(f"\n=== RESULTADO ===")
    for r in results: print(f"✅ {r['produto']}: {r['url']}")
    print(f"\nTotal: {len(results)}/{len(LISTINGS)}")

if __name__ == "__main__": main()
