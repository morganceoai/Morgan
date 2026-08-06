"""
Morgan CFO — Agente financeiro do império BCVertex.
Supervisiona: trading bot, PnL, drawdown, relatórios financeiros, alertas de risco.
Reporta ao Morgan CEO. A última decisão é sempre do Vasco.
"""
import os
import json
import threading
import time
from pathlib import Path
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv
load_dotenv()

MEMORY_DIR = Path(__file__).parent / "memory"
TRADING_STATE_FILE = MEMORY_DIR / "trading_state.json"
GRID_STATE_FILE    = MEMORY_DIR / "grid_state.json"
CFO_REPORT_FILE    = MEMORY_DIR / "cfo_reports.json"

DRAWDOWN_DAY_LIMITE   = 0.05   # 5% num dia — alerta imediato
DRAWDOWN_TOTAL_LIMITE = 0.15   # 15% total — parar bots
CAPITAL_BASE          = 100.0  # USDT de referência

# Limites de defesa
SALDO_DIVERGENCIA_MAX  = 0.05   # 5% de divergência saldo real vs memória → alerta
PRECO_SPIKE_MAX        = 0.10   # 10% de diferença vs último preço válido → recusa operação
TRADES_POR_HORA_MAX    = 15     # grid a fazer >15 trades/hora → anomalia
GRID_RANGE_ALERTA_PCT  = 0.005  # grid dentro de 0.5% do limite → alerta preventivo


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

    # Profit factor e expectancy
    gross_profit = sum(t["pnl"] for t in ganhos)
    gross_loss = abs(sum(t["pnl"] for t in perdas))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_win = gross_profit / len(ganhos) if ganhos else 0
    avg_loss = gross_loss / len(perdas) if perdas else 0
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")
    expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

    # Streak de perdas consecutivas (todos os trades, não só do mês)
    streak_perdas = 0
    for t in reversed(trades):
        if t.get("pnl", 0) < 0:
            streak_perdas += 1
        else:
            break

    # Dias sem trades
    trades_com_data = [t for t in trades if t.get("closed_at")]
    if trades_com_data:
        ultima_data_str = sorted(trades_com_data, key=lambda t: t["closed_at"])[-1]["closed_at"][:10]
        try:
            ultima_data = date.fromisoformat(ultima_data_str)
            dias_sem_trades = (date.today() - ultima_data).days
        except Exception:
            dias_sem_trades = 0
    else:
        dias_sem_trades = 0

    # Alertas
    alertas = []
    nivel_risco = "verde"

    if drawdown_dia_pct >= DRAWDOWN_DAY_LIMITE:
        alertas.append(f"DRAWDOWN DIA: -{drawdown_dia_pct*100:.1f}% (limite {DRAWDOWN_DAY_LIMITE*100:.0f}%)")
        nivel_risco = "vermelho"

    if drawdown_total_pct >= DRAWDOWN_TOTAL_LIMITE:
        alertas.append(f"DRAWDOWN TOTAL: -{drawdown_total_pct*100:.1f}% — recomendar paragem (limite {DRAWDOWN_TOTAL_LIMITE*100:.0f}%)")
        nivel_risco = "vermelho"
    elif drawdown_total_pct >= DRAWDOWN_TOTAL_LIMITE * 0.7:
        alertas.append(f"DRAWDOWN TOTAL: -{drawdown_total_pct*100:.1f}% — 70% do limite, atenção")
        nivel_risco = "amarelo"

    if streak_perdas >= 10:
        alertas.append(f"STREAK: {streak_perdas} perdas consecutivas — raro para WR de {win_rate:.0f}%, rever estratégia")
        nivel_risco = "vermelho"
    elif streak_perdas >= 7:
        alertas.append(f"STREAK: {streak_perdas} perdas consecutivas — monitorizar")
        if nivel_risco == "verde":
            nivel_risco = "amarelo"

    if len(trades_mes) >= 20 and profit_factor < 1.2:
        alertas.append(f"PROFIT FACTOR: {profit_factor:.2f} — abaixo do mínimo saudável (ref: >1.5)")
        if nivel_risco == "verde":
            nivel_risco = "amarelo"

    if len(trades_mes) >= 30 and win_rate < 35:
        alertas.append(f"WIN RATE: {win_rate:.0f}% com {len(trades_mes)} trades — abaixo do esperado para EMA 9/21")
        if nivel_risco == "verde":
            nivel_risco = "amarelo"

    if dias_sem_trades >= 10:
        alertas.append(f"INACTIVIDADE: {dias_sem_trades} dias sem trades — verificar bot")
        if nivel_risco == "verde":
            nivel_risco = "amarelo"

    if not active:
        alertas.append("Bot parado — requer verificação")
        if nivel_risco == "verde":
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
        "pnl_mes": round(sum(t.get("pnl", 0) for t in trades_mes), 4),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else None,
        "expectancy": round(expectancy, 4),
        "rr_ratio": round(rr_ratio, 2) if rr_ratio != float("inf") else None,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "streak_perdas": streak_perdas,
        "dias_sem_trades": dias_sem_trades,
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
        f"  Profit factor: {r['profit_factor'] if r['profit_factor'] else 'N/A (dados insuf.)'}",
        f"  Expectancy: {r['expectancy']:+.4f} USDT/trade",
        f"  R:R ratio: {r['rr_ratio'] if r['rr_ratio'] else 'N/A'}",
        f"  Streak perdas: {r['streak_perdas']}",
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

    # Etsy revenue
    try:
        from etsy_service import resumo_loja
        etsy = resumo_loja()
        linhas += [
            "",
            "ETSY — PlannerAtlas",
            f"  Listings activos: {etsy['listings_activos']}",
            f"  Vendas (30 dias): {etsy['vendas_periodo']}",
            f"  Receita estimada: €{etsy['receita_estimada']:.2f}",
        ]
    except Exception:
        pass

    # Consistência (Defesa 5)
    try:
        c = relatorio_consistencia()
        linhas += ["", "CONSISTÊNCIA"]
        linhas.append(f"  Saldo real: ${c['saldo_real_usdt']:.2f} USDT + {c['saldo_real_btc']:.6f} BTC")
        linhas.append(f"  Grid posições abertas: {c['grid_posicoes_abertas']}")
        if c["alertas"]:
            for a in c["alertas"]:
                linhas.append(f"  ⚠ {a}")
        else:
            linhas.append("  ✓ Sem divergências detectadas")
    except Exception:
        pass

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


