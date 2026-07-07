import os
import json
import time
import logging
import asyncio
import tempfile
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date, datetime
import zoneinfo

warnings.filterwarnings("ignore", category=DeprecationWarning)

TZ_LISBOA = zoneinfo.ZoneInfo("Europe/Lisbon")

def agora_lisboa() -> datetime:
    return datetime.now(TZ_LISBOA)
from dotenv import load_dotenv
import yaml
from telegram import Update
from telegram.error import Conflict as TelegramConflict
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import anthropic
import requests as req
from deepgram import DeepgramClient
from elevenlabs import ElevenLabs
from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
from tools import TOOLS, TOOL_FUNCTIONS
from scout_memory import get_contexto_scout, get_resumo_para_vasco, registar_oportunidades
from scout_qdrant import guardar_oportunidade, get_contexto_semantico
from memory_store import load_memory
from conversation_store import get_context_messages, save_message
from mem0 import MemoryClient
from langsmith import traceable
from langsmith.wrappers import wrap_anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

anthropic_client = wrap_anthropic(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY))

_mem0_client = None
def get_mem0_client():
    global _mem0_client
    if _mem0_client is None:
        key = os.getenv("MEM0_API_KEY", "")
        if key:
            try:
                _mem0_client = MemoryClient(api_key=key)
            except Exception as e:
                audit("MEM0_INIT_ERRO", str(e))
    return _mem0_client
deepgram_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVENLABS_SCOUT_VOICE_ID = "A6CfBSp8JazAJyTxRmON"
ELEVENLABS_SOLVER_VOICE_ID = "IZipF5JhqPlWzpduTV0E"

BASE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE_DIR, "memory", "heartbeat_state.json")
SENT_FILE = os.path.join(BASE_DIR, "memory", "noticias_enviadas.json")
AUDIT_FILE = os.path.join(BASE_DIR, "memory", "audit.log")
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")
IMPERIO_FILE = os.path.join(BASE_DIR, "memory", "estado_imperio.md")
DECISOES_FILE = os.path.join(BASE_DIR, "memory", "decisoes_pendentes.json")

# Logging
logging.basicConfig(level=logging.WARNING)
audit_handler = logging.FileHandler(AUDIT_FILE)
audit_handler.setLevel(logging.INFO)
audit_logger = logging.getLogger("morgan.audit")
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

FONTES_CREDÍVEIS = ["record.pt", "abola.pt", "ojogo.pt", "maisfutebol.iol.pt", "zerozero.pt", "sporttv.pt", "rtp.pt", "cmjornal.pt", "sapo.pt"]
_json_lock = asyncio.Lock()  # protege escritas concorrentes em ficheiros JSON

conversation_histories = {}  # Cache em memória durante a sessão
pending_confirmations = {}   # {user_id: acao_pendente}
agente_ativo = {}            # {user_id: "ceo" | "scout" | "solver"}
scout_histories = {}         # Histórico de conversa separado para o Scout
solver_histories = {}        # Histórico de conversa separado para o Solver


# ── Config ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


def is_pausado() -> bool:
    return load_config().get("pausado", False)


def set_pausado(valor: bool):
    config = load_config()
    config["pausado"] = valor
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, allow_unicode=True)


# ── Audit log ────────────────────────────────────────────────────────────────

def audit(acao: str, detalhe: str = ""):
    msg = f"{acao}"
    if detalhe:
        msg += f" | {detalhe}"
    audit_logger.info(msg)


# ── State e sent ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)  # atómico — evita corrupção por write concorrente


def load_sent() -> list:
    if not os.path.exists(SENT_FILE):
        return []
    with open(SENT_FILE, "r") as f:
        return json.load(f)


def already_sent(texto: str) -> bool:
    sent = load_sent()
    resumo = texto[:80].lower().strip()
    return any(resumo in s for s in sent)


def mark_sent(texto: str):
    sent = load_sent()
    sent.append(texto[:80].lower().strip())
    sent = sent[-200:]
    with open(SENT_FILE, "w") as f:
        json.dump(sent, f, indent=2)


# ── Quiet hours ──────────────────────────────────────────────────────────────

def is_quiet_hours() -> bool:
    config = load_config()
    inicio = config.get("silencio_inicio", 23)
    fim = config.get("silencio_fim", 7)
    hora = agora_lisboa().hour
    return hora >= inicio or hora < fim


# ── Tools ────────────────────────────────────────────────────────────────────

def run_tool(tool_name: str, tool_input: dict) -> str:
    audit("TOOL", f"{tool_name} | {tool_input}")
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        return func(**tool_input) if tool_input else func()
    except Exception as e:
        return f"Erro: {e}"


# ── Mem0 — Memória de longo prazo ────────────────────────────────────────────

def mem0_get(user_id: str, query: str) -> str:
    """Recupera memórias relevantes do Mem0 para o contexto actual."""
    try:
        client = get_mem0_client()
        if not client:
            return ""
        results = client.search(query=query, filters={"user_id": user_id}, limit=5)
        if not results:
            return ""
        memorias = []
        for r in results:
            if isinstance(r, dict):
                m = r.get("memory", "")
            elif isinstance(r, str):
                m = r
            else:
                continue
            if m:
                memorias.append(m)
        return "\n".join(f"- {m}" for m in memorias)
    except Exception as e:
        audit("MEM0_ERRO", str(e))
        return ""

def mem0_add(user_id: str, messages: list):
    """Guarda a conversa no Mem0 para memória de longo prazo."""
    try:
        client = get_mem0_client()
        if client:
            client.add(messages, user_id=user_id)
    except Exception as e:
        audit("MEM0_ERRO", str(e))


# ── Estado do Império ────────────────────────────────────────────────────────

