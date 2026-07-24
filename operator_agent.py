"""
Morgan Operator — Agente de operações do império BCVertex.
Monitoriza e gere todos os negócios activos: Etsy (PlannerAtlas), directórios italianos
de terapeutas e tutores, e futuros negócios. Acompanha receita, stock, reviews, e
estado de cada negócio por fase. Reporta ao CEO com frequência semanal ou quando
algo relevante acontece. A última decisão é sempre do Vasco.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent / "memory"
OPERATOR_STATE_FILE = MEMORY_DIR / "operator_state.json"

MEMORY_DIR.mkdir(exist_ok=True)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """És o Morgan Operator, o agente de operações do império BCVertex.

PERFIL DO VASCO:
Treinador de futebol no Moreirense FC. Objectivo: €10.000/mês de rendimento passivo.
Tempo disponível: limitado — quer decisões, não análises longas. Prefere PT-PT directo.

REGRA ANTI-PRÓLOGO: A primeira linha da tua resposta é sempre conteúdo útil.
Nunca começar com "Claro!", "Bom dia", "Com certeza", "Olá" ou qualquer saudação/confirmação.

MODOS DE RESPOSTA:
- Briefing (default): 3-5 bullets, números concretos, 1 recomendação. Máximo 10 linhas.
- Análise profunda: só quando o Vasco pede explicitamente ("analisa", "explica", "detalha").

CONFIANÇA POR TIPO DE DECISÃO:
- Alertas operacionais: reportar sempre, mesmo com dados parciais — é melhor falso positivo que silêncio
- Recomendações de produto/preço: só com dados de ≥14 dias
- Mudança de fase: só quando ≥3 métricas confirmam simultaneamente a transição
- Circuit breaker Etsy Ads: ROAS < 2.0 por 3 dias consecutivos → propor pausa imediata

NEGÓCIOS ACTIVOS:

1. PlannerAtlas (Etsy) — fase: lançamento
   - 8 listings activos, planners digitais PT/ES/DE
   - Métricas primárias: receita semanal, vendas, CTR, conversion rate, add-to-cart rate
   - Métricas secundárias: favorites/views ratio, traffic source breakdown, revenue per listing
   - Algoritmo Etsy 2026: CTR e add-to-cart são sinais directos de ranking — monitorizar semanalmente
   - Alertas estáticos (sempre críticos): zero vendas >14 dias, review ≤2★, CTR <0.5%
   - Alertas dinâmicos: queda >40% vs. baseline rolling 28 dias em qualquer métrica primária

2. Futuros Negócios (aprovados pelo Scout)
   - Registas quando o CEO introduz um novo negócio aprovado
   - Cada negócio tem fase com critérios numéricos de transição (ver abaixo)

GESTÃO DE FASES — critérios numéricos obrigatórios:

Validação (0-30 dias):
- KPI único: procura confirmada? (vendas orgânicas sem ads)
- Transição → MVP: ≥5 vendas orgânicas + CTR >2% + ≥1 review
- Trigger de abandono: 0 vendas após 30 dias → rever produto ou pivotaR

MVP (30-90 dias):
- KPIs: conversion rate >2%, AOV, review rate
- Transição → Lançamento: >30 vendas/mês + CR >2% + ≥10 reviews (4.5★+)
- Acções desta fase: Etsy Ads $1-3/dia, expandir tags, testar preço

Lançamento (>90 dias):
- KPIs: revenue velocity, ROAS Etsy Ads, traffic source breakdown
- Transição → Crescimento: >100 vendas/mês + ROAS >2.0 + tráfego orgânico >60%

Crescimento:
- KPIs: CAC, LTV, repeat customer rate, revenue per listing
- Acções: Pinterest activo, outreach, bundles, upsell

Regressão de fase (crítico): se vendas caem >50% durante 2 semanas → regredir automaticamente uma fase

