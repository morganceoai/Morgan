import os
import requests
from memory_store import save_fact, remove_fact, list_memory

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

PRIMEIRA_LIGA_ID = 94
CURRENT_SEASON = 2026


def _pesquisar_exa(query: str, num_results: int = 5) -> list[dict]:
    """Pesquisa semântica via Exa AI — retorna lista de {title, content, url}."""
    if not EXA_API_KEY:
        return []
    try:
        from exa_py import Exa
        exa = Exa(api_key=EXA_API_KEY)
        results = exa.search_and_contents(query, num_results=num_results, text={"max_characters": 500})
        return [{"title": r.title or "", "content": r.text or "", "url": r.url or ""} for r in results.results]
    except Exception:
        return []


def _pesquisar_tavily(query: str, num_results: int = 5) -> list[dict]:
    """Pesquisa via Tavily — retorna lista de {title, content, url}."""
    if not TAVILY_API_KEY:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        result = client.search(query=query, search_depth="advanced", max_results=num_results)
        return [{"title": r.get("title",""), "content": r.get("content",""), "url": r.get("url","")} for r in result.get("results", [])]
    except Exception:
        return []


def _pesquisar_brave(query: str, num_results: int = 5) -> list[dict]:
    """Pesquisa via Brave Search API (2000 req/mês gratuitas)."""
    if not BRAVE_API_KEY:
        return []
    try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY},
            params={"q": query, "count": num_results, "text_decorations": False},
            timeout=10
        )
        data = r.json()
        results = []
        for item in data.get("web", {}).get("results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "content": item.get("description", ""),
                "url": item.get("url", ""),
            })
        return results
    except Exception:
        return []


