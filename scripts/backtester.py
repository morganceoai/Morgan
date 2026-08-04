"""
BCVertex — Backtester de estratégias BTC/USDT
12 meses de dados reais Binance. Capital: 1.000 USDT. Fees: 0.2% round-trip.
Inclui long + short (simulação de futuros). SL/TP dinâmicos por estratégia.
"""

import os, json, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import ccxt
import math

# ── Config global ─────────────────────────────────────────────────────────────

CAPITAL_INICIAL = 1000.0
FEE = 0.001          # 0.1% por lado (maker/taker médio Binance)
SYMBOL = "BTC/USDT"
MESES = 12

# ── Fetch dados ───────────────────────────────────────────────────────────────

def fetch_ohlcv(timeframe: str, meses: int = 12) -> list:
    ex = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY", ""),
        "secret": os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })
    since = int((datetime.now(timezone.utc) - timedelta(days=30 * meses)).timestamp() * 1000)
    all_candles = []
    while True:
        candles = ex.fetch_ohlcv(SYMBOL, timeframe, since=since, limit=1000)
        if not candles:
            break
        all_candles.extend(candles)
        since = candles[-1][0] + 1
        if len(candles) < 1000:
            break
    # remover vela incompleta (actual)
    if all_candles:
        all_candles.pop()
    return all_candles

# ── Indicadores ───────────────────────────────────────────────────────────────

def _ema(values: list, n: int) -> list:
    ema = [None] * (n - 1)
    ema.append(sum(values[:n]) / n)
    k = 2 / (n + 1)
    for v in values[n:]:
        ema.append(ema[-1] * (1 - k) + v * k)
    return ema

def _sma(values: list, n: int) -> list:
    sma = [None] * (n - 1)
    for i in range(n - 1, len(values)):
        sma.append(sum(values[i - n + 1:i + 1]) / n)
    return sma

def _atr(highs, lows, closes, n: int) -> list:
    tr = [0.0]
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    atr = [sum(tr[:n]) / n]
    for i in range(1, len(tr)):
        atr.append((atr[-1] * (n - 1) + tr[i]) / n)
    return atr

def _rsi(closes: list, n: int = 14) -> list:
    rsi = [None] * n
    gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains[:n]) / n
    avg_loss = sum(losses[:n]) / n
    if avg_loss == 0:
        rsi.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100 - 100 / (1 + rs))
    for i in range(n, len(gains)):
        avg_gain = (avg_gain * (n - 1) + gains[i]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i]) / n
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - 100 / (1 + rs))
    return rsi

def _macd(closes: list, fast=12, slow=26, signal=9):
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = [None] * (slow - 1)
    for i in range(slow - 1, len(closes)):
        f = ema_fast[i]
        s = ema_slow[i]
        if f is None or s is None:
            macd_line.append(None)
        else:
            macd_line.append(f - s)
    valid = [v for v in macd_line if v is not None]
    sig_raw = _ema(valid, signal)
    signal_line = [None] * (len(macd_line) - len(sig_raw)) + sig_raw
    return macd_line, signal_line

def _supertrend(highs, lows, closes, n: int, mult: float):
    atr = _atr(highs, lows, closes, n)
    upper = [((highs[i] + lows[i]) / 2) + mult * atr[i] for i in range(len(closes))]
    lower = [((highs[i] + lows[i]) / 2) - mult * atr[i] for i in range(len(closes))]
    trend = [1] * len(closes)
    for i in range(1, len(closes)):
        if closes[i] > upper[i-1]:
            trend[i] = 1
        elif closes[i] < lower[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]
    return trend

def _bollinger(closes: list, n: int = 20, std_mult: float = 2.0):
    upper, lower, mid = [], [], []
    for i in range(len(closes)):
        if i < n - 1:
            upper.append(None); lower.append(None); mid.append(None)
        else:
            window = closes[i - n + 1:i + 1]
            m = sum(window) / n
            std = (sum((x - m) ** 2 for x in window) / n) ** 0.5
            mid.append(m)
            upper.append(m + std_mult * std)
            lower.append(m - std_mult * std)
    return upper, mid, lower

# ── Motor de backtest ─────────────────────────────────────────────────────────

