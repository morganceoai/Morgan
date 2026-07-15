"""
Serviço centralizado de memória de longo prazo via Mem0.
Usado por desktop_server.py e todos os agentes.

Mem0 extrai automaticamente factos importantes de cada conversa
e devolve os mais relevantes por query semântica — memória infinita
em formato compacto.
"""
import os

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from mem0 import MemoryClient
            key = os.getenv("MEM0_API_KEY", "")
            if key:
                _client = MemoryClient(api_key=key)
        except Exception as e:
            print(f"[Mem0] erro ao inicializar: {e}")
    return _client


def mem0_get(user_id: str, query: str, limit: int = 10) -> str:
    """Recupera memórias relevantes para a query. Devolve string formatada ou ''."""
    try:
        client = _get_client()
        if not client or not query:
            return ""
        results = client.search(query=query, filters={"user_id": user_id}, limit=limit)
        memorias = []
        for r in results:
            m = r.get("memory", "") if isinstance(r, dict) else str(r)
            if m:
                memorias.append(m)
        return "\n".join(f"- {m}" for m in memorias)
    except Exception as e:
        print(f"[Mem0] get erro: {e}")
        return ""


def mem0_add(user_id: str, messages: list):
    """Guarda uma lista de mensagens [{role, content}] no Mem0.
    Mem0 extrai automaticamente os factos relevantes."""
    try:
        client = _get_client()
        if client and messages:
            client.add(messages, user_id=user_id)
    except Exception as e:
        print(f"[Mem0] add erro: {e}")


def mem0_get_all(user_id: str, limit: int = 50) -> str:
    """Lista todas as memórias guardadas para um user_id (sem query semântica)."""
    try:
        client = _get_client()
        if not client:
            return ""
        results = client.get_all(filters={"user_id": user_id}, limit=limit)
        memorias = []
        for r in results:
            m = r.get("memory", "") if isinstance(r, dict) else str(r)
            if m:
                memorias.append(m)
        return "\n".join(f"- {m}" for m in memorias)
    except Exception as e:
        print(f"[Mem0] get_all erro: {e}")
        return ""


def mem0_collective_add(agent: str, content: str):
    """Guarda facto/insight na memória colectiva partilhada por todos os agentes."""
    try:
        client = _get_client()
        if client:
            client.add(
                [{"role": "assistant", "content": f"[{agent}] {content}"}],
                user_id="collective"
            )
    except Exception as e:
        print(f"[Mem0] collective_add erro: {e}")


def mem0_collective_get(query: str, limit: int = 5) -> str:
    """Recupera memórias colectivas relevantes para qualquer agente."""
    try:
        client = _get_client()
        if not client or not query:
            return ""
        results = client.search(query=query, filters={"user_id": "collective"}, limit=limit)
        memorias = []
        for r in results:
            m = r.get("memory", "") if isinstance(r, dict) else str(r)
            if m:
                memorias.append(m)
        return "\n".join(f"- {m}" for m in memorias)
    except Exception as e:
        print(f"[Mem0] collective_get erro: {e}")
        return ""
