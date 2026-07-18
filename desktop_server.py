"""
Morgan Desktop Server — FastAPI local (porta 8765)
Serve a interface JARVIS e liga ao mesmo cérebro do Morgan (Claude + tools + memória).
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Garantir que imports do Morgan funcionam
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import sentry_sdk
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        enable_logs=True,
        send_default_pii=False,
    )

from fastapi import FastAPI, UploadFile, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import anthropic

from tools import TOOLS, TOOL_FUNCTIONS
from memory_store import load_memory
from scout_memory import _load as load_scout
from conversation_store import get_context_messages, save_message as store_save
from voice_id import enroll_voice, is_vasco, has_profile, load_profile
from coach_agent import get_coach_reply
from cfo_agent import get_cfo_reply
from marketeer_agent import get_marketeer_reply
from operator_agent import get_operator_reply
from trading_bot import get_status as get_bot_status
from push_service import save_subscription, send_push, VAPID_PUBLIC_KEY
from mem0_service import mem0_get, mem0_add, mem0_collective_get
from config_service import is_pausado, pausar, retomar, hora_silencio, modelo as cfg_modelo, confianca_limiar
from morgan_logging import configure as _configure_logging, get_logger as _get_logger

# Logging estruturado + Sentry (se SENTRY_DSN definido)
_configure_logging()
_log = _get_logger("desktop_server")

# Pré-carregar perfil de voz se existir
load_profile()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_SECRET_KEY = os.getenv("HUME_SECRET_KEY")
HUME_VOICE_ID = os.getenv("HUME_VOICE_ID")
CONVAI_AGENT_ID = "agent_0001kwqq04nbe689bpxdtp2dkpc7"
DESKTOP_USER_ID = "vasco"

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
app = FastAPI()
DESKTOP_DIR = Path(__file__).parent / "desktop"

# Histórico de conversa — carregado do disco ao arrancar, persiste entre sessões
conversation_history: list[dict] = get_context_messages(DESKTOP_USER_ID)

def _mem0_guardar_se_relevante(user_text: str, reply: str):
    """Guarda no Qdrant em background. Haiku extrai só os factos relevantes antes de guardar."""
    try:
        import threading
        threading.Thread(
            target=mem0_add,
            args=("vasco", [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]),
            daemon=True
        ).start()
    except Exception:
        pass


def get_system_prompt(query: str = "") -> str:
    memoria = load_memory()
    agora = datetime.now().strftime("%d de %B de %Y, %H:%M")

    # Camada 3 — memória semântica (Qdrant)
    contexto = memoria
    try:
        from mem0_service import get_agent_context
        mem_semantica = get_agent_context("ceo", query or "Morgan CEO decisões Vasco BCVertex")
        if mem_semantica:
            contexto = memoria + "\n\n[Memórias relevantes]\n" + mem_semantica
    except Exception:
        pass

    # Camada 2 — contexto episódico recente (últimos 10 eventos do sistema)
    try:
        from episodic_memory import get_eventos_recentes
        eventos = get_eventos_recentes(limite=10)
        if eventos:
            linhas = []
            for ev in reversed(eventos):
                ts = ev.get("ts", "")[:10]
                ag = ev.get("agente", "?")
                conteudo = ev.get("conteudo", "")[:100]
                linhas.append(f"[{ts}] {ag}: {conteudo}")
            contexto += "\n\n[Histórico recente do sistema]\n" + "\n".join(linhas)
    except Exception:
        pass

    limiar = confianca_limiar()
    return f"""És o Morgan CEO — orquestrador do império BCVertex e braço direito do Vasco Botelho da Costa.
Data e hora: {agora}
Limiar de confiança: {limiar}%

{contexto}

## IDENTIDADE E PAPEL
- Coordenas 7 agentes: Scout, Coach, CFO, Creator, Solver, Operator, Marketeer.
- O teu trabalho é pensar, orquestrar, sintetizar e recomendar — nunca decidir unilateralmente em assuntos irreversíveis.
- A última decisão é sempre do Vasco. Prepara, recomenda, executa dentro dos limites definidos.

## LÍNGUA E TOM
- Sempre PT-PT. Nunca inglês. Nunca mistures línguas.
- Directo, conciso, sem rodeios. Sem markdown na conversa — fala como se estivesses ao telefone.
- Sem sumários no final. Sem frases de preenchimento ("claro", "com certeza", "óptima questão").
- Máximo 3 opções quando apresentas alternativas, sempre com recomendação clara.

## ORQUESTRAÇÃO — COMO DELEGAR
Quando delegas a um agente, define sempre:
1. Objectivo: o que precisas que o agente descubra ou faça
2. Output esperado: formato e nível de detalhe da resposta
3. Fronteira: o que o agente NÃO deve cobrir
4. Critério de aceitação: como sabes que a resposta é suficientemente boa

Separação de domínios (nunca misturar):
- Coach = futebol e táctica exclusivamente
- CFO = trading, finanças, capital exclusivamente
- Scout = oportunidades de negócio e inteligência de mercado
- Creator = código, novos agentes, automações
- Solver = diagnóstico e resolução de problemas técnicos
- Operator = gestão de negócios activos (Etsy, directórios)
- Marketeer = aquisição de clientes, SEO, outreach

## ORQUESTRAÇÃO — COMO SINTETIZAR
Quando recebes respostas de múltiplos agentes:
- Avalia cada resposta: PASS (usa directamente) / FIX (reenviar com falha identificada) / ESCALATE (leva ao Vasco)
- Se dois agentes devolverem informação contraditória, explica o conflito ao Vasco antes de agir
- Confiança em cadeia degrada: se delegaste a 2+ agentes, a tua confiança final é conservadora

## REGRA DE CONFIANÇA (obrigatória)
- Antes de qualquer acção consequente, avalia internamente a tua confiança de 0 a 100%.
- Confiança ≥ {limiar}%: age e informa o resultado directamente.
- Confiança < {limiar}%: NÃO ages. Diz "Confiança [X]% — preciso da tua confirmação" e explica a dúvida.
- Nunca inventes factos. Se não souberes, diz "não tenho a certeza".

## ACÇÕES IRREVERSÍVEIS — CONFIRMAÇÃO SEMPRE OBRIGATÓRIA
Nunca executes sem confirmação explícita do Vasco, independente da confiança:
- Enviar emails ou mensagens para fora do sistema Morgan
- Gastar ou mover dinheiro real (inclui alterar parâmetros do trading bot)
- Alterar código em produção ou fazer deploy
- Apagar dados, ficheiros ou memórias
- Publicar conteúdo público em nome do Vasco

## ESCALADA AO VASCO
Formato obrigatório ao escalar:
- Situação: [o que está a acontecer]
- Recomendação: [o que propões]
- Risco se não agires: [consequência]
- Alternativas: [máx 2 outras opções]

Escala imediatamente (sem esperar pedido) quando:
- CFO reporta drawdown >5% dia ou >15% total
- Operator reporta queda de vendas >30% em qualquer negócio
- Dois ou mais agentes reportam problema em simultâneo no mesmo negócio
- Qualquer agente retorna erro crítico numa acção irreversível

## BRIEFINGS — FORMATO PADRÃO
Reporta apenas o que mudou desde o último briefing.
Formato por área: [Agente]: [status em 1 linha] | [novidade ou "sem novidades"]
No final: [recomendação de prioridade do dia, se houver]

