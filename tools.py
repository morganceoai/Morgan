import os
import requests
from memory_store import save_fact, remove_fact, list_memory, consultar_base

try:
    from tavily import TavilyClient as _TavilyClient
    _TAVILY_AVAILABLE = True
except ImportError:
    _TAVILY_AVAILABLE = False
    _TavilyClient = None

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
        results = exa.search(query, num_results=num_results)
        return [{"title": r.title or "", "content": getattr(r, "text", "") or "", "url": r.url or ""} for r in results.results]
    except Exception:
        return []


def _pesquisar_tavily(query: str, num_results: int = 5) -> list[dict]:
    """Pesquisa via Tavily — retorna lista de {title, content, url}."""
    if not TAVILY_API_KEY:
        return []
    try:
        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return []
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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
        from ddgs import DDGS
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


def _formatar_resultados(resultados: list[dict], max_results: int = 5) -> str:
    output = []
    for r in resultados[:max_results]:
        if r.get("title") or r.get("content"):
            output.append(f"**{r['title']}**\n{r['content']}\nFonte: {r['url']}")
    return "\n\n---\n\n".join(output) if output else "Sem resultados."


# ── CASCATA DE PESQUISA POR AGENTE ─────────────────────────────────────────────

# Cascade por agente: lista ordenada de ferramentas a tentar.
# Cada entry é um nome de ferramenta. DDG é sempre o último safety net.
AGENT_CASCADE: dict[str, list[str]] = {
    "ceo":       ["exa", "tavily", "perplexity", "ddg"],
    "scout":     ["perplexity_pro", "exa", "tavily", "ddg"],
    "coach":     ["ddg", "exa"],
    "cfo":       ["perplexity", "exa", "ddg"],
    "creator":   ["perplexity_reasoning", "exa", "ddg"],
    "marketeer": ["exa", "tavily", "ddg"],
    "operator":  ["tavily", "exa", "ddg"],
    "solver":    ["exa", "perplexity_reasoning", "ddg"],
}

# Palavras-chave que indicam queries simples → ir directamente ao DDG sem gastar créditos
_SIMPLE_QUERY_PATTERNS = (
    "tempo em ", "temperatura ", "previsão meteorológica", "weather ",
    "que horas são", "que dia é", "fuso horário", "hora em ",
    "como chegar", "distância entre", "quanto tempo demora",
    "o que é ", "definição de ", "significado de ",
    "tradução de ", "traduzir ", "como se diz ",
    "quem é ", "quantos anos tem ", "data de nascimento",
    "capital de ", "moeda de ", "população de ",
)


def _e_query_simples(query: str) -> bool:
    """Detecta queries factuais simples que não justificam usar créditos de APIs pagas."""
    q = query.lower()
    return any(p in q for p in _SIMPLE_QUERY_PATTERNS)


def _notificar_solver_erro(ferramenta: str, query: str, erro: str) -> None:
    """Regista erro inesperado num ficheiro para o Solver processar autonomamente."""
    import json
    from pathlib import Path
    from datetime import datetime, timezone
    erros_path = Path(__file__).parent / "memory" / "search_errors.json"
    try:
        erros = json.loads(erros_path.read_text()) if erros_path.exists() else []
        erros.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "ferramenta": ferramenta,
            "query": query[:200],
            "erro": str(erro)[:500],
            "resolvido": False,
        })
        # manter apenas os últimos 100 erros
        erros_path.write_text(json.dumps(erros[-100:], ensure_ascii=False, indent=2))
    except Exception:
        pass  # falha silenciosa — não bloquear o fluxo principal


