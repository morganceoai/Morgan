"""
BCVertex — Trading Bot (Supertrend ATR10×3)
Estratégia: Supertrend 4h, BTC/USDT spot, SL 3%, TP 9%.
Backtest 18m: +$48, win rate 66.7%, drawdown máx 4.3%.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

CONFIG = {
    "symbol":             "BTC/USDT",
    "timeframe":          "4h",
    "capital":            float(os.getenv("BOT_CAPITAL", "100")),
    "risk_per_trade":     0.95,   # usa 95% do capital por posição
    "stop_loss":          0.03,   # 3%
    "take_profit":        0.09,   # 9%
    "atr_period":         10,
    "atr_multiplier":     3.0,
    "max_drawdown_day":   0.05,
    "max_drawdown_total": 0.15,
}

STATE_FILE = Path("memory/trading_state.json")


# ── Estado ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "active": True,
        "position": None,
        "trades": [],
        "pnl_total": 0.0,
        "pnl_today": 0.0,
        "last_check": "",
        "last_signal": "",
        "trend": 1,
    }

def save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ── Exchange ──────────────────────────────────────────────────────────────────

def get_exchange():
    import ccxt
    ex = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY", ""),
        "secret": os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })
    if TESTNET:
        ex.set_sandbox_mode(True)
    return ex


# ── Indicadores ───────────────────────────────────────────────────────────────

def _atr(highs, lows, closes, n):
    tr = [0.0]
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    atr = [sum(tr[:n]) / n]
    for i in range(1, len(tr)):
        atr.append((atr[-1] * (n-1) + tr[i]) / n)
    return atr

def get_supertrend_signal(ohlcv: list, prev_trend: int) -> tuple:
    """Calcula sinal Supertrend. Devolve (signal, new_trend)."""
    n = CONFIG["atr_period"]
    mult = CONFIG["atr_multiplier"]

    highs  = [c[2] for c in ohlcv]
    lows   = [c[3] for c in ohlcv]
    closes = [c[4] for c in ohlcv]

    atr = _atr(highs, lows, closes, n)
    upper = [((highs[i] + lows[i]) / 2) + mult * atr[i] for i in range(len(closes))]
    lower = [((highs[i] + lows[i]) / 2) - mult * atr[i] for i in range(len(closes))]

    trend = prev_trend
    signal = "hold"

    for i in range(1, len(closes)):
        if closes[i] > upper[i-1]:
            new_trend = 1
        elif closes[i] < lower[i-1]:
            new_trend = -1
        else:
            new_trend = trend

        if new_trend != trend:
            # Sinal apenas na vela mais recente
            if i == len(closes) - 1:
                signal = "buy" if new_trend == 1 else "sell"
            trend = new_trend

    return signal, trend


# ── Ciclo principal ───────────────────────────────────────────────────────────

def run_cycle() -> dict:
    state = load_state()
    if not state.get("active", True):
        return {"status": "pausado", "message": "Bot pausado."}

    capital = CONFIG["capital"]
    if state.get("pnl_today", 0) <= -(capital * CONFIG["max_drawdown_day"]):
        state["active"] = False
        save_state(state)
        return {"status": "drawdown_diario",
                "message": f"⛔ Perda diária >{CONFIG['max_drawdown_day']*100:.0f}% — bot pausado."}
    if state.get("pnl_total", 0) <= -(capital * CONFIG["max_drawdown_total"]):
        state["active"] = False
        save_state(state)
        return {"status": "drawdown_total",
                "message": f"⛔ Perda total >{CONFIG['max_drawdown_total']*100:.0f}% — bot pausado."}

    try:
        ex = get_exchange()
        ohlcv = ex.fetch_ohlcv(CONFIG["symbol"], CONFIG["timeframe"], limit=60)
        closes = [c[4] for c in ohlcv]
        price = closes[-1]

        prev_trend = state.get("trend", 1)
        signal, new_trend = get_supertrend_signal(ohlcv, prev_trend)
        state["trend"] = new_trend
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_signal"] = signal

        pos = state.get("position")

        if pos:
            entry = pos["entry"]
            pct = (price - entry) / entry
            exit_reason = None
            if pct <= -CONFIG["stop_loss"]:
                exit_reason = "stop_loss"
            elif pct >= CONFIG["take_profit"]:
                exit_reason = "take_profit"
            elif signal == "sell":
                exit_reason = "sinal_venda"

            if exit_reason:
                size = pos["size"]
                pnl = (price - entry) * size * (1 - 0.001)
                state["pnl_total"] = round(state.get("pnl_total", 0) + pnl, 4)
                state["pnl_today"] = round(state.get("pnl_today", 0) + pnl, 4)
                state["trades"].append({
                    "symbol": CONFIG["symbol"], "entry": entry,
                    "exit": price, "size": size,
                    "pnl": round(pnl, 4), "reason": exit_reason,
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                })
                state["position"] = None
                if not TESTNET:
                    ex.create_order(CONFIG["symbol"], "market", "sell", size)
                save_state(state)
                logger.info(f"[Supertrend] Fechado @ {price:.2f} | {exit_reason} | PnL {pnl:+.4f}")
                return {"status": "trade_fechado", "symbol": CONFIG["symbol"],
                        "price": price, "reason": exit_reason,
                        "pnl": pnl, "pnl_total": state["pnl_total"]}

        if signal == "buy" and not pos:
            notional = capital * CONFIG["risk_per_trade"]
            size = round(notional / price, 6)
            state["position"] = {
                "entry": price, "size": size,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }
            if not TESTNET:
                ex.create_order(CONFIG["symbol"], "market", "buy", size)
            save_state(state)
            logger.info(f"[Supertrend] Compra @ {price:.2f} | size {size}")
            return {"status": "compra", "symbol": CONFIG["symbol"], "price": price, "size": size}

        save_state(state)
        return {
            "status": "ok", "symbol": CONFIG["symbol"],
            "price": price, "signal": signal, "trend": new_trend,
            "position": pos,
            "pnl_total": state.get("pnl_total", 0),
            "pnl_today": state.get("pnl_today", 0),
            "trades": len(state.get("trades", [])),
        }

    except Exception as e:
        logger.error(f"[Supertrend] Erro: {e}")
        return {"status": "erro", "message": str(e)}


def get_status() -> dict:
    state = load_state()
    return {
        "bot": "Supertrend BTC/USDT 4h",
        "active": state.get("active", True),
        "position": state.get("position"),
        "pnl_total": state.get("pnl_total", 0),
        "pnl_today": state.get("pnl_today", 0),
        "trades": len(state.get("trades", [])),
        "last_check": state.get("last_check", ""),
        "last_signal": state.get("last_signal", ""),
        "trend": state.get("trend", 1),
        "testnet": TESTNET,
    }

def pause_bot():
    state = load_state(); state["active"] = False; save_state(state)

def resume_bot():
    state = load_state(); state["active"] = True; save_state(state)

def reset_daily_pnl():
    state = load_state(); state["pnl_today"] = 0.0; save_state(state)

# Compatibilidade com desktop_server.py
run_multi_pair_cycle = lambda: [run_cycle()]
get_multi_status = lambda: [get_status()]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