def _pesquisar_duckduckgo(query: str, num_results: int = 5) -> list[dict]:
    """Pesquisa via DuckDuckGo — gratuita, sem API key."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        return [{"title": r.get("title",""), "content": r.get("body",""), "url": r.get("href","")} for r in results]
    except Exception:
        return []


def _perplexity(query: str, modelo: str, max_tokens: int = 1500) -> str:
    """Chamada base à API Perplexity Sonar."""
    if not PERPLEXITY_API_KEY:
        return ""
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": modelo,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": query}],
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return ""


def pesquisar_web(query: str, modo: str = "auto") -> str:
    """Pesquisa na web com cascade: Perplexity Sonar → Exa → Tavily → Brave → DuckDuckGo."""
    if "2026" not in query and "2025" not in query:
        query = f"{query} 2026"

    # Perplexity Sonar como fonte primária (sintetiza + cita fontes)
    resposta = _perplexity(query, "sonar")
    if resposta:
        return f"{resposta}\n\n[Perplexity Sonar]"

    # Fallbacks baseados em resultados brutos
    resultados: list[dict] = []
    if modo == "semantico":
        resultados = _pesquisar_exa(query)
    elif modo == "noticias":
        resultados = _pesquisar_tavily(query) or _pesquisar_duckduckgo(query)
    else:
        resultados = (
            _pesquisar_exa(query) or
            _pesquisar_tavily(query) or
            _pesquisar_brave(query) or
            _pesquisar_duckduckgo(query)
        )

    if not resultados:
        return "Não encontrei resultados para essa pesquisa (todas as fontes indisponíveis)."

    output = []
    for r in resultados[:5]:
        if r.get("title") or r.get("content"):
            output.append(f"**{r['title']}**\n{r['content']}\nFonte: {r['url']}")
    return "\n\n---\n\n".join(output) if output else "Sem resultados."


def pesquisar_mercado(query: str) -> str:
    """Scout — análise de oportunidades de mercado via Perplexity sonar-pro.
    Melhor cobertura e síntese que sonar base. Fallback para pesquisar_web.
    """
    resposta = _perplexity(
        f"{query}\n\nResponde com dados concretos, números reais e fontes. Mínimo 3 fontes citadas.",
        modelo="sonar-pro",
        max_tokens=2000,
    )
    return resposta if resposta else pesquisar_web(query)


def pesquisar_oportunidade_profunda(query: str) -> str:
    """Scout — deep research para oportunidades que passaram o filtro inicial.
    Usa sonar-deep-research: múltiplas rondas de pesquisa, análise aprofundada.
    """
    resposta = _perplexity(
        f"{query}\n\nFaz uma análise aprofundada: mercado, concorrência, dimensão, tendências, riscos. Cita fontes concretas.",
        modelo="sonar-deep-research",
        max_tokens=3000,
    )
    return resposta if resposta else pesquisar_mercado(query)


def pesquisar_arquitectura(query: str) -> str:
    """Creator — pesquisa de arquitecturas técnicas e best practices via sonar-reasoning-pro.
    Raciocínio chain-of-thought para avaliar trade-offs técnicos.
    """
    resposta = _perplexity(
        f"{query}\n\nAnalisa as melhores opções com pros/cons técnicos, casos de uso reais e recomendação final.",
        modelo="sonar-reasoning-pro",
        max_tokens=2000,
    )
    return resposta if resposta else pesquisar_web(query)


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
    """Analisa tendências de interesse via Tavily (pytrends arquivado em Abril 2025)."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        termos = termos[:5]
        linhas = ["**Tendências de mercado — análise via web:**\n"]

        for termo in termos:
            queries = [
                f"{termo} trending growing 2026",
                f"{termo} site:reddit.com OR site:producthunt.com interest 2026",
            ]
            resumos = []
            for q in queries:
                try:
                    r = client.search(query=q, search_depth="basic", max_results=3)
                    for item in r.get("results", []):
                        conteudo = item.get("content", "")[:180]
                        if conteudo:
                            resumos.append(conteudo)
                except Exception:
                    continue

            if resumos:
                linhas.append(f"• **{termo}**\n  " + resumos[0])
            else:
                linhas.append(f"• **{termo}** — sem dados de tendência disponíveis.")

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
            # Máximo retorno, mínimo risco — mercado global
            "highest ROI AI business 2026 low risk passive income proven founder",
            "AI SaaS highest revenue lowest competition 2026 solopreneur indiehackers",
            "best passive income AI business 2026 real founders revenue data case study",
            # Mercados com pouca concorrência e alta margem
            "AI niche tools underserved market high margin 2026 recurring revenue",
            "micro SaaS AI vertical niche 2026 10k month monopoly founder",
            # Modelos de negócio validados com dados reais
            "AI automation agency 5k 10k month 2026 case study real revenue",
            "AI tools subscription revenue 2026 low churn high retention profitable",
            # Oportunidades emergentes com vantagem de primeiro a chegar
            "AI business opportunity early 2026 untapped market growing fast first mover",
            "new AI tools category 2026 no competition blue ocean niche",
            # Mercados lusófonos — pesquisa em inglês mas foco na vantagem de língua
            "Portuguese language market AI tools gap opportunity 2026 Brazil Portugal",
            "non-English AI SaaS market opportunity 2026 underserved language",
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


# ── Ferramentas do Solver ────────────────────────────────────────────────────

import subprocess
from pathlib import Path

MORGAN_DIR = Path(__file__).parent
ALLOWED_DIRS = [MORGAN_DIR, MORGAN_DIR / "memory", MORGAN_DIR / "desktop"]

# Comandos de diagnóstico permitidos (read-only, seguros)
_CMD_WHITELIST = ["ps", "grep", "tail", "head", "cat", "ls", "wc", "df", "free",
                  "python3", "pip", "git log", "git status", "git diff"]


def solver_ler_ficheiro(caminho: str) -> str:
    """Lê um ficheiro do sistema Morgan."""
    try:
        p = Path(caminho)
        if not p.is_absolute():
            p = MORGAN_DIR / caminho
        p = p.resolve()
        # Segurança: só dentro do dir Morgan
        if not any(str(p).startswith(str(d.resolve())) for d in ALLOWED_DIRS):
            return f"Acesso negado: {caminho} está fora do directório Morgan."
        if not p.exists():
            return f"Ficheiro não encontrado: {caminho}"
        content = p.read_text(encoding="utf-8", errors="replace")
        # Limita a 8000 chars para não explodir o contexto
        if len(content) > 8000:
            content = content[-8000:]
            return f"[Truncado — últimas 8000 chars]\n{content}"
        return content
    except Exception as e:
        return f"Erro a ler ficheiro: {e}"


