"""
CFO — Strategy Switcher para SOL/USDT
Gere a transição entre DCA e Grid para SOL com base na fase de mercado.

Regras:
- Bear  → dca_bot (DCA simples)
- Bull/lateral → sol_grid_bot (Grid)
- NUNCA troca se houver posições abertas (protecção)
- NUNCA troca sem aprovação explícita do Vasco
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path("memory/sol_strategy_state.json")

ESTRATEGIAS_VALIDAS = {"dca_apenas", "grid_bot"}

FASE_PARA_ESTRATEGIA = {
    "bull":    "grid_bot",
    "lateral": "grid_bot",
    "bear":    "dca_apenas",
}


# ── Estado ────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "estrategia_activa": "dca_apenas",
        "ultima_troca": None,
        "historico": [],
    }

def _save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str))


# ── Verificação de posições abertas ──────────────────────────────────────────

def _posicoes_abertas_dca() -> dict:
    """Verifica se o DCA tem SOL em carteira."""
    dca_file = Path("memory/dca_state.json")
    if not dca_file.exists():
        return {"tem_posicoes": False, "qty": 0.0, "bot": "DCA"}
    state = json.loads(dca_file.read_text())
    qty = state.get("qty", 0.0)
    return {"tem_posicoes": qty > 0, "qty": qty, "bot": "DCA"}

def _posicoes_abertas_grid() -> dict:
    """Verifica se o Grid SOL tem posições abertas."""
    grid_file = Path("memory/sol_grid_state.json")
    if not grid_file.exists():
        return {"tem_posicoes": False, "n": 0, "bot": "Grid SOL"}
    state = json.loads(grid_file.read_text())
    n = len(state.get("open_positions", {}))
    return {"tem_posicoes": n > 0, "n": n, "bot": "Grid SOL"}

def verificar_posicoes_abertas() -> dict:
    """Verifica ambos os bots. Retorna resumo e flag de bloqueio."""
    dca = _posicoes_abertas_dca()
    grid = _posicoes_abertas_grid()
    bloqueado = dca["tem_posicoes"] or grid["tem_posicoes"]
    return {
        "bloqueado": bloqueado,
        "dca": dca,
        "grid": grid,
        "razao_bloqueio": (
            f"DCA tem {dca['qty']:.4f} SOL em carteira" if dca["tem_posicoes"]
            else f"Grid tem {grid['n']} posições abertas" if grid["tem_posicoes"]
            else None
        ),
    }


# ── Análise de fase e recomendação ───────────────────────────────────────────

def analisar_e_recomendar() -> dict:
    """
    Consulta a fase actual de SOL e compara com a estratégia activa.
    Retorna recomendação — nunca age por conta própria.
    """
    from cfo_market_phase import snapshot_fase

    state = _load_state()
    estrategia_actual = state["estrategia_activa"]

    try:
        fase_data = snapshot_fase("SOL/USDT", use_cache=True)
        fase = fase_data["fase_estrutural"]["fase"]
        estrategia_ideal = FASE_PARA_ESTRATEGIA.get(fase, "dca_apenas")
        estrategia_razao = fase_data.get("estrategia_razao", "")
    except Exception as e:
        return {"status": "erro", "message": f"Não foi possível obter fase SOL: {e}"}

    mudanca_necessaria = estrategia_ideal != estrategia_actual
    posicoes = verificar_posicoes_abertas() if mudanca_necessaria else None

    resultado = {
        "fase_actual": fase,
        "estrategia_actual": estrategia_actual,
        "estrategia_ideal": estrategia_ideal,
        "mudanca_necessaria": mudanca_necessaria,
        "estrategia_razao": estrategia_razao,
    }

    if mudanca_necessaria:
        if posicoes and posicoes["bloqueado"]:
            resultado["pode_trocar"] = False
            resultado["razao_bloqueio"] = posicoes["razao_bloqueio"]
            resultado["mensagem"] = (
                f"Mudança recomendada ({estrategia_actual} → {estrategia_ideal}) "
                f"mas BLOQUEADA: {posicoes['razao_bloqueio']}. "
                f"Aguardar posições fecharem."
            )
        else:
            resultado["pode_trocar"] = True
            resultado["mensagem"] = (
                f"Recomendo mudar SOL de {estrategia_actual} para {estrategia_ideal}. "
                f"Razão: {estrategia_razao}. "
                f"Sem posições abertas — seguro trocar. Confirmas?"
            )
    else:
        resultado["pode_trocar"] = False
        resultado["mensagem"] = (
            f"Estratégia actual ({estrategia_actual}) já é a ideal para fase {fase}. "
            f"Nada a mudar."
        )

    return resultado


# ── Execução da troca (só após aprovação explícita) ──────────────────────────

def executar_troca(nova_estrategia: str, aprovado_por: str = "vasco") -> dict:
    """
    Executa a troca de estratégia para SOL.
    DEVE ser chamada apenas após aprovação explícita do Vasco.
    Verifica posições abertas mesmo assim — dupla protecção.
    """
    if nova_estrategia not in ESTRATEGIAS_VALIDAS:
        return {"status": "erro", "message": f"Estratégia inválida: {nova_estrategia}"}

    # Dupla protecção: verifica posições mesmo com aprovação
    posicoes = verificar_posicoes_abertas()
    if posicoes["bloqueado"]:
        return {
            "status": "bloqueado",
            "message": f"Troca BLOQUEADA mesmo com aprovação: {posicoes['razao_bloqueio']}. "
                       f"Fecha as posições primeiro.",
        }

    state = _load_state()
    estrategia_anterior = state["estrategia_activa"]

    if estrategia_anterior == nova_estrategia:
        return {"status": "sem_mudanca", "message": f"SOL já está em {nova_estrategia}."}

    # Pausa bot actual
    try:
        if estrategia_anterior == "dca_apenas":
            from dca_bot import pause_bot
            pause_bot()
        elif estrategia_anterior == "grid_bot":
            from sol_grid_bot import pause_bot
            pause_bot()
    except Exception as e:
        logger.warning(f"[SOL Switch] Aviso ao pausar bot anterior: {e}")

    # Activa novo bot
    try:
        if nova_estrategia == "dca_apenas":
            from dca_bot import resume_bot
            resume_bot()
        elif nova_estrategia == "grid_bot":
            from sol_grid_bot import resume_bot, reset_grid
            reset_grid()   # reinicia grid com preço actual
            resume_bot()
    except Exception as e:
        return {"status": "erro", "message": f"Erro ao activar {nova_estrategia}: {e}"}

    # Actualiza estado
    state["estrategia_activa"] = nova_estrategia
    state["ultima_troca"] = datetime.now(timezone.utc).isoformat()
    state["historico"].append({
        "de": estrategia_anterior,
        "para": nova_estrategia,
        "aprovado_por": aprovado_por,
        "ts": state["ultima_troca"],
    })
    _save_state(state)

    logger.info(f"[SOL Switch] {estrategia_anterior} → {nova_estrategia} (aprovado: {aprovado_por})")
    return {
        "status": "ok",
        "de": estrategia_anterior,
        "para": nova_estrategia,
        "message": f"SOL mudou de {estrategia_anterior} para {nova_estrategia}.",
    }


# ── Resumo para CFO ───────────────────────────────────────────────────────────

def resumo_para_cfo() -> str:
    state = _load_state()
    estrategia = state["estrategia_activa"]
    ultima_troca = state.get("ultima_troca") or "nunca"
    posicoes = verificar_posicoes_abertas()

    pos_str = ""
    if estrategia == "dca_apenas":
        qty = posicoes["dca"]["qty"]
        pos_str = f"{qty:.4f} SOL em carteira" if qty > 0 else "sem posições"
    elif estrategia == "grid_bot":
        n = posicoes["grid"]["n"]
        pos_str = f"{n} posições abertas" if n > 0 else "sem posições"

    return f"SOL estratégia: {estrategia} | {pos_str} | última troca: {ultima_troca}"


if __name__ == "__main__":
    import json
    result = analisar_e_recomendar()
    print(json.dumps(result, indent=2, ensure_ascii=False))
