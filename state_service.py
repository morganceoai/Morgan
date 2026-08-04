"""
Shared State Board — fonte de verdade do estado actual do sistema Morgan.
Todos os agentes lêem. CEO e agentes escrevem na sua área.
"""
import json
import threading
from datetime import datetime
from pathlib import Path

_STATE_FILE = Path(__file__).parent / "memory" / "system_state.json"
_lock = threading.Lock()

_DEFAULT = {
    "timestamp": "",
    "negocios": {
        "patlas": {
            "visitas_semana": 0,
            "vendas_semana": 0,
            "receita_semana": 0.0,
            "listings_ativos": 0,
            "ultima_acao": "",
            "estado": "activo"
        },
        "trading": {
            "saldo_usdt": 0.0,
            "posicao": "",
            "pnl_hoje": 0.0,
            "pnl_total": 0.0,
            "ultima_ordem": "",
            "estado": "activo"
        },
        "newsletter": {
            "subscribers": 0,
            "emails_enviados": 0,
            "ultimo_envio": "",
            "estado": "setup"
        }
    },
    "oportunidades": {
        "em_pipeline": [],
        "aprovadas": [],
        "rejeitadas": []
    },
    "sistema": {
        "agentes_com_erros": [],
        "ultimo_erro": "",
        "ultimo_erro_ts": "",
        "saude": "ok",
        "uptime_desde": ""
    },
    "moreirense": {
        "proximo_jogo": "",
        "adversario": "",
        "posicao_liga": "",
        "ultima_actualizacao": ""
    },
    "claude_usage": {
        "hoje_usd": 0.0,
        "mes_usd": 0.0,
        "agente_top": ""
    }
}


def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return json.loads(json.dumps(_DEFAULT))


def _save(state: dict):
    _STATE_FILE.parent.mkdir(exist_ok=True)
    state["timestamp"] = datetime.now().isoformat()
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def ler() -> dict:
    """Lê o estado actual do sistema. Seguro para todos os agentes."""
    with _lock:
        return _load()


def ler_negocio(nome: str) -> dict:
    """Lê o estado de um negócio específico: 'patlas', 'trading', 'newsletter'."""
    estado = ler()
    return estado.get("negocios", {}).get(nome, {})


def ler_sistema() -> dict:
    """Lê o estado de saúde do sistema."""
    return ler().get("sistema", {})


def escrever_negocio(nome: str, dados: dict):
    """Actualiza o estado de um negócio. Merge com dados existentes."""
    with _lock:
        state = _load()
        if "negocios" not in state:
            state["negocios"] = {}
        if nome not in state["negocios"]:
            state["negocios"][nome] = {}
        state["negocios"][nome].update(dados)
        _save(state)


def escrever_sistema(dados: dict):
    """Actualiza o estado de saúde do sistema."""
    with _lock:
        state = _load()
        if "sistema" not in state:
            state["sistema"] = {}
        state["sistema"].update(dados)
        _save(state)


def escrever_moreirense(dados: dict):
    """Actualiza dados do Moreirense."""
    with _lock:
        state = _load()
        if "moreirense" not in state:
            state["moreirense"] = {}
        state["moreirense"].update(dados)
        state["moreirense"]["ultima_actualizacao"] = datetime.now().isoformat()
        _save(state)


def escrever_oportunidades(em_pipeline: list = None, aprovadas: list = None, rejeitadas: list = None):
    """Actualiza oportunidades em pipeline/aprovadas/rejeitadas."""
    with _lock:
        state = _load()
        if "oportunidades" not in state:
            state["oportunidades"] = {"em_pipeline": [], "aprovadas": [], "rejeitadas": []}
        if em_pipeline is not None:
            state["oportunidades"]["em_pipeline"] = em_pipeline
        if aprovadas is not None:
            state["oportunidades"]["aprovadas"] = aprovadas
        if rejeitadas is not None:
            state["oportunidades"]["rejeitadas"] = rejeitadas
        _save(state)


def escrever_claude_usage(hoje_usd: float, mes_usd: float = None, agente_top: str = ""):
    """Actualiza consumo Claude."""
    with _lock:
        state = _load()
        if "claude_usage" not in state:
            state["claude_usage"] = {}
        state["claude_usage"]["hoje_usd"] = hoje_usd
        if mes_usd is not None:
            state["claude_usage"]["mes_usd"] = mes_usd
        if agente_top:
            state["claude_usage"]["agente_top"] = agente_top
        _save(state)


def registar_erro(agente: str, erro: str):
    """Regista um erro de um agente no estado do sistema."""
    with _lock:
        state = _load()
        if "sistema" not in state:
            state["sistema"] = {}
        state["sistema"]["ultimo_erro"] = f"[{agente}] {erro}"
        state["sistema"]["ultimo_erro_ts"] = datetime.now().isoformat()
        erros = state["sistema"].get("agentes_com_erros", [])
        if agente not in erros:
            erros.append(agente)
        state["sistema"]["agentes_com_erros"] = erros[-10:]  # máx 10
        _save(state)


def limpar_erro(agente: str):
    """Remove um agente da lista de erros quando volta a funcionar."""
    with _lock:
        state = _load()
        erros = state.get("sistema", {}).get("agentes_com_erros", [])
        state["sistema"]["agentes_com_erros"] = [e for e in erros if e != agente]
        _save(state)


def resumo_texto() -> str:
    """Resumo em texto do estado actual — para usar nos briefings do CEO."""
    s = ler()
    neg = s.get("negocios", {})
    patlas = neg.get("patlas", {})
    trading = neg.get("trading", {})
    newsletter = neg.get("newsletter", {})
    oport = s.get("oportunidades", {})
    sistema = s.get("sistema", {})
    usage = s.get("claude_usage", {})

    linhas = [
        f"📊 ESTADO DO SISTEMA — {s.get('timestamp', '')[:16]}",
        f"",
        f"🛍️ PlannerAtlas: {patlas.get('listings_ativos', 0)} listings | "
        f"visitas/semana: {patlas.get('visitas_semana', 0)} | "
        f"vendas/semana: {patlas.get('vendas_semana', 0)} | "
        f"receita: €{patlas.get('receita_semana', 0):.2f}",
        f"📈 Trading: saldo ${trading.get('saldo_usdt', 0):.2f} | "
        f"PnL hoje: ${trading.get('pnl_hoje', 0):+.2f} | "
        f"posição: {trading.get('posicao', 'nenhuma')}",
        f"📰 Newsletter: {newsletter.get('subscribers', 0)} subs | estado: {newsletter.get('estado', 'setup')}",
        f"",
        f"🎯 Oportunidades em pipeline: {len(oport.get('em_pipeline', []))} | "
        f"aprovadas: {len(oport.get('aprovadas', []))}",
        f"🤖 Claude hoje: ${usage.get('hoje_usd', 0):.3f}",
        f"⚙️ Saúde: {sistema.get('saude', 'ok')} | "
        f"erros: {', '.join(sistema.get('agentes_com_erros', [])) or 'nenhum'}",
    ]
    return "\n".join(linhas)


if __name__ == "__main__":
    print(resumo_texto())