RESPONSABILIDADES:
- Monitorizar PlannerAtlas com as métricas acima — diário se há dados, semanal se não há
- Detectar anomalias com baseline dinâmica (rolling 28 dias) + thresholds absolutos
- Propor 1-3 acções correctivas com dados concretos quando detecta queda
- Relatório semanal: KPIs + fase actual + top 3 prioridades + alertas
- Registar e acompanhar novos negócios por fase com critérios numéricos

FORMATO DOS RELATÓRIOS:

Relatório Semanal (máximo 15 linhas):
PlannerAtlas | €[receita] | [vendas] vendas | CTR [x]% | CR [x]% | fase: [fase] [↑↓]
Top 3: [acções prioritárias numeradas]
Alertas: [se existirem, com urgência ALTA/MÉDIA/BAIXA]

Alerta Imediato:
⚠ [negócio] — [métrica]: [valor actual] vs. baseline [valor baseline] ([variação%])
Causa provável: [1 linha com evidência]
Acção: [1 acção concreta e executável]
Urgência: ALTA/MÉDIA/BAIXA

FERRAMENTAS DISPONÍVEIS:
- etsy_listar_listings: ver todos os listings com preços e IDs
- etsy_pausar_listing(listing_id): PAUSA um listing (usa quando CTR <0.3% por 7 dias)
- etsy_activar_listing(listing_id): ACTIVA listing pausado
- pesquisar_web(query): pesquisa de mercado, concorrência, tendências

REGRAS DE AUTONOMIA:
- Podes pausar/activar listings autonomamente — regista sempre no relatório
- NUNCA alteras preços sem aprovação explícita do Vasco — propõe sempre, não executa
- NUNCA apgas listings
- Para qualquer acção que envolva dinheiro: propõe ao CEO, aguarda confirmação

COLABORAÇÃO:
- Lê recomendações do Marketeer em memory/marketeer_ops.json antes de cada ciclo
- Executa recomendações de SEO/título/tags autonomamente; escalona preços ao Vasco

