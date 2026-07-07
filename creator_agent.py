"""
Morgan Creator Agent
Constrói sub-Morgans para oportunidades de negócio aprovadas pelo Scout.
Cada sub-Morgan é um agente especializado com ferramentas, memória, ciclo de vida e reporting.

Reports automáticos desativados por defeito (REPORTS_ENABLED = False).
Ativar quando houver pelo menos um negócio com receita > 0.
"""
import os
import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path(__file__).parent / "memory"
CREATOR_STATE_FILE = MEMORY_DIR / "creator_state.json"

# ── Controlo de reports ──────────────────────────────────────────────────────
# Mantido em False até haver receita ativa. Mudar para True manualmente ou via CEO.
REPORTS_ENABLED = False

# ── Thresholds de autonomia hierárquica ──────────────────────────────────────
# Quando um negócio atinge estes valores, ganha gestão própria automaticamente.
# Abaixo de €500: Morgan CEO gere directamente.
# €500–€2k: 2-3 agentes operacionais, CEO ainda supervisiona.
# €2k–€5k: negócio ganha CEO próprio, Morgan CEO recebe relatórios.
# €5k+: CEO + CFO próprios — empresa autónoma dentro do império.
AUTONOMY_THRESHOLDS = [
    {
        "receita_min": 500,
        "receita_max": 2000,
        "estrutura": "multi_agente",
        "agentes": ["ops", "crescimento"],
        "descricao": "Equipa básica — Ops + Crescimento",
        "ceo_proprio": False,
        "cfo_proprio": False,
    },
    {
        "receita_min": 2000,
        "receita_max": 5000,
        "estrutura": "ceo_proprio",
        "agentes": ["ceo", "ops", "marketing"],
        "descricao": "CEO próprio — Morgan CEO recebe relatórios",
        "ceo_proprio": True,
        "cfo_proprio": False,
    },
    {
        "receita_min": 5000,
        "receita_max": None,  # sem tecto
        "estrutura": "empresa_autonoma",
        "agentes": ["ceo", "cfo", "ops", "marketing", "suporte"],
        "descricao": "Empresa autónoma — CEO + CFO próprios",
        "ceo_proprio": True,
        "cfo_proprio": True,
    },
]


# ── Knowledge Registry — o Creator sabe onde ir buscar o que precisa por domínio ──

