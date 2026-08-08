"""
Morgan — Memória Episódica Central
Camada episódica das 4 camadas de memória do sistema.

Regista TODAS as acções relevantes de TODOS os agentes num único log append-only
(knowledge_base.jsonl) + busca semântica via Qdrant.

Interface pública:
  registar_evento(agente, tema, conteudo, dados=None) → bool
  get_eventos_recentes(agente=None, tema=None, limite=20) → list[dict]
  pesquisar_memoria(query, agente=None, top_k=10) → list[dict]
  get_contexto_agente(agente, query, limite=5) → str
  consultar_base(query, agente=None, limite=20) → str   ← para o CEO
"""
import os
import uuid
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent / "memory"
KB_FILE = MEMORY_DIR / "knowledge_base.jsonl"   # append-only — não corrompe
QDRANT_COLLECTION = "episodic_memory"

_qdrant_client = None
_openai_client = None


# ── Clientes lazy ─────────────────────────────────────────────────────────────

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
        from qdrant_client.models import VectorParams, Distance
        cols = [col.name for col in c.get_collections().collections]
        if QDRANT_COLLECTION not in cols:
            c.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
        _qdrant_client = c
        return c
    except Exception as e:
        logger.debug("Qdrant indisponível: %s", e)
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


# ── Escrita ───────────────────────────────────────────────────────────────────

def _append_kb(evento: dict):
    """Append ao knowledge_base.jsonl — nunca corrompe ficheiros existentes."""
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(KB_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


def _qdrant_upsert(evento: dict):
    try:
        c = _qdrant()
        if not c:
            return
        texto = f"[{evento['agente']}] {evento['tema']}: {evento['conteudo']}"
        vec = _embed(texto)
        if not vec:
            return
        from qdrant_client.models import PointStruct
        c.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[PointStruct(id=str(uuid.uuid4()), vector=vec, payload=evento)],
        )
    except Exception as e:
        logger.debug("Qdrant upsert falhou: %s", e)


def registar_evento(agente: str, tema: str, conteudo: str, dados: dict | None = None) -> bool:
    """
    Regista um evento episódico.
    Escreve em knowledge_base.jsonl (local, sempre funciona) + Qdrant (best-effort).
    Devolve True se registado com sucesso.
    """
    if not conteudo or not conteudo.strip():
        return False

    evento = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agente": agente,
        "tema": tema,
        "conteudo": conteudo[:600],
    }
    if dados:
        evento["dados"] = dados

    try:
        _append_kb(evento)
    except Exception as e:
        logger.error("Falha ao escrever knowledge_base.jsonl: %s", e)
        return False

    # Qdrant em background — não bloqueia
    try:
        import threading
        threading.Thread(target=_qdrant_upsert, args=(evento,), daemon=True).start()
    except Exception:
        pass

    return True


# ── Leitura local ─────────────────────────────────────────────────────────────

def _carregar_kb(limite: int = 1000) -> list[dict]:
    """Lê as últimas N linhas do knowledge_base.jsonl."""
    if not KB_FILE.exists():
        return []
    try:
        lines = KB_FILE.read_text(encoding="utf-8").strip().split("\n")
        eventos = []
        for l in lines:
            l = l.strip()
            if l:
                try:
                    eventos.append(json.loads(l))
                except Exception:
                    pass
        return eventos[-limite:]
    except Exception:
        return []


def get_eventos_recentes(agente: str | None = None, tema: str | None = None, limite: int = 20) -> list[dict]:
    """Devolve os eventos mais recentes, opcionalmente filtrados por agente ou tema."""
    todos = _carregar_kb(limite * 10)
    if agente:
        todos = [e for e in todos if e.get("agente") == agente]
    if tema:
        todos = [e for e in todos if e.get("tema") == tema]
    return todos[-limite:]


# ── Leitura semântica (Qdrant) ─────────────────────────────────────────────────

