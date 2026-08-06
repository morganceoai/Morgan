"""
CFO Reporting — Briefings e relatórios de elite para o CFO BCVertex.

Módulos:
  - briefing_matinal()   → briefing 7h: fase + portfolio + acção do dia
  - relatorio_22h()      → relatório completo com curva ASCII 30 dias
  - scorecard_mensal()   → performance por Motor vs benchmark
"""
import json
from datetime import datetime, date, timedelta
from pathlib import Path

_BASE = Path(__file__).parent
_REPORT_HISTORY_FILE = _BASE / "memory" / "cfo_reports.json"


# ── Curva ASCII ───────────────────────────────────────────────────────────────

def _curva_ascii(valores: list[float], largura: int = 40, altura: int = 6) -> str:
    """
    Gera curva de capital em ASCII art.
    valores: lista de floats (capital diário)
    """
    if not valores or len(valores) < 2:
        return "  (dados insuficientes para curva)"

    vmin = min(valores)
    vmax = max(valores)
    rng = vmax - vmin or 1

    # Normalizar para altura
    normalizado = [int((v - vmin) / rng * (altura - 1)) for v in valores]

    # Amostrar para largura
    if len(normalizado) > largura:
        step = len(normalizado) / largura
        normalizado = [normalizado[int(i * step)] for i in range(largura)]

    linhas = []
    for row in range(altura - 1, -1, -1):
        linha = ""
        for val in normalizado:
            if val >= row:
                linha += "█"
            else:
                linha += " "
        # Label do eixo Y
        if row == altura - 1:
            linha += f" €{vmax:,.0f}"
        elif row == 0:
            linha += f" €{vmin:,.0f}"
        linhas.append("  " + linha)

    # Eixo X
    n = len(normalizado)
    linhas.append("  " + "─" * n)
    linhas.append(f"  -{min(len(valores), 30)}d" + " " * (n - 8) + "hoje")

    return "\n".join(linhas)


# ── Briefing matinal (7h) ─────────────────────────────────────────────────────

def briefing_matinal() -> str:
    """
    Briefing matinal das 7h — compacto, accionável.
    Combina: fase de mercado + portfolio + trading + acção recomendada.
    """
    hoje = date.today().strftime("%d/%m/%Y")
    linhas = [f"MORGAN CFO — {hoje}", ""]

    # Fase de mercado
    try:
        from cfo_market_phase import resumo_para_briefing
        linhas.append("── MERCADO ──")
        linhas.append(resumo_para_briefing())
        linhas.append("")
    except Exception as e:
        linhas.append(f"Mercado: indisponível ({e})")
        linhas.append("")

    # Portfolio
    try:
        from cfo_portfolio import resumo_para_briefing as portfolio_briefing
        linhas.append("── PORTFOLIO ──")
        linhas.append(portfolio_briefing())
        linhas.append("")
    except Exception as e:
        linhas.append(f"Portfolio: indisponível ({e})")
        linhas.append("")

    # Trading bot
    try:
        from cfo_agent import avaliar_risco_trading
        r = avaliar_risco_trading()
        linhas.append("── TRADING ──")
        linhas.append(f"Bot: {'ATIVO' if r['active'] else 'PARADO'} | PnL hoje: {r['pnl_hoje']:+.2f} USDT | Risco: {r['nivel_risco'].upper()}")
        if r["alertas"]:
            for a in r["alertas"]:
                linhas.append(f"  ⚠ {a}")
        linhas.append("")
    except Exception as e:
        linhas.append(f"Trading: indisponível ({e})")
        linhas.append("")

    # Negócios
    try:
        from patlas_agent import get_resumo_financeiro
        patlas = get_resumo_financeiro()
        linhas.append("── NEGÓCIOS ──")
        linhas.append(f"PAtlas: {patlas}")
    except Exception:
        pass

    try:
        from pulser_agent import get_resumo_financeiro
        pulser = get_resumo_financeiro()
        linhas.append(f"Pulser: {pulser}")
    except Exception:
        pass

    linhas.append("")

    # Acção do dia
    linhas.append("── ACÇÃO RECOMENDADA ──")
    try:
        from cfo_market_phase import snapshot_fase
        fase = snapshot_fase()
        estrategia = fase.get("estrategia_recomendada", "observar")
        razao = fase.get("estrategia_razao", "")
        alertas_fase = fase.get("alertas", [])

        linhas.append(f"Estratégia: {estrategia.upper()}")
        linhas.append(f"Razão: {razao}")
        for a in alertas_fase:
            linhas.append(f"⚠ {a}")
    except Exception:
        linhas.append("Manter posição actual.")

    return "\n".join(linhas)


