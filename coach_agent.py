"""
Morgan Coach — Agente especializado em análise tática e apoio à profissão do Vasco.
Especialidades: análise de adversários, briefings pré-jogo, relatórios pós-jogo,
planeamento de treinos, monitorização de jogadores e mercado.
"""
import os
import json
from pathlib import Path
from datetime import datetime
import anthropic
from dotenv import load_dotenv
load_dotenv()

MEMORY_DIR = Path(__file__).parent / "memory"
COACH_LOG_FILE = MEMORY_DIR / "coach_log.json"


# ── Memória do Coach ─────────────────────────────────────────────────────────

def _load_coach_log() -> dict:
    try:
        return json.loads(COACH_LOG_FILE.read_text())
    except Exception:
        return {"analises": [], "briefings": [], "relatorios": []}

def _save_coach_log(log: dict):
    COACH_LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))




# ── System Prompt ─────────────────────────────────────────────────────────────

def _fetch_moreirense_fixtures() -> str:
    """Busca próximos jogos do Moreirense via Tavily (API Football free plan não suporta época atual)."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        r = client.search(
            "Moreirense FC próximos jogos calendário 2025 2026 Liga Portugal",
            max_results=3,
            search_depth="basic"
        )
        snippets = []
        for res in (r.get("results") or [])[:3]:
            c = res.get("content", "")
            if c:
                snippets.append(c[:300])
        if snippets:
            return "Calendário Moreirense (fonte web):\n" + "\n---\n".join(snippets)
        return ""
    except Exception:
        return ""


def build_coach_system(contexto: str = "") -> str:
    from datetime import datetime
    hoje = datetime.now().strftime("%d de %B de %Y")
    fixtures_str = _fetch_moreirense_fixtures()
    moreirense_info = f"""Moreirense FC — Liga Portugal Betclic (Primeira Liga)
Vasco Botelho da Costa é o treinador principal.
Contrato até final da época 2026/27. Cláusula de rescisão: 1,5M€.
Moreira de Cónegos, Guimarães, Portugal.

{fixtures_str}"""
    memoria = ""
    try:
        from episodic_memory import get_contexto_agente
        mem_sistema = get_contexto_agente("coach", contexto or "futebol Moreirense Vasco")
    except Exception:
        mem_sistema = ""
    mem_bloco = ""
    if memoria or mem_sistema:
        partes = []
        if memoria: partes.append(memoria)
        if mem_sistema: partes.append(mem_sistema)
        mem_bloco = f"\n## Memória relevante:\n" + "\n\n".join(partes)

    return f"""És o Morgan Coach — assistente especializado em análise táctica e apoio ao Vasco Botelho da Costa como treinador profissional.

Data: {hoje}
Língua: sempre PT-PT. Terminologia táctica precisa. Sem emojis.
Reportas ao Morgan CEO. O Vasco pode falar directamente contigo.
Para voltar ao CEO, o Vasco diz "volta ao Morgan".

## CONTEXTO DO MOREIRENSE
{moreirense_info}
{mem_bloco}

## PERFIL DE TRABALHO DO VASCO
- Tempo disponível: muito limitado — assume sempre que tem menos de 5 minutos
- Quer respostas directas, não introduções
- Prefere 5 bullets accionáveis a 5 parágrafos explicativos
- Análise profunda só quando pedida explicitamente

## MODO DE RESPOSTA
- **Briefing/urgente**: máximo 5 bullets, sem introdução, acção concreta no fim
- **Análise pedida**: estrutura PADRÃO IDENTIFICADO → IMPLICAÇÃO TÁCTICA → ACÇÃO RECOMENDADA
- **Default**: modo briefing — brevidade é respeito pelo tempo do treinador
- Primeira linha é sempre conteúdo, nunca introdução ("Claro!", "Vou analisar...", etc.)
- Números sempre contextualizados: "acima da média da Liga Portugal" em vez de "0.34 xG"
- Distinguir claramente: dados reais / análise inferida / opinião táctica

