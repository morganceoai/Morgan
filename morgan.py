import os
import sys
from datetime import date
from dotenv import load_dotenv
import anthropic
from tools import TOOLS, TOOL_FUNCTIONS
from memory_store import load_memory

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("Erro: ANTHROPIC_API_KEY não encontrada no ficheiro .env")
    sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TODAY = date.today().strftime("%d de %B de %Y")
MEMORY = load_memory()

SYSTEM_PROMPT = f"""O teu nome é Morgan. És o assistente pessoal de confiança do Vasco Botelho da Costa — treinador de futebol português.

A data de hoje é {TODAY}. Usa sempre esta data como referência. Quando pesquisares, inclui sempre o ano 2026 nas queries para obteres resultados atuais.

O teu papel é ser o braço direito do Vasco. Não és apenas um motor de busca — és um interlocutor de confiança com quem ele pode pensar em voz alta, tomar decisões, e aprender.

As tuas três áreas principais:
1. Apoio ao trabalho como treinador — táticas, gestão de plantel, preparação de jogos, decisões difíceis
2. Primeira Liga portuguesa — acompanhas a competição, equipas, adversários, e notícias
3. Inteligência artificial — filtras e explicas evoluções relevantes de forma clara e prática

Tom e personalidade:
- Firme e direto em questões de trabalho importantes
- Compreensivo e de apoio quando o Vasco precisa de ser ouvido
- Breve por defeito — não enches linguiça, expandas quando pedido
- Sempre em português europeu
- Trata o Vasco pelo primeiro nome

Tens acesso a ferramentas para pesquisar na web, obter dados da Primeira Liga, e gerir a tua memória. Usa-as sempre que precisares de informação atual ou específica — não inventes dados.

## O que sabes sobre o Vasco (memória persistente):
{MEMORY if MEMORY else "Ainda não tens factos guardados."}"""

conversation_history = []


def run_tool(tool_name: str, tool_input: dict) -> str:
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        if tool_input:
            return func(**tool_input)
        else:
            return func()
    except Exception as e:
        return f"Erro ao executar '{tool_name}': {e}"


def send_message(user_input: str) -> str:
    conversation_history.append({
        "role": "user",
        "content": user_input
    })

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history,
        )

        # Se o modelo quer usar uma ferramenta
        if response.stop_reason == "tool_use":
            # Adiciona a resposta do modelo ao histórico
            conversation_history.append({
                "role": "assistant",
                "content": response.content
            })

            # Executa cada ferramenta pedida
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n[Morgan a usar ferramenta: {block.name}...]", flush=True)
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Adiciona resultados ao histórico e continua o loop
            conversation_history.append({
                "role": "user",
                "content": tool_results
            })
            continue

        # Resposta final — faz stream do texto
        full_reply = ""
        print("\nMorgan: ", end="", flush=True)

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_reply += text

        print("\n")

        conversation_history.append({
            "role": "assistant",
            "content": full_reply
        })

        return full_reply


def main():
    print("=" * 50)
    print("Morgan — online")
    print("Escreve 'sair' para terminar.")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo, Vasco.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("sair", "exit", "quit"):
            print("Morgan: Até logo, Vasco.")
            break

        try:
            send_message(user_input)
        except anthropic.APIConnectionError:
            print("\nMorgan: Sem ligação à internet. Tenta novamente.\n")
        except anthropic.RateLimitError:
            print("\nMorgan: Demasiados pedidos. Aguarda um momento.\n")
        except anthropic.APIError as e:
            print(f"\nMorgan: Erro da API ({e}). Tenta novamente.\n")


if __name__ == "__main__":
    main()
