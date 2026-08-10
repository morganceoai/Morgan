"""
CFO — Strategy Switcher para os 3 bots (BTC, ETH, SOL)
Recomenda e executa mudança de estratégia (grid/dca/trailing_stop) após aprovação do Vasco.
Nunca age sem posições fechadas. Nunca age sem aprovação explícita.

Fases → Estratégias:
  bull    → trailing_stop
  lateral → grid
  bear    → dca
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

FASE_PARA_ESTRATEGIA = {
    "bull":    "trailing_stop",
    "lateral": "grid",
    "bear":    "dca",
}

BOTS = {
    "BTC": ("grid_bot",   "BTC/USDT"),
    "ETH": ("eth_grid_bot", "ETH/USDT"),
    "SOL": ("sol_bot",    "SOL/USDT"),
}


def _get_bot_module(coin: str):
    import importlib
    module_name, symbol = BOTS[coin]
    return importlib.import_module(module_name), symbol


def analisar_e_recomendar(coin: str = "SOL") -> dict:
    """Analisa fase de mercado e recomenda estratégia para o bot indicado."""
    if coin not in BOTS:
        return {"status": "erro", "message": f"Coin inválida: {coin}. Usar BTC, ETH ou SOL."}

    mod, symbol = _get_bot_module(coin)
    status = mod.get_status()
    estrategia_actual = status["estrategia"]

    try:
        from cfo_market_phase import snapshot_fase
        fase_data = snapshot_fase(symbol, use_cache=True)
        fase = fase_data["fase_estrutural"]["fase"]
        estrategia_ideal = FASE_PARA_ESTRATEGIA.get(fase, "grid")
        razao = fase_data.get("estrategia_razao", "")
    except Exception as e:
        return {"status": "erro", "message": str(e)}

    mudanca = estrategia_ideal != estrategia_actual

    resultado = {
        "coin": coin,
        "symbol": symbol,
        "fase_actual": fase,
        "estrategia_actual": estrategia_actual,
        "estrategia_ideal": estrategia_ideal,
        "mudanca_necessaria": mudanca,
        "razao": razao,
    }

    if not mudanca:
        resultado["mensagem"] = f"{coin}: estratégia actual ({estrategia_actual}) já é a ideal para fase {fase}. Nada a mudar."
        return resultado

    if mod.tem_posicoes_abertas():
        resultado["pode_trocar"] = False
        resultado["mensagem"] = (
            f"{coin}: mudança recomendada ({estrategia_actual} → {estrategia_ideal}) "
            f"mas BLOQUEADA: há posições abertas. Aguardar fecharem."
        )
    else:
        resultado["pode_trocar"] = True
        resultado["mensagem"] = (
            f"{coin}: recomendo mudar de {estrategia_actual} para {estrategia_ideal}. "
            f"Razão: {razao}. Sem posições abertas — seguro trocar. Confirmas?"
        )

    return resultado


def analisar_todos() -> list:
    """Analisa os 3 bots e retorna recomendações."""
    return [analisar_e_recomendar(coin) for coin in BOTS]


def executar_troca(coin: str, nova_estrategia: str) -> dict:
    """Executa troca. Chamar só após 'sim' explícito do Vasco."""
    if coin not in BOTS:
        return {"status": "erro", "message": f"Coin inválida: {coin}"}
    mod, _ = _get_bot_module(coin)
    return mod.set_estrategia(nova_estrategia)


def resumo_para_cfo() -> str:
    linhas = []
    for coin, (module_name, _) in BOTS.items():
        try:
            import importlib
            mod = importlib.import_module(module_name)
            s = mod.get_status()
            linhas.append(
                f"{coin}/{s['estrategia']} | PnL ${s['pnl_total']:+.2f} | "
                f"Trades: {s['total_trades']} | ${s['last_price']}"
            )
        except Exception as e:
            linhas.append(f"{coin}: erro — {e}")
    return " | ".join(linhas)


if __name__ == "__main__":
    import json
    print(json.dumps(analisar_todos(), indent=2, ensure_ascii=False))