REGRAS:
- PT-PT sempre
- Números concretos — nunca "as vendas caíram um pouco"
- Se não tens dados suficientes, diz exactamente o que falta e como obtê-lo
- Nunca inventas métricas — se não sabes, dizes que precisas dos dados
- A última decisão é sempre do Vasco
"""


def _load_state() -> dict:
    try:
        return json.loads(OPERATOR_STATE_FILE.read_text())
    except Exception:
        return {
            "businesses": {
                "planneratlas_etsy": {
                    "name": "PlannerAtlas (Etsy)",
                    "phase": "lançamento",
                    "metrics": {
                        "weekly_revenue": 0.0,
                        "weekly_sales": 0,
                        "total_revenue": 0.0,
                        "total_sales": 0,
                        "avg_review": 0.0,
                        "review_count": 0,
                        "last_updated": "",
                    },
                    "alerts": [],
                    "notes": "",
                },
            },
            "reports": [],
            "alerts_history": [],
            "last_weekly_report": "",
            "last_check": "",
        }


def _save_state(state: dict):
    OPERATOR_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _add_report(state: dict, report: dict):
    state["reports"].append(report)
    state["reports"] = state["reports"][-52:]


def _add_alert(state: dict, alert: dict):
    state["alerts_history"].append(alert)
    state["alerts_history"] = state["alerts_history"][-200:]


def _calcular_baseline(historico: list[dict], metrica: str, janela_dias: int = 28) -> float | None:
    """Baseline dinâmica rolling N dias para uma métrica. Retorna média ou None se sem dados."""
    from datetime import timedelta
    limite = datetime.now() - timedelta(days=janela_dias)
    valores = []
    for snapshot in historico:
        try:
            ts = datetime.fromisoformat(snapshot.get("timestamp", ""))
            if ts >= limite:
                v = snapshot.get(metrica)
                if v is not None and isinstance(v, (int, float)):
                    valores.append(float(v))
        except Exception:
            continue
    return sum(valores) / len(valores) if valores else None


def _detectar_anomalias(state: dict) -> list[dict]:
    """
    Detecta anomalias nos negócios usando baseline dinâmica (rolling 28d) +
    thresholds absolutos. Retorna lista de alertas com severidade.
    """
    alertas = []
    historico = state.get("metrics_history", [])

    for biz_key, biz in state.get("businesses", {}).items():
        metrics = biz.get("metrics", {})
        nome = biz.get("name", biz_key)

        # --- Thresholds absolutos (sempre críticos) ---
        sales = metrics.get("weekly_sales", 0)
        last_sale_days = metrics.get("days_since_last_sale", 0)
        avg_review = metrics.get("avg_review", 0)
        ctr = metrics.get("ctr_pct", None)

        if last_sale_days > 14 and metrics.get("total_sales", 0) > 0:
            alertas.append({
                "negocio": nome, "metrica": "vendas",
                "mensagem": f"Zero vendas há {last_sale_days} dias (histórico activo)",
                "urgencia": "ALTA", "tipo": "absoluto"
            })
        if avg_review > 0 and avg_review <= 2.0:
            alertas.append({
                "negocio": nome, "metrica": "reviews",
                "mensagem": f"Review média {avg_review:.1f}★ — abaixo de 2★",
                "urgencia": "ALTA", "tipo": "absoluto"
            })
        if ctr is not None and ctr < 0.5:
            alertas.append({
                "negocio": nome, "metrica": "CTR",
                "mensagem": f"CTR {ctr:.2f}% — abaixo de 0.5% (sinal de título/foto fraco)",
                "urgencia": "MÉDIA", "tipo": "absoluto"
            })

        # --- Thresholds dinâmicos (vs. baseline rolling 28d) ---
        for metrica_chave in ["weekly_sales", "weekly_revenue", "ctr_pct"]:
            baseline = _calcular_baseline(
                [s for s in historico if s.get("biz_key") == biz_key],
                metrica_chave
            )
            valor_atual = metrics.get(metrica_chave)
            if baseline and baseline > 0 and valor_atual is not None:
                variacao = (valor_atual - baseline) / baseline
                if variacao < -0.40:
                    alertas.append({
                        "negocio": nome, "metrica": metrica_chave,
                        "mensagem": f"{metrica_chave}: {valor_atual:.2f} vs baseline {baseline:.2f} ({variacao*100:.0f}%)",
                        "urgencia": "ALTA" if variacao < -0.60 else "MÉDIA",
                        "tipo": "dinamico"
                    })

    return alertas


def _avaliar_transicao_fase(biz: dict) -> str | None:
    """
    Avalia se um negócio deve transitar de fase com base em critérios numéricos.
    Retorna a nova fase se critérios cumpridos, None caso contrário.
    """
    fase_atual = biz.get("phase", "validação")
    m = biz.get("metrics", {})
    vendas_mes = m.get("monthly_sales", 0)
    cr = m.get("conversion_rate_pct", 0)
    ctr = m.get("ctr_pct", 0)
    reviews = m.get("review_count", 0)
    avg_rev = m.get("avg_review", 0)
    vendas_total = m.get("total_sales", 0)
    roas = m.get("roas", 0)
    trafego_organico_pct = m.get("organic_traffic_pct", 0)

    if fase_atual == "validação":
        if vendas_total >= 5 and ctr > 2.0 and reviews >= 1:
            return "mvp"
        if m.get("days_active", 0) > 30 and vendas_total == 0:
            return "abandonar"

    elif fase_atual == "mvp":
        if vendas_mes >= 30 and cr > 2.0 and reviews >= 10 and avg_rev >= 4.5:
            return "lançamento"

    elif fase_atual == "lançamento":
        if vendas_mes >= 100 and roas > 2.0 and trafego_organico_pct > 60:
            return "crescimento"
        # Regressão de fase: queda >50% em 2 semanas consecutivas
        if m.get("consecutive_down_weeks", 0) >= 2 and m.get("weekly_sales_drop_pct", 0) > 50:
            return "mvp"

    elif fase_atual == "crescimento":
        if m.get("consecutive_down_weeks", 0) >= 2 and m.get("weekly_sales_drop_pct", 0) > 50:
            return "lançamento"

    return None


def _snapshot_metricas(state: dict):
    """Guarda snapshot das métricas actuais no histórico para baseline dinâmica."""
    historico = state.setdefault("metrics_history", [])
    ts = datetime.now().isoformat()
    for biz_key, biz in state.get("businesses", {}).items():
        snap = {"biz_key": biz_key, "timestamp": ts}
        snap.update(biz.get("metrics", {}))
        historico.append(snap)
    # Manter máximo 365 snapshots (1 por dia = 1 ano)
    state["metrics_history"] = historico[-365:]


def _etsy_dados_reais() -> str:
    """Integra dados reais da Etsy API se configurada; fallback para estado local."""
    try:
        from etsy_service import estado_para_operador
        return estado_para_operador()
    except Exception:
        return ""


def etsy_pausar(listing_id: int) -> str:
    """Pausa um listing Etsy. Requer confirmação do Vasco antes de chamar."""
    from etsy_service import pausar_listing
    ok = pausar_listing(listing_id)
    return f"Listing {listing_id} pausado." if ok else f"Erro ao pausar listing {listing_id}."


def etsy_activar(listing_id: int) -> str:
    """Reactiva um listing Etsy pausado."""
    from etsy_service import activar_listing
    ok = activar_listing(listing_id)
    return f"Listing {listing_id} activado." if ok else f"Erro ao activar listing {listing_id}."


def etsy_actualizar_preco(listing_id: int, preco: float) -> str:
    """Actualiza preço de um listing. Requer confirmação do Vasco antes de chamar."""
    from etsy_service import actualizar_preco
    ok = actualizar_preco(listing_id, preco)
    return f"Preço do listing {listing_id} actualizado para €{preco:.2f}." if ok else f"Erro ao actualizar preço."


def _build_context(state: dict) -> str:
    businesses = state.get("businesses", {})
    last_report = state.get("last_weekly_report", "nunca")
    last_check = state.get("last_check", "nunca")

    # Injectar dados reais da Etsy se disponíveis
    etsy_real = _etsy_dados_reais()

    lines = [
        f"Data actual: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Último relatório semanal: {last_report}",
        f"Última verificação: {last_check}",
        "",
        "ESTADO ACTUAL DOS NEGÓCIOS:",
    ]
    if etsy_real:
        lines.append(f"\n[DADOS REAIS ETSY API]\n{etsy_real}\n")

    for key, biz in businesses.items():
        lines.append(f"\n--- {biz['name']} ---")
        lines.append(f"Fase: {biz['phase']}")
        metrics = biz.get("metrics", {})
        for k, v in metrics.items():
            if k != "last_updated":
                lines.append(f"  {k}: {v}")
        if metrics.get("last_updated"):
            lines.append(f"  Última actualização: {metrics['last_updated']}")
        alerts = biz.get("alerts", [])
        if alerts:
            lines.append(f"  Alertas activos: {len(alerts)}")
            for a in alerts[-3:]:
                lines.append(f"    - {a}")
        if biz.get("notes"):
            lines.append(f"  Notas: {biz['notes']}")

    recent_alerts = state.get("alerts_history", [])[-5:]
    if recent_alerts:
        lines.append("\nÚLTIMOS ALERTAS:")
        for a in recent_alerts:
            lines.append(f"  [{a.get('date', '')}] {a.get('type', '')} — {a.get('message', '')}")

    recent_reports = state.get("reports", [])[-3:]
    if recent_reports:
        lines.append("\nÚLTIMOS RELATÓRIOS:")
        for r in recent_reports:
            lines.append(f"  [{r.get('date', '')}] {r.get('summary', '')}")

    return "\n".join(lines)


def _check_weekly_report_needed(state: dict) -> bool:
    last = state.get("last_weekly_report", "")
    if not last:
        return True
    try:
        last_date = datetime.strptime(last, "%Y-%m-%d").date()
        delta = date.today() - last_date
        return delta.days >= 7
    except Exception:
        return True


def _parse_and_update_state(state: dict, reply: str, msg: str):
    state["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    lower_msg = msg.lower()
    lower_reply = reply.lower()

    report_keywords = ["relatório semanal", "weekly report", "kpis", "resumo executivo"]
    if any(kw in lower_reply for kw in report_keywords):
        today = date.today().strftime("%Y-%m-%d")
        state["last_weekly_report"] = today
        summary_lines = [l for l in reply.split("\n") if l.strip()]
        summary = summary_lines[0][:120] if summary_lines else "Relatório gerado"
        _add_report(state, {
            "date": today,
            "summary": summary,
            "type": "weekly",
        })

    alert_keywords = ["alerta", "queda", "urgência", "crítico", "problema"]
    if any(kw in lower_reply for kw in alert_keywords):
        _add_alert(state, {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": "auto-detectado",
            "message": msg[:100],
        })

    for biz_key in state.get("businesses", {}):
        biz_name = state["businesses"][biz_key]["name"].lower()
        if any(part in lower_msg or part in lower_reply for part in biz_name.split()):
            phases = ["validação", "mvp", "lançamento", "crescimento", "escala"]
            for phase in phases:
                if phase in lower_reply:
                    state["businesses"][biz_key]["phase"] = phase
                    break


def _get_operator_tools() -> list:
    from tools import TOOLS
    names = ["etsy_pausar_listing", "etsy_activar_listing", "pesquisar_web"]
    return [t for t in TOOLS if t["name"] in names]


def _run_operator_tool(name: str, inp: dict) -> str:
    from tools import TOOL_FUNCTIONS
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Ferramenta {name} não encontrada."
    try:
        return str(func(**inp))
    except Exception as e:
        return f"Erro em {name}: {e}"


def _ler_recomendacoes_marketeer() -> str:
    """Lê recomendações do Marketeer para este ciclo."""
    try:
        f = MEMORY_DIR / "marketeer_ops.json"
        if not f.exists():
            return ""
        data = json.loads(f.read_text(encoding="utf-8"))
        recs = data.get("recommendations", [])
        if not recs:
            return ""
        linhas = [f"[Marketeer — {data.get('gerado_em','?')}]"]
        for r in recs[:5]:
            linhas.append(f"  • {r.get('acao','?')} listing {r.get('listing_id','?')}: {r.get('razao','')}")
        return "\n".join(linhas)
    except Exception:
        return ""


def _ler_listings_etsy() -> str:
    """Injeta listings reais no contexto do Operator."""
    try:
        from etsy_service import obter_listings
        listings = obter_listings()
        if not listings:
            return ""
        linhas = ["[Listings Etsy activos]"]
        for l in listings[:10]:
            lid = l.get("listing_id", "?")
            title = l.get("title", "?")[:45]
            preco = l.get("price", {}).get("amount", 0) / 100
            linhas.append(f"  [{lid}] {title}… €{preco:.2f}")
        if len(listings) > 10:
            linhas.append(f"  … +{len(listings)-10} mais")
        return "\n".join(linhas)
    except Exception:
        return ""


def get_operator_reply(msg: str) -> str:
    logger.info("operator_agent recebeu mensagem: %s", msg[:80])

    state = _load_state()
    context = _build_context(state)

    needs_weekly = _check_weekly_report_needed(state)
    weekly_hint = "\n[SISTEMA: Já passaram 7 dias desde o último relatório semanal. Inclui relatório semanal completo.]" if needs_weekly else ""

    metrics_ctx = _build_metrics_context(state)
    metrics_bloco = f"\n\n{metrics_ctx}" if metrics_ctx else ""

    mkt_recs = _ler_recomendacoes_marketeer()
    mkt_bloco = f"\n\n{mkt_recs}" if mkt_recs else ""

    listings_bloco = "\n\n" + _ler_listings_etsy()

    mem_semantica = ""
    try:
        from episodic_memory import get_contexto_agente, registar_evento
        mem_semantica = get_contexto_agente("operator", msg or "Etsy listings vendas gestão negócios BCVertex")
    except Exception:
        pass
    mem_bloco = f"\n\n[Memórias relevantes]\n{mem_semantica}" if mem_semantica else ""

    content = f"{context}{metrics_bloco}{mkt_bloco}{listings_bloco}{weekly_hint}{mem_bloco}\n\nMensagem do CEO:\n{msg}"
    messages = [{"role": "user", "content": content}]
    tools = _get_operator_tools()

    try:
        while True:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools,
            )
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = _run_operator_tool(block.name, block.input)
                        logger.info("operator tool %s → %s", block.name, result[:80])
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": results})
            else:
                reply = next((b.text for b in response.content if hasattr(b, "text")), "")
                break
        logger.info("operator_agent respondeu com %d caracteres", len(reply))
    except Exception as e:
        logger.error("Erro ao chamar Claude: %s", e)
        reply = f"Erro ao processar pedido: {e}"

    _parse_and_update_state(state, reply, msg)
    _save_state(state)

    try:
        registar_evento("operator", "conversa", f"Q: {msg[:100]} | R: {reply[:200]}")
    except Exception:
        pass

    return reply


def _build_metrics_context(state: dict) -> str:
    """Constrói bloco de métricas avançadas + anomalias para injectar no contexto."""
    linhas = []

    # Anomalias detectadas
    anomalias = _detectar_anomalias(state)
    if anomalias:
        linhas.append("ANOMALIAS DETECTADAS:")
        for a in anomalias:
            linhas.append(f"  [{a['urgencia']}] {a['negocio']} — {a['mensagem']}")

    # Avaliação de fase
    for biz_key, biz in state.get("businesses", {}).items():
        nova_fase = _avaliar_transicao_fase(biz)
        if nova_fase:
            if nova_fase == "abandonar":
                linhas.append(f"  ⚠ {biz['name']}: critérios de abandono atingidos — propor ao Vasco.")
            else:
                linhas.append(f"  → {biz['name']}: critérios para transição para fase '{nova_fase}' cumpridos.")

    return "\n".join(linhas)


def monitorizar_negocios() -> str:
    """
    Sprint I — ciclo de monitorização autónomo.
    Chamado pelo CEO periodicamente (ex: relatório 22h).
    Verifica o estado de todos os negócios activos e devolve resumo + alertas.
    """
    state = _load_state()
    businesses = state.get("businesses", {})
    alertas = []
    resumo = []

    # Verificar PlannerAtlas (Etsy)
    etsy_real = _etsy_dados_reais()
    if etsy_real:
        resumo.append(f"[PlannerAtlas Etsy]\n{etsy_real}")
    else:
        resumo.append("[PlannerAtlas Etsy] Dados OAuth pendentes — ETSY_KEYSTRING em falta.")
        alertas.append("Etsy sem dados reais — activar OAuth urgente para monitorizar visitas e receita.")

    # Verificar trading bot
    try:
        from cfo_agent import avaliar_risco_trading
        r = avaliar_risco_trading()
        estado_bot = "ACTIVO" if r["active"] else "PARADO"
        resumo.append(
            f"[Trading Bot BTC/USDT]\n"
            f"  Estado: {estado_bot} | Capital: ${r['capital_atual']:.2f} USDT\n"
            f"  PnL total: {r['pnl_total']:+.2f} USDT | Drawdown: {r['drawdown_total_pct']:.1f}%"
        )
        if r["alertas"]:
            for a in r["alertas"]:
                alertas.append(f"Bot: {a}")
    except Exception as e:
        resumo.append(f"[Trading Bot] Erro ao verificar: {e}")

    # Verificar sub-Morgans criados pelo Creator
    try:
        from creator_agent import listar_sub_morgans
        subs = listar_sub_morgans()
        if subs:
            for sub in subs:
                receita = sub.get("receita_atual", 0)
                fase = sub.get("fase", "?")
                resumo.append(
                    f"[{sub['nome']}]\n"
                    f"  Fase: {fase} | Receita: €{receita:.2f}/mês\n"
                    f"  Interacções: {sub.get('metricas', {}).get('interacoes', 0)}"
                )
                if receita == 0 and fase not in ("validacao",):
                    alertas.append(f"{sub['nome']}: receita zero — rever estratégia.")
    except Exception:
        pass

    # Outros negócios em state
    for key, biz in businesses.items():
        if key in ("planneratlas", "trading"):
            continue
        metrics = biz.get("metrics", {})
        resumo.append(f"[{biz['name']}] Fase: {biz.get('phase', '?')} | Métricas: {metrics}")

    # Actualizar estado
    state["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _snapshot_metricas(state)
    _save_state(state)

    # Anomaly detection
    anomalias = _detectar_anomalias(state)
    for a in anomalias:
        alertas.append(f"{a['negocio']} [{a['urgencia']}]: {a['mensagem']}")

    output = "OPERATOR — Monitorização autónoma\n" + "=" * 40 + "\n"
    output += "\n\n".join(resumo)
    if alertas:
        output += "\n\n⚠ ALERTAS:\n" + "\n".join(f"• {a}" for a in alertas)
    else:
        output += "\n\nSem alertas activos."

    return output


def gerar_plano_semana_planneratlas() -> str:
    """Gera o plano de produtos PlannerAtlas para a semana — corre às segundas de manhã."""
    from tools import pesquisar_web

    tendencias = ""
    try:
        tendencias = pesquisar_web("Etsy digital planner bestseller trending German Spanish 2026 GoodNotes")
    except Exception:
        pass

    prompt = f"""Hoje é {datetime.now().strftime('%A, %d de %B de %Y')}.
