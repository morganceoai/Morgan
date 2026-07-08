"""
Morgan CFO — Agente financeiro do império BC Industries.
Supervisiona: trading bot, PnL, drawdown, relatórios financeiros, alertas de risco.
Reporta ao Morgan CEO. A última decisão é sempre do Vasco.
"""
import os
import json
from pathlib import Path
from datetime import datetime, date
import anthropic

MEMORY_DIR = Path(__file__).parent / "memory"
TRADING_STATE_FILE = MEMORY_DIR / "trading_state.json"
CFO_REPORT_FILE = MEMORY_DIR / "cfo_reports.json"

DRAWDOWN_DAY_LIMITE = 0.05    # 5% num dia — alerta imediato
DRAWDOWN_TOTAL_LIMITE = 0.15  # 15% total — parar bot
CAPITAL_BASE = 100.0          # USDT de referência


# ── Estado do trading bot ────────────────────────────────────────────────────

def _load_trading_state() -> dict:
    try:
        return json.loads(TRADING_STATE_FILE.read_text())
    except Exception:
        return {
            "active": True,
            "position": None,
            "trades": [],
            "pnl_total": 0.0,
            "pnl_today": 0.0,
            "last_check": "",
            "last_signal": "",
        }


# ── Relatórios CFO ───────────────────────────────────────────────────────────

def _load_reports() -> list:
    try:
        return json.loads(CFO_REPORT_FILE.read_text())
    except Exception:
        return []

def _save_report(report: dict):
    reports = _load_reports()
    reports.append(report)
    reports = reports[-90:]  # 90 dias de histórico
    CFO_REPORT_FILE.write_text(json.dumps(reports, ensure_ascii=False, indent=2))


# ── Análise de risco ─────────────────────────────────────────────────────────

def avaliar_risco_trading() -> dict:
    """Avalia o estado de risco do trading bot em tempo real."""
    state = _load_trading_state()
    trades = state.get("trades", [])
    pnl_total = state.get("pnl_total", 0.0)
    pnl_hoje = state.get("pnl_today", 0.0)
    position = state.get("position")
    active = state.get("active", True)

    # Calcular métricas
    drawdown_total_pct = abs(pnl_total) / CAPITAL_BASE if pnl_total < 0 else 0
    drawdown_dia_pct = abs(pnl_hoje) / CAPITAL_BASE if pnl_hoje < 0 else 0

    # Trades do mês
    mes_atual = date.today().strftime("%Y-%m")
    trades_mes = [t for t in trades if t.get("closed_at", "")[:7] == mes_atual]
    ganhos = [t for t in trades_mes if t.get("pnl", 0) > 0]
    perdas = [t for t in trades_mes if t.get("pnl", 0) < 0]
    win_rate = len(ganhos) / len(trades_mes) * 100 if trades_mes else 0

    # Alertas
    alertas = []
    nivel_risco = "verde"

    if drawdown_dia_pct >= DRAWDOWN_DAY_LIMITE:
        alertas.append(f"DRAWDOWN DIA: -{drawdown_dia_pct*100:.1f}% — limite atingido ({DRAWDOWN_DAY_LIMITE*100:.0f}%)")
        nivel_risco = "vermelho"

    if drawdown_total_pct >= DRAWDOWN_TOTAL_LIMITE:
        alertas.append(f"DRAWDOWN TOTAL: -{drawdown_total_pct*100:.1f}% — bot deve parar ({DRAWDOWN_TOTAL_LIMITE*100:.0f}%)")
        nivel_risco = "vermelho"
    elif drawdown_total_pct >= DRAWDOWN_TOTAL_LIMITE * 0.7:
        alertas.append(f"DRAWDOWN TOTAL: -{drawdown_total_pct*100:.1f}% — atenção (70% do limite)")
        nivel_risco = "amarelo"

    if not active:
        alertas.append("Bot parado — requer verificação")
        nivel_risco = "amarelo"

    return {
        "active": active,
        "pnl_total": pnl_total,
        "pnl_hoje": pnl_hoje,
        "capital_atual": CAPITAL_BASE + pnl_total,
        "drawdown_total_pct": round(drawdown_total_pct * 100, 2),
        "drawdown_dia_pct": round(drawdown_dia_pct * 100, 2),
        "position_aberta": position is not None,
        "position": position,
        "trades_mes": len(trades_mes),
        "win_rate": round(win_rate, 1),
        "ganhos_mes": len(ganhos),
        "perdas_mes": len(perdas),
        "pnl_mes": sum(t.get("pnl", 0) for t in trades_mes),
        "nivel_risco": nivel_risco,
        "alertas": alertas,
        "ultimo_sinal": state.get("last_signal", ""),
        "ultima_verificacao": state.get("last_check", ""),
    }


# ── Relatório financeiro ─────────────────────────────────────────────────────

