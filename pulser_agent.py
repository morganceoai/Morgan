"""
Pulser — Agente autónomo da newsletter The AI Pulse BC
Actua por iniciativa própria: cura, rascunha, monitoriza, alerta o CEO.
Não precisa de ser chamado — tem ciclo de vida próprio.
"""
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MEMORY_DIR = Path(__file__).parent / "memory"
PULSER_STATE_FILE = MEMORY_DIR / "pulser_state.json"

# ── Thresholds de alerta ─────────────────────────────────────────────────────
ALERTA_SEM_DRAFT_DIAS = 14
ALERTA_OPEN_RATE_MIN = 0.30        # 30% — abaixo disto subject lines estão a falhar
ALERTA_CRESCIMENTO_SEMANAL_MIN = 5 # menos de 5 novos subs/semana após 60 dias → rever SEO


def _load_state() -> dict:
    if PULSER_STATE_FILE.exists():
        return json.loads(PULSER_STATE_FILE.read_text())
    estado = {
        "nome": "The AI Pulse BC",
        "fase": "setup",
        "subscribers": 0,
        "subscribers_semana_passada": 0,
        "open_rate": 0.0,
        "emails_enviados": 0,
        "ultimo_draft_criado": "",
        "ultimo_envio": "",
        "receita_total": 0.0,
        "alertas_activos": [],
        "ciclos_executados": 0,
        "criado_em": datetime.now().isoformat(),
    }
    PULSER_STATE_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False))
    return estado


def _save_state(state: dict):
    PULSER_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _notificar_ceo(titulo: str, corpo: str, urgente: bool = False):
    """Publica evento no CEO sem passar pelo briefing."""
    try:
        from episodic_memory import registar_evento
        prefixo = "🚨 URGENTE" if urgente else "📰 Pulser"
        registar_evento("ceo", "pulser_alerta" if urgente else "pulser_update",
                        f"{prefixo} — {titulo}: {corpo}")
    except Exception:
        pass
    try:
        from ceo_events import publicar
        nivel = "critico" if urgente else "aviso"
        publicar("pulser", "alerta" if urgente else "update", f"{titulo}: {corpo}", nivel=nivel)
    except Exception:
        pass
    if urgente:
        try:
            from push_service import send_push
            send_push(title=f"Morgan — {titulo}", body=corpo[:160], url="/pwa/")
        except Exception:
            pass


def _detectar_fase(state: dict) -> str:
    subs = state.get("subscribers", 0)
    receita = state.get("receita_total", 0.0)
    if receita > 2000:
        return "escala"
    if subs >= 1000:
        return "monetizacao"
    if subs >= 100:
        return "crescimento"
    return "setup"


def obter_metricas() -> dict:
    """Vai buscar métricas reais ao Beehiiv e actualiza estado."""
    from newsletter_agent import obter_stats
    stats = obter_stats()
    if "erro" in stats:
        return {"ok": False, "erro": stats["erro"]}

    state = _load_state()
    state["subscribers_semana_passada"] = state.get("subscribers", 0)
    state["subscribers"] = stats.get("subscribers", state["subscribers"])
    state["emails_enviados"] = stats.get("emails_enviados", state["emails_enviados"])
    state["fase"] = _detectar_fase(state)
    _save_state(state)
    return {"ok": True, **stats}