DOMAIN_KNOWLEDGE = {
    "directorio": {
        "fontes_pesquisa": [
            "profitable directory website niche 2026 indiehackers revenue",
            "directory business model monetization case study AppSumo",
            "niche directory PT BR market gap opportunity 2026",
        ],
        "comunidades": ["IndieHackers", "r/indiehackers", "r/entrepreneur", "MicroAcquire"],
        "ferramentas_data": ["Ahrefs (SEO)", "SimilarWeb (tráfego)", "Google Trends"],
        "metricas_sucesso": ["visitantes/mês", "listagens pagas", "receita afiliados"],
        "plataformas_venda": ["listagens diretas", "afiliados", "leads pagos"],
    },
    "templates_digitais": {
        "fontes_pesquisa": [
            "digital products templates Gumroad bestsellers 2026 revenue",
            "Etsy digital downloads passive income 2026 Portugal Brazil",
            "notion templates Lemon Squeezy top sellers 2026",
        ],
        "comunidades": ["r/passive_income", "Gumroad creators", "AppSumo marketplace"],
        "ferramentas_data": ["Gumroad analytics", "Etsy stats", "Lemon Squeezy dashboard"],
        "metricas_sucesso": ["unidades vendidas/mês", "preço médio", "churn"],
        "plataformas_venda": ["Gumroad", "Lemon Squeezy", "Etsy", "Payhip"],
    },
    "relatorios_taticos": {
        "fontes_pesquisa": [
            "football tactical analysis SaaS coaches 2026 revenue pricing",
            "Wyscout alternative smaller clubs affordable AI reports",
            "AI football scouting platform MLS Liga Portugal subscription 2026",
            "StatsBomb open data API football analytics startups",
        ],
        "comunidades": ["r/soccer", "r/footballtactics", "LinkedIn coaches groups"],
        "ferramentas_data": ["Wyscout API", "FBref", "StatsBomb", "Transfermarkt", "API Football"],
        "metricas_sucesso": ["clubes subscritores", "preço/relatório", "churn de clubes"],
        "plataformas_venda": ["subscrição direta", "contacto a clubes", "parceria com ligas"],
        "vantagem_vasco": "Treinador profissional — credibilidade e rede de contactos no futebol PT/ES",
    },
    "micro_saas": {
        "fontes_pesquisa": [
            "micro SaaS vertical niche 2026 10k month founder story indiehackers",
            "SaaS one person company profitable 2026 low competition",
            "vertical SaaS niche monopoly 2026 case study revenue",
        ],
        "comunidades": ["IndieHackers", "r/SaaS", "r/entrepreneur", "MicroAcquire"],
        "ferramentas_data": ["Stripe dashboard", "ChartMogul", "ProfitWell"],
        "metricas_sucesso": ["MRR", "churn rate", "LTV/CAC"],
        "plataformas_venda": ["subscrição SaaS", "freemium", "usage-based pricing"],
    },
    "investimento": {
        "fontes_pesquisa": [
            "passive portfolio management AI 2026 automation dividends",
            "automated investment strategy ETF rebalancing AI tools",
            "passive income investing Portugal 2026 tax efficient",
        ],
        "comunidades": ["r/investing", "r/financialindependence", "r/eupersonalfinance"],
        "ferramentas_data": ["Interactive Brokers API", "Yahoo Finance", "Alpha Vantage"],
        "metricas_sucesso": ["rendimento anual %", "volatilidade", "drawdown máximo"],
        "plataformas_venda": ["autogestão", "advisory fee se escalado a outros"],
    },
}


# ── Estado ──────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        return json.loads(CREATOR_STATE_FILE.read_text())
    except Exception:
        return {"sub_morgans": {}, "criados_em": []}

def _save_state(state: dict):
    CREATOR_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── Templates de sub-Morgan ──────────────────────────────────────────────────

