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


def get_system_prompt(query: str = "") -> str:
    memoria = load_memory()
    agora = datetime.now().strftime("%d de %B de %Y, %H:%M")

    # Mem0 desligado temporariamente (quota esgotada até 1 Agosto 2026)
    contexto = memoria

    return f"""És o Morgan, assistente pessoal do Vasco Botelho da Costa.
Data e hora atual: {agora}

{contexto}

LÍNGUA: Responde SEMPRE em português europeu (PT-PT). Nunca uses inglês, mesmo que a pergunta contenha palavras em inglês. Nunca mistures línguas.

Estás na interface desktop do Morgan — modo de conversa direta.
Responde de forma natural, concisa e direta. Sem markdown — escreve como se estivesses a falar com o Vasco.
Respostas curtas sempre que possível.

REGRA DE CONFIANÇA (obrigatória):
- Antes de qualquer ação consequente, avalia internamente a tua confiança de 0 a 100%.
- Se confiança ≥ 90%: age e informa o resultado de forma direta.
- Se confiança < 90%: NÃO ages. Diz "Confiança [X]% — preciso da tua confirmação" e explica a dúvida.
- Nunca inventes dados factuais. Se não souberes, diz "não tenho a certeza"."""


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


# ─── Routing de agentes ──────────────────────────────────────────────────────

def _quer_cfo(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in ["cfo", "trading bot", "trading", "pnl", "drawdown",
                                  "capital", "lucro", "perda", "trades", "win rate",
                                  "posição aberta", "financeiro", "finanças",
                                  "btc", "bitcoin", "usdt", "binance", "ema",
                                  "relatório financeiro"])

def _quer_coach(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in ["coach", "treinador", "tático", "tatico",
                                  "treino", "adversário", "adversario", "próximo jogo",
                                  "análise tática", "pré-jogo", "pós-jogo", "plantel",
                                  "jogador", "formação", "moreirense", "liga portugal",
                                  "scout de jogador", "perfil tático"])

def _quer_scout(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in ["scout", "oportunidade", "negócio", "negocio",
                                  "rendimento passivo", "saas", "produto", "receita",
                                  "empreend", "startup", "império", "dinheiro passivo"])

def _quer_marketeer(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in ["marketeer", "marketing", "outreach", "lead", "campanha",
                                  "aquisição", "cliente", "anúncio", "etsy", "descrição produto",
                                  "copywriting", "copy", "mensagem de venda", "crescimento",
                                  "canal de vendas", "conversão", "funil"])


def _quer_operator(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in ["operator", "operações", "lojas", "etsy vendas", "directório estado", "negócios estado", "receita total", "planneratlas"])

def _chat_ceo(user_text: str) -> str:
    """CEO — chamada direta ao Claude com ferramentas."""
    conversation_history.append({"role": "user", "content": user_text})
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
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
            model="claude-sonnet-4-6", max_tokens=512,
            system=get_system_prompt(user_text), tools=TOOLS,
            messages=conversation_history[-50:],
        )
    reply = "".join(block.text for block in response.content if hasattr(block, "text"))
    conversation_history.append({"role": "assistant", "content": reply})
    # Guardar no Mem0 em background (não bloqueia a resposta)
    try:
        import threading
        threading.Thread(
            target=mem0_add,
            args=("vasco", [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]),
            daemon=True
        ).start()
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

    # Reset explícito para CEO
    if any(k in msg_lower for k in ["morgan ceo", "volta ao morgan", "ceo", "morgan principal"]):
        _desktop_agent["current"] = "ceo"
        reply = "Morgan CEO de volta. Em que posso ajudar?"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Routing por intenção
    if _quer_cfo(user_text):
        _desktop_agent["current"] = "cfo"
        try:
            reply = "[CFO] " + get_cfo_reply(user_text)
        except Exception as e:
            reply = f"[CFO] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if _quer_coach(user_text):
        _desktop_agent["current"] = "coach"
        try:
            reply = "[COACH] " + get_coach_reply(user_text)
        except Exception as e:
            reply = f"[COACH] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    if _quer_marketeer(user_text):
        _desktop_agent["current"] = "marketeer"
        try:
            reply = "[MARKETEER] " + get_marketeer_reply(user_text)
        except Exception as e:
            reply = f"[MARKETEER] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply


    if _quer_operator(user_text):
        _desktop_agent["current"] = "operator"
        try:
            reply = "[OPERATOR] " + get_operator_reply(user_text)
        except Exception as e:
            reply = f"[OPERATOR] Erro: {e}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

    # Scout — CEO com contexto Scout
    if _quer_scout(user_text):
        _desktop_agent["current"] = "scout"
        scout_data = load_scout()
        ops = list(scout_data.get("oportunidades", {}).keys())[:5]
        scout_ctx = f"\n\n[SCOUT] Oportunidades em memória: {', '.join(ops) if ops else 'nenhuma ainda.'}"
        old_system = get_system_prompt
        def scout_system():
            return get_system_prompt() + scout_ctx + "\n\nResponde como Morgan Scout — analisa oportunidades de negócio com dados reais."
        # Temporariamente override
        reply_body = _chat_ceo_with_system(user_text, scout_system())
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
        max_tokens=512,
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
            model="claude-sonnet-4-6", max_tokens=512,
            system=system, tools=TOOLS, messages=msgs,
        )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


