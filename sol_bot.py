"""
BCVertex — SOL/USDT Bot
Estratégia configurável pelo CFO após aprovação do Vasco:
  - "dca"  : compra quando cai ≥5%, vende quando sobe ≥8%
  - "grid" : 10 níveis ±7% do preço de referência

Estado persistido em memory/sol_bot_state.json
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
SYMBOL  = "SOL/USDT"

DCA_CONFIG = {
    "capital":      float(os.getenv("SOL_CAPITAL", "100")),
    "drop_pct":     0.05,
    "sell_pct":     0.08,
    "buy_fraction": 0.50,
    "fee":          0.001,
}

GRID_CONFIG = {
    "capital":      float(os.getenv("SOL_CAPITAL", "100")),
    "n_levels":     10,
    "range_pct":    0.14,   # ±7%
    "capital_pct":  0.90,
    "max_open":     5,
    "fee":          0.001,
}

STATE_FILE = Path("memory/sol_bot_state.json")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_vazio() -> dict:
    return {
        "estrategia":       "dca",   # "dca" | "grid"
        "active":           True,
        # DCA
        "cash":             DCA_CONFIG["capital"],
        "qty":              0.0,
        "ref_price":        None,
        # Grid
        "grid_ref":         None,
        "level_size":       None,
        "capital_per_level":None,
        "open_positions":   {},
        # Comum
        "trades":           [],
        "pnl_total":        0.0,
        "pnl_today":        0.0,
        "last_check":       "",
        "last_price":       None,
        "created_at":       "",
    }

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return _estado_vazio()

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


# ── DCA ───────────────────────────────────────────────────────────────────────

def _run_dca(state: dict, ex, price: float) -> dict:
    cfg = DCA_CONFIG
    acoes = []

    if state["ref_price"] is None:
        state["ref_price"] = price
        logger.info(f"[SOL DCA] Referência inicial: ${price:.4f}")

    ref = state["ref_price"]

    # Venda
    if state["qty"] > 0 and price >= ref * (1 + cfg["sell_pct"]):
        size = state["qty"]
        revenue = size * price * (1 - cfg["fee"])
        pnl = revenue - (size * ref)
        state["pnl_total"] = round(state["pnl_total"] + pnl, 4)
        state["pnl_today"] = round(state["pnl_today"] + pnl, 4)
        state["cash"] += revenue
        state["qty"] = 0.0
        state["ref_price"] = price
        state["trades"].append({"tipo": "venda", "price": round(price, 4), "size": round(size, 4), "pnl": round(pnl, 4), "ts": datetime.now(timezone.utc).isoformat()})
        if not TESTNET:
            ex.create_order(SYMBOL, "market", "sell", size)
        acoes.append(f"VENDA {size:.4f} SOL @ ${price:.4f} | PnL ${pnl:+.4f}")
        logger.info(f"[SOL DCA] SELL {size:.4f} @ ${price:.4f} | PnL ${pnl:+.4f}")

    # Compra
    elif price <= ref * (1 - cfg["drop_pct"]) and state["cash"] > 10:
        buy_amount = state["cash"] * cfg["buy_fraction"]
        size = round(buy_amount / price * (1 - cfg["fee"]), 4)
        if size * price >= 10:
            state["cash"] -= buy_amount
            state["qty"] = round(state["qty"] + size, 4)
            state["ref_price"] = price
            state["trades"].append({"tipo": "compra", "price": round(price, 4), "size": size, "ts": datetime.now(timezone.utc).isoformat()})
            if not TESTNET:
                ex.create_order(SYMBOL, "market", "buy", size)
            acoes.append(f"COMPRA {size:.4f} SOL @ ${price:.4f}")
            logger.info(f"[SOL DCA] BUY {size:.4f} @ ${price:.4f}")

    return {"acoes": acoes, "qty": state["qty"], "cash": state["cash"]}


# ── Grid ──────────────────────────────────────────────────────────────────────

def _run_grid(state: dict, ex, price: float) -> dict:
    cfg = GRID_CONFIG
    acoes = []

    if state["grid_ref"] is None:
        level_size = price * cfg["range_pct"] / cfg["n_levels"]
        capital_por_nivel = (cfg["capital"] * cfg["capital_pct"]) / cfg["n_levels"]
        state["grid_ref"] = round(price, 4)
        state["level_size"] = round(level_size, 4)
        state["capital_per_level"] = round(capital_por_nivel, 4)
        state["open_positions"] = {}
        state["created_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[SOL Grid] Iniciado @ ${price:.4f} | Nível ${level_size:.4f}")

    ref        = state["grid_ref"]
    level_size = state["level_size"]
    cap_nivel  = state["capital_per_level"]
    positions  = state["open_positions"]
    nivel_now  = round((price - ref) / level_size)

    # Saídas
    for n_str, pos in list(positions.items()):
        if price >= pos["entry"] + level_size:
            pnl_gross = (price - pos["entry"]) * pos["size"]
            fee_cost  = price * pos["size"] * cfg["fee"] * 2
            pnl_net   = pnl_gross - fee_cost
            state["pnl_total"] = round(state["pnl_total"] + pnl_net, 4)
            state["pnl_today"] = round(state["pnl_today"] + pnl_net, 4)
            state["trades"].append({"nivel": int(n_str), "entry": pos["entry"], "exit": round(price, 4), "size": pos["size"], "pnl": round(pnl_net, 4), "ts": datetime.now(timezone.utc).isoformat()})
            del positions[n_str]
            if not TESTNET:
                ex.create_order(SYMBOL, "market", "sell", pos["size"])
            acoes.append(f"VENDA nivel {n_str} @ ${price:.4f} | PnL ${pnl_net:+.4f}")

    # Entradas
    min_nivel = -cfg["n_levels"] // 2
    candidatos = [n for n in range(min_nivel, nivel_now) if str(n) not in positions]
    if candidatos and len(positions) < cfg["max_open"]:
        n_entrada = max(candidatos)
        size = round(cap_nivel / price, 4)
        if size * price >= 10:
            if not TESTNET:
                ex.create_order(SYMBOL, "market", "buy", size)
            positions[str(n_entrada)] = {"entry": round(price, 4), "size": size, "opened_at": datetime.now(timezone.utc).isoformat()}
            acoes.append(f"COMPRA nivel {n_entrada} @ ${price:.4f} | size {size}")

    state["open_positions"] = positions
    return {"acoes": acoes, "open_positions": len(positions), "grid_ref": ref}


# ── Ciclo principal ───────────────────────────────────────────────────────────

def run_cycle() -> dict:
    state = load_state()

    if not state.get("active", True):
        return {"status": "pausado", "message": "SOL Bot pausado."}

    try:
        ex = get_exchange()
        price = ex.fetch_ticker(SYMBOL)["last"]
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_price"] = price

        estrategia = state.get("estrategia", "dca")
        if estrategia == "dca":
            resultado = _run_dca(state, ex, price)
        else:
            resultado = _run_grid(state, ex, price)

        if len(state["trades"]) > 500:
            state["trades"] = state["trades"][-500:]
        save_state(state)

        return {
            "status": "ok",
            "estrategia": estrategia,
            "price": price,
            "pnl_total": state["pnl_total"],
            "pnl_today": state["pnl_today"],
            "total_trades": len(state["trades"]),
            **resultado,
        }

    except Exception as e:
        logger.error(f"[SOL Bot] Erro: {e}")
        return {"status": "erro", "message": str(e)}


# ── Switching de estratégia ───────────────────────────────────────────────────

def tem_posicoes_abertas() -> bool:
    state = load_state()
    return state.get("qty", 0.0) > 0 or len(state.get("open_positions", {})) > 0

def set_estrategia(nova: str) -> dict:
    """Muda estratégia. Só chamar após aprovação do Vasco e sem posições abertas."""
    if nova not in ("dca", "grid"):
        return {"status": "erro", "message": f"Estratégia inválida: {nova}"}
    if tem_posicoes_abertas():
        return {"status": "bloqueado", "message": "Posições abertas — fecha antes de mudar estratégia."}
    state = load_state()
    anterior = state.get("estrategia", "dca")
    state["estrategia"] = nova
    # Reseta estado da nova estratégia
    if nova == "grid":
        state["grid_ref"] = None
        state["level_size"] = None
        state["capital_per_level"] = None
        state["open_positions"] = {}
    else:
        state["ref_price"] = None
        state["cash"] = DCA_CONFIG["capital"]
        state["qty"] = 0.0
    save_state(state)
    logger.info(f"[SOL Bot] Estratégia: {anterior} → {nova}")
    return {"status": "ok", "de": anterior, "para": nova}


# ── Status e utilitários ──────────────────────────────────────────────────────

def get_status() -> dict:
    state = load_state()
    return {
        "bot": "SOL/USDT",
        "estrategia": state.get("estrategia", "dca"),
        "active": state.get("active", True),
        "last_price": state.get("last_price"),
        "pnl_total": state.get("pnl_total", 0),
        "pnl_today": state.get("pnl_today", 0),
        "total_trades": len(state.get("trades", [])),
        "last_check": state.get("last_check", ""),
        "testnet": TESTNET,
        # DCA
        "qty": state.get("qty", 0),
        "cash": state.get("cash", 0),
        # Grid
        "open_positions": len(state.get("open_positions", {})),
        "grid_ref": state.get("grid_ref"),
    }

def pause_bot():
    state = load_state(); state["active"] = False; save_state(state)

def resume_bot():
    state = load_state(); state["active"] = True; save_state(state)

def reset_daily_pnl():
    state = load_state(); state["pnl_today"] = 0.0; save_state(state)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import json as _json
    print(_json.dumps(run_cycle(), indent=2, ensure_ascii=False))