def _executar_ferramenta(nome: str, query: str) -> list[dict] | str | None:
    """
    Executa uma ferramenta de pesquisa pelo nome.
    Retorna lista de resultados, string (Perplexity), ou None se falhou.
    Regista no Solver se o erro for inesperado (não é limite de quota).
    """
    try:
        if nome == "exa":
            r = _pesquisar_exa(query)
            if not r:
                return None
            return r
        elif nome == "tavily":
            r = _pesquisar_tavily(query)
            if not r:
                return None
            return r
        elif nome == "ddg":
            r = _pesquisar_duckduckgo(query)
            return r  # DDG pode devolver lista vazia, mas nunca falha com erro
        elif nome == "perplexity":
            r = _perplexity(query, modelo="sonar", max_tokens=800)
            return r if r else None
        elif nome == "perplexity_pro":
            r = _perplexity(query, modelo="sonar-pro", max_tokens=1500)
            return r if r else None
        elif nome == "perplexity_reasoning":
            r = _perplexity(query, modelo="sonar-reasoning-pro", max_tokens=1500)
            return r if r else None
        else:
            return None
    except Exception as e:
        erro_str = str(e).lower()
        # Erros de quota/limite são esperados — não notificar Solver
        is_limit = any(w in erro_str for w in ("quota", "limit", "rate", "429", "402", "credits", "exceeded"))
        if not is_limit:
            _notificar_solver_erro(nome, query, str(e))
        return None


def pesquisar(query: str, agente: str = "ceo", tipo: str = "auto") -> str:
    """
    Pesquisa na web com cascata específica por agente.
    - Queries simples (tempo, hora, definições) → DDG directamente, sem gastar créditos.
    - Cascade silenciosa: se uma ferramenta falhar, passa à seguinte.
    - Erros inesperados (não quota) são registados em memory/search_errors.json.
    - DDG é sempre o safety net final — nunca falha.
    """
    if "2026" not in query and "2025" not in query and tipo == "auto":
        query = f"{query} 2026"

    cascade = AGENT_CASCADE.get(agente, AGENT_CASCADE["ceo"])

    # Queries simples: ignorar ferramentas pagas e ir directamente ao DDG
    if _e_query_simples(query) and tipo == "auto":
        resultados = _pesquisar_duckduckgo(query)
        return _formatar_resultados(resultados) if resultados else "Não encontrei resultados."

    for ferramenta in cascade:
        resultado = _executar_ferramenta(ferramenta, query)
        if resultado is None:
            continue
        # Perplexity devolve string directamente
        if isinstance(resultado, str) and resultado.strip():
            return resultado
        # Ferramentas de lista
        if isinstance(resultado, list) and resultado:
            return _formatar_resultados(resultado)

    return "Não encontrei resultados para essa pesquisa."


def pesquisar_web(query: str, modo: str = "auto") -> str:
    """Wrapper de compatibilidade → pesquisar(agente='ceo').
    Mantido para não quebrar chamadas existentes.
    """
    return pesquisar(query, agente="ceo", tipo=modo)


def pesquisar_noticias(query: str) -> str:
    """Notícias recentes: Tavily → Exa → DDG. DDG como safety net."""
    resultados = (
        _pesquisar_tavily(query) or
        _pesquisar_exa(query) or
        _pesquisar_duckduckgo(query)
    )
    if not resultados:
        return "Não encontrei notícias recentes para essa query."
    return _formatar_resultados(resultados)


# ── FIRECRAWL ──────────────────────────────────────────────────────────────────

def scrape_url(url: str, formato: str = "markdown") -> str:
    """
    Extrai conteúdo limpo de qualquer URL e devolve markdown pronto para LLM.
    Usa Firecrawl. Útil para: analisar listings Etsy de concorrentes, ler páginas
    de diretórios, extrair conteúdo de sites sem API.
    500 créditos/mês gratuitos (FIRECRAWL_API_KEY no .env).
    """
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        return "Firecrawl não configurado — adicionar FIRECRAWL_API_KEY ao .env."
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=api_key)
        result = app.scrape_url(url, formats=[formato])
        content = getattr(result, "markdown", None) or getattr(result, "content", None) or str(result)
        return content[:4000] if content else "Sem conteúdo extraído."
    except ImportError:
        return "firecrawl-py não instalado. Corre: pip install firecrawl-py"
    except Exception as e:
        return f"Firecrawl erro: {e}"