# ── Sistema de defesa ────────────────────────────────────────────────────────

def _notificar_cfo(tipo: str, mensagem: str, urgencia: str = "alta"):
    """Escreve evento em ceo_events.json e imprime no log."""
    print(f"[cfo/{tipo}] {mensagem}", flush=True)
    try:
        ceo_events_file = MEMORY_DIR / "ceo_events.json"
        try:
            eventos = json.loads(ceo_events_file.read_text())
        except Exception:
            eventos = []
        eventos.append({
            "ts": datetime.now().isoformat(),
            "agente": "cfo",
            "tipo": tipo,
            "mensagem": mensagem,
            "urgencia": urgencia,
        })
        ceo_events_file.write_text(json.dumps(eventos, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[cfo] erro ceo_events: {e}", flush=True)


def _get_exchange():
    import ccxt
    return ccxt.binance({
        "apiKey":  os.getenv("BINANCE_API_KEY", ""),
        "secret":  os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })


def verificar_saldo_vs_memoria() -> list:
    """
    Defesa 1: compara saldo real Binance com o esperado pelos estados em memória.
    Divergência >5% → alerta (indica bug silencioso ou ordem não registada).
    """
    alertas = []
    try:
        ex = _get_exchange()
        balance = ex.fetch_balance()
        usdt_real = float(balance.get("USDT", {}).get("total", 0))
        btc_real  = float(balance.get("BTC",  {}).get("total", 0))
        ticker    = ex.fetch_ticker("BTC/USDT")
        preco     = ticker["last"]
        total_real = usdt_real + btc_real * preco

        # Capital esperado: base - perdas registadas
        st = _load_trading_state()
        pnl_super = st.get("pnl_total", 0.0)

        grid_pnl = 0.0
        try:
            grid_st = json.loads(GRID_STATE_FILE.read_text())
            grid_pnl = grid_st.get("pnl_total", 0.0)
            # Valor em posições abertas do grid
            for pos in grid_st.get("open_positions", {}).values():
                grid_pnl += pos.get("size", 0) * preco
        except Exception:
            pass

        capital_esperado = CAPITAL_BASE + pnl_super + grid_pnl
        divergencia = abs(total_real - capital_esperado) / max(capital_esperado, 1)

        if divergencia > SALDO_DIVERGENCIA_MAX:
            msg = (
                f"SALDO DIVERGENTE: real=${total_real:.2f} "
                f"vs esperado=${capital_esperado:.2f} "
                f"(divergência {divergencia*100:.1f}%)"
            )
            alertas.append(msg)
            _notificar_cfo("saldo_divergente", msg, "critica")

    except Exception as e:
        alertas.append(f"SALDO: erro a verificar ({e})")

    return alertas


def verificar_velocidade_grid() -> list:
    """
    Defesa 2: detecta se o grid está a executar trades a velocidade anómala.
    >15 trades na última hora → possível loop de erro.
    """
    alertas = []
    try:
        grid_st = json.loads(GRID_STATE_FILE.read_text())
        trades = grid_st.get("trades", [])
        uma_hora_atras = datetime.now().isoformat()[:13]  # "YYYY-MM-DDTHH"
        trades_hora = [
            t for t in trades
            if t.get("closed_at", "")[:13] == uma_hora_atras
        ]
        if len(trades_hora) > TRADES_POR_HORA_MAX:
            msg = (
                f"VELOCIDADE ANÓMALA: {len(trades_hora)} trades na última hora "
                f"(limite: {TRADES_POR_HORA_MAX})"
            )
            alertas.append(msg)
            _notificar_cfo("velocidade_grid", msg, "critica")
    except Exception:
        pass
    return alertas


def verificar_range_grid() -> list:
    """
    Defesa 3: alerta preventivo quando o preço se aproxima dos limites do grid.
    Não pausa — coloca o Vasco em posição de decidir antes da ruptura.
    """
    alertas = []
    try:
        grid_st = json.loads(GRID_STATE_FILE.read_text())
        if not grid_st.get("active") or not grid_st.get("ref_price"):
            return alertas

        ex = _get_exchange()
        preco = ex.fetch_ticker("BTC/USDT")["last"]

        ref        = grid_st["ref_price"]
        level_size = grid_st["level_size"]
        n_levels   = 10
        lower      = ref - (n_levels // 2) * level_size
        upper      = ref + (n_levels // 2) * level_size
        margem     = (upper - lower) * GRID_RANGE_ALERTA_PCT

        if preco < lower + margem:
            dist_pct = (preco - lower) / lower * 100
            msg = (
                f"GRID LIMITE INFERIOR: BTC ${preco:.0f} está a "
                f"{dist_pct:.1f}% do limite inferior ${lower:.0f}. "
                f"Se romper, posições abertas ficam em perda não realizada."
            )
            alertas.append(msg)
            _notificar_cfo("grid_range", msg, "alta")
        elif preco > upper - margem:
            msg = (
                f"GRID LIMITE SUPERIOR: BTC ${preco:.0f} está a "
                f"{((upper - preco) / upper * 100):.1f}% do limite superior ${upper:.0f}."
            )
            alertas.append(msg)
            _notificar_cfo("grid_range", msg, "media")

    except Exception:
        pass
    return alertas


def verificar_preco_sanidade(preco_novo: float, simbolo: str = "BTC/USDT") -> bool:
    """
    Defesa 4: valida se um preço recebido é plausível vs o último registado.
    Retorna False se o preço for suspeito (spike de API). Usado pelos bots antes de operar.
    """
    try:
        grid_st = json.loads(GRID_STATE_FILE.read_text())
        ultimo = grid_st.get("last_price")
        if ultimo and abs(preco_novo - ultimo) / ultimo > PRECO_SPIKE_MAX:
            msg = (
                f"PREÇO SUSPEITO: recebido ${preco_novo:.2f} vs último ${ultimo:.2f} "
                f"(diferença {abs(preco_novo - ultimo) / ultimo * 100:.1f}% > {PRECO_SPIKE_MAX*100:.0f}%)"
            )
            _notificar_cfo("preco_spike", msg, "critica")
            return False
    except Exception:
        pass
    return True


def relatorio_consistencia() -> dict:
    """
    Defesa 5: snapshot de consistência para incluir no relatório das 22h.
    Compara estado em memória com realidade Binance.
    """
    resultado = {
        "ts": datetime.now().isoformat(),
        "alertas": [],
        "saldo_real_usdt": None,
        "saldo_real_btc": None,
        "grid_posicoes_abertas": 0,
        "supertrend_posicao": None,
        "consistente": True,
    }
    try:
        ex = _get_exchange()
        balance = ex.fetch_balance()
        resultado["saldo_real_usdt"] = round(float(balance.get("USDT", {}).get("total", 0)), 4)
        resultado["saldo_real_btc"]  = round(float(balance.get("BTC",  {}).get("total", 0)), 8)

        try:
            grid_st = json.loads(GRID_STATE_FILE.read_text())
            resultado["grid_posicoes_abertas"] = len(grid_st.get("open_positions", {}))
        except Exception:
            pass

        st = _load_trading_state()
        resultado["supertrend_posicao"] = st.get("position")

        alertas = (
            verificar_saldo_vs_memoria() +
            verificar_velocidade_grid() +
            verificar_range_grid()
        )
        resultado["alertas"] = alertas
        resultado["consistente"] = len(alertas) == 0

    except Exception as e:
        resultado["alertas"].append(f"Erro ao verificar consistência: {e}")
        resultado["consistente"] = False

    return resultado


def run_defesa_completa() -> list:
    """
    Corre todas as verificações de defesa. Chamado pelo scheduler do CFO.
    Retorna lista de alertas activos.
    """
    alertas = []
    alertas += verificar_saldo_vs_memoria()
    alertas += verificar_velocidade_grid()
    alertas += verificar_range_grid()
    return alertas


# ── Circuit breaker autónomo ─────────────────────────────────────────────────

def parar_bot(razao: str):
    """
    Para o trading bot escrevendo active=False em trading_state.json.
    NUNCA fecha posições — isso seria uma trade. Apenas impede novas entradas.
    """
    try:
        state = _load_trading_state()
        state["active"] = False
        state["circuit_breaker_razao"] = razao
        state["circuit_breaker_ts"] = datetime.now().isoformat()
        TRADING_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[cfo] parar_bot: erro a escrever state: {e}", flush=True)
        return

    msg = f"[CFO CIRCUIT BREAKER] Bot parado automaticamente. Razão: {razao}"
    print(msg, flush=True)

    # Notificar CEO via ceo_events.json (CEO lê no próximo briefing)
    try:
        ceo_events_file = MEMORY_DIR / "ceo_events.json"
        try:
            eventos = json.loads(ceo_events_file.read_text())
        except Exception:
            eventos = []
        eventos.append({
            "ts": datetime.now().isoformat(),
            "agente": "cfo",
            "tipo": "circuit_breaker",
            "mensagem": msg,
            "urgencia": "critica",
        })
        ceo_events_file.write_text(json.dumps(eventos, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[cfo] parar_bot: erro ceo_events: {e}", flush=True)

    # Registar em memória episódica
    try:
        from episodic_memory import registar_evento
        registar_evento("cfo", "circuit_breaker", msg)
    except Exception:
        pass


def circuit_breaker() -> bool:
    """
    Verifica thresholds críticos e para o bot se necessário.
    Retorna True se activado, False caso contrário.
    Condições: drawdown total >= 15% OU streak >= 10 perdas consecutivas.
    """
    r = avaliar_risco_trading()

    if not r["active"]:
        return False  # já parado

    razao = None

    if r["drawdown_total_pct"] >= DRAWDOWN_TOTAL_LIMITE * 100:
        razao = (
            f"Drawdown total atingiu {r['drawdown_total_pct']:.1f}% "
            f"(limite: {DRAWDOWN_TOTAL_LIMITE * 100:.0f}%)"
        )
    elif r["streak_perdas"] >= 10:
        razao = f"Streak de {r['streak_perdas']} perdas consecutivas (limite: 10)"

    if razao:
        parar_bot(razao)
        # Pausar também o grid bot se estiver activo
        try:
            from grid_bot import pause_bot as grid_pause
            grid_pause()
            print(f"[cfo] Grid Bot também pausado: {razao}", flush=True)
        except Exception:
            pass
        return True

    return False


def ciclo_decisao() -> dict:
    """
    Ciclo de inteligência do CFO — corre a cada 30 minutos.
    PERCEPÇÃO → ANÁLISE (LLM) → DECISÃO → EXECUÇÃO (observation ou real).

    Retorna a decisão tomada.
    """
    try:
        from cfo_market import snapshot_mercado
        from cfo_accounts import resumo_imperio
        from cfo_executor import executar_decisao, get_modo

        # 1. PERCEPÇÃO
        mercado = snapshot_mercado("BTC/USDT")
        imperio = resumo_imperio()
        risco_trading = avaliar_risco_trading()
        modo_executor = get_modo()

        # Snapshot do grid
        grid_status = {}
        try:
            from grid_bot import get_status
            grid_status = get_status()
        except Exception:
            pass

        # Fase de mercado enriquecida
        fase_mercado = {}
        try:
            from cfo_market_phase import snapshot_fase
            fase_mercado = snapshot_fase()
        except Exception:
            pass

        # Portfolio M1-M5
        portfolio = {}
        try:
            from cfo_portfolio import resumo_portfolio
            portfolio = resumo_portfolio()
        except Exception:
            pass

        # Negócios (PAtlas + Pulser)
        negocios_str = ""
        try:
            from patlas_agent import get_resumo_financeiro as patlas_res
            negocios_str += f"PAtlas: {patlas_res()}\n"
        except Exception:
            pass
        try:
            from pulser_agent import get_resumo_financeiro as pulser_res
            negocios_str += f"Pulser: {pulser_res()}"
        except Exception:
            pass

        fase_est = fase_mercado.get("fase_estrutural", {})
        fase_cp = fase_mercado.get("fase_curto_prazo", {})
        funding = fase_mercado.get("funding_rate", {})
        dom = fase_mercado.get("dominancia_btc", {})
        alertas_fase = fase_mercado.get("alertas", [])

        contexto = f"""CICLO CFO — {datetime.now().strftime('%d/%m/%Y %H:%M')}
MODO EXECUTOR: {modo_executor.upper()} (observation=só analisar; execution=executar)

FASE DE MERCADO BTC/USDT:
- Fase estrutural (diário): {fase_est.get('fase','?').upper()} | RSI={fase_est.get('rsi14','?')} | SMA200 ${fase_est.get('sma200','?')} ({fase_est.get('distancia_sma200_pct',0):+.1f}%)
- Tendência curto prazo (30m): {fase_cp.get('tendencia','?').upper()}
- Funding rate: {funding.get('rate_pct','?')}% ({funding.get('sentimento','?')})
- Dominância BTC: {dom.get('dominancia_pct','?')}% — {dom.get('interpretacao','?')}
- Estratégia recomendada: {fase_mercado.get('estrategia_recomendada','?')} — {fase_mercado.get('estrategia_razao','?')}
- Alertas fase: {'; '.join(alertas_fase) if alertas_fase else 'nenhum'}

GRID BOT:
- Activo: {grid_status.get('active', '?')}
- Posições abertas: {grid_status.get('open_positions', 0)}
- PnL total: {grid_status.get('pnl_total', 0):.4f} USDT
- PnL hoje: {grid_status.get('pnl_today', 0):.4f} USDT
- Último preço: ${grid_status.get('last_price', '?')}
- Ref. grid: ${grid_status.get('ref_price', '?')}

RISCO TRADING:
- Nível: {risco_trading.get('nivel_risco', '?').upper()}
- Drawdown total: {risco_trading.get('drawdown_total_pct', 0):.1f}%
- Streak perdas: {risco_trading.get('streak_perdas', 0)}
- Alertas: {'; '.join(risco_trading.get('alertas', [])) or 'nenhum'}

PORTFOLIO BCVertex (M1-M5):
- Capital total: €{portfolio.get('capital_total_eur', 0):,.0f}
- Milestones novos: {[m['milestone_eur'] for m in portfolio.get('milestones_novos', [])] or 'nenhum'}
- Próximo milestone: {portfolio.get('proximo_milestone', {}).get('milestone_eur', 'N/A')} (falta €{portfolio.get('proximo_milestone', {}).get('falta_eur', 'N/A')})

NEGÓCIOS:
{negocios_str or 'indisponível'}

IMPÉRIO (contas Binance):
- Capital total alocado: ${imperio.get('capital_total_alocado', 0):.2f}
- PnL total império: ${imperio.get('pnl_total_imperio', 0):.4f}
- Contas activas: {imperio.get('contas_activas', 0)}/{imperio.get('total_contas', 0)}"""

        system = """És o CFO do império BCVertex. Analisa o contexto e toma UMA decisão estruturada.

DECISÕES AUTÓNOMAS (não precisam do Vasco):
- manter: continuar como está
- pausar_grid: parar o grid bot temporariamente
- retomar_grid: retomar o grid bot após pausa

DECISÕES QUE REQUEREM VASCO (autonomo: false):
- escalar_vasco: quando há risco elevado, oportunidade de reajuste de capital, ou situação fora do normal
- resetar_grid: reiniciar o grid com novo preço de referência (impacto alto)

REGRAS:
- Se risco VERMELHO → pausa_grid + escala ao Vasco
- Se regime VOLATILE → considera pausar_grid
- Se regime mudou de LATERAL para TRENDING → escalar (estratégia pode mudar)
- Se tudo estável → manter

Responde APENAS com JSON válido, sem mais texto:
{
  "acao": "manter" | "pausar_grid" | "retomar_grid" | "resetar_grid" | "escalar_vasco",
  "autonomo": true | false,
  "confianca": 0-100,
  "razao": "explicação concisa em PT-PT",
  "conta_id": "binance_grid_btc",
  "observacoes_futuras": "o que monitorizar na próxima análise"
}"""

        # 2. ANÁLISE LLM
        from claude_guard import GuardedClient
        client = GuardedClient("cfo")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": contexto}],
        )

        raw = response.content[0].text.strip()
        # Extrair JSON mesmo se vier com markdown
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()

        decisao = json.loads(raw)

        # 3. EXECUÇÃO
        resultado = executar_decisao(decisao)

        print(
            f"[cfo/ciclo] {decisao.get('acao')} | autonomo={decisao.get('autonomo')} "
            f"| confianca={decisao.get('confianca')}% | modo={modo_executor} "
            f"| resultado={resultado.get('status')}",
            flush=True
        )

        return {**decisao, "resultado_execucao": resultado}

    except Exception as e:
        print(f"[cfo/ciclo] erro no ciclo de decisão: {e}", flush=True)
        return {"acao": "erro", "razao": str(e)}


def iniciar_scheduler_cfo():
    """
    Inicia loop autónomo do CFO — a cada 30 minutos:
    1. Circuit breaker (drawdown/streak)
    2. Defesa completa (saldo, velocidade, range)
    3. Ciclo de decisão inteligente (LLM)
    """
    def _loop():
        time.sleep(60)  # 1min startup delay
        ciclo_count = 0
        while True:
            try:
                circuit_breaker()
            except Exception as e:
                print(f"[cfo] circuit_breaker erro: {e}", flush=True)
            try:
                run_defesa_completa()
            except Exception as e:
                print(f"[cfo] defesa erro: {e}", flush=True)
            try:
                ciclo_decisao()
            except Exception as e:
                print(f"[cfo] ciclo_decisao erro: {e}", flush=True)

            # ETF + portfolio — a cada 4 ciclos (2h)
            ciclo_count += 1
            if ciclo_count % 4 == 0:
                try:
                    from cfo_etf import run_verificacoes_etf
                    alertas_etf = run_verificacoes_etf()
                    for a in alertas_etf:
                        _notificar_cfo("etf_alerta", a, "media")
                except Exception as e:
                    print(f"[cfo] etf check erro: {e}", flush=True)
                try:
                    from cfo_portfolio import verificar_milestones
                    milestones = verificar_milestones()
                    for m in milestones:
                        _notificar_cfo("milestone", f"Portfolio atingiu €{m['milestone_eur']:,}! Acções: {', '.join(m['acoes'][:2])}", "critica")
                except Exception as e:
                    print(f"[cfo] milestone check erro: {e}", flush=True)

            time.sleep(30 * 60)

    t = threading.Thread(target=_loop, daemon=True, name="cfo-scheduler")
    t.start()


# ── Conversa com o CFO ───────────────────────────────────────────────────────

_cfo_history: list = []

def analisar_reits() -> str:
    """
    Análise estática de REITs e fundos imobiliários PT/ES/IE como alternativa
    de rendimento passivo para o portfólio BCVertex.
    Actualizar quando houver dados em tempo real via API.
    """
    fundos = [
        # Portugal
        {
            "nome": "Sierra Income Fund (SIFB)",
            "mercado": "PT",
            "tipo": "REIT cotado",
            "foco": "Centros comerciais PT/ES",
            "dividend_yield_est": "5-7%",
            "min_investimento": "Acções — sem mínimo",
            "risco": "Médio",
            "notas": "Gerido pela Sierra (Sonae). Liquidez diária na Euronext Lisboa.",
        },
        {
            "nome": "ECS — Edifício Chiado (imobiliário privado)",
            "mercado": "PT",
            "tipo": "Fundo imobiliário fechado",
            "foco": "Imóveis comerciais Lisboa/Porto",
            "dividend_yield_est": "4-6%",
            "min_investimento": "€5.000–€25.000",
            "risco": "Médio",
            "notas": "Distribuição anual. Liquidez limitada — horizonte 5+ anos.",
        },
        # Espanha
        {
            "nome": "Merlin Properties (MRL.MC)",
            "mercado": "ES",
            "tipo": "SOCIMI (REIT espanhol)",
            "foco": "Escritórios, logística, centros comerciais ES/PT",
            "dividend_yield_est": "4-5%",
            "min_investimento": "Acções — sem mínimo",
            "risco": "Médio",
            "notas": "IBEX 35. Cotada na Bolsa de Madrid. Dividend yield estável.",
        },
        {
            "nome": "Inmobiliaria Colonial (COL.MC)",
            "mercado": "ES",
            "tipo": "SOCIMI",
            "foco": "Escritórios prime Madrid/Barcelona/Paris",
            "dividend_yield_est": "3-4%",
            "min_investimento": "Acções — sem mínimo",
            "risco": "Médio-baixo",
            "notas": "Prime office. Menor yield, maior estabilidade.",
        },
        # Irlanda
        {
            "nome": "IRES REIT (IRES.IE)",
            "mercado": "IE",
            "tipo": "REIT residencial",
            "foco": "Apartamentos Dublin",
            "dividend_yield_est": "5-6%",
            "min_investimento": "Acções — sem mínimo",
            "risco": "Médio",
            "notas": "Cotada na Euronext Dublin. Exposição ao mercado residencial IE.",
        },
        {
            "nome": "Hibernia REIT → Brookfield (absors. 2022)",
            "mercado": "IE",
            "tipo": "Privado pós-aquisição",
            "foco": "Escritórios Dublin",
            "dividend_yield_est": "N/A",
            "min_investimento": "Não cotado",
            "risco": "N/A",
            "notas": "Já não cotado. Referência histórica.",
        },
        # ETFs como alternativa
        {
            "nome": "iShares European Property Yield (IPRP.L)",
            "mercado": "EU",
            "tipo": "ETF REIT Europa",
            "foco": "Diversificado — PT/ES/DE/FR/NL",
            "dividend_yield_est": "3-4%",
            "min_investimento": "Acções — sem mínimo",
            "risco": "Médio-baixo",
            "notas": "Diversificação máxima. Liquidez diária. Ideal para começar.",
        },
        {
            "nome": "Xtrackers FTSE EPRA/NAREIT (XREA.DE)",
            "mercado": "EU",
            "tipo": "ETF REIT Europa + Global",
            "foco": "REITs Europeus + US",
            "dividend_yield_est": "3-5%",
            "min_investimento": "Acções — sem mínimo",
            "risco": "Médio-baixo",
            "notas": "Exposição global com peso europeu. Acumulação ou distribuição disponíveis.",
        },
    ]

    hoje = date.today().strftime("%d/%m/%Y")
    linhas = [
        f"CFO — Análise REITs e Fundos Imobiliários PT/ES/IE ({hoje})",
        "=" * 60,
        "",
        "OBJECTIVO: Rendimento passivo complementar ao trading e Etsy.",
        "META: Contribuição para €10.000/mês passivo do Vasco.",
        "",
    ]

    por_mercado: dict[str, list] = {}
    for f in fundos:
        por_mercado.setdefault(f["mercado"], []).append(f)

    for mercado, fs in por_mercado.items():
        linhas.append(f"── {mercado} ──")
        for f in fs:
            linhas += [
                f"  {f['nome']} ({f['tipo']})",
                f"    Foco: {f['foco']}",
                f"    Yield estimado: {f['dividend_yield_est']} | Risco: {f['risco']}",
                f"    Mínimo: {f['min_investimento']}",
                f"    Nota: {f['notas']}",
                "",
            ]

    linhas += [
        "── RECOMENDAÇÃO CFO ──",
        "",
        "Para capital inicial <€5.000: ETF iShares IPRP.L ou Xtrackers XREA.DE.",
        "  → Liquidez diária, diversificação, yield 3-5%, sem gestão activa.",
        "",
        "Para capital €5.000–€25.000: Merlin Properties (MRL.MC) + ETF.",
        "  → SOCIMI PT/ES com track record, dividend estável.",
        "",
        "Para capital >€25.000: adicionar Sierra Income Fund (SIFB) para exposição PT directa.",
        "",
        "Próximo passo: Vasco confirma envelope de capital disponível para imobiliário",
        "→ CFO afina alocação e timing de entrada.",
        "",
        "Confiança 85% — dados de yield são estimativas 2025-2026. Verificar prospecto actual antes de investir.",
    ]

    return "\n".join(linhas)


def _build_cfo_system(contexto: str = "") -> str:
    r = avaliar_risco_trading()
    hoje = datetime.now().strftime("%d de %B de %Y")

    pf_str = f"{r['profit_factor']}" if r['profit_factor'] else "N/A (<20 trades)"
    rr_str = f"{r['rr_ratio']}" if r['rr_ratio'] else "N/A"
    amostra_nota = f" (⚠ amostra pequena: {r['trades_mes']} trades)" if r['trades_mes'] < 30 else ""

    return f"""És o Morgan CFO — director financeiro do império BCVertex.

Data: {hoje}
Língua: sempre PT-PT. Números em primeiro lugar. Sem emojis.
Reportas ao Morgan CEO. O Vasco pode falar directamente contigo.
Para voltar ao CEO, o Vasco diz "volta ao Morgan".

## ESTADO DO TRADING BOT (BTC/USDT · EMA 9/21 · 30m)
Capital: ${r['capital_atual']:.2f} USDT (base: $100) | Estado: {'ATIVO' if r['active'] else 'PARADO'}
PnL total: {r['pnl_total']:+.2f} USDT | PnL hoje: {r['pnl_hoje']:+.2f} USDT
Drawdown total: {r['drawdown_total_pct']:.1f}% | Drawdown dia: {r['drawdown_dia_pct']:.1f}%

MÉTRICAS DO MÊS ({r['trades_mes']} trades{amostra_nota}):
Win rate: {r['win_rate']:.0f}% | Profit factor: {pf_str} | R:R: {rr_str}
Expectancy: {r['expectancy']:+.4f} USDT/trade
Streak perdas actual: {r['streak_perdas']} | Dias sem trades: {r['dias_sem_trades']}

RISCO: {r['nivel_risco'].upper()}
{chr(10).join(r['alertas']) if r['alertas'] else 'Sem alertas.'}

## MODO DE RESPOSTA
- **Briefing/rotina**: máximo 2 linhas — número principal + estado de risco
- **Análise pedida**: MÉTRICA → CONTEXTO → ACÇÃO RECOMENDADA
- **Default**: modo briefing — brevidade é respeito pelo tempo do Vasco
- Primeira linha é sempre conteúdo, nunca introdução ("Bom dia", "Vou analisar...", etc.)
- Mostrar sempre valor absoluto E percentagem (ex: "-$3.20 (-3.2%)")
- Qualificar sempre com amostra: "com {r['trades_mes']} trades, esta métrica é {'indicativa' if r['trades_mes'] < 30 else 'significativa'}"

## RESPONSABILIDADES
1. Supervisionar trading bot BTC/USDT — capital $100 USDT
2. Monitorizar PnL, drawdown, profit factor, streak, inactividade
3. Alertar CEO quando qualquer threshold for atingido
4. Relatórios financeiros diários (7h via cfo_reporting.briefing_matinal) e completos (22h via cfo_reporting.relatorio_22h)
5. Avaliar viabilidade financeira de novos negócios antes de aprovação
6. Monitorizar portfolio M1-M5 via cfo_portfolio — capital por motor, milestones, projecções
7. Monitorizar ETFs via cfo_etf — dividend cut, NAV drift, revisão anual
8. Analisar fase de mercado via cfo_market_phase — SMA200, RSI, funding rate, dominância BTC
9. Receber resumos financeiros do PAtlas (Etsy) e Pulser (newsletter) — não gerir esses negócios
10. Scorecard mensal via cfo_reporting.scorecard_mensal — dia 1 de cada mês

## THRESHOLDS DE ALERTA
| Métrica | Amarelo | Vermelho |
|---------|---------|---------|
| Drawdown dia | — | >5% |
| Drawdown total | >10.5% (70% limite) | >15% |
| Streak perdas | ≥7 | ≥10 |
| Profit factor (≥20 trades) | <1.5 | <1.2 |
| Win rate (≥30 trades) | — | <35% |
| Inactividade | ≥7 dias | ≥10 dias |

## REGRAS DE AUTONOMIA
Age sozinho (reporta depois): calcular métricas, arquivar relatório, identificar alertas.
Escala ao CEO/Vasco: drawdown >15%, streak ≥10, profit factor <1.0 com ≥50 trades, bot inactivo ≥10 dias.
NUNCA faz autonomamente: executar trades, alterar parâmetros do bot, mover capital.

## REGRAS DE CONFIANÇA (por tipo de decisão)
- Relatório de rotina: reportar directamente
- Alerta de risco: indicar confiança + dados que fundamentam
- Recomendação de parar bot: exige confiança ≥95% + dados suficientes (≥30 trades)
- Nunca inflar confiança com amostra pequena — dizer "amostra insuficiente" é a resposta correcta
- Formato obrigatório em decisões: "Confiança X% — [n trades, período] — [análise]"

## CONTEXTO DE MERCADO
- EMA crossover em 30m: win rate normal 38–50%, profit factor saudável >1.5
- Inactividade em mercado lateral = comportamento correcto, não bug
- Drawdown em bear market + bot em drawdown = pode ser esperado — contextualizar sempre
- Nunca recomendar paragem sem verificar contexto de mercado BTC"""


def get_cfo_reply(user_message: str) -> str:
    """Ponto de entrada para conversa com o CFO."""
    global _cfo_history

    mem_semantica = ""
    try:
        from episodic_memory import get_contexto_agente
        mem_semantica = get_contexto_agente("cfo", user_message or "trading Binance BTC posições portfolio BCVertex")
    except Exception:
        pass

    system = _build_cfo_system(user_message + ("\n\n[Memórias relevantes]\n" + mem_semantica if mem_semantica else ""))
    _cfo_history.append({"role": "user", "content": user_message})

    if len(_cfo_history) > 20:
        _cfo_history = _cfo_history[-20:]

    from claude_guard import GuardedClient
    client = GuardedClient("cfo")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=_cfo_history,
    )

    reply = response.content[0].text
    _cfo_history.append({"role": "assistant", "content": reply})

    # Camada episódica — registar evento
    try:
        from episodic_memory import registar_evento
        registar_evento("cfo", "conversa", f"Q: {user_message[:100]} | R: {reply[:200]}")
    except Exception:
        pass

    return reply


if __name__ == "__main__":
    print(relatorio_financeiro_diario())
