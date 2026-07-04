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


def hacker_news_trending() -> str:
    """Busca os posts mais relevantes de IA no Hacker News."""
    try:
        # Top stories do HN
        top = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10).json()
        best = requests.get("https://hacker-news.firebaseio.com/v0/beststories.json", timeout=10).json()
        ids = list(dict.fromkeys(top[:50] + best[:50]))[:60]

        palavras_chave = ["ai", "llm", "gpt", "claude", "openai", "anthropic", "machine learning",
                          "artificial intelligence", "agent", "saas", "startup", "revenue", "passive income",
                          "automation", "business", "tool", "product"]
        encontrados = []
        for item_id in ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=5).json()
                titulo = (item.get("title") or "").lower()
                url = item.get("url", "")
                score = item.get("score", 0)
                comentarios = item.get("descendants", 0)
                if any(p in titulo for p in palavras_chave) and score > 50:
                    encontrados.append({
                        "titulo": item.get("title"),
                        "url": url,
                        "score": score,
                        "comentarios": comentarios
                    })
                    if len(encontrados) >= 10:
                        break
            except Exception:
                continue

        if not encontrados:
            return "Nenhum post relevante de IA no Hacker News hoje."

        linhas = ["**Hacker News — Top IA hoje:**\n"]
        for p in encontrados:
            linhas.append(
                f"• **{p['titulo']}** ({p['score']} pontos, {p['comentarios']} comentários)\n"
                f"  {p['url']}"
            )
        return "\n\n".join(linhas)
    except Exception as e:
        return f"Erro Hacker News: {e}"


def reddit_trending() -> str:
    """Busca posts populares de IA e negócios no Reddit via Tavily."""
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        queries = [
            "site:reddit.com r/artificial OR r/MachineLearning AI tools 2026",
            "site:reddit.com r/SideProject OR r/entrepreneur AI business revenue 2026",
            "site:reddit.com r/passive_income OR r/indiehackers AI automation 2026",
        ]
        encontrados = []
        vistas = set()
        for query in queries:
            try:
                result = client.search(query=query, search_depth="basic", max_results=4)
                for r in result.get("results", []):
                    url = r.get("url", "")
                    titulo = r.get("title", "")
                    conteudo = r.get("content", "")[:200]
                    if not url or url in vistas or "reddit.com" not in url:
                        continue
                    vistas.add(url)
                    encontrados.append(f"• **{titulo}**\n  {conteudo}\n  {url}")
            except Exception:
                continue

        if not encontrados:
            return "Nenhum post relevante no Reddit encontrado."

        return "**Reddit — Discussões de IA e negócio:**\n\n" + "\n\n".join(encontrados[:8])
    except Exception as e:
        return f"Erro Reddit: {e}"


def google_trends(termos: list) -> str:
    """Verifica se um conjunto de termos está a crescer ou a decrescer no Google Trends."""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="pt-PT", tz=0, timeout=(10, 25))

        # Máximo 5 termos por chamada
        termos = termos[:5]
        pytrends.build_payload(termos, timeframe="today 3-m", geo="")

        df = pytrends.interest_over_time()
        if df.empty:
            return "Não foi possível obter dados do Google Trends para estes termos."

        linhas = ["**Google Trends — últimos 3 meses:**\n"]
        for termo in termos:
            if termo not in df.columns:
                continue
            serie = df[termo]
            valor_atual = int(serie.iloc[-1])
            valor_inicio = int(serie.iloc[0])
            maximo = int(serie.max())
            if valor_atual > valor_inicio * 1.2:
                tendencia = "↑ Em crescimento"
            elif valor_atual < valor_inicio * 0.8:
                tendencia = "↓ Em declínio"
            else:
                tendencia = "→ Estável"
            linhas.append(
                f"• **{termo}**\n"
                f"  {tendencia} | Agora: {valor_atual}/100 | Pico: {maximo}/100"
            )

        # Regiões com mais interesse
        try:
            by_region = pytrends.interest_by_region(resolution="COUNTRY", inc_low_vol=False)
            if not by_region.empty:
                top = by_region[termos[0]].nlargest(5)
                paises = ", ".join([f"{p} ({v})" for p, v in top.items()])
                linhas.append(f"\nPaíses com mais interesse em **{termos[0]}**: {paises}")
        except Exception:
            pass

        return "\n\n".join(linhas)
    except Exception as e:
        return f"Erro Google Trends: {e}"