## MEMÓRIA
- Semântica (Qdrant) + episódica (histórico de eventos) + procedural (estas regras) injectadas acima.
- Usa a memória para não repetir o que já foi dito e manter contexto entre sessões."""


def run_tool(tool_name: str, tool_input: dict) -> str:
    fn = TOOL_FUNCTIONS.get(tool_name)
    if not fn:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        return str(fn(**tool_input))
    except Exception as e:
        return f"Erro em {tool_name}: {e}"


# ── Escalada de confiança ─────────────────────────────────────────────────────

def escalada_push(agente: str, situacao: str, confianca: int, opcoes: list[str] = None):
    """Envia push ao Vasco quando um agente tem confiança < 90% e precisa de decisão."""
    opcoes_str = ""
    if opcoes:
        opcoes_str = " | Opções: " + " / ".join(opcoes)
    corpo = f"[{agente}] Confiança {confianca}% — {situacao}{opcoes_str}"
    send_push(
        title=f"Morgan precisa de ti — {agente}",
        body=corpo[:200],
        url="/pwa/"
    )
    # Registar no audit log
    audit_file = Path(__file__).parent / "memory" / "audit.log"
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            from datetime import datetime as _dt
            f.write(f"[{_dt.now().isoformat()}] ESCALADA {agente} conf={confianca}%: {situacao}\n")
    except Exception:
        pass


@app.get("/health")
async def health():
    """Health check — usado pelo Creator para verificar deploys e pelo launchd para monitorizar."""
    import time as _t
    return JSONResponse({
        "status": "ok",
        "uptime_s": int(_t.time() - _HEARTBEAT_START),
        "agents": list(_desktop_agent.keys()),
        "pausado": is_pausado(),
        "modelo": cfg_modelo(),
    })


@app.post("/api/control/pause")
async def api_pause():
    pausar()
    return JSONResponse({"ok": True, "pausado": True})

@app.post("/api/control/resume")
async def api_resume():
    retomar()
    return JSONResponse({"ok": True, "pausado": False})

@app.get("/api/control/status")
async def api_control_status():
    from config_service import load_config
    c = load_config()
    return JSONResponse({
        "pausado": c.get("pausado", False),
        "modelo": c.get("modelo", "claude-sonnet-4-6"),
        "silencio_inicio": c.get("silencio_inicio", 23),
        "silencio_fim": c.get("silencio_fim", 7),
        "confianca_limiar": c.get("confianca_limiar", 90),
    })

@app.post("/api/escalada")
async def api_escalada(request: Request):
    """Endpoint interno para agentes enviarem escaladas ao Vasco via push."""
    body = await request.json()
    escalada_push(
        agente=body.get("agente", "CEO"),
        situacao=body.get("situacao", ""),
        confianca=body.get("confianca", 0),
        opcoes=body.get("opcoes", []),
    )
    return JSONResponse({"ok": True})


# ─── BARGE-IN — processo de áudio atual ──────────────
current_player: asyncio.subprocess.Process | None = None


async def kill_player():
    global current_player
    if current_player and current_player.returncode is None:
        try:
            current_player.kill()
            await current_player.wait()
        except Exception:
            pass
    current_player = None


async def play_audio_bytes(audio_bytes: bytes) -> bool:
    """Toca bytes MP3 com afplay. Retorna False se interrompido."""
    global current_player
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        current_player = await asyncio.create_subprocess_exec(
            "afplay", tmp_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await current_player.wait()
        completed = current_player.returncode == 0
    except Exception:
        completed = False
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return completed


def split_sentences(text: str) -> list[str]:
    """Divide texto em frases prontas para TTS."""
    import re
    parts = re.split(r'(?<=[.!?…])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


VOICE_SETTINGS = {
    "stability": 0.35,
    "similarity_boost": 0.98,
    "style": 0.35,
    "use_speaker_boost": True,
    "speed": 0.70,
}


async def elevenlabs_sentence(text: str) -> bytes | None:
    """Gera áudio ElevenLabs para uma frase."""
    try:
        from elevenlabs import ElevenLabs
        from elevenlabs.types import VoiceSettings
        el = ElevenLabs(api_key=ELEVENLABS_KEY)
        chunks = []
        for chunk in el.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=VOICE_SETTINGS["stability"],
                similarity_boost=VOICE_SETTINGS["similarity_boost"],
                style=VOICE_SETTINGS["style"],
                use_speaker_boost=VOICE_SETTINGS["use_speaker_boost"],
                speed=VOICE_SETTINGS["speed"],
            ),
        ):
            chunks.append(chunk)
        return b"".join(chunks)
    except Exception as e:
        print(f"ElevenLabs erro: {e}")
        return None


async def say_sentence(text: str):
    """Fallback: say macOS."""
    import subprocess
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: subprocess.run(["say", "-v", "Joana", text])
    )


# ─── Routing de agentes — Haiku mini-classifier ──────────────────────────────

_ROUTER_SYSTEM = """És um classificador de intenções para o assistente Morgan.
Analisa a mensagem e responde APENAS com um destes labels (sem mais texto):
  solver     — erros, bugs, crashes, CI falhou, sistema não arranca, problema técnico, debugging, logs, fix
  cfo        — finanças, trading, BTC, capital, PnL, drawdown, Binance
  coach      — futebol, táticas, treino, Moreirense, adversário, plantel, jogadores
  marketeer  — marketing, outreach, leads, campanhas, Etsy, copywriting, Pinterest, email frio, crescimento
  operator   — estado das lojas, operações diárias, receita total, PlannerAtlas, directórios
  scout      — oportunidades de negócio, SaaS, rendimento passivo, startups, nicho, mercado
  ceo        — tudo o resto (conversa geral, tarefas, perguntas pessoais, status)