## ESPECIALIDADES
1. **Análise de adversários** — padrões táticos, fraquezas exploráveis, jogadores-chave, set-pieces
2. **Briefing pré-jogo** — resumo executivo em bullets, alertas táticos, proposta de abordagem
3. **Relatório pós-jogo** — desempenho vs. plano, o que correu bem/mal, ajustes para o próximo
4. **Planeamento de treinos** — sessões baseadas no adversário seguinte e estado físico da equipa
5. **Mercado de jogadores** — perfis táticos em ligas PT/ES/BR/FR compatíveis com o sistema do Vasco
6. **Tendências táticas globais** — o que as melhores equipas fazem e como aplicar ao Moreirense
7. **Dados StatsBomb** — eventos reais (remates, passes, pressões) convertidos em linguagem táctica accionável
8. **Set-pieces** — análise de cantos, livres e bolas paradas do adversário e do Moreirense

## HIERARQUIA DE DADOS
Quando precisas de informação sobre um jogo ou equipa, usa nesta ordem:
1. API Football — resultados, classificações, dados ao vivo
2. StatsBomb Open Data — análise táctica histórica
3. Pesquisa web (Transfermarkt, WhoScored, FBref, Sofascore via Tavily)
4. Se os dados forem insuficientes: diz explicitamente o que falta e sugere fonte alternativa

## REGRAS
- Pesquisa em inglês primeiro (fontes globais têm muito mais dados), responde sempre em PT-PT
- Vai além dos dados básicos — procura padrões, fraquezas exploráveis, contexto
- Acção concreta sempre no fim de cada análise
- Quando identificares algo relevante pro-activamente (ex: adversário em má forma, jogador suspenso), alerta sem esperar que o Vasco pergunte
- EXCLUSIVO futebol — nunca misturar com trading, negócios ou outras áreas
"""


# ── Ferramentas disponíveis ───────────────────────────────────────────────────

_API_CACHE: dict = {}

def _api_football_cached(endpoint: str, params: dict, ttl: int = 14400) -> dict:
    """Cache de 4h para chamadas à API Football — poupa quota."""
    import time, requests
    key = f"{endpoint}:{sorted(params.items())}"
    if key in _API_CACHE:
        age = time.time() - _API_CACHE[key]["ts"]
        if age < ttl:
            return _API_CACHE[key]["data"]
    headers = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")}
    try:
        r = requests.get(
            f"https://v3.football.api-sports.io/{endpoint}",
            headers=headers, params=params, timeout=8
        )
        data = r.json()
        _API_CACHE[key] = {"data": data, "ts": time.time()}
        return data
    except Exception:
        return {}


def _sofascore_jogo(home: str, away: str) -> str:
    """Stats de jogo via Tavily (proxy Sofascore sem API key)."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        r = client.search(
            f"site:sofascore.com {home} {away} statistics ratings",
            search_depth="basic", max_results=3
        )
        snippets = [item.get("content", "")[:300] for item in r.get("results", [])[:3] if item.get("content")]
        return "Sofascore stats:\n" + "\n---\n".join(snippets) if snippets else ""
    except Exception:
        return ""


def statsbomb_dados_abertos(adversario: str = "", competicao: str = "") -> str:
    """
    Dados táticos StatsBomb open data (gratuito).
    Analisa eventos de jogos disponíveis para extrair padrões táticos.
    """
    try:
        from statsbombpy import sb
        comps = sb.competitions()
        if comps is None or comps.empty:
            return "StatsBomb: sem competições disponíveis."

        # Filtrar por competição pedida ou usar La Liga (rica em dados táticos)
        filtro = competicao.lower() if competicao else "la liga"
        comp_filtrado = comps[comps["competition_name"].str.lower().str.contains(filtro, na=False)]
        if comp_filtrado.empty:
            comp_filtrado = comps[comps["competition_name"].str.lower().str.contains("la liga", na=False)]
        if comp_filtrado.empty:
            comp_filtrado = comps.head(1)

        row = comp_filtrado.iloc[0]
        cid, sid = int(row["competition_id"]), int(row["season_id"])
        cname = row["competition_name"]

        matches = sb.matches(competition_id=cid, season_id=sid)
        if matches is None or matches.empty:
            return f"StatsBomb ({cname}): sem jogos disponíveis."

        # Se adversário especificado, filtrar jogos desse adversário
        if adversario:
            adv_lower = adversario.lower()
            mask = (
                matches["home_team"].str.lower().str.contains(adv_lower, na=False) |
                matches["away_team"].str.lower().str.contains(adv_lower, na=False)
            )
            jogos_adv = matches[mask].head(3)
        else:
            jogos_adv = matches.head(3)

        if jogos_adv.empty:
            return f"StatsBomb ({cname}): sem jogos encontrados para '{adversario}'."

        linhas = [f"**StatsBomb — {cname}**"]
        for _, jogo in jogos_adv.iterrows():
            mid = int(jogo["match_id"])
            home = jogo.get("home_team", "")
            away = jogo.get("away_team", "")
            score_h = jogo.get("home_score", "?")
            score_a = jogo.get("away_score", "?")
            linhas.append(f"\n{home} {score_h}–{score_a} {away} (match_id={mid})")
            try:
                events = sb.events(match_id=mid)
                if events is not None and not events.empty:
                    shots = len(events[events["type"] == "Shot"])
                    passes = len(events[events["type"] == "Pass"])
                    pressures = len(events[events["type"] == "Pressure"])
                    linhas.append(f"  Remates: {shots} | Passes: {passes} | Pressões: {pressures}")
            except Exception:
                linhas.append("  (eventos não disponíveis)")

        return "\n".join(linhas)

    except ImportError:
        return "statsbombpy não instalado. Corre: pip install statsbombpy"
    except Exception as e:
        return f"StatsBomb erro: {e}"