def product_hunt_trending() -> str:
    """Busca os produtos de IA mais votados no Product Hunt esta semana."""
    try:
        token = os.getenv("PRODUCT_HUNT_TOKEN")
        if not token:
            return "Product Hunt API não configurada (falta PRODUCT_HUNT_TOKEN)."

        query = """
        {
          posts(order: VOTES, topic: "artificial-intelligence", first: 15) {
            edges {
              node {
                name
                tagline
                description
                votesCount
                website
                reviewsCount
                createdAt
                topics {
                  edges { node { name } }
                }
              }
            }
          }
        }
        """
        response = requests.post(
            "https://api.producthunt.com/v2/api/graphql",
            json={"query": query},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=15,
        )
        data = response.json()
        posts = data.get("data", {}).get("posts", {}).get("edges", [])
        if not posts:
            return "Não foi possível obter dados do Product Hunt."

        linhas = ["**Product Hunt — Top IA desta semana:**\n"]
        for edge in posts[:10]:
            p = edge["node"]
            nome = p.get("name", "")
            tagline = p.get("tagline", "")
            votos = p.get("votesCount", 0)
            site = p.get("website", "")
            topicos = [t["node"]["name"] for t in p.get("topics", {}).get("edges", [])]
            linhas.append(
                f"• **{nome}** ({votos} votos)\n"
                f"  {tagline}\n"
                f"  Tópicos: {', '.join(topicos[:3])}\n"
                f"  {site}"
            )
        return "\n\n".join(linhas)
    except Exception as e:
        return f"Erro Product Hunt: {e}"


def scout_oportunidades() -> str:
    """Analisa o mercado de IA e identifica oportunidades de negócio com potencial de rendimento passivo."""
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        queries = [
            "AI SaaS tools fastest growing revenue 2026 passive income",
            "best AI business opportunities 2026 low competition high margin",
            "AI tools trending Product Hunt 2026 monetization",
            "AI automation business ideas 2026 recurring revenue",
            "AI tools for sports coaches market opportunity 2026",
            "Portuguese Brazilian Spanish AI market opportunities 2026",
            "AI affiliate programs high commission 2026",
            "AI newsletter creator tools audience monetization 2026",
            "micro SaaS AI 2026 solopreneur revenue",
            "AI content creation business profitable niche 2026",
        ]
        resultados = []
        for query in queries:
            try:
                result = client.search(query=query, search_depth="advanced", max_results=3)
                for r in result.get("results", []):
                    titulo = r.get("title", "")
                    conteudo = r.get("content", "")[:300]
                    url = r.get("url", "")
                    if titulo and conteudo:
                        resultados.append(f"• {titulo}\n  {conteudo}\n  Fonte: {url}")
            except Exception:
                continue
        if not resultados:
            return "Não foi possível obter dados de mercado neste momento."
        return "**Dados de mercado recolhidos pelo Morgan AI Scout:**\n\n" + "\n\n".join(resultados[:20])
    except Exception as e:
        return f"Erro no scout de oportunidades: {e}"


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


def indiehackers_trending() -> str:
    """Pesquisa no IndieHackers negócios reais com receita declarada pelos fundadores."""
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        queries = [
            "site:indiehackers.com \"making\" OR \"revenue\" OR \"MRR\" 2025 OR 2026 AI SaaS",
            "site:indiehackers.com passive income AI tools revenue 2026",
            "site:indiehackers.com solo founder $10k MRR 2025 2026",
        ]
        resultados = []
        vistos = set()
        for q in queries:
            try:
                r = client.search(query=q, search_depth="basic", max_results=5)
                for item in r.get("results", []):
                    url = item.get("url", "")
                    if url in vistos:
                        continue
                    vistos.add(url)
                    titulo = item.get("title", "")
                    conteudo = item.get("content", "")[:300]
                    resultados.append(f"• **{titulo}**\n  {conteudo}\n  {url}")
            except Exception:
                continue

        if not resultados:
            return "Não foi possível obter dados do IndieHackers."

        header = "**IndieHackers — negócios reais com receita declarada:**\n"
        return header + "\n\n".join(resultados[:10])
    except Exception as e:
        return f"Erro IndieHackers: {e}"


def aprovar_oportunidade_scout(nome: str) -> str:
    """Marca uma oportunidade do Scout como aprovada pelo Vasco para acompanhamento semanal contínuo."""
    try:
        from scout_memory import aprovar_oportunidade, _load
        data = _load()
        if nome not in data["oportunidades"]:
            return f"Oportunidade '{nome}' não encontrada no histórico do Scout. Verifica o nome exato com `ver_historico_scout`."
        aprovar_oportunidade(nome)
        return f"✅ '{nome}' aprovada. O Scout vai acompanhá-la de perto em cada relatório semanal."
    except Exception as e:
        return f"Erro ao aprovar oportunidade: {e}"