def solver_executar_diagnostico(comando: str) -> str:
    """Executa um comando de diagnóstico (read-only). Requer aprovação para comandos que modificam."""
    try:
        # Verifica se o comando é permitido
        cmd_base = comando.strip().split()[0] if comando.strip() else ""
        permitido = any(comando.strip().startswith(w) for w in _CMD_WHITELIST)
        if not permitido:
            return f"Comando '{cmd_base}' não está na lista de comandos permitidos para diagnóstico automático. Pede confirmação ao Vasco antes de executar."
        result = subprocess.run(
            comando, shell=True, capture_output=True, text=True,
            cwd=str(MORGAN_DIR), timeout=30
        )
        output = result.stdout + result.stderr
        if len(output) > 4000:
            output = output[-4000:]
        return output or "(sem output)"
    except subprocess.TimeoutExpired:
        return "Comando excedeu 30 segundos — abortado."
    except Exception as e:
        return f"Erro a executar comando: {e}"


def solver_verificar_saude() -> str:
    """Verifica a saúde dos serviços principais do Morgan."""
    import os
    resultados = []

    # Verifica variáveis de ambiente críticas
    vars_criticas = ["ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY",
                     "DEEPGRAM_API_KEY", "TAVILY_API_KEY"]
    em_falta = [v for v in vars_criticas if not os.getenv(v)]
    if em_falta:
        resultados.append(f"ERRO: Variáveis em falta: {', '.join(em_falta)}")
    else:
        resultados.append("OK: Todas as variáveis de ambiente críticas presentes.")

    # Verifica ficheiros de memória
    # Críticos — devem sempre existir
    criticos = ["memory/audit.log", "memory/factos.md"]
    # Auto-criados — só existem após primeiro ciclo, não são erro
    auto_criados = ["memory/heartbeat_state.json", "memory/scout_memoria.json"]

    for f in criticos:
        p = MORGAN_DIR / f
        if p.exists():
            resultados.append(f"OK: {f} ({p.stat().st_size} bytes)")
        else:
            resultados.append(f"ERRO: {f} não existe — ficheiro crítico em falta")

    for f in auto_criados:
        p = MORGAN_DIR / f
        if p.exists():
            resultados.append(f"OK: {f} ({p.stat().st_size} bytes)")
        else:
            resultados.append(f"INFO: {f} ainda não existe — criado automaticamente no primeiro ciclo (normal)")

    # Últimas entradas do audit log — só conta linhas cuja TAG termina em _ERRO/_ERROR
    audit_path = MORGAN_DIR / "memory" / "audit.log"
    if audit_path.exists():
        lines = audit_path.read_text().splitlines()
        def _e_erro(linha: str) -> bool:
            partes = linha.split(" | ", 1)
            if not partes:
                return False
            tag = partes[0].split()[-1] if partes[0].split() else ""
            return tag.upper().endswith(("_ERRO", "_ERROR", "ERRO", "ERROR"))
        erros = [l for l in lines[-200:] if _e_erro(l)]
        if erros:
            resultados.append(f"\nERROS reais no audit ({len(erros)} encontrados):")
            resultados.extend(erros[-5:])
        else:
            resultados.append("OK: Sem erros reais recentes no audit.log.")

    return "\n".join(resultados)


def solver_analisar_logs(linhas: int = 100) -> str:
    """Lê as últimas N linhas do audit.log."""
    try:
        audit_path = MORGAN_DIR / "memory" / "audit.log"
        if not audit_path.exists():
            return "audit.log não encontrado."
        content = audit_path.read_text(encoding="utf-8").splitlines()
        ultimas = content[-linhas:]
        return "\n".join(ultimas)
    except Exception as e:
        return f"Erro a ler audit.log: {e}"