def _run_backtest(signals: list, closes: list, timestamps: list,
                  sl_pct: float, tp_pct: float, label: str) -> dict:
    """
    signals: lista de 'buy', 'sell', 'hold' por índice
    sl_pct/tp_pct: stop loss / take profit (ex: 0.03, 0.09)
    Suporta long e short.
    """
    capital = CAPITAL_INICIAL
    trades = []
    position = None

    for i in range(len(signals)):
        sig = signals[i]
        price = closes[i]

        if position:
            entry = position["entry"]
            side = position["side"]
            pct = (price - entry) / entry if side == "long" else (entry - price) / entry

            exit_reason = None
            if pct <= -sl_pct:
                exit_reason = "SL"
            elif pct >= tp_pct:
                exit_reason = "TP"
            elif side == "long" and sig == "sell":
                exit_reason = "sinal"
            elif side == "short" and sig == "buy":
                exit_reason = "sinal"

            if exit_reason:
                size = position["size"]
                gross_pnl = pct * (size * entry)
                fee_cost = size * entry * FEE * 2
                net_pnl = gross_pnl - fee_cost
                capital += net_pnl
                trades.append({
                    "entry": entry, "exit": price,
                    "side": side, "pct": round(pct * 100, 2),
                    "pnl": round(net_pnl, 4),
                    "reason": exit_reason,
                    "ts_entry": position["ts"],
                    "ts_exit": timestamps[i],
                })
                position = None

        if not position:
            if sig == "buy":
                size = round((capital * 0.95) / price, 6)
                fee_cost = size * price * FEE
                capital -= fee_cost
                position = {"side": "long", "entry": price, "size": size, "ts": timestamps[i]}
            elif sig == "sell":
                size = round((capital * 0.95) / price, 6)
                fee_cost = size * price * FEE
                capital -= fee_cost
                position = {"side": "short", "entry": price, "size": size, "ts": timestamps[i]}

    # fechar posição aberta no fim
    if position:
        price = closes[-1]
        entry = position["entry"]
        side = position["side"]
        pct = (price - entry) / entry if side == "long" else (entry - price) / entry
        size = position["size"]
        net_pnl = pct * (size * entry) - size * entry * FEE * 2
        capital += net_pnl
        trades.append({
            "entry": entry, "exit": price, "side": side,
            "pct": round(pct * 100, 2), "pnl": round(net_pnl, 4),
            "reason": "fim_backtest", "ts_entry": position["ts"],
            "ts_exit": timestamps[-1],
        })

    if not trades:
        return {"label": label, "trades": 0, "win_rate": 0,
                "profit_factor": 0, "max_dd": 0,
                "retorno_pct": 0, "capital_final": CAPITAL_INICIAL,
                "trades_por_mes": 0}

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(trades) * 100
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # drawdown máximo
    peak = CAPITAL_INICIAL
    running = CAPITAL_INICIAL
    max_dd = 0.0
    for t in trades:
        running += t["pnl"]
        if running > peak:
            peak = running
        dd = (peak - running) / peak * 100
        if dd > max_dd:
            max_dd = dd

    retorno_pct = (capital - CAPITAL_INICIAL) / CAPITAL_INICIAL * 100
    dias_total = (timestamps[-1] - timestamps[0]) / 1000 / 86400
    trades_por_mes = len(trades) / (dias_total / 30) if dias_total > 0 else 0

    return {
        "label": label,
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 99.9,
        "max_dd": round(max_dd, 1),
        "retorno_pct": round(retorno_pct, 1),
        "capital_final": round(capital, 2),
        "trades_por_mes": round(trades_por_mes, 1),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "avg_win": round(gross_profit / len(wins), 2) if wins else 0,
        "avg_loss": round(gross_loss / len(losses), 2) if losses else 0,
    }

# ── Estratégias ───────────────────────────────────────────────────────────────

def strat_supertrend(ohlcv, n=10, mult=3.0, label=None):
    highs  = [c[2] for c in ohlcv]
    lows   = [c[3] for c in ohlcv]
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    trend  = _supertrend(highs, lows, closes, n, mult)
    signals = ["hold"] * len(closes)
    for i in range(1, len(closes)):
        if trend[i] == 1 and trend[i-1] == -1:
            signals[i] = "buy"
        elif trend[i] == -1 and trend[i-1] == 1:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.03, tp_pct=0.09,
                         label=label or f"Supertrend {n}×{mult}")