def monitorizar_oportunidades_aprovadas() -> str:
    """Faz pesquisa aprofundada sobre cada oportunidade aprovada pelo Vasco — novidades, concorrentes, receita real, casos de sucesso recentes."""
    try:
        from scout_memory import _load, _save
        from datetime import date
        data = _load()
        aprovadas = data.get("aprovadas", [])
        if not aprovadas:
            return "Nenhuma oportunidade aprovada ainda. Aprova uma oportunidade do relatório do Scout para acompanhamento contínuo."

        client = TavilyClient(api_key=TAVILY_API_KEY)
        semana = date.today().strftime("%Y-W%W")
        relatorio = ["**Acompanhamento de oportunidades aprovadas:**\n"]

        for ap in aprovadas:
            nome = ap["nome"]
            linhas_op = [f"### {nome}"]
            queries = [
                f"{nome} revenue MRR 2025 2026 founder",
                f"{nome} market growth competition 2026",
                f"{nome} how to start build tutorial 2026",
            ]
            resumos = []
            for q in queries:
                try:
                    r = client.search(query=q, search_depth="basic", max_results=3)
                    for item in r.get("results", [])[:2]:
                        conteudo = item.get("content", "")[:250]
                        url = item.get("url", "")
                        resumos.append(f"  • {conteudo} ({url})")
                except Exception:
                    continue
            if resumos:
                linhas_op.extend(resumos[:4])
            else:
                linhas_op.append("  Sem novidades encontradas esta semana.")

            # Guardar update no histórico
            update_entry = {"semana": semana, "resumo": " | ".join(resumos[:2])}
            ap.setdefault("updates", [])
            ap["updates"].append(update_entry)
            ap["updates"] = ap["updates"][-12:]

            relatorio.append("\n".join(linhas_op))

        _save(data)
        return "\n\n".join(relatorio)
    except Exception as e:
        return f"Erro na monitorização de aprovadas: {e}"


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
        "name": "google_trends",
        "description": "Verifica se termos ou nichos de negócio estão a crescer ou a decrescer no Google Trends nos últimos 3 meses. Usa para validar oportunidades antes de recomendar — se o interesse está a crescer é um bom sinal, se está a cair é um alerta. Máximo 5 termos por chamada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "termos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de termos a analisar, ex: ['AI automation', 'passive income AI', 'micro SaaS']. Máximo 5."
                }
            },
            "required": ["termos"]
        }
    },
    {
        "name": "hacker_news_trending",
        "description": "Busca os posts mais relevantes de IA, startups e negócios no Hacker News. Gratuito, sem API key. Usa no relatório do Scout para captar tendências da comunidade tech.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "reddit_trending",
        "description": "Busca posts populares de IA e negócios em subreddits relevantes: artificial, MachineLearning, SideProject, entrepreneur, indiehackers, passive_income, AItools. Gratuito, sem API key.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "product_hunt_trending",
        "description": "Busca os produtos de IA mais votados no Product Hunt esta semana. Usa no relatório do Scout para identificar ferramentas e negócios de IA em crescimento antes de explodirem.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "scout_oportunidades",
        "description": "Analisa o mercado de IA e identifica as melhores oportunidades de negócio com potencial de rendimento passivo. Pesquisa SaaS, afiliados, nichos de conteúdo, automação, mercados PT/BR/ES. Usa no relatório semanal do Morgan AI Scout ou quando o Vasco pede análise de oportunidades.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ver_historico_scout",
        "description": "Mostra o histórico acumulado do Morgan AI Scout: todas as oportunidades identificadas, quantas vezes cada uma apareceu, e quais foram aprovadas pelo Vasco. Usa quando o Vasco pedir para ver o histórico ou acompanhar uma oportunidade específica.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
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
        "name": "indiehackers_trending",
        "description": "Pesquisa no IndieHackers negócios reais com receita declarada pelos fundadores. Fonte de dados honestos sobre quanto dinheiro cada nicho/produto gera na prática. Usa no relatório do Scout para validar se uma oportunidade tem provas reais de receita.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "aprovar_oportunidade_scout",
        "description": "Marca uma oportunidade do Morgan AI Scout como aprovada pelo Vasco para acompanhamento semanal contínuo. Usa quando o Vasco disser 'aprova esta', 'quero acompanhar X', 'marca X para seguimento'. Requer o nome exato da oportunidade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {
                    "type": "string",
                    "description": "Nome exato da oportunidade a aprovar, conforme aparece no histórico do Scout."
                }
            },
            "required": ["nome"]
        }
    },
    {
        "name": "monitorizar_oportunidades_aprovadas",
        "description": "Faz pesquisa aprofundada sobre cada oportunidade aprovada pelo Vasco — novidades, concorrentes, receita real, casos de sucesso recentes. Usa automaticamente no relatório semanal do Scout se houver oportunidades aprovadas.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
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
    "google_trends": google_trends,
    "hacker_news_trending": hacker_news_trending,
    "reddit_trending": reddit_trending,
    "product_hunt_trending": product_hunt_trending,
    "scout_oportunidades": scout_oportunidades,
    "ver_historico_scout": lambda: __import__('scout_memory').get_resumo_para_vasco(),
    "indiehackers_trending": indiehackers_trending,
    "aprovar_oportunidade_scout": lambda nome: aprovar_oportunidade_scout(nome),
    "monitorizar_oportunidades_aprovadas": monitorizar_oportunidades_aprovadas,
}
