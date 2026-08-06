"""
CFO — Strategy Switcher para SOL/USDT
Recomenda e executa mudança de estratégia (dca/grid) após aprovação do Vasco.
Nunca age sem posicoes fechadas. Nunca age sem aprovação explícita.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

FASE_PARA_ESTRATEGIA = {
    "bull":    "grid",
    "lateral": "grid",
    "bear":    "dca",
}


def analisar_e_recomendar() -> dict:
    from cfo_market_phase import snapshot_fase
    from sol_bot import get_status, tem_posicoes_abertas

    status = get_status()
    estrategia_actual = status["estrategia"]

    try:
        fase_data = snapshot_fase("SOL/USDT", use_cache=True)
        fase = fase_data["fase_estrutural"]["fase"]
        estrategia_ideal = FASE_PARA_ESTRATEGIA.get(fase, "dca")
        razao = fase_data.get("estrategia_razao", "")
    except Exception as e:
        return {"status": "erro", "message": str(e)}

    mudanca = estrategia_ideal != estrategia_actual

    resultado = {
        "fase_actual": fase,
        "estrategia_actual": estrategia_actual,
        "estrategia_ideal": estrategia_ideal,
        "mudanca_necessaria": mudanca,
        "razao": razao,
    }

    if not mudanca:
        resultado["mensagem"] = f"Estratégia actual ({estrategia_actual}) já é a ideal para fase {fase}. Nada a mudar."
        return resultado

    if tem_posicoes_abertas():
        resultado["pode_trocar"] = False
        resultado["mensagem"] = (
            f"Mudança recomendada ({estrategia_actual} → {estrategia_ideal}) "
            f"mas BLOQUEADA: há posições abertas. Aguardar fecharem."
        )
    else:
        resultado["pode_trocar"] = True
        resultado["mensagem"] = (
            f"Recomendo mudar SOL de {estrategia_actual} para {estrategia_ideal}. "
            f"Razão: {razao}. Sem posições abertas — seguro trocar. Confirmas?"
        )

    return resultado


def executar_troca(nova_estrategia: str) -> dict:
    """Executa troca. Chamar só após 'sim' explícito do Vasco."""
    from sol_bot import set_estrategia
    return set_estrategia(nova_estrategia)


def resumo_para_cfo() -> str:
    from sol_bot import get_status
    s = get_status()
    return (
        f"SOL/{s['estrategia']} | "
        f"PnL ${s['pnl_total']:+.2f} | "
        f"Trades: {s['total_trades']} | "
        f"Preço: ${s['last_price']}"
    )


if __name__ == "__main__":
    import json
    print(json.dumps(analisar_e_recomendar(), indent=2, ensure_ascii=False))
