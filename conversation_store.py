"""
Histórico de conversa centralizado — Supabase.
Telegram e Desktop partilham o mesmo histórico via base de dados na cloud.
Fallback para ficheiro local se Supabase não estiver configurado.
"""
import os
import json
import httpx
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nzewcorujofapxymupzr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
MAX_MESSAGES = 100

# Fallback local (usado se SUPABASE_KEY não estiver definido)
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "memory", "historico.json")

MORGAN_USER_ID = "vasco"  # ID único partilhado por todos os canais


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _supabase_ok() -> bool:
    return bool(SUPABASE_KEY)


# ── Supabase ──────────────────────────────────────────────────────────────────

def _sb_load(user_id: str) -> list:
    try:
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        r = httpx.get(url, headers=_headers(), params={
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(MAX_MESSAGES),
        }, timeout=6)
        rows = r.json()
        if not isinstance(rows, list):
            return []
        rows.reverse()
        return rows
    except Exception:
        return []


def _sb_save(user_id: str, role: str, content: str):
    try:
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        httpx.post(url, headers=_headers(), json={
            "user_id": user_id,
            "role": role,
            "content": content,
        }, timeout=6)
    except Exception:
        pass


# ── Fallback ficheiro local ───────────────────────────────────────────────────

def _file_load(user_id: str) -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(user_id, [])[-MAX_MESSAGES:]


def _file_save(user_id: str, role: str, content: str):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    data = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    if user_id not in data:
        data[user_id] = []
    if isinstance(content, str):
        data[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
    data[user_id] = data[user_id][-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── API pública ───────────────────────────────────────────────────────────────

def load_history(user_id: str) -> list:
    if _supabase_ok():
        return _sb_load(user_id)
    return _file_load(user_id)


def save_message(user_id: str, role: str, content: str):
    if not isinstance(content, str):
        return
    if _supabase_ok():
        _sb_save(user_id, role, content)
    else:
        _file_save(user_id, role, content)


def get_context_messages(user_id: str) -> list:
    history = load_history(user_id)
    return [{"role": m["role"], "content": m["content"]} for m in history]
