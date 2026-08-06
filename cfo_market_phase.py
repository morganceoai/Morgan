"""
CFO Market Phase — Análise de fase de mercado multi-timeframe para o CFO.

Vai além do cfo_market.py (regime simples) — combina:
  - SMA200 + RSI14 (timeframe diário) → fase estrutural
  - EMA9/21 (30m) → fase de curto prazo
  - Funding rate Binance → sentimento alavancado
  - Dominância BTC → rotação de capital cripto
  - Próximos eventos macro (hard-coded + actualizável)

Output estruturado para o ciclo de decisão do CFO.
"""
import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Literal

_CACHE_FILE = Path(__file__).parent / "memory" / "cfo_phase_cache.json"
_CACHE_TTL_MINUTES = 30  # fase não muda ao minuto

Phase = Literal["bull", "bear", "flat", "unknown"]


# ── Cache ────────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    try:
        data = json.loads(_CACHE_FILE.read_text())
        ts = datetime.fromisoformat(data.get("ts", "2000-01-01"))
        if (datetime.now() - ts).total_seconds() / 60 < _CACHE_TTL_MINUTES:
            return data
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    _CACHE_FILE.parent.mkdir(exist_ok=True)
    _CACHE_FILE.write_text(json.dumps({**data, "ts": datetime.now().isoformat()}, ensure_ascii=False, indent=2))


# ── Exchange ─────────────────────────────────────────────────────────────────

def _get_exchange():
    import ccxt
    return ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY", ""),
        "secret": os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": "spot"},
    })


# ── Indicadores ──────────────────────────────────────────────────────────────

def _sma(closes: list, period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _ema(closes: list, period: int) -> float | None:
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = c * k + ema * (1 - k)
    return ema


def _rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [abs(d) for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


# ── Fase estrutural (diário) ─────────────────────────────────────────────────

def _fase_estrutural(symbol: str = "BTC/USDT") -> dict:
    """SMA200 + RSI14 em timeframe diário → fase de longo prazo."""
    try:
        ex = _get_exchange()
        ohlcv = ex.fetch_ohlcv(symbol, "1d", limit=220)
        closes = [c[4] for c in ohlcv]
        preco = closes[-1]

        sma200 = _sma(closes, 200)
        rsi = _rsi(closes, 14)

        if sma200 is None or rsi is None:
            return {"fase": "unknown", "razao": "dados insuficientes"}

        acima_sma200 = preco > sma200
        distancia_sma_pct = round((preco - sma200) / sma200 * 100, 1)

        if acima_sma200 and rsi > 55:
            fase = "bull"
        elif not acima_sma200 and rsi < 45:
            fase = "bear"
        else:
            fase = "flat"

        return {
            "fase": fase,
            "preco": round(preco, 0),
            "sma200": round(sma200, 0),
            "distancia_sma200_pct": distancia_sma_pct,
            "acima_sma200": acima_sma200,
            "rsi14": rsi,
            "razao": f"Preço {'acima' if acima_sma200 else 'abaixo'} SMA200 ({distancia_sma_pct:+.1f}%), RSI={rsi}",
        }
    except Exception as e:
        return {"fase": "unknown", "razao": str(e)}


# ── Fase curto prazo (30m) ────────────────────────────────────────────────────

def _fase_curto_prazo(symbol: str = "BTC/USDT") -> dict:
    """EMA9/21 em 30m → momentum de curto prazo."""
    try:
        ex = _get_exchange()
        ohlcv = ex.fetch_ohlcv(symbol, "30m", limit=50)
        closes = [c[4] for c in ohlcv]

        ema9 = _ema(closes, 9)
        ema21 = _ema(closes, 21)

        if ema9 is None or ema21 is None:
            return {"tendencia": "unknown"}

        if ema9 > ema21 * 1.001:
            tendencia = "alta"
        elif ema9 < ema21 * 0.999:
            tendencia = "baixa"
        else:
            tendencia = "lateral"

        return {
            "tendencia": tendencia,
            "ema9": round(ema9, 0),
            "ema21": round(ema21, 0),
            "diferenca_pct": round((ema9 - ema21) / ema21 * 100, 2),
        }
    except Exception as e:
        return {"tendencia": "unknown", "erro": str(e)}


# ── Funding rate ──────────────────────────────────────────────────────────────

def _funding_rate(symbol: str = "BTC/USDT") -> dict:
    """Funding rate de futuros Binance — indica sentimento alavancado."""
    try:
        import ccxt
        ex_fut = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY", ""),
            "secret": os.getenv("BINANCE_SECRET_KEY", ""),
            "options": {"defaultType": "future"},
        })
        info = ex_fut.fetch_funding_rate(symbol)
        rate = info.get("fundingRate", 0) * 100  # em percentagem

        if rate > 0.05:
            sentimento = "sobrecomprado (longs pagam shorts)"
        elif rate < -0.01:
            sentimento = "sobrevendido (shorts pagam longs)"
        else:
            sentimento = "neutro"

        return {
            "rate_pct": round(rate, 4),
            "sentimento": sentimento,
        }
    except Exception as e:
        return {"rate_pct": None, "sentimento": "indisponível", "erro": str(e)}


