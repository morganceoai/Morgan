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
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import anthropic
import requests as req
from deepgram import DeepgramClient
from elevenlabs import ElevenLabs
from tools import TOOLS, TOOL_FUNCTIONS
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


# ── Heartbeat ────────────────────────────────────────────────────────────────

CHECKS = [
    {
        "nome": "moreirense_noticias",
        "descricao": "Pesquisa notícias recentes de hoje sobre o Moreirense FC em 2026. Resultados, lesões, transferências, declarações, rumores. Se não houver nada genuinamente novo hoje, responde apenas: NADA",
    },
    {
        "nome": "primeira_liga_noticias",
        "descricao": "Pesquisa notícias recentes de hoje da Primeira Liga portuguesa em 2026 — todos os clubes. Resultados, transferências, rumores, destaques. Se não houver nada genuinamente novo hoje, responde apenas: NADA",
    },
    {
        "nome": "mencoes_vasco",
        "descricao": 'Pesquisa menções a "Vasco Botelho da Costa" em todas as plataformas em 2026. Se não houver nenhuma menção nova, responde apenas: NADA',
    },
    {
        "nome": "novidades_ia",
        "descricao": "Pesquisa novidades importantes de inteligência artificial em 2026 — novos modelos, ferramentas úteis para treinadores. Se não houver nada genuinamente novo, responde apenas: NADA",
    },
]

PREFIXOS = {
    "moreirense_noticias": "Vasco, em relação ao Moreirense",
    "primeira_liga_noticias": "Vasco, em relação à Primeira Liga",
    "mencoes_vasco": "Vasco, encontrei referências ao teu nome",
    "novidades_ia": "Vasco, em relação à inteligência artificial",
}


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


async def heartbeat_loop(app):
    await asyncio.sleep(10)
    audit("HEARTBEAT", "Iniciado — briefings às 7h e 20h")

    while True:
        try:
            if is_pausado():
                await asyncio.sleep(60)
                continue

            if not should_run_briefing():
                await asyncio.sleep(60)
                continue

            mark_briefing_done()
            audit("HEARTBEAT", f"Briefing das {datetime.now().hour}h iniciado")

            for check in CHECKS:
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
        reply = get_morgan_reply(user_id, user_message)
    except Exception as e:
        reply = f"Ocorreu um erro: {e}"

    if update.message.voice and ELEVENLABS_VOICE_ID:
        # Envia texto imediatamente enquanto gera o áudio
        await update.message.reply_text(reply)
        try:
            audio = elevenlabs_client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
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


MENCOES_FILE = os.path.join(BASE_DIR, "memory", "mencoes_enviadas.json")

MENCOES_CHECKS = [
    'site:reddit.com "Vasco Botelho da Costa" 2026',
    'site:youtube.com "Vasco Botelho da Costa" 2026',
    '"Vasco Botelho da Costa" site:x.com OR site:twitter.com 2026',
    '"Vasco Botelho da Costa" -site:record.pt -site:abola.pt 2026',
]


def load_mencoes_enviadas() -> list:
    if not os.path.exists(MENCOES_FILE):
        return []
    with open(MENCOES_FILE, "r") as f:
        return json.load(f)


def mencao_ja_enviada(url: str) -> bool:
    return url in load_mencoes_enviadas()


def marcar_mencao_enviada(url: str):
    enviadas = load_mencoes_enviadas()
    if url not in enviadas:
        enviadas.append(url)
        enviadas = enviadas[-500:]
        with open(MENCOES_FILE, "w") as f:
            json.dump(enviadas, f, indent=2)


async def mencoes_loop(app):
    await asyncio.sleep(30)
    audit("MENCOES", "Loop de monitorização do nome iniciado — verifica a cada 2h")

    while True:
        try:
            if is_pausado() or is_quiet_hours():
                await asyncio.sleep(600)
                continue

            from tavily import TavilyClient
            tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

            for query in MENCOES_CHECKS:
                try:
                    result = tavily.search(query=query, search_depth="basic", max_results=3)
                    for r in result.get("results", []):
                        url = r.get("url", "")
                        titulo = r.get("title", "")
                        conteudo = r.get("content", "")[:300]
                        if not url or mencao_ja_enviada(url):
                            continue
                        # Confirma que é mesmo sobre Vasco
                        if "vasco botelho da costa" not in (titulo + conteudo).lower():
                            continue
                        marcar_mencao_enviada(url)
                        plataforma = "Reddit" if "reddit" in url else "YouTube" if "youtube" in url else "X/Twitter" if "twitter" in url or "x.com" in url else "Web"
                        mensagem = (
                            f"⚠️ *Vasco, encontrei uma menção ao teu nome*\n\n"
                            f"*Plataforma:* {plataforma}\n"
                            f"*Título:* {titulo}\n"
                            f"*Resumo:* {conteudo}\n"
                            f"*Link:* {url}"
                        )
                        await app.bot.send_message(
                            chat_id=TELEGRAM_CHAT_ID,
                            text=mensagem,
                            parse_mode="Markdown"
                        )
                        audit("MENCAO_ENCONTRADA", f"{plataforma} | {url}")
                except Exception as e:
                    audit("MENCOES_ERRO", str(e))

            await asyncio.sleep(7200)  # verifica a cada 2 horas

        except Exception as e:
            audit("MENCOES_LOOP_ERRO", str(e))
            await asyncio.sleep(600)


async def post_init(app):
    asyncio.create_task(heartbeat_loop(app))
    asyncio.create_task(mencoes_loop(app))


def main():
    print("Morgan — online (conversa + heartbeat + Tier 6)")
    print("Kill switch: envia 'morgan pausa' / 'morgan continua' no Telegram")
    print("Ctrl+C para terminar.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).post_init(post_init).build()
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
