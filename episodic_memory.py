"""
Morgan Episodic Memory — registo de eventos com deduplicação (hash) + armazenamento
semântico em Qdrant. Permite recuperação cronológica e semântica de contexto entre sessões.

Camada 1 (JSON local): deduplicação por hash para briefings eficientes.
Camada 2 (Qdrant + OpenAI embeddings): pesquisa semântica cross-sessão.

Interface pública (retrocompatível):
  registar_evento(agente, tema, conteudo)  → bool (True se novidade)
  get_eventos_recentes(agente, tema, limite)
  pesquisar_memoria(query, agente, top_k)   ← novo
  get_contexto_agente(agente, query, limite) ← novo
"""
import os
import uuid
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent / "memory"
EPISODIC_FILE = MEMORY_DIR / "episodic_memory.json"
MAX_EVENTOS = 1000
QDRANT_COLLECTION = "episodic_memory"

# Clientes lazy
_qdrant_client = None
_openai_client = None


def _qdrant():
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client
    try:
        from qdrant_client import QdrantClient
        url = os.getenv("QDRANT_URL", "")
        key = os.getenv("QDRANT_API_KEY", "")
        if not url:
            return None
        c = QdrantClient(url=url, api_key=key or None, timeout=10)
        # Criar colecção se não existir
        from qdrant_client.models import VectorParams, Distance
        cols = [col.name for col in c.get_collections().collections]
        if QDRANT_COLLECTION not in cols:
            c.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
        _qdrant_client = c
        return _qdrant_client
    except Exception as e:
        logger.debug("Qdrant episodic indisponível: %s", e)
        return None


def _openai():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    try:
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            return None
        _openai_client = OpenAI(api_key=key)
        return _openai_client
    except Exception:
        return None


def _embed(texto: str) -> list[float] | None:
    oa = _openai()
    if not oa:
        return None
    try:
        resp = oa.embeddings.create(model="text-embedding-3-small", input=texto[:2000])
        return resp.data[0].embedding
    except Exception as e:
        logger.debug("Embedding falhou: %s", e)
        return None


def _qdrant_upsert(evento: dict):
    """Guarda evento no Qdrant com embedding. Falha silenciosamente."""
    try:
        c = _qdrant()
        if not c:
            return
        texto = f"{evento['agente']} {evento['tema']}: {evento['conteudo']}"
        vec = _embed(texto)
        if not vec:
            return
        from qdrant_client.models import PointStruct
        c.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[PointStruct(id=str(uuid.uuid4()), vector=vec, payload=evento)],
        )
    except Exception as e:
        logger.debug("Qdrant upsert episódico falhou: %s", e)


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
    Regista um evento episódico.
    Devolve True se é novidade (hash mudou), False se repetição.
    Guarda em JSON local (sempre) + Qdrant com embedding (assíncrono, best-effort).
    """
    if not conteudo or not conteudo.strip():
        return False

    chave = f"{agente}:{tema}"
    h = _hash(conteudo)
    data = _load()

    ultimo = data["ultimo_hash"].get(chave)
    is_novidade = ultimo != h

    evento = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agente": agente,
        "tema": tema,
        "conteudo": conteudo[:500],
        "hash": h,
    }

    # Sempre guardar no JSON (deduplicação para briefings)
    if is_novidade:
        data["eventos"].append(evento)
        data["eventos"] = data["eventos"][-MAX_EVENTOS:]
        data["ultimo_hash"][chave] = h
        _save(data)

    # Guardar no Qdrant em background (não bloqueia — falha silenciosamente)
    try:
        import threading
        threading.Thread(target=_qdrant_upsert, args=(evento,), daemon=True).start()
    except Exception:
        pass

    return is_novidade


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


def pesquisar_memoria(query: str, agente: str | None = None, top_k: int = 5) -> list[dict]:
    """
    Pesquisa semântica no histórico episódico via Qdrant.
    Fallback: keyword match simples no JSON local.
    """
    c = _qdrant()
    if c:
        try:
            vec = _embed(query)
            if vec:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_filter = None
                if agente:
                    search_filter = Filter(
                        must=[FieldCondition(key="agente", match=MatchValue(value=agente))]
                    )
                resultados = c.search(
                    collection_name=QDRANT_COLLECTION,
                    query_vector=vec,
                    query_filter=search_filter,
                    limit=top_k,
                    score_threshold=0.65,
                    with_payload=True,
                )
                return [r.payload for r in resultados if r.payload]
        except Exception as e:
            logger.debug("Pesquisa semântica falhou: %s", e)

    # Fallback: keyword match no JSON
    data = _load()
    eventos = data.get("eventos", [])
    if agente:
        eventos = [e for e in eventos if e.get("agente") == agente]
    termos = set(query.lower().split())
    scored = [(sum(1 for t in termos if t in e.get("conteudo", "").lower()), e) for e in eventos]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for s, e in scored[:top_k] if s > 0]


def get_contexto_agente(agente: str, query: str = "", limite: int = 5) -> str:
    """
    Combina memória recente (JSON) + semântica (Qdrant) num bloco de texto
    pronto a injectar no system prompt de qualquer agente.
    """
    recentes = get_eventos_recentes(agente=agente, limite=limite)
    semanticos = pesquisar_memoria(query, agente=agente, top_k=3) if query else []

    vistos: set[str] = set()
    linhas: list[str] = []

    for ev in semanticos:
        chave = ev.get("ts", "")[:19] + ev.get("conteudo", "")[:30]
        if chave not in vistos:
            vistos.add(chave)
            ts = ev.get("ts", "")[:10]
            linhas.append(f"[{ts}|relevante] {ev.get('conteudo', '')[:150]}")

    for ev in reversed(recentes):
        chave = ev.get("ts", "")[:19] + ev.get("conteudo", "")[:30]
        if chave not in vistos:
            vistos.add(chave)
            ts = ev.get("ts", "")[:10]
            linhas.append(f"[{ts}] {ev.get('conteudo', '')[:150]}")

    return "\n".join(linhas) if linhas else ""


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