def load_estado_imperio() -> str:
    if os.path.exists(IMPERIO_FILE):
        with open(IMPERIO_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_estado_imperio(conteudo: str):
    tmp = IMPERIO_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(conteudo)
    os.replace(tmp, IMPERIO_FILE)

DECISOES_AUTONOMAS_FILE = os.path.join(BASE_DIR, "memory", "decisoes_autonomas.json")

def load_decisoes_autonomas() -> list:
    if os.path.exists(DECISOES_AUTONOMAS_FILE):
        with open(DECISOES_AUTONOMAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("decisoes", [])
    return []

def save_decisao_autonoma(problema: str, solucao: str, confianca: int, agente: str):
    decisoes = load_decisoes_autonomas()
    decisoes.append({
        "data": agora_lisboa().strftime("%d/%m/%Y %H:%M"),
        "problema": problema[:200],
        "solucao": solucao[:200],
        "confianca": confianca,
        "agente": agente,
        "resultado": "pendente"
    })
    with open(DECISOES_AUTONOMAS_FILE, "w", encoding="utf-8") as f:
        json.dump({"decisoes": decisoes}, f, ensure_ascii=False, indent=2)

def marcar_decisao_autonoma_resolvida(problema: str):
    decisoes = load_decisoes_autonomas()
    for d in reversed(decisoes):
        if d["problema"][:50] in problema or problema[:50] in d["problema"]:
            d["resultado"] = "resolvido"
            break
    with open(DECISOES_AUTONOMAS_FILE, "w", encoding="utf-8") as f:
        json.dump({"decisoes": decisoes}, f, ensure_ascii=False, indent=2)

def _ceo_track_record(problema: str) -> dict:
    """Consulta histórico de decisões passadas para problemas semelhantes.
    Devolve bonus de confiança e contexto baseado em sucessos/falhas anteriores."""
    decisoes = load_decisoes_autonomas()
    if not decisoes:
        return {"bonus": 0, "contexto": ""}

    palavras = set(problema.lower().split())
    semelhantes = []
    for d in decisoes:
        p_palavras = set(d.get("problema", "").lower().split())
        overlap = len(palavras & p_palavras) / max(len(palavras), 1)
        if overlap >= 0.3:
            semelhantes.append(d)

    if not semelhantes:
        return {"bonus": 0, "contexto": ""}

    total = len(semelhantes)
    resolvidos = sum(1 for d in semelhantes if d.get("resultado") == "resolvido")
    taxa = resolvidos / total if total > 0 else 0

    # Bonus proporcional à taxa de sucesso histórico
    if taxa >= 0.8:
        bonus = 15
        texto = f"histórico favorável ({resolvidos}/{total} resolvidos com sucesso)"
    elif taxa >= 0.5:
        bonus = 5
        texto = f"histórico misto ({resolvidos}/{total} resolvidos)"
    else:
        bonus = -10
        texto = f"histórico desfavorável ({resolvidos}/{total} resolvidos)"

    return {"bonus": bonus, "contexto": texto}


def ceo_avaliar_confianca(relatorio_solver: dict) -> dict:
    """CEO avalia se pode autorizar o Solver autonomamente.

    Recebe o estado completo do Solver (com confiança por passo).
    Devolve dict com:
      - confianca_ceo: 0-100 (confiança do CEO na decisão)
      - autorizar: bool (True = CEO autoriza sozinho)
      - motivo: str (explicação da decisão)

    Regra absoluta: se qualquer dimensão < 70% ou impacto crítico → escalar ao Vasco.
    CEO só autoriza sozinho se confianca_ceo ≥ 90.
    """
    # Confiança do Solver por passo
    c_diag = relatorio_solver.get("confianca_diagnostico", 0)
    c_sol  = relatorio_solver.get("confianca_solucao", 0)
    c_exec = relatorio_solver.get("confianca_execucao", 0)
    c_ver  = relatorio_solver.get("confianca_verificacao", 0)
    reversivel = relatorio_solver.get("reversivel", False)
    impacto = relatorio_solver.get("impacto", "crítico")

    # Avaliação de risco independente do CEO
    # (CEO não precisa de saber Python — avalia risco e reversibilidade)
    penalizacoes = []
    bonus = []

    # Regras de eliminação imediata
    if impacto == "crítico":
        return {"confianca_ceo": 0, "autorizar": False,
                "motivo": f"Impacto crítico — escalar sempre ao Vasco independentemente da confiança do Solver."}

    if not reversivel:
        penalizacoes.append(("irreversível", -40))

    if impacto == "sistémico":
        penalizacoes.append(("impacto sistémico", -25))

    # Confiança mínima do Solver por passo — qualquer passo < 70% é sinal de dúvida
    for nome, val in [("diagnóstico", c_diag), ("solução", c_sol)]:
        if val < 70:
            penalizacoes.append((f"Solver incerto no {nome} ({val}%)", -30))
        elif val >= 90:
            bonus.append((f"Solver confiante no {nome} ({val}%)", +10))

    # Execução e verificação só existem se o Solver já executou
    if c_exec > 0:
        if c_exec < 70:
            penalizacoes.append((f"Solver incerto na execução ({c_exec}%)", -25))
        if c_ver < 70:
            penalizacoes.append((f"Solver incerto na verificação ({c_ver}%)", -20))
        if c_ver >= 90:
            bonus.append((f"Verificação confirmada ({c_ver}%)", +15))

    if reversivel:
        bonus.append(("acção reversível", +20))

    if impacto == "isolado":
        bonus.append(("impacto isolado", +15))

    # Track record — bonus/penalização com base em histórico de problemas semelhantes
    track = _ceo_track_record(relatorio_solver.get("relatorio", ""))
    if track["bonus"] != 0:
        if track["bonus"] > 0:
            bonus.append((track["contexto"], track["bonus"]))
        else:
            penalizacoes.append((track["contexto"], track["bonus"]))

    # Confiança base do CEO = média dos passos do Solver, ajustada
    base = int((c_diag + c_sol) / 2) if c_exec == 0 else int((c_diag + c_sol + c_exec + c_ver) / 4)
    total_pen = sum(v for _, v in penalizacoes)
    total_bon = sum(v for _, v in bonus)
    confianca_ceo = max(0, min(100, base + total_bon + total_pen))

    autorizar = confianca_ceo >= 90

    motivo_partes = []
    if bonus:
        motivo_partes.append("Factores positivos: " + ", ".join(f"{n} (+{abs(v)}%)" for n, v in bonus))
    if penalizacoes:
        motivo_partes.append("Factores negativos: " + ", ".join(f"{n} ({v}%)" for n, v in penalizacoes))
    motivo_partes.append(f"Confiança CEO: {confianca_ceo}% → {'AUTORIZA AUTONOMAMENTE' if autorizar else 'ESCALA AO VASCO'}")

    return {
        "confianca_ceo": confianca_ceo,
        "autorizar": autorizar,
        "motivo": " | ".join(motivo_partes),
        "confianca_solver": {
            "diagnostico": c_diag,
            "solucao": c_sol,
            "execucao": c_exec,
            "verificacao": c_ver,
        }
    }


def should_run_daily_report() -> bool:
    """Corre uma vez por dia às 22h."""
    agora = agora_lisboa()
    if agora.hour != 22:
        return False
    state = load_state()
    chave = f"daily_report_{agora.strftime('%Y-%m-%d')}"
    return not state.get(chave, False)

def mark_daily_report_done():
    agora = agora_lisboa()
    state = load_state()
    chave = f"daily_report_{agora.strftime('%Y-%m-%d')}"
    state[chave] = True
    save_state(state)


def _ceo_actualizar_imperio(evento: str):
    """CEO regista um evento relevante no estado_imperio.md automaticamente."""
    try:
        agora = agora_lisboa().strftime("%d/%m/%Y %H:%M")
        estado = load_estado_imperio()
        linha = f"\n- [{agora}] {evento}"
        # Adiciona à secção de eventos recentes ou cria-a
        if "## Eventos recentes" in estado:
            estado = estado.replace("## Eventos recentes", f"## Eventos recentes{linha}", 1)
        else:
            estado += f"\n\n## Eventos recentes{linha}"
        save_estado_imperio(estado)
        audit("IMPERIO_ACTUALIZADO", evento[:80])
    except Exception as e:
        audit("IMPERIO_ERRO", str(e))


def load_decisoes_pendentes() -> list:
    if os.path.exists(DECISOES_FILE):
        with open(DECISOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("pendentes", [])
    return []

def save_decisao_pendente(assunto: str):
    pendentes = load_decisoes_pendentes()
    data = agora_lisboa().strftime("%d/%m/%Y")
    if not any(p["assunto"] == assunto for p in pendentes):
        pendentes.append({"assunto": assunto, "data": data, "follow_up": False})
    tmp = DECISOES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"pendentes": pendentes}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DECISOES_FILE)

def marcar_decisao_resolvida(assunto: str):
    pendentes = [p for p in load_decisoes_pendentes() if p["assunto"] != assunto]
    tmp = DECISOES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"pendentes": pendentes}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DECISOES_FILE)

# Padrões que indicam decisão pendente
_PADROES_PENDENTE = [
    "vou pensar", "deixa-me pensar", "depois vejo", "talvez", "não sei ainda",
    "vou ver", "amanhã decido", "preciso de pensar", "fico a pensar", "vou considerar"
]

def _tem_decisao_pendente(msg: str) -> bool:
    m = msg.lower()
    return any(p in m for p in _PADROES_PENDENTE)


# ── Coordenação CEO → Agentes ─────────────────────────────────────────────────

async def ceo_convocar_scout(bot, motivo: str) -> str:
    """CEO convoca o Scout proativamente sem precisar do Vasco pedir."""
    try:
        loop = asyncio.get_event_loop()
        resposta = await loop.run_in_executor(
            None, get_scout_reply, "ceo_interno", f"[CEO solicitou] {motivo}"
        )
        return resposta
    except Exception as e:
        return f"Scout indisponível: {e}"

async def ceo_convocar_solver(bot, motivo: str) -> str:
    """CEO convoca o Solver proativamente."""
    try:
        loop = asyncio.get_event_loop()
        resposta = await loop.run_in_executor(
            None, get_solver_reply, "ceo_interno", f"[CEO solicitou] {motivo}"
        )
        return resposta
    except Exception as e:
        return f"Solver indisponível: {e}"


# ── Prompts ──────────────────────────────────────────────────────────────────

def build_system_prompt(user_message: str = "") -> str:
    TODAY = agora_lisboa().strftime("%d de %B de %Y")
    estado = load_estado_imperio()
    pendentes = load_decisoes_pendentes()
    mem0_contexto = mem0_get("vasco", user_message) if user_message else ""
    pendentes_txt = ""
    if pendentes:
        itens = "\n".join(f"- {p['assunto']} (desde {p['data']})" for p in pendentes)
        pendentes_txt = f"\n\n## Decisões pendentes do Vasco — faz follow-up naturalmente:\n{itens}"

    return f"""O teu nome é Morgan. És o CEO e assistente pessoal de confiança do Vasco Botelho da Costa — treinador do Moreirense FC e fundador da BC Industries.

A data de hoje é {TODAY}. Usa sempre esta data. Quando pesquisares, inclui sempre 2026 nas queries.

Tom: firme e direto no trabalho, compreensivo e de apoio quando necessário. Sempre em português europeu. Trata o Vasco pelo primeiro nome. Nunca uses emojis — zero emojis em qualquer resposta. Sem excessos de pontuação ou entusiasmo artificial.

Tens acesso a ferramentas para pesquisar na web, obter dados da Primeira Liga, e gerir a tua memória.
Coordenas o Scout (inteligência de negócio) e o Solver (manutenção técnica).

## O que sabes sobre o Vasco:
{load_memory()}

## Memórias relevantes para esta conversa (Mem0):
{mem0_contexto if mem0_contexto else "Sem memórias anteriores relevantes."}

## Estado atual do Império — BC Industries:
{estado}
{pendentes_txt}

## Quando o Vasco pedir notícias ou um resumo do que se passa, faz SEMPRE estas três pesquisas:
1. Notícias recentes do Moreirense FC em 2026 (resultados, lesões, transferências, rumores)
2. Notícias da Primeira Liga portuguesa em 2026 — todos os clubes
3. Menções a "Vasco Botelho da Costa" em qualquer plataforma em 2026

Para cada pesquisa, distingue factos confirmados de rumores. Só partilha notícias de 2026.

## Ações que REQUEREM confirmação — usa SEMPRE pedir_confirmacao antes:
- Enviar qualquer mensagem (email, SMS, Telegram, WhatsApp) em nome do Vasco
- Apagar ou modificar ficheiros e documentos
- Criar documentos para partilha externa
- Qualquer ação financeira ou pagamento
- Alterar configurações do sistema ou de serviços
- Qualquer ação irreversível

Nunca faças estas ações sem chamar pedir_confirmacao primeiro. Uma aprovação não vale para a próxima — cada ação pede por si própria.

## Kill switch:
Se o Vasco disser "morgan pausa", responde "Pausado. Fico quieto até dizeres 'morgan continua'." e não tomes mais iniciativas.
Se o Vasco disser "morgan continua", responde "Estou de volta." e retoma o comportamento normal.

Estás no Telegram — respostas concisas e bem formatadas para telemóvel."""