def pesquisar_memoria(query: str, agente: str | None = None, top_k: int = 10) -> list[dict]:
    """Busca semântica no Qdrant. Fallback para leitura local se Qdrant indisponível."""
    c = _qdrant()
    if not c:
        return get_eventos_recentes(agente=agente, limite=top_k)

    vec = _embed(query)
    if not vec:
        return get_eventos_recentes(agente=agente, limite=top_k)

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        filtro = None
        if agente:
            filtro = Filter(must=[FieldCondition(key="agente", match=MatchValue(value=agente))])

        results = c.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vec,
            limit=top_k,
            query_filter=filtro,
            with_payload=True,
        )
        return [r.payload for r in results]
    except Exception as e:
        logger.debug("Qdrant search falhou: %s", e)
        return get_eventos_recentes(agente=agente, limite=top_k)


def get_contexto_agente(agente: str, query: str = "", limite: int = 5) -> str:
    """Devolve contexto relevante para um agente, formatado para injectar no system prompt."""
    if query:
        eventos = pesquisar_memoria(query, agente=agente, top_k=limite)
    else:
        eventos = get_eventos_recentes(agente=agente, limite=limite)

    if not eventos:
        return ""

    linhas = []
    for e in eventos:
        ts = e.get("ts", "")[:10]
        tema = e.get("tema", "")
        conteudo = e.get("conteudo", "")[:200]
        linhas.append(f"[{ts}] {tema}: {conteudo}")

    return "Memória recente:\n" + "\n".join(linhas)


# ── Consulta CEO (linguagem natural) ─────────────────────────────────────────

def consultar_base(query: str, agente: str | None = None, limite: int = 20) -> str:
    """
    Ferramenta do CEO para consultar a base de conhecimento em linguagem natural.
    Usa Qdrant se disponível, senão filtra localmente.
    """
    eventos = pesquisar_memoria(query, agente=agente, top_k=limite)

    if not eventos:
        return "Sem eventos relevantes encontrados."

    linhas = [f"Base de conhecimento — '{query}':"]
    for e in eventos:
        ts = e.get("ts", "")[:16].replace("T", " ")
        ag = e.get("agente", "?")
        tema = e.get("tema", "?")
        conteudo = e.get("conteudo", "")[:250]
        linhas.append(f"\n[{ts}] [{ag}|{tema}]\n{conteudo}")

    return "\n".join(linhas)


# ── Migração de dados históricos ─────────────────────────────────────────────