Responde apenas com o label. Nenhuma outra palavra."""

_haiku_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

def _classificar_agente(msg: str) -> str:
    """Usa Claude Haiku para classificar para qual agente encaminhar a mensagem."""
    m = msg.lower()
    if any(k in m for k in ["morgan ceo", "volta ao morgan", "morgan principal"]):
        return "ceo"
    for agente in ("solver", "cfo", "coach", "marketeer", "operator", "scout"):
        if m.strip().startswith(agente) or f"[{agente}]" in m:
            return agente

    try:
        r = _haiku_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=_ROUTER_SYSTEM,
            messages=[{"role": "user", "content": msg[:400]}],
        )
        label = r.content[0].text.strip().lower().split()[0]
        if label in ("solver", "cfo", "coach", "marketeer", "operator", "scout", "ceo"):
            return label
    except Exception:
        pass

    # Fallback keyword simples se Haiku falhar
    if any(k in m for k in ["erro", "bug", "crash", "falhou", "não arranca", "fix", "log", "ci "]):
        return "solver"
    if any(k in m for k in ["btc", "trading", "pnl", "financeiro", "capital"]):
        return "cfo"
    if any(k in m for k in ["moreirense", "treino", "tático", "adversário"]):
        return "coach"
    if any(k in m for k in ["etsy", "lead", "campanha", "marketing"]):
        return "marketeer"
    if any(k in m for k in ["operações", "planneratlas", "receita total"]):
        return "operator"
    if any(k in m for k in ["oportunidade", "rendimento passivo", "startup"]):
        return "scout"
    return "ceo"

def _chat_ceo(user_text: str) -> str:
    """CEO — chamada direta ao Claude com ferramentas."""
    conversation_history.append({"role": "user", "content": user_text})
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=get_system_prompt(user_text),
        tools=TOOLS,
        messages=conversation_history[-50:],
    )
    while response.stop_reason == "tool_use":
        tool_results = []
        assistant_content = list(response.content)
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        conversation_history.append({"role": "assistant", "content": assistant_content})
        conversation_history.append({"role": "user", "content": tool_results})
        response = claude.messages.create(
            model="claude-sonnet-4-6", max_tokens=2048,
            system=get_system_prompt(user_text), tools=TOOLS,
            messages=conversation_history[-50:],
        )
    reply = "".join(block.text for block in response.content if hasattr(block, "text"))
    conversation_history.append({"role": "assistant", "content": reply})
    # Guardar no Mem0 apenas trocas com decisões ou factos novos (poupar quota)
    _mem0_guardar_se_relevante(user_text, reply)

    # Camada 2 — episódica
    try:
        from episodic_memory import registar_evento
        registar_evento("ceo", "conversa", f"Q: {user_text[:100]} | R: {reply[:200]}")
    except Exception:
        pass

    return reply

# Agente ativo por sessão desktop
_desktop_agent = {"current": "ceo"}

def chat_with_morgan(user_text: str) -> str:
    store_save(DESKTOP_USER_ID, "user", user_text)

    msg_lower = user_text.lower()

    # Kill switch — pausa/retoma
    if any(k in msg_lower for k in ["pausa morgan", "morgan pausa", "pausar morgan", "morgan pausar"]):
        pausar()
        reply = "Morgan pausado. Não enviarei notificações nem agirei autonomamente até retomares. Diz 'retoma Morgan' para reativar."
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if any(k in msg_lower for k in ["retoma morgan", "morgan retoma", "reativa morgan", "unpause"]):
        retomar()
        reply = "Morgan reativado. Briefings, heartbeat e agentes voltam ao normal."
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Bloquear respostas autónomas se pausado (mas responde ao Vasco na conversa)
    if is_pausado() and not any(k in msg_lower for k in ["status", "estado", "pausado"]):
        reply = "Estou pausado — respondo mas não ajo autonomamente. Diz 'retoma Morgan' para reativar."
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Aprovação / rejeição de oportunidades Scout
    import re as _re
    _m_aprovo = _re.match(r"^aprovo?\s+(.+)$", msg_lower.strip())
    _m_rejeito = _re.match(r"^rejeito?\s+(.+)$", msg_lower.strip())
    if _m_aprovo:
        nome_op = _m_aprovo.group(1).strip()
        try:
            from approval_pipeline import executar_oportunidade_aprovada
            reply = executar_oportunidade_aprovada(nome_op, f"Aprovado pelo Vasco: {nome_op}")
        except Exception as e:
            reply = f"Erro ao aprovar: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if _m_rejeito:
        nome_op = _m_rejeito.group(1).strip()
        try:
            from scout_memory import arquivar_oportunidade
            arquivar_oportunidade(nome_op)
            reply = f"Oportunidade '{nome_op}' arquivada."
        except Exception:
            reply = f"Oportunidade '{nome_op}' marcada como rejeitada."
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Reset explícito para CEO
    if any(k in msg_lower for k in ["morgan ceo", "volta ao morgan", "ceo", "morgan principal"]):
        _desktop_agent["current"] = "ceo"
        reply = "Morgan CEO de volta. Em que posso ajudar?"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Routing por intenção — Haiku mini-classifier
    agente_alvo = _classificar_agente(user_text)
    _desktop_agent["current"] = agente_alvo

    if agente_alvo == "cfo":
        try:
            reply = "[CFO] " + get_cfo_reply(user_text)
        except Exception as e:
            reply = f"[CFO] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if agente_alvo == "coach":
        try:
            reply = "[COACH] " + get_coach_reply(user_text)
        except Exception as e:
            reply = f"[COACH] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if agente_alvo == "marketeer":
        try:
            reply = "[MARKETEER] " + get_marketeer_reply(user_text)
        except Exception as e:
            reply = f"[MARKETEER] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if agente_alvo == "operator":
        try:
            reply = "[OPERATOR] " + get_operator_reply(user_text)
        except Exception as e:
            reply = f"[OPERATOR] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Solver — problemas técnicos, erros, bugs, CI
    if agente_alvo == "solver":
        _desktop_agent["current"] = "solver"
        try:
            from solver_graph import run_solver
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                reply_body = pool.submit(run_solver, user_text).result(timeout=120)
        except Exception as e:
            reply_body = f"[Solver indisponível: {e}]"
        reply = "[SOLVER] " + reply_body
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Scout — agente standalone com quality gate
    if agente_alvo == "scout":
        _desktop_agent["current"] = "scout"
        try:
            from scout_agent import get_scout_reply
            reply_body = get_scout_reply(user_text)
        except Exception as e:
            reply_body = f"[Scout indisponível: {e}]"
        reply = "[SCOUT] " + reply_body
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Agente persistente da sessão
    agente = _desktop_agent.get("current", "ceo")
    if agente == "cfo":
        try:
            reply = "[CFO] " + get_cfo_reply(user_text)
        except Exception as e:
            reply = f"[CFO] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply
    if agente == "coach":
        try:
            reply = "[COACH] " + get_coach_reply(user_text)
        except Exception as e:
            reply = f"[COACH] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if agente == "marketeer":
        try:
            reply = "[MARKETEER] " + get_marketeer_reply(user_text)
        except Exception as e:
            reply = f"[MARKETEER] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # CEO (default)
    reply = _chat_ceo(user_text)
    store_save(DESKTOP_USER_ID, "assistant", reply)
    return reply


def _chat_ceo_with_system(user_text: str, system: str) -> str:
    """CEO com system prompt customizado (ex: Scout mode)."""
    msgs = conversation_history[-28:] + [{"role": "user", "content": user_text}]
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        tools=TOOLS,
        messages=msgs,
    )
    while response.stop_reason == "tool_use":
        tool_results = []
        assistant_content = list(response.content)
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        msgs.append({"role": "assistant", "content": assistant_content})
        msgs.append({"role": "user", "content": tool_results})
        response = claude.messages.create(
            model="claude-sonnet-4-6", max_tokens=2048,
            system=system, tools=TOOLS, messages=msgs,
        )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


PWA_DIR = Path(__file__).parent / "pwa"

@app.get("/")
async def serve_interface(request: Request):
    ua = request.headers.get("user-agent", "").lower()
    is_mobile = any(k in ua for k in ["iphone", "android", "mobile", "ipad"])
    if is_mobile:
        return RedirectResponse(url="/app/", status_code=302)
    desktop_file = DESKTOP_DIR / "index_v2.html"
    if desktop_file.exists():
        return FileResponse(desktop_file)
    return RedirectResponse(url="/app/", status_code=302)

@app.get("/v2")
@app.get("/v2/")
async def serve_interface_v2():
    return FileResponse(DESKTOP_DIR / "index_v2.html")

_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}

from fastapi.responses import RedirectResponse

# /pwa/* redireciona para /app/* (URL nova sem cache no browser)
@app.get("/pwa/")
@app.get("/pwa/index.html")
async def redirect_pwa_root():
    return RedirectResponse("/app/", status_code=302)

@app.get("/pwa/{filename}")
async def redirect_pwa_file(filename: str):
    return RedirectResponse(f"/app/{filename}", status_code=302)

# /app/ — URL principal da PWA (nunca esteve em cache)
@app.get("/app/")
@app.get("/app/index.html")
async def serve_app():
    return FileResponse(PWA_DIR / "index.html", headers=_NO_CACHE)

@app.get("/app/{filename}")
async def serve_app_file(filename: str):
    f = PWA_DIR / filename
    return FileResponse(f if f.exists() else PWA_DIR / "index.html", headers=_NO_CACHE)


@app.get("/api/widgets")
async def get_widgets():
    agora = datetime.now()

    # Tempo
    weather_text = "--°C"
    weather_desc = ""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://wttr.in/Moreira+de+Conegos?format=%t|%C", timeout=4)
            parts = r.text.strip().split("|")
            weather_text = parts[0].strip() if parts else "--°C"
            weather_desc = parts[1].strip() if len(parts) > 1 else ""
    except Exception:
        pass

    # Scout
    import re as _re
    scout_data = load_scout()
    total_ops = len(scout_data.get("oportunidades", {}))
    aprovadas = len(scout_data.get("aprovadas", []))
    recorrentes = [
        nome for nome, info in scout_data.get("oportunidades", {}).items()
        if info.get("vezes_visto", 0) >= 2
    ]

    def _short_nome(nome: str) -> str:
        abrevs = {
            "directório": "Dir.", "micro-saas": "SaaS", "micro": "SaaS",
            "relatórios": "Relat", "produtos": "Tmpl", "compra": "Blog",
        }
        first = nome.split()[0].lower().rstrip(",.")
        return abrevs.get(first, nome[:5])

    def _score(info: dict) -> int:
        for nota in info.get("notas", []):
            m = _re.search(r"(\d+)\s+fonte", nota)
            if m:
                return min(92, int(m.group(1)) * 20 + 20)
        return 60 + info.get("vezes_visto", 1) * 5

    top_ops = sorted(
        [{"label": _short_nome(n), "score": _score(i), "nome": n}
         for n, i in scout_data.get("oportunidades", {}).items()],
        key=lambda x: -x["score"]
    )[:3]

    # Próximo jogo Moreirense
    proximo_jogo = {"adversario": "--", "data": "--", "competicao": "--"}
    ultimo_resultado = {"adversario": "--", "resultado": "--"}
    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        async with httpx.AsyncClient() as c:
            r = await c.get(
                "https://v3.football.api-sports.io/fixtures",
                params={"team": 229, "next": 1, "season": 2026},
                headers=headers, timeout=5
            )
            data = r.json()
            if data.get("response"):
                f = data["response"][0]
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                adversario = away if home == "Moreirense" else home
                data_jogo = f["fixture"]["date"][:10]
                hora_jogo = f["fixture"]["date"][11:16]
                proximo_jogo = {
                    "adversario": adversario,
                    "data": f"{data_jogo} {hora_jogo}",
                    "competicao": f["league"]["name"],
                    "casa": home == "Moreirense",
                }
    except Exception:
        pass

    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        async with httpx.AsyncClient() as c:
            r = await c.get(
                "https://v3.football.api-sports.io/fixtures",
                params={"team": 229, "last": 1, "season": 2026},
                headers=headers, timeout=5
            )
            data = r.json()
            if data.get("response"):
                f = data["response"][0]
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                gh = f["goals"]["home"]
                ga = f["goals"]["away"]
                adversario = away if home == "Moreirense" else home
                if home == "Moreirense":
                    resultado = f"{gh}-{ga}"
                    ganhou = gh > ga
                else:
                    resultado = f"{ga}-{gh}"
                    ganhou = ga > gh
                ultimo_resultado = {
                    "adversario": adversario,
                    "resultado": resultado,
                    "ganhou": ganhou,
                }
    except Exception:
        pass

    return {
        "time": agora.strftime("%H:%M:%S"),
        "date": agora.strftime("%A, %d %B %Y").capitalize(),
        "weather": {"temp": weather_text, "desc": weather_desc},
        "scout": {"total": total_ops, "aprovadas": aprovadas, "recorrentes": recorrentes[:3], "top": top_ops},
        "proximo_jogo": proximo_jogo,
        "ultimo_resultado": ultimo_resultado,
    }


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    user_text = body.get("message", "").strip()
    if not user_text:
        return JSONResponse({"response": ""})
    reply = chat_with_morgan(user_text)
    return JSONResponse({"response": reply})


@app.post("/api/chat-stream")
async def chat_stream(request: Request):
    """Claude com streaming — tokens aparecem à medida que chegam."""
    body = await request.json()
    user_text = body.get("message", "").strip()
    if not user_text:
        return StreamingResponse(iter([""]), media_type="text/plain")

    store_save(DESKTOP_USER_ID, "user", user_text)
    conversation_history.append({"role": "user", "content": user_text})

    async def generate():
        full_reply = ""
        with claude.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=get_system_prompt(user_text),
            messages=conversation_history[-50:],
        ) as stream:
            for text in stream.text_stream:
                full_reply += text
                yield text
        conversation_history.append({"role": "assistant", "content": full_reply})
        store_save(DESKTOP_USER_ID, "assistant", full_reply)
        _mem0_guardar_se_relevante(user_text, full_reply)

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.post("/api/chat-speak")
async def chat_speak(request: Request):
    """Claude → ElevenLabs frase-a-frase → SSE para estado em tempo real."""
    body = await request.json()
    user_text = body.get("message", "").strip()
    if not user_text:
        return JSONResponse({"ok": True, "response": ""})

    await kill_player()

    async def generate():
        reply = await asyncio.get_event_loop().run_in_executor(None, chat_with_morgan, user_text)
        sentences = split_sentences(reply)

        # Texto aparece no ecrã imediatamente
        yield f"data: {json.dumps({'type': 'speaking', 'text': reply})}\n\n"

        for sentence in sentences:
            if not sentence:
                continue
            audio = await elevenlabs_sentence(sentence)
            if audio:
                completed = await play_audio_bytes(audio)
            else:
                await say_sentence(sentence)
                completed = True
            if not completed:
                break

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/barge-in")
async def barge_in():
    """Para o áudio imediatamente — chamado quando o utilizador começa a falar."""
    await kill_player()
    return JSONResponse({"ok": True})


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        from deepgram import DeepgramClient
        dg = DeepgramClient(DEEPGRAM_KEY)
        audio_bytes = await audio.read()
        mimetype = audio.content_type or "audio/webm"
        response = dg.listen.rest.v("1").transcribe_file(
            {"buffer": audio_bytes, "mimetype": mimetype},
            {"model": "nova-2", "language": "pt"},
        )
        transcript = response.results.channels[0].alternatives[0].transcript
        return JSONResponse({"transcript": transcript})
    except Exception as e:
        return JSONResponse({"transcript": "", "error": str(e)})


@app.post("/api/speak")
async def speak(request: Request):
    """Toca texto em voz. Tenta ElevenLabs; se falhar usa 'say' nativo do macOS."""
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return JSONResponse({"ok": True})

    import subprocess
    import tempfile

    # Tentar ElevenLabs primeiro
    try:
        from elevenlabs import ElevenLabs
        el = ElevenLabs(api_key=ELEVENLABS_KEY)
        chunks = []
        for chunk in el.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=VOICE_SETTINGS,
        ):
            chunks.append(chunk)
        audio_bytes = b"".join(chunks)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(["afplay", tmp_path], check=True)
        )
        os.unlink(tmp_path)
        return JSONResponse({"ok": True, "engine": "elevenlabs"})
    except Exception as e_el:
        pass  # fallback para say

    # Fallback: say nativo do macOS (voz Joana PT)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(["say", "-v", "Joana", text], check=True)
        )
        return JSONResponse({"ok": True, "engine": "say"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws/convai")
async def ws_convai(websocket: WebSocket):
    """Proxy WebSocket: browser → ElevenLabs Conversational AI → browser.
    Áudio de saída tocado via sounddevice em tempo real."""
    await websocket.accept()

    import base64
    import numpy as np
    import sounddevice as sd
    import websockets as ws_lib

    # Sistema prompt dinâmico com memória atual
    memoria = load_memory()
    agora = datetime.now().strftime("%d de %B de %Y, %H:%M")
    system_prompt = f"""És o Morgan, assistente pessoal do Vasco Botelho da Costa.