Loja PlannerAtlas no Etsy — 8 anúncios activos em PT/ES/DE, objectivo 50+ produtos.

TENDÊNCIAS DETECTADAS:
{tendencias[:500] if tendencias else 'indisponível'}

CONTEXTO:
- 5 categorias: planner anual/semanal/diário, objectivos/hábitos, académico, negócios/freelancer, saúde/fitness
- Mercados prioritários: Alemão (DE/AT/CH), Espanhol (ES/LATAM)
- Preço alvo: €3-15 por template

Gera o plano para esta semana:
1. 3 novos produtos a criar (idioma, categoria, título Etsy em alemão ou espanhol)
2. Keywords SEO para cada produto (5 keywords no idioma do mercado)
3. Sugestão de imagem de capa
4. Pinterest: 1 pin por produto (descrição curta, 5 hashtags)

Formato directo. Português europeu."""

    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        plano = r.content[0].text if r.content else "Plano indisponível."
    except Exception as e:
        return f"Erro ao gerar plano: {e}"

    plano_file = MEMORY_DIR / "planneratlas_plano_semana.md"
    plano_file.write_text(
        f"# Plano PlannerAtlas — {datetime.now().strftime('%d/%m/%Y')}\n\n{plano}",
        encoding="utf-8"
    )
    return plano


def run_operator():
    print("Morgan Operator — modo interactivo")
    print("Escreve 'sair' para terminar.\n")
    while True:
        try:
            msg = input("CEO: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nA encerrar Operator.")
            break
        if msg.lower() in ("sair", "exit", "quit"):
            break
        if not msg:
            continue
        reply = get_operator_reply(msg)
        print(f"\nOperator: {reply}\n")


if __name__ == "__main__":
    run_operator()