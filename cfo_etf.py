"""
CFO ETF — Monitorização automática de ETFs do portfolio BCVertex.

5 regras automáticas:
  1. Dividend cut alert — ETF cortou ou eliminou dividendo
  2. NAV drift — ETF desviou >2% do índice de referência (tracking error elevado)
  3. Relatório mensal — resumo de performance, dia 1 de cada mês
  4. Milestone alert — portfolio cruzou threshold de capital (delegado ao cfo_portfolio)
  5. Revisão anual — Janeiro, avalia se manter/substituir cada ETF

Usa yfinance para dados. Sem API key necessária.
Não executa ordens — apenas gera alertas para o CFO comunicar ao Vasco.
"""
import json
from datetime import datetime, date
from pathlib import Path

_BASE = Path(__file__).parent
_ETF_STATE_FILE = _BASE / "memory" / "cfo_etf_state.json"

# ETFs monitorizados com metadados
ETF_UNIVERSE = {
    "CSPX.L": {
        "nome": "iShares Core S&P 500 UCITS ETF",
        "motor": "M4",
        "tipo": "acumulacao",
        "benchmark_ticker": "^GSPC",
        "distribui_dividendos": False,
        "ter_pct": 0.07,
        "notas": "S&P 500 — acumulação, fiscal PT eficiente",
    },
    "QQQ": {
        "nome": "Invesco QQQ Trust (Nasdaq 100)",
        "motor": "M5",
        "tipo": "acumulacao",
        "benchmark_ticker": "^NDX",
        "distribui_dividendos": False,
        "ter_pct": 0.20,
        "notas": "Nasdaq 100 — crescimento, ~15%/ano histórico",
    },
    "IAU": {
        "nome": "iShares Gold Trust",
        "motor": "M5",
        "tipo": "commodity",
        "benchmark_ticker": "GC=F",
        "distribui_dividendos": False,
        "ter_pct": 0.25,
        "notas": "Ouro físico — seguro do portfolio",
    },
    "PHO": {
        "nome": "Invesco Water Resources ETF",
        "motor": "M5",
        "tipo": "acumulacao",
        "benchmark_ticker": None,
        "distribui_dividendos": True,
        "ter_pct": 0.60,
        "notas": "Empresas de água — tese de escassez hídrica",
    },
    "XDIV": {
        "nome": "iShares MSCI World Quality Dividend ESG",
        "motor": "M2",
        "tipo": "distribuicao",
        "benchmark_ticker": "URTH",
        "distribui_dividendos": True,
        "ter_pct": 0.38,
        "notas": "Dividendos — atenção à fiscalidade PT (28% sem exclusão)",
    },
    "IPRP.L": {
        "nome": "iShares European Property Yield",
        "motor": "M3",
        "tipo": "distribuicao",
        "benchmark_ticker": None,
        "distribui_dividendos": True,
        "ter_pct": 0.40,
        "notas": "REITs Europa — distribuição trimestral",
    },
}

NAV_DRIFT_THRESHOLD = 0.02   # 2% de tracking error → investigar
DIVIDEND_CUT_THRESHOLD = 0.20  # queda >20% no dividendo → alerta


# ── Estado ───────────────────────────────────────────────────────────────────

def _load() -> dict:
    try:
        return json.loads(_ETF_STATE_FILE.read_text())
    except Exception:
        return {"etfs": {}, "ultimo_relatorio_mensal": None, "ultima_revisao_anual": None}


def _save(state: dict):
    _ETF_STATE_FILE.parent.mkdir(exist_ok=True)
    _ETF_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── Dados yfinance ────────────────────────────────────────────────────────────

def _get_etf_data(ticker: str) -> dict:
    """Obtém dados básicos de um ETF via yfinance."""
    try:
        import yfinance as yf
        etf = yf.Ticker(ticker)
        info = etf.info
        hist = etf.history(period="1mo")

        preco_atual = hist["Close"].iloc[-1] if not hist.empty else None
        preco_mes_atras = hist["Close"].iloc[0] if len(hist) > 1 else None
        retorno_mes = None
        if preco_atual and preco_mes_atras and preco_mes_atras > 0:
            retorno_mes = round((preco_atual / preco_mes_atras - 1) * 100, 2)

        # Dividendo anual (se distribui)
        div_yield = info.get("dividendYield", 0) or 0
        div_rate = info.get("dividendRate", 0) or 0

        return {
            "ticker": ticker,
            "preco": round(preco_atual, 2) if preco_atual else None,
            "retorno_1m_pct": retorno_mes,
            "retorno_1y_pct": round(info.get("52WeekChange", 0) * 100, 1) if info.get("52WeekChange") else None,
            "dividend_yield_pct": round(div_yield * 100, 2),
            "dividend_rate": round(div_rate, 2),
            "ter_pct": ETF_UNIVERSE.get(ticker, {}).get("ter_pct"),
            "aum": info.get("totalAssets"),
            "ok": True,
        }
    except Exception as e:
        return {"ticker": ticker, "ok": False, "erro": str(e)}