def _get_coach_tools():
    from tools import TOOLS
    nomes_permitidos = ["pesquisar_web", "proximos_jogos",
                        "resultados_recentes", "classificacao_primeira_liga"]
    return [t for t in TOOLS if t["name"] in nomes_permitidos]

def _run_tool(name: str, inp: dict) -> str:
    from tools import TOOL_FUNCTIONS
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Ferramenta {name} não encontrada."
    try:
        return func(**inp) if inp else func()
    except Exception as e:
        return f"Erro: {e}"


# ── Chamada ao Claude ─────────────────────────────────────────────────────────

def _chamar_claude_coach(system: str, messages: list) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    tools = _get_coach_tools()
    kwargs = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 3000,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    msgs = list(messages)
    while True:
        response = client.messages.create(**{**kwargs, "messages": msgs})
        if response.stop_reason == "tool_use" and tools:
            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            msgs.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""


# ── Histórico de conversa do Coach ───────────────────────────────────────────

_coach_history: list = []

def get_coach_reply(user_message: str) -> str:
    """Ponto de entrada principal para conversa com o Coach."""
    global _coach_history

    system = build_coach_system(user_message)
    _coach_history.append({"role": "user", "content": user_message})

    # Limitar histórico a 20 mensagens
    if len(_coach_history) > 20:
        _coach_history = _coach_history[-20:]

    reply = _chamar_claude_coach(system, _coach_history)
    _coach_history.append({"role": "assistant", "content": reply})


    # Camada episódica — registar evento
    try:
        from episodic_memory import registar_evento
        registar_evento("coach", "conversa", f"Q: {user_message[:100]} | R: {reply[:200]}")
    except Exception:
        pass

    return reply


# ── Funções de análise estruturada ───────────────────────────────────────────

def analisar_adversario(clube: str, competicao: str = "") -> str:
    """Análise completa de um adversário com dados Sofascore + API Football (cached)."""
    # Dados extra: últimos jogos do adversário via API Football (cached 4h)
    dados_api = ""
    try:
        data = _api_football_cached("teams", {"name": clube, "league": 94, "season": 2026})
        if data.get("response"):
            team_id = data["response"][0]["team"]["id"]
            fixtures = _api_football_cached("fixtures", {"team": team_id, "last": 5, "season": 2026})
            if fixtures.get("response"):
                linhas = []
                for f in fixtures["response"]:
                    h = f["teams"]["home"]["name"]
                    a = f["teams"]["away"]["name"]
                    gh = f["goals"]["home"]
                    ga = f["goals"]["away"]
                    linhas.append(f"{h} {gh}-{ga} {a}")
                dados_api = "Últimos 5 jogos (API Football):\n" + "\n".join(linhas)
    except Exception:
        pass

    sofascore = _sofascore_jogo(clube, "Moreirense") or ""
    dados_extra = "\n\n".join(filter(None, [dados_api, sofascore]))

    dados_bloco = ("DADOS RECOLHIDOS:\n" + dados_extra) if dados_extra else ""
    competicao_label = competicao if competicao else "Liga Portugal Betclic"
    prompt = f"""Faz uma análise tática completa do {clube} para me preparar para o próximo jogo.
{dados_bloco}

Pesquisa em inglês em fontes como WhoScored, FBref, Transfermarkt, Soccerway, ESPN FC.
Inclui:
1. Formação habitual e variações
2. Jogadores-chave e as suas características
3. Padrões ofensivos e pontos fortes
4. Vulnerabilidades defensivas exploráveis
5. Resultados recentes (últimos 5 jogos) e tendência de forma
6. Como o Moreirense deve abordar este jogo — proposta tática concreta

Competição: {competicao_label}
Termina com: ALERTA PRINCIPAL: [o aspeto mais importante a considerar]"""

    reply = get_coach_reply(prompt)
    log = _load_coach_log()
    log["analises"].append({
        "clube": clube,
        "data": datetime.now().isoformat(),
        "resumo": reply[:300],
    })
    _save_coach_log(log)
    return reply


