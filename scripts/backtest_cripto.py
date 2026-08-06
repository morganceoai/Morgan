"""
Backtesting de estratégias cripto — BTC, ETH, SOL
Utilizado pelo CFO para análise histórica e detecção de configurações óptimas.

Estratégias:
  1. DCA — compra fixa periódica
  2. Grid Bot — lateralização com degraus automáticos
  3. Trailing Stop — bull market com protecção de lucros

Detecção de fase: SMA200 + RSI14
"""

import ccxt
import pandas as pd
import numpy as np
import talib
import json
import pickle
import time
from pathlib import Path

PAIRS = {
    'BTC/USDT': ('BTC', '2015-01-01T00:00:00Z'),
    'ETH/USDT': ('ETH', '2017-01-01T00:00:00Z'),
    'SOL/USDT': ('SOL', '2020-04-01T00:00:00Z'),
}

CACHE_PATH = Path('/tmp/crypto_ohlcv.pkl')


def fetch_ohlcv(use_cache=True):
    if use_cache and CACHE_PATH.exists():
        with open(CACHE_PATH, 'rb') as f:
            return pickle.load(f)

    exchange = ccxt.binance({'enableRateLimit': True})
    data = {}

    for symbol, (label, start) in PAIRS.items():
        print(f"A buscar {symbol}...")
        since = exchange.parse8601(start)
        ohlcv = []
        while True:
            batch = exchange.fetch_ohlcv(symbol, '1d', since=since, limit=1000)
            if not batch:
                break
            ohlcv.extend(batch)
            since = batch[-1][0] + 86400000
            if batch[-1][0] >= exchange.milliseconds() - 86400000:
                break
            time.sleep(0.2)

        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['ts'], unit='ms')
        df = df.set_index('date').drop('ts', axis=1)
        data[label] = df
        print(f"  {label}: {len(df)} dias")

    with open(CACHE_PATH, 'wb') as f:
        pickle.dump(data, f)

    return data


def backtest_dca(close, daily_buy=1.0):
    n = len(close)
    units = 0.0
    invested = 0.0
    portfolio_values = []

    for i in range(n):
        units += daily_buy / close[i]
        invested += daily_buy
        portfolio_values.append(units * close[i])

    final_value = units * close[-1]
    total_ret = (final_value / invested - 1) * 100

    pv = np.array(portfolio_values)
    running_max = np.maximum.accumulate(pv)
    max_dd = ((pv - running_max) / running_max * 100).min()

    return {
        'total_return': round(total_ret, 1),
        'buy_hold_return': round((close[-1] / close[0] - 1) * 100, 1),
        'max_drawdown': round(max_dd, 1),
        'final_per_dollar': round(final_value / invested, 2),
    }


def backtest_trailing_stop(close, trail_pct=0.15, entry_lookback=20):
    cash = 100.0
    units = 0.0
    in_trade = False
    peak = 0.0
    entry_price = 0.0
    trades = []

    for i in range(entry_lookback, len(close)):
        price = close[i]
        if not in_trade:
            if price == max(close[max(0, i - entry_lookback):i + 1]):
                units = cash / price
                cash = 0.0
                in_trade = True
                peak = price
                entry_price = price
        else:
            if price > peak:
                peak = price
            if price < peak * (1 - trail_pct):
                cash = units * price
                trades.append({'entry': entry_price, 'exit': price, 'ret': (price / entry_price - 1) * 100})
                units = 0.0
                in_trade = False

    final_value = cash + units * close[-1]
    total_ret = (final_value / 100.0 - 1) * 100

    vals = []
    c2, u2, in2, pk2 = 100.0, 0.0, False, 0.0
    for i in range(entry_lookback, len(close)):
        p = close[i]
        if not in2:
            if p == max(close[max(0, i - entry_lookback):i + 1]):
                u2 = c2 / p; c2 = 0.0; in2 = True; pk2 = p
        else:
            if p > pk2:
                pk2 = p
            if p < pk2 * (1 - trail_pct):
                c2 = u2 * p; u2 = 0.0; in2 = False
        vals.append(c2 + u2 * p)

    vals = np.array(vals)
    rm = np.maximum.accumulate(vals)
    max_dd = ((vals - rm) / rm * 100).min() if len(vals) > 0 else 0

    return {
        'total_return': round(total_ret, 1),
        'max_drawdown': round(max_dd, 1),
        'n_trades': len(trades),
        'trail_pct': int(trail_pct * 100),
        'entry_lookback': entry_lookback,
    }


def backtest_grid_bot(close, high_arr, low_arr, grid_range_pct=0.15, n_grids=10, capital=100.0):
    """
    Simula o grid bot em janelas de 90 dias ao longo do histórico.
    Retorna retorno médio dentro e fora do range, e % do tempo em range.
    """
    window = 90
    results_windows = []

    for start in range(0, len(close) - window, window):
        end = start + window
        c = close[start:end]
        h = high_arr[start:end]
        l = low_arr[start:end]

        center = c[0]
        grid_low = center * (1 - grid_range_pct / 2)
        grid_high = center * (1 + grid_range_pct / 2)
        step = (grid_high - grid_low) / n_grids

        profit = 0.0
        trades = 0

        for i in range(1, len(c)):
            price_range = abs(h[i] - l[i])
            crossings = max(0, int(price_range / step))
            if crossings > 0 and grid_low <= c[i] <= grid_high:
                qty_per_grid = (capital / 2) / (n_grids * center)
                profit_per_trade = step * qty_per_grid
                commission = 0.001 * 2 * qty_per_grid * c[i]
                profit += (profit_per_trade - commission) * min(crossings, 3)
                trades += min(crossings, 3)

        period_ret = profit / capital * 100
        results_windows.append({
            'ret': period_ret,
            'trades': trades,
            'in_range': grid_low <= c[-1] <= grid_high,
        })

    in_range = [r for r in results_windows if r['in_range']]
    avg_ret_in = np.mean([r['ret'] for r in in_range]) if in_range else 0
    avg_ret_all = np.mean([r['ret'] for r in results_windows])
    pct_in_range = len(in_range) / len(results_windows) * 100

    return {
        'avg_return_90d_in_range': round(avg_ret_in, 2),
        'avg_return_90d_all': round(avg_ret_all, 2),
        'pct_time_in_range': round(pct_in_range, 1),
        'avg_trades_per_90d': round(np.mean([r['trades'] for r in results_windows]), 0),
        'annualized_in_range': round(avg_ret_in * 4, 1),
        'range_pct': int(grid_range_pct * 100),
        'n_grids': n_grids,
    }