def strat_ema_cross(ohlcv, fast=9, slow=21, label=None):
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    ema_f  = _ema(closes, fast)
    ema_s  = _ema(closes, slow)
    signals = ["hold"] * len(closes)
    for i in range(slow, len(closes)):
        if ema_f[i] is None or ema_s[i] is None:
            continue
        if ema_f[i] > ema_s[i] and ema_f[i-1] <= ema_s[i-1]:
            signals[i] = "buy"
        elif ema_f[i] < ema_s[i] and ema_f[i-1] >= ema_s[i-1]:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.025, tp_pct=0.075,
                         label=label or f"EMA {fast}/{slow}")

def strat_macd(ohlcv, label="MACD 12/26/9"):
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    macd, sig = _macd(closes)
    signals = ["hold"] * len(closes)
    for i in range(1, len(closes)):
        m, s = macd[i], sig[i]
        mp, sp = macd[i-1], sig[i-1]
        if m is None or s is None or mp is None or sp is None:
            continue
        if m > s and mp <= sp:
            signals[i] = "buy"
        elif m < s and mp >= sp:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.03, tp_pct=0.09, label=label)

def strat_rsi(ohlcv, n=14, oversold=30, overbought=70, label=None):
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    rsi    = _rsi(closes, n)
    signals = ["hold"] * len(closes)
    in_long = False
    for i in range(1, len(closes)):
        r, rp = rsi[i], rsi[i-1]
        if r is None or rp is None:
            continue
        if not in_long and rp < oversold and r >= oversold:
            signals[i] = "buy"
            in_long = True
        elif in_long and rp < overbought and r >= overbought:
            signals[i] = "sell"
            in_long = False
        elif in_long and rp > oversold and r <= oversold:  # re-oversold
            signals[i] = "sell"
            in_long = False
    return _run_backtest(signals, closes, ts, sl_pct=0.025, tp_pct=0.08,
                         label=label or f"RSI {n} ({oversold}/{overbought})")

def strat_rsi_aggressive(ohlcv, label="RSI 7 (25/75)"):
    return strat_rsi(ohlcv, n=7, oversold=25, overbought=75, label=label)

def strat_bollinger(ohlcv, n=20, std=2.0, label=None):
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    upper, mid, lower = _bollinger(closes, n, std)
    signals = ["hold"] * len(closes)
    in_long = False
    for i in range(1, len(closes)):
        if lower[i] is None or lower[i-1] is None or upper[i] is None or upper[i-1] is None or mid[i] is None:
            continue
        if not in_long and closes[i-1] < lower[i-1] and closes[i] >= lower[i]:
            signals[i] = "buy"
            in_long = True
        elif in_long and closes[i-1] > upper[i-1] and closes[i] <= upper[i]:
            signals[i] = "sell"
            in_long = False
        elif in_long and closes[i] < mid[i] * 0.99:
            signals[i] = "sell"
            in_long = False
    return _run_backtest(signals, closes, ts, sl_pct=0.025, tp_pct=0.06,
                         label=label or f"Bollinger {n}/{std}")

def strat_breakout(ohlcv, n=20, label=None):
    highs  = [c[2] for c in ohlcv]
    lows   = [c[3] for c in ohlcv]
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    signals = ["hold"] * len(closes)
    for i in range(n, len(closes)):
        window_h = max(highs[i-n:i])
        window_l = min(lows[i-n:i])
        if closes[i] > window_h and closes[i-1] <= window_h:
            signals[i] = "buy"
        elif closes[i] < window_l and closes[i-1] >= window_l:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.03, tp_pct=0.09,
                         label=label or f"Breakout {n}p")

def strat_supertrend_rsi(ohlcv, n=10, mult=3.0, rsi_n=10, label="Supertrend+RSI"):
    """Entra apenas quando Supertrend bullish E RSI confirma momentum."""
    highs  = [c[2] for c in ohlcv]
    lows   = [c[3] for c in ohlcv]
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    trend  = _supertrend(highs, lows, closes, n, mult)
    rsi    = _rsi(closes, rsi_n)
    signals = ["hold"] * len(closes)
    for i in range(1, len(closes)):
        if rsi[i] is None:
            continue
        if trend[i] == 1 and trend[i-1] == -1 and rsi[i] > 50:
            signals[i] = "buy"
        elif trend[i] == -1 and trend[i-1] == 1 and rsi[i] < 50:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.03, tp_pct=0.09, label=label)