Data e hora atual: {agora}

{memoria}

Estás na interface desktop do Morgan — modo de conversa por voz.
Responde de forma natural, concisa e direta. Sem markdown. Fala como se estivesses ao lado do Vasco.
Respostas curtas e naturais. Nunca digas que és uma IA."""

    el_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={CONVAI_AGENT_ID}"

    # Stream de áudio para o altifalante (PCM 16kHz 16-bit mono)
    audio_queue: asyncio.Queue = asyncio.Queue()
    playback_active = True

    def audio_player():
        """Toca chunks PCM em tempo real."""
        with sd.OutputStream(samplerate=16000, channels=1, dtype='int16') as stream:
            while playback_active:
                try:
                    chunk = audio_queue.get_nowait()
                    if chunk is None:
                        break
                    arr = np.frombuffer(chunk, dtype=np.int16)
                    stream.write(arr)
                except Exception:
                    import time; time.sleep(0.005)

    import threading
    player_thread = threading.Thread(target=audio_player, daemon=True)
    player_thread.start()

    try:
        async with ws_lib.connect(
            el_url,
            additional_headers={"xi-api-key": ELEVENLABS_KEY}
        ) as el_ws:

            # 1. Receber metadata inicial
            init_msg = await el_ws.recv()

            # 2. Enviar configuração
            await el_ws.send(json.dumps({
                "type": "conversation_initiation_client_data",
                "conversation_config_override": {
                    "agent": {
                        "language": "pt"
                    },
                    "tts": {
                        "voice_id": ELEVENLABS_VOICE_ID,
                        "voice_settings": {
                            "stability": 0.35,
                            "similarity_boost": 0.98,
                            "style": 0.35,
                            "use_speaker_boost": True,
                            "speed": 0.70
                        }
                    },
                    "turn": {
                        "turn_timeout": 3600
                    }
                }
            }))

            async def el_to_browser():
                """ElevenLabs → browser (eventos) + altifalante (áudio)."""
                nonlocal playback_active
                async for msg in el_ws:
                    try:
                        data = json.loads(msg)
                        t = data.get("type", "")

                        if t == "audio":
                            # Tocar áudio PCM imediatamente
                            chunk = base64.b64decode(data.get("audio_event", {}).get("audio_base_64", ""))
                            if chunk:
                                await audio_queue.put(chunk)

                        elif t == "user_transcript":
                            text = data.get("user_transcription_event", {}).get("user_transcript", "")
                            if text:
                                store_save(DESKTOP_USER_ID, "user", text)
                                await websocket.send_text(json.dumps({"type": "user", "text": text}))

                        elif t == "agent_response":
                            text = data.get("agent_response_event", {}).get("agent_response", "")
                            if text:
                                store_save(DESKTOP_USER_ID, "assistant", text)
                                await websocket.send_text(json.dumps({"type": "agent", "text": text}))

                        elif t == "interruption":
                            # Utilizador interrompeu — limpar queue de áudio
                            while not audio_queue.empty():
                                try: audio_queue.get_nowait()
                                except: pass
                            await websocket.send_text(json.dumps({"type": "interrupted"}))

                    except Exception:
                        pass

            async def browser_to_el():
                """Browser (mic PCM) → ElevenLabs."""
                try:
                    while True:
                        audio = await websocket.receive_bytes()
                        # ElevenLabs espera base64 PCM 16kHz 16-bit
                        await el_ws.send(json.dumps({
                            "user_audio_chunk": base64.b64encode(audio).decode()
                        }))
                except WebSocketDisconnect:
                    pass
                except Exception:
                    pass

            await asyncio.gather(el_to_browser(), browser_to_el())

    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "text": str(e)}))
        except Exception:
            pass
    finally:
        playback_active = False
        await audio_queue.put(None)


def _contexto_para_hume() -> str:
    """Constrói contexto completo para o Hume:
    - Mem0: memórias de longo prazo (factos extraídos de TODAS as conversas)
    - Supabase: últimas 100 mensagens raw (continuidade recente)
    """
    partes = []

    # Camada 1 — Mem0: memória semântica de longo prazo
    try:
        mem_vasco = mem0_get("vasco", "Morgan BCVertex negócios trading Moreirense Vasco", limit=15)
        mem_col = mem0_collective_get("decisões importantes negócios agentes", limit=5)
        if mem_vasco:
            partes.append(f"=== MEMÓRIA DE LONGO PRAZO (tudo o que o Morgan sabe sobre o Vasco) ===\n{mem_vasco}")
        if mem_col:
            partes.append(f"=== MEMÓRIA COLECTIVA DOS AGENTES ===\n{mem_col}")
    except Exception:
        pass

    # Camada 2 — Supabase: últimas 100 mensagens raw para continuidade
    try:
        msgs = get_context_messages(DESKTOP_USER_ID, limit=100)
        if msgs:
            lines = []
            for m in msgs:
                role = "Vasco" if m["role"] == "user" else "Morgan"
                content = str(m.get("content", ""))[:250].replace("\n", " ")
                lines.append(f"{role}: {content}")
            partes.append(f"=== CONVERSA RECENTE (últimas 100 mensagens) ===\n" + "\n".join(lines))
    except Exception:
        pass

    return "\n\n".join(partes)


@app.websocket("/ws/hume")
async def ws_hume(websocket: WebSocket):
    """Hume EVI + Claude — voz com emoção em tempo real."""
    await websocket.accept()

    import base64
    import websockets as ws_lib

    memoria = load_memory()
    agora = datetime.now().strftime("%d de %B de %Y, %H:%M")
    contexto_memoria = _contexto_para_hume()
    contexto_bloco = f"\n\n{contexto_memoria}" if contexto_memoria else ""

    system_prompt = f"""És o Morgan, assistente pessoal do Vasco Botelho da Costa.