TEMPLATES = {
    "directorio": {
        "nome": "Morgan Directório",
        "descricao": "Gere directório de nicho PT/BR — conteúdo, SEO, monetização",
        "ferramentas": ["pesquisar_web", "tavily_search"],
        "prompt_base": """És o Morgan Directório, um sub-agente especializado em construir e gerir
directórios de nicho em português. O teu trabalho é:
1. Identificar categorias e subcategorias relevantes para o nicho
2. Pesquisar e catalogar entidades relevantes
3. Sugerir estratégias de monetização (listagens pagas, leads, afiliados)
4. Gerar conteúdo SEO optimizado em PT-PT
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "templates_digitais": {
        "nome": "Morgan Templates",
        "descricao": "Cria e vende produtos digitais/templates em português",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan Templates, especializado em criar e vender produtos digitais
em português (templates, planeadores, guias). O teu trabalho é:
1. Identificar nichos com baixa concorrência em PT
2. Criar produtos digitais de alta margem
3. Optimizar páginas de venda em Gumroad/Etsy
4. Monitorizar vendas e ajustar estratégia
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "relatorios_taticos": {
        "nome": "Morgan Tático",
        "descricao": "Gera relatórios táticos automáticos para clubes PT/ES",
        "ferramentas": ["pesquisar_web", "api_football"],
        "prompt_base": """És o Morgan Tático, especializado em análise e relatórios táticos de futebol.
Constróis relatórios pré-jogo e pós-jogo em português para clubes. O teu trabalho é:
1. Analisar dados de jogos e adversários via API Football
2. Identificar padrões táticos e vulnerabilidades
3. Gerar relatórios em linguagem natural para treinadores
4. Traduzir dados XML de Metrica/SportsCode em briefings legíveis
A vantagem competitiva é o conhecimento insider do Vasco como treinador profissional.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "micro_saas": {
        "nome": "Morgan SaaS",
        "descricao": "Desenvolve e lança micro-SaaS vertical de nicho",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan SaaS, especializado em identificar e construir micro-SaaS
para nichos verticais específicos. O teu trabalho é:
1. Validar o problema com utilizadores reais antes de construir
2. Definir MVP mínimo e stack tecnológico
3. Construir landing page e sistema de pagamento
4. Iterar com base em feedback real
Foco: resolver UM problema completamente para um grupo muito específico.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
}

OPORTUNIDADE_TO_TEMPLATE = {
    "Directório de nicho PT/BR monetizado": "directorio",
    "Produtos digitais/templates em PT": "templates_digitais",
    "Relatórios táticos automáticos em PT/ES (pivô futebol)": "relatorios_taticos",
    "Micro-SaaS vertical de nicho": "micro_saas",
}


# ── Interface pública ────────────────────────────────────────────────────────

def criar_sub_morgan(oportunidade: str) -> dict:
    """Cria um sub-Morgan para uma oportunidade aprovada pelo Scout."""
    state = _load_state()

    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade)
    if not template_key:
        # Template genérico para oportunidades não mapeadas
        template_key = "micro_saas"

    template = TEMPLATES[template_key].copy()
    sub_id = template_key + "_" + datetime.now().strftime("%Y%m%d")

    if sub_id in state["sub_morgans"]:
        return {"status": "ja_existe", "id": sub_id, "nome": template["nome"]}

    knowledge = DOMAIN_KNOWLEDGE.get(template_key, {})
    sub_morgan = {
        "id": sub_id,
        "oportunidade": oportunidade,
        "nome": template["nome"],
        "descricao": template["descricao"],
        "ferramentas": template["ferramentas"],
        "prompt_base": template["prompt_base"],
        "criado_em": datetime.now().isoformat(),
        # Ciclo de vida: validacao → mvp → lancamento → crescimento → consolidacao → analise
        "fase": "validacao",
        "receita_atual": 0.0,
        "reports_enabled": False,  # ativar só quando houver receita
        # Knowledge do domínio herdado do registry
        "fontes_pesquisa": knowledge.get("fontes_pesquisa", []),
        "comunidades": knowledge.get("comunidades", []),
        "metricas_sucesso": knowledge.get("metricas_sucesso", []),
        "vantagem_vasco": knowledge.get("vantagem_vasco", ""),
        "mem0_user_id": f"sub_{template_key}",
        "metricas": {"interacoes": 0, "tarefas_concluidas": 0},
    }

    state["sub_morgans"][sub_id] = sub_morgan
    state["criados_em"].append({
        "id": sub_id,
        "oportunidade": oportunidade,
        "data": datetime.now().isoformat(),
    })
    _save_state(state)

    return {"status": "criado", "id": sub_id, "nome": template["nome"]}


def listar_sub_morgans() -> list:
    """Lista todos os sub-Morgans existentes."""
    state = _load_state()
    return list(state["sub_morgans"].values())


def get_sub_morgan(sub_id: str) -> dict:
    """Retorna um sub-Morgan pelo ID."""
    state = _load_state()
    return state["sub_morgans"].get(sub_id, {})


def get_prompt_sub_morgan(oportunidade: str) -> str:
    """Retorna o system prompt para o sub-Morgan de uma oportunidade."""
    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade, "micro_saas")
    return TEMPLATES[template_key]["prompt_base"]


