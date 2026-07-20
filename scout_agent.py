"""
Morgan Scout — Agente de inteligência de mercado do império BCVertex.
Missão A (domingo 20h): identifica e valida oportunidades de negócio.
Missão B (quarta 20h): melhorias ao ecossistema de agentes.

QUALITY GATE OBRIGATÓRIO: nenhuma oportunidade passa ao CEO sem:
  1. TAM com número real (fonte citada)
  2. Mínimo 3 casos de sucesso públicos com receita declarada
  3. Mercado por país validado com dados (não hipóteses)
  4. Capital inicial mínimo estimado com base em ferramentas reais
  5. 3 competidores directos com preços e tráfego estimado
  6. Tempo realista até primeiro €1 (dados de fundadores reais)
  7. Confiança mínima 85% — abaixo disso descarta ou marca como "em investigação"
  8. Formato padronizado obrigatório antes de propor ao CEO
"""
import os
import json
from pathlib import Path
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv
load_dotenv()

MEMORY_DIR = Path(__file__).parent / "memory"
SCOUT_STATE_FILE = MEMORY_DIR / "scout_state.json"
SCOUT_REPORTS_DIR = MEMORY_DIR / "scout_reports"
SCOUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


# ── Quality Gate ──────────────────────────────────────────────────────────────

QUALITY_GATE_PROMPT = """És o Morgan Scout. Antes de propor qualquer oportunidade ao CEO, aplica o Quality Gate obrigatório.

QUALITY GATE — 10 critérios (todos obrigatórios):

1. TAM (Mercado Total Endereçável)
   - Obrigatório: número real com fonte citada (ex: "$4.2B em 2026, Statista")
   - Recusa se: "grande mercado", "mercado em crescimento" sem números

2. Casos de sucesso reais
   - Obrigatório: mínimo 3 fundadores reais com receita declarada e links
   - Recusa se: só "este modelo funciona" sem exemplos verificáveis

3. Mercado por país validado
   - Obrigatório: dados concretos por país (volume de pesquisa, nº empresas alvo, competidores locais)
   - Recusa se: "mercado PT/BR/ES" sem validar qual e porquê

4. Capital inicial real
   - Obrigatório: itemização detalhada (hosting €X/mês, ferramentas €X, tempo desenvolvimento X horas)
   - Recusa se: "custo baixo" ou "praticamente zero"

5. Competidores directos
   - Obrigatório: 3 competidores com preços actuais, tráfego estimado (SimilarWeb/Ahrefs), e ponto fraco explorável
   - Recusa se: "sem competição" ou lista vaga

6. Timeline realista
   - Obrigatório: dias/semanas até primeiro cliente, com base em casos reais de fundadores similares
   - Recusa se: "pode gerar rendimento rapidamente"

7. Diversidade de fontes
   - Obrigatório: pelo menos 1 fonte que documente FALHANÇO ou DIFICULDADE neste modelo de negócio
   - Recusa se: todos os dados vêm de fontes com viés de sucesso (IndieHackers, Product Hunt)
   - Exemplo aceitável: "Reddit r/entrepreneur tem 3 posts de pessoas que tentaram e abandonaram por [razão]"

8. Fit real com perfil do Vasco
   - Horas de setup estimadas (não "fácil de configurar" — número real)
   - Quantas decisões por semana requer o operador? (threshold: máximo 1h/semana após setup)
   - O Morgan consegue executar 90%+ das tarefas operacionais? Especifica quais não consegue
   - Recusa se: "automatizável" sem detalhar o que não é automático

9. Score de confiança ponderado (calcular explicitamente, campo a campo):
   - TAM com fonte verificável: 15 pts
   - 3+ casos de sucesso com receita declarada: 25 pts
   - 1+ caso de falhanço documentado encontrado: 10 pts
   - Capital inicial itemizado com ferramentas reais: 15 pts
   - Competidores com dados reais: 15 pts
   - Timeline baseada em dados de fundadores: 10 pts
   - Fit com perfil Vasco (horas/semana reais): 10 pts
   Total: 100 pts.
   - ≥85 pts: propõe ao CEO
   - 70-84 pts: marca como "em investigação — mais dados necessários"
   - <70 pts: descarta, não propõe

10. Formato padronizado obrigatório
   OPORTUNIDADE: [nome claro]
   MERCADO: [país(es) validado(s) com dados]
   TAM: [valor com fonte]
   CASOS REAIS: [3 fundadores/empresas com receita e link]
   CASO DE FALHANÇO: [1 exemplo documentado com razão]
   COMPETIDORES: [3 com preços e tráfego]
   CAPITAL INICIAL: [itemização detalhada, total em €]
   RECEITA ESTIMADA: [30/60/90 dias com base em casos reais]
   TEMPO ATÉ 1º CLIENTE: [dias, baseado em dados reais]
   INTERVENÇÃO DO VASCO: [horas de setup + horas/semana após + o que o Morgan não automatiza]
   SCORE: [X/100 pts com detalhe por critério]
   PRÓXIMO PASSO: [acção concreta hoje]

Se não conseguires preencher todos os campos com dados reais, NÃO propões. Dizes: "Dados insuficientes — em investigação."
"""

