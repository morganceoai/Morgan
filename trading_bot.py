"""
BC Industries — Trading Bot
Braço de investimento automatizado do império.
Corre autonomamente, reporta ao Morgan CEO.
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────────────────────

TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

CONFIG = {
    "symbol":         "BTC/USDT",
    "timeframe":      "30m",
    "capital":        float(os.getenv("BOT_CAPITAL", "100")),  # USDT a usar
    "risk_per_trade": 0.02,                                     # 2% do capital por trade
    "stop_loss":      0.015,                                    # 1.5% stop loss
    "take_profit":    0.03,                                     # 3% take profit
    "ema_fast":       9,
    "ema_slow":       21,
    "max_drawdown_day":   0.05,   # para se perder >5% do capital num dia
    "max_drawdown_total": 0.15,   # para se perder >15% do capital total
}

STATE_FILE = Path("memory/trading_state.json")


# ── Estado persistente ────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "active":       True,
        "position":     None,     # {"side": "long", "entry": 0.0, "size": 0.0, "opened_at": ""}
        "trades":       [],
        "pnl_total":    0.0,
        "pnl_today":    0.0,
        "last_check":   "",
        "last_signal":  "",
    }

def save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ── Exchange ──────────────────────────────────────────────────────────────────

def get_exchange():
    try:
        import ccxt
    except ImportError:
        raise RuntimeError("ccxt não instalado. Corre: pip install ccxt")

    params = {
        "apiKey":  os.getenv("BINANCE_API_KEY", ""),
        "secret":  os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    }
    if TESTNET:
        params["options"]["testnet"] = True

    exchange = ccxt.binance(params)
    if TESTNET:
        exchange.set_sandbox_mode(True)
    return exchange


# ── Indicadores ───────────────────────────────────────────────────────────────

def ema(prices: list[float], period: int) -> float:
    """EMA do último valor."""
    if len(prices) < period:
        return prices[-1]
    k = 2 / (period + 1)
    val = prices[0]
    for p in prices[1:]:
        val = p * k + val * (1 - k)
    return val

def get_signal(closes: list[float]) -> str:
    """Retorna 'buy', 'sell' ou 'hold'."""
    fast = ema(closes, CONFIG["ema_fast"])
    slow = ema(closes, CONFIG["ema_slow"])
    prev_fast = ema(closes[:-1], CONFIG["ema_fast"])
    prev_slow = ema(closes[:-1], CONFIG["ema_slow"])

    if prev_fast <= prev_slow and fast > slow:
        return "buy"
    if prev_fast >= prev_slow and fast < slow:
        return "sell"
    return "hold"


# ── Gestão de risco ───────────────────────────────────────────────────────────

def position_size(capital: float, price: float) -> float:
    """Calcula tamanho da posição com risco fixo."""
    risk_amount = capital * CONFIG["risk_per_trade"]
    stop_distance = price * CONFIG["stop_loss"]
    size = risk_amount / stop_distance
    return round(size, 6)

def check_exits(state: dict, current_price: float) -> str | None:
    """Verifica se deve fechar posição por SL ou TP."""
    pos = state.get("position")
    if not pos:
        return None
    entry = pos["entry"]
    if pos["side"] == "long":
        if current_price <= entry * (1 - CONFIG["stop_loss"]):
            return "stop_loss"
        if current_price >= entry * (1 + CONFIG["take_profit"]):
            return "take_profit"
    return None


# ── Execução ──────────────────────────────────────────────────────────────────

def fetch_ohlcv(exchange) -> list[float]:
    """Busca as últimas velas e retorna os closes."""
    ohlcv = exchange.fetch_ohlcv(
        CONFIG["symbol"], CONFIG["timeframe"], limit=50
    )
    return [c[4] for c in ohlcv]  # close prices

def open_position(exchange, state: dict, price: float, side: str):
    size = position_size(state.get("capital_available", CONFIG["capital"]), price)
    now = datetime.now(timezone.utc).isoformat()

    if not TESTNET:
        exchange.create_order(
            CONFIG["symbol"], "market", side, size
        )

    state["position"] = {
        "side": side, "entry": price,
        "size": size, "opened_at": now,
    }
    logger.info(f"[BOT] Abriu {side} {size} {CONFIG['symbol']} @ {price:.2f}")

def close_position(exchange, state: dict, price: float, reason: str):
    pos = state["position"]
    if not TESTNET:
        side = "sell" if pos["side"] == "long" else "buy"
        exchange.create_order(CONFIG["symbol"], "market", side, pos["size"])

    pnl = (price - pos["entry"]) * pos["size"]
    if pos["side"] == "short":
        pnl = -pnl

    state["pnl_total"] = round(state.get("pnl_total", 0) + pnl, 4)
    state["pnl_today"] = round(state.get("pnl_today", 0) + pnl, 4)
    state["trades"].append({
        "symbol":    CONFIG["symbol"],
        "side":      pos["side"],
        "entry":     pos["entry"],
        "exit":      price,
        "size":      pos["size"],
        "pnl":       round(pnl, 4),
        "reason":    reason,
        "closed_at": datetime.now(timezone.utc).isoformat(),
    })
    state["position"] = None
    logger.info(f"[BOT] Fechou posição @ {price:.2f} | PnL: {pnl:+.4f} USDT | Motivo: {reason}")
    return pnl


# ── Ciclo principal ───────────────────────────────────────────────────────────

def check_drawdown(state: dict) -> dict | None:
    """Verifica se drawdown diário ou total foi atingido. Retorna alerta ou None."""
    capital = CONFIG["capital"]
    loss_today = state.get("pnl_today", 0)
    loss_total = state.get("pnl_total", 0)

    if loss_today <= -(capital * CONFIG["max_drawdown_day"]):
        state["active"] = False
        save_state(state)
        return {
            "status":  "drawdown_diario",
            "message": f"⛔ Bot pausado automaticamente — perda diária atingiu {loss_today:.4f} USDT ({CONFIG['max_drawdown_day']*100:.0f}% do capital). Retoma com /bot retomar.",
        }
    if loss_total <= -(capital * CONFIG["max_drawdown_total"]):
        state["active"] = False
        save_state(state)
        return {
            "status":  "drawdown_total",
            "message": f"⛔ Bot pausado automaticamente — perda total atingiu {loss_total:.4f} USDT ({CONFIG['max_drawdown_total']*100:.0f}% do capital). Requer revisão manual.",
        }
    return None


def run_cycle() -> dict:
    """
    Corre um ciclo de análise e execução.
    Retorna relatório para o CEO/CFO.
    """
    state = load_state()
    if not state.get("active", True):
        return {"status": "pausado", "message": "Bot pausado pelo Vasco."}

    alert = check_drawdown(state)
    if alert:
        return alert

    try:
        exchange = get_exchange()
        closes = fetch_ohlcv(exchange)
        price = closes[-1]
        signal = get_signal(closes)

        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_signal"] = signal

        # Verifica exits antes de novos sinais
        exit_reason = check_exits(state, price)
        if exit_reason:
            pnl = close_position(exchange, state, price, exit_reason)
            save_state(state)
            return {
                "status": "trade_fechado",
                "symbol": CONFIG["symbol"],
                "price":  price,
                "reason": exit_reason,
                "pnl":    pnl,
                "pnl_total": state["pnl_total"],
            }

        # Novos sinais
        if signal == "buy" and not state.get("position"):
            open_position(exchange, state, price, "long")

        elif signal == "sell" and state.get("position", {}).get("side") == "long":
            pnl = close_position(exchange, state, price, "sinal_venda")

        save_state(state)
        return {
            "status":     "ok",
            "symbol":     CONFIG["symbol"],
            "price":      price,
            "signal":     signal,
            "position":   state.get("position"),
            "pnl_total":  state.get("pnl_total", 0),
            "pnl_today":  state.get("pnl_today", 0),
            "trades":     len(state.get("trades", [])),
            "testnet":    TESTNET,
        }

    except Exception as e:
        logger.error(f"[BOT] Erro no ciclo: {e}")
        return {"status": "erro", "message": str(e)}


def get_status() -> dict:
    """Retorna estado atual para o dashboard."""
    state = load_state()
    return {
        "active":    state.get("active", True),
        "position":  state.get("position"),
        "pnl_total": state.get("pnl_total", 0),
        "pnl_today": state.get("pnl_today", 0),
        "trades":    len(state.get("trades", [])),
        "last_check": state.get("last_check", ""),
        "last_signal": state.get("last_signal", ""),
        "symbol":    CONFIG["symbol"],
        "testnet":   TESTNET,
    }

def pause_bot():
    state = load_state()
    state["active"] = False
    save_state(state)

def resume_bot():
    state = load_state()
    state["active"] = True
    save_state(state)

def reset_daily_pnl():
    state = load_state()
    state["pnl_today"] = 0.0
    save_state(state)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("[BOT] A correr ciclo manual...")
    result = run_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
