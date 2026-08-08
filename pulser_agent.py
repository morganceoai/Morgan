"""
Pulser — Agente autónomo da newsletter The AI Pulse BC
Actua por iniciativa própria: cura, rascunha, monitoriza, cresce, alerta o CEO.
Inclui marketing de crescimento, outreach a sponsors e gestão de fase.
"""
import json
import os
import smtplib
import ssl
import threading
import time
from datetime import datetime, timedelta, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MEMORY_DIR = Path(__file__).parent / "memory"
PULSER_STATE_FILE = MEMORY_DIR / "pulser_state.json"

from claude_guard import GuardedClient
client = GuardedClient("pulser")

from episodic_memory import registar_evento

# ── Thresholds ────────────────────────────────────────────────────────────────
ALERTA_SEM_DRAFT_DIAS = 14
ALERTA_OPEN_RATE_MIN = 0.30
ALERTA_CRESCIMENTO_SEMANAL_MIN = 5
_OUTREACH_CAP = 50

SYSTEM_PROMPT = """És o Pulser, o agente autónomo da newsletter "The AI Pulse BC" no Beehiiv.

NEGÓCIO:
- Newsletter faceless EN — AI tools & productivity para founders (US/UK/CA)
- Publicar às terças 8h EST (maior open rate EN B2B)
- Objectivo: €10.000/mês de rendimento passivo para o Vasco

REGRA ANTI-PRÓLOGO: A primeira linha da tua resposta é sempre conteúdo útil.

GESTÃO DE FASES:
Setup (0-100 subs): foco em SEO e distribuição orgânica.
Crescimento (100-1k subs): Beehiiv Boosts + cross-post HN/Reddit + SEO "best AI tools for X".
Monetização (1k+ subs): Beehiiv Ad Network activa ($15-40 CPM). Sponsors directos a partir 5k.
Escala (5k+ subs): sponsors directos $50-200/edição.

Regressão: crescimento <5 subs/semana por 4 semanas → rever estratégia de distribuição.

ESTRATÉGIA DE CRESCIMENTO:
1. SEO — artigos "best AI tools for X" que ranqueiam e convertem
2. Beehiiv Boosts — pagar outros para recomendar (só fase crescimento+)
3. Cross-post HN/Reddit Show HN com conteúdo genuíno
4. Referral loops — oferecer algo em troca de referências
5. Outreach a sponsors — só após 1k subs

ALERTAS:
- 0 rascunhos >14 dias → newsletter parada
- Open rate <30% → subject lines a falhar
- <5 novos subs/semana após fase crescimento → rever SEO

PT-PT sempre (internamente). Newsletter em EN. A última decisão é sempre do Vasco."""


# ── Estado ────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if PULSER_STATE_FILE.exists():
        return json.loads(PULSER_STATE_FILE.read_text())
    estado = {
        "nome": "The AI Pulse BC",
        "fase": "setup",
        "subscribers": 0,
        "subscribers_semana_passada": 0,
        "open_rate": 0.0,
        "click_rate": 0.0,
        "emails_enviados": 0,
        "ultimo_draft_criado": "",
        "ultimo_envio": "",
        "receita_total": 0.0,
        "alertas_activos": [],
        "ciclos_executados": 0,
        "campanhas": [],
        "outreach_diario": {},
        "metrics_history": [],
        "criado_em": datetime.now().isoformat(),
    }
    PULSER_STATE_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False))
    return estado


def _save_state(state: dict):
    PULSER_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ── Notificações ──────────────────────────────────────────────────────────────

def _notificar_ceo(titulo: str, corpo: str, urgente: bool = False):
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


# ── Métricas e anomalias ──────────────────────────────────────────────────────

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


def _avaliar_transicao_fase(state: dict) -> str | None:
    fase = state.get("fase", "setup")
    subs = state.get("subscribers", 0)
    receita = state.get("receita_total", 0.0)
    open_rate = state.get("open_rate", 0.0)

    if fase == "setup" and subs >= 100:
        return "crescimento"
    if fase == "crescimento" and subs >= 1000:
        return "monetizacao"
    if fase == "monetizacao" and receita > 2000:
        return "escala"
    return None


def _snapshot_metricas(state: dict):
    historico = state.setdefault("metrics_history", [])
    snap = {
        "timestamp": datetime.now().isoformat(),
        "subscribers": state.get("subscribers", 0),
        "open_rate": state.get("open_rate", 0.0),
        "receita_total": state.get("receita_total", 0.0),
    }
    historico.append(snap)
    state["metrics_history"] = historico[-365:]


