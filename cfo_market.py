"""
CFO Market — Dados de mercado e detecção de regime para o CFO.
O CFO usa isto para contextualizar decisões com o estado real do mercado.
Regime: LATERAL | TRENDING | VOLATILE
"""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_CACHE_FILE = Path(__file__).parent / "memory" / "cfo_market_cache.json"
_CACHE_TTL_MINUTES = 10  # não chamar exchange mais que 1x por 10min por check


def _load_cache() -> dict:
    try:
        data = json.loads(_CACHE_FILE.read_text())
        ts = datetime.fromisoformat(data.get("ts", "2000-01-01"))
        age_min = (datetime.now() - ts).total_seconds() / 60
        if age_min < _CACHE_TTL_MINUTES:
            return data
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    _CACHE_FILE.parent.mkdir(exist_ok=True)
    _CACHE_FILE.write_text(json.dumps({**data, "ts": datetime.now().isoformat()}, ensure_ascii=False, indent=2))


def _get_exchange():
    import ccxt
    ex = ccxt.binance({
        "apiKey":  os.getenv("BINANCE_API_KEY", ""),
        "secret":  os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })
    if os.getenv("BINANCE_TESTNET", "false").lower() == "true":
        ex.set_sandbox_mode(True)
    return ex


def _ema(closes: list, period: int) -> list:
    result = [None] * len(closes)
    k = 2 / (period + 1)
    for i in range(len(closes)):
        if i < period - 1:
            continue
        if i == period - 1:
            result[i] = sum(closes[:period]) / period
        else:
            if result[i-1] is not None:
                result[i] = closes[i] * k + result[i-1] * (1 - k)
    return result


