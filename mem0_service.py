"""
Serviço de memória de longo prazo via Qdrant Cloud.
Substitui Mem0 Cloud — sem quota, sem custo adicional.

Arquitectura:
  - Qdrant Cloud (QDRANT_URL + QDRANT_API_KEY): vector store
  - fastembed (local, gratuito): embeddings 384-dim
  - Haiku: extrai factos estruturados das conversas antes de guardar

API pública (compatível com código existente):
  mem0_add(user_id, messages)
  mem0_get(user_id, query, limit)
  mem0_get_all(user_id, limit)
  mem0_collective_add(agent, content)
  mem0_collective_get(query, limit)
  mem0_mode() → str
"""
import os
import json
import logging
import uuid
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

_log = logging.getLogger("mem0_service")

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_KEY = os.getenv("QDRANT_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

COLLECTION_NAME = "morgan_memory"
EMBEDDING_DIM = 384  # fastembed all-MiniLM-L6-v2

_qdrant = None
_embedder = None
_mode = "none"


def _init():
    global _qdrant, _embedder, _mode
    if _mode != "none":
        return

    if not QDRANT_URL or not QDRANT_KEY:
        _log.warning("[Mem] QDRANT_URL ou QDRANT_API_KEY em falta — memória desactivada")
        _mode = "degraded"
        return

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        _qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)

        from qdrant_client.models import PayloadSchemaType
        # Criar collection se não existir
        existing = [c.name for c in _qdrant.get_collections().collections]
        if COLLECTION_NAME not in existing:
            _qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
            _qdrant.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="user_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            _log.info(f"[Mem] collection '{COLLECTION_NAME}' criada")
        else:
            # Garantir índice mesmo em collections existentes
            try:
                _qdrant.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="user_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass

    except Exception as e:
        _log.error(f"[Mem] erro ao conectar Qdrant: {e}")
        _mode = "degraded"
        return

    try:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        _log.error(f"[Mem] erro ao carregar fastembed: {e}")
        _mode = "degraded"
        return

    _mode = "qdrant"
    _log.info("[Mem] modo Qdrant Cloud activo")


def _embed(text: str) -> list[float]:
    embeddings = list(_embedder.embed([text]))
    return embeddings[0].tolist()


def _extrair_factos(messages: list) -> list[str]:
    """Usa Haiku para extrair factos memoráveis de uma troca de mensagens."""
    if not ANTHROPIC_KEY:
        return [m.get("content", "") for m in messages if m.get("role") == "user"]

    conversa = "\n".join(
        f"{m.get('role','?').upper()}: {m.get('content','')}"
        for m in messages
        if isinstance(m.get("content"), str)
    )
    if not conversa.strip():
        return []

    try:
        import anthropic
        c = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        r = c.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=(
                "Extrai factos memoráveis desta conversa. "
                "Só extrai o que tem valor a longo prazo: decisões, preferências, factos sobre o Vasco, "
                "objectivos, negócios, pessoas mencionadas. "
                "Ignora perguntas triviais e respostas sem informação nova. "
                "Responde com uma lista JSON de strings curtas (máx 20 palavras cada). "
                "Se não há nada memorável, responde com []."
            ),
            messages=[{"role": "user", "content": conversa}],
        )
        text = r.content[0].text.strip()
        # Extrair o JSON da resposta
        import re
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            factos = json.loads(m.group())
            return [f for f in factos if isinstance(f, str) and f.strip()]
        return []
    except Exception as e:
        _log.warning(f"[Mem] extracção de factos falhou: {e}")
        return []


def mem0_add(user_id: str, messages: list):
    _init()
    if _mode != "qdrant":
        return

    factos = _extrair_factos(messages)
    if not factos:
        return

    try:
        from qdrant_client.models import PointStruct
        pontos = []
        for facto in factos:
            vec = _embed(facto)
            pontos.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "memory": facto,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ))
        _qdrant.upsert(collection_name=COLLECTION_NAME, points=pontos)
    except Exception as e:
        _log.error(f"[Mem] add erro: {e}")


def mem0_get(user_id: str, query: str, limit: int = 10) -> str:
    _init()
    if _mode != "qdrant":
        return ""

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        vec = _embed(query)
        results = _qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vec,
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=limit,
            score_threshold=0.5,
            with_payload=True,
        )
        memorias = [r.payload.get("memory", "") for r in results.points if r.payload]
        return "\n".join(f"- {m}" for m in memorias if m)
    except Exception as e:
        _log.error(f"[Mem] get erro: {e}")
        return ""


def mem0_get_all(user_id: str, limit: int = 50) -> str:
    _init()
    if _mode != "qdrant":
        return ""

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        results, _ = _qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=limit,
            with_payload=True,
        )
        memorias = [r.payload.get("memory", "") for r in results if r.payload]
        return "\n".join(f"- {m}" for m in memorias if m)
    except Exception as e:
        _log.error(f"[Mem] get_all erro: {e}")
        return ""


def mem0_collective_add(agent: str, content: str):
    mem0_add("collective", [{"role": "assistant", "content": f"[{agent}] {content}"}])


def mem0_collective_get(query: str, limit: int = 5) -> str:
    return mem0_get("collective", query, limit)


def mem0_mode() -> str:
    _init()
    return _mode


def get_agent_context(agente: str, query: str) -> str:
    """Contexto relevante para um agente antes de responder.
    Combina memória do utilizador + memória colectiva filtrada por relevância.
    Retorna string vazia se memória indisponível — nunca bloqueia o agente.
    """
    try:
        mem_vasco  = mem0_get("vasco", query, limit=6)
        mem_col    = mem0_collective_get(query, limit=4)
        partes = []
        if mem_vasco:
            partes.append(f"[Memória Vasco]\n{mem_vasco}")
        if mem_col:
            partes.append(f"[Memória sistema]\n{mem_col}")
        return "\n\n".join(partes)
    except Exception:
        return ""