# ── Relatório 22h ─────────────────────────────────────────────────────────────

def relatorio_22h() -> str:
    """
    Relatório completo de fim de dia com curva ASCII de capital.
    """
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [f"MORGAN CFO — Relatório 22h  {agora}", "=" * 55, ""]

    # Curva de capital (últimos 30 dias)
    try:
        reports = json.loads(_REPORT_HISTORY_FILE.read_text())
        # Últimos 30 registos com capital
        capitais = [r.get("capital", 0) for r in reports[-30:] if r.get("capital")]
        if len(capitais) >= 5:
            linhas.append("── CURVA DE CAPITAL (30 dias) ──")
            linhas.append(_curva_ascii(capitais))
            linhas.append("")
    except Exception:
        pass

    # Trading completo
    try:
        from cfo_agent import avaliar_risco_trading, resumo_mensal
        r = avaliar_risco_trading()
        linhas += [
            "── TRADING BOT ──",
            f"Capital: ${r['capital_atual']:.2f} USDT | PnL total: {r['pnl_total']:+.2f} | PnL hoje: {r['pnl_hoje']:+.2f}",
            f"Trades mês: {r['trades_mes']} | Win rate: {r['win_rate']:.0f}% | Profit factor: {r['profit_factor'] or 'N/A'}",
            f"Drawdown total: {r['drawdown_total_pct']:.1f}% | Streak perdas: {r['streak_perdas']}",
            f"Risco: {r['nivel_risco'].upper()}",
        ]
        if r["alertas"]:
            for a in r["alertas"]:
                linhas.append(f"  ⚠ {a}")
        linhas.append("")
    except Exception as e:
        linhas.append(f"Trading: erro ({e})\n")

    # Portfolio
    try:
        from cfo_portfolio import resumo_portfolio
        p = resumo_portfolio()
        linhas += [
            "── PORTFOLIO ──",
            f"Capital total: €{p['capital_total_eur']:,.0f}",
        ]
        for mid, pct in p.get("alocacao_pct", {}).items():
            cap = p["motores"][mid]["capital_eur"]
            linhas.append(f"  {mid}: €{cap:,.0f} ({pct}%)")
        if p.get("milestones_novos"):
            for m in p["milestones_novos"]:
                linhas.append(f"🎯 MILESTONE €{m['milestone_eur']:,} ATINGIDO!")
        if p.get("proximo_milestone"):
            pm = p["proximo_milestone"]
            linhas.append(f"Próximo milestone: €{pm['milestone_eur']:,} — faltam €{pm['falta_eur']:,.0f}")
        linhas.append("")
    except Exception as e:
        linhas.append(f"Portfolio: erro ({e})\n")

    # Fase de mercado
    try:
        from cfo_market_phase import snapshot_fase
        fase = snapshot_fase()
        est = fase["fase_estrutural"]
        linhas += [
            "── MERCADO ──",
            f"Fase: {est.get('fase','?').upper()} | RSI={est.get('rsi14','?')} | SMA200 ${est.get('sma200','?')} ({est.get('distancia_sma200_pct',0):+.1f}%)",
            f"Funding rate: {fase['funding_rate'].get('rate_pct','?')}% | Dom BTC: {fase['dominancia_btc'].get('dominancia_pct','?')}%",
            f"Estratégia: {fase['estrategia_recomendada'].upper()}",
        ]
        for a in fase.get("alertas", []):
            linhas.append(f"  ⚠ {a}")
        linhas.append("")
    except Exception:
        pass

    # ETF alertas
    try:
        from cfo_etf import run_verificacoes_etf
        etf_alertas = run_verificacoes_etf()
        if etf_alertas:
            linhas.append("── ETF ALERTAS ──")
            for a in etf_alertas:
                linhas.append(f"  ⚠ {a}")
            linhas.append("")
    except Exception:
        pass

    # Negócios
    try:
        from patlas_agent import get_resumo_financeiro as patlas_res
        linhas.append("── NEGÓCIOS ──")
        linhas.append(f"PAtlas: {patlas_res()}")
    except Exception:
        pass
    try:
        from pulser_agent import get_resumo_financeiro as pulser_res
        linhas.append(f"Pulser: {pulser_res()}")
    except Exception:
        pass

    return "\n".join(linhas)


