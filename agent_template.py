"""
Morgan Agent Template — base obrigatória para todos os novos agentes.

Todo o agente criado (pelo Creator ou manualmente) deve:
1. Importar e chamar agent_bootstrap() na primeira execução
2. Chamar get_agent_context() no início de cada resposta (camada semântica)
3. Chamar registar_evento() no fim de cada resposta (camada episódica)
4. Seguir a estrutura de get_{nome}_reply(msg) como ponto de entrada

Camadas de memória obrigatórias:
  Camada 1 — Trabalho (RAM): histórico da sessão em _history list
  Camada 2 — Episódica: registar_evento() após cada resposta
  Camada 3 — Semântica: get_agent_context() antes de cada resposta
  Camada 4 — Procedural: system prompt com regras explícitas do agente
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import anthropic
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent / "memory"
EPISODIC_FILE = MEMORY_DIR / "episodic_memory.json"


# ── Bootstrap — primeira tarefa de qualquer novo agente ──────────────────────

def agent_bootstrap(nome_agente: str, verbose: bool = False) -> str:
    """
    Primeira tarefa de qualquer novo agente: ler toda a memória do sistema
    desde o momento zero e construir contexto completo.

    Lê:
    - Todos os eventos episódicos registados (episodic_memory.json)
    - Memória semântica do Qdrant (get_agent_context)
    - factos.md (memória procedural)
    - sistema_estado.json (estado actual do sistema)

    Deve ser chamado uma vez na inicialização do agente.
    Regista o bootstrap como evento episódico para não repetir.
    """
    from episodic_memory import registar_evento, get_eventos_recentes

    # Verificar se já foi feito o bootstrap
    bootstrap_key = f"{nome_agente}:bootstrap_completo"
    try:
        data = json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
        if bootstrap_key in data.get("ultimo_hash", {}):
            if verbose:
                logger.info("[%s] bootstrap já realizado anteriormente", nome_agente)
            return "bootstrap_ja_feito"
    except Exception:
        pass

    resumo_partes = []

    # 1. Eventos episódicos — tudo o que aconteceu
    eventos = get_eventos_recentes(limite=200)
    if eventos:
        linhas = []
        for ev in reversed(eventos):  # cronológico
            ts = ev.get("ts", "")[:10]
            ag = ev.get("agente", "?")
            tema = ev.get("tema", "?")
            conteudo = ev.get("conteudo", "")[:120]
            linhas.append(f"[{ts}] {ag}/{tema}: {conteudo}")
        resumo_partes.append("=== HISTÓRICO EPISÓDICO ===\n" + "\n".join(linhas))

    # 2. Memória semântica Qdrant
    try:
        from mem0_service import get_agent_context
        ctx = get_agent_context(nome_agente, "contexto geral Morgan BC Industries Vasco agentes")
        if ctx:
            resumo_partes.append(f"=== MEMÓRIA SEMÂNTICA ===\n{ctx}")
    except Exception:
        pass

    # 3. Factos procedurais
    try:
        factos_path = MEMORY_DIR / "factos.md"
        if factos_path.exists():
            resumo_partes.append(f"=== FACTOS DO SISTEMA ===\n{factos_path.read_text(encoding='utf-8')[:1000]}")
    except Exception:
        pass

    # 4. Estado actual do sistema
    try:
        estado_path = MEMORY_DIR / "sistema_estado.json"
        if estado_path.exists():
            estado = json.loads(estado_path.read_text(encoding="utf-8"))
            agentes = estado.get("agentes", {})
            negocios = estado.get("negocios", {})
            resumo_partes.append(
                f"=== ESTADO SISTEMA ===\n"
                f"Agentes activos: {list(agentes.keys())}\n"
                f"Negócios: {list(negocios.keys())}"
            )
    except Exception:
        pass

    resumo_completo = "\n\n".join(resumo_partes)

    # Registar bootstrap como evento — não vai repetir
    registar_evento(nome_agente, "bootstrap_completo",
                    f"bootstrap em {datetime.now().strftime('%Y-%m-%d')} — {len(eventos)} eventos lidos")

    if verbose:
        logger.info("[%s] bootstrap completo: %d eventos, %d chars de contexto",
                    nome_agente, len(eventos), len(resumo_completo))

    return resumo_completo


# ── Funções de memória padrão — copiar para cada agente ──────────────────────

def _memory_before_reply(nome_agente: str, query: str) -> str:
    """Camada 3 (semântica) — chamar ANTES de gerar resposta."""
    try:
        from mem0_service import get_agent_context
        return get_agent_context(nome_agente, query) or ""
    except Exception:
        return ""


def _memory_after_reply(nome_agente: str, tema: str, pergunta: str, resposta: str):
    """Camada 2 (episódica) — chamar DEPOIS de gerar resposta."""
    try:
        from episodic_memory import registar_evento
        registar_evento(nome_agente, tema, f"Q: {pergunta[:100]} | R: {resposta[:200]}")
    except Exception:
        pass


# ── Template de agente — esqueleto para o Creator copiar ─────────────────────

AGENT_CODE_TEMPLATE = '''"""
Morgan {NOME_MAIUSCULAS} — {DESCRICAO}
"""
import os
import logging
from pathlib import Path
import anthropic
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
MEMORY_DIR = Path(__file__).parent / "memory"

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
_{NOME}_history: list = []

SYSTEM_PROMPT = """És o Morgan {NOME_MAIUSCULAS}. {DESCRICAO}
Reportas ao Morgan CEO. O Vasco pode falar directamente contigo.
Para voltar ao Morgan CEO, o Vasco diz "volta ao Morgan".
Tom: directo, factual, sem rodeios. Sempre em português europeu. Sem emojis.
"""


def _bootstrap_once():
    """Lê toda a memória do sistema na primeira execução."""
    from agent_template import agent_bootstrap
    return agent_bootstrap("{NOME}", verbose=True)


# Executar bootstrap na importação (uma vez, ignorado se já feito)
_bootstrap_context = _bootstrap_once()


def get_{NOME}_reply(msg: str) -> str:
    global _{NOME}_history

    # Camada 3 — memória semântica
    mem = ""
    try:
        from mem0_service import get_agent_context
        mem = get_agent_context("{NOME}", msg or "{QUERY_DEFAULT}") or ""
    except Exception:
        pass

    system = SYSTEM_PROMPT
    if mem:
        system += f"\\n## Memória relevante:\\n{{mem}}\\n"
    if _bootstrap_context and _bootstrap_context != "bootstrap_ja_feito":
        system += f"\\n## Contexto histórico do sistema:\\n{{_bootstrap_context[:2000]}}\\n"

    _{NOME}_history.append({{"role": "user", "content": msg}})
    if len(_{NOME}_history) > 20:
        _{NOME}_history = _{NOME}_history[-20:]

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=_{NOME}_history,
    )
    reply = response.content[0].text if response.content else "Sem resposta."
    _{NOME}_history.append({{"role": "assistant", "content": reply}})

    # Camada 2 — memória episódica
    try:
        from episodic_memory import registar_evento
        registar_evento("{NOME}", "conversa", f"Q: {{msg[:100]}} | R: {{reply[:200]}}")
    except Exception:
        pass

    return reply


if __name__ == "__main__":
    print(get_{NOME}_reply("Apresenta-te e descreve as tuas capacidades."))
'''


def gerar_codigo_agente_base(nome: str, descricao: str, query_default: str = "") -> str:
    """
    Gera código Python de um novo agente com todas as camadas de memória.
    Usado pelo Creator como ponto de partida antes de personalizar.
    """
    return (AGENT_CODE_TEMPLATE
            .replace("{NOME}", nome.lower())
            .replace("{NOME_MAIUSCULAS}", nome.upper())
            .replace("{DESCRICAO}", descricao)
            .replace("{QUERY_DEFAULT}", query_default or f"{nome} sistema Morgan"))