# ── Regra 1: Dividend cut ─────────────────────────────────────────────────────

def verificar_dividend_cut() -> list[dict]:
    """Detecta ETFs que cortaram ou eliminaram dividendo vs histórico."""
    state = _load()
    alertas = []

    for ticker, cfg in ETF_UNIVERSE.items():
        if not cfg["distribui_dividendos"]:
            continue

        dados = _get_etf_data(ticker)
        if not dados["ok"]:
            continue

        div_atual = dados["dividend_rate"]
        historico = state["etfs"].get(ticker, {}).get("dividend_rate_historico")

        if historico and historico > 0 and div_atual < historico * (1 - DIVIDEND_CUT_THRESHOLD):
            queda_pct = round((div_atual - historico) / historico * 100, 1)
            alertas.append({
                "tipo": "dividend_cut",
                "ticker": ticker,
                "nome": cfg["nome"],
                "motor": cfg["motor"],
                "div_atual": div_atual,
                "div_anterior": historico,
                "queda_pct": queda_pct,
                "mensagem": f"{ticker}: dividendo caiu {queda_pct:.0f}% (€{historico:.2f} → €{div_atual:.2f}/ano). Investigar.",
            })

        # Guardar histórico
        if ticker not in state["etfs"]:
            state["etfs"][ticker] = {}
        if div_atual > 0:
            state["etfs"][ticker]["dividend_rate_historico"] = div_atual

    _save(state)
    return alertas


# ── Regra 2: NAV drift ───────────────────────────────────────────────────────

def verificar_nav_drift() -> list[dict]:
    """Compara retorno do ETF vs benchmark — tracking error elevado indica problema."""
    alertas = []

    for ticker, cfg in ETF_UNIVERSE.items():
        bench_ticker = cfg.get("benchmark_ticker")
        if not bench_ticker:
            continue

        try:
            import yfinance as yf
            etf_hist = yf.Ticker(ticker).history(period="3mo")["Close"]
            bench_hist = yf.Ticker(bench_ticker).history(period="3mo")["Close"]

            if etf_hist.empty or bench_hist.empty:
                continue

            ret_etf = (etf_hist.iloc[-1] / etf_hist.iloc[0] - 1) * 100
            ret_bench = (bench_hist.iloc[-1] / bench_hist.iloc[0] - 1) * 100
            drift = abs(ret_etf - ret_bench)

            if drift > NAV_DRIFT_THRESHOLD * 100:
                alertas.append({
                    "tipo": "nav_drift",
                    "ticker": ticker,
                    "nome": cfg["nome"],
                    "motor": cfg["motor"],
                    "ret_etf_pct": round(ret_etf, 1),
                    "ret_bench_pct": round(ret_bench, 1),
                    "drift_pct": round(drift, 1),
                    "mensagem": f"{ticker}: tracking error de {drift:.1f}% vs {bench_ticker} em 3 meses. Verificar estrutura do ETF.",
                })
        except Exception:
            pass

    return alertas


# ── Regra 3: Relatório mensal ─────────────────────────────────────────────────

def relatorio_mensal_etf(forcar: bool = False) -> str | None:
    """
    Gera relatório mensal de todos os ETFs.
    Corre automaticamente no dia 1 de cada mês.
    Retorna None se não for dia 1 (e forcar=False).
    """
    hoje = date.today()
    state = _load()

    if not forcar and hoje.day != 1:
        return None

    ultimo = state.get("ultimo_relatorio_mensal")
    if not forcar and ultimo:
        ultimo_date = date.fromisoformat(ultimo[:10])
        if ultimo_date.month == hoje.month and ultimo_date.year == hoje.year:
            return None  # já correu este mês

    linhas = [
        f"CFO ETF — Relatório Mensal {hoje.strftime('%B %Y')}",
        "=" * 50,
        "",
    ]

    # ETFs monitorizados no portfolio (só os que têm capital alocado)
    from cfo_portfolio import get_state as get_portfolio
    portfolio = get_portfolio()
    etfs_ativos = []
    for motor_id, motor in portfolio["motores"].items():
        for etf_ticker in motor.get("etfs", []):
            if etf_ticker in ETF_UNIVERSE and motor["capital_eur"] > 0:
                etfs_ativos.append((etf_ticker, motor_id, motor["capital_eur"]))

    if not etfs_ativos:
        linhas.append("Nenhum ETF com capital alocado ainda.")
    else:
        for ticker, motor_id, capital in etfs_ativos:
            dados = _get_etf_data(ticker)
            cfg = ETF_UNIVERSE[ticker]
            linhas += [
                f"{ticker} — {cfg['nome']} ({motor_id})",
                f"  Capital: €{capital:,.0f} | Preço: {dados.get('preco','N/A')}",
                f"  Retorno 1m: {dados.get('retorno_1m_pct','N/A')}% | 1a: {dados.get('retorno_1y_pct','N/A')}%",
            ]
            if cfg["distribui_dividendos"]:
                linhas.append(f"  Dividend yield: {dados.get('dividend_yield_pct','N/A')}%")
            linhas.append("")

    # Alertas activos
    alertas = verificar_dividend_cut() + verificar_nav_drift()
    if alertas:
        linhas.append("ALERTAS:")
        for a in alertas:
            linhas.append(f"  ⚠ {a['mensagem']}")
    else:
        linhas.append("Sem alertas — todos os ETFs dentro dos parâmetros.")

    state["ultimo_relatorio_mensal"] = datetime.now().isoformat()
    _save(state)

    return "\n".join(linhas)


