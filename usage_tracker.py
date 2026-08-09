"""
Usage Tracker — consumos em tempo real de todos os serviços externos BCVertex.

Fontes:
  Anthropic   → memory/claude_usage.json   (claude_guard escreve a cada chamada)
  Higgsfield  → API balance                (polling a cada 6h, cache em usage_cache.json)
  ElevenLabs  → API subscription           (polling a cada 6h)
  Perplexity  → memory/api_requests.json   (tools.py incrementa a cada request)
  Exa         → memory/api_requests.json   (idem)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

_log = logging.getLogger(__name__)
MEMORY_DIR = Path(__file__).parent / "memory"
CACHE_FILE  = MEMORY_DIR / "usage_cache.json"
REQS_FILE   = MEMORY_DIR / "api_requests.json"
CLAUDE_FILE = MEMORY_DIR / "claude_usage.json"
CACHE_TTL_SEC = 6 * 3600  # refrescar Higgsfield/ElevenLabs a cada 6h


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hoje() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _mes() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")

def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return {}

def _save_json(path: Path, data: dict):
    try:
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        pass


# ── Contagem de requests (Perplexity, Exa, etc.) ─────────────────────────────

def registar_request(servico: str):
    """Chamado por tools.py sempre que um serviço externo é invocado."""
    hoje = _hoje()
    mes = _mes()
    data = _load_json(REQS_FILE)
    for chave in [hoje, mes]:
        data.setdefault(chave, {})
        data[chave][servico] = data[chave].get(servico, 0) + 1
    # manter só últimos 60 dias + 12 meses
    dias = sorted(k for k in data if len(k) == 10)
    for d in dias[:-60]:
        del data[d]
    _save_json(REQS_FILE, data)


# ── Polling Higgsfield ────────────────────────────────────────────────────────

def _poll_higgsfield(cache: dict) -> dict:
    """Consulta a API Higgsfield via MCP ou requests directo."""
    ultimo = cache.get("higgsfield_ts", 0)
    agora = datetime.now(timezone.utc).timestamp()
    if agora - ultimo < CACHE_TTL_SEC:
        return cache.get("higgsfield", {})

    try:
        # Higgsfield não tem API pública REST directa — lemos do accounts.json
        # que é actualizado pelo polling do desktop_server (via MCP)
        accounts = _load_json(MEMORY_DIR / "accounts.json")
        hf = next((c for c in accounts.get("contas", []) if c["nome"] == "Higgsfield"), {})
        result = {
            "plano": hf.get("plano", "Ultra"),
            "creditos_restantes": hf.get("creditos_actuais"),
            "creditos_ciclo": hf.get("creditos_por_ciclo", 3000),
            "proxima_renovacao": hf.get("proxima_renovacao"),
            "verificado_em": hf.get("verificado_em"),
        }
        cache["higgsfield"] = result
        cache["higgsfield_ts"] = agora
    except Exception as e:
        _log.warning("Higgsfield poll erro: %s", e)
    return cache.get("higgsfield", {})


def _poll_elevenlabs(cache: dict) -> dict:
    """Consulta API ElevenLabs para estado da subscrição."""
    ultimo = cache.get("elevenlabs_ts", 0)
    agora = datetime.now(timezone.utc).timestamp()
    if agora - ultimo < CACHE_TTL_SEC:
        return cache.get("elevenlabs", {})

    try:
        key = os.getenv("ELEVENLABS_API_KEY")
        if not key:
            return {}
        r = requests.get(
            "https://api.elevenlabs.io/v1/user/subscription",
            headers={"xi-api-key": key},
            timeout=8,
        )
        r.raise_for_status()
        d = r.json()
        import datetime as _dt
        proxima = _dt.datetime.fromtimestamp(
            d.get("next_character_count_reset_unix", 0), tz=timezone.utc
        ).strftime("%Y-%m-%d")
        result = {
            "plano": d.get("tier", "creator").title(),
            "chars_usados": d.get("character_count", 0),
            "chars_limite": d.get("character_limit", 0),
            "chars_pct": round(d.get("character_count", 0) / max(d.get("character_limit", 1), 1) * 100, 1),
            "proxima_renovacao": proxima,
            "proxima_fatura_usd": round(d.get("next_invoice", {}).get("amount_due_cents", 0) / 100, 2),
            "estado": d.get("status", "active"),
        }
        cache["elevenlabs"] = result
        cache["elevenlabs_ts"] = agora
    except Exception as e:
        _log.warning("ElevenLabs poll erro: %s", e)
    return cache.get("elevenlabs", {})


# ── Dados Anthropic ───────────────────────────────────────────────────────────

def _dados_anthropic() -> dict:
    data = _load_json(CLAUDE_FILE)
    hoje = _hoje()
    mes = _mes()
    dias = data.get("dias", {})

    dia_actual = dias.get(hoje, {})
    total_mes_usd = sum(
        d.get("total_usd", 0) for k, d in dias.items() if k.startswith(mes)
    )
    total_mes_tok = sum(
        d.get("total_tokens", 0) for k, d in dias.items() if k.startswith(mes)
    )

    return {
        "hoje": {
            "tokens": dia_actual.get("total_tokens", 0),
            "custo_usd": round(dia_actual.get("total_usd", 0), 4),
            "chamadas": sum(
                a.get("chamadas", 0) for a in dia_actual.get("agentes", {}).values()
            ),
        },
        "mes": {
            "tokens": total_mes_tok,
            "custo_usd": round(total_mes_usd, 4),
        },
        "agentes_hoje": {
            ag: {
                "tokens": info.get("tokens", 0),
                "usd": round(info.get("usd", 0), 4),
                "chamadas": info.get("chamadas", 0),
            }
            for ag, info in dia_actual.get("agentes", {}).items()
        },
        "budget_total_dia_usd": 5.0,
    }


# ── Ponto de entrada principal ────────────────────────────────────────────────

def get_all_usage() -> dict:
    """Retorna consumos consolidados de todos os serviços. Usado pelo /api/usage."""
    cache = _load_json(CACHE_FILE)
    reqs = _load_json(REQS_FILE)
    hoje = _hoje()
    mes = _mes()

    hf = _poll_higgsfield(cache)
    el = _poll_elevenlabs(cache)
    _save_json(CACHE_FILE, cache)

    return {
        "anthropic": _dados_anthropic(),
        "higgsfield": hf,
        "elevenlabs": el,
        "perplexity": {
            "requests_hoje": reqs.get(hoje, {}).get("perplexity", 0),
            "requests_mes": reqs.get(mes, {}).get("perplexity", 0),
        },
        "exa": {
            "requests_hoje": reqs.get(hoje, {}).get("exa", 0),
            "requests_mes": reqs.get(mes, {}).get("exa", 0),
        },
        "atualizado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(get_all_usage())