def solver_git_log() -> str:
    """Mostra os últimos commits do repositório para o Solver verificar o que foi deployado."""
    try:
        result = subprocess.run(
            "git log --oneline -10",
            shell=True, capture_output=True, text=True,
            cwd=str(MORGAN_DIR), timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "Sem commits encontrados."
    except Exception as e:
        return f"Erro: {e}"


def solver_git_diff() -> str:
    """Mostra as alterações pendentes no repositório (read-only, sem confirmação)."""
    try:
        result = subprocess.run(
            "git diff HEAD --stat && git diff HEAD",
            shell=True, capture_output=True, text=True,
            cwd=str(MORGAN_DIR), timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        return output[:6000] if output else "Sem alterações pendentes."
    except Exception as e:
        return f"Erro: {e}"


def solver_git_commit_push(mensagem: str) -> str:
    """Faz git add, commit e push. REQUER confirmação prévia do Vasco."""
    import os
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return "GITHUB_TOKEN não configurado no Railway. Adiciona a variável de ambiente primeiro."
    try:
        # Configura remote com token para autenticação
        remote_url = f"https://{token}@github.com/morganceoai/Morgan.git"
        cmds = [
            f"git remote set-url origin {remote_url}",
            "git config user.email 'solver@morgan.ai'",
            "git config user.name 'Morgan Solver'",
            "git add -A",
            f"git commit -m '{mensagem}'",
            "git push origin main",
        ]
        for cmd in cmds:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               cwd=str(MORGAN_DIR), timeout=60)
            if r.returncode != 0 and "nothing to commit" not in r.stdout:
                return f"Erro em '{cmd}':\n{r.stderr or r.stdout}"
        return "Commit e push concluídos com sucesso."
    except Exception as e:
        return f"Erro: {e}"


def solver_mac_mini_logs(linhas: int = 50) -> str:
    """Obtém as últimas N linhas do log do Morgan no Mac Mini via SSH."""
    import subprocess
    host = os.getenv("MAC_MINI_HOST", "100.100.15.110")
    user = os.getenv("MAC_MINI_USER", "bcvertex")
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=no",
             f"{user}@{host}", f"tail -{linhas} /Users/bcvertex/Morgan/morgan_server.log"],
            capture_output=True, text=True, timeout=15
        )
        output = (result.stdout + result.stderr).strip()
        return output or "(sem output)"
    except Exception as e:
        return f"Erro SSH Mac Mini: {e}"


def solver_editar_ficheiro(caminho: str, texto_antigo: str, texto_novo: str) -> str:
    """Edição cirúrgica — substitui texto_antigo por texto_novo num ficheiro. Mais seguro que reescrever o ficheiro inteiro."""
    try:
        p = Path(caminho)
        if not p.is_absolute():
            p = MORGAN_DIR / caminho
        p = p.resolve()
        if not any(str(p).startswith(str(d.resolve())) for d in ALLOWED_DIRS):
            return f"Acesso negado: {caminho} está fora do directório Morgan."
        if not p.exists():
            return f"Ficheiro não encontrado: {caminho}"
        conteudo = p.read_text(encoding="utf-8")
        if texto_antigo not in conteudo:
            return f"Texto não encontrado no ficheiro. Confirma o texto exacto a substituir."
        novo_conteudo = conteudo.replace(texto_antigo, texto_novo, 1)
        p.write_text(novo_conteudo, encoding="utf-8")
        return f"Edição aplicada em {caminho}."
    except Exception as e:
        return f"Erro a editar ficheiro: {e}"


def solver_criar_ficheiro(caminho: str, conteudo: str) -> str:
    """Cria ou sobrescreve um ficheiro no sistema Morgan. REQUER confirmação prévia do Vasco."""
    try:
        p = Path(caminho)
        if not p.is_absolute():
            p = MORGAN_DIR / caminho
        p = p.resolve()
        if not any(str(p).startswith(str(d.resolve())) for d in ALLOWED_DIRS):
            return f"Acesso negado: {caminho} está fora do directório Morgan."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")
        return f"Ficheiro criado/actualizado: {caminho} ({len(conteudo)} chars)"
    except Exception as e:
        return f"Erro a criar ficheiro: {e}"


def solver_executar_correcao(comando: str) -> str:
    """Executa um comando de correcção após aprovação do Vasco. Regista no audit."""
    try:
        result = subprocess.run(
            comando, shell=True, capture_output=True, text=True,
            cwd=str(MORGAN_DIR), timeout=60
        )
        output = (result.stdout + result.stderr).strip()
        if len(output) > 3000:
            output = output[-3000:]
        status = "OK" if result.returncode == 0 else f"ERRO (código {result.returncode})"
        return f"{status}\n{output}" if output else status
    except subprocess.TimeoutExpired:
        return "Comando excedeu 60 segundos — abortado."
    except Exception as e:
        return f"Erro: {e}"