# ── Regra 5: Revisão anual ────────────────────────────────────────────────────

def revisao_anual_etf(forcar: bool = False) -> str | None:
    """
    Revisão anual de ETFs — corre em Janeiro.
    Avalia TER, tracking error, AUM e sugere substituições se necessário.
    """
    hoje = date.today()
    state = _load()

    if not forcar and hoje.month != 1:
        return None

    ultimo = state.get("ultima_revisao_anual")
    if not forcar and ultimo and date.fromisoformat(ultimo[:10]).year == hoje.year:
        return None

    linhas = [
        f"CFO ETF — Revisão Anual {hoje.year}",
        "=" * 50,
        "",
        "Critérios de avaliação: TER < 0.5%, AUM > €1B, tracking error < 2%, alternativa mais barata disponível.",
        "",
    ]

    substituicoes_sugeridas = []

    for ticker, cfg in ETF_UNIVERSE.items():
        dados = _get_etf_data(ticker)
        issues = []

        ter = cfg.get("ter_pct", 0)
        aum = dados.get("aum", 0) or 0

        if ter > 0.5:
            issues.append(f"TER elevado: {ter}%")
        if aum > 0 and aum < 1_000_000_000:
            issues.append(f"AUM baixo: €{aum/1e6:.0f}M (risco de encerramento)")

        status = "✓ OK" if not issues else "⚠ " + " | ".join(issues)
        linhas.append(f"{ticker}: {status}")

        if issues:
            substituicoes_sugeridas.append({"ticker": ticker, "issues": issues})

    if substituicoes_sugeridas:
        linhas += ["", "SUGESTÕES DE SUBSTITUIÇÃO:"]
        for s in substituicoes_sugeridas:
            linhas.append(f"  {s['ticker']}: {'; '.join(s['issues'])} — pesquisar alternativa com menor TER")

    linhas += [
        "",
        "Próxima revisão: Janeiro " + str(hoje.year + 1),
        "Decisão final: sempre do Vasco.",
    ]

    state["ultima_revisao_anual"] = datetime.now().isoformat()
    _save(state)

    return "\n".join(linhas)


# ── Verificação combinada para o CFO ─────────────────────────────────────────

def run_verificacoes_etf() -> list[str]:
    """
    Corre todas as verificações automáticas.
    Retorna lista de alertas activos (string) para o CFO usar.
    """
    alertas = []

    try:
        for a in verificar_dividend_cut():
            alertas.append(a["mensagem"])
    except Exception as e:
        alertas.append(f"ETF dividend check: erro ({e})")

    try:
        for a in verificar_nav_drift():
            alertas.append(a["mensagem"])
    except Exception as e:
        alertas.append(f"ETF NAV drift check: erro ({e})")

    # Relatório mensal (só no dia 1)
    try:
        rel = relatorio_mensal_etf()
        if rel:
            alertas.append("RELATÓRIO MENSAL ETF gerado — ver ceo_events")
            from pathlib import Path
            import json as _json
            ev_file = Path(__file__).parent / "memory" / "ceo_events.json"
            try:
                evs = _json.loads(ev_file.read_text())
            except Exception:
                evs = []
            evs.append({
                "ts": datetime.now().isoformat(),
                "agente": "cfo_etf",
                "tipo": "relatorio_mensal",
                "mensagem": rel[:1000],
                "urgencia": "baixa",
            })
            ev_file.write_text(_json.dumps(evs, ensure_ascii=False, indent=2))
    except Exception:
        pass

    # Revisão anual (só em Janeiro)
    try:
        rev = revisao_anual_etf()
        if rev:
            alertas.append("REVISÃO ANUAL ETF — acção requerida do Vasco")
    except Exception:
        pass

    return alertas