SCOUT_MISSAO_A_PROMPT = """És o Morgan Scout. Hoje é domingo — Missão A: identificar as melhores oportunidades de negócio para o Vasco Botelho da Costa.

CONTEXTO DO VASCO:
- Treinador de futebol no Moreirense FC (Portugal) — muito pouco tempo disponível
- Objetivo: €10.000/mês de rendimento passivo
- Capital disponível: pequeno (€200-1000 por oportunidade para começar)
- Tem o Morgan (8 agentes IA) para executar automaticamente
- Prefere negócios onde a sua intervenção seja ZERO após lançamento, ou máximo "aprovar uma vez por semana"
- NÃO quer negócios que dependam da sua identidade como treinador de futebol

CRITÉRIOS DE SELECÇÃO:
- Rendimento passivo real (não "semi-passivo")
- Mercados globais ou ibéricos (não só Portugal — mercado pequeno)
- Modelos com provas de receita de fundadores solo
- Capital inicial acessível
- Automatizável pelo Morgan

PROCESSO DE TRABALHO:
1. Pesquisa extensa em múltiplas fontes (IndieHackers, HN, Product Hunt, Reddit, Exa)
2. Identifica 5-10 candidatos iniciais
3. FALSIFICAÇÃO OBRIGATÓRIA: Para cada candidato, pesquisa activamente evidências contra:
   - "why [negócio] failed", "[negócio] not worth it reddit", "[negócio] saturated 2026"
   - Casos de pessoas que tentaram e desistiram
   - Mercados com race-to-bottom em preço ou dominados por grandes players
   - Se não encontras nada negativo, é sinal de pesquisa insuficiente — não de que não existe
4. Aplica o Quality Gate a cada um (incluindo score ponderado)
5. Propõe ao CEO apenas os que atingem ≥85 pts
6. Máximo 3 oportunidades por relatório (as 3 com score mais alto)

Usa as ferramentas pesquisar_mercado, pesquisar_web, hacker_news_trending, indiehackers_trending, product_hunt_trending para recolher dados.
Depois aplica o Quality Gate a cada candidato.
"""

SCOUT_MISSAO_B_PROMPT = """És o Morgan Scout. Hoje é quarta-feira — Missão B: melhorias ao ecossistema de agentes Morgan.

OBJETIVO:
Identificar ferramentas, APIs, ou técnicas novas (lançadas nos últimos 3 meses) que melhorem as capacidades dos agentes existentes.

AGENTES A ANALISAR: CEO, Coach, CFO, Creator, Solver, Operator, Marketeer

PARA CADA AGENTE:
- Existe uma API ou biblioteca mais recente que melhore as suas capacidades?
- Há uma ferramenta nova que valha integrar?
- O que os founders do IndieHackers/HN estão a usar para automatizar tarefas semelhantes?
- Qual o custo mensal? É compatível com o orçamento actual (mínimo)?

CRITÉRIOS DE REJEIÇÃO (Missão B):
- Não propõe ferramentas ainda em beta sem casos de uso em produção documentados por utilizadores reais
- Não propõe se o custo mensal for superior a €30/agente sem ROI demonstrável e calculado
- Para cada sugestão: existe pelo menos 1 utilizador real (fora da empresa que faz o produto) a usar em produção?
- Não propõe o que já foi sugerido nas últimas 4 semanas sem novo argumento

FORMATO:
[Agente] — [Melhoria] — [Impacto estimado] — [Custo/mês] — [Utilizador real em produção] — [Prioridade: ALTA/MÉDIA/BAIXA]

Máximo 5 sugestões de alta qualidade. Prefere menos com mais substância a mais com menos rigor.
"""


