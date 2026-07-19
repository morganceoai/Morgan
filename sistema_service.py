"""
sistema_service.py — fonte de verdade do estado do sistema Morgan.

Quando um novo agente, negócio ou conta é criado, registar aqui.
Todos os agentes lêem daqui para saberem o que existe.
"""
import json
from datetime import datetime
from pathlib import Path

_FILE = Path(__file__).parent / "memory" / "sistema_estado.json"

_DEFAULT = {
    "agentes": {
        "ceo":        {"nome": "CEO",        "descricao": "Orquestrador principal, routing, Mem0, histórico", "ativo": True},
        "scout":      {"nome": "Scout",      "descricao": "Oportunidades de negócio + melhorias a agentes (dom 20h, qua 20h)", "ativo": True},
        "coach":      {"nome": "Coach",      "descricao": "Futebol, Moreirense, táticas, StatsBomb, briefing 7h", "ativo": True},
        "cfo":        {"nome": "CFO",        "descricao": "Trading BTC/USDT, PnL, drawdown, Binance", "ativo": True},
        "solver":     {"nome": "Solver",     "descricao": "Diagnóstico de problemas, LangGraph, escalada <90%", "ativo": True},
        "creator":    {"nome": "Creator",    "descricao": "Deploy seguro, rollback automático, browser automation", "ativo": True},
        "operator":   {"nome": "Operator",   "descricao": "Etsy OAuth2, vendas, listings, limpeza sistema", "ativo": True},
        "marketeer":  {"nome": "Marketeer",  "descricao": "Pinterest, Gmail outreach, leads, SEO Etsy", "ativo": True},
    },
    "negocios": {
        "etsy_planneratlas": {
            "nome": "PlannerAtlas Etsy",
            "tipo": "etsy",
            "plataforma": "etsy.com",
            "descricao": "Planners digitais PT/ES/DE",
            "listings": 8,
            "email": "morganceoai@gmail.com",
            "ativo": True,
            "criado_em": "2026-07-08",
        }
    },
    "contas": {
        "zoho": [],
        "limite_zoho": 5,
    },
    "ultima_atualizacao": datetime.now().isoformat(),
}


def _load() -> dict:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text())
        except Exception:
            pass
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(_DEFAULT, ensure_ascii=False, indent=2))
    return _DEFAULT.copy()


def _save(estado: dict):
    estado["ultima_atualizacao"] = datetime.now().isoformat()
    _FILE.write_text(json.dumps(estado, ensure_ascii=False, indent=2))


def get_estado() -> dict:
    return _load()


def get_agentes_ativos() -> dict:
    return {k: v for k, v in _load()["agentes"].items() if v.get("ativo")}


def get_negocios_ativos() -> dict:
    return {k: v for k, v in _load()["negocios"].items() if v.get("ativo")}


def registar_agente(chave: str, nome: str, descricao: str, notificar: bool = True) -> str:
    """Regista um novo agente no sistema e propaga conhecimento."""
    estado = _load()
    estado["agentes"][chave] = {
        "nome": nome,
        "descricao": descricao,
        "ativo": True,
        "criado_em": datetime.now().strftime("%Y-%m-%d"),
    }
    _save(estado)

    # Propagar para memória episódica — CEO, Marketeer, Solver ficam a saber
    try:
        from episodic_memory import registar_evento
        registar_evento("ceo", "sistema", f"Novo agente adicionado: {nome} — {descricao}")
        registar_evento("marketeer", "sistema", f"Novo agente {nome} criado. Se tiver negócio associado, assumir responsabilidade de marketing.")
        registar_evento("solver", "sistema", f"Novo agente {nome} adicionado. Monitorizar saúde e reportar erros no briefing diário.")
    except Exception:
        pass

    # Push ao Vasco
    if notificar:
        try:
            from push_service import send_push
            send_push(
                title=f"Morgan — Novo agente: {nome}",
                body=descricao[:160],
                url="/pwa/"
            )
        except Exception:
            pass

    return f"Agente '{nome}' registado e propagado ao sistema."


def registar_negocio(chave: str, nome: str, tipo: str, plataforma: str, descricao: str, email: str = "", notificar: bool = True) -> str:
    """Regista um novo negócio. Propaga responsabilidade ao Marketeer, CEO e Solver."""
    estado = _load()
    estado["negocios"][chave] = {
        "nome": nome,
        "tipo": tipo,
        "plataforma": plataforma,
        "descricao": descricao,
        "email": email,
        "ativo": True,
        "criado_em": datetime.now().strftime("%Y-%m-%d"),
    }
    _save(estado)

    try:
        from episodic_memory import registar_evento
        registar_evento("ceo", "sistema", f"Novo negócio no sistema: {nome} ({plataforma}) — {descricao}")
        registar_evento("marketeer", "sistema", f"Novo negócio para gerir: {nome} em {plataforma}. Assumir marketing imediatamente.")
        registar_evento("operator", "sistema", f"Novo negócio operacional: {nome} em {plataforma}. Monitorizar estado diário.")
        registar_evento("cfo", "sistema", f"Novo negócio: {nome}. Incluir nas projeções financeiras mensais.")
        registar_evento("solver", "sistema", f"Novo negócio {nome} criado. Monitorizar erros e dependências.")
    except Exception:
        pass

    if notificar:
        try:
            from push_service import send_push
            send_push(
                title=f"Morgan — Novo negócio: {nome}",
                body=f"{plataforma} — {descricao}"[:160],
                url="/pwa/"
            )
        except Exception:
            pass

    return f"Negócio '{nome}' registado e sistema actualizado."


def registar_conta_zoho(email: str) -> str:
    """Regista uma nova conta Zoho. Avisa quando perto do limite de 5."""
    estado = _load()
    contas = estado.setdefault("contas", {}).setdefault("zoho", [])
    limite = estado["contas"].get("limite_zoho", 5)

    if email in contas:
        return f"Conta {email} já registada."

    contas.append(email)
    _save(estado)

    restantes = limite - len(contas)
    if restantes == 1:
        try:
            from push_service import send_push
            send_push(
                title="Morgan — Atenção: contas Zoho",
                body=f"Próxima conta Zoho será a última do plano gratuito ({limite} max). Considerar migração para Gmail ($6/mês).",
                url="/pwa/"
            )
        except Exception:
            pass
    elif restantes <= 0:
        try:
            from push_service import send_push
            send_push(
                title="Morgan — Limite Zoho atingido",
                body="Limite de 5 contas Zoho gratuitas atingido. Autoriza migração para Gmail ($6/mês)?",
                url="/pwa/"
            )
        except Exception:
            pass

    return f"Conta {email} registada. {restantes} vagas restantes no plano Zoho."


def resumo_sistema() -> str:
    """Texto resumido do estado do sistema — usado nos briefings."""
    estado = _load()
    agentes = [v["nome"] for v in estado["agentes"].values() if v.get("ativo")]
    negocios = [f"{v['nome']} ({v['plataforma']})" for v in estado["negocios"].values() if v.get("ativo")]
    contas_zoho = len(estado.get("contas", {}).get("zoho", []))
    limite_zoho = estado.get("contas", {}).get("limite_zoho", 5)

    linhas = [
        f"Agentes activos ({len(agentes)}): {', '.join(agentes)}",
        f"Negócios activos ({len(negocios)}): {', '.join(negocios) if negocios else 'nenhum'}",
        f"Contas Zoho: {contas_zoho}/{limite_zoho}",
    ]
    return "\n".join(linhas)
