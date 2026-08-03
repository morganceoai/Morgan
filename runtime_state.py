"""
Runtime State — estado partilhado entre agentes em tempo real.
Cada agente publica o seu estado aqui. Qualquer agente pode ler qualquer outro.
Substitui a necessidade de passar pelo CEO para saber "o que está o PAtlas a fazer".
"""
import json
import threading
from datetime import datetime
from pathlib import Path

_STATE_FILE = Path(__file__).parent / "memory" / "runtime_state.json"
_lock = threading.Lock()


def _load() -> dict:
    with _lock:
        if _STATE_FILE.exists():
            try:
                return json.loads(_STATE_FILE.read_text())
            except Exception:
                pass
        return {}


def _save(state: dict):
    with _lock:
        _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def publicar(agente: str, dados: dict):
    """
    Agente publica o seu estado actual.
    dados: dict com campos livres — cada agente define os seus.
    Campos reservados (gerados automaticamente): ts, agente
    """
    state = _load()
    state[agente] = {
        "agente": agente,
        "ts": datetime.now().isoformat(),
        **dados,
    }
    _save(state)


def ler(agente: str) -> dict:
    """Lê o estado actual de um agente específico. Retorna {} se não existe."""
    return _load().get(agente, {})


def ler_todos() -> dict:
    """Retorna o estado de todos os agentes."""
    return _load()


def resumo_sistema() -> str:
    """Resumo compacto do estado de todos os agentes — para briefings e system prompt."""
    state = _load()
    if not state:
        return "(sem estado publicado)"

    linhas = []
    for agente, dados in sorted(state.items()):
        ts = dados.get("ts", "")[:16].replace("T", " ")
        status = dados.get("status", "—")
        extra = dados.get("resumo", "")
        linha = f"• {agente.upper()} [{ts}]: {status}"
        if extra:
            linha += f" — {extra}"
        linhas.append(linha)

    return "\n".join(linhas)