def relatorio_financeiro_diario() -> str:
    """Relatório diário do CFO para o CEO."""
    r = avaliar_risco_trading()
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

    linhas = [
        f"MORGAN CFO — Relatório {hoje}",
        "",
        "TRADING BOT (BTC/USDT 30m · EMA 9/21)",
        f"  Estado: {'ATIVO' if r['active'] else 'PARADO'}",
        f"  Capital: ${r['capital_atual']:.2f} USDT (base: ${CAPITAL_BASE:.0f})",
        f"  PnL total: {'+'if r['pnl_total']>=0 else ''}{r['pnl_total']:.2f} USDT",
        f"  PnL hoje: {'+'if r['pnl_hoje']>=0 else ''}{r['pnl_hoje']:.2f} USDT",
        f"  Drawdown total: {r['drawdown_total_pct']:.1f}%",
        "",
        "ESTE MÊS",
        f"  Trades: {r['trades_mes']} ({r['ganhos_mes']} ganhos / {r['perdas_mes']} perdas)",
        f"  Win rate: {r['win_rate']:.0f}%",
        f"  PnL mês: {'+'if r['pnl_mes']>=0 else ''}{r['pnl_mes']:.2f} USDT",
    ]

    if r["position_aberta"] and r["position"]:
        p = r["position"]
        linhas.append("")
        linhas.append("POSIÇÃO ABERTA")
        linhas.append(f"  {p.get('side','?').upper()} @ ${p.get('entry',0):.2f} · Size: {p.get('size',0):.6f} BTC")

    linhas.append("")
    if r["alertas"]:
        linhas.append(f"RISCO: {r['nivel_risco'].upper()}")
        for a in r["alertas"]:
            linhas.append(f"  ⚠ {a}")
    else:
        linhas.append(f"RISCO: VERDE — sem alertas")

    report_txt = "\n".join(linhas)

    # Guardar histórico
    _save_report({
        "data": hoje,
        "pnl_total": r["pnl_total"],
        "pnl_hoje": r["pnl_hoje"],
        "capital": r["capital_atual"],
        "win_rate": r["win_rate"],
        "nivel_risco": r["nivel_risco"],
        "alertas": r["alertas"],
    })

    return report_txt


def resumo_mensal() -> str:
    """Resumo mensal de performance."""
    reports = _load_reports()
    mes_atual = date.today().strftime("%Y-%m")
    reports_mes = [r for r in reports if r.get("data", "")[:7] == mes_atual]

    if not reports_mes:
        return "CFO: sem dados suficientes para resumo mensal."

    pnl_inicial = reports_mes[0].get("pnl_total", 0) if len(reports_mes) > 1 else 0
    pnl_final = reports_mes[-1].get("pnl_total", 0)
    pnl_mes = pnl_final - pnl_inicial
    win_rates = [r["win_rate"] for r in reports_mes if r.get("win_rate", 0) > 0]
    win_medio = sum(win_rates) / len(win_rates) if win_rates else 0
    dias_vermelho = sum(1 for r in reports_mes if r.get("nivel_risco") == "vermelho")

    return (
        f"CFO — Resumo {mes_atual}\n"
        f"PnL do mês: {'+'if pnl_mes>=0 else ''}{pnl_mes:.2f} USDT\n"
        f"Win rate médio: {win_medio:.0f}%\n"
        f"Dias em alerta vermelho: {dias_vermelho}\n"
        f"Capital final: ${CAPITAL_BASE + pnl_final:.2f} USDT"
    )


def verificar_alertas_criticos() -> list:
    """Verifica se há alertas que requerem ação imediata do CEO/Vasco."""
    r = avaliar_risco_trading()
    criticos = []
    for a in r["alertas"]:
        if "DRAWDOWN" in a or "parar" in a.lower():
            criticos.append(a)
    return criticos


# ── Conversa com o CFO ───────────────────────────────────────────────────────

_cfo_history: list = []

def _build_cfo_system() -> str:
    r = avaliar_risco_trading()
    hoje = datetime.now().strftime("%d de %B de %Y")
    return f"""És o Morgan CFO, o director financeiro do império BC Industries.
A data de hoje é {hoje}.
Tom: preciso, direto, números em primeiro lugar. Sempre em português europeu. Sem emojis.
Reportas ao Morgan CEO. O Vasco pode falar diretamente contigo.
Para voltar ao Morgan CEO, o Vasco diz "volta ao Morgan".

## Estado atual do Trading Bot:
Capital: ${r['capital_atual']:.2f} USDT | PnL total: {r['pnl_total']:+.2f} USDT
PnL hoje: {r['pnl_hoje']:+.2f} USDT | Drawdown: {r['drawdown_total_pct']:.1f}%
Win rate (mês): {r['win_rate']:.0f}% | Trades mês: {r['trades_mes']}
Estado: {'ATIVO' if r['active'] else 'PARADO'} | Risco: {r['nivel_risco'].upper()}
{('Alertas: ' + ' | '.join(r['alertas'])) if r['alertas'] else 'Sem alertas.'}

## As tuas responsabilidades:
1. Supervisionar o trading bot BTC/USDT (EMA 9/21, 30m) — capital de $100 USDT
2. Monitorizar PnL diário e total, drawdown, win rate
3. Alertar o CEO quando drawdown >5% dia ou >15% total
4. Produzir relatórios financeiros diários e mensais
5. Quando o império crescer: supervisionar receitas dos sub-Morgans, balanços, impostos
6. Avaliar viabilidade financeira de novos negócios antes de aprovação

## Regras de risco:
- Drawdown dia >5%: alerta imediato ao Vasco
- Drawdown total >15%: recomendar paragem do bot
- Win rate <40% por 2 semanas consecutivas: revisão de estratégia
- Nunca executar trades — apenas supervisionar e reportar"""


def get_cfo_reply(user_message: str) -> str:
    """Ponto de entrada para conversa com o CFO."""
    global _cfo_history

    system = _build_cfo_system()
    _cfo_history.append({"role": "user", "content": user_message})

    if len(_cfo_history) > 20:
        _cfo_history = _cfo_history[-20:]

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=_cfo_history,
    )

    reply = response.content[0].text
    _cfo_history.append({"role": "assistant", "content": reply})
    return reply


if __name__ == "__main__":
    print(relatorio_financeiro_diario())
