"""
Serviço centralizado de memória de longo prazo via Mem0.
Suporta dois modos:
  1. Cloud  — MEM0_API_KEY definido → MemoryClient (API paga)
  2. Local  — QDRANT_URL + QDRANT_API_KEY definidos → Memory local com Qdrant Cloud

Sem nenhuma variável definida: modo degradado (sem memória persistente, log de aviso).
"""
import os
import logging

_log = logging.getLogger("mem0_service")

# ── Clientes singleton ─────────────────────────────────────────────────────────
_cloud_client = None   # MemoryClient (cloud)
_local_client = None   # Memory (local + Qdrant)
_mode: str = "none"    # "cloud" | "local" | "none"


def _init():
    global _cloud_client, _local_client, _mode
    if _mode != "none":
        return  # já inicializado

    mem0_key = os.getenv("MEM0_API_KEY", "")
    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_key = os.getenv("QDRANT_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Modo 1: cloud MemoryClient
    if mem0_key:
        try:
            from mem0 import MemoryClient
            _cloud_client = MemoryClient(api_key=mem0_key)
            _mode = "cloud"
            _log.info("[Mem0] modo cloud ativo")
            return
        except Exception as e:
            _log.warning(f"[Mem0] falha cloud: {e}")

    # Modo 2: local Memory + Qdrant Cloud + Anthropic embeddings
    if qdrant_url and qdrant_key and anthropic_key:
        try:
            from mem0 import Memory
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "url": qdrant_url,
                        "api_key": qdrant_key,
                        "collection_name": "morgan_memory",
                        "embedding_model_dims": 1536,
                    },
                },
                "embedder": {
                    "provider": "openai",  # mem0 usa openai-compatible; funciona com Anthropic se OPENAI_API_KEY mockado
                    "config": {"model": "text-embedding-3-small"},
                },
                "llm": {
                    "provider": "anthropic",
                    "config": {
                        "model": "claude-haiku-4-5-20251001",
                        "api_key": anthropic_key,
                    },
                },
            }
            _local_client = Memory.from_config(config)
            _mode = "local"
            _log.info("[Mem0] modo local (Qdrant Cloud) ativo")
            return
        except Exception as e:
            _log.warning(f"[Mem0] falha local/Qdrant: {e}")

    _log.warning("[Mem0] sem MEM0_API_KEY nem QDRANT_URL — memória desativada")
    _mode = "degraded"


# ── API pública ────────────────────────────────────────────────────────────────

def mem0_get(user_id: str, query: str, limit: int = 10) -> str:
    _init()
    try:
        if _mode == "cloud" and _cloud_client:
            results = _cloud_client.search(query=query, filters={"user_id": user_id}, limit=limit)
        elif _mode == "local" and _local_client:
            results = _local_client.search(query=query, user_id=user_id, limit=limit)
        else:
            return ""
        memorias = []
        for r in (results or []):
            m = r.get("memory", "") if isinstance(r, dict) else str(r)
            if m:
                memorias.append(m)
        return "\n".join(f"- {m}" for m in memorias)
    except Exception as e:
        _log.error(f"[Mem0] get erro: {e}")
        return ""


def mem0_add(user_id: str, messages: list):
    _init()
    try:
        if _mode == "cloud" and _cloud_client:
            _cloud_client.add(messages, user_id=user_id)
        elif _mode == "local" and _local_client:
            _local_client.add(messages, user_id=user_id)
    except Exception as e:
        _log.error(f"[Mem0] add erro: {e}")


def mem0_get_all(user_id: str, limit: int = 50) -> str:
    _init()
    try:
        if _mode == "cloud" and _cloud_client:
            results = _cloud_client.get_all(filters={"user_id": user_id}, limit=limit)
        elif _mode == "local" and _local_client:
            results = _local_client.get_all(user_id=user_id, limit=limit)
        else:
            return ""
        memorias = []
        for r in (results or []):
            m = r.get("memory", "") if isinstance(r, dict) else str(r)
            if m:
                memorias.append(m)
        return "\n".join(f"- {m}" for m in memorias)
    except Exception as e:
        _log.error(f"[Mem0] get_all erro: {e}")
        return ""


def mem0_collective_add(agent: str, content: str):
    mem0_add("collective", [{"role": "assistant", "content": f"[{agent}] {content}"}])


def mem0_collective_get(query: str, limit: int = 5) -> str:
    return mem0_get("collective", query, limit)


def mem0_mode() -> str:
    """Devolve o modo atual: 'cloud', 'local', 'degraded' ou 'none'."""
    _init()
    return _mode