# ── Scorecard mensal ──────────────────────────────────────────────────────────

def scorecard_mensal() -> str:
    """
    Scorecard de performance mensal por Motor vs benchmark.
    Corre no dia 1 de cada mês (ou sob pedido).
    """
    hoje = date.today()
    mes_anterior = (hoje.replace(day=1) - timedelta(days=1))
    mes_label = mes_anterior.strftime("%B %Y")

    linhas = [
        f"CFO — Scorecard Mensal: {mes_label}",
        "=" * 50,
        "",
    ]

    try:
        from cfo_portfolio import get_state, MOTORES_REF
        from cfo_etf import ETF_UNIVERSE, _get_etf_data
        import yfinance as yf

        state = get_state()

        # Performance por Motor
        linhas.append("PERFORMANCE POR MOTOR")
        linhas.append(f"{'Motor':<6} {'Capital':>10} {'ETF':>8} {'1m%':>7} {'Bench':>8} {'1m%':>7} {'Alpha':>7}")
        linhas.append("─" * 58)

        for motor_id, motor in state["motores"].items():
            if motor["capital_eur"] == 0:
                continue

            cap = motor["capital_eur"]
            etfs = motor.get("etfs", [])

            if not etfs:
                linhas.append(f"{motor_id:<6} €{cap:>9,.0f}   (sem ETF alocado)")
                continue

            for etf_ticker in etfs[:1]:  # ETF principal do motor
                cfg = ETF_UNIVERSE.get(etf_ticker, {})
                dados = _get_etf_data(etf_ticker)
                ret_etf = dados.get("retorno_1m_pct", "N/A")

                # Benchmark
                bench_ticker = cfg.get("benchmark_ticker")
                ret_bench = "N/A"
                alpha = "N/A"
                if bench_ticker:
                    try:
                        hist = yf.Ticker(bench_ticker).history(period="1mo")["Close"]
                        if not hist.empty:
                            ret_bench = round((hist.iloc[-1] / hist.iloc[0] - 1) * 100, 1)
                            if isinstance(ret_etf, float) and isinstance(ret_bench, float):
                                alpha = round(ret_etf - ret_bench, 1)
                    except Exception:
                        pass

                ret_etf_str = f"{ret_etf:+.1f}%" if isinstance(ret_etf, float) else str(ret_etf)
                ret_bench_str = f"{ret_bench:+.1f}%" if isinstance(ret_bench, float) else str(ret_bench)
                alpha_str = f"{alpha:+.1f}%" if isinstance(alpha, float) else str(alpha)

                linhas.append(
                    f"{motor_id:<6} €{cap:>9,.0f} {etf_ticker:>8} {ret_etf_str:>7} {bench_ticker or 'N/A':>8} {ret_bench_str:>7} {alpha_str:>7}"
                )

    except Exception as e:
        linhas.append(f"Dados de benchmark indisponíveis: {e}")
        linhas.append("Performance manual: verificar broker.")

    # Trading bot do mês
    try:
        from cfo_agent import resumo_mensal
        linhas += ["", "TRADING BOT", resumo_mensal()]
    except Exception:
        pass

    linhas += [
        "",
        f"Próximo scorecard: 1 de {(hoje.replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%B %Y')}",
    ]

    return "\n".join(linhas)