PWA_DIR = Path(__file__).parent / "pwa"

@app.get("/")
async def serve_interface(request: Request):
    ua = request.headers.get("user-agent", "").lower()
    is_mobile = any(k in ua for k in ["iphone", "android", "mobile", "ipad"])
    if is_mobile:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/pwa/")
    return FileResponse(DESKTOP_DIR / "index_v2.html")

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
        # Guardar no Mem0 em background
        import threading
        threading.Thread(
            target=mem0_add,
            args=("vasco", [{"role": "user", "content": user_text}, {"role": "assistant", "content": full_reply}]),
            daemon=True
        ).start()

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
        mem_vasco = mem0_get("vasco", "Morgan BC Industries negócios trading Moreirense Vasco", limit=15)
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
                                # Guardar troca voz no Mem0 (em background)
                                _last_user = getattr(ws_hume, "_last_user_text", "")
                                if _last_user:
                                    import threading
                                    threading.Thread(
                                        target=mem0_add,
                                        args=("vasco", [{"role": "user", "content": _last_user}, {"role": "assistant", "content": text}]),
                                        daemon=True
                                    ).start()
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
    if _time.time() - _HEARTBEAT_START < 120:
        return False
    if is_pausado():
        return False
    agora = _agora_lisboa()
    from config_service import load_config
    horas = load_config().get("briefing_horas", [7, 20])
    if agora.hour not in horas:
        return False
    return not _dedup_check(f"push_briefing_{agora.strftime('%Y-%m-%d_%H')}")


def _should_run_scout() -> bool:
    agora = _agora_lisboa()
    if agora.weekday() != 6 or agora.hour != 20:
        return False
    return not _dedup_check(f"push_scout_{agora.strftime('%Y-%W')}")


def _build_briefing_prompt(hora: int, extra: dict = None) -> str:
    memoria = load_memory()
    scout_data = load_scout()
    ops = list(scout_data.get("oportunidades", {}).keys())[:3]
    ops_str = ", ".join(ops) if ops else "nenhuma ainda"
    aprovadas = scout_data.get("aprovadas", [])
    aprovadas_str = ", ".join(aprovadas[:3]) if aprovadas else "nenhuma"
    periodo = "matinal" if hora == 7 else "noturno"

    extra = extra or {}
    meteo = extra.get("meteo", "")
    bot_str = extra.get("bot", "")
    proximo_jogo_str = extra.get("proximo_jogo", "")

    blocos = [f"Memória do Vasco:\n{memoria}"]
    if meteo:
        blocos.append(f"Tempo em Moreira de Cónegos: {meteo}")
    if bot_str:
        blocos.append(f"Trading bot: {bot_str}")
    if proximo_jogo_str:
        blocos.append(f"Moreirense: {proximo_jogo_str}")
    blocos.append(f"Scout — oportunidades activas: {ops_str}")
    blocos.append(f"Scout — oportunidades aprovadas: {aprovadas_str}")

    contexto = "\n\n".join(blocos)

    return f"""És o Morgan. Gera o briefing {periodo} para o Vasco. Hora: {hora}h.

{contexto}

Instruções:
- Directamente ao ponto, sem saudações longas
- Se for 7h: foco no que fazer hoje, estado do bot de trading, próximo jogo se relevante, oportunidade mais prioritária do Scout
- Se for 20h: resumo do que aconteceu, o que ficou por fazer, preparação para amanhã, menção ao resultado se houve jogo hoje
- Máximo 7 linhas. Sem emojis. Português europeu."""