def pesquisar_e_scrape(query: str, num_resultados: int = 3) -> str:
    """
    Pesquisa na web e extrai conteúdo completo dos resultados (não apenas snippets).
    Usa Firecrawl crawl sobre resultados Exa. Para análise profunda de concorrentes,
    extracção de leads de diretórios, research de mercado detalhado.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        # fallback para pesquisa normal
        return pesquisar_web(query)
    resultados_exa = _pesquisar_exa(query, num_results=num_resultados)
    if not resultados_exa:
        return pesquisar_web(query)
    output = [f"**Pesquisa profunda: {query}**\n"]
    for r in resultados_exa[:num_resultados]:
        url = r.get("url", "")
        titulo = r.get("title", url)
        if not url:
            continue
        output.append(f"\n## {titulo}\nURL: {url}")
        conteudo = scrape_url(url)
        output.append(conteudo[:1500])
    return "\n".join(output)


def pesquisar_mercado(query: str) -> str:
    """Scout — análise de oportunidades de mercado via Perplexity sonar-pro.
    Melhor cobertura e síntese que sonar base. Fallback para pesquisar_web.
    """
    resposta = _perplexity(
        f"{query}\n\nResponde com dados concretos, números reais e fontes. Mínimo 3 fontes citadas.",
        modelo="sonar-pro",
        max_tokens=2000,
    )
    return resposta if resposta else pesquisar(query, agente="scout")


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
    return resposta if resposta else pesquisar(query, agente="creator")


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


def get_stats_jogador(nome_jogador: str, equipa: str = "", temporada: int = 2026) -> str:
    """Stats individuais de um jogador na Primeira Liga via API Football."""
    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        # Encontrar jogador
        params: dict = {"search": nome_jogador, "league": PRIMEIRA_LIGA_ID, "season": temporada}
        r = requests.get("https://v3.football.api-sports.io/players", headers=headers, params=params, timeout=10)
        data = r.json()
        if not data.get("response"):
            return f"Jogador '{nome_jogador}' não encontrado na Primeira Liga {temporada}."
        p = data["response"][0]
        info = p["player"]
        stats = p["statistics"][0] if p.get("statistics") else {}
        nome = info.get("name", nome_jogador)
        clube = stats.get("team", {}).get("name", "?")
        pos = stats.get("games", {}).get("position", "?")
        jogos = stats.get("games", {}).get("appearences", 0)
        golos = stats.get("goals", {}).get("total", 0)
        assistencias = stats.get("goals", {}).get("assists", 0)
        rating = stats.get("games", {}).get("rating", "?")
        duelos_ganhos = stats.get("duels", {}).get("won", 0)
        passes = stats.get("passes", {}).get("total", 0)
        precisao_passe = stats.get("passes", {}).get("accuracy", "?")
        return (
            f"{nome} ({clube} | {pos})\n"
            f"Jogos: {jogos} | Golos: {golos} | Assistências: {assistencias} | Rating: {rating}\n"
            f"Passes: {passes} (precisão {precisao_passe}%) | Duelos ganhos: {duelos_ganhos}"
        )
    except Exception as e:
        return f"Erro ao obter stats de {nome_jogador}: {e}"


def analise_adversario_tatico(adversario: str, temporada: int = 2026) -> str:
    """Análise tática de um adversário: últimos resultados, golos, tendências."""
    try:
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        # Encontrar equipa
        r = requests.get("https://v3.football.api-sports.io/teams", headers=headers,
                         params={"name": adversario, "league": PRIMEIRA_LIGA_ID, "season": temporada}, timeout=10)
        data = r.json()
        if not data.get("response"):
            return f"Equipa '{adversario}' não encontrada."
        team_id = data["response"][0]["team"]["id"]
        team_name = data["response"][0]["team"]["name"]

        # Últimos 5 jogos
        r2 = requests.get("https://v3.football.api-sports.io/fixtures", headers=headers,
                          params={"team": team_id, "league": PRIMEIRA_LIGA_ID, "season": temporada, "last": 5}, timeout=10)
        fixtures = r2.json().get("response", [])

        # Estatísticas da equipa
        r3 = requests.get("https://v3.football.api-sports.io/teams/statistics", headers=headers,
                          params={"team": team_id, "league": PRIMEIRA_LIGA_ID, "season": temporada}, timeout=10)
        stats = r3.json().get("response", {})

        linhas = [f"Análise tática — {team_name}\n"]

        if fixtures:
            linhas.append("Últimos 5 jogos:")
            for f in fixtures:
                data_j = f["fixture"]["date"][:10]
                casa = f["teams"]["home"]["name"]
                fora = f["teams"]["away"]["name"]
                g_casa = f["goals"]["home"]
                g_fora = f["goals"]["away"]
                linhas.append(f"  {data_j}: {casa} {g_casa}-{g_fora} {fora}")

        if stats:
            gm = stats.get("goals", {}).get("for", {}).get("total", {}).get("total", "?")
            gs = stats.get("goals", {}).get("against", {}).get("total", {}).get("total", "?")
            f_form = stats.get("form", "")
            linhas.append(f"\nGolos marcados: {gm} | Golos sofridos: {gs}")
            linhas.append(f"Forma recente: {f_form}")

        return "\n".join(linhas)
    except Exception as e:
        return f"Erro análise tática {adversario}: {e}"


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
        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return "Tavily indisponível."
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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
        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return "Tavily indisponível."
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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
        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return "Tavily indisponível."
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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
        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return "Tavily indisponível."
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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
        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return "Tavily indisponível."
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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

        if not _TAVILY_AVAILABLE or not _TavilyClient:
            return "Tavily indisponível."
        client = _TavilyClient(api_key=TAVILY_API_KEY)
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


def _ver_historico_scout_safe() -> str:
    """Ver histórico do Scout com fallback robusto se scout_memory não existe/falha."""
    try:
        import scout_memory
        return scout_memory.get_resumo_para_vasco()
    except Exception:
        pass
    # Fallback: ler scout_state.json directamente
    try:
        from pathlib import Path
        import json
        state_file = Path(__file__).parent / "memory" / "scout_state.json"
        if state_file.exists():
            s = json.loads(state_file.read_text())
            propostas = s.get("oportunidades_propostas", [])
            aprovadas = s.get("oportunidades_aprovadas", [])
            ultima_a = s.get("ultima_missao_a", "nunca")
            return (
                f"Histórico Scout (fallback directo):\n"
                f"- Última Missão A: {ultima_a}\n"
                f"- Oportunidades propostas: {', '.join(propostas) if propostas else 'nenhuma'}\n"
                f"- Aprovadas: {', '.join([a if isinstance(a, str) else a.get('nome','?') for a in aprovadas]) if aprovadas else 'nenhuma'}"
            )
    except Exception as e:
        return f"Histórico Scout indisponível: {e}"
    return "Histórico Scout: sem dados ainda."


# ── Scout: ferramentas multilíngue e geográficas ─────────────────────────────

_GEO_MODES = {
    "iberico_latam": {
        "lang_label": "PT/ES",
        "query_sets": [
            # Português (BR/PT)
            ("{kw} negócio rendimento passivo Brasil 2026", "Brasil"),
            ("{kw} renda passiva fundador solo receita 2025 2026 site:indiehackers.com OR site:reddit.com", "Brasil"),
            ("{kw} oportunidade negócio mercado Brasil Portugal 2026 receita", "Brasil/PT"),
            ("{kw} SaaS nicho mercado português brasileiro concorrência 2026", "PT/BR"),
            # Espanhol (MX/ES/AR)
            ("{kw} negocio ingresos pasivos México España 2026", "México/España"),
            ("{kw} fundador solo ingresos MRR 2025 2026 Latinoamérica", "LATAM"),
            ("{kw} oportunidad mercado hispanohablante competencia baja 2026", "LATAM"),
            # Inglês mas com foco Ibérico/LATAM
            ("{kw} business Portuguese Spanish market opportunity low competition 2026", "Ibérico/LATAM"),
            ("{kw} solo founder revenue Brazil Mexico passive income case study 2025", "BR/MX"),
        ],
    },
    "anglofonico": {
        "lang_label": "EN",
        "query_sets": [
            ("{kw} business opportunity passive income United States 2026", "US"),
            ("{kw} solo founder revenue MRR case study US UK 2025 2026", "US/UK"),
            ("{kw} SaaS niche market United States competition analysis 2026", "US"),
            ("{kw} passive income business Australia Canada 2026 founder", "AU/CA"),
            ("{kw} indie hacker $10k MRR United States 2025 2026", "US"),
            ("{kw} business opportunity UK market underserved 2026", "UK"),
        ],
    },
    "dach": {
        "lang_label": "DE",
        "query_sets": [
            # Alemão real
            ("{kw} passives Einkommen Geschäft Deutschland 2026", "Deutschland"),
            ("{kw} Gründer Solo-Unternehmer Einnahmen Fallstudie 2025 2026 Deutschland Österreich", "DACH"),
            ("{kw} SaaS Nische Markt Deutschland Wettbewerb 2026", "Deutschland"),
            ("{kw} Online-Geschäft passives Einkommen Schweiz Österreich 2026", "CH/AT"),
            # Inglês mas foco DACH
            ("{kw} business opportunity Germany Austria Switzerland underserved market 2026", "DACH"),
            ("{kw} solo founder Germany revenue passive income 2025 2026 case study", "DACH"),
        ],
    },
}


def scout_pesquisa_multilang(geo_mode: str, keywords: list) -> str:
    """
    Pesquisa oportunidades de negócio com queries nativas (PT/ES/DE) para o modo geográfico.
    geo_mode: 'iberico_latam' | 'anglofonico' | 'dach'
    keywords: lista de termos a pesquisar (max 5)
    """
    config = _GEO_MODES.get(geo_mode)
    if not config:
        return f"Modo geográfico inválido. Escolhe: {list(_GEO_MODES.keys())}"

    results_all = []
    keywords = keywords[:5]
    seen_urls: set = set()

    for kw in keywords:
        for template, market_label in config["query_sets"]:
            q = template.format(kw=kw)
            # Perplexity sonar-pro primeiro — melhor cobertura multilíngue PT/ES/DE
            perp = _perplexity(q, modelo="sonar-pro", max_tokens=400) if PERPLEXITY_API_KEY else ""
            r: list[dict] = []
            if perp:
                r = [{"title": f"Perplexity: {market_label}", "content": perp, "url": ""}]
            else:
                r = _pesquisar_tavily(q, num_results=3) or _pesquisar_exa(q, num_results=3) or _pesquisar_duckduckgo(q, num_results=3)
            for item in r:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                if item.get("title") or item.get("content"):
                    results_all.append(
                        f"[{market_label}] **{item['title']}**\n{item['content'][:300]}\n{url}"
                    )
        # sem break por keyword — percorre todos os query_sets para cobertura completa

    if not results_all:
        return f"Sem resultados para modo {geo_mode}."

    label = config["lang_label"]
    # sem limite artificial — devolve todos os resultados únicos recolhidos
    return f"**Pesquisa multilíngue ({label}) — {geo_mode} ({len(results_all)} resultados):**\n\n" + "\n\n---\n\n".join(results_all)


def scout_g2_capterra(nicho: str) -> str:
    """
    Pesquisa competidores, reviews e gaps de mercado no G2 e Capterra para um nicho.
    nicho: ex. 'directory software', 'scheduling tool', 'AI writing assistant'
    """
    queries = [
        f"site:g2.com {nicho} reviews alternatives competitors",
        f"site:capterra.com {nicho} pricing reviews 2025 2026",
        f"{nicho} G2 OR Capterra market leader gap underserved 2026",
        f"{nicho} users complain missing feature reddit 2025 2026",
    ]
    resultados = []
    for q in queries:
        r = _pesquisar_exa(q, num_results=4) or _pesquisar_tavily(q, num_results=4) or _pesquisar_duckduckgo(q, num_results=4)
        for item in r:
            if item.get("title") or item.get("content"):
                resultados.append(f"**{item['title']}**\n{item['content'][:300]}\nFonte: {item['url']}")

    if not resultados:
        return f"Sem dados G2/Capterra para '{nicho}'."

    return f"**G2/Capterra — análise de competidores: {nicho}**\n\n" + "\n\n---\n\n".join(resultados[:10])


def scout_job_boards(nicho: str) -> str:
    """
    Pesquisa job boards (LinkedIn, Indeed, Remote.co) para medir procura de skills no nicho.
    Um nicho com muitas vagas = mercado com dinheiro a circular = oportunidade.
    nicho: ex. 'AI prompt engineer', 'no-code automation', 'SEO specialist'
    """
    queries = [
        f"site:linkedin.com/jobs {nicho} 2026 hiring demand",
        f"site:indeed.com {nicho} jobs growing 2026",
        f"{nicho} remote jobs growing demand 2025 2026 salary range",
        f"{nicho} freelance market size clients budget 2026",
    ]
    resultados = []
    for q in queries:
        r = _pesquisar_exa(q, num_results=3) or _pesquisar_tavily(q, num_results=3) or _pesquisar_duckduckgo(q, num_results=3)
        for item in r:
            if item.get("title") or item.get("content"):
                resultados.append(f"**{item['title']}**\n{item['content'][:250]}\n{item['url']}")

    if not resultados:
        return f"Sem dados de job boards para '{nicho}'."

    return f"**Job Boards — sinal de mercado: {nicho}**\n\n" + "\n\n---\n\n".join(resultados[:8])


# ── Ferramentas do Solver ────────────────────────────────────────────────────

import subprocess
from pathlib import Path

MORGAN_DIR = Path(__file__).parent
ALLOWED_DIRS = [MORGAN_DIR, MORGAN_DIR / "memory", MORGAN_DIR / "desktop"]

# Comandos de diagnóstico permitidos (read-only, seguros)
_CMD_WHITELIST = ["ps", "grep", "tail", "head", "cat", "ls", "wc", "df", "free",
                  "git log", "git status", "git diff", "git tag", "systemctl status",
                  "pgrep", "lsof", "netstat", "curl -s", "ping -c"]


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
        if len(content) > 8000:
            return f"[Truncado — primeiras 8000 chars de {len(content)}]\n{content[:8000]}"
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
                     "BINANCE_API_KEY", "TAVILY_API_KEY", "QDRANT_URL", "MEM0_API_KEY"]
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
    """Faz git add (só .py e .json, nunca .env), commit e push via SSH. REQUER confirmação prévia do Vasco."""
    try:
        cmds = [
            "git config user.email 'solver@morgan.ai'",
            "git config user.name 'Morgan Solver'",
            # Nunca adicionar .env ou credenciais — só código e configs
            "git add -- '*.py' '*.json' '*.md' '*.yml' '*.yaml'",
            f"git commit -m '{mensagem}'",
            "git push origin main",
        ]
        for cmd in cmds:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               cwd=str(MORGAN_DIR), timeout=60)
            if r.returncode != 0:
                # "nothing to commit" não é erro
                combined = (r.stdout + r.stderr).lower()
                if "nothing to commit" in combined or "nothing added to commit" in combined:
                    continue
                return f"Erro em '{cmd}':\n{(r.stderr or r.stdout)[:400]}"
        return "Commit e push concluídos. GitHub Actions faz deploy automático no Mac Mini."
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
        "description": "Pesquisa na web via Exa → Tavily → DuckDuckGo. Para informação geral, artigos, páginas. NÃO usa Perplexity. Para análise de mercado usa pesquisar_mercado. Para notícias recentes de futebol usa pesquisar_noticias.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "O que pesquisar."},
                "modo": {"type": "string", "enum": ["auto", "semantico", "noticias"], "description": "auto (padrão), semantico (Exa primeiro), noticias (DDG/Tavily)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "pesquisar_noticias",
        "description": "Pesquisa notícias recentes via DuckDuckGo → Tavily. Ideal para futebol, transferências, resultados, actualidades. Gratuito, sem Perplexity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "O que pesquisar. Ex: 'Moreirense transferências Julho 2026'"}
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
        "name": "get_stats_jogador",
        "description": "Stats individuais de um jogador na Primeira Liga (golos, assistências, passes, rating, duelos).",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_jogador": {"type": "string", "description": "Nome do jogador"},
                "equipa": {"type": "string", "description": "Equipa (opcional, para desambiguar)"},
                "temporada": {"type": "integer", "description": "Época, ex: 2026"}
            },
            "required": ["nome_jogador"]
        }
    },
    {
        "name": "analise_adversario_tatico",
        "description": "Análise tática de um adversário: últimos 5 resultados, golos marcados/sofridos, forma recente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "adversario": {"type": "string", "description": "Nome da equipa adversária"},
                "temporada": {"type": "integer", "description": "Época, ex: 2026"}
            },
            "required": ["adversario"]
        }
    },
    {
        "name": "etsy_pausar_listing",
        "description": "Pausa um listing Etsy (torna-o inactivo). Usar quando CTR baixo ou stock esgotado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "integer", "description": "ID do listing Etsy"}
            },
            "required": ["listing_id"]
        }
    },
    {
        "name": "etsy_activar_listing",
        "description": "Reactiva um listing Etsy pausado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "integer", "description": "ID do listing Etsy"}
            },
            "required": ["listing_id"]
        }
    },
    {
        "name": "etsy_actualizar_preco",
        "description": "Actualiza o preço de um listing Etsy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "integer", "description": "ID do listing Etsy"},
                "preco": {"type": "number", "description": "Novo preço em EUR, ex: 4.99"}
            },
            "required": ["listing_id", "preco"]
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
        "description": "Analisa tendências de interesse para termos de negócio via pesquisa web (Tavily/DDG). ATENÇÃO: não usa a API do Google Trends — retorna artigos e discussões web sobre tendências do termo, não dados de volume de pesquisa reais. Útil para contexto qualitativo de crescimento/declínio. Para dados quantitativos de volume, usa pesquisar_mercado. Máximo 5 termos por chamada.",
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
        "description": "[LEGADO — usar scout_pesquisa_multilang em vez desta] Pesquisa básica de oportunidades de negócio. Substituída por scout_pesquisa_multilang que suporta 3 modos geográficos e queries nativas PT/ES/DE. Mantida por compatibilidade com código mais antigo.",
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
        "name": "consultar_base_conhecimento",
        "description": "Consulta a base de conhecimento central do Morgan em linguagem natural. Acede ao historial de TODOS os agentes — o que o Scout detectou, o que o Solver corrigiu, o que o Creator construiu, decisões do CFO, briefings do Coach. Usa sempre que precisas de contexto histórico ou queres saber o que aconteceu no sistema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Pergunta em linguagem natural. Ex: 'o que o creator construiu esta semana', 'problemas corrigidos pelo solver', 'oportunidades detectadas pelo scout'"},
                "agente": {"type": "string", "description": "Filtrar por agente específico: ceo, scout, cfo, coach, solver, creator (opcional)"},
                "limite": {"type": "integer", "description": "Número máximo de resultados. Default: 15"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "consultar_historico_imperio",
        "description": "Consulta o histórico de ações passadas do império BCVertex. Usa quando precisas de contexto histórico — decisões antigas, semanas anteriores do Scout, arquitectura explicada. Não carregado por defeito — só consulta quando relevante.",
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
        "name": "scrape_url",
        "description": "Extrai conteúdo completo de uma URL e devolve markdown limpo. Usa para: analisar listings Etsy da concorrência, ler páginas de diretórios, extrair conteúdo de sites sem API. Mais completo que pesquisar_web.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL completa a fazer scrape"},
                "formato": {"type": "string", "description": "Formato de saída: 'markdown' (padrão) ou 'html'", "default": "markdown"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "pesquisar_e_scrape",
        "description": "Pesquisa na web E extrai conteúdo completo dos resultados (não apenas snippets). Para análise profunda de concorrentes, extracção de leads, research detalhado. Mais lento mas muito mais completo que pesquisar_web.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query de pesquisa"},
                "num_resultados": {"type": "integer", "description": "Número de URLs a analisar (1-5, padrão 3)", "default": 3}
            },
            "required": ["query"]
        }
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
        "name": "criar_email_bcvertex",
        "description": "Cria um novo endereço de email no domínio bcvertex.com via PurelyMail. Totalmente autónomo — sem interacção humana. Usa para criar emails de novos negócios (ex: planneratlas@bcvertex.com).",
        "input_schema": {
            "type": "object",
            "properties": {
                "utilizador": {"type": "string", "description": "Nome do utilizador sem domínio (ex: 'planneratlas', 'suporte', 'info')"},
                "dominio": {"type": "string", "description": "Domínio (padrão: bcvertex.com)", "default": "bcvertex.com"}
            },
            "required": ["utilizador"]
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
    },
    {
        "name": "scout_pesquisa_multilang",
        "description": "Pesquisa oportunidades de negócio em múltiplas línguas e mercados. Usa um dos 3 modos geográficos: 'iberico_latam' (PT/ES/BR/MX), 'anglofonico' (US/UK/AU/CA), 'dach' (DE/AT/CH). Ideal para validar se uma oportunidade funciona fora do mercado PT.",
        "input_schema": {
            "type": "object",
            "properties": {
                "geo_mode": {"type": "string", "description": "Modo geográfico: 'iberico_latam' | 'anglofonico' | 'dach'"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Lista de keywords a pesquisar (max 5)"}
            },
            "required": ["geo_mode", "keywords"]
        }
    },
    {
        "name": "scout_g2_capterra",
        "description": "Pesquisa no G2 e Capterra para encontrar competidores, preços, reviews e gaps de mercado num nicho específico. Usa para validar o critério de competidores do Quality Gate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nicho": {"type": "string", "description": "Nicho de mercado a analisar (ex: 'directory software', 'AI scheduling tool')"}
            },
            "required": ["nicho"]
        }
    },
    {
        "name": "scout_job_boards",
        "description": "Pesquisa job boards (LinkedIn, Indeed) para medir a procura real num nicho. Muitas vagas = mercado com dinheiro a circular. Útil para medir monetization_intent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nicho": {"type": "string", "description": "Skill ou nicho a analisar (ex: 'no-code automation', 'AI prompt engineer')"}
            },
            "required": ["nicho"]
        }
    }
]

# Mapa de nome para função
TOOL_FUNCTIONS = {
    "pesquisar": pesquisar,
    "pesquisar_web": pesquisar_web,
    "pesquisar_noticias": pesquisar_noticias,
    "classificacao_primeira_liga": classificacao_primeira_liga,
    "proximos_jogos": proximos_jogos,
    "resultados_recentes": resultados_recentes,
    "get_stats_jogador": get_stats_jogador,
    "analise_adversario_tatico": analise_adversario_tatico,
    "etsy_pausar_listing": lambda listing_id: "OK" if __import__("etsy_service").pausar_listing(int(listing_id)) else "Erro",
    "etsy_activar_listing": lambda listing_id: "OK" if __import__("etsy_service").activar_listing(int(listing_id)) else "Erro",
    "etsy_actualizar_preco": lambda listing_id, preco: "OK" if __import__("etsy_service").actualizar_preco(int(listing_id), float(preco)) else "Erro",
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
    "ver_historico_scout": lambda: _ver_historico_scout_safe(),
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
    "consultar_base_conhecimento": lambda query, agente=None, limite=15: consultar_base(query, agente=agente, limite=limite),
    "consultar_historico_imperio": consultar_historico_imperio,
    "atualizar_estado_imperio": atualizar_estado_imperio,
    "listar_google_drive": listar_google_drive,
    "organizar_google_drive_sugestoes": organizar_google_drive_sugestoes,
    "scrape_url": scrape_url,
    "pesquisar_e_scrape": pesquisar_e_scrape,
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
    "criar_email_bcvertex": lambda utilizador, dominio="bcvertex.com": (
        __import__("creator_agent").criar_email_purelymail(utilizador, dominio)
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
    "scout_pesquisa_multilang": scout_pesquisa_multilang,
    "scout_g2_capterra": scout_g2_capterra,
    "scout_job_boards": scout_job_boards,
}