def detect_phases(close, dates):
    """Classifica cada dia em Bull / Bear / Flat via SMA200 + RSI14."""
    sma200 = talib.SMA(close, timeperiod=200)
    rsi14 = talib.RSI(close, timeperiod=14)
    phases = []
    for i in range(len(close)):
        if np.isnan(sma200[i]) or np.isnan(rsi14[i]):
            phases.append('unknown')
        elif close[i] > sma200[i] and rsi14[i] > 55:
            phases.append('bull')
        elif close[i] < sma200[i] and rsi14[i] < 45:
            phases.append('bear')
        else:
            phases.append('flat')
    return phases


def run_full_backtest(use_cache=True):
    data = fetch_ohlcv(use_cache=use_cache)
    results = {}

    for label, df in data.items():
        print(f"\n{'='*60}")
        print(f"  {label}  —  {df.index[0].date()} → {df.index[-1].date()}  ({len(df)} dias)")
        print(f"{'='*60}")

        close = df['close'].values.astype(float)
        high  = df['high'].values.astype(float)
        low   = df['low'].values.astype(float)
        dates = df.index

        res = {
            'label': label,
            'days': len(close),
            'start': str(dates[0].date()),
            'end': str(dates[-1].date()),
        }

        # DCA
        res['dca'] = backtest_dca(close)
        print(f"\n[DCA] +{res['dca']['total_return']}%  |  B&H: +{res['dca']['buy_hold_return']}%  |  DD: {res['dca']['max_drawdown']}%")

        # Trailing Stop — grid search
        best_ts = None
        for trail in [0.10, 0.15, 0.20, 0.25]:
            for lookback in [20, 30, 50]:
                ts = backtest_trailing_stop(close, trail, lookback)
                if best_ts is None or ts['total_return'] > best_ts['total_return']:
                    best_ts = ts
        res['trailing_stop'] = best_ts
        print(f"[TRAILING] +{best_ts['total_return']}%  trail={best_ts['trail_pct']}%  look={best_ts['entry_lookback']}d  DD: {best_ts['max_drawdown']}%")

        # Grid Bot — grid search
        best_grid = None
        for rng in [0.10, 0.15, 0.20, 0.25]:
            for ng in [8, 10, 15, 20]:
                gr = backtest_grid_bot(close, high, low, rng, ng)
                if best_grid is None or gr['avg_return_90d_in_range'] > best_grid['avg_return_90d_in_range']:
                    best_grid = gr
        res['grid_bot'] = best_grid
        print(f"[GRID]     +{best_grid['annualized_in_range']}%/ano (in-range)  range={best_grid['range_pct']}%  grids={best_grid['n_grids']}  tempo em range: {best_grid['pct_time_in_range']}%")

        # Fases de mercado
        phases = detect_phases(close, dates)
        phase_returns = {'bull': [], 'bear': [], 'flat': []}
        for i in range(len(close) - 1):
            p = phases[i]
            if p in phase_returns:
                phase_returns[p].append((close[i + 1] / close[i] - 1) * 100)

        phase_stats = {}
        for phase, rets in phase_returns.items():
            if rets:
                m = np.mean(rets) / 100
                ann = round(((1 + m) ** 252 - 1) * 100, 1)
            else:
                ann = 0
            phase_stats[phase] = {'days': len(rets), 'annualized_ret': ann}
        res['phases'] = phase_stats
        print(f"[FASES]    Bull: {phase_stats['bull']['days']}d +{phase_stats['bull']['annualized_ret']}%  "
              f"Bear: {phase_stats['bear']['days']}d {phase_stats['bear']['annualized_ret']}%  "
              f"Flat: {phase_stats['flat']['days']}d {phase_stats['flat']['annualized_ret']}%")

        # Max drawdown histórico
        running_max = np.maximum.accumulate(close)
        dd_series = (close - running_max) / running_max * 100
        max_dd = dd_series.min()
        idx_bottom = dd_series.argmin()
        idx_peak = np.argmax(close[:idx_bottom])
        res['max_drawdown_ever'] = round(max_dd, 1)
        res['max_dd_peak_date'] = str(dates[idx_peak].date())
        res['max_dd_bottom_date'] = str(dates[idx_bottom].date())
        print(f"[MAX DD]   {max_dd:.1f}%  ({dates[idx_peak].date()} → {dates[idx_bottom].date()})")

        results[label] = res

    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backtest cripto BTC/ETH/SOL')
    parser.add_argument('--no-cache', action='store_true', help='Forçar nova descarga dos dados')
    parser.add_argument('--output', default='/tmp/backtest_results.json', help='Ficheiro de saída JSON')
    args = parser.parse_args()

    results = run_full_backtest(use_cache=not args.no_cache)

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados guardados em {args.output}")
