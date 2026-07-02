import os
import json
import time
import logging
import asyncio
import tempfile
from datetime import date, datetime
from dotenv import load_dotenv
import yaml
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import anthropic
import requests as req
from deepgram import DeepgramClient
from tools import TOOLS, TOOL_FUNCTIONS
from memory_store import load_memory
from conversation_store import get_context_messages, save_message

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
deepgram_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

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

Tom: firme e direto no trabalho, compreensivo e de apoio quando necessário. Sempre em português europeu. Trata o Vasco pelo primeiro nome.

Tens acesso a ferramentas para pesquisar na web, obter dados da Primeira Liga, e gerir a tua memória.

## O que sabes sobre o Vasco:
{load_memory()}

## Quando o Vasco pedir notícias ou um resumo do que se passa, faz SEMPRE estas três pesquisas:
1. Notícias recentes do Moreirense FC em 2026 (resultados, lesões, transferências, rumores)
2. Notícias da Primeira Liga portuguesa em 2026 — todos os clubes
3. Menções a "Vasco Botelho da Costa" em qualquer plataforma em 2026

Para cada pesquisa, distingue factos confirmados de rumores. Só partilha notícias de 2026.

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
        save_message(user_id, "assistant", reply)
        audit("RESPOSTA", reply[:100])

        if len(history) > 100:
            conversation_histories[user_id] = history[-100:]

        return reply


# ── Heartbeat ────────────────────────────────────────────────────────────────

def get_checks() -> list:
    config = load_config()
    intervalos = config.get("intervalos", {})
    return [
        {
            "nome": "moreirense_noticias",
            "descricao": "Pesquisa notícias recentes de 2026 sobre o Moreirense FC. Resultados, lesões, transferências, declarações, rumores.",
            "intervalo_minutos": intervalos.get("moreirense_noticias", 60),
        },
        {
            "nome": "primeira_liga_noticias",
            "descricao": "Pesquisa notícias recentes de 2026 da Primeira Liga portuguesa — todos os clubes. Resultados, transferências, rumores, destaques.",
            "intervalo_minutos": intervalos.get("primeira_liga_noticias", 120),
        },
        {
            "nome": "mencoes_vasco",
            "descricao": 'Pesquisa menções a "Vasco Botelho da Costa" em todas as plataformas em 2026.',
            "intervalo_minutos": intervalos.get("mencoes_vasco", 90),
        },
        {
            "nome": "novidades_ia",
            "descricao": "Pesquisa novidades importantes de inteligência artificial em 2026 — novos modelos, ferramentas úteis para treinadores.",
            "intervalo_minutos": intervalos.get("novidades_ia", 360),
        },
    ]


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


async def heartbeat_loop(app):
    await asyncio.sleep(10)
    audit("HEARTBEAT", "Iniciado")

    while True:
        try:
            if is_pausado():
                await asyncio.sleep(60)
                continue

            state = load_state()
            checks = get_checks()

            for check in checks:
                nome = check["nome"]
                intervalo = check["intervalo_minutos"] * 60
                ultima_vez = state.get(nome, 0)

                if time.time() - ultima_vez < intervalo:
                    continue

                audit("HEARTBEAT_CHECK", nome)
                resultado = run_heartbeat_check(check)
                state[nome] = time.time()
                save_state(state)

                if resultado:
                    if already_sent(resultado):
                        audit("HEARTBEAT_IGNORADO", resultado[:60])
                    elif is_quiet_hours():
                        audit("HEARTBEAT_SILENCIO", resultado[:60])
                    else:
                        await app.bot.send_message(
                            chat_id=TELEGRAM_CHAT_ID,
                            text=f"🔔 *Morgan*\n\n{resultado}",
                            parse_mode="Markdown"
                        )
                        mark_sent(resultado)
                        if TELEGRAM_CHAT_ID not in conversation_histories:
                            conversation_histories[TELEGRAM_CHAT_ID] = []
                        conversation_histories[TELEGRAM_CHAT_ID].append({
                            "role": "assistant",
                            "content": resultado
                        })
                        audit("HEARTBEAT_ENVIADO", resultado[:60])

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
        reply = get_morgan_reply(user_id, user_message)
    except Exception as e:
        reply = f"Ocorreu um erro: {e}"

    await update.message.reply_text(reply)


async def post_init(app):
    asyncio.create_task(heartbeat_loop(app))


def main():
    print("Morgan — online (conversa + heartbeat + Tier 6)")
    print("Kill switch: envia 'morgan pausa' / 'morgan continua' no Telegram")
    print("Ctrl+C para terminar.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).post_init(post_init).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
