"""
Morgan CFO — Agente financeiro do império BCVertex.
Supervisiona: trading bot, PnL, drawdown, relatórios financeiros, alertas de risco.
Reporta ao Morgan CEO. A última decisão é sempre do Vasco.
"""
import os
import json
from pathlib import Path
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv
load_dotenv()

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
4. Relatórios financeiros diários (7h) e completos (22h)
5. Avaliar viabilidade financeira de novos negócios antes de aprovação
6. Quando império crescer: receitas dos sub-Morgans, balanços, impostos
7. REITs e fundos PT/ES/IE como rendimento passivo (usa analisar_reits() para detalhes)

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

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
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