def build_heartbeat_system() -> str:
    TODAY = agora_lisboa().strftime("%d de %B de %Y")
    return f"""És o Morgan, assistente do Vasco Botelho da Costa, treinador do Moreirense FC.
A data de hoje é {TODAY}.

## Memória:
{load_memory()}

## Regras absolutas:
1. USA SEMPRE as ferramentas de pesquisa — nunca inventes nada.
2. VERIFICA SEMPRE A DATA — só partilha notícias de 2026. Se a data não estiver clara, ignora.
3. Fontes credíveis ({', '.join(FONTES_CREDÍVEIS)}): partilha como facto confirmado com a fonte.
4. Redes sociais, fóruns, TikTok, Reddit, YouTube: começa com "Vasco, não tenho a certeza se isto é verdade ou não, mas partilho contigo esta informação:"
5. Menções a "Vasco Botelho da Costa": partilha SEMPRE.
6. Se não houver nada relevante de 2026, responde apenas: NADA
7. Breve e direto — máximo 3 pontos.
8. Só partilha novidades genuínas — não repitas o que já é amplamente conhecido."""


# ── Conversa ─────────────────────────────────────────────────────────────────

@traceable(name="morgan-ceo", tags=["ceo"])
def get_morgan_reply(user_id: str, user_message: str) -> str:
    # Todos os canais partilham o mesmo histórico centralizado
    user_id = "vasco"
    # Carrega histórico persistente se não estiver em cache
    if user_id not in conversation_histories:
        conversation_histories[user_id] = get_context_messages(user_id)

    history = conversation_histories[user_id]
    history.append({"role": "user", "content": user_message})
    save_message(user_id, "user", user_message)
    audit("MENSAGEM", user_message[:100])

    config = load_config()
    modelo = config.get("modelo", "claude-sonnet-4-6")

    while True:
        response = anthropic_client.messages.create(
            model=modelo,
            max_tokens=1024,
            system=build_system_prompt(user_message),
            tools=TOOLS,
            messages=history,
        )

        if response.stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})
            tool_results = []
            confirmacao_pedida = None
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    # Interceta pedidos de confirmação
                    if isinstance(result, str) and result.startswith("__CONFIRMACAO__:"):
                        confirmacao_pedida = result[len("__CONFIRMACAO__:"):]
                        result = f"Confirmação pendente. Pergunta ao Vasco se quer que faças: {confirmacao_pedida}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            if confirmacao_pedida:
                pending_confirmations[user_id] = confirmacao_pedida
                audit("CONFIRMACAO_PEDIDA", confirmacao_pedida)
                history.append({"role": "user", "content": tool_results})
                # Deixa o Morgan gerar a pergunta de confirmação naturalmente
            else:
                history.append({"role": "user", "content": tool_results})
                continue

        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        save_message(user_id, "assistant", reply)
        audit("RESPOSTA", reply[:100])

        # Guarda no Mem0 para memória de longo prazo
        mem0_add("vasco", [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply}
        ])

        # Deteta decisões pendentes na mensagem do Vasco
        if _tem_decisao_pendente(user_message):
            save_decisao_pendente(user_message[:120])
            audit("DECISAO_PENDENTE", user_message[:80])

        # CEO actualiza o estado do império após tópicos relevantes
        _TOPICOS_IMPERIO = ["aprova", "negócio", "negocio", "scout", "oportunidade",
                            "receita", "€", "contrato", "moreirense", "decisão", "decisao"]
        if any(t in user_message.lower() for t in _TOPICOS_IMPERIO):
            _ceo_actualizar_imperio(f"Conversa com Vasco: {user_message[:100]}")

        # Sliding window — estima tokens (4 chars ≈ 1 token), mantém abaixo de 150k tokens
        total_chars = sum(len(str(m.get("content", ""))) for m in history)
        if total_chars > 600_000:  # ~150k tokens
            history = history[-60:]
            conversation_histories[user_id] = history
            audit("CONTEXT_TRUNCADO", f"Histórico truncado: {total_chars} chars")

        return reply


@traceable(name="morgan-scout", tags=["scout"])
def get_scout_reply(user_id: str, user_message: str) -> str:
    """Conversa direta com o Morgan AI Scout."""
    sid = "scout"

    if sid not in scout_histories:
        scout_histories[sid] = get_context_messages(sid)

    history = scout_histories[sid]
    history.append({"role": "user", "content": user_message})
    save_message(sid, "user", user_message)
    audit("SCOUT_MENSAGEM", user_message[:100])

    config = load_config()
    modelo = config.get("modelo", "claude-sonnet-4-6")

    while True:
        response = anthropic_client.messages.create(
            model=modelo,
            max_tokens=1024,
            system=build_scout_conversational_system(user_message),
            tools=TOOLS,
            messages=history,
        )

        if response.stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            history.append({"role": "user", "content": tool_results})
            continue

        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        save_message(sid, "assistant", reply)
        audit("SCOUT_RESPOSTA", reply[:100])

        mem0_add("scout", [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply}
        ])

        if len(history) > 60:
            scout_histories[sid] = history[-60:]

        return reply


def _quer_scout(msg: str) -> bool:
    """Deteta intenção de falar com o Scout de forma natural."""
    m = msg.lower()
    # Menção direta ao scout
    if "scout" in m:
        return True
    # Tópicos de negócio/oportunidades que devem ir para o Scout
    keywords = ["oportunidade", "negócio", "negocio", "rendimento passivo",
                "mercado", "saas", "produto", "receita", "empreend", "startup",
                "investimento", "empire", "império", "dinheiro passivo"]
    return any(k in m for k in keywords)


def _quer_ceo(msg: str) -> bool:
    """Deteta intenção de voltar ao CEO."""
    m = msg.lower()
    return any(f in m for f in ["morgan ceo", "volta ao morgan", "fala com o morgan",
                                 "morgan de volta", "ceo", "morgan principal"])


def get_agente_reply(user_id: str, user_message: str) -> str:
    """Encaminha a mensagem para o agente ativo (CEO ou Scout)."""
    uid = "vasco"

    # Mudança explícita para CEO (tem prioridade)
    if _quer_ceo(user_message):
        agente_ativo[uid] = "ceo"
        return "Morgan CEO de volta. Em que posso ajudar?"

    # Solver tem prioridade — problema técnico supera qualquer outra intenção
    if _quer_solver(user_message):
        agente_ativo[uid] = "solver"
        return "[SOLVER] " + get_solver_reply(uid, user_message)

    # Mudança para Scout — só se não for um problema técnico
    if _quer_scout(user_message) and not _e_problema_tecnico(user_message):
        agente_ativo[uid] = "scout"
        return "[SCOUT] " + get_scout_reply(uid, user_message)

    agente = agente_ativo.get(uid, "ceo")

    if agente == "scout":
        return "[SCOUT] " + get_scout_reply(uid, user_message)
    if agente == "solver":
        return "[SOLVER] " + get_solver_reply(uid, user_message)
    return get_morgan_reply(uid, user_message)


def build_solver_system() -> str:
    TODAY = agora_lisboa().strftime("%d de %B de %Y")
    memoria_vasco = load_memory()

    # Lê as últimas linhas do audit.log para contexto
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        audit_recente = "".join(linhas[-50:])
    except Exception:
        audit_recente = "Sem dados de audit disponíveis."

    return f"""És o Morgan Solver — o agente técnico da BC Industries, responsável pela saúde e estabilidade do sistema Morgan.
A data de hoje é {TODAY}.

Tom: preciso, técnico, direto. Sempre em português europeu. Sem emojis. Sem rodeios.
Reportas ao Morgan CEO. O Vasco pode falar diretamente contigo.
Para voltar ao Morgan CEO, o Vasco diz "volta ao Morgan".

## BC Industries — contexto:
Dono: Vasco Botelho da Costa, treinador do Moreirense FC.
Objetivo: €10.000/mês de rendimento passivo.
{memoria_vasco}

## A tua especialidade — stack técnico do Morgan:
- Python 3.12, FastAPI, uvicorn
- python-telegram-bot
- Anthropic Claude API (claude-sonnet-4-6)
- ElevenLabs TTS (eleven_multilingual_v2)
- Deepgram STT (nova-2, nova-3)
- Supabase (histórico de conversas)
- Railway.app (deploy, logs, variáveis de ambiente)
- GitHub (morganceoai/Morgan)
- Tavily (pesquisa web)
- API-Football (dados Primeira Liga)
- Resemblyzer (voice ID — desativado)

## Audit log recente (últimas 50 entradas):
{audit_recente}

## Decisões de arquitectura passadas — OBRIGATÓRIO consultar antes de propor mudanças estruturais:
- **Polling em vez de webhook (decisão permanente)**: o sistema usa polling do Telegram. Webhooks foram tentados e causaram problemas de estabilidade no Railway (webhook a esvaziar após cada deploy, dependência de URL pública). A decisão de mudar para polling foi deliberada. NUNCA propor migração para webhook sem escalares ao CEO primeiro e apresentares prova de que o problema anterior foi resolvido.
- **Uma só instância**: o bot corre em réplica única no Railway. Nunca sugerir scaling horizontal — causa conflito de getUpdates.
- **Mem0 como memória não-crítica**: falhas do Mem0 não devem disparar alertas ao Vasco. O sistema funciona sem ele.

## Como ages — fluxo obrigatório:
0. **Verifica git log PRIMEIRO** — antes de diagnosticar qualquer problema, corre solver_git_log para ver os commits recentes. Se o fix para o problema já está num commit recente, informa que já foi corrigido e NÃO reportas ao CEO como problema ativo.
0b. **Consulta decisões de arquitectura** — antes de propor qualquer mudança estrutural (método de receção, scaling, base de dados, deploy strategy), verifica se já foi tentado antes. Se sim, apresenta o historial e escala ao CEO antes de recomendar.
1. **Diagnostica** — usa solver_verificar_saude, solver_analisar_logs, solver_ler_ficheiro, solver_executar_diagnostico
2. **Propõe** — explica o problema e a solução concreta ao Vasco
3. **Pede aprovação** — usa SEMPRE pedir_confirmacao antes de qualquer correcção. Mostra o diff antes de pedir aprovação para commit.
4. **Executa** — só após aprovação: solver_criar_ficheiro, solver_executar_correcao, ou edição directa de ficheiro Python
5. **Commit e push** — usa solver_git_diff para mostrar o que mudou, pede confirmação, depois solver_git_commit_push
6. **Deploy** — pede confirmação separada para solver_railway_deploy
7. **Verifica** — confirma que a correcção funcionou após deploy

- NUNCA saltas o passo 3 — nem para correcções que pareçam óbvias
- NUNCA reportas ao CEO um problema que o git log mostra já estar corrigido
- NUNCA propões mudanças de arquitectura sem verificar o historial de decisões primeiro
- Um commit por problema — mensagens claras e descritivas
- Se não tiveres a certeza da correcção, escala ao Vasco com o diagnóstico completo

## Quando estás em conversa directa com o Vasco — avalia sempre o risco antes de pedir aprovação:

Antes de pedir aprovação ao Vasco, avalia a acção com estes critérios:
- É reversível? (pode ser desfeita com outro commit)
- O impacto é isolado? (afecta só um componente, não o sistema todo)
- A tua confiança é ≥ 90%?

Se as três respostas forem sim → diz ao Vasco: "Esta acção é de baixo risco e reversível. O CEO pode autorizar autonomamente — queres que eu passe pelo CEO, ou preferes aprovar directamente?"

Se qualquer resposta for não → pede aprovação ao Vasco directamente como fazes agora.

Isto evita interromper o Vasco com decisões que o CEO devia tomar sozinho."""