def consultar_historico_imperio() -> str:
    """Lê o ficheiro de histórico do império — usado pelos agentes quando precisam de contexto passado."""
    try:
        hist = Path(__file__).parent / "memory" / "historico_imperio.md"
        return hist.read_text(encoding="utf-8") if hist.exists() else "Histórico ainda não existe."
    except Exception as e:
        return f"Erro ao ler histórico: {e}"


def atualizar_estado_imperio(seccao: str, conteudo: str) -> str:
    """Atualiza uma secção do estado_imperio.md. Chamado pelo CEO após decisões relevantes."""
    try:
        f = Path(__file__).parent / "memory" / "estado_imperio.md"
        texto = f.read_text(encoding="utf-8") if f.exists() else ""
        # Acrescenta ao log de últimas ações
        from datetime import datetime
        linha_nova = f"- {datetime.now().strftime('%d/%m/%Y')}: {conteudo}"
        if "## Histórico de acções relevantes" in texto:
            texto = texto.replace(
                "## Histórico de acções relevantes",
                f"## Histórico de acções relevantes\n{linha_nova}"
            )
        else:
            texto += f"\n\n## Histórico de acções relevantes\n{linha_nova}"
        f.write_text(texto, encoding="utf-8")
        return f"estado_imperio.md atualizado: {conteudo[:80]}"
    except Exception as e:
        return f"Erro ao atualizar estado: {e}"


def listar_google_drive(pasta: str = "root", max_itens: int = 20) -> str:
    """
    Lista ficheiros e pastas do Google Drive do Vasco.
    Requer GOOGLE_SERVICE_ACCOUNT_JSON ou GOOGLE_OAUTH_TOKEN no .env.
    Sem credenciais: devolve instrução de setup.
    """
    import os
    token = os.getenv("GOOGLE_OAUTH_TOKEN", "")
    service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not token and not service_account:
        return (
            "Google Drive não configurado. Para ativar:\n"
            "1. Vai a https://console.cloud.google.com → APIs & Services → Enable Google Drive API\n"
            "2. Cria OAuth 2.0 Client ID → copia o token de acesso\n"
            "3. Adiciona GOOGLE_OAUTH_TOKEN=... ao .env do Mac Mini"
        )

    try:
        import httpx
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "q": f"'{pasta}' in parents and trashed=false" if pasta != "root" else "trashed=false",
            "fields": "files(id,name,mimeType,modifiedTime,size)",
            "pageSize": max_itens,
            "orderBy": "modifiedTime desc",
        }
        r = httpx.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=10)
        if r.status_code == 401:
            return "Google Drive: token expirado. Renova GOOGLE_OAUTH_TOKEN no .env."
        data = r.json()
        files = data.get("files", [])
        if not files:
            return "Google Drive: pasta vazia ou sem acesso."
        linhas = [f"Google Drive — {len(files)} itens (pasta: {pasta}):"]
        for f in files:
            tipo = "📁" if "folder" in f.get("mimeType", "") else "📄"
            tamanho = f" ({int(f['size'])//1024}KB)" if f.get("size") else ""
            data_mod = f.get("modifiedTime", "")[:10]
            linhas.append(f"  {tipo} {f['name']}{tamanho} · {data_mod}")
        return "\n".join(linhas)
    except Exception as e:
        return f"Google Drive erro: {e}"


def organizar_google_drive_sugestoes() -> str:
    """
    Analisa o Google Drive e sugere organização em pastas por categoria.
    Não move ficheiros — só sugere. O Vasco decide.
    """
    conteudo = listar_google_drive(max_itens=50)
    if "não configurado" in conteudo or "erro" in conteudo.lower():
        return conteudo

    import anthropic as _a, os
    client = _a.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    r = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": f"""Analisa esta listagem do Google Drive e sugere uma estrutura de pastas mais organizada:

{conteudo}