def obter_metricas() -> dict:
    """Vai buscar métricas reais ao Beehiiv."""
    try:
        from newsletter_agent import obter_stats
        stats = obter_stats()
        if "erro" in stats:
            return {"ok": False, "erro": stats["erro"]}

        state = _load_state()
        state["subscribers_semana_passada"] = state.get("subscribers", 0)
        state["subscribers"] = stats.get("subscribers", state["subscribers"])
        state["emails_enviados"] = stats.get("emails_enviados", state["emails_enviados"])
        state["open_rate"] = stats.get("open_rate", state["open_rate"])
        state["fase"] = _detectar_fase(state)
        _save_state(state)
        return {"ok": True, **stats}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def verificar_anomalias() -> list[str]:
    """Detecta problemas proactivamente."""
    state = _load_state()
    alertas = []
    agora = datetime.now()

    # Sem draft há demasiado tempo
    if state.get("ultimo_draft_criado"):
        ultimo = datetime.fromisoformat(state["ultimo_draft_criado"])
        dias_sem_draft = (agora - ultimo).days
        if dias_sem_draft >= ALERTA_SEM_DRAFT_DIAS:
            alertas.append(f"Sem rascunho há {dias_sem_draft} dias — newsletter parada")

    # Open rate baixo
    open_rate = state.get("open_rate", 0.0)
    if open_rate > 0 and open_rate < ALERTA_OPEN_RATE_MIN:
        alertas.append(f"Open rate {open_rate:.0%} — abaixo de {ALERTA_OPEN_RATE_MIN:.0%} (subject lines a falhar?)")

    # Crescimento estagnado
    if state.get("fase") in ("crescimento", "monetizacao"):
        crescimento = state.get("subscribers", 0) - state.get("subscribers_semana_passada", 0)
        if crescimento < ALERTA_CRESCIMENTO_SEMANAL_MIN:
            alertas.append(f"Crescimento semanal: +{crescimento} subs — abaixo de {ALERTA_CRESCIMENTO_SEMANAL_MIN} (rever SEO/Boosts)")

    # Transição de fase
    nova_fase = _avaliar_transicao_fase(state)
    if nova_fase:
        alertas.append(f"Critérios para transição para '{nova_fase}' cumpridos — confirmar com Vasco")

    # Notificar CEO para alertas novos
    alertas_anteriores = set(state.get("alertas_activos", []))
    alertas_novos = [a for a in alertas if a not in alertas_anteriores]
    for alerta in alertas_novos:
        _notificar_ceo("Pulser — anomalia detectada", alerta, urgente=True)

    state["alertas_activos"] = alertas
    _save_state(state)
    return alertas


# ── Marketing de crescimento ──────────────────────────────────────────────────

def pesquisar_leads(nicho: str, mercado: str = "US") -> str:
    """Pesquisa leads (sponsors, parceiros, fontes de subs) para a newsletter."""
    try:
        from tools import pesquisar
        query = f"{nicho} newsletter sponsor AI tools productivity {mercado} 2026"
        return pesquisar(query, agente="pulser")
    except Exception as e:
        return f"Erro na pesquisa: {e}"


def redigir_mensagem_outreach(contexto: str, destinatario: str, produto: str) -> str:
    """Redige mensagem de outreach para sponsor ou parceiro de newsletter."""
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=[{"type": "text", "text": "Rediges mensagens de outreach curtas (max 80 palavras), personalizadas, em EN. Tom: profissional mas humano. Nunca uses saudações genéricas.", "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Contexto do lead: {contexto}\nDestinatário: {destinatario}\nOferta: {produto}\n\nRedige a mensagem:"}]
        )
        return r.content[0].text
    except Exception as e:
        return f"Erro ao redigir: {e}"


def registar_campanha(nome: str, canal: str, objetivo: str) -> str:
    """Regista uma campanha de crescimento da newsletter."""
    state = _load_state()
    campanhas = state.setdefault("campanhas", [])
    campanha = {
        "id": f"camp_{len(campanhas)+1:03d}",
        "nome": nome,
        "canal": canal,
        "objetivo": objetivo,
        "criada": datetime.now().isoformat()[:16],
        "status": "ativa",
        "conversoes": 0,
    }
    campanhas.append(campanha)
    _save_state(state)
    return f"Campanha '{nome}' registada (ID: {campanha['id']})."


def _outreach_hoje(state: dict) -> int:
    hoje = str(date.today())
    return state.get("outreach_diario", {}).get(hoje, 0)


def _registar_outreach_enviado(state: dict):
    hoje = str(date.today())
    d = state.setdefault("outreach_diario", {})
    d[hoje] = d.get(hoje, 0) + 1
    _save_state(state)


