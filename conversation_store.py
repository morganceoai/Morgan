import os
import json
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "memory", "historico.json")
MAX_MESSAGES = 100  # Mensagens mais recentes a carregar no contexto


def load_history(user_id: str) -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Devolve só as últimas MAX_MESSAGES mensagens para não sobrecarregar o contexto
    return data.get(user_id, [])[-MAX_MESSAGES:]


def save_message(user_id: str, role: str, content: str):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if user_id not in data:
        data[user_id] = []

    # Só guarda mensagens de texto simples (não tool calls)
    if isinstance(content, str):
        data[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    # Guarda no máximo 500 mensagens por utilizador
    data[user_id] = data[user_id][-500:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_context_messages(user_id: str) -> list:
    """Devolve o histórico no formato que o Claude espera (sem timestamps)."""
    history = load_history(user_id)
    return [{"role": m["role"], "content": m["content"]} for m in history]
