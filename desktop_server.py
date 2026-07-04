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

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import anthropic

from tools import TOOLS, TOOL_FUNCTIONS
from memory_store import load_memory
from scout_memory import _load as load_scout

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

app = FastAPI()

# Histórico de conversa da sessão desktop (separado do Telegram)
conversation_history: list[dict] = []

DESKTOP_DIR = Path(__file__).parent / "desktop"


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


def chat_with_morgan(user_text: str) -> str:
    conversation_history.append({"role": "user", "content": user_text})

    messages = conversation_history[-30:]
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
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
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        conversation_history.append({"role": "assistant", "content": assistant_content})
        conversation_history.append({"role": "user", "content": tool_results})

        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=get_system_prompt(),
            tools=TOOLS,
            messages=conversation_history[-30:],
        )

    reply = ""
    for block in response.content:
        if hasattr(block, "text"):
            reply += block.text

    conversation_history.append({"role": "assistant", "content": reply})
    return reply


@app.get("/")
async def serve_interface():
    return FileResponse(DESKTOP_DIR / "index.html")


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
    scout_data = load_scout()
    total_ops = len(scout_data.get("oportunidades", {}))
    aprovadas = len(scout_data.get("aprovadas", []))
    recorrentes = [
        nome for nome, info in scout_data.get("oportunidades", {}).items()
        if info.get("vezes_visto", 0) >= 2
    ]

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
        "scout": {"total": total_ops, "aprovadas": aprovadas, "recorrentes": recorrentes[:3]},
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
