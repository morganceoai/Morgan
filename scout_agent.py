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

from claude_guard import GuardedClient as _GuardedClient
_client = _GuardedClient("scout")


# ── Quality Gate ──────────────────────────────────────────────────────────────

QUALITY_GATE_PROMPT = """És o Morgan Scout. Antes de propor qualquer oportunidade ao CEO, aplica o Quality Gate obrigatório.

QUALITY GATE — 10 critérios (todos obrigatórios):

1. TAM (Mercado Total Endereçável)
   - Obrigatório: número real com fonte citada (ex: "$4.2B em 2026, Statista")
   - Recusa se: "grande mercado", "mercado em crescimento" sem números

2. Casos de sucesso reais
   - Obrigatório: mínimo 3 fundadores reais com receita declarada e links
   - Recusa se: só "este modelo funciona" sem exemplos verificáveis

3. Mercado por país validado — MÍNIMO 2 mercados distintos obrigatórios
   - Obrigatório: dados concretos por país (volume de pesquisa, nº empresas alvo, competidores locais)
   - OBRIGATÓRIO: avaliar pelo menos 1 mercado anglófono (US/UK/AU) E 1 mercado ibérico/DACH
   - Recusa se: apenas PT validado (mercado <10M hab = muito pequeno para escalar)
   - Recusa se: "mercado global" sem dados por país específico

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

8. Fit real com perfil do Vasco — avaliação proporcional ao rendimento
   - Horas de setup estimadas: número concreto (não "fácil de configurar")
   - Horas de operação semanal após setup: número concreto
   - O Morgan consegue executar 90%+ das tarefas operacionais? Listar explicitamente o que NÃO consegue
   - Aplicar a tabela de threshold esforço/rendimento (ver CONTEXTO DO VASCO):
     * Calcula o rendimento documentado real (não hipóteses)
     * Verifica se o setup e operação cabem no tier correspondente
     * Se cabe: FIT = SIM. Se não cabe: FIT = NÃO, mesmo que pareça prometedor.
   - Recusa se: "automatizável" sem listar especificamente as tarefas que NÃO são automáticas
   - Recusa se: rendimento projectado sem pelo menos 2 fundadores reais com números públicos

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
   CAPITAL_MAXIMO_TIER: [€300 / €1.500 / €3.000 / €5.000 — baseado no rendimento documentado]
   INTERVENÇÃO DO VASCO: [horas de setup reais] setup + [horas/semana reais] operação semanal | FIT: [SIM/NÃO segundo tabela] | O que o Morgan NÃO automatiza: [lista concreta]
   SCORE: [X/100 pts com detalhe por critério]
   PRÓXIMO PASSO: [acção concreta hoje]

Se não conseguires preencher todos os campos com dados reais, NÃO propões. Dizes: "Dados insuficientes — em investigação."

OBRIGAÇÃO DE VERIFICAÇÃO COM FERRAMENTAS:
Para cada critério que exige dados reais, usa as ferramentas disponíveis ANTES de preencher o campo:
- TAM: usa pesquisar_mercado("TAM [nicho] market size 2026") + pesquisar_web("site:statista.com OR site:grandviewresearch.com [nicho]")
- Casos de sucesso: usa indiehackers_trending() + pesquisar_web("[nicho] founder revenue 2025 2026")
- Caso de falhanço: usa pesquisar_web("[nicho] failed why reddit") + reddit_trending()
- Competidores: usa scout_g2_capterra(nicho=...) + pesquisar_web("[competidor] traffic similarweb")
- Mercado por país: usa scout_pesquisa_multilang() para cada modo geográfico

Não preenches nenhum campo com conhecimento do teu treino sem verificar com pesquisa actual.
Se a ferramenta não retornar dados suficientes, escreves "Dados insuficientes — em investigação" nesse campo.
"""