# ── Estado persistente ────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        return json.loads(SCOUT_STATE_FILE.read_text())
    except Exception:
        return {
            "oportunidades_investigacao": [],  # passaram gate parcialmente
            "oportunidades_propostas": [],      # passaram gate completo, propostas ao CEO
            "oportunidades_aprovadas": [],      # aprovadas pelo Vasco
            "oportunidades_rejeitadas": [],     # rejeitadas
            "ultima_missao_a": "",
            "ultima_missao_b": "",
            "missoes_completadas": 0,
        }


def _save_state(state: dict):
    SCOUT_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _get_tools_scout() -> list:
    from tools import TOOLS
    names = [
        "pesquisar_web", "pesquisar_mercado",
        "hacker_news_trending", "indiehackers_trending",
        "product_hunt_trending", "reddit_trending",
        "google_trends", "ver_historico_scout",
        "monitorizar_oportunidades_aprovadas",
    ]
    return [t for t in TOOLS if t["name"] in names]


def _run_tool(name: str, inp: dict) -> str:
    from tools import TOOL_FUNCTIONS
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return f"Ferramenta {name} não encontrada."
    try:
        return fn(**inp) if inp else fn()
    except Exception as e:
        return f"Erro em {name}: {e}"


def _chamar_claude_scout(system: str, messages: list, max_tokens: int = 2000) -> str:
    tools = _get_tools_scout()
    msgs = list(messages)
    while True:
        response = _client.messages.create(
            model="claude-opus-4-8",  # Scout usa Opus — decisões de negócio
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=msgs,
        )
        if response.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _run_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            msgs.append({"role": "user", "content": tool_results})
        else:
            return "".join(b.text for b in response.content if hasattr(b, "text"))


def _aplicar_quality_gate(oportunidade_raw: str) -> tuple[str, int]:
    """Aplica o Quality Gate a uma oportunidade descrita em texto.
    Retorna (texto_validado, confianca).
    """
    system = QUALITY_GATE_PROMPT + "\n\nSe os dados forem insuficientes, diz exactamente o que falta e porque não pode ser proposta agora."
    msgs = [{"role": "user", "content": f"Aplica o Quality Gate a esta oportunidade:\n\n{oportunidade_raw}"}]
    resultado = _chamar_claude_scout(system, msgs, max_tokens=1500)

    # Extrair confiança do texto
    import re
    m = re.search(r"CONFIANÇA:\s*(\d+)%", resultado, re.IGNORECASE)
    confianca = int(m.group(1)) if m else 0

    return resultado, confianca


# ── Missões ───────────────────────────────────────────────────────────────────

def missao_a_oportunidades() -> str:
    """Missão A — domingo 20h: identificar e validar oportunidades de negócio."""
    state = _load_state()

    # Camada 3 — memória episódica semântica
    mem_bloco = ""
    try:
        from episodic_memory import get_contexto_agente
        mem = get_contexto_agente("scout", "oportunidades negócio aprovadas rejeitadas rendimento passivo")
        if mem:
            mem_bloco = f"\n## Memória relevante:\n{mem}\n"
    except Exception:
        pass

    system = SCOUT_MISSAO_A_PROMPT + "\n\n" + QUALITY_GATE_PROMPT + mem_bloco

    msgs = [{"role": "user", "content": (
        "Inicia a Missão A. Pesquisa, identifica candidatos, e para cada um aplica o Quality Gate. "
        "Propõe apenas os que passam com ≥85% confiança. "
        "No final, apresenta o relatório estruturado com máximo 3 oportunidades validadas."
    )}]

    relatorio = _chamar_claude_scout(system, msgs, max_tokens=3000)

    # Guardar relatório
    hoje = date.today().strftime("%Y-%m-%d")
    report_file = SCOUT_REPORTS_DIR / f"missao_a_{hoje}.txt"
    report_file.write_text(relatorio, encoding="utf-8")

    state["ultima_missao_a"] = hoje
    state["missoes_completadas"] = state.get("missoes_completadas", 0) + 1
    _save_state(state)

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "missao_a", relatorio[:400])
    except Exception:
        pass

    return relatorio