def strat_ema_rsi(ohlcv, fast=9, slow=21, rsi_n=14, label="EMA 9/21 + RSI"):
    """EMA cross com filtro RSI — evita entradas em exaustão."""
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    ema_f  = _ema(closes, fast)
    ema_s  = _ema(closes, slow)
    rsi    = _rsi(closes, rsi_n)
    signals = ["hold"] * len(closes)
    for i in range(slow, len(closes)):
        if ema_f[i] is None or ema_s[i] is None or rsi[i] is None:
            continue
        if ema_f[i] > ema_s[i] and ema_f[i-1] <= ema_s[i-1] and rsi[i] < 65:
            signals[i] = "buy"
        elif ema_f[i] < ema_s[i] and ema_f[i-1] >= ema_s[i-1] and rsi[i] > 35:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.025, tp_pct=0.075, label=label)

def strat_macd_rsi(ohlcv, label="MACD + RSI"):
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    macd, sig = _macd(closes)
    rsi    = _rsi(closes, 14)
    signals = ["hold"] * len(closes)
    for i in range(1, len(closes)):
        m, s = macd[i], sig[i]
        mp, sp = macd[i-1], sig[i-1]
        r = rsi[i]
        if m is None or s is None or mp is None or sp is None or r is None:
            continue
        if m > s and mp <= sp and r < 65:
            signals[i] = "buy"
        elif m < s and mp >= sp and r > 35:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.03, tp_pct=0.09, label=label)

def strat_triple_ema(ohlcv, label="Triple EMA 8/21/55"):
    """Entra quando EMA rápida > média > lenta (tendência alinhada)."""
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    ema8   = _ema(closes, 8)
    ema21  = _ema(closes, 21)
    ema55  = _ema(closes, 55)
    signals = ["hold"] * len(closes)
    for i in range(1, len(closes)):
        if ema8[i] is None or ema21[i] is None or ema55[i] is None:
            continue
        if ema8[i-1] is None or ema21[i-1] is None or ema55[i-1] is None:
            continue
        bullish = ema8[i] > ema21[i] > ema55[i]
        bullish_prev = ema8[i-1] > ema21[i-1] > ema55[i-1]
        bearish = ema8[i] < ema21[i] < ema55[i]
        bearish_prev = ema8[i-1] < ema21[i-1] < ema55[i-1]
        if bullish and not bullish_prev:
            signals[i] = "buy"
        elif bearish and not bearish_prev:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.03, tp_pct=0.09, label=label)

def strat_atr_breakout(ohlcv, atr_n=14, mult=1.5, label="ATR Breakout"):
    """Breakout quando preço move > 1.5×ATR numa vela."""
    highs  = [c[2] for c in ohlcv]
    lows   = [c[3] for c in ohlcv]
    closes = [c[4] for c in ohlcv]
    opens  = [c[1] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    atr    = _atr(highs, lows, closes, atr_n)
    signals = ["hold"] * len(closes)
    for i in range(atr_n + 1, len(closes)):
        move = closes[i] - opens[i]
        if move > mult * atr[i-1]:
            signals[i] = "buy"
        elif move < -mult * atr[i-1]:
            signals[i] = "sell"
    return _run_backtest(signals, closes, ts, sl_pct=0.02, tp_pct=0.06, label=label)

def strat_mean_reversion_bb_rsi(ohlcv, label="BB+RSI Mean Rev."):
    """Mean reversion: entra quando BB lower E RSI<35. Sai em BB mid."""
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]
    upper, mid, lower = _bollinger(closes, 20, 2.0)
    rsi = _rsi(closes, 14)
    signals = ["hold"] * len(closes)
    in_long = False
    for i in range(1, len(closes)):
        if lower[i] is None or mid[i] is None or rsi[i] is None:
            continue
        if not in_long and closes[i] < lower[i] and rsi[i] < 35:
            signals[i] = "buy"
            in_long = True
        elif in_long and closes[i] > mid[i]:
            signals[i] = "sell"
            in_long = False
    return _run_backtest(signals, closes, ts, sl_pct=0.02, tp_pct=0.05, label=label)