def briefing_pre_jogo(adversario: str, data_jogo: str = "") -> str:
    """Briefing executivo pré-jogo — versão curta para o dia do jogo."""
    prompt = f"""Cria um briefing pré-jogo para o jogo de hoje/amanhã contra o {adversario}.
{f'Data: {data_jogo}' if data_jogo else ''}

Formato:
- ADVERSÁRIO: [nome + formação]
- ATENÇÃO: [máximo 3 alertas táticos críticos, 1 linha cada]
- EXPLORAR: [máximo 2 vulnerabilidades concretas]
- ABORDAGEM: [1 parágrafo com proposta tática clara]

Breve, direto, acionável. Máximo 200 palavras."""

    return get_coach_reply(prompt)


def relatorio_pos_jogo(adversario: str, resultado: str, notas: str = "") -> str:
    """Análise pós-jogo."""
    prompt = f"""Analisa o jogo que acabou de acontecer.

Adversário: {adversario}
Resultado: {resultado}
Notas do Vasco: {notas if notas else 'Sem notas adicionais.'}

Inclui:
1. O que correu bem taticamente
2. O que falhou e porquê
3. Pontos a trabalhar nos próximos treinos
4. Impacto na classificação e próximo adversário

Conclusão com 1 ação prioritária para a próxima semana."""

    reply = get_coach_reply(prompt)
    log = _load_coach_log()
    log["relatorios"].append({
        "adversario": adversario,
        "resultado": resultado,
        "data": datetime.now().isoformat(),
        "resumo": reply[:300],
    })
    _save_coach_log(log)
    return reply


def pesquisar_jogador(perfil: str, ligas: str = "PT/ES/BR/FR") -> str:
    """Pesquisa de jogadores por perfil tático."""
    prompt = f"""Pesquisa jogadores com este perfil para o Moreirense FC.

Perfil: {perfil}
Ligas a considerar: {ligas}

Pesquisa em inglês no Transfermarkt, FBref, Soccerway.
Para cada jogador encontrado:
- Nome, idade, clube atual, valor de mercado estimado
- Por que encaixa no perfil pedido
- Possibilidade realista de contratação para um clube como o Moreirense

Máximo 5 jogadores, ordenados por fit tático."""

    return get_coach_reply(prompt)


def report_semanal_coach() -> str:
    """Relatório semanal do Coach para o CEO."""
    log = _load_coach_log()
    analises = log.get("analises", [])
    relatorios = log.get("relatorios", [])

    n_analises = len([a for a in analises if a.get("data", "")[:10] >= (datetime.now().isoformat()[:10][:7])])
    n_relatorios = len([r for r in relatorios if r.get("data", "")[:10] >= (datetime.now().isoformat()[:10][:7])])

    return f"""MORGAN COACH — Relatório Semanal
Data: {datetime.now().strftime('%d/%m/%Y')}

Atividade esta semana:
- Análises de adversários: {n_analises}
- Relatórios pós-jogo: {n_relatorios}
- Total de análises acumuladas: {len(analises)}

{'Última análise: ' + analises[-1]['clube'] if analises else 'Sem análises ainda.'}
{'Último jogo analisado: ' + relatorios[-1]['adversario'] + ' (' + relatorios[-1]['resultado'] + ')' if relatorios else 'Sem relatórios ainda.'}

Estado: Operacional"""