def migrar_historico() -> dict:
    """
    Migra dados históricos de todos os ficheiros existentes para knowledge_base.jsonl.
    Idempotente — verifica se KB já tem dados antes de migrar.
    """
    existentes = _carregar_kb()
    if len(existentes) > 50:
        return {"status": "já migrado", "total": len(existentes)}

    migrados = 0

    # 1. Qdrant episodic_memory — já é a fonte mais rica
    try:
        c = _qdrant()
        if c:
            results = c.scroll(QDRANT_COLLECTION, limit=500, with_payload=True)
            pts = results[0]
            while results[1]:
                results = c.scroll(QDRANT_COLLECTION, limit=500, with_payload=True, offset=results[1])
                pts += results[0]
            for r in pts:
                p = r.payload
                if p.get("tema") == "claude_guard_alerta":
                    continue  # ruído
                _append_kb({
                    "ts": p.get("ts", datetime.now(timezone.utc).isoformat()),
                    "agente": p.get("agente", "sistema"),
                    "tema": p.get("tema", "evento"),
                    "conteudo": str(p.get("conteudo", ""))[:600],
                    "origem": "qdrant_migrado",
                })
                migrados += 1
    except Exception as e:
        logger.warning("Migração Qdrant falhou: %s", e)

    # 2. solver_fixes.json
    solver_file = MEMORY_DIR / "solver_fixes.json"
    if solver_file.exists():
        try:
            data = json.loads(solver_file.read_text())
            fixes = data.get("fixes", data) if isinstance(data, dict) else data
            for fix in fixes:
                _append_kb({
                    "ts": fix.get("data", datetime.now(timezone.utc).isoformat()),
                    "agente": "solver",
                    "tema": "fix_registado",
                    "conteudo": f"Problema: {fix.get('problema','')} | Fix: {fix.get('fix','')}",
                    "dados": {"diagnostico": fix.get("diagnostico",""), "confianca": fix.get("confianca",0)},
                    "origem": "solver_fixes_migrado",
                })
                migrados += 1
        except Exception as e:
            logger.warning("Migração solver_fixes falhou: %s", e)

    # 3. cfo_decision_log.jsonl — só as decisões não-triviais
    cfo_log = MEMORY_DIR / "cfo_decision_log.jsonl"
    if cfo_log.exists():
        try:
            lines = cfo_log.read_text().strip().split("\n")
            for l in lines[-10:]:  # só as 10 mais recentes — as antigas são repetição
                try:
                    entry = json.loads(l)
                    d = entry.get("decisao", {})
                    _append_kb({
                        "ts": entry.get("ts", datetime.now(timezone.utc).isoformat()),
                        "agente": "cfo",
                        "tema": "decisao_trading",
                        "conteudo": f"Acção: {d.get('acao','')} | Confiança: {d.get('confianca',0)}% | {d.get('razao','')[:200]}",
                        "origem": "cfo_log_migrado",
                    })
                    migrados += 1
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Migração CFO log falhou: %s", e)

    # 4. estado_imperio.md — contexto histórico do projecto
    estado = MEMORY_DIR / "estado_imperio.md"
    if estado.exists():
        try:
            conteudo = estado.read_text()[:800]
            _append_kb({
                "ts": "2026-07-07T00:00:00+00:00",
                "agente": "ceo",
                "tema": "estado_imperio",
                "conteudo": conteudo,
                "origem": "estado_imperio_migrado",
            })
            migrados += 1
        except Exception:
            pass

    # 5. scout_memoria.json — oportunidades históricas
    scout_mem = MEMORY_DIR / "scout_memoria.json"
    if scout_mem.exists():
        try:
            data = json.loads(scout_mem.read_text())
            ops = data.get("oportunidades", {})
            for nome, info in list(ops.items())[:20]:
                _append_kb({
                    "ts": "2026-07-01T00:00:00+00:00",
                    "agente": "scout",
                    "tema": "oportunidade_historica",
                    "conteudo": f"{nome} — visto {info.get('vezes_visto',1)}x desde {info.get('primeira_vez','')}",
                    "origem": "scout_memoria_migrado",
                })
                migrados += 1
        except Exception as e:
            logger.warning("Migração scout_memoria falhou: %s", e)

    return {"status": "migrado", "total_migrados": migrados}


# ── Decorator para funções de agentes ────────────────────────────────────────

def registar_acao(agente: str, tema: str, extrair_resumo=None):
    """
    Decorator que regista automaticamente o resultado de uma função na base de conhecimento.
    Só regista se o resultado não for None, não for erro, e não for "sem novidade".

    Uso:
        @registar_acao("cfo", "nova_funcao")
        def nova_funcao(...) -> str:
            ...
    """
    import functools

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            resultado = fn(*args, **kwargs)
            try:
                # Não regista None, erros vazios, ou resultados triviais
                if resultado is None:
                    return resultado
                resumo = extrair_resumo(resultado) if extrair_resumo else str(resultado)[:400]
                # Filtra resultados sem valor
                sem_valor = ("sem dados", "indisponível", "sem novidade", "nenhum", "ok")
                if resumo.strip().lower() in sem_valor or len(resumo.strip()) < 10:
                    return resultado
                registar_evento(agente, tema, resumo)
            except Exception:
                pass
            return resultado
        return wrapper
    return decorator


# ── Compatibilidade retroactiva ───────────────────────────────────────────────

def get_eventos(agente: str | None = None, tema: str | None = None, limite: int = 20) -> list[dict]:
    return get_eventos_recentes(agente=agente, tema=tema, limite=limite)
