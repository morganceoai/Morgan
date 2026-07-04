import os
import requests
from tavily import TavilyClient
from memory_store import save_fact, remove_fact, list_memory

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

PRIMEIRA_LIGA_ID = 94
CURRENT_SEASON = 2026


def pesquisar_web(query: str) -> str:
    """Pesquisa na web e devolve um resumo dos resultados."""
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        # Garante resultados recentes adicionando o ano se não estiver na query
        if "2026" not in query and "2025" not in query:
            query = f"{query} 2026"
        result = client.search(query=query, search_depth="advanced", max_results=5)
        if not result.get("results"):
            return "Não encontrei resultados para essa pesquisa."
        output = []
        for r in result["results"]:
            output.append(f"**{r['title']}**\n{r['content']}\nFonte: {r['url']}")
        return "\n\n---\n\n".join(output)
    except Exception as e:
        return f"Erro na pesquisa web: {e}"


def classificacao_primeira_liga() -> str:
    """Devolve a classificação atual da Primeira Liga portuguesa."""
    try:
        url = "https://v3.football.api-sports.io/standings"
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        params = {"league": PRIMEIRA_LIGA_ID, "season": CURRENT_SEASON}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        standings = data["response"][0]["league"]["standings"][0]
        lines = ["**Classificação — Primeira Liga**\n"]
        for team in standings:
            pos = team["rank"]
            nome = team["team"]["name"]
            pts = team["points"]
            jogos = team["all"]["played"]
            v = team["all"]["win"]
            e = team["all"]["draw"]
            d = team["all"]["lose"]
            gm = team["all"]["goals"]["for"]
            gs = team["all"]["goals"]["against"]
            lines.append(f"{pos}. {nome} — {pts}pts ({jogos}j: {v}V {e}E {d}D) GM:{gm} GS:{gs}")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao obter classificação: {e}"


def proximos_jogos(equipa: str) -> str:
    """Devolve os próximos jogos de uma equipa na Primeira Liga."""
    try:
        # Primeiro encontrar o ID da equipa
        url_teams = "https://v3.football.api-sports.io/teams"
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        params = {"name": equipa, "league": PRIMEIRA_LIGA_ID, "season": CURRENT_SEASON}
        r = requests.get(url_teams, headers=headers, params=params, timeout=10)
        teams_data = r.json()

        if not teams_data["response"]:
            return f"Não encontrei a equipa '{equipa}' na Primeira Liga."

        team_id = teams_data["response"][0]["team"]["id"]
        team_name = teams_data["response"][0]["team"]["name"]

        # Buscar próximos jogos
        url_fixtures = "https://v3.football.api-sports.io/fixtures"
        params = {"team": team_id, "league": PRIMEIRA_LIGA_ID, "season": CURRENT_SEASON, "next": 5}
        r = requests.get(url_fixtures, headers=headers, params=params, timeout=10)
        fixtures_data = r.json()

        if not fixtures_data["response"]:
            return f"Não encontrei próximos jogos para {team_name}."

        lines = [f"**Próximos jogos — {team_name}**\n"]
        for f in fixtures_data["response"]:
            data = f["fixture"]["date"][:10]
            casa = f["teams"]["home"]["name"]
            fora = f["teams"]["away"]["name"]
            lines.append(f"{data}: {casa} vs {fora}")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao obter jogos: {e}"


def resultados_recentes(equipa: str) -> str:
    """Devolve os últimos resultados de uma equipa na Primeira Liga."""
    try:
        url_teams = "https://v3.football.api-sports.io/teams"
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        params = {"name": equipa, "league": PRIMEIRA_LIGA_ID, "season": CURRENT_SEASON}
        r = requests.get(url_teams, headers=headers, params=params, timeout=10)
        teams_data = r.json()

        if not teams_data["response"]:
            return f"Não encontrei a equipa '{equipa}' na Primeira Liga."

        team_id = teams_data["response"][0]["team"]["id"]
        team_name = teams_data["response"][0]["team"]["name"]

        url_fixtures = "https://v3.football.api-sports.io/fixtures"
        params = {"team": team_id, "league": PRIMEIRA_LIGA_ID, "season": CURRENT_SEASON, "last": 5}
        r = requests.get(url_fixtures, headers=headers, params=params, timeout=10)
        fixtures_data = r.json()

        if not fixtures_data["response"]:
            return f"Não encontrei resultados recentes para {team_name}."

        lines = [f"**Últimos resultados — {team_name}**\n"]
        for f in fixtures_data["response"]:
            data = f["fixture"]["date"][:10]
            casa = f["teams"]["home"]["name"]
            fora = f["teams"]["away"]["name"]
            gols_casa = f["goals"]["home"]
            gols_fora = f["goals"]["away"]
            lines.append(f"{data}: {casa} {gols_casa} - {gols_fora} {fora}")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao obter resultados: {e}"