def enviar_outreach_email(destinatario_email: str, assunto: str, corpo: str, nome_destinatario: str = "") -> str:
    """Envia email de outreach (sponsors, parceiros). Limite: 50/dia."""
    state = _load_state()
    enviados = _outreach_hoje(state)
    if enviados >= _OUTREACH_CAP:
        return f"Limite diário de {_OUTREACH_CAP} emails atingido."

    smtp_user = os.getenv("MORGAN_EMAIL", "")
    smtp_pass = os.getenv("MORGAN_EMAIL_PASS", "")
    if not smtp_user or not smtp_pass:
        return "Variáveis MORGAN_EMAIL / MORGAN_EMAIL_PASS não configuradas no .env."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = smtp_user
        msg["To"] = f"{nome_destinatario} <{destinatario_email}>" if nome_destinatario else destinatario_email
        msg.attach(MIMEText(corpo, "plain", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP("smtp.purelymail.com", 587) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, destinatario_email, msg.as_string())

        _registar_outreach_enviado(state)
        return f"Email enviado para {destinatario_email}. Total hoje: {_outreach_hoje(state)}/{_OUTREACH_CAP}."
    except smtplib.SMTPAuthenticationError:
        return "Erro de autenticação. Verifica MORGAN_EMAIL_PASS no .env."
    except Exception as e:
        return f"Erro ao enviar email: {e}"


def gerar_estrategia_crescimento() -> str:
    """Gera plano de crescimento de subscribers para a fase actual."""
    state = _load_state()
    fase = state.get("fase", "setup")
    subs = state.get("subscribers", 0)

    prompt = f"""Newsletter "The AI Pulse BC" — fase actual: {fase} | {subs} subscribers.

Gera um plano de crescimento concreto para esta semana:
1. Canal principal a focar (SEO / Beehiiv Boosts / Reddit HN / referral)
2. 3 acções específicas com métrica esperada
3. Subject line para o próximo envio (teste A/B: 2 opções)
4. Tópico da próxima edição (tendência AI da semana)

Máximo 15 linhas. EN. Números concretos."""

    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text if r.content else "Plano indisponível."
    except Exception as e:
        return f"Erro: {e}"


# ── Relatórios ────────────────────────────────────────────────────────────────

def relatorio_para_ceo() -> str:
    state = _load_state()
    alertas = state.get("alertas_activos", [])
    crescimento = state.get("subscribers", 0) - state.get("subscribers_semana_passada", 0)

    linhas = [
        "📰 THE AI PULSE BC — Relatório",
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


# ── Ciclo autónomo ────────────────────────────────────────────────────────────

def ciclo_semanal() -> str:
    """Corre automaticamente ao domingo 18h."""
    state = _load_state()
    state["ciclos_executados"] = state.get("ciclos_executados", 0) + 1
    _save_state(state)

    obter_metricas()
    alertas = verificar_anomalias()
    _snapshot_metricas(state)
    _save_state(state)

    # Curar e rascunhar
    try:
        from newsletter_agent import ciclo_semanal_automatico
        resultado_draft = ciclo_semanal_automatico()
        if "✅ Rascunho guardado" in resultado_draft:
            state = _load_state()
            state["ultimo_draft_criado"] = datetime.now().isoformat()
            _save_state(state)
    except Exception as e:
        resultado_draft = f"Erro ao criar draft: {e}"

    state = _load_state()
    resumo = (
        f"Pulser — ciclo semanal completo | "
        f"Subs: {state['subscribers']} | "
        f"Fase: {state['fase']} | "
        f"Alertas: {len(alertas)}"
    )
    _notificar_ceo("Ciclo semanal concluído", resumo)

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

    try:
        state = _load_state()
        registar_evento("pulser", "ciclo_semanal",
                        f"Fase: {state['fase']} | Subs: {state['subscribers']} | "
                        f"Emails: {state['emails_enviados']} | Open rate: {state.get('open_rate', 0):.0%} | "
                        f"Alertas: {len(alertas)}",
                        dados={"alertas": alertas[:3]} if alertas else None)
    except Exception:
        pass

    return f"{resumo}\n{resultado_draft}"


def get_resumo_financeiro() -> str:
    """Resumo financeiro compacto para o CFO — subscribers, receita, fase."""
    state = _load_state()
    receita = state.get("receita_total", 0.0)
    subscribers = state.get("subscribers", 0)
    open_rate = state.get("open_rate", 0.0)
    fase = state.get("fase", "setup")
    alertas = state.get("alertas_activos", [])
    alerta_str = f" | ⚠ {len(alertas)} alerta(s)" if alertas else ""
    return f"Beehiiv/AI Pulse — Subscribers: {subscribers} | Open rate: {open_rate:.0%} | Receita: €{receita:.2f} | Fase: {fase}{alerta_str}"


def iniciar_scheduler_pulser():
    """Arranca o loop autónomo semanal do Pulser em daemon thread."""
    def _loop():
        # Esperar 3min após startup
        time.sleep(180)
        while True:
            try:
                agora = datetime.now()
                # Domingo 18h
                if agora.weekday() == 6 and agora.hour == 18:
                    ciclo_semanal()
            except Exception as e:
                print(f"[pulser] ciclo_semanal erro: {e}", flush=True)
            # Verificar a cada hora
            time.sleep(3600)

    t = threading.Thread(target=_loop, daemon=True, name="pulser-scheduler")
    t.start()


# ── Interface conversacional ──────────────────────────────────────────────────

TOOLS = [
    {"name": "obter_metricas", "description": "Vai buscar métricas reais do Beehiiv.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "verificar_anomalias", "description": "Detecta anomalias e alertas activos.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "relatorio_para_ceo", "description": "Gera relatório do estado da newsletter.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "gerar_estrategia_crescimento", "description": "Gera plano de crescimento de subscribers para esta semana.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "pesquisar_leads", "description": "Pesquisa sponsors ou parceiros para a newsletter.", "input_schema": {"type": "object", "properties": {"nicho": {"type": "string"}, "mercado": {"type": "string", "default": "US"}}, "required": ["nicho"]}},
    {"name": "redigir_mensagem_outreach", "description": "Redige mensagem de outreach para sponsor ou parceiro.", "input_schema": {"type": "object", "properties": {"contexto": {"type": "string"}, "destinatario": {"type": "string"}, "produto": {"type": "string"}}, "required": ["contexto", "destinatario", "produto"]}},
    {"name": "enviar_outreach_email", "description": "Envia email de outreach. Limite 50/dia. Requer confirmação do Vasco.", "input_schema": {"type": "object", "properties": {"destinatario_email": {"type": "string"}, "assunto": {"type": "string"}, "corpo": {"type": "string"}, "nome_destinatario": {"type": "string"}}, "required": ["destinatario_email", "assunto", "corpo"]}},
    {"name": "registar_campanha", "description": "Regista uma campanha de crescimento.", "input_schema": {"type": "object", "properties": {"nome": {"type": "string"}, "canal": {"type": "string"}, "objetivo": {"type": "string"}}, "required": ["nome", "canal", "objetivo"]}},
]

TOOL_MAP = {
    "obter_metricas": lambda a: str(obter_metricas()),
    "verificar_anomalias": lambda a: str(verificar_anomalias()),
    "relatorio_para_ceo": lambda a: relatorio_para_ceo(),
    "gerar_estrategia_crescimento": lambda a: gerar_estrategia_crescimento(),
    "pesquisar_leads": lambda a: pesquisar_leads(**a),
    "redigir_mensagem_outreach": lambda a: redigir_mensagem_outreach(**a),
    "enviar_outreach_email": lambda a: enviar_outreach_email(**a),
    "registar_campanha": lambda a: registar_campanha(**a),
}


def get_pulser_reply(user_text: str) -> str:
    state = _load_state()
    context = (
        f"Estado actual: Fase={state['fase']} | Subs={state['subscribers']} | "
        f"Receita=€{state.get('receita_total', 0):.2f} | Alertas={len(state.get('alertas_activos', []))}"
    )

    mem_semantica = ""
    try:
        from episodic_memory import get_contexto_agente
        mem_semantica = get_contexto_agente("pulser", user_text or "newsletter AI Pulse subscribers crescimento")
    except Exception:
        pass
    if mem_semantica:
        context += f"\n\n[Memórias relevantes]\n{mem_semantica}"

    msgs = [{"role": "user", "content": user_text}]
    for _ in range(5):
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=[{"type": "text", "text": SYSTEM_PROMPT + "\n\n" + context, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=msgs,
        )
        if r.stop_reason == "end_turn":
            reply = next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")
            try:
                from episodic_memory import registar_evento
                registar_evento("pulser", "conversa", f"Q: {user_text[:100]} | R: {reply[:200]}")
            except Exception:
                pass
            return reply
        if r.stop_reason != "tool_use":
            break
        tool_results = []
        for block in r.content:
            if block.type == "tool_use":
                fn = TOOL_MAP.get(block.name)
                result = fn(block.input) if fn else f"Ferramenta desconhecida: {block.name}"
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        msgs.append({"role": "assistant", "content": r.content})
        msgs.append({"role": "user", "content": tool_results})

    return next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")


if __name__ == "__main__":
    print(relatorio_para_ceo())
    print()
    anomalias = verificar_anomalias()
    if anomalias:
        print("Anomalias:", anomalias)