def strat_grid_sim(ohlcv, n_levels=10, range_pct=0.05, label="Grid Bot (sim)"):
    """
    Simulação simplificada de grid bot.
    Divide o range em N níveis, compra em cada queda de 1 nível, vende na subida.
    """
    closes = [c[4] for c in ohlcv]
    ts     = [c[0] for c in ohlcv]

    # Definir grid a partir do preço inicial
    p0 = closes[0]
    step = p0 * range_pct / n_levels
    capital = CAPITAL_INICIAL
    orders_per_level = capital / n_levels / p0
    trades = []
    open_orders = {}  # nivel: {entry, size}

    for i in range(1, len(closes)):
        price = closes[i]
        level = round((price - p0) / step)

        # verificar se alguma ordem de compra foi preenchida (queda)
        for lvl in list(open_orders.keys()):
            order = open_orders[lvl]
            if price >= order["entry"] * (1 + range_pct / n_levels):
                # vender
                pnl = (price - order["entry"]) * order["size"] - order["entry"] * order["size"] * FEE * 2
                capital += pnl
                trades.append({"pnl": pnl, "entry": order["entry"], "exit": price})
                del open_orders[lvl]

        # nova ordem de compra se cair para novo nível
        if level not in open_orders and level < 0:
            entry = p0 + level * step
            size = orders_per_level * 0.9
            fee_cost = entry * size * FEE
            if capital > entry * size + fee_cost:
                capital -= fee_cost
                open_orders[level] = {"entry": entry, "size": size}

    if not trades:
        return {"label": label, "trades": 0, "win_rate": 0,
                "profit_factor": 0, "max_dd": 0, "retorno_pct": 0,
                "capital_final": CAPITAL_INICIAL, "trades_por_mes": 0,
                "gross_profit": 0, "gross_loss": 0, "avg_win": 0, "avg_loss": 0}

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(trades) * 100
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.9
    retorno = (capital - CAPITAL_INICIAL) / CAPITAL_INICIAL * 100
    dias = (ts[-1] - ts[0]) / 1000 / 86400
    return {
        "label": label,
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(pf, 2),
        "max_dd": 0,  # grid não tem drawdown linear
        "retorno_pct": round(retorno, 1),
        "capital_final": round(capital, 2),
        "trades_por_mes": round(len(trades) / (dias / 30), 1),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "avg_win": round(gross_profit / len(wins), 2) if wins else 0,
        "avg_loss": round(gross_loss / len(losses), 2) if losses else 0,
    }

# ── Output ────────────────────────────────────────────────────────────────────

def _fmt_row(r: dict, i: int) -> str:
    pf = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 99 else "∞"
    retorno = f"{r['retorno_pct']:+.1f}%"
    return (
        f"  {i:2}. {r['label']:<28} | {r['trades']:>6} trades | "
        f"WR {r['win_rate']:>5.1f}% | PF {pf:>5} | "
        f"DD -{r['max_dd']:>4.1f}% | {retorno:>8} | "
        f"€{r['capital_final']:>8.2f} | {r['trades_por_mes']:>5.1f}/mês"
    )