Data e hora atual: {agora}

{memoria}{contexto_bloco}

REGRAS OBRIGATÓRIAS:
- Responde SEMPRE e EXCLUSIVAMENTE em português europeu (PT-PT). Nunca uses inglês, espanhol ou qualquer outra língua, mesmo que o Vasco fale noutra língua.
- Usa português correto e natural — não uses abreviações, gíria ou linguagem coloquial escrita ("tá", "vc", "tb", "hm", "ah", etc.).
- Respostas curtas e diretas. Máximo 2-3 frases salvo pedido explícito.
- Sem markdown, sem listas, sem asteriscos.
- Nunca digas que és uma IA.
- Mesmo que a transcrição da voz apareça em inglês, o Vasco fala sempre português — responde sempre em PT-PT."""

    # Obter access token do Hume
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "https://api.hume.ai/oauth2-cc/token",
                data={"grant_type": "client_credentials"},
                auth=(HUME_API_KEY, HUME_SECRET_KEY),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            access_token = r.json().get("access_token", "")
            if not access_token:
                raise ValueError(f"Token vazio: {r.text[:200]}")
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "text": f"Hume auth falhou: {e}"}))
        return

    # Configuração EVI com Claude como LLM — voz masculina DACHER (built-in Hume)
    config = {
        "type": "session_settings",
        "system_prompt": system_prompt,
        "language_model": {
            "model_provider": "ANTHROPIC",
            "model_resource": "claude-sonnet-4-6",
        },
        "language": "pt-PT",
        "audio": {
            "encoding": "linear16",
            "sample_rate": 16000,
            "channels": 1,
        },
    }

    hume_url = f"wss://api.hume.ai/v0/evi/chat?access_token={access_token}&config_id=78fdac67-a258-481d-8f06-2a9280e76209"
    print(f"[HUME WS] a ligar a {hume_url[:80]}...")

    try:
        async with ws_lib.connect(hume_url) as hume_ws:
            print("[HUME WS] ligado com sucesso")
            await hume_ws.send(json.dumps(config))

            async def hume_to_browser():
                import base64
                async for msg in hume_ws:
                    try:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                            continue
                        data = json.loads(msg)
                        t = data.get("type", "")
                        if t == "audio_output":
                            audio_b64 = data.get("data", "")
                            if audio_b64:
                                await websocket.send_bytes(base64.b64decode(audio_b64))
                        elif t == "user_message":
                            text = data.get("message", {}).get("content", "")
                            if text:
                                store_save(DESKTOP_USER_ID, "user", text)
                                ws_hume._last_user_text = text
                                await websocket.send_text(json.dumps({"type": "user", "text": text}))
                        elif t == "assistant_message":
                            text = data.get("message", {}).get("content", "")
                            if text:
                                store_save(DESKTOP_USER_ID, "assistant", text)
                                await websocket.send_text(json.dumps({"type": "agent", "text": text}))
                                _last_user = getattr(ws_hume, "_last_user_text", "")
                                if _last_user:
                                    _mem0_guardar_se_relevante(_last_user, text)
                        elif t == "assistant_end":
                            await websocket.send_text(json.dumps({"type": "done"}))
                        elif t == "error":
                            msg_text = data.get("message", "")
                            print(f"[HUME ERROR] {msg_text}")
                            await websocket.send_text(json.dumps({"type": "error", "text": msg_text}))
                        else:
                            print(f"[HUME MSG] type={t}")
                    except Exception as e:
                        print(f"[HUME hume_to_browser erro] {e}")

            async def browser_to_hume():
                import base64
                try:
                    while True:
                        audio = await websocket.receive_bytes()
                        await hume_ws.send(json.dumps({
                            "type": "audio_input",
                            "data": base64.b64encode(audio).decode("utf-8"),
                        }))
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    print(f"[HUME browser_to_hume erro] {e}")

            await asyncio.gather(hume_to_browser(), browser_to_hume())

    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "text": str(e)}))
        except Exception:
            pass


@app.post("/api/enroll-voice")
async def enroll_voice_endpoint(request: Request):
    """Recebe chunks PCM acumulados e cria o perfil de voz do Vasco."""
    body = await request.body()
    if len(body) < 16000 * 2 * 2:  # mínimo ~2s a 16kHz 16-bit
        return JSONResponse({"ok": False, "error": "Amostra muito curta. Fala durante pelo menos 3 segundos."})
    ok = enroll_voice([body])
    return JSONResponse({"ok": ok, "message": "Perfil de voz guardado." if ok else "Erro ao criar perfil."})


@app.get("/api/voice-id-status")
async def voice_id_status():
    return JSONResponse({"enrolled": has_profile()})


@app.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket):
    """Proxy WebSocket: browser → Deepgram Live API → browser com verificação de voz."""
    await websocket.accept()
    sample_rate = int(websocket.query_params.get("sr", "16000"))

    dg_url = (
        f"wss://api.deepgram.com/v1/listen"
        f"?model=nova-2&language=pt&encoding=linear16"
        f"&sample_rate={sample_rate}&channels=1"
        f"&interim_results=true&endpointing=400&smart_format=true&vad_events=true"
    )

    # Buffer de áudio para verificação de voz
    audio_buffer: list[bytes] = []

    try:
        import websockets as ws_lib
        async with ws_lib.connect(dg_url, additional_headers={"Authorization": f"Token {DEEPGRAM_KEY}"}) as dg_ws:

            async def dg_to_browser():
                async for msg in dg_ws:
                    try:
                        data = json.loads(msg)
                        if data.get("type") != "Results":
                            continue
                        alts = data.get("channel", {}).get("alternatives", [{}])
                        text = (alts[0].get("transcript", "") if alts else "").strip()
                        is_final = data.get("is_final", False)
                        speech_final = data.get("speech_final", False)

                        if not text:
                            continue

                        if speech_final:
                            # Verificar se é o Vasco antes de enviar ao browser
                            loop = asyncio.get_event_loop()
                            vasco, sim = await loop.run_in_executor(
                                None, is_vasco, list(audio_buffer)
                            )
                            audio_buffer.clear()
                            if not vasco:
                                print(f"Voice ID: voz rejeitada (sim={sim})")
                                continue
                            await websocket.send_text(json.dumps({"type": "speech_final", "text": text}))
                        elif is_final:
                            await websocket.send_text(json.dumps({"type": "final", "text": text}))
                        else:
                            await websocket.send_text(json.dumps({"type": "interim", "text": text}))
                    except Exception:
                        pass

            async def browser_to_dg():
                try:
                    while True:
                        audio = await websocket.receive_bytes()
                        audio_buffer.append(audio)
                        await dg_ws.send(audio)
                except WebSocketDisconnect:
                    pass
                except Exception:
                    pass

            await asyncio.gather(dg_to_browser(), browser_to_dg())

    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "text": str(e)}))
        except Exception:
            pass

@app.get("/api/bot")
async def bot_status():
    """Estado atual do trading bot (sem fazer ciclo)."""
    try:
        status = get_bot_status()
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/activity")
async def get_activity(n: int = 20):
    """Últimas N linhas do audit.log."""
    audit_file = Path(__file__).parent / "memory" / "audit.log"
    if not audit_file.exists():
        return JSONResponse({"lines": []})
    try:
        lines = audit_file.read_text(encoding="utf-8").splitlines()
        return JSONResponse({"lines": lines[-n:]})
    except Exception as e:
        return JSONResponse({"lines": [], "error": str(e)})


@app.get("/api/agents")
async def get_agents():
    """Lista todos os agentes activos no sistema — lida dinamicamente dos ficheiros."""
    import re
    agents_dir = Path(__file__).parent
    builtin = [
        {"id": "ceo",       "label": "CEO",       "role": "núcleo",         "color": "190,150,10"},
        {"id": "scout",     "label": "Scout",     "role": "inteligência",   "color": "190,150,10"},
        {"id": "coach",     "label": "Coach",     "role": "análise tática", "color": "0,255,157"},
        {"id": "cfo",       "label": "CFO",       "role": "financeiro",     "color": "110,130,160"},
        {"id": "creator",   "label": "Creator",   "role": "meta-tool",      "color": "255,170,0"},
        {"id": "operator",  "label": "Operator",  "role": "operações",      "color": "0,200,130"},
        {"id": "marketeer", "label": "Marketeer", "role": "crescimento",    "color": "180,100,255"},
        {"id": "solver",    "label": "Solver",    "role": "manutenção",     "color": "155,109,255"},
    ]
    builtin_ids = {a["id"] for a in builtin}
    # Adicionar agentes criados dinamicamente pelo Creator
    for f in sorted(agents_dir.glob("*_agent.py")):
        agent_id = f.stem.replace("_agent", "")
        if agent_id not in builtin_ids:
            # Ler primeira linha da docstring como role
            try:
                first_doc = f.read_text(encoding="utf-8").split('"""')[1].strip().split("\n")[0][:40]
            except Exception:
                first_doc = ""
            builtin.append({"id": agent_id, "label": agent_id.replace("_", " ").title(),
                            "role": first_doc, "color": "100,200,255"})
    return JSONResponse({"agents": builtin})