def monitorizar_nome(nome: str = "Vasco Botelho da Costa") -> str:
    """Pesquisa menções ao nome em múltiplas plataformas."""
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        queries = [
            f'"{nome}" site:reddit.com 2026',
            f'"{nome}" site:youtube.com 2026',
            f'"{nome}" site:x.com OR site:twitter.com 2026',
            f'"{nome}" site:facebook.com 2026',
            f'"{nome}" site:instagram.com 2026',
            f'"{nome}" site:tiktok.com 2026',
            f'"{nome}" site:linkedin.com 2026',
            f'"{nome}" site:zerozero.pt OR site:maisfutebol.iol.pt OR site:abola.pt 2026',
            f'"{nome}" site:transfermarkt.pt OR site:transfermarkt.com 2026',
            f'"{nome}" -site:reddit.com -site:youtube.com -site:twitter.com -site:x.com -site:facebook.com -site:instagram.com -site:tiktok.com 2026',
        ]
        encontradas = []
        vistas = set()
        for query in queries:
            try:
                result = client.search(query=query, search_depth="basic", max_results=3)
                for r in result.get("results", []):
                    url = r.get("url", "")
                    titulo = r.get("title", "")
                    conteudo = r.get("content", "")[:200]
                    if not url or url in vistas:
                        continue
                    if nome.lower() not in (titulo + conteudo).lower():
                        continue
                    vistas.add(url)
                    plataforma = (
                        "Reddit" if "reddit.com" in url else
                        "YouTube" if "youtube.com" in url else
                        "X/Twitter" if "x.com" in url or "twitter.com" in url else
                        "Facebook" if "facebook.com" in url else
                        "Instagram" if "instagram.com" in url else
                        "TikTok" if "tiktok.com" in url else
                        "LinkedIn" if "linkedin.com" in url else
                        "Transfermarkt" if "transfermarkt" in url else
                        "ZeroZero" if "zerozero.pt" in url else
                        "Web"
                    )
                    encontradas.append(f"**{plataforma}** — {titulo}\n{conteudo}\nFonte: {url}")
            except Exception:
                continue
        if not encontradas:
            return "Não encontrei menções ao teu nome em nenhuma plataforma."
        return f"**Menções a '{nome}'**\n\n" + "\n\n---\n\n".join(encontradas)
    except Exception as e:
        return f"Erro na monitorização do nome: {e}"


# Registo de todas as tools disponíveis para o Morgan
TOOLS = [
    {
        "name": "pesquisar_web",
        "description": "Pesquisa na web sobre qualquer tema — notícias, análises táticas, novidades de IA, informações gerais. Usa quando precisas de informação atual ou específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "O que pesquisar. Sê específico para melhores resultados."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "classificacao_primeira_liga",
        "description": "Devolve a classificação atual da Primeira Liga portuguesa com pontos, jogos, vitórias, empates, derrotas e golos.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "proximos_jogos",
        "description": "Devolve os próximos jogos de uma equipa na Primeira Liga portuguesa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipa": {
                    "type": "string",
                    "description": "Nome da equipa, ex: 'Benfica', 'Porto', 'Sporting'"
                }
            },
            "required": ["equipa"]
        }
    },
    {
        "name": "resultados_recentes",
        "description": "Devolve os últimos 5 resultados de uma equipa na Primeira Liga portuguesa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipa": {
                    "type": "string",
                    "description": "Nome da equipa, ex: 'Benfica', 'Porto', 'Sporting'"
                }
            },
            "required": ["equipa"]
        }
    },
    {
        "name": "guardar_facto",
        "description": "Guarda um facto durável sobre o Vasco, as suas preferências, a sua equipa, ou qualquer coisa que deva ser lembrada entre sessões. Usa quando o Vasco te pedir para lembrares algo, ou quando aprenderes algo importante sobre ele.",
        "input_schema": {
            "type": "object",
            "properties": {
                "facto": {
                    "type": "string",
                    "description": "O facto a guardar, escrito como uma frase clara e direta. Ex: 'O Vasco prefere treinos de manhã' ou 'A equipa do Vasco joga em 4-3-3'."
                }
            },
            "required": ["facto"]
        }
    },
    {
        "name": "remover_facto",
        "description": "Remove um facto da memória quando já não é verdade ou o Vasco pedir para esquecer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "facto": {
                    "type": "string",
                    "description": "Palavra-chave ou parte do facto a remover."
                }
            },
            "required": ["facto"]
        }
    },
    {
        "name": "ver_memoria",
        "description": "Mostra tudo o que o Morgan tem guardado na memória sobre o Vasco.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "monitorizar_nome",
        "description": "Pesquisa menções ao nome 'Vasco Botelho da Costa' em múltiplas plataformas: Reddit, YouTube, X/Twitter, Facebook, Instagram, TikTok, LinkedIn, Transfermarkt, ZeroZero, e web em geral. Usa nos briefings e sempre que o Vasco pedir para verificar o que se diz sobre ele.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {
                    "type": "string",
                    "description": "Nome a pesquisar. Por defeito: 'Vasco Botelho da Costa'."
                }
            },
            "required": []
        }
    },
    {
        "name": "pedir_confirmacao",
        "description": "Pede confirmação ao Vasco antes de executar uma ação sensível. Usa SEMPRE esta ferramenta antes de enviar mensagens, apagar ou criar ficheiros, gastar dinheiro, ou alterar configurações. Nunca executes essas ações sem confirmação explícita.",
        "input_schema": {
            "type": "object",
            "properties": {
                "acao": {
                    "type": "string",
                    "description": "Descrição clara e concisa da ação a confirmar. Ex: 'enviar email ao teu agente a dizer que estás disponível para conversas'"
                }
            },
            "required": ["acao"]
        }
    }
]

# Mapa de nome para função
TOOL_FUNCTIONS = {
    "pesquisar_web": pesquisar_web,
    "classificacao_primeira_liga": classificacao_primeira_liga,
    "proximos_jogos": proximos_jogos,
    "resultados_recentes": resultados_recentes,
    "guardar_facto": lambda facto: save_fact(facto),
    "remover_facto": lambda facto: remove_fact(facto),
    "ver_memoria": list_memory,
    "pedir_confirmacao": lambda acao: f"__CONFIRMACAO__:{acao}",
    "monitorizar_nome": lambda nome="Vasco Botelho da Costa": monitorizar_nome(nome),
}
