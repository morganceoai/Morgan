"""
Zep — memória temporal com timeline.
Regista eventos com timestamps reais. Permite perguntas como "o que aconteceu há 3 semanas?".
Complementa o Qdrant (semântico) com a dimensão temporal.

Usa Zep Cloud (free tier, até 2500 sessões).
Conta: criar em getzep.com com morganceoai@gmail.com.
ZEP_API_KEY deve estar no .env.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

ZEP_API_KEY = os.getenv("ZEP_API_KEY", "")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not ZEP_API_KEY:
        return None
    try:
        from zep_cloud.client import Zep
        _client = Zep(api_key=ZEP_API_KEY)
        return _client
    except Exception as e:
        logger.warning(f"Zep não disponível: {e}")
        return None


def _session_id(agente: str) -> str:
    return f"morgan_{agente}"


def _user_id(agente: str) -> str:
    return f"agente_{agente}"


def _garantir_user_e_session(client, agente: str):
    uid = _user_id(agente)
    sid = _session_id(agente)
    try:
        client.user.get(uid)
    except Exception:
        try:
            client.user.add(user_id=uid, metadata={"agente": agente, "sistema": "morgan"})
        except Exception:
            pass
    try:
        client.memory.get_session(sid)
    except Exception:
        try:
            client.memory.add_session(session_id=sid, user_id=uid)
        except Exception:
            pass


def registar_evento(agente: str, tipo: str, conteudo: str, metadata: Optional[dict] = None) -> bool:
    """
    Regista um evento no Zep com timestamp real.

    agente: "ceo", "scout", "cfo", etc.
    tipo: "briefing", "trade", "oportunidade", "decisao", "conversa", etc.
    conteudo: texto do evento
    """
    client = _get_client()
    if not client:
        return False
    try:
        from zep_cloud.types import Message
        _garantir_user_e_session(client, agente)
        sid = _session_id(agente)
        meta = {"tipo": tipo, "agente": agente, "timestamp_pt": datetime.now(timezone.utc).isoformat()}
        if metadata:
            meta.update(metadata)
        client.memory.add(
            session_id=sid,
            messages=[Message(
                role="assistant",
                role_type="assistant",
                content=f"[{tipo.upper()}] {conteudo}",
                metadata=meta,
            )]
        )
        return True
    except Exception as e:
        logger.warning(f"Zep registar_evento erro: {e}")
        return False


def recuperar_historico(agente: str, query: str, limite: int = 5) -> str:
    """
    Recupera eventos relevantes do historial temporal de um agente.
    Usa pesquisa semântica sobre a timeline Zep.
    """
    client = _get_client()
    if not client:
        return ""
    try:
        sid = _session_id(agente)
        result = client.memory.search_sessions(
            text=query,
            user_id=_user_id(agente),
            limit=limite,
        )
        if not result or not result.results:
            return ""
        linhas = []
        for r in result.results:
            if r.message and r.message.content:
                ts = ""
                if r.message.metadata and "timestamp_pt" in r.message.metadata:
                    try:
                        dt = datetime.fromisoformat(r.message.metadata["timestamp_pt"])
                        ts = dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        pass
                linhas.append(f"[{ts}] {r.message.content}")
        return "\n".join(linhas) if linhas else ""
    except Exception as e:
        logger.warning(f"Zep recuperar_historico erro: {e}")
        return ""


def recuperar_memoria_recente(agente: str, n_mensagens: int = 10) -> str:
    """Recupera as últimas n mensagens da sessão de um agente."""
    client = _get_client()
    if not client:
        return ""
    try:
        _garantir_user_e_session(client, agente)
        sid = _session_id(agente)
        mem = client.memory.get(session_id=sid, lastn=n_mensagens)
        if not mem or not mem.messages:
            return ""
        linhas = []
        for m in mem.messages:
            ts = ""
            if m.metadata and "timestamp_pt" in m.metadata:
                try:
                    dt = datetime.fromisoformat(m.metadata["timestamp_pt"])
                    ts = dt.strftime("%d/%m %H:%M")
                except Exception:
                    pass
            linhas.append(f"[{ts}] {m.content}")
        return "\n".join(linhas)
    except Exception as e:
        logger.warning(f"Zep recuperar_memoria_recente erro: {e}")
        return ""


def get_contexto_temporal(agente: str, query: str) -> str:
    """
    Interface principal: contexto temporal relevante para um agente.
    Combina pesquisa semântica + recentes.
    Retorna string pronta a injectar no system prompt.
    """
    client = _get_client()
    if not client:
        return ""
    historico = recuperar_historico(agente, query, limite=3)
    recentes = recuperar_memoria_recente(agente, n_mensagens=5)
    partes = []
    if historico:
        partes.append(f"[Histórico relevante]\n{historico}")
    if recentes:
        partes.append(f"[Últimos eventos]\n{recentes}")
    return "\n\n".join(partes) if partes else ""


def zep_disponivel() -> bool:
    return _get_client() is not None