def missao_b_melhorias() -> str:
    """Missão B — quarta 20h: melhorias ao ecossistema de agentes."""
    from sistema_service import get_agentes_ativos
    state = _load_state()

    try:
        agentes = get_agentes_ativos()
        agentes_lista = "\n".join(f"- {v['nome']}: {v['descricao']}" for v in agentes.values())
    except Exception:
        agentes_lista = "CEO, Scout, Coach, CFO, Creator, Solver, Operator, Marketeer"

    # Camada 3 — memória episódica semântica
    mem_bloco = ""
    try:
        from episodic_memory import get_contexto_agente
        mem = get_contexto_agente("scout", "melhorias agentes ferramentas APIs sistema Morgan")
        if mem:
            mem_bloco = f"\n## Memória relevante:\n{mem}\n"
    except Exception:
        pass

    system = SCOUT_MISSAO_B_PROMPT + mem_bloco
    msgs = [{"role": "user", "content": (
        f"Agentes actuais:\n{agentes_lista}\n\n"
        "Pesquisa melhorias. Usa hacker_news_trending e pesquisar_web. "
        "Propõe apenas melhorias com impacto real e custo justificado."
    )}]

    relatorio = _chamar_claude_scout(system, msgs, max_tokens=1500)

    hoje = date.today().strftime("%Y-%m-%d")
    report_file = SCOUT_REPORTS_DIR / f"missao_b_{hoje}.txt"
    report_file.write_text(relatorio, encoding="utf-8")

    state["ultima_missao_b"] = hoje
    _save_state(state)

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "missao_b", relatorio[:400])
    except Exception:
        pass

    return relatorio


MISSAO_C_INTERVALO_DIAS = 30   # análise de saúde de negócios activos
MISSAO_D_INTERVALO_DIAS = 14   # pesquisa de estratégias de trading


def missao_c_saude_negocios() -> str:
    """
    Missão C — corre a cada 30 dias por negócio activo.
    Analisa se o negócio ainda faz sentido, mercados a explorar/abandonar,
    alterações recomendadas. Padrão obrigatório para TODOS os negócios aprovados.
    """
    state = _load_state()
    hoje = date.today().strftime("%Y-%m-%d")

    # Ler negócios activos do sistema
    try:
        from sistema_service import get_negocios_ativos
        negocios = get_negocios_ativos()
    except Exception:
        negocios = {"planneratlas_etsy": {"nome": "PlannerAtlas (Etsy)", "plataforma": "Etsy", "descricao": "Planners digitais PT/ES/DE"}}

    if not negocios:
        return "Sem negócios activos para analisar."

    # Verificar quais precisam de análise (30 dias desde última)
    missoes_c = state.get("missoes_c", {})
    negocios_a_analisar = []
    for chave, neg in negocios.items():
        ultima = missoes_c.get(chave, "")
        if not ultima:
            negocios_a_analisar.append((chave, neg))
        else:
            from datetime import timedelta
            dias_passados = (date.today() - date.fromisoformat(ultima)).days
            if dias_passados >= MISSAO_C_INTERVALO_DIAS:
                negocios_a_analisar.append((chave, neg))

    if not negocios_a_analisar:
        return f"Missão C: todos os negócios analisados recentemente (próxima em {MISSAO_C_INTERVALO_DIAS} dias)."

    relatorios = []
    for chave, neg in negocios_a_analisar:
        nome = neg.get("nome", chave)
        plataforma = neg.get("plataforma", "?")
        descricao = neg.get("descricao", "")

        # Dados reais da plataforma se disponível
        dados_reais = ""
        if "etsy" in plataforma.lower():
            try:
                from etsy_service import estado_para_operador
                dados_reais = estado_para_operador()
            except Exception:
                pass

        system = f"""És o Morgan Scout. Fazes análise de saúde periódica de negócios activos do império BCVertex.
Analisa com dados reais. Sem hype. PT-PT. Máximo 20 linhas por negócio.

Para cada negócio responde:
1. O negócio ainda faz sentido? (sim/não/condicional + dados)
2. Mercados a expandir (com dados de procura)
3. Mercados a abandonar ou reduzir
4. Alterações recomendadas ao produto/preço/posicionamento
5. Ameaças detectadas (concorrência, algoritmo, sazonalidade)
6. Próximas 3 acções concretas (ordenadas por impacto)
7. Score de saúde: 0-10"""

        msgs = [{"role": "user", "content": (
            f"Negócio: {nome} | Plataforma: {plataforma}\n"
            f"Descrição: {descricao}\n"
            f"{f'Dados reais:{chr(10)}{dados_reais}' if dados_reais else ''}\n\n"
            "Faz a análise de saúde completa. Pesquisa tendências de mercado actuais."
        )}]

        relatorio = _chamar_claude_scout(system, msgs, max_tokens=1500)
        relatorios.append(f"=== {nome} ===\n{relatorio}")

        # Registar data da análise
        missoes_c[chave] = hoje
        state["missoes_c"] = missoes_c

        # Guardar relatório
        report_file = SCOUT_REPORTS_DIR / f"missao_c_{chave}_{hoje}.txt"
        report_file.write_text(relatorio, encoding="utf-8")

        try:
            from episodic_memory import registar_evento
            registar_evento("scout", f"missao_c_{chave}", relatorio[:400])
        except Exception:
            pass

    _save_state(state)
    return "\n\n".join(relatorios)


