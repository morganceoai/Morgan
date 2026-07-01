import os
import json
import time
import logging
from datetime import date, datetime
from dotenv import load_dotenv
import anthropic
import requests
from tools import TOOLS, TOOL_FUNCTIONS
from memory_store import load_memory

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

STATE_FILE = os.path.join(os.path.dirname(__file__), "memory", "heartbeat_state.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "memory", "heartbeat_log.txt")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M"
)

QUIET_HOURS_START = 23
QUIET_HOURS_END = 7

FONTES_CREDÍVEIS = ["record.pt", "abola.pt", "ojogo.pt", "maisfutebol.iol.pt", "zerozero.pt", "sporttv.pt", "rtp.pt", "cmjornal.pt", "sapo.pt"]
FONTES_RUMOR = ["tiktok", "reddit", "twitter", "x.com", "youtube", "forum", "instagram"]

CHECKS = [
    {
        "nome": "moreirense_noticias",
        "descricao": f"""Pesquisa notícias recentes sobre o Moreirense FC em 2026. Procura: resultados, lesões, transferências, declarações, rumores, qualquer novidade.

Fontes credíveis (partilha como facto): {', '.join(FONTES_CREDÍVEIS)}
Outras fontes (partilha como rumor com aviso): redes sociais, fóruns, YouTube, TikTok, Reddit.

Formato para factos confirmados: partilha diretamente.
Formato para rumores: começa sempre com "Vasco, não tenho a certeza se isto é verdade ou não, mas partilho contigo esta informação:"

Se não houver nada novo, responde: NADA""",
        "intervalo_minutos": 60,
    },
    {
        "nome": "primeira_liga_noticias",
        "descricao": f"""Pesquisa notícias recentes da Primeira Liga portuguesa em 2026 — todos os clubes. Resultados, transferências, rumores, polémicas, destaques táticos.

Fontes credíveis (partilha como facto): {', '.join(FONTES_CREDÍVEIS)}
Outras fontes (partilha como rumor com aviso): redes sociais, fóruns, YouTube, TikTok, Reddit.

Formato para factos confirmados: partilha diretamente.
Formato para rumores: começa sempre com "Vasco, não tenho a certeza se isto é verdade ou não, mas partilho contigo esta informação:"

Se não houver nada novo, responde: NADA""",
        "intervalo_minutos": 120,
    },
    {
        "nome": "mencoes_vasco",
        "descricao": """Pesquisa menções a "Vasco Botelho da Costa" em todas as plataformas: Reddit, X/Twitter, TikTok, YouTube, fóruns, notícias, seja onde for.

Se encontrares qualquer menção, partilha SEMPRE — mesmo que seja um simples comentário.
Para menções em fontes credíveis: partilha como facto.
Para menções em redes sociais ou fóruns: começa com "Vasco, encontrei uma menção ao teu nome que pode ou não ser relevante:"

Se não houver nenhuma menção, responde: NADA""",
        "intervalo_minutos": 90,
    },
    {
        "nome": "novidades_ia",
        "descricao": """Pesquisa novidades importantes de inteligência artificial em 2026 — novos modelos, ferramentas úteis para treinadores de futebol, evoluções relevantes.

Só partilha se for genuinamente relevante e novo. Fontes técnicas e jornalísticas credíveis.
Se não houver nada novo, responde: NADA""",
        "intervalo_minutos": 360,
    },
]


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_quiet_hours() -> bool:
    hora = datetime.now().hour
    if QUIET_HOURS_START <= hora or hora < QUIET_HOURS_END:
        return True
    return False


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
        logging.info(f"Mensagem enviada: {message[:80]}...")
    except Exception as e:
        logging.error(f"Erro ao enviar Telegram: {e}")


def run_tool(tool_name: str, tool_input: dict) -> str:
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        return func(**tool_input) if tool_input else func()
    except Exception as e:
        return f"Erro: {e}"


def run_check(check: dict) -> str | None:
    TODAY = date.today().strftime("%d de %B de %Y")
    MEMORY = load_memory()

    system = f"""És o Morgan, assistente pessoal do Vasco Botelho da Costa, treinador do Moreirense FC.
A data de hoje é {TODAY}.

## Memória:
{MEMORY}

## Regras absolutas:
1. USA SEMPRE as ferramentas de pesquisa — nunca inventes nada nem uses conhecimento do teu treino.
2. VERIFICA SEMPRE A DATA — só partilha notícias de 2026. Se a data não estiver clara, ignora essa notícia.
3. Para cada informação, identifica a fonte e avalia a sua credibilidade.
4. Fontes credíveis ({', '.join(FONTES_CREDÍVEIS)}): partilha como facto confirmado, inclui a fonte.
5. Fontes de redes sociais, fóruns, TikTok, Reddit, YouTube: partilha sempre como rumor, começando com "Vasco, não tenho a certeza se isto é verdade ou não, mas partilho contigo esta informação:"
6. Menções ao nome "Vasco Botelho da Costa": partilha SEMPRE, seja de que fonte for.
7. Se não houver nada de 2026, responde apenas: NADA
8. Sê breve e direto — máximo 3 pontos por mensagem."""

    messages = [{"role": "user", "content": check["descricao"]}]

    while True:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
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
        if reply.upper() == "NADA":
            return None
        return reply


def main():
    print("Morgan Heartbeat — online")
    print(f"A verificar a cada ciclo. Horas de silêncio: {QUIET_HOURS_START}h-{QUIET_HOURS_END}h")
    print("Ctrl+C para parar.")
    logging.info("Heartbeat iniciado.")

    while True:
        try:
            state = load_state()
            now = datetime.now()

            for check in CHECKS:
                nome = check["nome"]
                intervalo = check["intervalo_minutos"] * 60
                ultima_vez = state.get(nome, 0)

                if time.time() - ultima_vez < intervalo:
                    continue

                print(f"[{now.strftime('%H:%M')}] A verificar: {nome}...")
                logging.info(f"Check: {nome}")

                resultado = run_check(check)
                state[nome] = time.time()
                save_state(state)

                if resultado:
                    if is_quiet_hours():
                        logging.info(f"Horas de silêncio — guardado para depois: {resultado[:60]}")
                        print(f"  → Horas de silêncio. Guardado para depois.")
                    else:
                        send_telegram(f"🔔 *Morgan*\n\n{resultado}")
                        print(f"  → Enviado ao Vasco.")
                else:
                    print(f"  → Nada relevante.")

            time.sleep(60)

        except KeyboardInterrupt:
            print("\nHeartbeat parado.")
            logging.info("Heartbeat parado.")
            break
        except Exception as e:
            logging.error(f"Erro no heartbeat: {e}")
            print(f"Erro: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
