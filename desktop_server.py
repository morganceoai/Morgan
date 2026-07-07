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

# Pré-carregar perfil de voz se existir
load_profile()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
CONVAI_AGENT_ID = "agent_0001kwqq04nbe689bpxdtp2dkpc7"
DESKTOP_USER_ID = "vasco"

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
app = FastAPI()
DESKTOP_DIR = Path(__file__).parent / "desktop"

# Histórico de conversa — carregado do disco ao arrancar, persiste entre sessões
conversation_history: list[dict] = get_context_messages(DESKTOP_USER_ID)


def get_system_prompt() -> str:
    memoria = load_memory()
    agora = datetime.now().strftime("%d de %B de %Y, %H:%M")
    return f"""És o Morgan, assistente pessoal do Vasco Botelho da Costa.
Data e hora atual: {agora}

{memoria}

Estás na interface desktop do Morgan — modo de conversa por voz.
Responde de forma natural, concisa e direta. Sem markdown — fala como se estivesses ao lado do Vasco.
Respostas curtas sempre que possível."""


def run_tool(tool_name: str, tool_input: dict) -> str:
    fn = TOOL_FUNCTIONS.get(tool_name)
    if not fn:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        return str(fn(**tool_input))
    except Exception as e:
        return f"Erro em {tool_name}: {e}"


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


def chat_with_morgan(user_text: str) -> str:
    conversation_history.append({"role": "user", "content": user_text})
    store_save(DESKTOP_USER_ID, "user", user_text)

    messages = conversation_history[-30:]
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=get_system_prompt(),
        tools=TOOLS,
        messages=messages,
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
            system=get_system_prompt(), tools=TOOLS,
            messages=conversation_history[-30:],
        )
    reply = "".join(block.text for block in response.content if hasattr(block, "text"))
    conversation_history.append({"role": "assistant", "content": reply})
    store_save(DESKTOP_USER_ID, "assistant", reply)
    return reply


PWA_DIR = Path(__file__).parent / "pwa"

@app.get("/")
async def serve_interface():
    return FileResponse(DESKTOP_DIR / "index.html")

@app.get("/pwa/")
@app.get("/pwa/index.html")
async def serve_pwa():
    return FileResponse(PWA_DIR / "index.html")

@app.get("/pwa/{filename}")
async def serve_pwa_file(filename: str):
    f = PWA_DIR / filename
    if f.exists():
        return FileResponse(f)
    return FileResponse(PWA_DIR / "index.html")


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