SCOUT_MISSAO_A_PROMPT = """És o Morgan Scout. Hoje é domingo — Missão A: identificar as melhores oportunidades de negócio para o Vasco Botelho da Costa.

CONTEXTO DO VASCO:
- Treinador de futebol no Moreirense FC (Portugal) — tempo limitado mas não zero
- Objetivo: €10.000/mês de rendimento passivo
- Tem o Morgan (8+ agentes IA) para executar automaticamente
- NÃO quer negócios que dependam da sua identidade como treinador de futebol
- O modelo de negócio pode ser qualquer coisa que o Morgan consiga operar — não limitar à stack actual (Python, Etsy). Se a oportunidade for grande, o Creator constrói o que for necessário.

THRESHOLD DE ESFORÇO vs RENDIMENTO — aplicar esta tabela a cada oportunidade:

  Rendimento projectado (6 meses)  | Setup máximo aceitável | Operação semanal após setup | Capital inicial máximo
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  < €1.000/mês                     | 5h                     | 30 min/semana               | €300
  €1.000 – €3.000/mês              | 20h                    | 2h/semana                   | €1.500
  €3.000 – €7.000/mês              | 40h                    | 4h/semana                   | €3.000
  > €7.000/mês                     | 80h                    | 8h/semana                   | €5.000

Regra: se o rendimento real documentado (não hipóteses) justificar o esforço segundo a tabela, a oportunidade passa. Um negócio que requer 60h de setup mas pode gerar €8k/mês é melhor do que um que requer 2h e gera €200/mês.

"Rendimento documentado" significa: fundadores reais que reportaram esses números publicamente (IndieHackers, Twitter/X, Reddit, entrevistas). Projecções sem dados reais de pessoas reais = hipótese = não conta.

MERCADOS ALVO — OBRIGATÓRIO pesquisar TODOS os 3 modos geográficos:
- Modo A "anglofonico": US, UK, AU, CA — mercado maior, mais competitivo, mais data disponível
- Modo B "iberico_latam": PT, BR, ES, MX, AR — vantagem linguística, concorrência 40-60% menor
- Modo C "dach": DE, AT, CH — mercados com alto poder de compra, pouco explorados por portugueses
- Excluir: China, Japão (barreiras operacionais demasiado complexas para o Morgan)
- Brasil e Tailândia — incluir quando há dados concretos de receita documentada

USA AS FERRAMENTAS NESTA ORDEM:
1. scout_pesquisa_multilang(geo_mode="anglofonico", keywords=[...]) — US/UK primeiro
2. scout_pesquisa_multilang(geo_mode="iberico_latam", keywords=[...]) — PT/BR/ES
3. scout_pesquisa_multilang(geo_mode="dach", keywords=[...]) — DE/AT/CH
4. hacker_news_trending() — tendências tech actuais
5. indiehackers_trending() — fundadores reais com receita
6. product_hunt_trending() — produtos emergentes
7. reddit_trending() — discussões de fundadores
8. scout_g2_capterra(nicho=...) — para cada candidato sério
9. scout_job_boards(nicho=...) — sinal de mercado

PROCESSO DE TRABALHO:
1. Pesquisa extensa com as ferramentas acima em TODOS os modos geográficos
2. Identifica 5-10 candidatos iniciais (de múltiplos mercados, não apenas PT)
3. Para cada candidato, calcula o SCORING MULTIDIMENSIONAL (5 dimensões):
   - trend_velocity: velocidade de crescimento do interesse (1-10) — dados de pesquisa, posts recentes
   - competition_gap: lacuna de mercado sem solução adequada (1-10) — G2/Capterra, reviews negativas
   - social_signal: volume e qualidade de discussão orgânica (1-10) — Reddit, HN, IH
   - monetization_intent: evidência de que pessoas pagam (1-10) — job boards, preços de competitors
   - frustration_level: nível de dor do cliente documentada (1-10) — Reddit complaints, reviews 1-2 estrelas
   Score multidimensional = média ponderada (trend*20% + gap*25% + social*20% + monetization*25% + frustration*10%)
4. FALSIFICAÇÃO OBRIGATÓRIA: Para cada candidato com score ≥6, pesquisa evidências contra:
   - "why [negócio] failed", "[negócio] not worth it reddit", "[negócio] saturated 2026"
   - Casos de pessoas que tentaram e desistiram
   - Se não encontras nada negativo, é sinal de pesquisa insuficiente
5. Aplica o Quality Gate completo a cada candidato com score multidimensional ≥6
6. Propõe ao CEO apenas os que atingem ≥85 pts no Quality Gate
7. Máximo 3 oportunidades por relatório (as 3 com score mais alto)

FORMATO DO RELATÓRIO:
Para cada oportunidade proposta, inclui obrigatoriamente:
- Modo geográfico principal validado (anglofonico/iberico_latam/dach)
- Score multidimensional (5 dimensões + média)
- Diferencial por mercado (ex: "US: competição alta; BR: quasi-monopólio possível")
- Todos os campos do Quality Gate preenchidos com dados reais
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
        "scout_pesquisa_multilang", "scout_g2_capterra", "scout_job_boards",
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
    max_iterations = 30  # guard: evita loops infinitos de tool_use em produção
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        response = _client.messages.create(
            model="claude-opus-4-8",  # Scout usa Opus — decisões de negócio
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
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
    return "[Scout: limite de iterações atingido após 30 chamadas — relatório pode estar incompleto]"


_DECISION_LOG = Path(__file__).parent / "memory" / "scout_decision_log.jsonl"


def _registar_decisao_scout(
    oportunidade: str,
    score: int,
    decisao: str,
    relatorio_completo: str,
) -> None:
    """Regista a decisão do Quality Gate com raciocínio completo. Append-only."""
    import re
    entrada = {
        "ts": datetime.now().isoformat(),
        "oportunidade": oportunidade,
        "score": score,
        "decisao": decisao,  # APROVADA | EM_INVESTIGACAO | REJEITADA
        "criterios": {
            "tam": _extrair_campo(relatorio_completo, "TAM"),
            "casos_reais": _extrair_campo(relatorio_completo, "CASOS REAIS"),
            "caso_falhanço": _extrair_campo(relatorio_completo, "CASO DE FALHANÇO"),
            "competidores": _extrair_campo(relatorio_completo, "COMPETIDORES"),
            "capital": _extrair_campo(relatorio_completo, "CAPITAL INICIAL"),
            "timeline": _extrair_campo(relatorio_completo, "TEMPO ATÉ 1º CLIENTE"),
            "fit_vasco": _extrair_campo(relatorio_completo, "INTERVENÇÃO DO VASCO"),
        },
        "relatorio": relatorio_completo[:2000],
    }
    _DECISION_LOG.parent.mkdir(exist_ok=True)
    with open(_DECISION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def _extrair_campo(texto: str, campo: str) -> str:
    """Extrai o valor de um campo do formato padronizado do Scout."""
    import re
    m = re.search(rf"{re.escape(campo)}:\s*(.+?)(?:\n[A-Z]|\Z)", texto, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip()[:300] if m else ""


def _aplicar_quality_gate(oportunidade_raw: str) -> tuple[str, int]:
    """Aplica o Quality Gate a uma oportunidade descrita em texto.
    Retorna (texto_validado, confianca).
    """
    system = QUALITY_GATE_PROMPT + "\n\nSe os dados forem insuficientes, diz exactamente o que falta e porque não pode ser proposta agora."
    msgs = [{"role": "user", "content": f"Aplica o Quality Gate a esta oportunidade:\n\n{oportunidade_raw}"}]
    resultado = _chamar_claude_scout(system, msgs, max_tokens=1500)

    # Extrair score do texto — aceita "SCORE: 87/100", "87 pts", "87/100 pts", "CONFIANÇA: 87%"
    import re
    m = (
        re.search(r"SCORE:\s*(\d+)\s*/\s*100", resultado, re.IGNORECASE) or
        re.search(r"(\d+)\s*/\s*100\s*pts", resultado, re.IGNORECASE) or
        re.search(r"(\d+)\s*pts?\b", resultado, re.IGNORECASE) or
        re.search(r"CONFIANÇA:\s*(\d+)%", resultado, re.IGNORECASE)
    )
    confianca = int(m.group(1)) if m else 0

    # Decision log — registo completo de cada avaliação
    import re as _re2
    nome_m = _re2.search(r"OPORTUNIDADE:\s*(.+)", resultado, _re2.IGNORECASE)
    nome = nome_m.group(1).strip() if nome_m else oportunidade_raw[:60]
    if confianca >= 85:
        decisao = "APROVADA"
    elif confianca >= 70:
        decisao = "EM_INVESTIGACAO"
    else:
        decisao = "REJEITADA"
    try:
        _registar_decisao_scout(nome, confianca, decisao, resultado)
    except Exception:
        pass

    # Regista decisões relevantes — aprovadas e investigação
    if confianca >= 70:
        try:
            from episodic_memory import registar_evento
            registar_evento(
                "scout", f"oportunidade_{decisao.lower()}",
                f"{nome} — Confiança: {confianca}% | {resultado[:250]}",
                {"confianca": confianca, "decisao": decisao},
            )
        except Exception:
            pass

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

    # Sinais do sweep desta semana — alimenta a análise com dados reais já recolhidos
    sinais_bloco = ""
    try:
        from scout_sweep import _get_top_signals_week
        sinais = _get_top_signals_week(top_n=15)
        if sinais:
            linhas = "\n".join(
                f"  - [{s['fonte']}] {s['titulo']} (velocity {s.get('velocity', '?')}x)"
                for s in sinais
            )
            sinais_bloco = f"\n\n## SINAIS DO SWEEP (últimos 7 dias, por velocity):\n{linhas}\n\nAnalisa estes sinais como ponto de partida — podem indicar oportunidades emergentes."
    except Exception:
        pass

    system = SCOUT_MISSAO_A_PROMPT + "\n\n" + QUALITY_GATE_PROMPT + mem_bloco + sinais_bloco

    msgs = [{"role": "user", "content": (
        "Inicia a Missão A. Pesquisa, identifica candidatos, e para cada um aplica o Quality Gate. "
        "Propõe apenas os que passam com ≥85% confiança. "
        "No final, apresenta o relatório estruturado com máximo 3 oportunidades validadas."
    )}]

    relatorio = _chamar_claude_scout(system, msgs, max_tokens=6000)

    # ── Verificação programática do Quality Gate — filtragem hard ────────────
    import re as _re

    def _extrair_score_bloco(bloco: str) -> int:
        """Extrai o score numérico de um bloco de oportunidade. Retorna 0 se não encontrado."""
        for pat in [
            r"SCORE:\s*(\d+)\s*/\s*100",
            r"(\d+)\s*/\s*100\s*pts",
            r"(\d+)\s*pts\b(?!\s*de\b)",
        ]:
            m = _re.search(pat, bloco, _re.IGNORECASE)
            if m:
                val = int(m.group(1))
                if 0 < val <= 100:
                    return val
        return 0

    # Split do relatório em blocos por oportunidade
    partes = _re.split(r"(?=OPORTUNIDADE:\s*\S)", relatorio, flags=_re.IGNORECASE)
    cabecalho = partes[0]  # texto antes da primeira oportunidade (intro, contexto)
    blocos_opor = partes[1:]

    blocos_aprovados = []
    blocos_removidos = []
    scores_aprovados = []

    for bloco in blocos_opor:
        score = _extrair_score_bloco(bloco)
        if score >= 85:
            blocos_aprovados.append(bloco)
            scores_aprovados.append(score)
        else:
            nome_m = _re.search(r"OPORTUNIDADE:\s*(.+)", bloco, _re.IGNORECASE)
            nome_bloco = nome_m.group(1).strip() if nome_m else "?"
            blocos_removidos.append(f"{nome_bloco} ({score}pts)")

    # Reconstruir relatório só com aprovados
    relatorio = cabecalho + "".join(blocos_aprovados)

    if blocos_removidos:
        relatorio += (
            f"\n\n---\n⚠️ QG (verificação programática): {len(blocos_removidos)} oportunidade(s) "
            f"removida(s) por score abaixo de 85pts: {', '.join(blocos_removidos)}"
        )
    if not blocos_aprovados and blocos_opor:
        relatorio += "\n\n[Scout: nenhuma oportunidade passou o Quality Gate nesta semana — dados insuficientes para proposta.]"

    # Guardar relatório
    hoje = date.today().strftime("%Y-%m-%d")
    report_file = SCOUT_REPORTS_DIR / f"missao_a_{hoje}.txt"
    report_file.write_text(relatorio, encoding="utf-8")

    # Persistir apenas oportunidades aprovadas
    nomes_propostos = _re.findall(r"OPORTUNIDADE:\s*(.+)", "".join(blocos_aprovados))
    for nome in nomes_propostos:
        nome = nome.strip()
        if nome and nome not in state.get("oportunidades_propostas", []):
            state.setdefault("oportunidades_propostas", []).append(nome)

    state["ultima_missao_a"] = hoje
    state["missoes_completadas"] = state.get("missoes_completadas", 0) + 1
    state["ultimo_qg_scores"] = scores_aprovados  # scores das oportunidades que passaram
    _save_state(state)

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "missao_a", relatorio[:400])
    except Exception:
        pass

    return relatorio


def missao_a_oportunidades_triggered(contexto_sinais: str) -> str:
    """
    Versão da Missão A accionada pelo sweep quando detecta sinais muito fortes (velocity ≥3x).
    Recebe o resumo dos sinais para dar contexto ao Scout.
    """
    state = _load_state()
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
        f"O sweep automático detectou sinais de mercado muito fortes:\n\n{contexto_sinais}\n\n"
        "Analisa estes sinais e decide se representam oportunidades reais. "
        "Para cada candidato, aplica o Quality Gate completo. "
        "Propõe apenas os que passam com ≥85% confiança. "
        "Relatório estruturado com máximo 2 oportunidades."
    )}]

    relatorio = _chamar_claude_scout(system, msgs, max_tokens=4000)

    # Hard filter programático — igual à Missão A normal
    import re as _re_trig
    partes = _re_trig.split(r"(?=OPORTUNIDADE:\s*\S)", relatorio, flags=_re_trig.IGNORECASE)
    blocos_aprovados = []
    blocos_removidos = []
    for bloco in partes[1:]:
        for pat in [r"SCORE:\s*(\d+)\s*/\s*100", r"(\d+)\s*/\s*100\s*pts", r"(\d+)\s*pts\b(?!\s*de\b)"]:
            m = _re_trig.search(pat, bloco, _re_trig.IGNORECASE)
            if m:
                val = int(m.group(1))
                if 0 < val <= 100:
                    if val >= 85:
                        blocos_aprovados.append(bloco)
                    else:
                        nome_m = _re_trig.search(r"OPORTUNIDADE:\s*(.+)", bloco, _re_trig.IGNORECASE)
                        blocos_removidos.append(nome_m.group(1).strip() if nome_m else "?")
                    break
    if blocos_aprovados or blocos_removidos:
        relatorio = partes[0] + "".join(blocos_aprovados)
        if blocos_removidos:
            relatorio += f"\n\n[QG: {len(blocos_removidos)} removida(s) por score <85pts: {', '.join(blocos_removidos)}]"

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "missao_a_triggered", relatorio[:400])
    except Exception:
        pass

    # Entregar ao Vasco via push se houver oportunidades aprovadas
    try:
        import re as _re_t
        tem_aprovadas = bool(_re_t.search(r"OPORTUNIDADE:", relatorio, _re_t.IGNORECASE))
        if tem_aprovadas and "dados insuficientes" not in relatorio.lower():
            from push_service import send_push
            send_push(
                title="Scout — Sinal forte detectado",
                body=relatorio[:180],
                url="/pwa/",
            )
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

    # Validação programática: remover sugestões sem utilizador real documentado
    import re as _re_b
    linhas = relatorio.splitlines()
    linhas_validas = []
    for linha in linhas:
        # Linha de sugestão: começa com [Agente] ou é cabeçalho/contexto
        if _re_b.match(r"^\[?\w+\]?\s*[—–-]", linha):
            linha_low = linha.lower()
            # Rejeitar se não há evidência de utilizador real
            tem_utilizador = any(kw in linha_low for kw in [
                "utilizador", "user", "produção", "production", "caso real",
                "empresa", "company", "fundador", "founder", "review", "https://"
            ])
            # Rejeitar se custo > €30 sem ROI explícito
            custo_m = _re_b.search(r"€\s*(\d+)", linha)
            custo_alto = custo_m and int(custo_m.group(1)) > 30 and "roi" not in linha_low
            if not tem_utilizador or custo_alto:
                linhas_validas.append(f"~~{linha}~~ [QG-B: sem utilizador real ou custo não justificado]")
                continue
        linhas_validas.append(linha)
    relatorio = "\n".join(linhas_validas)

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
    mudanças de mercado. Avalia as 3 estratégias activas: Grid (BTC/ETH), DCA e Trailing Stop (SOL).
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
1. Condições actuais de mercado (fase: bull/flat/bear, volatilidade, dominância BTC)
2. Performance de Grid Bot em BTC/ETH nas condições actuais
3. Performance de DCA em mercado actual
4. Trailing Stop — parâmetros óptimos actuais para BTC/ETH/SOL
5. Recomendação de estratégia para cada par (BTC, ETH, SOL) com base na fase actual
6. Proposta concreta para o CFO avaliar"""

    msgs = [{"role": "user", "content": (
        "Analisa as estratégias de trading activas do Morgan: Grid Bot (BTC/USDT e ETH/USDT), "
        "DCA (SOL/USDT), e avalia quando usar Trailing Stop. Capital $100 por bot (a escalar para $1000). "
        "Binance spot, sem alavancagem. Pesquisa resultados recentes e condições actuais de mercado."
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


def missao_b_solver_ideal() -> str:
    """
    Missão B especial — pesquisa focada no Solver ideal.
    Investiga padrões SRE, AIOps e chaos engineering do mundo real
    para informar a construção do Solver proactivo do Morgan.
    """
    system = """És o Morgan Scout. Tens uma missão de investigação técnica urgente.

OBJECTIVO:
Pesquisar como os melhores sistemas de IA e SRE do mundo detectam erros silenciosos proactivamente.
O Morgan tem um Solver que só age quando há erro reportado. Queremos torná-lo proactivo.

PERGUNTAS A RESPONDER (com fontes reais):
1. Como os melhores sistemas SRE/AIOps detectam erros ANTES de serem reportados?
2. Que padrões de "proactive error scanning" existem em produção hoje? (ex: chaos engineering, canary testing, anomaly detection)
3. Que ferramentas/bibliotecas Python fazem scan proactivo de sistemas em produção?
4. O que fazem o Datadog, Sentry, Honeycomb, OpenTelemetry de diferente dos sistemas reactivos?
5. Para um sistema com 8 agentes Python num Mac Mini: qual o padrão mais leve e eficaz de scan proactivo?

CRITÉRIOS:
- Apenas padrões com utilizadores reais documentados
- Implementável em Python 3.12 sem infraestrutura adicional pesada
- Custo: €0 preferível, máx €20/mês
- Foco em detecção de erros silenciosos (não crashes óbvios — esses já temos)

FORMATO DA RESPOSTA:
## Padrões encontrados (máx 5, por ordem de relevância)
[Nome] | [Como funciona] | [Implementação Python] | [Custo] | [Fonte]

## Recomendação para o Solver Morgan
[O que adoptar, em que ordem, com que esforço de implementação]

## Riscos e trade-offs
[O que perdemos vs. ganharíamos com cada abordagem]

Pesquisa em inglês (mercado global). Resposta final em PT-PT."""

    msgs = [{"role": "user", "content": (
        "Investiga padrões de Solver/SRE proactivo para sistemas multi-agente Python. "
        "Usa pesquisar_web e hacker_news_trending. Foca em implementações reais, não teoria."
    )}]

    relatorio = _chamar_claude_scout(system, msgs, max_tokens=2500)

    hoje = date.today().strftime("%Y-%m-%d")
    report_file = SCOUT_REPORTS_DIR / f"missao_b_solver_ideal_{hoje}.txt"
    report_file.write_text(relatorio, encoding="utf-8")

    try:
        from episodic_memory import registar_evento
        registar_evento("scout", "missao_b_solver", relatorio[:400])
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
        "REGRA DE PESQUISA: para qualquer análise de oportunidade, usa SEMPRE as ferramentas\n"
        "scout_pesquisa_multilang nos 3 modos (anglofonico, iberico_latam, dach) antes de concluir.\n"
        "Nunca baseies uma recomendação apenas em mercado PT — é pequeno demais.\n\n"
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
