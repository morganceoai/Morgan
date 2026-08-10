"""
BCVertex — BTC/USDT Bot
Estratégia configurável pelo CFO após aprovação do Vasco:
  - "grid"          : N níveis ±4% — mercado lateral
  - "dca"           : compra quando cai ≥5%, vende quando sobe ≥8% — mercado bear
  - "trailing_stop" : segue o pico, vende se cair ≥8% do máximo — mercado bull
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

SYMBOL = "BTC/USDT"

CONFIG = {
    "symbol":        SYMBOL,
    "capital":       float(os.getenv("BOT_CAPITAL", "100")),
    "n_levels":      10,
    "range_pct":     0.08,   # grid cobre ±4% do preço de referência
    "capital_pct":   0.90,
    "max_open":      5,
    "fee":           0.001,
}

DCA_CONFIG = {
    "capital":      float(os.getenv("BOT_CAPITAL", "100")),
    "drop_pct":     0.05,
    "sell_pct":     0.08,
    "buy_fraction": 0.50,
    "fee":          0.001,
}

TRAILING_CONFIG = {
    "capital":      float(os.getenv("BOT_CAPITAL", "100")),
    "capital_pct":  0.90,
    "trail_pct":    0.08,
    "fee":          0.001,
}

STATE_FILE = Path("memory/grid_state.json")


# ── Estado ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "estrategia": "grid",
        "active": True,
        # Grid
        "ref_price": None,
        "level_size": None,
        "capital_per_level": None,
        "open_positions": {},
        # DCA
        "dca_cash": DCA_CONFIG["capital"],
        "dca_qty": 0.0,
        "dca_ref": None,
        # Trailing Stop
        "ts_qty": 0.0,
        "ts_cash": TRAILING_CONFIG["capital"],
        "ts_entry": None,
        "ts_peak": None,
        # Comum
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


# ── DCA ───────────────────────────────────────────────────────────────────────

def _run_dca(state: dict, ex, price: float) -> dict:
    cfg = DCA_CONFIG
    acoes = []
    if state.get("dca_ref") is None:
        state["dca_ref"] = price

    ref = state["dca_ref"]

    if state.get("dca_qty", 0.0) > 0 and price >= ref * (1 + cfg["sell_pct"]):
        size = state["dca_qty"]
        revenue = size * price * (1 - cfg["fee"])
        pnl = revenue - (size * ref)
        state["pnl_total"] = round(state["pnl_total"] + pnl, 4)
        state["pnl_today"] = round(state["pnl_today"] + pnl, 4)
        state["dca_cash"] = round(state.get("dca_cash", 0) + revenue, 4)
        state["dca_qty"] = 0.0
        state["dca_ref"] = price
        state["trades"].append({"tipo": "dca_venda", "price": round(price, 2), "size": round(size, 6), "pnl": round(pnl, 4), "ts": datetime.now(timezone.utc).isoformat()})
        if not TESTNET:
            ex.create_order(SYMBOL, "market", "sell", size)
        acoes.append(f"DCA VENDA {size:.6f} BTC @ ${price:.2f} | PnL ${pnl:+.4f}")

    elif price <= ref * (1 - cfg["drop_pct"]) and state.get("dca_cash", 0) > 10:
        buy_amount = state["dca_cash"] * cfg["buy_fraction"]
        size = round(buy_amount / price * (1 - cfg["fee"]), 6)
        if size * price >= 10:
            state["dca_cash"] = round(state["dca_cash"] - buy_amount, 4)
            state["dca_qty"] = round(state.get("dca_qty", 0) + size, 6)
            state["dca_ref"] = price
            state["trades"].append({"tipo": "dca_compra", "price": round(price, 2), "size": size, "ts": datetime.now(timezone.utc).isoformat()})
            if not TESTNET:
                ex.create_order(SYMBOL, "market", "buy", size)
            acoes.append(f"DCA COMPRA {size:.6f} BTC @ ${price:.2f}")

    return {"acoes": acoes, "dca_qty": state.get("dca_qty", 0), "dca_cash": state.get("dca_cash", 0)}


# ── Trailing Stop ─────────────────────────────────────────────────────────────

def _run_trailing_stop(state: dict, ex, price: float) -> dict:
    cfg = TRAILING_CONFIG
    acoes = []

    if state.get("ts_qty", 0.0) == 0.0:
        cash = state.get("ts_cash", cfg["capital"])
        if cash > 10:
            buy_amount = cash * cfg["capital_pct"]
            size = round(buy_amount / price * (1 - cfg["fee"]), 6)
            if size * price >= 10:
                state["ts_qty"] = size
                state["ts_cash"] = round(cash - buy_amount, 4)
                state["ts_entry"] = price
                state["ts_peak"] = price
                state["trades"].append({"tipo": "ts_compra", "price": round(price, 2), "size": size, "ts": datetime.now(timezone.utc).isoformat()})
                if not TESTNET:
                    ex.create_order(SYMBOL, "market", "buy", size)
                acoes.append(f"TS COMPRA {size:.6f} BTC @ ${price:.2f}")
                logger.info(f"[BTC TS] COMPRA {size:.6f} @ ${price:.2f}")
    else:
        if price > state.get("ts_peak", price):
            state["ts_peak"] = price
        stop_price = state["ts_peak"] * (1 - cfg["trail_pct"])
        if price <= stop_price:
            size = state["ts_qty"]
            revenue = size * price * (1 - cfg["fee"])
            pnl = revenue - (size * state["ts_entry"])
            state["pnl_total"] = round(state["pnl_total"] + pnl, 4)
            state["pnl_today"] = round(state["pnl_today"] + pnl, 4)
            state["ts_cash"] = round(state.get("ts_cash", 0) + revenue, 4)
            state["ts_qty"] = 0.0
            state["ts_entry"] = None
            state["ts_peak"] = None
            state["trades"].append({"tipo": "ts_venda", "price": round(price, 2), "size": size, "pnl": round(pnl, 4), "ts": datetime.now(timezone.utc).isoformat()})
            if not TESTNET:
                ex.create_order(SYMBOL, "market", "sell", size)
            acoes.append(f"TS VENDA {size:.6f} BTC @ ${price:.2f} | PnL ${pnl:+.4f}")
            logger.info(f"[BTC TS] VENDA {size:.6f} @ ${price:.2f} | PnL ${pnl:+.4f}")

    ts_peak = state.get("ts_peak")
    return {
        "acoes": acoes,
        "ts_qty": state.get("ts_qty", 0),
        "ts_peak": ts_peak,
        "ts_stop": round(ts_peak * (1 - cfg["trail_pct"]), 2) if ts_peak else None,
    }


# ── Lógica do grid ────────────────────────────────────────────────────────────

def _preco_nivel(ref: float, nivel: int, level_size: float) -> float:
    """Preço alvo do nível N (negativo = abaixo da ref, positivo = acima)."""
    return ref + nivel * level_size

def _nivel_actual(price: float, ref: float, level_size: float) -> int:
    """Em que nível está o preço actual (arredondado)."""
    return round((price - ref) / level_size)

def _inicializar_grid(price: float, state: dict) -> dict:
    """Define os parâmetros do grid com base no preço actual."""
    level_size = price * CONFIG["range_pct"] / CONFIG["n_levels"]
    capital_por_nivel = (CONFIG["capital"] * CONFIG["capital_pct"]) / CONFIG["n_levels"]
    state["ref_price"] = round(price, 2)
    state["level_size"] = round(level_size, 2)
    state["capital_per_level"] = round(capital_por_nivel, 4)
    state["created_at"] = datetime.now(timezone.utc).isoformat()
    state["open_positions"] = {}
    logger.info(
        f"[Grid] Iniciado @ ${price:.2f} | "
        f"Range ${price - CONFIG['n_levels']//2 * level_size:.2f}–"
        f"${price + CONFIG['n_levels']//2 * level_size:.2f} | "
        f"Nível: ${level_size:.2f} | Capital/nível: ${capital_por_nivel:.2f}"
    )
    return state


# ── Ciclo principal ───────────────────────────────────────────────────────────

def _run_grid_cycle(state: dict, ex, price: float) -> dict:
    acoes = []
    if state["ref_price"] is None:
        state = _inicializar_grid(price, state)
        save_state(state)
        return {"status": "grid_iniciado", "ref_price": state["ref_price"], "level_size": state["level_size"]}

    ref = state["ref_price"]
    level_size = state["level_size"]
    capital_per_level = state["capital_per_level"]
    open_positions = state["open_positions"]
    nivel_actual = _nivel_actual(price, ref, level_size)

    for nivel_str, pos in list(open_positions.items()):
        nivel = int(nivel_str)
        entry = pos["entry"]
        size = pos["size"]
        if price >= entry + level_size:
            pnl_gross = (price - entry) * size
            fee_cost = price * size * CONFIG["fee"] * 2
            pnl_net = pnl_gross - fee_cost
            state["pnl_total"] = round(state.get("pnl_total", 0) + pnl_net, 4)
            state["pnl_today"] = round(state.get("pnl_today", 0) + pnl_net, 4)
            state["trades"].append({"nivel": nivel, "entry": entry, "exit": round(price, 2), "size": size, "pnl": round(pnl_net, 4), "closed_at": datetime.now(timezone.utc).isoformat()})
            del open_positions[nivel_str]
            if not TESTNET:
                ex.create_order(SYMBOL, "market", "sell", size)
            acoes.append(f"VENDA nivel {nivel} @ ${price:.2f} | PnL ${pnl_net:+.4f}")
            logger.info(f"[BTC Grid] SELL nivel {nivel} @ ${price:.2f} | PnL ${pnl_net:+.4f}")

    min_nivel = -CONFIG["n_levels"] // 2
    niveis_para_entrar = [n for n in range(min_nivel, nivel_actual) if str(n) not in open_positions]
    if niveis_para_entrar and len(open_positions) < CONFIG["max_open"]:
        nivel_entrada = max(niveis_para_entrar)
        if nivel_entrada < nivel_actual:
            size = round(capital_per_level / price, 6)
            if size * price >= 10:
                if not TESTNET:
                    ex.create_order(SYMBOL, "market", "buy", size)
                open_positions[str(nivel_entrada)] = {"entry": round(price, 2), "size": size, "opened_at": datetime.now(timezone.utc).isoformat()}
                acoes.append(f"COMPRA nivel {nivel_entrada} @ ${price:.2f} | size {size}")
                logger.info(f"[BTC Grid] BUY nivel {nivel_entrada} @ ${price:.2f} | size {size}")

    state["open_positions"] = open_positions
    return {
        "acoes": acoes,
        "open_positions": len(open_positions),
        "nivel_actual": nivel_actual,
        "grid_range": {"lower": round(ref + min_nivel * level_size, 2), "upper": round(ref + (CONFIG["n_levels"] // 2) * level_size, 2)},
    }


def run_cycle() -> dict:
    state = load_state()

    if not state.get("active", True):
        return {"status": "pausado", "message": "BTC Bot pausado."}

    try:
        ex = get_exchange()
        price = ex.fetch_ticker(SYMBOL)["last"]
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_price"] = price

        estrategia = state.get("estrategia", "grid")
        if estrategia == "dca":
            resultado = _run_dca(state, ex, price)
        elif estrategia == "trailing_stop":
            resultado = _run_trailing_stop(state, ex, price)
        else:
            resultado = _run_grid_cycle(state, ex, price)

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
        logger.error(f"[BTC Bot] Erro: {e}")
        return {"status": "erro", "message": str(e)}


def tem_posicoes_abertas() -> bool:
    state = load_state()
    return (
        len(state.get("open_positions", {})) > 0
        or state.get("dca_qty", 0.0) > 0
        or state.get("ts_qty", 0.0) > 0
    )

def set_estrategia(nova: str) -> dict:
    """Muda estratégia. Só chamar após aprovação do Vasco e sem posições abertas."""
    if nova not in ("dca", "grid", "trailing_stop"):
        return {"status": "erro", "message": f"Estratégia inválida: {nova}"}
    if tem_posicoes_abertas():
        return {"status": "bloqueado", "message": "Posições abertas — fecha antes de mudar estratégia."}
    state = load_state()
    anterior = state.get("estrategia", "grid")
    state["estrategia"] = nova
    if nova == "grid":
        state["ref_price"] = None
        state["level_size"] = None
        state["capital_per_level"] = None
        state["open_positions"] = {}
    elif nova == "trailing_stop":
        state["ts_qty"] = 0.0
        state["ts_cash"] = TRAILING_CONFIG["capital"]
        state["ts_entry"] = None
        state["ts_peak"] = None
    else:  # dca
        state["dca_ref"] = None
        state["dca_cash"] = DCA_CONFIG["capital"]
        state["dca_qty"] = 0.0
    save_state(state)
    logger.info(f"[BTC Bot] Estratégia: {anterior} → {nova}")
    return {"status": "ok", "de": anterior, "para": nova}


def get_status() -> dict:
    state = load_state()
    ts_peak = state.get("ts_peak")
    return {
        "bot": "BTC/USDT",
        "estrategia": state.get("estrategia", "grid"),
        "active": state.get("active", True),
        "last_price": state.get("last_price"),
        "pnl_total": state.get("pnl_total", 0),
        "pnl_today": state.get("pnl_today", 0),
        "total_trades": len(state.get("trades", [])),
        "last_check": state.get("last_check", ""),
        "created_at": state.get("created_at", ""),
        "testnet": TESTNET,
        # Grid
        "ref_price": state.get("ref_price"),
        "level_size": state.get("level_size"),
        "open_positions": len(state.get("open_positions", {})),
        # DCA
        "dca_qty": state.get("dca_qty", 0),
        "dca_cash": state.get("dca_cash", 0),
        # Trailing Stop
        "ts_qty": state.get("ts_qty", 0),
        "ts_cash": state.get("ts_cash", 0),
        "ts_peak": ts_peak,
        "ts_stop": round(ts_peak * (1 - TRAILING_CONFIG["trail_pct"]), 2) if ts_peak else None,
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
    """Apaga o grid actual — será reiniciado com o preço corrente na próxima run."""
    state = load_state()
    state["ref_price"] = None
    state["level_size"] = None
    state["capital_per_level"] = None
    state["open_positions"] = {}
    state["created_at"] = ""
    save_state(state)
    logger.info("[Grid] Grid resetado — será reiniciado na próxima run.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