@app.get("/api/agent")
async def get_agent():
    """Agente desktop ativo neste momento."""
    return JSONResponse({"agent": _desktop_agent.get("current", "ceo")})


@app.post("/api/agent")
async def set_agent(request: Request):
    """Define o agente ativo via canvas click."""
    body = await request.json()
    agent = body.get("agent", "ceo")
    valid = {"ceo", "coach", "cfo", "scout", "solver", "creator", "operator"}
    if agent in valid:
        _desktop_agent["current"] = agent
    return JSONResponse({"agent": _desktop_agent.get("current", "ceo")})


# ── Push Notifications ────────────────────────────────────────────────────────

@app.get("/api/push/vapid-public-key")
async def get_vapid_public_key():
    return JSONResponse({"key": VAPID_PUBLIC_KEY})


@app.post("/api/push/subscribe")
async def push_subscribe(request: Request):
    sub = await request.json()
    save_subscription(sub)
    return JSONResponse({"ok": True})


@app.post("/api/push/test")
async def push_test():
    result = send_push(
        title="Morgan",
        body="Notificações activas. Estás ligado.",
        url="/pwa/"
    )
    return JSONResponse(result)


@app.post("/api/push/report")
async def push_report_now():
    """Força o relatório diário agora — para teste sem esperar as 22h."""
    await _run_daily_report()
    return JSONResponse({"ok": True})


@app.post("/api/solver/run")
async def solver_run(request: Request):
    """Corre o Solver v2 (LangGraph) com um problema — endpoint de teste."""
    body = await request.json()
    problema = body.get("problema", "").strip()
    if not problema:
        return JSONResponse({"error": "Parâmetro 'problema' é obrigatório."}, status_code=400)
    loop = asyncio.get_event_loop()
    try:
        from solver_graph import run_solver
        resultado = await loop.run_in_executor(None, run_solver, problema)
        return JSONResponse({"ok": True, "resultado": resultado})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/etsy/plano")
