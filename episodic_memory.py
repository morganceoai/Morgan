"""
Camada episódica do Morgan — registo de eventos com timestamp e delta reporting.

Resolve o problema de repetição nos briefings: cada tema (futebol, trading, scout, etc.)
tem um hash do último conteúdo reportado. Se o hash não mudou, não há novidade.

Estrutura de memory/episodic_memory.json:
{
  "eventos": [
    {
      "ts": "2026-07-18T07:00:00",
      "agente": "coach",
      "tema": "moreirense_tabela",
      "conteudo": "...",
      "hash": "abc123"
    }
  ],
  "ultimo_hash": {
    "coach:moreirense_tabela": "abc123",
    "cfo:trading_status": "def456"
  }
}
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = Path(__file__).parent / "memory"
EPISODIC_FILE = MEMORY_DIR / "episodic_memory.json"
MAX_EVENTOS = 500  # manter os últimos N eventos


def _load() -> dict:
    try:
        return json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"eventos": [], "ultimo_hash": {}}


def _save(data: dict):
    MEMORY_DIR.mkdir(exist_ok=True)
    EPISODIC_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash(conteudo: str) -> str:
    return hashlib.sha256(conteudo.strip().encode()).hexdigest()[:16]


def registar_evento(agente: str, tema: str, conteudo: str) -> bool:
    """
    Regista um evento episódico. Devolve True se é novidade (hash mudou), False se repetição.
    Usar antes de reportar ao Vasco — se False, não vale a pena incluir no briefing.
    """
    if not conteudo or not conteudo.strip():
        return False

    chave = f"{agente}:{tema}"
    h = _hash(conteudo)
    data = _load()

    ultimo = data["ultimo_hash"].get(chave)
    if ultimo == h:
        return False  # sem novidade

    # Há novidade — registar
    evento = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agente": agente,
        "tema": tema,
        "conteudo": conteudo[:500],  # truncar para não engordar o ficheiro
        "hash": h,
    }
    data["eventos"].append(evento)
    data["eventos"] = data["eventos"][-MAX_EVENTOS:]
    data["ultimo_hash"][chave] = h
    _save(data)
    return True


def tem_novidade(agente: str, tema: str, conteudo: str) -> bool:
    """Verifica se há novidade sem registar. Útil para decisões de routing."""
    if not conteudo or not conteudo.strip():
        return False
    chave = f"{agente}:{tema}"
    h = _hash(conteudo)
    data = _load()
    return data["ultimo_hash"].get(chave) != h


def get_ultimo_evento(agente: str, tema: str) -> dict | None:
    """Devolve o último evento registado para este agente/tema."""
    chave = f"{agente}:{tema}"
    data = _load()
    # Percorrer de trás para a frente
    for ev in reversed(data["eventos"]):
        if f"{ev['agente']}:{ev['tema']}" == chave:
            return ev
    return None


def get_eventos_recentes(agente: str | None = None, tema: str | None = None, limite: int = 20) -> list[dict]:
    """Lista eventos recentes, filtrando opcionalmente por agente e/ou tema."""
    data = _load()
    eventos = reversed(data["eventos"])
    resultado = []
    for ev in eventos:
        if agente and ev.get("agente") != agente:
            continue
        if tema and ev.get("tema") != tema:
            continue
        resultado.append(ev)
        if len(resultado) >= limite:
            break
    return resultado


def get_resumo_delta(temas: list[tuple[str, str, str]]) -> str:
    """
    Dado uma lista de (agente, tema, conteudo), filtra apenas as novidades.
    Devolve string de resumo para incluir no briefing CEO.

    temas: list of (agente, tema, conteudo)
    """
    novidades = []
    for agente, tema, conteudo in temas:
        if registar_evento(agente, tema, conteudo):
            novidades.append(conteudo)

    if not novidades:
        return ""
    return "\n".join(novidades)