def activar_sub_morgan(oportunidade: str, mensagem: str) -> str:
    """Invoca o sub-Morgan de uma oportunidade com uma mensagem."""
    import anthropic
    from tools import TOOLS, TOOL_FUNCTIONS
    from scout_memory import _load as load_scout

    scout_data = load_scout()
    aprovadas = scout_data.get("aprovadas", [])
    if oportunidade not in aprovadas:
        return f"Oportunidade '{oportunidade}' não está aprovada pelo Vasco."

    state = _load_state()
    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade, "micro_saas")
    template = TEMPLATES[template_key]

    ferramentas_disponiveis = [t for t in TOOLS if t["name"] in template["ferramentas"]]

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    msgs = [{"role": "user", "content": mensagem}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=[{"type": "text", "text": template["prompt_base"],
                      "cache_control": {"type": "ephemeral"}}],
            messages=msgs,
            tools=ferramentas_disponiveis if ferramentas_disponiveis else [],
        )

        if response.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    func = TOOL_FUNCTIONS.get(block.name)
                    result = func(**block.input) if func else f"Ferramenta {block.name} não encontrada."
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            msgs.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if hasattr(block, "text"):
                    # Actualiza métricas
                    for sub in state["sub_morgans"].values():
                        if sub.get("oportunidade") == oportunidade:
                            sub["metricas"]["interacoes"] += 1
                    _save_state(state)
                    return block.text
            return ""


def verificar_autonomia(sub_id: str) -> dict:
    """
    Verifica se um negócio atingiu receita suficiente para ganhar gestão própria.
    Retorna a estrutura recomendada e se é uma mudança face ao estado actual.
    """
    state = _load_state()
    sub = state["sub_morgans"].get(sub_id)
    if not sub:
        return {"status": "nao_encontrado"}

    receita = sub.get("receita_atual", 0)
    estrutura_atual = sub.get("estrutura_autonomia", "ceo_central")

    # Determinar threshold aplicável
    threshold_aplicavel = None
    for t in AUTONOMY_THRESHOLDS:
        r_max = t["receita_max"] if t["receita_max"] else float("inf")
        if t["receita_min"] <= receita < r_max:
            threshold_aplicavel = t
            break

    if not threshold_aplicavel:
        # Abaixo de €500 — CEO central gere directamente
        nova_estrutura = "ceo_central"
        descricao = "CEO central gere directamente"
        agentes = []
        ceo_proprio = False
        cfo_proprio = False
    else:
        nova_estrutura = threshold_aplicavel["estrutura"]
        descricao = threshold_aplicavel["descricao"]
        agentes = threshold_aplicavel["agentes"]
        ceo_proprio = threshold_aplicavel["ceo_proprio"]
        cfo_proprio = threshold_aplicavel["cfo_proprio"]

    mudou = nova_estrutura != estrutura_atual

    if mudou:
        sub["estrutura_autonomia"] = nova_estrutura
        sub["agentes_autonomia"] = agentes
        sub["ceo_proprio"] = ceo_proprio
        sub["cfo_proprio"] = cfo_proprio
        _save_state(state)

    return {
        "status": "ok",
        "sub_id": sub_id,
        "nome": sub["nome"],
        "receita": receita,
        "estrutura": nova_estrutura,
        "descricao": descricao,
        "agentes_necessarios": agentes,
        "ceo_proprio": ceo_proprio,
        "cfo_proprio": cfo_proprio,
        "mudanca": mudou,
        "alerta_vasco": mudou and ceo_proprio,  # avisa o Vasco quando ganha CEO próprio
    }


def avancar_fase(sub_id: str) -> dict:
    """Avança o sub-Morgan para a próxima fase do ciclo de vida."""
    FASES = ["validacao", "mvp", "lancamento", "crescimento", "consolidacao", "analise", "autonomia"]
    state = _load_state()
    sub = state["sub_morgans"].get(sub_id)
    if not sub:
        return {"status": "nao_encontrado"}
    fase_atual = sub.get("fase", "validacao")
    idx = FASES.index(fase_atual) if fase_atual in FASES else 0
    if idx < len(FASES) - 1:
        sub["fase"] = FASES[idx + 1]
        # Ativar reports automaticamente a partir do lançamento
        if sub["fase"] in ("lancamento", "crescimento", "consolidacao", "analise"):
            sub["reports_enabled"] = True
        _save_state(state)
        return {"status": "ok", "fase_anterior": fase_atual, "fase_nova": sub["fase"]}
    return {"status": "ja_na_ultima_fase", "fase": fase_atual}