async def etsy_plano():
    """Devolve o último plano semanal do PlannerAtlas ou gera um novo."""
    plano_file = Path(__file__).parent / "memory" / "planneratlas_plano_semana.md"
    if plano_file.exists():
        return JSONResponse({"ok": True, "plano": plano_file.read_text(encoding="utf-8")})
    loop = asyncio.get_event_loop()
    try:
        from creator_agent import gerar_plano_semana_planneratlas
        plano = await loop.run_in_executor(None, gerar_plano_semana_planneratlas)
        return JSONResponse({"ok": True, "plano": plano, "gerado_agora": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/bot/multi")
async def bot_multi_status():
    """Estado do trading bot em modo multi-par."""
    try:
        from trading_bot import get_multi_status
        return JSONResponse(get_multi_status())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


_NOTIF_FILE = Path(__file__).parent / "memory" / "notificacoes.json"

def _load_notifs() -> list:
    try:
        return json.loads(_NOTIF_FILE.read_text())
    except Exception:
        return []

def _save_notif(title: str, body: str):
    notifs = _load_notifs()
    notifs.append({"ts": datetime.now().isoformat()[:16], "title": title, "body": body})
    _NOTIF_FILE.write_text(json.dumps(notifs[-200:], ensure_ascii=False))


@app.get("/api/history")
async def get_history(n: int = 30):
    """Últimas N trocas do histórico de conversa."""
    hist_file = Path(__file__).parent / "memory" / "historico.json"
    try:
        raw = json.loads(hist_file.read_text())
        msgs = raw.get("vasco", raw) if isinstance(raw, dict) else raw
        pairs = []
        i = 0
        while i < len(msgs) - 1:
            if msgs[i].get("role") == "user" and msgs[i+1].get("role") == "assistant":
                pairs.append({"user": msgs[i]["content"][:300], "assistant": msgs[i+1]["content"][:500]})
                i += 2
            else:
                i += 1
        return JSONResponse({"pairs": pairs[-n:]})
    except Exception as e:
        return JSONResponse({"pairs": [], "error": str(e)})


@app.get("/api/reports")
async def get_reports(n: int = 7):
    """Últimos N reports diários."""
    mem = Path(__file__).parent / "memory"
    reports = sorted(mem.glob("report_*.txt"), reverse=True)[:n]
    result = []
    for f in reports:
        date = f.stem.replace("report_", "")
        result.append({"date": date, "content": f.read_text(encoding="utf-8")[:2000]})
    return JSONResponse({"reports": result})


@app.get("/api/notifications")
async def get_notifications(n: int = 50):
    """Últimas N notificações push enviadas."""
    notifs = _load_notifs()
    return JSONResponse({"notifications": notifs[-n:][::-1]})


# ── Heartbeat interno ─────────────────────────────────────────────────────────

import time as _time
import zoneinfo as _zi

_HEARTBEAT_STATE_FILE = Path(__file__).parent / "memory" / "heartbeat_state.json"
_DEDUP_FILE = Path(__file__).parent / "memory" / "push_dedup.json"
_HEARTBEAT_START = _time.time()
_LISBON = _zi.ZoneInfo("Europe/Lisbon")


def _agora_lisboa():
    return datetime.now(_LISBON)


def _dedup_check(chave: str) -> bool:
    try:
        data = json.loads(_DEDUP_FILE.read_text()) if _DEDUP_FILE.exists() else {}
        return chave in data
    except Exception:
        return False


def _dedup_mark(chave: str):
    try:
        data = json.loads(_DEDUP_FILE.read_text()) if _DEDUP_FILE.exists() else {}
        data[chave] = _agora_lisboa().isoformat()
        # Manter só as últimas 500 entradas
        if len(data) > 500:
            keys = sorted(data, key=lambda k: data[k])
            for k in keys[:-400]:
                del data[k]
        _DEDUP_FILE.write_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def _should_run_briefing() -> bool:
    # Briefing matinal apenas às 7h — conteúdo via Coach
    if _time.time() - _HEARTBEAT_START < 120:
        return False
    if is_pausado():
        return False
    agora = _agora_lisboa()
    if agora.hour != 7:
        return False
    return not _dedup_check(f"push_briefing_{agora.strftime('%Y-%m-%d_%H')}")


def _should_run_scout_melhorias() -> bool:
    # Scout Missão B — melhorias a agentes existentes — quarta-feira às 20h
    agora = _agora_lisboa()
    if agora.weekday() != 2 or agora.hour != 20:
        return False
    return not _dedup_check(f"scout_melhorias_{agora.strftime('%Y-%W')}")


def _should_run_scout() -> bool:
    agora = _agora_lisboa()
    if agora.weekday() != 6 or agora.hour != 20:
        return False
    return not _dedup_check(f"push_scout_{agora.strftime('%Y-%W')}")


async def _run_briefing(hora: int):
    """Briefing matinal às 7h — CEO orquestra, Coach fornece secção de futebol, CFO o trading."""
    loop = asyncio.get_event_loop()
    agora = _agora_lisboa()

    # Meteo
    meteo = ""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://wttr.in/Moreira+de+Conegos?format=%t+%C", timeout=4)
            meteo = r.text.strip()
    except Exception:
        pass

    # CFO — trading (não pertence ao Coach)
    bot_str = ""
    try:
        from trading_bot import get_status as _bot_status
        b = _bot_status()
        bot_str = (
            f"{'ATIVO' if b.get('active') else 'PARADO'} | "
            f"PnL hoje: {b.get('pnl_today', 0):+.2f} USDT | "
            f"PnL total: {b.get('pnl_total', 0):+.2f} USDT"
        )
    except Exception:
        pass

    # Coach — secção de futebol (próximo jogo, Moreirense, Liga Portugal)
    coach_str = ""
    try:
        from coach_agent import get_coach_reply
        coach_str = await loop.run_in_executor(
            None,
            lambda: get_coach_reply("Resume em 2 linhas: próximo jogo do Moreirense e posição na tabela. Só futebol, sem mais nada.")
        )
        coach_str = coach_str.replace("[COACH]", "").strip()
    except Exception:
        pass

    # Scout
    scout_data = load_scout()
    aprovadas_raw = scout_data.get("aprovadas", [])
    aprovadas = [a if isinstance(a, str) else a.get("nome", str(a)) for a in aprovadas_raw]
    oport_top = list(scout_data.get("oportunidades", {}).keys())[:1]

    # Delta reporting — memória episódica
    # Só inclui secção se o conteúdo mudou desde o último briefing
    from episodic_memory import registar_evento
    coach_novidade = registar_evento("coach", "moreirense_briefing", coach_str) if coach_str else False
    bot_novidade = registar_evento("cfo", "trading_briefing", bot_str) if bot_str else False
    scout_texto = oport_top[0] if oport_top else ""
    scout_novidade = registar_evento("scout", "oportunidade_top", scout_texto) if scout_texto else False

    coach_bloco = coach_str if coach_str else "Dados de futebol indisponíveis."
    if not coach_novidade and coach_str:
        coach_bloco += "\n[sem alterações desde ontem]"

    bot_bloco = bot_str if bot_str else "Bot indisponível."
    if not bot_novidade and bot_str:
        bot_bloco += " [sem alterações]"

    scout_bloco = (
        f"Oportunidade prioritária: {scout_texto}" if scout_texto else "Sem oportunidades novas."
    )
    if scout_texto and not scout_novidade:
        scout_bloco += " [já reportada]"
    if aprovadas:
        scout_bloco += f"\nAprovadas em curso: {', '.join(aprovadas[:2])}"

    prompt = f"""És o Morgan CEO. Gera o briefing matinal das 7h para o Vasco Botelho da Costa.
Data: {agora.strftime('%d/%m/%Y')}.
{f'Tempo: {meteo}' if meteo else ''}

FUTEBOL (Coach):
{coach_bloco}

CFO — TRADING:
{bot_bloco}

SCOUT:
{scout_bloco}

MEMÓRIA DO VASCO:
{load_memory()}

Instruções:
- Primeira linha: futebol (jogo ou situação na tabela) — omite se [sem alterações desde ontem]
- Segunda linha: trading (CFO — 1 linha, factual) — omite se [sem alterações]
- Terceira linha: oportunidade prioritária ou negócio em curso — omite se [já reportada]
- Se não há novidades em nenhuma área, diz isso directamente numa linha
- Tom de braço direito a falar ao chefe de manhã
- Máximo 5 linhas. Sem emojis. Português europeu."""

    response = await loop.run_in_executor(
        None,
        lambda: claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=get_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )
    )
    texto = response.content[0].text if response.content else "Briefing indisponível."
    send_push(title="Morgan — Bom dia", body=texto[:200], url="/pwa/")
    _dedup_mark(f"push_briefing_{agora.strftime('%Y-%m-%d_%H')}")


async def _run_scout_push():
    loop = asyncio.get_event_loop()
    try:
        from scout_agent import missao_a_oportunidades
        relatorio = await loop.run_in_executor(None, missao_a_oportunidades)
        corpo = relatorio[:300]
    except Exception as e:
        corpo = f"Erro Scout Missão A: {e}"
    send_push(
        title="Morgan Scout — Oportunidades Validadas",
        body=corpo[:200],
        url="/pwa/"
    )
    _dedup_mark(f"push_scout_{_agora_lisboa().strftime('%Y-%W')}")


async def _run_scout_relatorio_completo():
    """Scout on-demand — análise completa de oportunidades de negócio com pesquisa real."""
    loop = asyncio.get_event_loop()

    # Pesquisar em paralelo: Lego/BrickLink, REITs, oportunidades digitais PT/BR
    queries = [
        "BrickLink lego reseller business profit margins 2026",
        "REIT ETF Portugal Europe passive income 2026",
        "negócios digitais passivos Portugal Brasil SaaS 2026",
        "indie hackers passive income $1000 month 2026",
    ]

    resultados = []
    from tools import pesquisar_web
    for q in queries:
        try:
            r = await loop.run_in_executor(None, lambda q=q: pesquisar_web(q))
            resultados.append(r[:400])
        except Exception:
            pass

    pesquisa_combinada = "\n\n---\n\n".join(resultados)

    # Incluir análise de REITs do CFO
    try:
        from cfo_agent import analisar_reits
        reits_analise = analisar_reits()
    except Exception as e:
        reits_analise = f"(análise REITs indisponível: {e})"

    prompt = f"""És o Scout do Morgan. O Vasco quer lançar 5 negócios hoje. Analisa estas oportunidades com base nos dados de pesquisa abaixo.

CONTEXTO DO VASCO:
- Treinador de futebol no Moreirense FC (Portugal)
- Tem uma coleção de Lego e interesse em loja BrickLink
- Quer rendimento passivo de €10k/mês
- Tem o Morgan (8 agentes IA) para executar automaticamente
- Capital inicial disponível: pequeno (€200-1000 por negócio)

PRIORIDADES IDENTIFICADAS:
1. Loja BrickLink (Lego) — o Vasco tem coleção, quer escalar
2. REITs / fundos real estate — investimento passivo PT/EU
3. Produto digital futebol PT/BR — análise táctica, templates, conteúdo
4. Negócio IA/automação para PMEs portuguesas
5. Quinta oportunidade — o que os dados revelam

DADOS DE PESQUISA:
{pesquisa_combinada[:2000]}

ANÁLISE CFO — REITs PT/ES/IE:
{reits_analise[:1000]}

Para cada oportunidade:
- Nome do negócio
- Potencial de receita em 90 dias (€/mês)
- Capital inicial necessário (€)
- O que o Morgan executa automaticamente vs o que o Vasco faz uma vez
- Nível de risco: Baixo/Médio/Alto
- Próximo passo concreto (hoje)

Sê específico e realista. Português europeu. Máximo 400 palavras."""

    response = await loop.run_in_executor(
        None,
        lambda: claude.messages.create(
            model="claude-opus-4-8",
            max_tokens=1200,
            system="És o Scout do BCVertex. Analisas oportunidades de negócio com dados reais. Directo, concreto, sem hype.",
            messages=[{"role": "user", "content": prompt}]
        )
    )
    texto = response.content[0].text if response.content else "Scout indisponível."

    send_push(
        title="Morgan Scout — 5 Negócios para hoje",
        body=texto[:200],
        url="/pwa/"
    )

    report_file = Path(__file__).parent / "memory" / f"report_{_agora_lisboa().strftime('%Y-%m-%d')}.txt"
    report_file.write_text(texto, encoding="utf-8")
    print(f"[scout] relatório completo guardado: {report_file}", flush=True)


async def _run_scout_melhorias():
    """Scout Missão B — quarta-feira 20h. Pesquisa melhorias para agentes existentes."""
    loop = asyncio.get_event_loop()
    from sistema_service import get_agentes_ativos

    agentes = get_agentes_ativos()
    agentes_lista = "\n".join(f"- {v['nome']}: {v['descricao']}" for v in agentes.values())

    prompt = f"""És o Scout do Morgan. A tua Missão B é encontrar melhorias para os agentes existentes.

AGENTES ACTUAIS:
{agentes_lista}

Para cada agente, pesquisa:
1. Existe uma API ou biblioteca mais recente que melhore as suas capacidades?
2. Há uma ferramenta nova (lançada nos últimos 3 meses) que valha integrar?
3. O que os founders do IndieHackers/HN estão a usar para automatizar tarefas semelhantes?

Responde com uma lista concisa de melhorias concretas, por agente.
Formato: [Agente] — [Melhoria] — [Impacto estimado]
Máximo 8 sugestões. Português europeu."""

    try:
        from tools import pesquisar_web
        pesquisa = await loop.run_in_executor(
            None,
            lambda: pesquisar_web("new AI tools automation agents 2026 indie hackers")
        )
    except Exception:
        pesquisa = ""

    if pesquisa:
        prompt += f"\n\nDADOS DE PESQUISA:\n{pesquisa[:800]}"

    response = await loop.run_in_executor(
        None,
        lambda: claude.messages.create(
            model="claude-opus-4-8",
            max_tokens=800,
            system="És o Scout do Morgan. Foco em melhorias práticas e implementáveis. Análise profunda e rigorosa.",
            messages=[{"role": "user", "content": prompt}]
        )
    )
    texto = response.content[0].text if response.content else "Scout Missão B indisponível."

    send_push(
        title="Morgan Scout — Melhorias de agentes",
        body=texto[:200],
        url="/pwa/"
    )

    report_file = Path(__file__).parent / "memory" / f"scout_melhorias_{_agora_lisboa().strftime('%Y-%m-%d')}.txt"
    report_file.write_text(texto, encoding="utf-8")


def _should_run_report() -> bool:
    if _time.time() - _HEARTBEAT_START < 120:
        return False
    if is_pausado():
        return False
    agora = _agora_lisboa()
    from config_service import load_config
    report_hora = load_config().get("report_hora", 22)
    if agora.hour != report_hora:
        return False
    return not _dedup_check(f"push_report_{agora.strftime('%Y-%m-%d')}")


async def _run_daily_report():
    """Relatório diário às 22h — resume tudo o que aconteceu hoje."""
    loop = asyncio.get_event_loop()
    agora = _agora_lisboa()
    hoje = agora.strftime("%Y-%m-%d")

    # Conversas de hoje (filtrar por data)
    try:
        from conversation_store import load_history
        todas = load_history(DESKTOP_USER_ID)
        msgs_hoje = [
            m for m in todas
            if str(m.get("created_at", m.get("timestamp", ""))).startswith(hoje)
        ]
        n_trocas = len([m for m in msgs_hoje if m.get("role") == "user"])
        def _conv_texto(m):
            c = m.get('content', '')
            if isinstance(c, list):
                c = ' '.join(b.get('text', '') if isinstance(b, dict) else str(b) for b in c)
            return str(c)[:120]
        resumo_conv = "\n".join(
            f"  {m['role']}: {_conv_texto(m)}"
            for m in msgs_hoje[-20:]
        ) if msgs_hoje else "  Nenhuma conversa registada hoje."
    except Exception:
        n_trocas = 0
        resumo_conv = "  (erro ao carregar conversas)"

    # Estado do trading bot
    try:
        from trading_bot import get_status
        bot = get_status()
        bot_str = (
            f"PnL hoje: {bot.get('pnl_today', 0):+.4f} USDT | "
            f"PnL total: {bot.get('pnl_total', 0):+.4f} USDT | "
            f"Trades: {bot.get('trades', 0)} | "
            f"Sinal: {bot.get('signal', 'hold')}"
        )
    except Exception:
        bot_str = "indisponível"

    # Scout — oportunidades aprovadas
    try:
        scout_data = load_scout()
        aprovadas_raw = scout_data.get("aprovadas", [])
        aprovadas = [a if isinstance(a, str) else a.get("nome", str(a)) for a in aprovadas_raw]
        ops_str = ", ".join(aprovadas[:3]) if aprovadas else "nenhuma aprovada"
        oport_novas = list(scout_data.get("oportunidades", {}).keys())[:2]
        oport_str = ", ".join(oport_novas) if oport_novas else "nenhuma nova"
    except Exception:
        ops_str = "indisponível"
        oport_str = "indisponível"

    # Sprint I — Operator monitoriza todos os negócios autonomamente
    operator_str = "indisponível"
    try:
        from operator_agent import monitorizar_negocios
        operator_str = await loop.run_in_executor(None, monitorizar_negocios)
        operator_str = operator_str[:600]
    except Exception as e:
        operator_str = f"(erro: {e})"

    # Estado do sistema (agentes + negócios activos)
    from sistema_service import resumo_sistema
    sistema_str = resumo_sistema()

    # Relatório de logs / erros do dia (últimas 20 linhas do error log)
    erros_str = ""
    try:
        err_file = Path(__file__).parent / "morgan_error.log"
        if err_file.exists():
            linhas_err = err_file.read_text().strip().splitlines()[-10:]
            erros_str = "\n".join(linhas_err) if linhas_err else "Sem erros registados."
    except Exception:
        erros_str = "Log de erros não disponível."

    prompt = f"""És o Morgan CEO. Gera o relatório de fim de dia para o Vasco.
Data: {agora.strftime('%d/%m/%Y')}

SISTEMA MORGAN:
{sistema_str}

CONVERSAS DE HOJE ({n_trocas} trocas):
{resumo_conv}

CFO — TRADING BOT:
{bot_str}

OPERATOR — NEGÓCIOS ACTIVOS:
{operator_str}

SCOUT:
Oportunidades aprovadas: {ops_str}
Oportunidades activas: {oport_str}

ERROS DO DIA:
{erros_str}

Instruções:
- Secção por agente/área: CFO, Operator, Scout, sistema
- O que aconteceu hoje, o que ficou por fazer, decisões tomadas
- Alertas se houver erros ou anomalias
- O que o Vasco deve ter em mente amanhã
- Tom direto, como um relatório de CEO. Máximo 10 linhas. Sem emojis. Português europeu."""

    response = await loop.run_in_executor(
        None,
        lambda: claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=get_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )
    )
    texto = response.content[0].text if response.content else "Relatório indisponível."

    send_push(
        title=f"Morgan — Relatório {agora.strftime('%d/%m')}",
        body=texto[:200],
        url="/pwa/"
    )

    report_file = Path(__file__).parent / "memory" / f"report_{hoje}.txt"
    report_file.write_text(texto, encoding="utf-8")

    _dedup_mark(f"push_report_{hoje}")