Propõe: máximo 6 pastas de topo com nomes claros. Para cada pasta, lista que tipo de ficheiros devem ir para lá.
Formato direto, sem rodeios. Português europeu."""}]
    )
    return r.content[0].text if r.content else "Sugestão indisponível."


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
        "name": "solver_mac_mini_logs",
        "description": "Obtém as últimas N linhas do log do Morgan no Mac Mini via SSH. Usa para diagnosticar erros em produção.",
        "input_schema": {
            "type": "object",
            "properties": {
                "linhas": {"type": "integer", "description": "Número de linhas de log a obter. Default: 50."}
            },
            "required": []
        }
    },
    {
        "name": "pesquisar_mercado",
        "description": "Síntese de mercado via Perplexity (se disponível) ou pesquisa semântica Exa. Ideal para o Scout validar uma oportunidade com dados reais antes de propor ao CEO. Retorna análise sintetizada com fontes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Pergunta de mercado. Ex: 'TAM mercado CRM freelancers global 2026 receita real founders'"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "solver_ler_ficheiro",
        "description": "Lê um ficheiro do sistema Morgan. Usa para inspecionar código, configurações, ou ficheiros de memória durante diagnóstico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {"type": "string", "description": "Caminho do ficheiro (relativo ao dir Morgan ou absoluto). Ex: 'desktop_server.py', 'memory/audit.log'"}
            },
            "required": ["caminho"]
        }
    },
    {
        "name": "solver_executar_diagnostico",
        "description": "Executa um comando de diagnóstico seguro (ps, grep, tail, git log, etc.). Apenas comandos read-only permitidos. Para comandos que modificam, pede sempre confirmação ao Vasco.",
        "input_schema": {
            "type": "object",
            "properties": {
                "comando": {"type": "string", "description": "Comando bash de diagnóstico. Ex: 'ps aux | grep python', 'tail -50 memory/audit.log'"}
            },
            "required": ["comando"]
        }
    },
    {
        "name": "solver_verificar_saude",
        "description": "Verifica a saúde geral do sistema Morgan: variáveis de ambiente, ficheiros de memória, erros recentes no audit.log. Usa sempre que o Solver é invocado ou quando há suspeita de problema.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "solver_analisar_logs",
        "description": "Lê as últimas N linhas do audit.log para diagnóstico de erros.",
        "input_schema": {
            "type": "object",
            "properties": {
                "linhas": {"type": "integer", "description": "Número de linhas a ler. Default: 100."}
            },
            "required": []
        }
    },
    {
        "name": "solver_git_log",
        "description": "Mostra os últimos 10 commits do repositório. Usa para verificar o que já foi deployado em produção antes de diagnosticar um problema.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "solver_git_diff",
        "description": "Mostra as alterações pendentes no repositório — o que mudou e ainda não foi commitado. Usa antes de fazer commit para confirmar o que vai ser enviado.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "solver_git_commit_push",
        "description": "Faz git add, commit e push para o GitHub. APENAS após aprovação explícita do Vasco via pedir_confirmacao. Mostra sempre o diff antes de pedir aprovação.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mensagem": {"type": "string", "description": "Mensagem do commit. Descritiva e clara."}
            },
            "required": ["mensagem"]
        }
    },
    {
        "name": "solver_mac_mini_restart",
        "description": "Reinicia o servidor Morgan no Mac Mini via SSH. APENAS após aprovação explícita do Vasco.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "solver_editar_ficheiro",
        "description": "Edição cirúrgica de um ficheiro — substitui texto_antigo por texto_novo. Mais seguro que reescrever o ficheiro inteiro. APENAS usa após aprovação do Vasco.",
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {"type": "string", "description": "Caminho do ficheiro relativo ao dir Morgan."},
                "texto_antigo": {"type": "string", "description": "Texto exacto a substituir."},
                "texto_novo": {"type": "string", "description": "Texto de substituição."}
            },
            "required": ["caminho", "texto_antigo", "texto_novo"]
        }
    },
    {
        "name": "solver_criar_ficheiro",
        "description": "Cria ou actualiza um ficheiro no sistema Morgan. APENAS usa após o Vasco aprovar explicitamente via pedir_confirmacao. Nunca uses sem aprovação.",
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {"type": "string", "description": "Caminho do ficheiro relativo ao dir Morgan. Ex: 'memory/scout_memoria.json'"},
                "conteudo": {"type": "string", "description": "Conteúdo completo a escrever no ficheiro."}
            },
            "required": ["caminho", "conteudo"]
        }
    },
    {
        "name": "solver_executar_correcao",
        "description": "Executa um comando de correcção após aprovação explícita do Vasco. APENAS usa após pedir_confirmacao ser aprovado. Para diagnóstico usa solver_executar_diagnostico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "comando": {"type": "string", "description": "Comando bash a executar para aplicar a correcção."}
            },
            "required": ["comando"]
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
                    "description": "Descrição clara e concisa da ação a confirmar."
                }
            },
            "required": ["acao"]
        }
    },
    {
        "name": "consultar_historico_imperio",
        "description": "Consulta o histórico de ações passadas do império BC Industries. Usa quando precisas de contexto histórico — decisões antigas, semanas anteriores do Scout, arquitectura explicada. Não carregado por defeito — só consulta quando relevante.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "atualizar_estado_imperio",
        "description": "Atualiza o estado_imperio.md com uma nova entrada no log de ações. Usa após tomar decisões relevantes — aprovação de oportunidade, criação de sub-Morgan, resolução de problema, mudança de arquitectura.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seccao": {"type": "string", "description": "Secção a atualizar (ex: 'Últimas ações', 'Oportunidades')"},
                "conteudo": {"type": "string", "description": "O que registar, em 1-2 linhas."}
            },
            "required": ["seccao", "conteudo"]
        }
    },
    {
        "name": "listar_google_drive",
        "description": "Lista ficheiros e pastas do Google Drive do Vasco. Usa quando o Vasco pedir para ver, encontrar ou organizar ficheiros na cloud.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pasta": {"type": "string", "description": "ID da pasta ou 'root' para a raiz", "default": "root"},
                "max_itens": {"type": "integer", "description": "Máximo de itens a listar (padrão 20)", "default": 20}
            },
            "required": []
        }
    },
    {
        "name": "organizar_google_drive_sugestoes",
        "description": "Analisa o Google Drive do Vasco e sugere uma estrutura de organização em pastas. Não move ficheiros — só sugere.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "creator_listar_agentes",
        "description": "Lista todos os agentes Python existentes no projecto Morgan.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "creator_construir_agente",
        "description": "Cria um novo agente Morgan de forma autónoma: gera o código Python com IA, escreve o ficheiro e integra no desktop. Pede sempre confirmação ao Vasco antes do deploy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome do agente em minúsculas sem espaços (ex: 'operator', 'marketeer_v2')"},
                "descricao": {"type": "string", "description": "O que o agente faz — descrição completa"},
                "capacidades": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de capacidades específicas do agente"
                },
                "keywords_trigger": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Palavras-chave que activam este agente na conversa"
                }
            },
            "required": ["nome", "descricao", "capacidades", "keywords_trigger"]
        }
    },
    {
        "name": "creator_rever_agente",
        "description": "Mostra o código do agente gerado para revisão antes do deploy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome do agente (sem _agent.py)"}
            },
            "required": ["nome"]
        }
    },
    {
        "name": "creator_deploy_agente",
        "description": "Faz deploy de um agente já criado: git commit + push + SSH pull + restart do servidor no Mac Mini. Usar APENAS após aprovação explícita do Vasco.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome do agente (sem _agent.py)"},
                "mensagem_commit": {"type": "string", "description": "Mensagem de commit git (opcional)"}
            },
            "required": ["nome"]
        }
    },
    {
        "name": "criar_conta_plataforma",
        "description": "Usa browser automation (Playwright) para criar conta numa plataforma web. Preenche formulário de registo e submete. Requer aprovação do Vasco. Não automatiza 2FA.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plataforma": {"type": "string", "description": "Nome da plataforma (ex: 'Gumroad', 'Pinterest')"},
                "url_registo": {"type": "string", "description": "URL da página de registo"},
                "email": {"type": "string", "description": "Email a usar (conta Zoho)"},
                "password": {"type": "string", "description": "Password a definir"},
                "dados_extra": {"type": "object", "description": "Campos adicionais: nome, empresa, etc.", "additionalProperties": {"type": "string"}}
            },
            "required": ["plataforma", "url_registo", "email", "password"]
        }
    },
    {
        "name": "verificar_email_confirmacao",
        "description": "Verifica o email Zoho à procura de um email de confirmação de conta. Extrai e devolve o URL de confirmação.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remetente_keywords": {"type": "array", "items": {"type": "string"}, "description": "Palavras-chave do remetente (ex: ['etsy', 'noreply'])"},
                "assunto_keywords": {"type": "array", "items": {"type": "string"}, "description": "Palavras-chave do assunto (ex: ['confirm', 'verify'])"},
                "minutos": {"type": "integer", "description": "Janela de tempo em minutos (padrão: 10)"}
            },
            "required": ["remetente_keywords"]
        }
    },
    {
        "name": "registar_negocio_sistema",
        "description": "Regista um novo negócio no sistema Morgan — propaga conhecimento a todos os agentes (CEO, Marketeer, Operator, Solver, CFO) via Mem0.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chave": {"type": "string", "description": "Identificador único em minúsculas sem espaços (ex: 'directorio_pt')"},
                "nome": {"type": "string", "description": "Nome legível do negócio"},
                "tipo": {"type": "string", "description": "Tipo: etsy, saas, servico, directorio, etc."},
                "plataforma": {"type": "string", "description": "Plataforma principal (ex: etsy.com, gumroad.com)"},
                "descricao": {"type": "string", "description": "Descrição do que o negócio faz"},
                "email": {"type": "string", "description": "Email associado ao negócio"}
            },
            "required": ["chave", "nome", "tipo", "plataforma", "descricao"]
        }
    },
    {
        "name": "estado_sistema",
        "description": "Devolve o estado completo do sistema Morgan: agentes activos, negócios activos, contas Zoho.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
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
    "solver_ler_ficheiro": solver_ler_ficheiro,
    "solver_executar_diagnostico": solver_executar_diagnostico,
    "solver_verificar_saude": solver_verificar_saude,
    "solver_analisar_logs": solver_analisar_logs,
    "solver_editar_ficheiro": solver_editar_ficheiro,
    "solver_criar_ficheiro": solver_criar_ficheiro,
    "solver_executar_correcao": solver_executar_correcao,
    "solver_git_log": solver_git_log,
    "solver_git_diff": solver_git_diff,
    "solver_git_commit_push": solver_git_commit_push,
    "solver_mac_mini_logs": lambda linhas=50: solver_mac_mini_logs(linhas),
    "solver_mac_mini_restart": lambda: solver_executar_correcao(
        "ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no bcvertex@100.100.15.110 "
        "'launchctl kickstart -k gui/$(id -u)/com.bcvertex.morgan'"
    ),
    "pesquisar_mercado": pesquisar_mercado,
    "consultar_historico_imperio": consultar_historico_imperio,
    "atualizar_estado_imperio": atualizar_estado_imperio,
    "listar_google_drive": listar_google_drive,
    "organizar_google_drive_sugestoes": organizar_google_drive_sugestoes,
    "creator_listar_agentes": lambda: __import__('creator_agent').listar_agentes(),
    "creator_construir_agente": lambda nome, descricao, capacidades, keywords_trigger: (
        __import__('json').dumps(
            __import__('creator_agent').construir_agente(nome, descricao, capacidades, keywords_trigger, auto_deploy=False),
            ensure_ascii=False, indent=2
        )
    ),
    "creator_rever_agente": lambda nome: __import__('creator_agent').rever_agente(nome),
    "creator_deploy_agente": lambda nome, mensagem_commit="": (
        __import__('json').dumps(
            __import__('creator_agent').deploy_agente(nome, mensagem_commit),
            ensure_ascii=False, indent=2
        )
    ),
    "criar_conta_plataforma": lambda plataforma, url_registo, email, password, dados_extra=None: (
        __import__('automation_service').criar_conta_plataforma(plataforma, url_registo, email, password, dados_extra)
    ),
    "verificar_email_confirmacao": lambda remetente_keywords, assunto_keywords=None, minutos=10: (
        __import__('automation_service').verificar_email_confirmacao(remetente_keywords, assunto_keywords, minutos) or "Nenhum email de confirmação encontrado ainda."
    ),
    "registar_negocio_sistema": lambda chave, nome, tipo, plataforma, descricao, email="": (
        __import__('sistema_service').registar_negocio(chave, nome, tipo, plataforma, descricao, email)
    ),
    "estado_sistema": lambda: __import__('json').dumps(
        __import__('sistema_service').get_estado(), ensure_ascii=False, indent=2
    ),
}
