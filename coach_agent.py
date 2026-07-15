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


# ── Mem0 por Coach ───────────────────────────────────────────────────────────

def _mem0_coach_get(query: str) -> str:
    try:
        from mem0 import MemoryClient
        client = MemoryClient(api_key=os.getenv("MEM0_API_KEY", ""))
        results = client.search(query, user_id="coach", limit=5)
        memorias = []
        for r in results:
            m = r.get("memory", "") if isinstance(r, dict) else r
            if m:
                memorias.append(str(m))
        return "\n".join(memorias) if memorias else ""
    except Exception:
        return ""

def _mem0_coach_add(texto: str):
    try:
        from mem0 import MemoryClient
        client = MemoryClient(api_key=os.getenv("MEM0_API_KEY", ""))
        client.add(texto, user_id="coach")
    except Exception:
        pass


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
    memoria = _mem0_coach_get(contexto) if contexto else ""
    mem_bloco = f"\n## Memória relevante:\n{memoria}" if memoria else ""

    return f"""És o Morgan Coach, o assistente especializado em análise tática e apoio à profissão do Vasco Botelho da Costa como treinador de futebol.

A data de hoje é {hoje}.
Tom: profissional, direto, focado, sem rodeios. Sempre em português europeu. Sem emojis.
Reportas ao Morgan CEO. O Vasco pode falar diretamente contigo.
Para voltar ao Morgan CEO, o Vasco diz "volta ao Morgan".

## Contexto:
{moreirense_info}
{mem_bloco}

## As tuas especialidades:
1. **Análise de adversários** — pesquisas em fontes internacionais (Transfermarkt, Soccerway, WhoScored, FBref, ESPN FC), identificação de padrões táticos, pontos fortes e fracos
2. **Briefing pré-jogo** — resumo executivo do adversário, alertas táticos, propostas de abordagem
3. **Relatório pós-jogo** — análise de desempenho, comparação com adversário, pontos a melhorar
4. **Planeamento de treinos** — sessões baseadas no adversário seguinte e no estado físico da equipa
5. **Mercado de jogadores** — monitorização de jogadores em ligas PT/ES/BR/FR por perfil tático
6. **Tendências táticas globais** — análise de tendências na Premier League, La Liga, Bundesliga aplicáveis ao Moreirense

## Regras:
- Pesquisas SEMPRE em inglês primeiro (fontes globais têm muito mais dados), traduz e adapta no final em PT-PT.
- Quando analisares adversários, vai além dos dados básicos — procura padrões, fraquezas exploráveis, jogadores-chave.
- Sugere sempre uma linha de ação concreta no final de cada análise.
- Guarda em memória o que for relevante para análises futuras.
"""


# ── Ferramentas disponíveis ───────────────────────────────────────────────────

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

    # Guardar memória se análise relevante
    _mem0_coach_add(f"Conversa sobre: {user_message[:100]} — resposta: {reply[:200]}")

    return reply


# ── Funções de análise estruturada ───────────────────────────────────────────

def analisar_adversario(clube: str, competicao: str = "") -> str:
    """Análise completa de um adversário."""
    prompt = f"""Faz uma análise tática completa do {clube} para me preparar para o próximo jogo.

Pesquisa em inglês em fontes como WhoScored, FBref, Transfermarkt, Soccerway, ESPN FC.
Inclui:
1. Formação habitual e variações
2. Jogadores-chave e as suas características
3. Padrões ofensivos e pontos fortes
4. Vulnerabilidades defensivas exploráveis
5. Resultados recentes (últimos 5 jogos) e tendência de forma
6. Como o Moreirense deve abordar este jogo — proposta tática concreta

Competição: {competicao if competicao else 'Liga Portugal Betclic'}
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
