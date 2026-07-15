"""
Serviço de configuração centralizado — lê/escreve config.yaml.
Partilhado por desktop_server.py e todos os agentes.
"""
import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.yaml"

_DEFAULTS = {
    "pausado": False,
    "silencio_inicio": 23,
    "silencio_fim": 7,
    "modelo": "claude-sonnet-4-6",
    "modelo_pesado": "claude-opus-4-8",
    "max_tokens": 512,
    "context_window": 50,
    "briefing_horas": [7, 20],
    "report_hora": 22,
    "scout_weekday": 6,
    "trading": {
        "capital_base": 100.0,
        "drawdown_dia_limite": 0.05,
        "drawdown_total_limite": 0.15,
        "win_rate_minimo": 0.40,
    },
    "confianca_limiar": 90,
    "confirmacao_obrigatoria": ["enviar mensagem", "apagar ficheiro", "gastar dinheiro"],
}


def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Merge com defaults para campos em falta
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except Exception:
        return dict(_DEFAULTS)


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get(key: str, default=None):
    return load_config().get(key, default)


def set_value(key: str, value):
    config = load_config()
    config[key] = value
    save_config(config)


# ── Atalhos mais usados ───────────────────────────────────────────────────────

def is_pausado() -> bool:
    return load_config().get("pausado", False)

def pausar():
    set_value("pausado", True)

def retomar():
    set_value("pausado", False)

def hora_silencio(hora: int) -> bool:
    c = load_config()
    inicio = c.get("silencio_inicio", 23)
    fim = c.get("silencio_fim", 7)
    if inicio > fim:
        return hora >= inicio or hora < fim
    return inicio <= hora < fim

def modelo() -> str:
    return load_config().get("modelo", "claude-sonnet-4-6")

def confianca_limiar() -> int:
    return int(load_config().get("confianca_limiar", 90))