def verificar_anomalias() -> list[str]:
    """Detecta problemas proactivamente e notifica o CEO se necessário."""
    state = _load_state()
    alertas = []
    agora = datetime.now()

    # Sem draft há demasiado tempo
    if state.get("ultimo_draft_criado"):
        ultimo = datetime.fromisoformat(state["ultimo_draft_criado"])
        dias_sem_draft = (agora - ultimo).days
        if dias_sem_draft >= ALERTA_SEM_DRAFT_DIAS:
            alertas.append(f"Sem rascunho há {dias_sem_draft} dias — newsletter parada")

    # Open rate abaixo do mínimo (só relevante com dados reais)
    open_rate = state.get("open_rate", 0.0)
    if open_rate > 0 and open_rate < ALERTA_OPEN_RATE_MIN:
        alertas.append(f"Open rate {open_rate:.0%} — abaixo de {ALERTA_OPEN_RATE_MIN:.0%} (subject lines a falhar?)")

    # Crescimento estagnado após fase de crescimento
    if state.get("fase") in ("crescimento", "monetizacao"):
        crescimento = state.get("subscribers", 0) - state.get("subscribers_semana_passada", 0)
        if crescimento < ALERTA_CRESCIMENTO_SEMANAL_MIN:
            alertas.append(f"Crescimento semanal: +{crescimento} subs — abaixo de {ALERTA_CRESCIMENTO_SEMANAL_MIN} (rever SEO/Boosts)")

    # Notificar CEO se há alertas novos
    alertas_anteriores = set(state.get("alertas_activos", []))
    alertas_novos = [a for a in alertas if a not in alertas_anteriores]
    for alerta in alertas_novos:
        _notificar_ceo("Pulser — anomalia detectada", alerta, urgente=True)

    state["alertas_activos"] = alertas
    _save_state(state)
    return alertas


def ciclo_semanal() -> str:
    """
    Corre automaticamente ao domingo 18h.
    1. Actualiza métricas
    2. Detecta anomalias
    3. Cura conteúdo e cria rascunho no Beehiiv
    4. Notifica CEO — rascunho aguarda aprovação do Vasco
    """
    state = _load_state()
    state["ciclos_executados"] = state.get("ciclos_executados", 0) + 1
    _save_state(state)

    # 1. Métricas
    metricas = obter_metricas()

    # 2. Anomalias
    alertas = verificar_anomalias()

    # 3. Curar e rascunhar
    from newsletter_agent import ciclo_semanal_automatico
    resultado_draft = ciclo_semanal_automatico()

    # Registar timestamp do draft
    if "✅ Rascunho guardado" in resultado_draft:
        state = _load_state()
        state["ultimo_draft_criado"] = datetime.now().isoformat()
        _save_state(state)

    # 4. Reportar ao CEO
    state = _load_state()
    resumo = (
        f"Pulser — ciclo semanal completo | "
        f"Subs: {state['subscribers']} | "
        f"Fase: {state['fase']} | "
        f"Alertas: {len(alertas)}"
    )
    _notificar_ceo("Ciclo semanal concluído", resumo)

    # Publicar estado no runtime partilhado
    try:
        from runtime_state import publicar as rs_publicar
        rs_publicar("pulser", {
            "status": f"{'⚠️ alertas' if alertas else '✅ normal'}",
            "resumo": f"Subs: {state['subscribers']} | Fase: {state['fase']} | Alertas: {len(alertas)}",
            "subscribers": state.get("subscribers", 0),
            "fase": state.get("fase", "setup"),
            "ultimo_draft": state.get("ultimo_draft_criado", ""),
            "alertas": alertas,
        })
    except Exception:
        pass

    return f"{resumo}\n{resultado_draft}"


def relatorio_para_operator() -> str:
    """Chamado pelo Operator para monitorização. Retorna estado actual."""
    state = _load_state()
    metricas = obter_metricas()
    alertas = verificar_anomalias()

    crescimento = state.get("subscribers", 0) - state.get("subscribers_semana_passada", 0)

    linhas = [
        f"📰 THE AI PULSE BC — Relatório",
        f"Fase: {state['fase']} | Subs: {state['subscribers']} (+{crescimento} esta semana)",
        f"Emails enviados: {state['emails_enviados']} | Open rate: {state.get('open_rate', 0):.0%}",
        f"Receita: €{state.get('receita_total', 0):.2f}",
        f"Último draft: {state.get('ultimo_draft_criado', 'nunca')[:10] or 'nunca'}",
    ]
    if alertas:
        linhas.append(f"⚠️ Alertas: {' | '.join(alertas)}")
    else:
        linhas.append("✅ Sem alertas")

    return "\n".join(linhas)


if __name__ == "__main__":
    print(relatorio_para_operator())