def _atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
    trs = []
    for i in range(len(closes)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            trs.append(tr)
    atr = [None] * len(closes)
    for i in range(len(trs)):
        if i < period:
            continue
        if i == period:
            atr[i] = sum(trs[:period+1]) / (period + 1)
        else:
            if atr[i-1] is not None:
                atr[i] = (atr[i-1] * (period - 1) + trs[i]) / period
    return atr


def detectar_regime(symbol: str = "BTC/USDT", timeframe: str = "1h", lookback: int = 48) -> dict:
    """
    Detecta o regime de mercado actual.

    Retorna:
        regime: "LATERAL" | "TRENDING" | "VOLATILE"
        confianca: 0-100
        metricas: detalhes para o LLM raciocinar
        preco_actual: float
    """
    cache = _load_cache()
    if cache.get("regime"):
        return cache

    try:
        ex = _get_exchange()
        ohlcv = ex.fetch_ohlcv(symbol, timeframe, limit=lookback + 10)

        if len(ohlcv) < lookback:
            return {"regime": "DESCONHECIDO", "confianca": 0, "erro": "dados insuficientes"}

        timestamps = [c[0] for c in ohlcv]
        opens  = [c[1] for c in ohlcv]
        highs  = [c[2] for c in ohlcv]
        lows   = [c[3] for c in ohlcv]
        closes = [c[4] for c in ohlcv]

        preco = closes[-1]

        # ATR relativo (volatilidade)
        atrs = _atr(highs, lows, closes, period=14)
        atr_actual = atrs[-1]
        atr_rel = atr_actual / preco if preco else 0  # ATR como % do preço

        # EMA 20 e 50 para tendência
        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)
        ema20_actual = ema20[-1]
        ema50_actual = ema50[-1]

        # Range das últimas 24h vs últimas 48h
        n_recent = min(24, len(closes))
        n_full   = min(48, len(closes))
        range_recent = max(closes[-n_recent:]) - min(closes[-n_recent:])
        range_full   = max(closes[-n_full:])   - min(closes[-n_full:])
        range_pct_24h = range_recent / preco

        # Inclinação EMA50 (rate of change)
        ema50_prev = ema50[-5] if ema50[-5] else ema50[-1]
        ema50_slope = (ema50_actual - ema50_prev) / ema50_prev if ema50_prev else 0

        # Classificação de regime
        regime = "LATERAL"
        confianca = 50
        razao = []

        # VOLATILE: ATR relativo alto
        if atr_rel > 0.025:  # > 2.5% de ATR por hora → altamente volátil
            regime = "VOLATILE"
            confianca = min(90, int(atr_rel * 2000))
            razao.append(f"ATR/h {atr_rel*100:.2f}% > 2.5%")

        # TRENDING: EMA alinhada e inclinação significativa
        elif abs(ema50_slope) > 0.003:  # EMA50 a mover > 0.3% em 5h
            regime = "TRENDING"
            confianca = min(85, int(abs(ema50_slope) * 15000))
            direcao = "ALTA" if ema50_slope > 0 else "BAIXA"
            razao.append(f"EMA50 slope {ema50_slope*100:.3f}%/5h → tendência {direcao}")
            if ema20_actual > ema50_actual and ema50_slope > 0:
                confianca = min(90, confianca + 10)
                razao.append("EMA20 > EMA50 confirma alta")
            elif ema20_actual < ema50_actual and ema50_slope < 0:
                confianca = min(90, confianca + 10)
                razao.append("EMA20 < EMA50 confirma baixa")

        # LATERAL: range estreito, ATR baixo
        else:
            range_score = 1 - min(1, range_pct_24h / 0.05)  # 0% range = 100% lateral
            confianca = int(40 + range_score * 50)
            razao.append(f"Range 24h {range_pct_24h*100:.1f}%, ATR {atr_rel*100:.2f}%")

        # Estratégia recomendada por regime
        estrategia_recomendada = {
            "LATERAL":  "grid",
            "TRENDING": "trailing_stop",
            "VOLATILE": "reduzir_exposicao",
        }.get(regime, "nenhuma")

        resultado = {
            "regime": regime,
            "confianca": confianca,
            "estrategia_recomendada": estrategia_recomendada,
            "preco_actual": round(preco, 2),
            "metricas": {
                "atr_relativo_pct": round(atr_rel * 100, 3),
                "range_24h_pct": round(range_pct_24h * 100, 2),
                "ema50_slope_pct_5h": round(ema50_slope * 100, 4),
                "ema20": round(ema20_actual, 2) if ema20_actual else None,
                "ema50": round(ema50_actual, 2) if ema50_actual else None,
                "ema20_acima_ema50": ema20_actual > ema50_actual if ema20_actual and ema50_actual else None,
            },
            "razao": " | ".join(razao),
            "timeframe": timeframe,
            "lookback_horas": lookback,
        }

        _save_cache(resultado)
        return resultado

    except Exception as e:
        return {"regime": "DESCONHECIDO", "confianca": 0, "erro": str(e)}


def snapshot_mercado(symbol: str = "BTC/USDT") -> dict:
    """
    Snapshot rápido do mercado para contexto do CFO.
    Combina regime + preço actual + variação 24h.
    """
    try:
        ex = _get_exchange()
        ticker = ex.fetch_ticker(symbol)
        regime_data = detectar_regime(symbol)

        return {
            "symbol": symbol,
            "preco": ticker.get("last"),
            "variacao_24h_pct": round(ticker.get("percentage", 0), 2),
            "high_24h": ticker.get("high"),
            "low_24h": ticker.get("low"),
            "volume_24h_usdt": round(ticker.get("quoteVolume", 0), 0),
            "regime": regime_data.get("regime", "DESCONHECIDO"),
            "regime_confianca": regime_data.get("confianca", 0),
            "estrategia_recomendada": regime_data.get("estrategia_recomendada", "nenhuma"),
            "regime_razao": regime_data.get("razao", ""),
            "regime_metricas": regime_data.get("metricas", {}),
            "ts": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"symbol": symbol, "erro": str(e), "ts": datetime.now().isoformat()}


if __name__ == "__main__":
    data = snapshot_mercado()
    print(json.dumps(data, indent=2, ensure_ascii=False))
