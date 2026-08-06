"""
CFO Portfolio — Estado unificado do portfolio BCVertex (Motores M1-M5).

Responsabilidades:
  - Persistir capital alocado por Motor em portfolio_state.json
  - Detectar milestones atingidos (€10k, €25k, €50k, €100k, €250k, €1M)
  - Projecções compound em 3 cenários (bull/base/bear)
  - Análise fiscal PT: vantagem de exclusão aos 8 anos
  - Benchmark por Motor vs índice de referência

O CFO lê deste módulo — não edita directamente os motores.
O Vasco actualiza capital manualmente via API ou conversa com o CFO.
"""
import json
from datetime import datetime, date
from pathlib import Path

_BASE = Path(__file__).parent
_STATE_FILE = _BASE / "memory" / "portfolio_state.json"

# Milestones de capital total (€)
MILESTONES = [10_000, 25_000, 50_000, 100_000, 250_000, 1_000_000]

# Rendimentos anuais esperados por cenário
CENARIOS = {
    "bull":  {"rendimento_anual": 0.25, "label": "Bull (+25%/ano)"},
    "base":  {"rendimento_anual": 0.12, "label": "Base (+12%/ano)"},
    "bear":  {"rendimento_anual": 0.04, "label": "Bear (+4%/ano)"},
}

# Alocação por Motor (referência documental — não executa ordens)
MOTORES_REF = {
    "M1": {"nome": "Cripto — Grid Bot",        "benchmark": "BTC/USDT hold"},
    "M2": {"nome": "Dividendos",               "benchmark": "XDIV"},
    "M3": {"nome": "REITs",                    "benchmark": "IPRP.L"},
    "M4": {"nome": "ETFs Acumulação",          "benchmark": "CSPX"},
    "M5": {"nome": "Crescimento + Ouro + Água","benchmark": "QQQ"},
}

# Exclusão fiscal PT: +8 anos → ~19.6% efectivo vs 28% imediato
TAXA_NORMAL_PT = 0.28
TAXA_EXCLUSAO_PT = 0.196  # com exclusão de 30% após 8 anos


# ── Estado ───────────────────────────────────────────────────────────────────

def _load() -> dict:
    try:
        return json.loads(_STATE_FILE.read_text())
    except Exception:
        return _estado_inicial()