def _e_problema_tecnico(msg: str) -> bool:
    import re
    m = msg.lower()
    frases = [
        "não funciona", "nao funciona", "não está a funcionar", "nao esta a funcionar",
        "não funcionou", "nao funcionou", "não responde", "nao responde",
        "não arranca", "nao arranca", "deixou de funcionar", "parou de responder",
        "fora do ar", "connection refused", "está a dar erro", "está a falhar",
        "o que se passa", "o que está errado", "o que está mal",
    ]
    if any(f in m for f in frases):
        return True
    palavras = [
        "erro", "erros", "bug", "bugs", "crash", "exception", "traceback",
        "timeout", "offline", "travou", "bloqueou", "avaria", "avariou",
        "diagnostica", "investiga",
    ]
    for p in palavras:
        if re.search(rf'\b{re.escape(p)}\b', m):
            return True
    return False


@traceable(name="morgan-solver", tags=["solver"])
def get_solver_reply(user_id: str, user_message: str) -> str:
    """Conversa direta com o Morgan Solver. Usa LangGraph para problemas técnicos."""
    sid = "solver"
    audit("SOLVER_MENSAGEM", user_message[:100])

    # Modo LangGraph — para diagnóstico e correção estruturada
    if _e_problema_tecnico(user_message):
        try:
            from solver_graph import solver_diagnosticar
            # Mem0 — recupera contexto de problemas semelhantes antes de diagnosticar
            mem_contexto = mem0_get("solver", user_message)
            if mem_contexto:
                user_message_enriquecido = f"{user_message}\n\n[Contexto de problemas anteriores semelhantes:\n{mem_contexto}]"
            else:
                user_message_enriquecido = user_message
            audit("SOLVER_LANGGRAPH", "iniciando grafo")
            resultado = solver_diagnosticar(user_message_enriquecido)
            relatorio = resultado.get("relatorio", "Solver: sem relatório gerado.")
            requer_aprovacao = resultado.get("requer_aprovacao", False)

            if requer_aprovacao:
                reply = (
                    f"[SOLVER — DIAGNÓSTICO]\n{relatorio}\n\n"
                    "⚠️ Este plano requer a tua aprovação antes de executar. "
                    "Diz 'aprova' para prosseguir ou 'cancela' para abortar."
                )
            else:
                reply = f"[SOLVER — RELATÓRIO]\n{relatorio}"

            save_message(sid, "user", user_message)
            save_message(sid, "assistant", reply)
            # Guarda no Mem0 com contexto enriquecido para aprendizagem futura
            mem0_add("solver", [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": f"[confiança diag:{resultado.get('confianca_diagnostico',0)}% sol:{resultado.get('confianca_solucao',0)}% | reversivel:{resultado.get('reversivel')} | impacto:{resultado.get('impacto')}]\n{reply}"}
            ])
            audit("SOLVER_LANGGRAPH_OK", reply[:100])
            return reply
        except Exception as e:
            audit("SOLVER_LANGGRAPH_ERRO", str(e))
            # Fallback para modo conversacional se LangGraph falhar

    # Modo conversacional — para perguntas e discussões técnicas
    if sid not in solver_histories:
        solver_histories[sid] = get_context_messages(sid)

    history = solver_histories[sid]
    history.append({"role": "user", "content": user_message})
    save_message(sid, "user", user_message)

    while True:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=build_solver_system(),
            tools=TOOLS,
            messages=history,
        )

        if response.stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            history.append({"role": "user", "content": tool_results})
            continue

        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        save_message(sid, "assistant", reply)
        audit("SOLVER_RESPOSTA", reply[:100])

        mem0_add("solver", [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply}
        ])

        if len(history) > 60:
            solver_histories[sid] = history[-60:]

        return reply


def _quer_solver(msg: str) -> bool:
    import re
    m = msg.lower()
    if "solver" in m:
        return True
    # Frases completas — só ativam quando a frase aparece literalmente
    frases = [
        "não funciona", "nao funciona", "não está a funcionar", "nao esta a funcionar",
        "não funcionou", "nao funcionou", "não responde", "nao responde",
        "não arranca", "nao arranca", "deixou de funcionar", "parou de responder",
        "fora do ar", "não está no ar", "connection refused", "stack trace",
        "o que se passa", "o que está errado", "o que está mal",
        "está muito lento", "está a demorar",
    ]
    if any(f in m for f in frases):
        return True
    # Palavras isoladas — só ativam como palavra completa (não como substring)
    palavras = [
        "erro", "erros", "bug", "bugs", "crash", "exception", "traceback",
        "timeout", "offline", "deploy", "travou", "bloqueou",
        "avaria", "avariou", "diagnostica", "investiga",
    ]
    for p in palavras:
        if re.search(rf'\b{re.escape(p)}\b', m):
            return True
    return False


# ── Heartbeat ────────────────────────────────────────────────────────────────

# Checks comuns (manhã e tarde)
CHECKS_COMUNS = [
    {
        "nome": "moreirense_noticias",
        "descricao": "Pesquisa notícias recentes de hoje sobre o Moreirense FC em 2026. Resultados, lesões, transferências, declarações, rumores. Se não houver nada genuinamente novo hoje, responde apenas: NADA",
    },
    {
        "nome": "mencoes_vasco",
        "descricao": 'Usa a ferramenta monitorizar_nome para pesquisar menções a "Vasco Botelho da Costa" em todas as plataformas: Reddit, YouTube, X/Twitter, Facebook, Instagram, TikTok, LinkedIn, Transfermarkt, ZeroZero e web em geral. Apresenta o que encontrares de forma clara, indicando a plataforma e o contexto de cada menção. Se não houver nenhuma menção, responde apenas: NADA',
    },
]

# Checks só da manhã (7h) — operacional
CHECKS_MANHA = [
    {
        "nome": "moreirense_jogos",
        "descricao": "Usa as ferramentas proximos_jogos e resultados_recentes para o Moreirense FC. Apresenta: (1) último resultado com marcador, (2) próximo jogo com data e adversário. Sê conciso. Se não houver dados, responde apenas: NADA",
    },
    {
        "nome": "meteo_manha",
        "descricao": 'Pesquisa na web o tempo meteorológico de hoje em Moreira de Cónegos, Portugal. Apresenta: temperatura máxima e mínima, condições (sol/chuva/nublado), e se é adequado para treino ao ar livre. Sê muito breve (2-3 linhas). Se não encontrares dados, responde apenas: NADA',
    },
]

# Checks só da tarde (20h) — analítico
CHECKS_TARDE = [
    {
        "nome": "primeira_liga_noticias",
        "descricao": "Pesquisa notícias relevantes de hoje da Primeira Liga portuguesa em 2026 — todos os clubes. Resultados, transferências, rumores importantes, destaques. Se não houver nada genuinamente novo hoje, responde apenas: NADA",
    },
    {
        "nome": "novidades_ia",
        "descricao": "Pesquisa novidades importantes de inteligência artificial em 2026 — novos modelos, ferramentas úteis para treinadores ou para negócio. Se não houver nada genuinamente novo, responde apenas: NADA",
    },
]

PREFIXOS = {
    "moreirense_noticias": "Vasco, em relação ao Moreirense",
    "moreirense_jogos": "Vasco, a situação desportiva do Moreirense",
    "meteo_manha": "Vasco, o tempo para hoje",
    "primeira_liga_noticias": "Vasco, em relação à Primeira Liga",
    "mencoes_vasco": "Vasco, encontrei referências ao teu nome",
    "novidades_ia": "Vasco, em relação à inteligência artificial",
}