def main():
    print("\n" + "="*120)
    print(f"  BCVertex — BACKTESTER BTC/USDT ({MESES} meses) | Capital: €{CAPITAL_INICIAL:.0f} | Fees: {FEE*100:.1f}% cada lado")
    print("="*120)

    # Fetch dados por timeframe
    print("\n  A carregar dados da Binance...")
    data = {}
    for tf in ["4h", "1h", "15m"]:
        print(f"    {tf}...", end=" ", flush=True)
        data[tf] = fetch_ohlcv(tf, MESES)
        print(f"{len(data[tf])} velas")

    results = []

    print("\n  A correr estratégias...\n")

    # ── Trend following ───────────────────────────────────────────────────────
    print("  [Trend Following]")
    for tf, desc in [("4h", "4h"), ("1h", "1h"), ("15m", "15m")]:
        r = strat_supertrend(data[tf], n=10, mult=3.0, label=f"Supertrend 10×3 {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    for tf, desc in [("1h", "1h"), ("15m", "15m")]:
        r = strat_ema_cross(data[tf], fast=9, slow=21, label=f"EMA 9/21 {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_ema_cross(data[tf], fast=21, slow=55, label=f"EMA 21/55 {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    for tf, desc in [("1h", "1h"), ("15m", "15m")]:
        r = strat_triple_ema(data[tf]); r["label"] += f" {desc}"
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    # ── Momentum ──────────────────────────────────────────────────────────────
    print("\n  [Momentum / Breakout]")
    for tf, desc in [("1h", "1h"), ("15m", "15m")]:
        r = strat_macd(data[tf], label=f"MACD 12/26/9 {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_breakout(data[tf], n=20, label=f"Breakout 20p {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_atr_breakout(data[tf], label=f"ATR Breakout {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    # ── Mean Reversion ────────────────────────────────────────────────────────
    print("\n  [Mean Reversion]")
    for tf, desc in [("1h", "1h"), ("15m", "15m")]:
        r = strat_rsi(data[tf], label=f"RSI 14 {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_rsi_aggressive(data[tf]); r["label"] += f" {desc}"
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_bollinger(data[tf], label=f"Bollinger 20/2 {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_mean_reversion_bb_rsi(data[tf]); r["label"] += f" {desc}"
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    # ── Combinadas ────────────────────────────────────────────────────────────
    print("\n  [Estratégias Combinadas]")
    for tf, desc in [("1h", "1h"), ("15m", "15m")]:
        r = strat_supertrend_rsi(data[tf], label=f"Supertrend+RSI {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_ema_rsi(data[tf], label=f"EMA 9/21+RSI {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_macd_rsi(data[tf], label=f"MACD+RSI {desc}")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    # ── Grid ──────────────────────────────────────────────────────────────────
    print("\n  [Grid Bot]")
    for tf, desc in [("1h", "1h")]:
        r = strat_grid_sim(data[tf], n_levels=10, range_pct=0.08, label="Grid Bot 10n/8%")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")
        r = strat_grid_sim(data[tf], n_levels=20, range_pct=0.10, label="Grid Bot 20n/10%")
        results.append(r); print(f"    {r['label']}: {r['trades']} trades, {r['retorno_pct']:+.1f}%")

    # ── Ranking ───────────────────────────────────────────────────────────────
    ranked = sorted(results, key=lambda r: r["retorno_pct"], reverse=True)

    print("\n" + "="*120)
    print(f"  RANKING COMPLETO — ordenado por retorno | Capital inicial: €{CAPITAL_INICIAL:.0f}")
    print("="*120)
    header = (
        f"  {'#':>3}  {'Estratégia':<28} | {'Trades':>8} | "
        f"{'Win%':>7} | {'PF':>6} | {'MaxDD':>7} | {'Retorno':>8} | "
        f"{'Capital Final':>13} | {'Freq/mês':>9}"
    )
    print(header)
    print("  " + "-"*116)
    for i, r in enumerate(ranked, 1):
        print(_fmt_row(r, i))

    # ── Top 5 análise ─────────────────────────────────────────────────────────
    print("\n" + "="*120)
    print("  TOP 5 — ANÁLISE DETALHADA")
    print("="*120)
    for r in ranked[:5]:
        pf = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 99 else "∞"
        print(f"""
  {r['label']}
  ├─ Retorno: {r['retorno_pct']:+.1f}%  |  Capital final: €{r['capital_final']:.2f}
  ├─ Trades: {r['trades']} ({r['trades_por_mes']:.1f}/mês)  |  Win rate: {r['win_rate']:.1f}%
  ├─ Profit Factor: {pf}  |  Max Drawdown: -{r['max_dd']:.1f}%
  ├─ Lucro médio/trade ganho: €{r['avg_win']:.2f}  |  Perda média/trade perdido: €{r['avg_loss']:.2f}
  └─ Gross profit: €{r['gross_profit']:.2f}  |  Gross loss: €{r['gross_loss']:.2f}""")

    # ── Simulação compounding ─────────────────────────────────────────────────
    print("\n" + "="*120)
    print("  SIMULAÇÃO DE COMPOUNDING — Top 3 estratégias (12 meses)")
    print("="*120)
    print(f"  {'Estratégia':<30} | {'Mês 3':>10} | {'Mês 6':>10} | {'Mês 12':>10}")
    print("  " + "-"*65)
    for r in ranked[:3]:
        if r['trades_por_mes'] > 0 and r['win_rate'] > 0:
            monthly = r['retorno_pct'] / 12 / 100
            c3  = CAPITAL_INICIAL * (1 + monthly) ** 3
            c6  = CAPITAL_INICIAL * (1 + monthly) ** 6
            c12 = CAPITAL_INICIAL * (1 + monthly) ** 12
            print(f"  {r['label']:<30} | €{c3:>9.2f} | €{c6:>9.2f} | €{c12:>9.2f}")

    # ── Guardar JSON ──────────────────────────────────────────────────────────
    output_file = Path(__file__).parent / "backtest_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "data": datetime.now().isoformat(),
            "capital_inicial": CAPITAL_INICIAL,
            "meses": MESES,
            "symbol": SYMBOL,
            "resultados": ranked,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Resultados guardados em: {output_file}")
    print("="*120 + "\n")

if __name__ == "__main__":
    main()