def _save(state: dict):
    _STATE_FILE.parent.mkdir(exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _estado_inicial() -> dict:
    return {
        "ts_criado": datetime.now().isoformat(),
        "ts_actualizado": datetime.now().isoformat(),
        "capital_total_eur": 0.0,
        "motores": {
            "M1": {"capital_eur": 100.0,  "data_inicio": "2026-07-01", "etfs": [], "notas": "Grid Bot BTC/USDT Binance"},
            "M2": {"capital_eur": 0.0,    "data_inicio": None,         "etfs": [], "notas": "Aguarda abertura conta broker"},
            "M3": {"capital_eur": 0.0,    "data_inicio": None,         "etfs": [], "notas": "Aguarda abertura conta broker"},
            "M4": {"capital_eur": 0.0,    "data_inicio": None,         "etfs": ["CSPX"], "notas": "Trade Republic — compra automática quando conta aberta"},
            "M5": {"capital_eur": 0.0,    "data_inicio": None,         "etfs": ["QQQ", "IAU", "PHO"], "notas": "Fase 2 — activar em Milestone 1 (€10k)"},
        },
        "milestones_atingidos": [],
        "ultimo_milestone_alerta": None,
        "deposito_mensal_eur": 0.0,
    }


def get_state() -> dict:
    return _load()


def actualizar_motor(motor_id: str, capital_eur: float, notas: str = "") -> dict:
    """Actualiza capital de um Motor. Chamado manualmente pelo Vasco via CFO."""
    state = _load()
    if motor_id not in state["motores"]:
        return {"erro": f"Motor {motor_id} não existe"}

    state["motores"][motor_id]["capital_eur"] = round(capital_eur, 2)
    if notas:
        state["motores"][motor_id]["notas"] = notas
    if not state["motores"][motor_id].get("data_inicio") and capital_eur > 0:
        state["motores"][motor_id]["data_inicio"] = date.today().isoformat()

    state["capital_total_eur"] = round(sum(m["capital_eur"] for m in state["motores"].values()), 2)
    state["ts_actualizado"] = datetime.now().isoformat()
    _save(state)
    return {"ok": True, "capital_total": state["capital_total_eur"]}


def definir_deposito_mensal(valor_eur: float) -> dict:
    """Define o depósito mensal total (distribuído pelos Motores activos)."""
    state = _load()
    state["deposito_mensal_eur"] = round(valor_eur, 2)
    state["ts_actualizado"] = datetime.now().isoformat()
    _save(state)
    return {"ok": True, "deposito_mensal": valor_eur}


# ── Milestones ────────────────────────────────────────────────────────────────

def verificar_milestones() -> list[dict]:
    """
    Verifica se algum milestone foi atingido desde o último check.
    Retorna lista de milestones novos (para o CFO alertar o Vasco).
    """
    state = _load()
    capital = state["capital_total_eur"]
    ja_atingidos = set(state.get("milestones_atingidos", []))
    novos = []

    for m in MILESTONES:
        if capital >= m and m not in ja_atingidos:
            novos.append({
                "milestone_eur": m,
                "capital_actual": capital,
                "acoes": _acoes_milestone(m),
            })
            ja_atingidos.add(m)

    if novos:
        state["milestones_atingidos"] = sorted(ja_atingidos)
        state["ultimo_milestone_alerta"] = datetime.now().isoformat()
        _save(state)

    return novos


def _acoes_milestone(milestone: int) -> list[str]:
    acoes = {
        10_000:  ["Activar Motor 5 (crescimento + ouro + água)", "Abrir conta IBKR se não aberta", "Aumentar DCA mensal"],
        25_000:  ["Activar rebalanceamento trimestral", "Considerar SOL/USDT grid bot", "Rever alocação M1 vs M4"],
        50_000:  ["Avaliar estrutura empresarial UAE Free Zone", "Contratar contabilista para Anexo J", "Rebalancear para 60/40 (crescimento/defensivo)"],
        100_000: ["Avaliar JP Morgan Private Bank", "Diversificar para mercados emergentes", "Rever cobertura de risco (ouro 10%)"],
        250_000: ["Activar gestão profissional de parte do portfolio", "Estrutura empresarial obrigatória se rendimentos >€50k/ano"],
        1_000_000: ["Rever toda a estratégia com advisor independente", "Avaliar family office"],
    }
    return acoes.get(milestone, ["Rever estratégia de alocação"])


def proximo_milestone(capital: float) -> dict | None:
    """Retorna o próximo milestone e distância."""
    for m in MILESTONES:
        if capital < m:
            return {
                "milestone_eur": m,
                "falta_eur": round(m - capital, 2),
                "percentagem_completa": round(capital / m * 100, 1),
            }
    return None


# ── Projecções compound ───────────────────────────────────────────────────────

def projectar_compound(anos: int = 10) -> dict:
    """
    Projecções compound em 3 cenários para o capital actual + depósito mensal.
    Assume reinvestimento total (acumulação perpétua).
    """
    state = _load()
    capital_inicial = state["capital_total_eur"]
    deposito_mensal = state["deposito_mensal_eur"]

    resultados = {}
    for cenario, cfg in CENARIOS.items():
        r_mensal = (1 + cfg["rendimento_anual"]) ** (1/12) - 1
        valor = capital_inicial
        for _ in range(anos * 12):
            valor = valor * (1 + r_mensal) + deposito_mensal
        resultados[cenario] = {
            "label": cfg["label"],
            "valor_final_eur": round(valor, 0),
            "ganho_total_eur": round(valor - capital_inicial - deposito_mensal * anos * 12, 0),
            "multiplicador": round(valor / capital_inicial, 1) if capital_inicial > 0 else None,
        }

    return {
        "capital_inicial": capital_inicial,
        "deposito_mensal": deposito_mensal,
        "anos": anos,
        "cenarios": resultados,
    }


# ── Análise fiscal PT ─────────────────────────────────────────────────────────

def analise_fiscal_motores() -> list[dict]:
    """
    Para cada Motor com data_inicio, calcula:
    - Anos desde início
    - Se já elegível para exclusão (8 anos)
    - Poupança fiscal estimada se vender agora vs esperar
    """
    state = _load()
    hoje = date.today()
    resultado = []

    for motor_id, m in state["motores"].items():
        if not m.get("data_inicio") or m["capital_eur"] == 0:
            continue

        data_inicio = date.fromisoformat(m["data_inicio"])
        anos = (hoje - data_inicio).days / 365.25
        anos_para_exclusao = max(0, 8 - anos)
        elegivel = anos >= 8

        # Ganho estimado (simplificado: assume 50% de mais-valias no capital)
        capital = m["capital_eur"]
        mais_valias_estimadas = capital * 0.5  # conservador

        imposto_agora = mais_valias_estimadas * TAXA_NORMAL_PT
        imposto_exclusao = mais_valias_estimadas * TAXA_EXCLUSAO_PT
        poupanca = imposto_agora - imposto_exclusao

        resultado.append({
            "motor": motor_id,
            "nome": MOTORES_REF.get(motor_id, {}).get("nome", motor_id),
            "capital_eur": capital,
            "data_inicio": m["data_inicio"],
            "anos": round(anos, 1),
            "elegivel_exclusao": elegivel,
            "anos_para_exclusao": round(anos_para_exclusao, 1),
            "poupanca_fiscal_estimada": round(poupanca, 0),
            "recomendacao": "Não vender — aguardar exclusão" if not elegivel and anos_para_exclusao < 5 else (
                "Elegível para exclusão — vantagem fiscal activa" if elegivel else "Considerar horizonte de 8 anos"
            ),
        })

    return resultado


# ── Resumo para CFO ───────────────────────────────────────────────────────────

def resumo_portfolio() -> dict:
    """Resumo completo para o ciclo de decisão do CFO."""
    state = _load()
    milestones_novos = verificar_milestones()
    proximo = proximo_milestone(state["capital_total_eur"])
    proj = projectar_compound(10)
    fiscal = analise_fiscal_motores()

    motores_activos = {k: v for k, v in state["motores"].items() if v["capital_eur"] > 0}
    alocacao = {
        k: round(v["capital_eur"] / state["capital_total_eur"] * 100, 1)
        for k, v in motores_activos.items()
    } if state["capital_total_eur"] > 0 else {}

    return {
        "capital_total_eur": state["capital_total_eur"],
        "deposito_mensal_eur": state["deposito_mensal_eur"],
        "motores": state["motores"],
        "alocacao_pct": alocacao,
        "milestones_novos": milestones_novos,
        "proximo_milestone": proximo,
        "projecoes_10anos": proj["cenarios"],
        "analise_fiscal": fiscal,
        "alertas": [f"MILESTONE {m['milestone_eur']:,}€ ATINGIDO!" for m in milestones_novos],
    }


def resumo_para_briefing() -> str:
    """Versão compacta para o briefing matinal das 7h."""
    state = _load()
    capital = state["capital_total_eur"]
    proximo = proximo_milestone(capital)

    linhas = [f"PORTFOLIO: €{capital:,.0f} total"]

    motores_activos = [(k, v) for k, v in state["motores"].items() if v["capital_eur"] > 0]
    for mid, m in motores_activos:
        linhas.append(f"  {mid} ({MOTORES_REF.get(mid,{}).get('nome',mid)}): €{m['capital_eur']:,.0f}")

    if proximo:
        linhas.append(f"Próximo milestone: €{proximo['milestone_eur']:,} — faltam €{proximo['falta_eur']:,.0f} ({proximo['percentagem_completa']:.0f}%)")

    return "\n".join(linhas)
