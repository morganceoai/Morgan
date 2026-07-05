import os
import json
import hashlib
from datetime import date
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import anthropic

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
COLLECTION = "scout_oportunidades"
VECTOR_SIZE = 1536  # text-embedding-3-small

_client = None
_anthropic = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        # Cria a coleção se não existir
        existing = [c.name for c in _client.get_collections().collections]
        if COLLECTION not in existing:
            _client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _client


def get_embedding(text: str) -> list[float]:
    """Gera embedding usando a API da Anthropic via OpenAI-compatible endpoint."""
    global _anthropic
    # Usa OpenAI embeddings (mais barato e simples para este caso)
    try:
        from openai import OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            # Fallback: embedding simples baseado em hash (sem API externa)
            return _hash_embedding(text)
        client = OpenAI(api_key=openai_key)
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    except Exception:
        return _hash_embedding(text)


def _hash_embedding(text: str) -> list[float]:
    """Embedding determinístico baseado em hash — fallback sem API externa."""
    import struct
    h = hashlib.sha256(text.encode()).digest()
    # Repete o hash até ter 1536 floats
    raw = (h * (1536 // 32 + 1))[:1536 * 4]
    floats = list(struct.unpack(f"{1536}f", raw[:1536 * 4]))
    # Normaliza
    norm = sum(f * f for f in floats) ** 0.5 or 1.0
    return [f / norm for f in floats]


def guardar_oportunidade(oportunidade: dict):
    """Guarda uma oportunidade no Qdrant com embedding semântico."""
    try:
        client = get_client()
        texto = f"{oportunidade.get('nome', '')} — {oportunidade.get('descricao', '')} — {oportunidade.get('notas', '')}"
        vector = get_embedding(texto)
        uid = hashlib.md5(oportunidade.get("nome", "").encode()).hexdigest()
        uid_int = int(uid[:8], 16)  # Qdrant usa IDs numéricos

        client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=uid_int,
                vector=vector,
                payload={
                    "nome": oportunidade.get("nome", ""),
                    "descricao": oportunidade.get("descricao", ""),
                    "receita_estimada": oportunidade.get("receita_estimada", ""),
                    "notas": oportunidade.get("notas", ""),
                    "data": date.today().isoformat(),
                }
            )]
        )
    except Exception as e:
        print(f"Qdrant guardar_oportunidade erro: {e}")


def pesquisar_similares(query: str, limite: int = 5) -> list[dict]:
    """Pesquisa oportunidades semelhantes à query por significado."""
    try:
        client = get_client()
        vector = get_embedding(query)
        results = client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=limite,
            score_threshold=0.5,
        )
        return [r.payload for r in results]
    except Exception as e:
        print(f"Qdrant pesquisar_similares erro: {e}")
        return []


def get_contexto_semantico(query: str) -> str:
    """Devolve contexto semântico para o Scout usar no relatório."""
    similares = pesquisar_similares(query)
    if not similares:
        return ""
    linhas = ["## Oportunidades semanticamente relacionadas (Qdrant):"]
    for op in similares:
        linhas.append(f"- **{op.get('nome')}** ({op.get('data', '')}) — {op.get('descricao', '')[:100]}")
    return "\n".join(linhas)