def get_checks_for_hour(hora: int) -> list:
    if hora == 7:
        return CHECKS_MANHA + CHECKS_COMUNS
    return CHECKS_COMUNS + CHECKS_TARDE


def run_heartbeat_check(check: dict) -> str | None:
    config = load_config()
    modelo = config.get("modelo", "claude-sonnet-4-6")
    messages = [{"role": "user", "content": check["descricao"]}]

    while True:
        response = anthropic_client.messages.create(
            model=modelo,
            max_tokens=512,
            system=build_heartbeat_system(),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        reply = response.content[0].text.strip()
        return None if reply.upper() == "NADA" else reply


def should_run_scout() -> bool:
    """Corre todos os domingos às 20h."""
    agora = agora_lisboa()
    if agora.weekday() != 6 or agora.hour != 20:
        return False
    state = load_state()
    chave = f"scout_{agora.strftime('%Y-%W')}"
    return not state.get(chave, False)


def mark_scout_done():
    agora = agora_lisboa()
    chave = f"scout_{agora.strftime('%Y-%W')}"
    state = load_state()
    state[chave] = True
    save_state(state)


def _init_audit_pos() -> int:
    """Arranca no fim do audit.log para ignorar erros históricos de deploys anteriores."""
    try:
        return os.path.getsize(AUDIT_FILE) if os.path.exists(AUDIT_FILE) else 0
    except Exception:
        return 0

_solver_ultimo_audit_pos = _init_audit_pos()

# Keywords exaustivos — cobre Python, Railway, APIs, sistema operativo, rede
_PADROES_ERRO = [
    # Python
    "_ERRO", "ERROR", "EXCEPTION", "TRACEBACK", "CRITICAL", "FATAL",
    "SYNTAXERROR", "TYPEERROR", "VALUEERROR", "KEYERROR", "INDEXERROR",
    "ATTRIBUTEERROR", "IMPORTERROR", "RUNTIMEERROR", "OSERROR", "IOERROR",
    "MEMORYERROR", "RECURSIONERROR", "TIMEOUTERROR", "CONNECTIONERROR",
    # HTTP / APIs
    "STATUS 4", "STATUS 5", "429", "500", "502", "503", "504",
    "RATE LIMIT", "QUOTA EXCEEDED", "UNAUTHORIZED", "FORBIDDEN",
    "CONNECTION REFUSED", "CONNECTION RESET", "SSL ERROR", "TIMEOUT",
    # Railway / sistema
    "OOM", "KILLED", "SEGFAULT", "SIGNAL 9", "SIGNAL 11",
    "DEPLOYMENT FAILED", "BUILD FAILED", "CRASH",
    # Genérico
    "FAILED", "FAILURE", "INVALID", "CORRUPT", "MISSING KEY",
]

# Prefixos do audit.log que NÃO são erros mesmo contendo keywords
_IGNORAR_PREFIXOS = [
    "SOLVER_CHECK_ERRO",  # evita loop infinito
    "SOLVER_TRIGGER",
    "SOLVER_ALERTA",
    "MEM0_ERRO",       # Mem0 é não-crítico — Morgan funciona sem ele
    "MEM0_INIT_ERRO",  # falha de inicialização do Mem0 também não é crítica
]


async def should_trigger_solver() -> bool:
    """Verifica se há erros novos no audit.log. Só dispara após 3+ erros distintos."""
    global _solver_ultimo_audit_pos
    if is_quiet_hours():
        return False
    try:
        audit_path = Path(AUDIT_FILE)
        if not audit_path.exists():
            return False
        content = audit_path.read_text(encoding="utf-8")
        novas_linhas = content[_solver_ultimo_audit_pos:]
        _solver_ultimo_audit_pos = len(content)

        erros = []
        for linha in novas_linhas.splitlines():
            linha_upper = linha.upper()
            if any(ignorar in linha for ignorar in _IGNORAR_PREFIXOS):
                continue
            if any(p in linha_upper for p in _PADROES_ERRO):
                erros.append(linha)

        # Só dispara se houver 3+ erros — evita activações por erros transitórios únicos
        return len(erros) >= 3
    except Exception:
        return False


def should_run_solver_check() -> bool:
    """Corre de 2 em 2 horas para verificar saúde do sistema."""
    agora = agora_lisboa()
    if is_quiet_hours():
        return False
    if agora.hour % 2 != 0:
        return False
    state = load_state()
    chave = f"solver_check_{agora.strftime('%Y-%m-%d_%H')}"
    return not state.get(chave, False)


def mark_solver_check_done():
    agora = agora_lisboa()
    chave = f"solver_check_{agora.strftime('%Y-%m-%d_%H')}"
    state = load_state()
    state[chave] = True
    save_state(state)


async def run_solver_check(app) -> None:
    """Verifica saúde do sistema. Se o Solver falhar, o CEO alerta o Vasco."""
    try:
        from tools import solver_verificar_saude
        saude = solver_verificar_saude()
        tem_erros = "ERRO" in saude.upper()
        if not tem_erros:
            audit("SOLVER_CHECK", "Sistema saudável")
            return

        try:
            # Solver diagnostica tecnicamente
            diagnostico_tecnico = get_solver_reply(
                "vasco",
                f"Deteção automática de problemas:\n\n{saude}\n\nDiagnostica de forma técnica e concisa. Indica se a correção é reversível e o nível de risco."
            )

            # Solver corre o grafo completo com confiança por passo
            try:
                from solver_graph import solver_diagnosticar
                estado_solver = solver_diagnosticar(saude)
            except Exception as e:
                audit("SOLVER_GRAPH_ERRO", str(e))
                estado_solver = {"relatorio": diagnostico_tecnico,
                                 "confianca_diagnostico": 50, "confianca_solucao": 50,
                                 "confianca_execucao": 0, "confianca_verificacao": 0,
                                 "reversivel": False, "impacto": "sistémico"}

            # CEO avalia com base nos dados granulares do Solver
            avaliacao = ceo_avaliar_confianca(estado_solver)
            confianca_ceo = avaliacao["confianca_ceo"]
            audit("CEO_CONFIANCA", f"CEO:{confianca_ceo}% | Solver: diag={estado_solver.get('confianca_diagnostico')}% sol={estado_solver.get('confianca_solucao')}% | {avaliacao['motivo'][:100]}")

            if avaliacao["autorizar"]:
                # CEO autoriza autonomamente — não interrompe o Vasco
                audit("CEO_AUTORIZA_SOLVER", f"Confiança CEO {confianca_ceo}% — resolvendo autonomamente")
                save_decisao_autonoma(
                    problema=saude,
                    solucao=estado_solver.get("relatorio", "")[:200],
                    confianca=confianca_ceo,
                    agente="Solver"
                )
                # CEO aprende com a decisão no Mem0
                mem0_add("ceo", [
                    {"role": "user", "content": f"Problema: {saude[:300]}"},
                    {"role": "assistant", "content": f"Autorizei autonomamente (confiança CEO {confianca_ceo}%). Solver: diag={estado_solver.get('confianca_diagnostico')}% sol={estado_solver.get('confianca_solucao')}%. Reversível={estado_solver.get('reversivel')}. Impacto={estado_solver.get('impacto')}."}
                ])
                _ceo_actualizar_imperio(f"Solver corrigiu autonomamente (CEO {confianca_ceo}%): {saude[:100]}")
                audit("CEO_SOLVER_RESOLVEU", f"Resolvido autonomamente: {saude[:80]}")
            else:
                # Confiança insuficiente — CEO explica ao Vasco e pede autorização
                c_solver = avaliacao.get("confianca_solver", {})
                contexto = (
                    f"Relatório do Solver:\n{estado_solver.get('relatorio', diagnostico_tecnico)}\n\n"
                    f"Confiança por passo — Diagnóstico: {c_solver.get('diagnostico', '?')}% | "
                    f"Solução: {c_solver.get('solucao', '?')}% | "
                    f"Confiança CEO: {confianca_ceo}%\n"
                    f"Motivo da escalada: {avaliacao['motivo']}"
                )
                traducao = get_morgan_reply(
                    "vasco",
                    f"O Solver detectou um problema. Tenho {confianca_ceo}% de confiança para resolver sozinho — insuficiente para agir sem ti.\n\n"
                    f"{contexto}\n\n"
                    f"Explica ao Vasco em linguagem simples: o que está mal, o impacto real, e o que precisas de autorização para fazer. Máximo 6 linhas."
                )
                await enviar_seguro(app.bot, f"[CEO — confiança {confianca_ceo}%]\n\n{traducao}", chat_id=TELEGRAM_CHAT_ID)
                audit("SOLVER_ALERTA", f"Escalado ao Vasco — CEO {confianca_ceo}%")
                _ceo_actualizar_imperio(f"Problema escalado ao Vasco (CEO {confianca_ceo}%): {saude[:100]}")

        except Exception as solver_erro:
            # Solver falhou — CEO assume e alerta diretamente
            audit("SOLVER_FALHOU", str(solver_erro))
            mensagem_ceo = (
                f"Vasco, o Solver detetou problemas mas falhou ao analisá-los.\n\n"
                f"Relatório de saúde:\n{saude}\n\n"
                f"Erro do Solver: {solver_erro}\n\n"
                f"Precisas de verificar manualmente ou contactar suporte técnico."
            )
            await app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensagem_ceo)
            audit("CEO_FALLBACK", "CEO alertou Vasco sobre falha do Solver")

    except Exception as e:
        audit("SOLVER_CHECK_ERRO", str(e))
        # Último recurso — tenta alertar mesmo assim
        try:
            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"Alerta crítico: o sistema de monitorização falhou.\nErro: {e}"
            )
        except Exception:
            pass