def _handle_trading_result(result: dict, label: str):
    """Processa resultado de um ciclo de trading e envia push se necessário."""
    status = result.get("status")
    if status == "trade_fechado":
        pnl = result.get("pnl", 0)
        sinal = "+" if pnl >= 0 else ""
        action = result.get("action", "")
        symbol = result.get("symbol", result.get("bot", ""))
        msg = (
            f"{label} — {symbol}"
            + (f" ({action})" if action else "") + "\n"
            f"Motivo: {result.get('reason', action or 'venda')}\n"
            f"PnL: {sinal}{pnl:.4f} USDT | Total: {result.get('pnl_total', 0):+.4f} USDT"
        )
        send_push(title="Trading Bot", body=msg, url="/pwa/")
    elif status == "compra":
        bot = result.get("bot", result.get("symbol", label))
        price = result.get("price", 0)
        send_push(title="Trading Bot — Compra", body=f"{bot} @ {price:.2f} USDT", url="/pwa/")
    elif status == "drawdown_diario":
        escalada_push(
            agente="CFO",
            situacao=result.get("message", "Drawdown diário atingido"),
            confianca=40,
            opcoes=["Parar bot", "Continuar com monitorização reforçada"]
        )
    elif status == "drawdown_total":
        escalada_push(
            agente="CFO",
            situacao=result.get("message", "Drawdown total atingiu limite — bot parado"),
            confianca=20,
            opcoes=["Confirmar paragem", "Rever estratégia"]
        )


async def _run_trading_cycle():
    """Corre ciclo do Supertrend BTC + DCA SOL e envia push se necessário."""
    loop = asyncio.get_event_loop()

    # Supertrend BTC/USDT
    try:
        from trading_bot import run_cycle
        result = await loop.run_in_executor(None, run_cycle)
        _handle_trading_result(result, "Supertrend BTC")
    except Exception as e:
        print(f"[trading_bot] erro: {e}", flush=True)

    # DCA SOL/USDT
    try:
        from dca_bot import run_dca_cycle
        result_dca = await loop.run_in_executor(None, run_dca_cycle)
        _handle_trading_result(result_dca, "DCA SOL")
    except Exception as e:
        print(f"[dca_bot] erro: {e}", flush=True)


async def _heartbeat_loop():
    await asyncio.sleep(30)  # deixar o servidor arrancar primeiro
    while True:
        try:
            agora = _agora_lisboa()

            # Reset PnL diário às 7h (uma vez por dia)
            chave_pnl = f"reset_pnl_{agora.strftime('%Y-%m-%d')}"
            if agora.hour == 7 and not _dedup_check(chave_pnl):
                _dedup_mark(chave_pnl)
                try:
                    from trading_bot import reset_daily_pnl
                    asyncio.get_event_loop().run_in_executor(None, reset_daily_pnl)
                except Exception:
                    pass
                try:
                    from dca_bot import reset_dca_daily_pnl
                    asyncio.get_event_loop().run_in_executor(None, reset_dca_daily_pnl)
                except Exception:
                    pass

            # Ciclo do trading bot — a cada hora
            chave_ciclo = f"trading_ciclo_{agora.strftime('%Y-%m-%d_%H')}"
            if not _dedup_check(chave_ciclo):
                _dedup_mark(chave_ciclo)
                await _run_trading_cycle()

            # Briefings automáticos 7h e 20h
            if _should_run_briefing():
                await _run_briefing(agora.hour)

            # Relatório diário às 22h
            if _should_run_report():
                await _run_daily_report()

            # Scout Missão A — oportunidades de negócio (domingo 20h)
            if _should_run_scout():
                await _run_scout_push()

            # Scout Missão B — melhorias a agentes existentes (quarta 20h)
            if _should_run_scout_melhorias():
                _dedup_mark(f"scout_melhorias_{agora.strftime('%Y-%W')}")
                await _run_scout_melhorias()

            # Plano semanal PlannerAtlas — segunda-feira às 8h
            chave_etsy = f"etsy_plano_{agora.strftime('%Y-%W')}"
            if agora.weekday() == 0 and agora.hour == 8 and not _dedup_check(chave_etsy):
                _dedup_mark(chave_etsy)
                loop = asyncio.get_event_loop()
                try:
                    from creator_agent import gerar_plano_semana_planneratlas
                    plano = await loop.run_in_executor(None, gerar_plano_semana_planneratlas)
                    send_push(
                        title="Morgan Planners — Plano da semana",
                        body=plano[:200],
                        url="/pwa/"
                    )
                except Exception as e:
                    print(f"[creator] erro plano etsy: {e}", flush=True)

        except Exception as e:
            print(f"[heartbeat] erro: {e}", flush=True)
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_heartbeat_loop())


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