def registar_receita(sub_id: str, receita_mensal: float) -> dict:
    """Atualiza a receita de um sub-Morgan. Ativa reports e verifica autonomia."""
    state = _load_state()
    sub = state["sub_morgans"].get(sub_id)
    if not sub:
        return {"status": "nao_encontrado"}
    receita_anterior = sub.get("receita_atual", 0)
    sub["receita_atual"] = receita_mensal
    if receita_mensal > 0:
        sub["reports_enabled"] = True
    _save_state(state)

    # Verificar se muda de patamar de autonomia
    autonomia = verificar_autonomia(sub_id)

    resultado = {
        "status": "ok",
        "receita_anterior": receita_anterior,
        "receita_atual": receita_mensal,
        "reports_enabled": sub["reports_enabled"],
        "estrutura": autonomia["estrutura"],
        "descricao_estrutura": autonomia["descricao"],
    }

    if autonomia["alerta_vasco"]:
        resultado["alerta"] = (
            f"🏢 {sub['nome']} atingiu €{receita_mensal:.0f}/mês — "
            f"recomendo criar {autonomia['descricao']}. "
            f"Agentes necessários: {', '.join(autonomia['agentes_necessarios'])}."
        )

    return resultado


def report_global_creator() -> str:
    """Relatório global do Creator para o CEO — só corre se REPORTS_ENABLED ou houver receita ativa."""
    state = _load_state()
    subs = list(state["sub_morgans"].values())

    if not subs:
        return "Creator: nenhum sub-Morgan ativo."

    receita_total = sum(s.get("receita_atual", 0) for s in subs)
    com_receita = [s for s in subs if s.get("receita_atual", 0) > 0]

    if not REPORTS_ENABLED and receita_total == 0:
        return "Creator: reports em standby — sem receita ativa ainda."

    linhas = [f"MORGAN CREATOR — Relatório Global\nData: {datetime.now().strftime('%d/%m/%Y')}\n"]
    for sub in subs:
        linhas.append(
            f"• {sub['nome']} [{sub.get('fase','?')}]"
            f" — Receita: €{sub.get('receita_atual',0):.0f}/mês"
            f" — Reports: {'ON' if sub.get('reports_enabled') else 'standby'}"
        )
    linhas.append(f"\nReceita total: €{receita_total:.0f}/mês | Com receita: {len(com_receita)}/{len(subs)}")
    return "\n".join(linhas)


def get_domain_knowledge(oportunidade: str) -> str:
    """Devolve o knowledge do domínio formatado para uso em prompts."""
    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade, "micro_saas")
    k = DOMAIN_KNOWLEDGE.get(template_key, {})
    if not k:
        return ""
    lines = ["## Knowledge do domínio:"]
    if k.get("fontes_pesquisa"):
        lines.append("Queries de pesquisa recomendadas (em inglês):\n- " + "\n- ".join(k["fontes_pesquisa"]))
    if k.get("comunidades"):
        lines.append("Comunidades a monitorizar: " + ", ".join(k["comunidades"]))
    if k.get("metricas_sucesso"):
        lines.append("Métricas de sucesso: " + ", ".join(k["metricas_sucesso"]))
    if k.get("vantagem_vasco"):
        lines.append(f"Vantagem do Vasco: {k['vantagem_vasco']}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Teste rápido
    resultado = criar_sub_morgan("Directório de nicho PT/BR monetizado")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print("\nSub-Morgans criados:", len(listar_sub_morgans()))
    print("\nKnowledge do domínio:")
    print(get_domain_knowledge("Directório de nicho PT/BR monetizado"))