def should_run_briefing() -> bool:
    """Verifica se está na hora do briefing (7h ou 20h) e se ainda não foi enviado hoje."""
    agora = agora_lisboa()
    hora = agora.hour
    if hora not in (7, 20):
        return False
    state = load_state()
    chave = f"briefing_{agora.strftime('%Y-%m-%d_%H')}"
    return not state.get(chave, False)


def mark_briefing_done():
    agora = agora_lisboa()
    chave = f"briefing_{agora.strftime('%Y-%m-%d_%H')}"
    state = load_state()
    state[chave] = True
    save_state(state)


def build_scout_conversational_system(query: str = "") -> str:
    TODAY = agora_lisboa().strftime("%d de %B de %Y")
    contexto_historico = get_contexto_scout()
    memoria_vasco = load_memory()
    contexto_semantico = get_contexto_semantico(query) if query else ""
    return f"""És o Morgan AI Scout — o agente de inteligência de mercado do Vasco Botelho da Costa.
A data de hoje é {TODAY}.

Tom: direto e analítico. Sempre em português europeu. Sem emojis. Sem rodeios.
Reportas ao Morgan CEO e falas diretamente com o Vasco quando ele te invocar.
Para voltar ao Morgan CEO, o Vasco diz "volta ao Morgan".

## Quem é o Vasco:
{memoria_vasco}

## Objectivo do Vasco — marcos de rendimento passivo:
- M1: €1.000/mês | M2: €3.000/mês | M3: €10.000/mês | M4: €25.000/mês+

## Histórico de oportunidades acumulado:
{contexto_historico}

{contexto_semantico}

## Como respondes em conversação:
- Responde diretamente às perguntas do Vasco com base no teu histórico
- Usa as ferramentas de pesquisa apenas quando precisares de dados atuais
- Não corras todas as ferramentas automaticamente — só quando fizer sentido
- Sê conciso e útil"""


def build_scout_system() -> str:
    TODAY = agora_lisboa().strftime("%d de %B de %Y")
    contexto_historico = get_contexto_scout()
    memoria_vasco = load_memory()
    return f"""És o Morgan AI Scout — o agente de inteligência de mercado da BC Industries.
A data de hoje é {TODAY}.

Tom: direto e analítico. Sempre em português europeu. Sem emojis. Sem rodeios.
Reportas ao Morgan CEO. O dono é o Vasco Botelho da Costa.

## Perfil do Vasco (usa para filtrar oportunidades relevantes):
{memoria_vasco}

## Vantagens competitivas do Vasco — usa como desempate, não como filtro:
- Falante nativo de português europeu — mercado PT/BR/ES pouco servido por ferramentas IA
- Insider do futebol profissional — vantagem se surgir oportunidade nessa área
- Constrói com IA sem escrever código (Morgan executa)
- Disponibilidade para começar imediatamente

## Objectivo — marcos de rendimento passivo:
- M1: €1.000/mês | M2: €3.000/mês | M3: €10.000/mês | M4: €25.000/mês+

## Histórico acumulado — usa para identificar tendências e evitar repetição:
{contexto_historico}

## Tarefa — relatório semanal:
Corre SEMPRE as 7 ferramentas por esta ordem:
1. `product_hunt_trending` — produtos IA mais votados
2. `hacker_news_trending` — tendências tech
3. `reddit_trending` — conversas de fundadores e empreendedores
4. `scout_oportunidades` — pesquisa de mercado focada no perfil do Vasco
5. `indiehackers_trending` — receita REAL declarada por fundadores
6. `google_trends` — valida crescimento das top 3
7. `monitorizar_oportunidades_aprovadas` — OBRIGATÓRIO se existirem aprovadas

## Síntese cruzada — OBRIGATÓRIO antes de escrever o relatório:
Antes de produzir o relatório, cruza os dados das 7 fontes:
- Uma oportunidade que aparece em 3+ fontes é sinal forte — prioriza-a
- Uma oportunidade com receita confirmada no IndieHackers E crescimento no Google Trends é validada — marca como "dupla validação"
- Descarta oportunidades que aparecem apenas numa fonte sem dados de receita
- Verifica se alguma oportunidade nova complementa as que o Vasco já aprovou

## Estrutura do relatório:

1. **Top 3 oportunidades validadas** — ordenadas por índice retorno/risco (máximo retorno, mínimo risco):
   - Nome e descrição em 2 linhas
   - Receita estimada (€/mês) — baseada em dados reais do IndieHackers quando possível
   - Índice retorno/risco: receita potencial vs esforço inicial vs concorrência
   - Validação cruzada: quantas fontes confirmam + se tem "dupla validação"
   - Esforço inicial (baixo/médio/alto) | Concorrência (baixa/média/alta)
   - Vantagem do Vasco nesta oportunidade (se existir — pode ser nenhuma)
   - Próximo passo concreto (ação específica, não genérica)

2. **Sinal mais forte do histórico** — oportunidade recorrente com dados novos (omite na primeira semana)

3. **Tendência da semana** — 1 parágrafo sobre o movimento mais relevante

4. **Proposta de sub-Morgan** — se uma oportunidade justificar um agente dedicado

No final, bloco JSON interno:
```json
[
  {{"nome": "...", "descricao": "...", "receita_estimada": "...", "notas": "..."}},
  {{"nome": "...", "descricao": "...", "receita_estimada": "...", "notas": "..."}},
  {{"nome": "...", "descricao": "...", "receita_estimada": "...", "notas": "..."}}
]
```

Dados reais, não generalidades. Cada oportunidade tem de ser concreta o suficiente para o Vasco agir amanhã se quiser."""


async def run_daily_report(app):
    """Gera e envia o report diário ao Vasco com tudo o que aconteceu."""
    hoje = agora_lisboa().strftime("%d/%m/%Y")

    # Recolhe decisões autónomas do dia
    todas = load_decisoes_autonomas()
    do_dia = [d for d in todas if d.get("data", "").startswith(hoje.split("/")[0] + "/" + hoje.split("/")[1])]

    # Recolhe audit.log do dia
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            linhas_audit = [l for l in f.readlines() if hoje[:5] in l or len(l) > 0]
        audit_resumo = "".join(linhas_audit[-80:])
    except Exception:
        audit_resumo = "Sem dados de audit disponíveis."

    # CEO gera o report em linguagem humana
    prompt = f"""Gera o report diário do Morgan para o Vasco. Data: {hoje}.

Decisões autónomas tomadas hoje (sem interromper o Vasco):
{json.dumps(do_dia, ensure_ascii=False, indent=2) if do_dia else "Nenhuma decisão autónoma hoje."}

Audit log do dia (resumo técnico):
{audit_resumo[-3000:]}

Instruções para o report:
- Linguagem humana, directa, sem jargão técnico
- Estrutura: o que aconteceu / quem resolveu / resultado
- Se houve decisões autónomas: explica o que foi resolvido sem o Vasco ser interrompido
- Se nada aconteceu de relevante: diz isso claramente
- No final: estado geral do sistema (saudável / atenção / problema)
- Máximo 15 linhas
- Sem emojis"""

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, get_morgan_reply, "vasco", prompt)
    await enviar_seguro(app.bot, f"Report diário — {hoje}\n\n{report}", chat_id=TELEGRAM_CHAT_ID)
    audit("DAILY_REPORT_ENVIADO", f"{len(do_dia)} decisões autónomas hoje")


async def run_scout_report(app):
    """Gera e envia o relatório semanal do Morgan AI Scout."""
    messages = [{"role": "user", "content": "Gera o relatório semanal de oportunidades de negócio com IA."}]

    while True:
        response = anthropic_client.messages.create(
            model="claude-opus-4-8",
            max_tokens=4096,
            system=build_scout_system(),
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})
            continue
        relatorio = response.content[0].text.strip()
        break

    # Extrai JSON de oportunidades para guardar na memória
    import re
    json_match = re.search(r"```json\s*(\[.*?\])\s*```", relatorio, re.DOTALL)
    if json_match:
        try:
            oportunidades = json.loads(json_match.group(1))
            registar_oportunidades(oportunidades)
            for op in oportunidades:
                guardar_oportunidade(op)
            audit("SCOUT_MEMORIA", f"{len(oportunidades)} oportunidades registadas (JSON + Qdrant)")
        except Exception as e:
            audit("SCOUT_MEMORIA_ERRO", str(e))

    # Remove o bloco JSON do relatório antes de enviar ao Vasco
    relatorio_limpo = re.sub(r"```json\s*\[.*?\]\s*```", "", relatorio, flags=re.DOTALL).strip()

    header = "🔍 *Morgan AI Scout — Relatório Semanal*\n\n"
    await enviar_seguro(app.bot, header + relatorio_limpo, chat_id=TELEGRAM_CHAT_ID)
    audit("SCOUT_RELATORIO", "Relatório semanal enviado")