def missao_d_trading_estrategia() -> str:
    """
    Missão D — corre a cada 14 dias.
    Pesquisa estratégias de trading na Binance: novas estratégias, backtests publicados,
    mudanças de mercado, se a estratégia actual (Supertrend 4h BTC/USDT) ainda é válida.
    """
    state = _load_state()
    hoje = date.today().strftime("%Y-%m-%d")

    ultima_d = state.get("ultima_missao_d", "")
    if ultima_d:
        from datetime import timedelta
        dias = (date.today() - date.fromisoformat(ultima_d)).days
        if dias < MISSAO_D_INTERVALO_DIAS:
            return f"Missão D: próxima análise de trading em {MISSAO_D_INTERVALO_DIAS - dias} dias."

    system = """És o Morgan Scout a fazer análise de estratégia de trading.
Pesquisa dados reais. Cita fontes. PT-PT. Máximo 20 linhas.

Responde:
1. A estratégia Supertrend 4h BTC/USDT ainda é válida? (win rate publicado, condições actuais)
2. Que alterações de parâmetros têm melhor performance no mercado actual?
3. Há estratégias alternativas com melhor expectancy para BTC com $100-500 capital?
4. Condições de mercado actuais (trend, volatilidade, dominance BTC)
5. Recomendação: manter estratégia / ajustar parâmetros / considerar alternativa
6. Proposta concreta para o CFO avaliar"""

    msgs = [{"role": "user", "content": (
        "Analisa a estratégia de trading actual do Morgan (Supertrend BTC/USDT 4h, capital $100 USDT, Binance live). "
        "Pesquisa resultados recentes publicados desta estratégia e alternativas. "
        "Contexto: operador com pouco tempo, quer rendimento passivo, não quer monitorizar activamente."
    )}]

    relatorio = _chamar_claude_scout(system, msgs, max_tokens=1500)

    state["ultima_missao_d"] = hoje
    _save_state(state)

    report_file = SCOUT_REPORTS_DIR / f"missao_d_trading_{hoje}.txt"
    report_file.write_text(relatorio, encoding="utf-8")

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "missao_d_trading", relatorio[:400])
    except Exception:
        pass

    return relatorio


def get_scout_reply(user_message: str) -> str:
    """Resposta directa do Scout quando invocado na conversa."""
    try:
        from episodic_memory import get_contexto_agente
        mem_sistema = get_contexto_agente("scout", user_message or "oportunidades negócio mercado SaaS rendimento passivo")
    except Exception:
        mem_sistema = ""
    mem_bloco = f"\n## Memória relevante:\n{mem_sistema}\n\n" if mem_sistema else ""
    system = (
        "És o Morgan Scout, o agente de inteligência de mercado do império BCVertex.\n"
        "Especialidade: identificar e VALIDAR oportunidades de negócio com dados reais.\n"
        "Nunca propões hipóteses sem dados. Nunca exageras potencial. "
        "Cada afirmação tem fonte ou é marcada como estimativa.\n"
        "Responde sempre em PT-PT. Tom: directo, factual, sem hype.\n\n"
        + QUALITY_GATE_PROMPT
        + mem_bloco
    )
    msgs = [{"role": "user", "content": user_message}]
    reply = _chamar_claude_scout(system, msgs)

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "conversa", f"Q: {user_message[:100]} | R: {reply[:200]}")
    except Exception:
        pass

    return reply


def estado_scout() -> dict:
    """Estado actual do Scout para o CEO."""
    state = _load_state()
    return {
        "ultima_missao_a": state.get("ultima_missao_a", "nunca"),
        "ultima_missao_b": state.get("ultima_missao_b", "nunca"),
        "oportunidades_em_investigacao": len(state.get("oportunidades_investigacao", [])),
        "oportunidades_propostas": len(state.get("oportunidades_propostas", [])),
        "oportunidades_aprovadas": len(state.get("oportunidades_aprovadas", [])),
        "missoes_completadas": state.get("missoes_completadas", 0),
    }
