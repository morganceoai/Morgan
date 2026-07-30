"""Upload de vídeos para os 20 listings premium publicados."""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv('/Users/vascobotelhodacosta/Morgan/.env')
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


# listing_id → video path (reutilizar vídeos EN para todos os idiomas)
VIDEOS = [
    (4546893556, PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4"),
    (4546878659, PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4"),
    (4546893756, PREMIUM_DIR / "weekly_planner/EN/video/weekly_premium_EN.mp4"),
    (4546878887, PREMIUM_DIR / "monthly_planner/EN/video/monthly_premium_EN.mp4"),
    (4546879013, PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4"),
    (4546894114, PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4"),
    (4546879277, PREMIUM_DIR / "habit_tracker/EN/video/habit_premium_EN.mp4"),
    (4546879437, PREMIUM_DIR / "budget_tracker/EN/video/budget_premium_EN.mp4"),
    (4546894554, PREMIUM_DIR / "weekly_planner/EN/video/weekly_premium_EN.mp4"),
    (4546879695, PREMIUM_DIR / "monthly_planner/EN/video/monthly_premium_EN.mp4"),
    (4546879847, PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4"),
    (4546879995, PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4"),
    (4546880181, PREMIUM_DIR / "habit_tracker/EN/video/habit_premium_EN.mp4"),
    (4546895218, PREMIUM_DIR / "budget_tracker/EN/video/budget_premium_EN.mp4"),
    (4546880439, PREMIUM_DIR / "weekly_planner/EN/video/weekly_premium_EN.mp4"),
    (4546895486, PREMIUM_DIR / "monthly_planner/EN/video/monthly_premium_EN.mp4"),
    (4546880655, PREMIUM_DIR / "daily_planner/EN/video/daily_premium_EN.mp4"),
    (4546880797, PREMIUM_DIR / "meal_planner/EN/video/meal_premium_EN.mp4"),
    (4546895900, PREMIUM_DIR / "habit_tracker/EN/video/habit_premium_EN.mp4"),
    (4546880999, PREMIUM_DIR / "budget_tracker/EN/video/budget_premium_EN.mp4"),
]


def upload_video(token, lid, path):
    headers = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY_HEADER}
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/videos",
            headers=headers,
            files={"video": (path.name, f, "video/mp4")},
            data={"name": path.stem},
        )
    if r.ok:
        print(f"  ✅ {lid} — vídeo adicionado")
        return True
    else:
        print(f"  ❌ {lid} — {r.status_code}: {r.text[:150]}")
        return False


def main():
    print(f"=== UPLOAD VÍDEOS — {len(VIDEOS)} listings ===\n")
    token = get_token()
    ok = 0
    for lid, path in VIDEOS:
        if not path.exists():
            print(f"  ⚠️  {lid} — ficheiro não existe: {path}")
            continue
        if upload_video(token, lid, path):
            ok += 1
        time.sleep(1.5)
    print(f"\n✅ {ok}/{len(VIDEOS)} vídeos adicionados")


if __name__ == "__main__":
    main()
