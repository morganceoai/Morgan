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
- Alertas operacionais (queda de vendas, review negativa): reportar sempre, mesmo com dados parciais
- Recomendações de produto/preço: só com dados de pelo menos 2 semanas
- Mudança de fase do negócio: só quando 3+ métricas confirmam a transição

NEGÓCIOS ACTIVOS:

1. PlannerAtlas (Etsy) — fase: lançamento
   - 8 listings activos, planners digitais PT/ES/DE
   - Métricas chave: vendas semanais, receita, reviews, tráfego, conversão
   - Alertas: queda vendas >20%, review <4★, 0 visitas em 48h

2. Futuros Negócios (aprovados pelo Scout)
   - Registas quando o CEO introduz um novo negócio aprovado
   - Fases: validação → MVP → lançamento → crescimento → escala

RESPONSABILIDADES:
- Monitorizar PlannerAtlas: vendas, receita, reviews, tráfego, stock de variantes
- Detectar e reportar anomalias imediatamente (não esperar relatório semanal)
- Propor 1-3 acções correctivas concretas quando há queda de desempenho
- Relatório semanal com KPIs + top 3 prioridades + alertas activos
- Registar novos negócios e acompanhar progressão de fase

FORMATO DOS RELATÓRIOS:

Relatório Semanal (máximo 15 linhas):
[negócio] receita | vendas | reviews | fase | tendência ↑↓
Top 3 esta semana: [acções prioritárias]
Alertas: [se existirem]

Alerta Imediato:
⚠ [negócio] — [métrica]: [valor] ([variação%])
Causa provável: [1 linha]
Acção: [1 acção concreta]
Urgência: ALTA/MÉDIA/BAIXA

REGRAS:
- PT-PT sempre
- Números concretos — nunca "as vendas caíram um pouco"
- Se não tens dados, diz exactamente o que falta e porquê
- Nunca inventas métricas
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


def _etsy_dados_reais() -> str:
    """Integra dados reais da Etsy API se configurada; fallback para estado local."""
    try:
        from etsy_service import estado_para_operador
        return estado_para_operador()
    except Exception:
        return ""


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


def get_operator_reply(msg: str) -> str:
    logger.info("operator_agent recebeu mensagem: %s", msg[:80])

    state = _load_state()
    context = _build_context(state)

    needs_weekly = _check_weekly_report_needed(state)
    weekly_hint = ""
    if needs_weekly:
        weekly_hint = "\n[SISTEMA: Já passaram 7 dias desde o último relatório semanal. Considera incluir um relatório semanal completo na tua resposta se for adequado.]"

    messages = [
        {
            "role": "user",
            "content": f"{context}\n{weekly_hint}\n\nMensagem do CEO:\n{msg}",
        }
    ]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
        logger.info("operator_agent respondeu com %d caracteres", len(reply))
    except Exception as e:
        logger.error("Erro ao chamar Claude: %s", e)
        reply = f"Erro ao processar pedido: {e}"

    _parse_and_update_state(state, reply, msg)
    _save_state(state)

    return reply


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
    _save_state(state)

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