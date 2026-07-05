import os
import json
import time
import logging
import asyncio
import tempfile
import threading
from datetime import date, datetime
from dotenv import load_dotenv
import yaml
from telegram import Update
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
from memory_store import load_memory
from conversation_store import get_context_messages, save_message

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
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

# Logging
logging.basicConfig(level=logging.WARNING)
audit_handler = logging.FileHandler(AUDIT_FILE)
audit_handler.setLevel(logging.INFO)
audit_logger = logging.getLogger("morgan.audit")
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

FONTES_CREDÍVEIS = ["record.pt", "abola.pt", "ojogo.pt", "maisfutebol.iol.pt", "zerozero.pt", "sporttv.pt", "rtp.pt", "cmjornal.pt", "sapo.pt"]

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
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


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
    hora = datetime.now().hour
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


# ── Prompts ──────────────────────────────────────────────────────────────────

def build_system_prompt() -> str:
    TODAY = date.today().strftime("%d de %B de %Y")
    return f"""O teu nome é Morgan. És o assistente pessoal de confiança do Vasco Botelho da Costa — treinador do Moreirense FC.

A data de hoje é {TODAY}. Usa sempre esta data. Quando pesquisares, inclui sempre 2026 nas queries.

Tom: firme e direto no trabalho, compreensivo e de apoio quando necessário. Sempre em português europeu. Trata o Vasco pelo primeiro nome. Nunca uses emojis — zero emojis em qualquer resposta. Sem excessos de pontuação ou entusiasmo artificial.

Tens acesso a ferramentas para pesquisar na web, obter dados da Primeira Liga, e gerir a tua memória.

## O que sabes sobre o Vasco:
{load_memory()}

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
    TODAY = date.today().strftime("%d de %B de %Y")
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
            system=build_system_prompt(),
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

        if len(history) > 100:
            conversation_histories[user_id] = history[-100:]

        return reply


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
            system=build_scout_conversational_system(),
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

    # Mudança para Scout — explícita ou por tópico
    if _quer_scout(user_message) and agente_ativo.get(uid, "ceo") == "ceo":
        agente_ativo[uid] = "scout"
        return get_scout_reply(uid, user_message)

    # Mudança para Solver — explícita ou por tópico técnico
    if _quer_solver(user_message) and agente_ativo.get(uid, "ceo") == "ceo":
        agente_ativo[uid] = "solver"
        return get_solver_reply(uid, user_message)

    agente = agente_ativo.get(uid, "ceo")

    if agente == "scout":
        return get_scout_reply(uid, user_message)
    if agente == "solver":
        return get_solver_reply(uid, user_message)
    return get_morgan_reply(uid, user_message)


def build_solver_system() -> str:
    TODAY = date.today().strftime("%d de %B de %Y")
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

## Como ages:
- Diagnostica problemas com base no audit log e no que o Vasco te descreve
- Pesquisa online soluções para erros específicos quando necessário
- Propõe correções concretas com código ou passos claros
- NUNCA modificas código nem fazes deploy sem aprovação explícita do Vasco
- Se identificares um problema crítico que o Vasco não mencionou, alerta-o"""


