"""
Substitui o PDF nos 26 listings premium antigos (24 inativos + 2 EN já ativos)
e ativa os inativos. Mockups, vídeos e textos ficam intactos.
"""

import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv('/Users/vascobotelhodacosta/Morgan/.env')
import os

TOKENS_FILE = Path(__file__).parent.parent / "memory" / "etsy_tokens.json"
SCRIPTS_DIR = Path(__file__).parent
KEYSTRING = os.getenv("ETSY_KEYSTRING")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
SHOP_ID = os.getenv("ETSY_SHOP_ID", "66877755")
API_KEY_HEADER = f"{KEYSTRING}:{SHARED_SECRET}"


def get_token():
    data = json.loads(TOKENS_FILE.read_text())
    from datetime import datetime, timezone, timedelta
    expiry = datetime.fromisoformat(data["expiry"])
    if datetime.now(timezone.utc) < expiry:
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
    h = {"Authorization": f"Bearer {token}", "x-api-key": API_KEY_HEADER}
    if json_ct: h["Content-Type"] = "application/json"
    return h


def get_listing_files(token, lid):
    r = requests.get(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files",
                     headers=hdrs(token))
    return r.json().get("results", []) if r.ok else []


def delete_file(token, lid, file_id):
    r = requests.delete(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files/{file_id}",
                        headers=hdrs(token))
    return r.ok


def upload_pdf(token, lid, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}/files",
                          headers=hdrs(token),
                          files={"file": (path.name, f, "application/pdf")},
                          data={"name": path.name, "rank": 1})
    return r.ok, r.text[:150] if not r.ok else ""


def activate(token, lid):
    r = requests.patch(f"https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/{lid}",
                       headers=hdrs(token, True), json={"state": "active"})
    return r.ok


# Mapeamento: listing_id → pdf_path (já ativo ou inativo)
LISTINGS = {
    # ── EN (os 2 que ativamos com PDF velho + 4 inativos) ──
    4546893556: SCRIPTS_DIR / "daily_planner_EN.pdf",
    4546878659: SCRIPTS_DIR / "meal_planner_EN.pdf",
    4546807228: SCRIPTS_DIR / "budget_planner_EN.pdf",
    4546807140: SCRIPTS_DIR / "habit_tracker_EN.pdf",
    4546807058: SCRIPTS_DIR / "monthly_planner_EN.pdf",
    4546792825: SCRIPTS_DIR / "weekly_planner_EN.pdf",
    # ── DE ──
    4546879437: SCRIPTS_DIR / "budget_planner_DE.pdf",
    4546879277: SCRIPTS_DIR / "habit_tracker_DE.pdf",
    4546894114: SCRIPTS_DIR / "meal_planner_DE.pdf",
    4546879013: SCRIPTS_DIR / "daily_planner_DE.pdf",
    4546878887: SCRIPTS_DIR / "monthly_planner_DE.pdf",
    4546893756: SCRIPTS_DIR / "weekly_planner_DE.pdf",
    # ── ES ──
    4546895218: SCRIPTS_DIR / "budget_planner_ES.pdf",
    4546880181: SCRIPTS_DIR / "habit_tracker_ES.pdf",
    4546879995: SCRIPTS_DIR / "meal_planner_ES.pdf",
    4546879847: SCRIPTS_DIR / "daily_planner_ES.pdf",
    4546879695: SCRIPTS_DIR / "monthly_planner_ES.pdf",
    4546894554: SCRIPTS_DIR / "weekly_planner_ES.pdf",
    # ── PT ──
    4546880999: SCRIPTS_DIR / "budget_planner_PT.pdf",
    4546895900: SCRIPTS_DIR / "habit_tracker_PT.pdf",
    4546880797: SCRIPTS_DIR / "meal_planner_PT.pdf",
    4546880655: SCRIPTS_DIR / "daily_planner_PT.pdf",
    4546895486: SCRIPTS_DIR / "monthly_planner_PT.pdf",
    4546880439: SCRIPTS_DIR / "weekly_planner_PT.pdf",
}


def main():
    print(f"=== UPDATE PDFs — {len(LISTINGS)} LISTINGS ===\n")
    token = get_token()
    ok_count = 0

    for lid, pdf_path in LISTINGS.items():
        print(f"\n📦 {lid} — {pdf_path.name}")

        if not pdf_path.exists():
            print(f"  ⚠️  PDF não encontrado: {pdf_path}")
            continue

        # 1. Apagar PDF antigo
        files = get_listing_files(token, lid)
        for f in files:
            if f.get("filetype") == "download":
                deleted = delete_file(token, lid, f["listing_file_id"])
                print(f"  PDF antigo apagado ✓" if deleted else f"  ⚠️  Falhou apagar file {f['listing_file_id']}")
                time.sleep(0.3)

        # 2. Upload PDF novo
        ok, err = upload_pdf(token, lid, pdf_path)
        if ok:
            print(f"  PDF novo ✓")
        else:
            print(f"  ❌ Upload falhou: {err}")
            continue

        time.sleep(0.5)

        # 3. Ativar (se inativo)
        ok_act = activate(token, lid)
        print(f"  ✅ Ativo" if ok_act else f"  ⚠️  Já ativo ou erro ao ativar")
        ok_count += 1
        time.sleep(1.5)

    print(f"\n=== RESULTADO: {ok_count}/{len(LISTINGS)} atualizados ===")


if __name__ == "__main__":
    main()
