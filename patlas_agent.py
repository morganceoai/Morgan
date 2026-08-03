"""
PAtlas — Agente autónomo da loja PlannerAtlas (Etsy)
Monitoriza vendas, CTR, listings e alertas sem ser chamado.
Reporta ao CEO e ao Operator proactivamente.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MEMORY_DIR = Path(__file__).parent / "memory"
PATLAS_STATE_FILE = MEMORY_DIR / "patlas_state.json"

# ── Thresholds (alinhados com operator_agent.py) ─────────────────────────────
ALERTA_SEM_VENDAS_DIAS = 14
ALERTA_CTR_MIN = 0.005          # 0.5%
ALERTA_QUEDA_BASELINE = 0.40    # queda >40% vs. rolling 28 dias
ALERTA_REVIEW_MIN = 2.0         # review ≤ 2★


def _load_state() -> dict:
    if PATLAS_STATE_FILE.exists():
        return json.loads(PATLAS_STATE_FILE.read_text())
    estado = {
        "nome": "PlannerAtlas",
        "plataforma": "Etsy",
        "fase": "lançamento",
        "listings_activos": 0,
        "vendas_total": 0,
        "vendas_28d": [],        # lista de {data, valor} para baseline rolling
        "ctr_medio": 0.0,
        "conversion_rate": 0.0,
        "review_medio": 0.0,
        "receita_total": 0.0,
        "ultima_venda": "",
        "ultima_verificacao": "",
        "alertas_activos": [],
        "etsy_configurado": False,
        "criado_em": datetime.now().isoformat(),
    }
    PATLAS_STATE_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False))
    return estado


def _save_state(state: dict):
    PATLAS_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _notificar_ceo(titulo: str, corpo: str, urgente: bool = False):
    try:
        from episodic_memory import registar_evento
        prefixo = "🚨 URGENTE" if urgente else "🛍️ PAtlas"
        registar_evento("ceo", "patlas_alerta" if urgente else "patlas_update",
                        f"{prefixo} — {titulo}: {corpo}")
        registar_evento("operator", "patlas_update", f"{titulo}: {corpo}")
    except Exception:
        pass
    try:
        from ceo_events import publicar
        nivel = "critico" if urgente else "aviso"
        publicar("patlas", "alerta" if urgente else "update", f"{titulo}: {corpo}", nivel=nivel)
    except Exception:
        pass
    if urgente:
        try:
            from push_service import send_push
            send_push(title=f"Morgan — {titulo}", body=corpo[:160], url="/pwa/")
        except Exception:
            pass


def obter_metricas() -> dict:
    """Vai buscar métricas reais ao Etsy via etsy_service."""
    state = _load_state()

    try:
        from etsy_service import is_configured, resumo_loja, obter_vendas
        if not is_configured():
            state["etsy_configurado"] = False
            _save_state(state)
            return {"ok": False, "erro": "Etsy OAuth não configurado — ETSY_KEYSTRING em falta"}

        state["etsy_configurado"] = True
        resumo = resumo_loja()
        vendas_30d = obter_vendas(dias=30)

        state["listings_activos"] = resumo.get("listings_activos", state["listings_activos"])
        state["vendas_total"] = resumo.get("vendas_total", state["vendas_total"])
        state["receita_total"] = resumo.get("receita_total", state["receita_total"])
        state["ultima_verificacao"] = datetime.now().isoformat()

        if vendas_30d:
            state["ultima_venda"] = vendas_30d[0].get("data", "") if vendas_30d else state["ultima_venda"]
            # baseline rolling 28 dias
            state["vendas_28d"] = vendas_30d[:28]

        _save_state(state)
        return {"ok": True, "resumo": resumo, "vendas_30d": len(vendas_30d)}

    except Exception as e:
        return {"ok": False, "erro": str(e)}


def verificar_anomalias() -> list[str]:
    """Detecção proactiva de problemas. Alerta CEO imediatamente se crítico."""
    state = _load_state()
    alertas = []
    agora = datetime.now()

    # Etsy não configurado — alerta de setup
    if not state.get("etsy_configurado"):
        alertas.append("Etsy OAuth não configurado — métricas reais indisponíveis")
        state["alertas_activos"] = alertas
        _save_state(state)
        return alertas

    # Sem vendas há demasiado tempo
    if state.get("ultima_venda"):
        ultima = datetime.fromisoformat(state["ultima_venda"])
        dias_sem_venda = (agora - ultima).days
        if dias_sem_venda >= ALERTA_SEM_VENDAS_DIAS:
            alertas.append(f"Sem vendas há {dias_sem_venda} dias — rever produto ou SEO")

    # CTR abaixo do mínimo
    ctr = state.get("ctr_medio", 0.0)
    if ctr > 0 and ctr < ALERTA_CTR_MIN:
        alertas.append(f"CTR médio {ctr:.1%} — abaixo de 0.5% (thumbnails ou títulos a falhar)")

    # Review baixo
    review = state.get("review_medio", 0.0)
    if review > 0 and review <= ALERTA_REVIEW_MIN:
        alertas.append(f"Review médio {review:.1f}★ — verificar qualidade do produto")

    # Queda vs. baseline rolling 28 dias
    vendas_28d = state.get("vendas_28d", [])
    if len(vendas_28d) >= 14:
        baseline = len(vendas_28d)
        metade_recente = len([v for v in vendas_28d[:14]])
        metade_antiga = len([v for v in vendas_28d[14:]])
        if metade_antiga > 0:
            queda = (metade_antiga - metade_recente) / metade_antiga
            if queda >= ALERTA_QUEDA_BASELINE:
                alertas.append(f"Queda de {queda:.0%} nas últimas 2 semanas vs. baseline — investigar")

    # Notificar CEO para alertas novos críticos
    alertas_anteriores = set(state.get("alertas_activos", []))
    for alerta in alertas:
        if alerta not in alertas_anteriores:
            critico = any(k in alerta for k in ["Sem vendas", "Review", "Queda"])
            _notificar_ceo("PAtlas — anomalia", alerta, urgente=critico)

    state["alertas_activos"] = alertas
    _save_state(state)
    return alertas


def ciclo_diario() -> str:
    """
    Corre automaticamente todos os dias.
    1. Actualiza métricas do Etsy
    2. Detecta anomalias
    3. Reporta ao CEO/Operator se há alertas
    """
    state = _load_state()
    metricas = obter_metricas()
    alertas = verificar_anomalias()

    estado_str = relatorio_para_operator()

    if alertas:
        _notificar_ceo(
            "PAtlas — resumo diário com alertas",
            f"{len(alertas)} alerta(s): {alertas[0]}",
            urgente=False
        )

    return estado_str


def relatorio_para_operator() -> str:
    """Chamado pelo Operator para monitorização. Retorna estado actual."""
    state = _load_state()
    alertas = state.get("alertas_activos", [])

    ultima_venda = state.get("ultima_venda", "")
    if ultima_venda:
        dias = (datetime.now() - datetime.fromisoformat(ultima_venda)).days
        ultima_str = f"há {dias} dias" if dias > 0 else "hoje"
    else:
        ultima_str = "desconhecida"

    linhas = [
        f"🛍️ PLANNERATLAS — Relatório",
        f"Fase: {state['fase']} | Listings: {state['listings_activos']}",
        f"Vendas total: {state['vendas_total']} | Receita: €{state['receita_total']:.2f}",
        f"CTR: {state.get('ctr_medio', 0):.1%} | CR: {state.get('conversion_rate', 0):.1%}",
        f"Última venda: {ultima_str}",
        f"Etsy OAuth: {'✅' if state.get('etsy_configurado') else '⏳ pendente'}",
    ]
    if alertas:
        linhas.append(f"⚠️ {len(alertas)} alerta(s): {' | '.join(alertas[:2])}")
    else:
        linhas.append("✅ Sem alertas")

    return "\n".join(linhas)


def propor_accoes_correctivas() -> str:
    """Usa Claude para propor acções baseadas nos dados actuais."""
    state = _load_state()
    alertas = state.get("alertas_activos", [])
    if not alertas:
        return "Sem alertas activos — nenhuma acção correctiva necessária."

    try:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env")
        client = anthropic.Anthropic()

        prompt = f"""És o Morgan Operator a analisar a loja Etsy PlannerAtlas.

Estado actual:
- Fase: {state['fase']}
- Listings activos: {state['listings_activos']}
- Vendas total: {state['vendas_total']}
- Receita total: €{state['receita_total']:.2f}
- CTR médio: {state.get('ctr_medio', 0):.1%}

Alertas detectados:
{chr(10).join(f'- {a}' for a in alertas)}

Propõe 1-3 acções correctivas concretas e accionáveis. Sem rodeios, sem explicações longas.
Formato: cada acção em 1 linha, começando com verbo."""

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"Erro ao gerar acções: {e}"


if __name__ == "__main__":
    print(relatorio_para_operator())
    print()
    anomalias = verificar_anomalias()
    if anomalias:
        print("Anomalias:", anomalias)
        print()
        print(propor_accoes_correctivas())
