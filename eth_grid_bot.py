"""
BCVertex — Grid Bot ETH/USDT
Estratégia: grid de 10 níveis em torno do preço de arranque.
ETH tem ATR ~20% maior que BTC → range 10% para capturar mais oscilações.
Capital: $100 USDT. Corre em paralelo com o grid BTC.
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
    "symbol":        "ETH/USDT",
    "capital":       float(os.getenv("ETH_BOT_CAPITAL", "100")),
    "n_levels":      10,
    "range_pct":     0.10,   # ±5% — ETH mais volátil que BTC
    "capital_pct":   0.90,
    "max_open":      5,
    "fee":           0.001,
}

STATE_FILE = Path("memory/eth_grid_state.json")


# ── Estado ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "active": True,
        "ref_price": None,
        "level_size": None,
        "capital_per_level": None,
        "open_positions": {},
        "trades": [],
        "pnl_total": 0.0,
        "pnl_today": 0.0,
        "last_check": "",
        "last_price": None,
        "created_at": "",
    }

def save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str))


# ── Exchange ──────────────────────────────────────────────────────────────────

def get_exchange():
    import ccxt
    ex = ccxt.binance({
        "apiKey":  os.getenv("BINANCE_API_KEY", ""),
        "secret":  os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })
    if TESTNET:
        ex.set_sandbox_mode(True)
    return ex


# ── Lógica do grid ────────────────────────────────────────────────────────────

def _nivel_actual(price: float, ref: float, level_size: float) -> int:
    return round((price - ref) / level_size)

def _inicializar_grid(price: float, state: dict) -> dict:
    level_size = price * CONFIG["range_pct"] / CONFIG["n_levels"]
    capital_por_nivel = (CONFIG["capital"] * CONFIG["capital_pct"]) / CONFIG["n_levels"]
    state["ref_price"] = round(price, 2)
    state["level_size"] = round(level_size, 4)
    state["capital_per_level"] = round(capital_por_nivel, 4)
    state["created_at"] = datetime.now(timezone.utc).isoformat()
    state["open_positions"] = {}
    logger.info(
        f"[ETH Grid] Iniciado @ ${price:.2f} | "
        f"Range ${price - CONFIG['n_levels']//2 * level_size:.2f}–"
        f"${price + CONFIG['n_levels']//2 * level_size:.2f} | "
        f"Nível: ${level_size:.2f} | Capital/nível: ${capital_por_nivel:.2f}"
    )
    return state


# ── Ciclo principal ───────────────────────────────────────────────────────────

def run_cycle() -> dict:
    state = load_state()

    if not state.get("active", True):
        return {"status": "pausado", "message": "ETH Grid Bot pausado."}

    try:
        ex = get_exchange()
        ticker = ex.fetch_ticker(CONFIG["symbol"])
        price = ticker["last"]

        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_price"] = price

        if state["ref_price"] is None:
            state = _inicializar_grid(price, state)
            save_state(state)
            return {
                "status": "grid_iniciado",
                "ref_price": state["ref_price"],
                "level_size": state["level_size"],
                "capital_per_level": state["capital_per_level"],
            }

        ref = state["ref_price"]
        level_size = state["level_size"]
        capital_per_level = state["capital_per_level"]
        open_positions = state["open_positions"]
        nivel_actual = _nivel_actual(price, ref, level_size)

        acoes = []

        # ── Saídas ───────────────────────────────────────────────────────────
        for nivel_str, pos in list(open_positions.items()):
            entry = pos["entry"]
            size = pos["size"]
            target_exit = entry + level_size
            if price >= target_exit:
                pnl_gross = (price - entry) * size
                fee_cost = price * size * CONFIG["fee"] * 2
                pnl_net = pnl_gross - fee_cost
                state["pnl_total"] = round(state.get("pnl_total", 0) + pnl_net, 4)
                state["pnl_today"] = round(state.get("pnl_today", 0) + pnl_net, 4)
                state["trades"].append({
                    "nivel": int(nivel_str),
                    "entry": entry,
                    "exit": round(price, 4),
                    "size": size,
                    "pnl": round(pnl_net, 4),
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                })
                del open_positions[nivel_str]
                if not TESTNET:
                    ex.create_order(CONFIG["symbol"], "market", "sell", size)
                acoes.append(f"VENDA nivel {nivel_str} @ ${price:.2f} | PnL ${pnl_net:+.4f}")
                logger.info(f"[ETH Grid] SELL nivel {nivel_str} @ ${price:.2f} | PnL ${pnl_net:+.4f}")

        # ── Entradas ─────────────────────────────────────────────────────────
        min_nivel = -CONFIG["n_levels"] // 2
        niveis_para_entrar = [
            n for n in range(min_nivel, nivel_actual)
            if str(n) not in open_positions and n < nivel_actual
        ]

        if niveis_para_entrar and len(open_positions) < CONFIG["max_open"]:
            nivel_entrada = max(niveis_para_entrar)
            if nivel_entrada < nivel_actual:
                size = round(capital_per_level / price, 6)
                min_notional = 10.0
                if size * price >= min_notional:
                    if not TESTNET:
                        ex.create_order(CONFIG["symbol"], "market", "buy", size)
                    open_positions[str(nivel_entrada)] = {
                        "entry": round(price, 4),
                        "size": size,
                        "opened_at": datetime.now(timezone.utc).isoformat(),
                    }
                    acoes.append(f"COMPRA nivel {nivel_entrada} @ ${price:.2f} | size {size}")
                    logger.info(f"[ETH Grid] BUY nivel {nivel_entrada} @ ${price:.2f} | size {size}")

        state["open_positions"] = open_positions
        if len(state["trades"]) > 500:
            state["trades"] = state["trades"][-500:]
        save_state(state)

        return {
            "status": "ok",
            "price": price,
            "nivel_actual": nivel_actual,
            "ref_price": ref,
            "open_positions": len(open_positions),
            "pnl_total": state["pnl_total"],
            "pnl_today": state["pnl_today"],
            "total_trades": len(state["trades"]),
            "acoes": acoes,
            "grid_range": {
                "lower": round(ref + min_nivel * level_size, 2),
                "upper": round(ref + (CONFIG["n_levels"] // 2) * level_size, 2),
            },
        }

    except Exception as e:
        logger.error(f"[ETH Grid] Erro: {e}")
        return {"status": "erro", "message": str(e)}


def get_status() -> dict:
    state = load_state()
    ref = state.get("ref_price")
    lvl = state.get("level_size")
    grid_range = None
    if ref and lvl:
        grid_range = {
            "lower": round(ref - 5 * lvl, 2),
            "upper": round(ref + 5 * lvl, 2),
        }
    return {
        "bot": "Grid ETH/USDT",
        "active": state.get("active", True),
        "ref_price": ref,
        "level_size": lvl,
        "capital_per_level": state.get("capital_per_level"),
        "open_positions": len(state.get("open_positions", {})),
        "open_positions_detail": state.get("open_positions", {}),
        "pnl_total": state.get("pnl_total", 0),
        "pnl_today": state.get("pnl_today", 0),
        "total_trades": len(state.get("trades", [])),
        "last_check": state.get("last_check", ""),
        "last_price": state.get("last_price"),
        "created_at": state.get("created_at", ""),
        "testnet": TESTNET,
        "grid_range": grid_range,
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

def reset_grid():
    state = load_state()
    state["ref_price"] = None
    state["level_size"] = None
    state["capital_per_level"] = None
    state["open_positions"] = {}
    state["created_at"] = ""
    save_state(state)
    logger.info("[ETH Grid] Grid resetado.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