async def heartbeat_loop(app):
    await asyncio.sleep(10)
    audit("HEARTBEAT", "Iniciado — briefings às 7h e 20h, scout aos domingos às 20h")

    while True:
        try:
            if is_pausado():
                await asyncio.sleep(60)
                continue

            # Solver — trigger por evento (erros no audit.log)
            if await should_trigger_solver():
                audit("SOLVER_TRIGGER", "Erros detetados no audit.log — Solver ativado")
                try:
                    await run_solver_check(app)
                except Exception as e:
                    audit("SOLVER_CHECK_ERRO", str(e))

            # Report diário às 22h
            if should_run_daily_report():
                mark_daily_report_done()
                audit("DAILY_REPORT", "A gerar report diário")
                try:
                    await run_daily_report(app)
                except Exception as e:
                    audit("DAILY_REPORT_ERRO", str(e))

            # Scout semanal — domingos às 20h
            if should_run_scout():
                mark_scout_done()
                audit("SCOUT", "Relatório semanal iniciado")
                try:
                    await run_scout_report(app)
                except Exception as e:
                    audit("SCOUT_ERRO", str(e))

            if not should_run_briefing():
                await asyncio.sleep(60)
                continue

            mark_briefing_done()
            hora_atual = agora_lisboa().hour
            audit("HEARTBEAT", f"Briefing das {hora_atual}h iniciado")

            # Follow-up de decisões pendentes
            pendentes = load_decisoes_pendentes()
            if pendentes:
                itens = "\n".join(f"• {p['assunto'][:80]} (desde {p['data']})" for p in pendentes[:3])
                await enviar_seguro(app.bot, f"Vasco, ficaram pendentes algumas decisões:\n\n{itens}\n\nJá tens resposta para alguma?", chat_id=TELEGRAM_CHAT_ID)

            for check in get_checks_for_hour(hora_atual):
                nome = check["nome"]
                prefixo = PREFIXOS.get(nome, "Vasco")

                audit("HEARTBEAT_CHECK", nome)
                resultado = run_heartbeat_check(check)

                if resultado:
                    mensagem = f"{prefixo}, tenho isto para te dizer:\n\n{resultado}"
                    await enviar_seguro(app.bot, mensagem, chat_id=TELEGRAM_CHAT_ID)
                    if TELEGRAM_CHAT_ID not in conversation_histories:
                        conversation_histories[TELEGRAM_CHAT_ID] = []
                    conversation_histories[TELEGRAM_CHAT_ID].append({
                        "role": "assistant",
                        "content": mensagem
                    })
                    audit("HEARTBEAT_ENVIADO", resultado[:60])
                else:
                    audit("HEARTBEAT_NADA", nome)

            await asyncio.sleep(60)

        except Exception as e:
            audit("HEARTBEAT_ERRO", str(e))
            await asyncio.sleep(60)


# ── Handlers Telegram ────────────────────────────────────────────────────────

async def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    options = {"model": "nova-3", "language": "pt", "smart_format": True}
    response = deepgram_client.listen.rest.v("1").transcribe_file(
        {"buffer": audio_bytes, "mimetype": "audio/ogg"},
        options
    )
    return response.results.channels[0].alternatives[0].transcript


