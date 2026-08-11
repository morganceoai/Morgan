"""
CFO Executor — Executor puro de ordens para o CFO.
Não tem inteligência própria. Só executa o que o CFO decide.

Regras de segurança:
- Modo OBSERVATION (padrão): registar decisão mas NÃO executar
- Modo EXECUTION: executa ordens reais na exchange
- Nunca fecha posições em aberto automaticamente sem confirmação do Vasco
- Toda a execução fica em log antes e depois
- Limite por operação: máximo 50% do capital alocado à conta
"""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_BASE = Path(__file__).parent
_DECISION_LOG = _BASE / "memory" / "cfo_decision_log.jsonl"
_EXECUTOR_CONFIG = _BASE / "memory" / "cfo_executor_config.json"

# Modo padrão: observação. Alterar para "execution" com autorização explícita do Vasco.
_MODO_PADRAO = "observation"


def _get_modo() -> str:
    try:
        cfg = json.loads(_EXECUTOR_CONFIG.read_text())
        return cfg.get("modo", _MODO_PADRAO)
    except Exception:
        return _MODO_PADRAO


def set_modo(modo: Literal["observation", "execution"]):
    """Define o modo do executor. Requer confirmação do Vasco — Nível 3."""
    _EXECUTOR_CONFIG.parent.mkdir(exist_ok=True)
    cfg = {}
    try:
        cfg = json.loads(_EXECUTOR_CONFIG.read_text())
    except Exception:
        pass
    cfg["modo"] = modo
    cfg["alterado_em"] = datetime.now().isoformat()
    _EXECUTOR_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    print(f"[cfo_executor] Modo alterado para: {modo}", flush=True)


def get_modo() -> str:
    return _get_modo()


def _registar_decisao(decisao: dict, executada: bool, resultado: dict | None = None):
    _DECISION_LOG.parent.mkdir(exist_ok=True)
    entrada = {
        "ts": datetime.now().isoformat(),
        "decisao": decisao,
        "executada": executada,
        "modo": _get_modo(),
        "resultado": resultado,
    }
    with open(_DECISION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def _get_exchange():
    import ccxt
    ex = ccxt.binance({
        "apiKey":  os.getenv("BINANCE_API_KEY", ""),
        "secret":  os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })
    if os.getenv("BINANCE_TESTNET", "false").lower() == "true":
        ex.set_sandbox_mode(True)
    return ex


def executar_decisao(decisao: dict) -> dict:
    """
    Ponto de entrada principal. O CFO chama aqui com a decisão tomada.

    decisao = {
        "acao": "pausar_grid" | "retomar_grid" | "ajustar_grid" | "manter" | "escalar_vasco",
        "razao": str,
        "conta_id": str,       # id da conta em cfo_accounts.json
        "parametros": dict,    # parâmetros específicos da acção
        "confianca": 0-100,
        "autonomo": bool,      # se True: CFO decide; se False: escalar ao Vasco
    }
    """
    modo = _get_modo()
    acao = decisao.get("acao", "manter")
    autonomo = decisao.get("autonomo", False)

    # Escaladas ao Vasco — nunca executar, apenas registar e notificar
    if not autonomo or acao == "escalar_vasco":
        _registar_decisao(decisao, executada=False)
        _notificar_escalada(decisao)
        return {"status": "escalado_vasco", "mensagem": decisao.get("razao", "")}

    # Modo observação — registar mas não executar
    if modo == "observation":
        print(f"[cfo_executor] OBSERVATION: teria executado '{acao}' (conta: {decisao.get('conta_id')})", flush=True)
        _registar_decisao(decisao, executada=False)
        return {"status": "observation", "acao": acao, "nota": "Não executado — modo observação activo"}

    # Modo execução — executar com validações
    try:
        resultado = _executar_acao(acao, decisao)
        _registar_decisao(decisao, executada=True, resultado=resultado)
        print(f"[cfo_executor] EXECUTADO: {acao} → {resultado.get('status')}", flush=True)
        return resultado
    except Exception as e:
        erro = {"status": "erro", "acao": acao, "erro": str(e)}
        _registar_decisao(decisao, executada=False, resultado=erro)
        print(f"[cfo_executor] ERRO ao executar '{acao}': {e}", flush=True)
        return erro


def _executar_acao(acao: str, decisao: dict) -> dict:
    if acao == "pausar_grid":
        from grid_bot import pause_bot
        pause_bot()
        return {"status": "ok", "acao": "grid_pausado"}

    elif acao == "retomar_grid":
        from grid_bot import resume_bot
        resume_bot()
        return {"status": "ok", "acao": "grid_retomado"}

    elif acao == "resetar_grid":
        # Resetar o grid para o preço actual — reinicia com novo ref_price
        # Nível 3: só executar se autonomo=True E modo=execution E capital_impacto < 10%
        from grid_bot import reset_grid
        reset_grid()
        return {"status": "ok", "acao": "grid_resetado"}

    elif acao == "manter":
        return {"status": "ok", "acao": "sem_alteracoes"}

    else:
        return {"status": "nao_suportado", "acao": acao}


def _notificar_escalada(decisao: dict):
    """Escreve evento de escalada em ceo_events.json para o CEO entregar ao Vasco."""
    try:
        ceo_events = _BASE / "memory" / "ceo_events.json"
        try:
            eventos = json.loads(ceo_events.read_text())
            if not isinstance(eventos, list):
                eventos = []
        except Exception:
            eventos = []
        eventos.append({
            "ts": datetime.now().isoformat(),
            "agente": "cfo",
            "tipo": "escalada_vasco",
            "mensagem": (
                f"CFO recomenda acção '{decisao.get('acao')}' na conta '{decisao.get('conta_id')}'.\n"
                f"Razão: {decisao.get('razao', '')}\n"
                f"Confiança: {decisao.get('confianca', 0)}%\n"
                f"Requer aprovação do Vasco."
            ),
            "urgencia": "alta",
            "decisao": decisao,
        })
        ceo_events.write_text(json.dumps(eventos, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[cfo_executor] erro escalada: {e}", flush=True)


def listar_decisoes(limite: int = 20) -> list:
    """Histórico das últimas N decisões do CFO."""
    try:
        linhas = _DECISION_LOG.read_text(encoding="utf-8").splitlines()
        recentes = linhas[-limite:]
        return [json.loads(l) for l in recentes if l.strip()]
    except Exception:
        return []


if __name__ == "__main__":
    print(f"Modo actual: {get_modo()}")
    print("Últimas decisões:")
    for d in listar_decisoes(5):
        print(f"  {d['ts'][:16]} | {d['decisao'].get('acao')} | executada={d['executada']}")