async def _run_briefing(hora: int):
    loop = asyncio.get_event_loop()

    # Recolher dados em paralelo para o briefing enriquecido
    extra = {}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://wttr.in/Moreira+de+Conegos?format=%t+%C", timeout=4)
            extra["meteo"] = r.text.strip()
    except Exception:
        pass

    try:
        from trading_bot import get_status as _bot_status
        b = _bot_status()
        extra["bot"] = (
            f"{'ATIVO' if b.get('active') else 'PARADO'} | "
            f"PnL hoje: {b.get('pnl_today', 0):+.2f} USDT | "
            f"PnL total: {b.get('pnl_total', 0):+.2f} USDT | "
            f"Sinal: {b.get('signal', 'hold')}"
        )
    except Exception:
        pass

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
                adv = away if home == "Moreirense" else home
                data_j = f["fixture"]["date"][:10]
                hora_j = f["fixture"]["date"][11:16]
                loc = "casa" if home == "Moreirense" else "fora"
                liga = f["league"]["name"]
                extra["proximo_jogo"] = f"próximo jogo: {adv} ({loc}) — {data_j} {hora_j} | {liga}"
    except Exception:
        pass

    prompt = _build_briefing_prompt(hora, extra)
    # Gera reply com Claude
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
    periodo = "Briefing das 7h" if hora == 7 else "Briefing das 20h"
    # Primeira linha como título, resto como corpo
    linhas = texto.strip().split("\n", 1)
    titulo = f"Morgan — {periodo}"
    corpo = texto.strip()
    send_push(title=titulo, body=corpo[:200], url="/pwa/")
    _dedup_mark(f"push_briefing_{_agora_lisboa().strftime('%Y-%m-%d_%H')}")


async def _run_scout_push():
    scout_data = load_scout()
    ops = scout_data.get("oportunidades", {})
    if not ops:
        corpo = "Nenhuma oportunidade nova esta semana."
    else:
        top = list(ops.items())[:2]
        corpo = " | ".join(f"{n}" for n, _ in top)
    send_push(
        title="Morgan Scout — Relatório Semanal",
        body=corpo[:200],
        url="/pwa/"
    )
    _dedup_mark(f"push_scout_{_agora_lisboa().strftime('%Y-%W')}")


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
        resumo_conv = "\n".join(
            f"  {m['role']}: {str(m.get('content',''))[:120]}"
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
        aprovadas = scout_data.get("aprovadas", [])
        ops_str = ", ".join(aprovadas[:3]) if aprovadas else "nenhuma aprovada"
    except Exception:
        ops_str = "indisponível"

    prompt = f"""És o Morgan. Gera o relatório de fim de dia para o Vasco.
Data: {agora.strftime('%d/%m/%Y')}

CONVERSAS DE HOJE ({n_trocas} trocas):
{resumo_conv}

TRADING BOT:
{bot_str}

SCOUT — OPORTUNIDADES APROVADAS:
{ops_str}

Instruções:
- Resume em linguagem humana o que aconteceu hoje
- O que foi feito, o que ficou por fazer, decisões tomadas
- Estado do bot de trading e se houve algo relevante
- O que o Vasco deve ter em mente amanhã
- Tom direto, sem rodeios. Máximo 8 linhas. Sem emojis. Português europeu."""

    response = await loop.run_in_executor(
        None,
        lambda: claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=get_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )
    )
    texto = response.content[0].text if response.content else "Relatório indisponível."

    # Push — título curto, corpo truncado (push tem limite de ~200 chars visíveis)
    send_push(
        title=f"Morgan — Relatório {agora.strftime('%d/%m')}",
        body=texto[:200],
        url="/pwa/"
    )

    # Guardar relatório completo em ficheiro para consulta posterior
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

            # Scout dominical às 20h
            if _should_run_scout():
                await _run_scout_push()

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
