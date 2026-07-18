"""
BCVertex — DCA Bot (SOL/USDT)
Estratégia: Compra metade do capital disponível quando SOL cai ≥5%.
Vende tudo quando sobe ≥8% desde o último ponto de referência.
Backtest 18m: +$54, 14 trades, sem leverage, sem liquidação.
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
    "symbol":        "SOL/USDT",
    "timeframe":     "4h",
    "capital":       float(os.getenv("DCA_CAPITAL", "100")),
    "drop_pct":      0.05,   # compra quando cai 5% do último ponto de referência
    "sell_pct":      0.08,   # vende quando sobe 8% do último ponto de referência
    "buy_fraction":  0.50,   # usa 50% do cash disponível em cada compra
    "commission":    0.001,
}

STATE_FILE = Path("memory/dca_state.json")


# ── Estado ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "active":    True,
        "cash":      CONFIG["capital"],
        "qty":       0.0,
        "ref_price": None,     # último preço de referência (compra ou venda)
        "pnl_total": 0.0,
        "pnl_today": 0.0,
        "trades":    [],
        "last_check": "",
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


# ── Ciclo principal ───────────────────────────────────────────────────────────

def run_dca_cycle() -> dict:
    state = load_state()
    if not state.get("active", True):
        return {"status": "pausado", "bot": "DCA SOL/USDT"}

    try:
        ex = get_exchange()
        ohlcv = ex.fetch_ohlcv(CONFIG["symbol"], CONFIG["timeframe"], limit=2)
        price = ohlcv[-1][4]

        state["last_check"] = datetime.now(timezone.utc).isoformat()

        # Inicializa preço de referência na primeira execução
        if state["ref_price"] is None:
            state["ref_price"] = price
            save_state(state)
            return {"status": "ok", "bot": "DCA SOL/USDT", "price": price,
                    "message": "Referência iniciada", "ref_price": price}

        ref = state["ref_price"]
        pct = (price - ref) / ref

        # Vender: subiu ≥8% desde referência E temos SOL em carteira
        if pct >= CONFIG["sell_pct"] and state["qty"] > 0:
            qty = state["qty"]
            receita = qty * price * (1 - CONFIG["commission"])
            custo = qty * ref
            pnl = receita - custo
            state["cash"] += receita
            state["qty"] = 0.0
            state["pnl_total"] = round(state.get("pnl_total", 0) + pnl, 4)
            state["pnl_today"] = round(state.get("pnl_today", 0) + pnl, 4)
            state["ref_price"] = price
            state["trades"].append({
                "action": "sell", "price": price, "qty": round(qty, 6),
                "pnl": round(pnl, 4), "ref": ref,
                "date": datetime.now(timezone.utc).isoformat(),
            })
            if not TESTNET:
                ex.create_order(CONFIG["symbol"], "market", "sell", round(qty, 4))
            save_state(state)
            logger.info(f"[DCA] Vendeu {qty:.4f} SOL @ {price:.2f} | PnL {pnl:+.4f}")
            return {"status": "trade_fechado", "bot": "DCA SOL/USDT",
                    "action": "sell", "price": price, "qty": qty,
                    "pnl": pnl, "pnl_total": state["pnl_total"]}

        # Comprar: caiu ≥5% desde referência E temos cash
        if pct <= -CONFIG["drop_pct"] and state["cash"] >= 10:
            invest = state["cash"] * CONFIG["buy_fraction"]
            qty = invest * (1 - CONFIG["commission"]) / price
            state["cash"] -= invest
            state["qty"] += qty
            state["ref_price"] = price
            state["trades"].append({
                "action": "buy", "price": price, "qty": round(qty, 6),
                "invest": round(invest, 4),
                "date": datetime.now(timezone.utc).isoformat(),
            })
            if not TESTNET:
                ex.create_order(CONFIG["symbol"], "market", "buy", round(qty, 4))
            save_state(state)
            logger.info(f"[DCA] Comprou {qty:.4f} SOL @ {price:.2f} | investiu {invest:.2f}")
            return {"status": "compra", "bot": "DCA SOL/USDT",
                    "price": price, "qty": qty, "invest": invest}

        save_state(state)
        return {
            "status": "ok", "bot": "DCA SOL/USDT",
            "price": price, "ref_price": ref,
            "pct_from_ref": round(pct * 100, 2),
            "cash": round(state["cash"], 2),
            "qty_sol": round(state["qty"], 6),
            "pnl_total": state.get("pnl_total", 0),
            "trades": len(state.get("trades", [])),
        }

    except Exception as e:
        logger.error(f"[DCA] Erro: {e}")
        return {"status": "erro", "bot": "DCA SOL/USDT", "message": str(e)}


def get_dca_status() -> dict:
    state = load_state()
    try:
        ex = get_exchange()
        price = ex.fetch_ticker(CONFIG["symbol"])["last"]
        valor_sol = state.get("qty", 0) * price
    except Exception:
        price = None
        valor_sol = None

    return {
        "bot": "DCA SOL/USDT",
        "active": state.get("active", True),
        "cash": round(state.get("cash", 0), 2),
        "qty_sol": round(state.get("qty", 0), 6),
        "valor_sol_usdt": round(valor_sol, 2) if valor_sol else None,
        "ref_price": state.get("ref_price"),
        "pnl_total": state.get("pnl_total", 0),
        "pnl_today": state.get("pnl_today", 0),
        "trades": len(state.get("trades", [])),
        "last_check": state.get("last_check", ""),
    }

def reset_dca_daily_pnl():
    state = load_state(); state["pnl_today"] = 0.0; save_state(state)

def pause_dca():
    state = load_state(); state["active"] = False; save_state(state)

def resume_dca():
    state = load_state(); state["active"] = True; save_state(state)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_dca_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