# ── Dominância BTC ────────────────────────────────────────────────────────────

def _dominancia_btc() -> dict:
    """Dominância BTC via CoinGecko (sem API key necessária)."""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/global"
        req = urllib.request.Request(url, headers={"User-Agent": "Morgan-CFO/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        dom = data["data"]["market_cap_percentage"].get("btc", 0)
        dom = round(dom, 1)

        if dom > 60:
            interpretacao = "dominância alta — altcoins a sofrer, capital concentrado em BTC"
        elif dom < 45:
            interpretacao = "dominância baixa — altcoins a ganhar força (altseason possível)"
        else:
            interpretacao = "dominância neutra"

        return {"dominancia_pct": dom, "interpretacao": interpretacao}
    except Exception as e:
        return {"dominancia_pct": None, "interpretacao": "indisponível", "erro": str(e)}


# ── Eventos macro ─────────────────────────────────────────────────────────────

def _eventos_macro_proximos() -> list[dict]:
    """
    Calendário de eventos macro de alto impacto.
    Actualizar manualmente ou via feed externo quando disponível.
    Retorna eventos nos próximos 14 dias.
    """
    hoje = date.today()
    limite = hoje + timedelta(days=14)

    # Calendário fixo — actualizar mensalmente
    # Formato: {"data": "YYYY-MM-DD", "evento": "...", "impacto": "alto|médio"}
    calendario = [
        # Fed FOMC meetings 2026
        {"data": "2026-09-17", "evento": "Fed FOMC — decisão de taxa de juro", "impacto": "alto"},
        {"data": "2026-11-05", "evento": "Fed FOMC — decisão de taxa de juro", "impacto": "alto"},
        {"data": "2026-12-16", "evento": "Fed FOMC — decisão de taxa de juro", "impacto": "alto"},
        # CPI mensal (estimativas — primeiras semanas do mês)
        {"data": "2026-08-13", "evento": "US CPI Julho 2026", "impacto": "alto"},
        {"data": "2026-09-11", "evento": "US CPI Agosto 2026", "impacto": "alto"},
        {"data": "2026-10-09", "evento": "US CPI Setembro 2026", "impacto": "alto"},
        # Bitcoin ETF — datas relevantes (exemplo)
        {"data": "2026-10-01", "evento": "Fim do trimestre — rebalanceamento institucional", "impacto": "médio"},
    ]

    proximos = []
    for ev in calendario:
        try:
            ev_date = date.fromisoformat(ev["data"])
            if hoje <= ev_date <= limite:
                dias_para = (ev_date - hoje).days
                proximos.append({**ev, "dias_para": dias_para})
        except Exception:
            pass

    return sorted(proximos, key=lambda x: x["dias_para"])


# ── Snapshot completo ─────────────────────────────────────────────────────────

def snapshot_fase(symbol: str = "BTC/USDT", use_cache: bool = True) -> dict:
    """
    Snapshot completo de fase de mercado para o CFO.
    Combina todos os indicadores num único dict estruturado.
    """
    if use_cache:
        cached = _load_cache()
        if cached:
            return cached

    estrutural = _fase_estrutural(symbol)
    curto_prazo = _fase_curto_prazo(symbol)
    funding = _funding_rate(symbol)
    dominancia = _dominancia_btc()
    macro = _eventos_macro_proximos()

    # Estratégia recomendada baseada na combinação de fases
    fase = estrutural.get("fase", "unknown")
    tendencia = curto_prazo.get("tendencia", "unknown")

    if fase == "bull" and tendencia == "alta":
        estrategia = "trailing_stop"
        estrategia_razao = "Mercado em bull estrutural com momentum de curto prazo — deixar lucros correr"
    elif fase == "bull" and tendencia in ("lateral", "baixa"):
        estrategia = "dca_reforco"
        estrategia_razao = "Bull estrutural mas sem momentum imediato — DCA é seguro, grid pode operar"
    elif fase == "flat":
        estrategia = "grid_bot"
        estrategia_razao = "Mercado lateral — grid bot é a estratégia óptima"
    elif fase == "bear":
        estrategia = "dca_apenas"
        estrategia_razao = "Bear market — parar grid, apenas DCA de longo prazo"
    else:
        estrategia = "observar"
        estrategia_razao = "Fase indefinida — manter posição actual sem novas entradas"

    # Alerta de funding rate extremo
    alertas = []
    fr = funding.get("rate_pct")
    if fr is not None:
        if fr > 0.1:
            alertas.append(f"FUNDING RATE EXTREMO: {fr:.3f}% — risco de long squeeze iminente")
        elif fr < -0.05:
            alertas.append(f"FUNDING RATE NEGATIVO: {fr:.3f}% — pressão de shorts, possível rebound")

    if macro:
        ev = macro[0]
        if ev["dias_para"] <= 3 and ev["impacto"] == "alto":
            alertas.append(f"EVENTO MACRO EM {ev['dias_para']}d: {ev['evento']} — reduzir exposição")

    resultado = {
        "ts": datetime.now().isoformat(),
        "symbol": symbol,
        "fase_estrutural": estrutural,
        "fase_curto_prazo": curto_prazo,
        "funding_rate": funding,
        "dominancia_btc": dominancia,
        "eventos_macro_proximos": macro,
        "estrategia_recomendada": estrategia,
        "estrategia_razao": estrategia_razao,
        "alertas": alertas,
    }

    _save_cache(resultado)
    return resultado


def resumo_para_briefing(symbol: str = "BTC/USDT") -> str:
    """Versão compacta para o briefing matinal das 7h."""
    s = snapshot_fase(symbol)
    est = s["fase_estrutural"]
    cp = s["fase_curto_prazo"]
    fr = s["funding_rate"]
    dom = s["dominancia_btc"]

    linhas = [
        f"FASE: {est.get('fase','?').upper()} estrutural | {cp.get('tendencia','?').upper()} 30m",
        f"BTC ${est.get('preco','?')} | SMA200 ${est.get('sma200','?')} ({est.get('distancia_sma200_pct',0):+.1f}%) | RSI={est.get('rsi14','?')}",
        f"Funding: {fr.get('rate_pct','?')}% ({fr.get('sentimento','?')}) | Dom BTC: {dom.get('dominancia_pct','?')}%",
        f"Estratégia: {s['estrategia_recomendada'].upper()} — {s['estrategia_razao']}",
    ]

    if s["alertas"]:
        for a in s["alertas"]:
            linhas.append(f"⚠ {a}")

    macro = s.get("eventos_macro_proximos", [])
    if macro:
        ev = macro[0]
        linhas.append(f"Próximo evento: {ev['evento']} em {ev['dias_para']}d")

    return "\n".join(linhas)