def get_solver_reply(user_id: str, user_message: str) -> str:
    """Conversa direta com o Morgan Solver."""
    sid = "solver"

    if sid not in solver_histories:
        solver_histories[sid] = get_context_messages(sid)

    history = solver_histories[sid]
    history.append({"role": "user", "content": user_message})
    save_message(sid, "user", user_message)
    audit("SOLVER_MENSAGEM", user_message[:100])

    config = load_config()
    modelo = config.get("modelo", "claude-sonnet-4-6")

    while True:
        response = anthropic_client.messages.create(
            model=modelo,
            max_tokens=1024,
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

        if len(history) > 60:
            solver_histories[sid] = history[-60:]

        return reply


def _quer_solver(msg: str) -> bool:
    m = msg.lower()
    if "solver" in m:
        return True
    keywords = ["erro", "bug", "partido", "não funciona", "nao funciona", "problema técnico",
                "falha", "crash", "deploy", "railway", "código", "codigo", "corrigir", "fix"]
    return any(k in m for k in keywords)


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
    agora = datetime.now()
    if agora.weekday() != 6 or agora.hour != 20:
        return False
    state = load_state()
    chave = f"scout_{agora.strftime('%Y-%W')}"
    return not state.get(chave, False)


def mark_scout_done():
    agora = datetime.now()
    chave = f"scout_{agora.strftime('%Y-%W')}"
    state = load_state()
    state[chave] = True
    save_state(state)


def should_run_briefing() -> bool:
    """Verifica se está na hora do briefing (7h ou 20h) e se ainda não foi enviado hoje."""
    agora = datetime.now()
    hora = agora.hour
    if hora not in (7, 20):
        return False
    state = load_state()
    chave = f"briefing_{agora.strftime('%Y-%m-%d_%H')}"
    return not state.get(chave, False)


def mark_briefing_done():
    agora = datetime.now()
    chave = f"briefing_{agora.strftime('%Y-%m-%d_%H')}"
    state = load_state()
    state[chave] = True
    save_state(state)


def build_scout_conversational_system() -> str:
    TODAY = date.today().strftime("%d de %B de %Y")
    contexto_historico = get_contexto_scout()
    memoria_vasco = load_memory()
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

## Como respondes em conversação:
- Responde diretamente às perguntas do Vasco com base no teu histórico
- Usa as ferramentas de pesquisa apenas quando precisares de dados atuais
- Não corras todas as ferramentas automaticamente — só quando fizer sentido
- Sê conciso e útil"""


def build_scout_system() -> str:
    TODAY = date.today().strftime("%d de %B de %Y")
    contexto_historico = get_contexto_scout()
    return f"""És o Morgan AI Scout — o agente de inteligência de mercado do Vasco Botelho da Costa.
A data de hoje é {TODAY}.

Tom: direto e analítico. Sempre em português europeu. Sem emojis. Sem rodeios.
Reportas ao Morgan CEO e falas diretamente com o Vasco quando ele te invocar.
Quando o Vasco fizer perguntas sobre oportunidades, negócios, mercados ou rendimento passivo, responde com base no teu histórico e faz pesquisas adicionais se necessário.
Para voltar ao Morgan CEO, o Vasco diz "volta ao Morgan".

## Objectivo do Vasco — marcos progressivos de rendimento passivo:
- M1: €1.000/mês — primeiro negócio a funcionar
- M2: €3.000/mês — rendimento real
- M3: €10.000/mês — liberdade financeira base
- M4: €25.000/mês — primeiro império a escalar
- M5: €50.000/mês — múltiplos Morgans a operar
- M6: Sem teto — o Scout continua, o império continua a crescer

## Histórico acumulado — usa isto para identificar tendências:
{contexto_historico}

## Tarefa:
Usa SEMPRE estas ferramentas antes de produzir o relatório:
1. `product_hunt_trending` — produtos de IA mais votados esta semana
2. `hacker_news_trending` — tendências da comunidade tech
3. `reddit_trending` — conversas de empreendedores e criadores
4. `scout_oportunidades` — pesquisa de mercado ampla
5. `indiehackers_trending` — valida quais as oportunidades com receita REAL declarada por fundadores (dados honestos)
6. `google_trends` — valida as top 3 oportunidades que identificares (confirma se o interesse está a crescer)
7. `monitorizar_oportunidades_aprovadas` — OBRIGATÓRIO se houver oportunidades aprovadas no histórico acima. Faz pesquisa aprofundada sobre cada uma e inclui os resultados no relatório numa secção separada "Acompanhamento aprovadas".

Cruza os resultados com o histórico acima. Produz um relatório estruturado com:

1. **Top 3 oportunidades desta semana** — para cada uma:
   - Nome e descrição
   - Potencial de receita estimado (€/mês)
   - Esforço inicial (baixo/médio/alto)
   - Concorrência (baixa/média/alta)
   - Automação com IA (%)
   - Adequação PT/BR/ES
   - Se já apareceu em semanas anteriores: quantas vezes e o que mudou
   - Próximo passo concreto para começar

2. **Sinal mais forte do histórico** — a oportunidade que apareceu mais vezes e porquê merece atenção agora (omite se for a primeira semana)

3. **Tendência da semana** — o movimento mais relevante no mercado de IA

4. **Proposta de novo Morgan** — se identificares algo que justifique um agente especializado

No final, lista as 3 oportunidades num bloco JSON para registo interno:
```json
[
  {{"nome": "...", "descricao": "...", "receita_estimada": "...", "notas": "..."}},
  {{"nome": "...", "descricao": "...", "receita_estimada": "...", "notas": "..."}},
  {{"nome": "...", "descricao": "...", "receita_estimada": "...", "notas": "..."}}
]
```

Sê direto e concreto. Dados reais, não generalidades. O Vasco decide — o Scout informa com máxima fiabilidade."""


async def run_scout_report(app):
    """Gera e envia o relatório semanal do Morgan AI Scout."""
    config = load_config()
    modelo = config.get("modelo", "claude-sonnet-4-6")
    messages = [{"role": "user", "content": "Gera o relatório semanal de oportunidades de negócio com IA."}]

    while True:
        response = anthropic_client.messages.create(
            model=modelo,
            max_tokens=2048,
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
            audit("SCOUT_MEMORIA", f"{len(oportunidades)} oportunidades registadas")
        except Exception as e:
            audit("SCOUT_MEMORIA_ERRO", str(e))

    # Remove o bloco JSON do relatório antes de enviar ao Vasco
    relatorio_limpo = re.sub(r"```json\s*\[.*?\]\s*```", "", relatorio, flags=re.DOTALL).strip()

    header = "🔍 *Morgan AI Scout — Relatório Semanal*\n\n"
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=header + relatorio_limpo,
        parse_mode="Markdown"
    )
    audit("SCOUT_RELATORIO", "Relatório semanal enviado")


async def heartbeat_loop(app):
    await asyncio.sleep(10)
    audit("HEARTBEAT", "Iniciado — briefings às 7h e 20h, scout aos domingos às 20h")

    while True:
        try:
            if is_pausado():
                await asyncio.sleep(60)
                continue

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
            hora_atual = datetime.now().hour
            audit("HEARTBEAT", f"Briefing das {hora_atual}h iniciado")

            for check in get_checks_for_hour(hora_atual):
                nome = check["nome"]
                prefixo = PREFIXOS.get(nome, "Vasco")

                audit("HEARTBEAT_CHECK", nome)
                resultado = run_heartbeat_check(check)

                if resultado:
                    mensagem = f"{prefixo}, tenho isto para te dizer:\n\n{resultado}"
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=mensagem,
                        parse_mode="Markdown"
                    )
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


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status — mostra o estado atual do Morgan."""
    config = load_config()
    pausado = config.get("pausado", False)
    modelo = config.get("modelo", "claude-sonnet-4-6")
    silencio_i = config.get("silencio_inicio", 23)
    silencio_f = config.get("silencio_fim", 7)
    hora_atual = datetime.now().hour
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

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


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
            if any(p in texto for p in ("sim", "s", "yes", "confirmo", "vai", "prossegue", "faz")):
                del pending_confirmations[user_id]
                audit("CONFIRMACAO_ACEITE", acao)
                reply = get_morgan_reply(user_id, f"O Vasco confirmou. Prossegue com: {acao}")
                await update.message.reply_text(reply, parse_mode="Markdown")
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
            await update.message.reply_text(f"_{user_message}_", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Erro ao transcrever áudio: {e}")
            return
    else:
        user_message = update.message.text

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


async def post_init(app):
    asyncio.create_task(heartbeat_loop(app))


# ── Custom LLM API — para ElevenLabs ConvAI (desktop) ───────────────────────

llm_api = FastAPI()


@llm_api.get("/health")
async def health():
    return {"status": "ok", "service": "morgan-ceo"}


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


def start_llm_api():
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(llm_api, host="0.0.0.0", port=port, log_level="warning")


def main():
    print("Morgan — online (conversa + heartbeat + Tier 6 + LLM API)")
    print("Kill switch: envia 'morgan pausa' / 'morgan continua' no Telegram")
    print("Ctrl+C para terminar.")

    # Arrancar API do LLM custom em thread separada
    api_thread = threading.Thread(target=start_llm_api, daemon=True)
    api_thread.start()
    print(f"LLM API ativa na porta {os.getenv('PORT', 8000)}")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).post_init(post_init).build()
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