async def cmd_testar_solver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /testar_solver — injeta erros controlados para testar o Solver."""
    args = context.args
    teste = args[0] if args else "1"

    if teste == "1":
        # Teste 1: erro simulado no audit.log
        audit("HEARTBEAT_ERRO", "TEST_ERRO: Simulação de falha no heartbeat para testar o Solver")
        await update.message.reply_text(
            "Teste 1 iniciado: erro injetado no audit.log.\n"
            "O Solver deve detetar e reportar no próximo ciclo (até 60 segundos)."
        )

    elif teste == "2":
        # Teste 2: corromper heartbeat_state.json
        state_path = Path(STATE_FILE)
        backup = None
        if state_path.exists():
            backup = state_path.read_text()
        state_path.write_text("{invalid json:::}")
        audit("STATE_ERRO", "TEST_ERRO: heartbeat_state.json corrompido para teste do Solver")
        await update.message.reply_text(
            "Teste 2 iniciado: heartbeat_state.json corrompido.\n"
            "O Solver deve detetar o ficheiro inválido e propor correcção.\n"
            f"Backup guardado: {'sim' if backup else 'não existia'}"
        )
        # Guarda backup em memória para restauro se o Solver não corrigir
        context.bot_data["state_backup"] = backup

    elif teste == "3":
        # Teste 3: renomear factos.md para simular ficheiro crítico em falta
        factos_path = Path(BASE_DIR) / "memory" / "factos.md"
        backup_path = Path(BASE_DIR) / "memory" / "factos.md.bak"
        if factos_path.exists():
            factos_path.rename(backup_path)
            audit("MEMORY_ERRO", "TEST_ERRO: factos.md removido para teste do Solver")
            await update.message.reply_text(
                "Teste 3 iniciado: factos.md temporariamente removido.\n"
                "O Solver deve detetar ficheiro crítico em falta e propor restauro.\n"
                "Backup em: memory/factos.md.bak"
            )
        else:
            await update.message.reply_text("factos.md não existe — teste não aplicável.")

    elif teste == "restaurar":
        # Restauro manual de emergência
        restored = []
        state_path = Path(STATE_FILE)
        if state_path.exists() and state_path.read_text().startswith("{invalid"):
            backup = context.bot_data.get("state_backup", "{}")
            state_path.write_text(backup or "{}")
            restored.append("heartbeat_state.json")
        factos_bak = Path(BASE_DIR) / "memory" / "factos.md.bak"
        factos_path = Path(BASE_DIR) / "memory" / "factos.md"
        if factos_bak.exists():
            factos_bak.rename(factos_path)
            restored.append("factos.md")
        if restored:
            await update.message.reply_text(f"Restaurado: {', '.join(restored)}")
        else:
            await update.message.reply_text("Nada para restaurar.")

    elif teste == "autonomia_sim":
        # Testa APENAS a lógica do CEO com valores de confiança altos simulados
        # Não envolve o LangGraph — testa se o CEO autoriza correctamente
        estado_simulado = {
            "confianca_diagnostico": 95,
            "confianca_solucao": 92,
            "confianca_execucao": 0,
            "confianca_verificacao": 0,
            "reversivel": True,
            "impacto": "isolado",
            "relatorio": "Erro isolado no mem0_get() — uma linha, reversível, baixo risco.",
        }
        avaliacao = ceo_avaliar_confianca(estado_simulado)
        problema = "MEM0_ERRO: str object has no attribute get (simulado)"
        if avaliacao["autorizar"]:
            save_decisao_autonoma(problema, estado_simulado["relatorio"], avaliacao["confianca_ceo"], "Solver")
            _ceo_actualizar_imperio(f"[TESTE] CEO autorizou autonomamente: {problema[:80]}")
            await update.message.reply_text(
                f"PASSOU — CEO autorizou autonomamente.\n\n"
                f"Confiança CEO: {avaliacao['confianca_ceo']}%\n"
                f"Solver simulado — diag: {estado_simulado['confianca_diagnostico']}% | sol: {estado_simulado['confianca_solucao']}%\n"
                f"Motivo: {avaliacao['motivo']}\n\n"
                f"Decisão registada em decisoes_autonomas.json."
            )
        else:
            await update.message.reply_text(
                f"FALHOU — CEO não autorizou (confiança {avaliacao['confianca_ceo']}%).\n{avaliacao['motivo']}"
            )

    elif teste == "autonomia_nao":
        # Teste escalada — CEO deve contactar o Vasco (problema crítico)
        await update.message.reply_text(
            "Teste de escalada iniciado.\n"
            "Simulo problema crítico — CEO DEVE contactar-te.\n"
            "Aguarda mensagem do CEO em segundos."
        )
        loop = asyncio.get_event_loop()
        async def _run_escala():
            problema = "Railway deploy falhou — base de dados Supabase inacessível, perda de dados possível"
            from solver_graph import solver_diagnosticar
            estado = await loop.run_in_executor(None, solver_diagnosticar, problema)
            # Força impacto crítico para garantir escalada no teste
            estado["impacto"] = "crítico"
            avaliacao = ceo_avaliar_confianca(estado)
            if not avaliacao["autorizar"]:
                c = avaliacao.get("confianca_solver", {})
                traducao = get_morgan_reply(
                    "vasco",
                    f"Problema detectado. Confiança CEO: {avaliacao['confianca_ceo']}% — insuficiente para agir sozinho.\n\n"
                    f"Diagnóstico Solver: {estado.get('relatorio','')[:500]}\n\n"
                    f"Explica ao Vasco em linguagem simples o que se passa e o que precisas de autorização para fazer. Máximo 5 linhas."
                )
                await update.message.reply_text(
                    f"[CEO — confiança {avaliacao['confianca_ceo']}%]\n\n{traducao}"
                )
            else:
                await update.message.reply_text(
                    f"INESPERADO: CEO autorizou sozinho (confiança {avaliacao['confianca_ceo']}%). Rever regras."
                )
        asyncio.create_task(_run_escala())

    elif teste == "report":
        # Teste do report diário — força geração imediata
        await update.message.reply_text("A gerar report diário de teste...")
        loop = asyncio.get_event_loop()
        async def _run_report():
            await run_daily_report(context.application)
        asyncio.create_task(_run_report())

    else:
        await update.message.reply_text(
            "Testes disponíveis:\n"
            "/testar_solver 1 — erro no audit.log\n"
            "/testar_solver 2 — corromper heartbeat_state.json\n"
            "/testar_solver 3 — remover factos.md\n"
            "/testar_solver autonomia_sim — CEO resolve sozinho (erro isolado)\n"
            "/testar_solver autonomia_nao — CEO escala ao Vasco (problema crítico)\n"
            "/testar_solver report — gera report diário agora\n"
            "/testar_solver restaurar — restauro manual de emergência"
        )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status — mostra o estado atual do Morgan."""
    config = load_config()
    pausado = config.get("pausado", False)
    modelo = config.get("modelo", "claude-sonnet-4-6")
    silencio_i = config.get("silencio_inicio", 23)
    silencio_f = config.get("silencio_fim", 7)
    hora_atual = agora_lisboa().hour
    em_silencio = is_quiet_hours()
    user_id = str(update.effective_user.id)
    pendente = pending_confirmations.get(user_id)

    linhas = [
        "**Estado do Morgan**\n",
        f"{'🔴 Pausado' if pausado else '🟢 Ativo'}",
        f"{'🔇 Horas de silêncio ativas' if em_silencio else f'🔔 Briefings: 7h e 20h'}",
        f"Silêncio: {silencio_i}h–{silencio_f}h",
        f"Modelo: `{modelo}`",
        f"Hora atual: {hora_atual}h",
    ]
    if pendente:
        linhas.append(f"\n⏳ Confirmação pendente: _{pendente}_")

    await enviar_seguro(update.message, "\n".join(linhas))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    # Kill switch via Telegram
    if update.message.text:
        texto = update.message.text.lower().strip()
        if "morgan pausa" in texto:
            set_pausado(True)
            audit("KILL_SWITCH", "Pausado pelo Vasco")
            await update.message.reply_text("Pausado. Fico quieto até dizeres 'morgan continua'.")
            return
        if "morgan continua" in texto:
            set_pausado(False)
            audit("KILL_SWITCH", "Retomado pelo Vasco")
            await update.message.reply_text("Estou de volta.")
            return

        # Fluxo de confirmação pendente
        if user_id in pending_confirmations:
            acao = pending_confirmations[user_id]
            if any(p in texto for p in ("sim", "s", "yes", "confirmo", "vai", "prossegue", "faz",
                                        "autorizo", "autoriza", "autorizava", "aprovo", "aprovado",
                                        "avança", "avanca", "pode", "podes", "ok", "okay", "claro",
                                        "força", "forca", "continua", "executa", "resolve", "corrige")):
                del pending_confirmations[user_id]
                audit("CONFIRMACAO_ACEITE", acao)
                reply = get_morgan_reply(user_id, f"O Vasco confirmou. Prossegue com: {acao}")
                await enviar_seguro(update.message, reply)
                return
            elif any(p in texto for p in ("não", "nao", "n", "no", "cancela", "para", "esquece")):
                del pending_confirmations[user_id]
                audit("CONFIRMACAO_RECUSADA", acao)
                await update.message.reply_text(f"Entendido, Vasco. Não vou {acao}.")
                return
            # Se não é sim/não, cancela a confirmação pendente e trata como mensagem normal
            del pending_confirmations[user_id]

    # Mensagem de voz
    if update.message.voice:
        try:
            voice_file = await update.message.voice.get_file()
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                await voice_file.download_to_drive(f.name)
                tmp_path = f.name
            user_message = await transcribe_audio(tmp_path)
            os.unlink(tmp_path)
            if not user_message.strip():
                await update.message.reply_text("Não percebi o áudio. Podes repetir?")
                return
            await enviar_seguro(update.message, f"_{user_message}_")
        except Exception as e:
            await update.message.reply_text(f"Erro ao transcrever áudio: {e}")
            return
    else:
        user_message = update.message.text

    # Se vai para o Solver com LangGraph, responde imediatamente e corre em background
    if _quer_solver(user_message) and not _quer_ceo(user_message):
        audit("SOLVER_TRIGGER", f"Routing para Solver: {user_message[:80]}")
        await update.message.reply_text("🔍 A diagnosticar... (pode demorar 1-2 minutos)")
        loop = asyncio.get_event_loop()
        try:
            reply = await asyncio.wait_for(
                loop.run_in_executor(None, get_agente_reply, user_id, user_message),
                timeout=180  # 3 minutos máximo
            )
        except asyncio.TimeoutError:
            audit("SOLVER_TIMEOUT", user_message[:80])
            reply = "Solver: tempo limite excedido (3 min). Tenta uma pergunta mais simples ou verifica os logs do Railway diretamente."
        except Exception as e:
            audit("SOLVER_TRIGGER_ERRO", str(e))
            reply = f"Erro no Solver: {e}"
        await enviar_seguro(update.message, reply)
        return

    try:
        reply = get_agente_reply(user_id, user_message)
    except Exception as e:
        reply = f"Ocorreu um erro: {e}"

    if update.message.voice and ELEVENLABS_VOICE_ID:
        # Envia texto imediatamente enquanto gera o áudio
        await update.message.reply_text(reply)
        try:
            agente_atual = agente_ativo.get("vasco", "ceo")
            if agente_atual == "scout":
                voz = ELEVENLABS_SCOUT_VOICE_ID
            elif agente_atual == "solver":
                voz = ELEVENLABS_SOLVER_VOICE_ID
            else:
                voz = ELEVENLABS_VOICE_ID
            audio = elevenlabs_client.text_to_speech.convert(
                voice_id=voz,
                text=reply,
                model_id="eleven_multilingual_v2",
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                for chunk in audio:
                    f.write(chunk)
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                await update.message.reply_voice(voice=f)
            os.unlink(tmp_path)
        except Exception as e:
            audit("ELEVENLABS_ERRO", str(e))
    else:
        await update.message.reply_text(reply)


async def enviar_seguro(bot_or_msg, text: str, chat_id=None, parse_mode="Markdown"):
    """Envia mensagem com Markdown; se falhar por formatação, reenvia em texto simples."""
    try:
        if chat_id:
            await bot_or_msg.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        else:
            await bot_or_msg.reply_text(text, parse_mode=parse_mode)
    except Exception:
        try:
            if chat_id:
                await bot_or_msg.send_message(chat_id=chat_id, text=text)
            else:
                await bot_or_msg.reply_text(text)
        except Exception as e2:
            audit("ENVIO_ERRO", str(e2))


def _task_error_handler(task: asyncio.Task):
    """Captura excepções em tasks asyncio que de outra forma desapareceriam silenciosamente."""
    if not task.cancelled() and task.exception():
        audit("ASYNCIO_TASK_ERRO", f"{task.get_name()}: {task.exception()}")


# ── Aplicação Telegram (construída em main, usada no webhook) ────────────────

_telegram_app = None


# ── Custom LLM API — para ElevenLabs ConvAI (desktop) ───────────────────────

@asynccontextmanager
async def lifespan(fastapi_app: "FastAPI"):
    global _telegram_app
    _telegram_app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )
    _telegram_app.add_handler(CommandHandler("status", cmd_status))
    _telegram_app.add_handler(CommandHandler("testar_solver", cmd_testar_solver))
    _telegram_app.add_handler(CommandHandler("testar_autonomia", cmd_testar_solver))
    _telegram_app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))

    await _telegram_app.initialize()
    await _telegram_app.start()

    # Polling em vez de webhook — mais simples e sem dependência de URL pública
    await _telegram_app.updater.start_polling(drop_pending_updates=False)
    audit("TELEGRAM", "Polling iniciado")

    task = asyncio.create_task(heartbeat_loop(_telegram_app), name="heartbeat_loop")
    task.add_done_callback(_task_error_handler)

    yield

    await _telegram_app.updater.stop()
    await _telegram_app.stop()
    await _telegram_app.shutdown()


llm_api = FastAPI(lifespan=lifespan)


@llm_api.get("/health")
async def health():
    return {"status": "ok", "service": "morgan-ceo"}


@llm_api.post("/telegram/webhook")
async def telegram_webhook(request: FastAPIRequest):
    try:
        data = await request.json()
        update = Update.de_json(data, _telegram_app.bot)
        await _telegram_app.process_update(update)
    except Exception as e:
        audit("WEBHOOK_ERRO", str(e))
        import traceback
        audit("WEBHOOK_TRACEBACK", traceback.format_exc()[:500])
    return {"ok": True}


@llm_api.post("/morgan/responder")
async def morgan_responder(request: FastAPIRequest):
    """Ferramenta chamada pelo ElevenLabs ConvAI — corre o Morgan real."""
    body = await request.json()
    user_msg = body.get("mensagem", "") or body.get("message", "") or body.get("query", "")
    if not user_msg:
        return {"resposta": "Não percebi a mensagem."}
    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(None, get_morgan_reply, "desktop", user_msg)
    return {"resposta": reply}


@llm_api.post("/v1/chat/completions")
async def custom_llm(request: FastAPIRequest):
    body = await request.json()
    messages = body.get("messages", [])

    # Extrair última mensagem do utilizador
    user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                user_msg = content
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_msg = part.get("text", "")
                        break
            break

    if not user_msg:
        return JSONResponse({
            "id": "chatcmpl-morgan",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}]
        })

    # Correr Morgan brain em executor (chamada síncrona)
    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(None, get_morgan_reply, "desktop", user_msg)

    if body.get("stream", False):
        async def stream():
            chunk = {
                "id": "chatcmpl-morgan",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": reply}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            done = {
                "id": "chatcmpl-morgan",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(done)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(stream(), media_type="text/event-stream")

    return {
        "id": "chatcmpl-morgan",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}]
    }




def main():
    print("Morgan — online (conversa + heartbeat + Tier 6 + LLM API)")
    print("Kill switch: envia 'morgan pausa' / 'morgan continua' no Telegram")
    print("Ctrl+C para terminar.")
    port = int(os.getenv("PORT", 8000))
    print(f"LLM API + Telegram webhook na porta {port}")
    uvicorn.run(llm_api, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    main()
