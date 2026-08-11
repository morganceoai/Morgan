"""
CEO Events — sistema de eventos contínuo do CEO Morgan.
Cada agente publica eventos aqui. O CEO processa e age quando thresholds são cruzados.
Custo: €0 — Claude só é chamado quando há evento crítico, não a cada publicação.
"""
import json
import threading
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path(__file__).parent / "memory"
EVENTS_FILE = MEMORY_DIR / "ceo_events.json"
_lock = threading.Lock()

# Thresholds que disparam acção imediata do CEO (chamada Claude + push)
THRESHOLDS = {
    "erro_repetido": 3,          # mesmo erro 3x → escala ao CEO
    "sem_vendas_dias": 14,       # Etsy sem vendas → CEO alerta Vasco
    "trading_perda_pct": 0.05,   # perda >5% posição → CEO alerta CFO
    "newsletter_sem_draft": 14,  # sem rascunho → CEO alerta Marketeer
}


def _load() -> dict:
    _default = {"eventos": [], "contadores": {}, "ultimo_processado": ""}
    with _lock:
        if EVENTS_FILE.exists():
            try:
                data = json.loads(EVENTS_FILE.read_text())
                if isinstance(data, dict) and "eventos" in data:
                    return data
            except Exception:
                pass
        return _default


def _save(state: dict):
    with _lock:
        EVENTS_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def publicar(agente: str, tipo: str, mensagem: str, nivel: str = "info", dados: dict = None):
    """
    Publica um evento no sistema. Chamado por qualquer agente.
    nivel: "info" | "aviso" | "critico"
    """
    state = _load()
    evento = {
        "id": f"{agente}_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "agente": agente,
        "tipo": tipo,
        "mensagem": mensagem,
        "nivel": nivel,
        "dados": dados or {},
        "ts": datetime.now().isoformat(),
        "processado": False,
    }
    state["eventos"].append(evento)

    # Manter só os últimos 500 eventos
    if len(state["eventos"]) > 500:
        state["eventos"] = state["eventos"][-500:]

    # Actualizar contadores para detecção de padrões
    chave = f"{agente}_{tipo}"
    state["contadores"][chave] = state["contadores"].get(chave, 0) + 1

    _save(state)

    # Verificar thresholds em background — sem bloquear o caller
    if nivel in ("aviso", "critico"):
        threading.Thread(target=_verificar_thresholds, args=(evento, state), daemon=True).start()


def _verificar_thresholds(evento: dict, state: dict):
    """Verifica se algum threshold foi cruzado e age se necessário."""
    agente = evento["agente"]
    tipo = evento["tipo"]
    nivel = evento["nivel"]
    mensagem = evento["mensagem"]
    chave = f"{agente}_{tipo}"
    contagem = state["contadores"].get(chave, 1)

    deve_escalar = False
    motivo = ""

    # Erro repetido
    if "erro" in tipo.lower() and contagem >= THRESHOLDS["erro_repetido"]:
        deve_escalar = True
        motivo = f"Erro '{tipo}' repetido {contagem}x em '{agente}'"

    # Evento crítico isolado
    if nivel == "critico":
        deve_escalar = True
        motivo = mensagem

    if deve_escalar:
        _escalar_ao_ceo(agente, motivo, mensagem, contagem)


def _escalar_ao_ceo(agente: str, motivo: str, detalhe: str, contagem: int):
    """Notifica o CEO imediatamente — sem esperar o próximo briefing."""
    try:
        from episodic_memory import registar_evento
        registar_evento("ceo", "evento_critico",
                        f"[CEO ALERTA] {agente.upper()} — {motivo}: {detalhe}")
    except Exception:
        pass

    try:
        from push_service import send_push
        send_push(
            title=f"Morgan — Alerta {agente.upper()}",
            body=f"{motivo}"[:160],
            url="/pwa/"
        )
    except Exception:
        pass


def eventos_nao_processados(nivel_min: str = "aviso") -> list[dict]:
    """Retorna eventos ainda não processados acima de um nível mínimo."""
    niveis = {"info": 0, "aviso": 1, "critico": 2}
    min_val = niveis.get(nivel_min, 1)
    state = _load()
    return [
        e for e in state["eventos"]
        if not e.get("processado") and niveis.get(e.get("nivel", "info"), 0) >= min_val
    ]


def marcar_processado(evento_id: str):
    """Marca um evento como processado."""
    state = _load()
    for e in state["eventos"]:
        if e["id"] == evento_id:
            e["processado"] = True
            break
    _save(state)


def resumo_para_ceo() -> str:
    """Resumo dos eventos recentes para incluir nos briefings."""
    state = _load()
    eventos = state["eventos"][-50:]  # últimos 50

    criticos = [e for e in eventos if e.get("nivel") == "critico" and not e.get("processado")]
    avisos = [e for e in eventos if e.get("nivel") == "aviso" and not e.get("processado")]

    if not criticos and not avisos:
        return ""

    linhas = []
    if criticos:
        linhas.append(f"🚨 {len(criticos)} evento(s) crítico(s):")
        for e in criticos[:3]:
            linhas.append(f"  • [{e['agente'].upper()}] {e['mensagem'][:80]}")
    if avisos:
        linhas.append(f"⚠️ {len(avisos)} aviso(s):")
        for e in avisos[:3]:
            linhas.append(f"  • [{e['agente'].upper()}] {e['mensagem'][:80]}")

    return "\n".join(linhas)


def reset_contador(agente: str, tipo: str):
    """Reset do contador após resolução — evita alertas repetidos do mesmo problema resolvido."""
    state = _load()
    chave = f"{agente}_{tipo}"
    state["contadores"].pop(chave, None)
    _save(state)
