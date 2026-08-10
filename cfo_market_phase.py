"""
CFO Market Phase — Análise de fase de mercado multi-sinal para o CFO.

Fontes combinadas:
  - SMA200 + RSI14 (diário) → fase estrutural
  - EMA9/21 (30m) → momentum de curto prazo
  - Volume spike (1h) → detecção de movimentos anómalos
  - Funding rate Binance → sentimento alavancado
  - Dominância BTC (CoinGecko) → rotação de capital
  - Fear & Greed Index (alternative.me) → sentimento geral do mercado
  - Calendário económico (ForexFactory) → eventos macro de alto impacto

Estratégias: trailing_stop (bull) | grid (flat) | dca (bear)
Decisão só actua quando ≥4 sinais concordam.
"""
import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Literal

_CACHE_FILE = Path(__file__).parent / "memory" / "cfo_phase_cache.json"
_CACHE_TTL_MINUTES = 30

Phase = Literal["bull", "bear", "flat", "unknown"]


# ── Cache ─────────────────────────────────────────────────────────────────────

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


# ── Exchange ──────────────────────────────────────────────────────────────────

def _get_exchange(market_type: str = "spot"):
    import ccxt
    return ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY", ""),
        "secret": os.getenv("BINANCE_SECRET_KEY", ""),
        "options": {"defaultType": market_type},
    })


# ── Indicadores ───────────────────────────────────────────────────────────────

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
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 1)


# ── Fase estrutural (diário) ──────────────────────────────────────────────────

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


# ── Momentum curto prazo (30m) ────────────────────────────────────────────────

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


# ── Volume spike (1h) ─────────────────────────────────────────────────────────

def _volume_spike(symbol: str = "BTC/USDT") -> dict:
    """
    Detecta spikes de volume anómalos em 1h vs média das últimas 24h.
    Volume >3x da média = sinal de movimentação significativa (possível reversão ou crash).
    """
    try:
        ex = _get_exchange()
        ohlcv = ex.fetch_ohlcv(symbol, "1h", limit=25)
        volumes = [c[5] for c in ohlcv]

        vol_actual = volumes[-1]
        vol_medio_24h = sum(volumes[-25:-1]) / 24

        ratio = vol_actual / vol_medio_24h if vol_medio_24h > 0 else 1.0
        ratio = round(ratio, 2)

        if ratio >= 5:
            alerta = "CRÍTICO"
            descricao = f"Volume {ratio}x da média — possível crash ou pump em curso"
        elif ratio >= 3:
            alerta = "ALTO"
            descricao = f"Volume {ratio}x da média — movimento significativo em curso"
        elif ratio >= 2:
            alerta = "MODERADO"
            descricao = f"Volume {ratio}x da média — actividade acima do normal"
        else:
            alerta = "NORMAL"
            descricao = f"Volume normal ({ratio}x da média)"

        return {
            "ratio_vs_media": ratio,
            "alerta": alerta,
            "descricao": descricao,
            "volume_actual": round(vol_actual, 0),
            "volume_medio_24h": round(vol_medio_24h, 0),
        }
    except Exception as e:
        return {"ratio_vs_media": None, "alerta": "indisponível", "erro": str(e)}


# ── Funding rate ──────────────────────────────────────────────────────────────

def _funding_rate(symbol: str = "BTC/USDT") -> dict:
    """Funding rate de futuros Binance — indica sentimento alavancado."""
    try:
        ex_fut = _get_exchange("future")
        info = ex_fut.fetch_funding_rate(symbol)
        rate = info.get("fundingRate", 0) * 100

        if rate > 0.1:
            sentimento = "extremamente sobrecomprado — risco de long squeeze"
        elif rate > 0.05:
            sentimento = "sobrecomprado (longs pagam shorts)"
        elif rate < -0.05:
            sentimento = "extremamente sobrevendido — risco de short squeeze"
        elif rate < -0.01:
            sentimento = "sobrevendido (shorts pagam longs)"
        else:
            sentimento = "neutro"

        return {"rate_pct": round(rate, 4), "sentimento": sentimento}
    except Exception as e:
        return {"rate_pct": None, "sentimento": "indisponível", "erro": str(e)}


# ── Dominância BTC ────────────────────────────────────────────────────────────

def _dominancia_btc() -> dict:
    """Dominância BTC via CoinGecko."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.coingecko.com/api/v3/global",
            headers={"User-Agent": "Morgan-CFO/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        dom = round(data["data"]["market_cap_percentage"].get("btc", 0), 1)

        if dom > 60:
            interpretacao = "alta — capital concentrado em BTC, altcoins a sofrer"
        elif dom < 45:
            interpretacao = "baixa — altcoins a ganhar (altseason possível)"
        else:
            interpretacao = "neutra"

        return {"dominancia_pct": dom, "interpretacao": interpretacao}
    except Exception as e:
        return {"dominancia_pct": None, "interpretacao": "indisponível", "erro": str(e)}


# ── Fear & Greed Index ────────────────────────────────────────────────────────

def _fear_greed() -> dict:
    """Fear & Greed Index via alternative.me — sentimento geral do mercado (0-100)."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.alternative.me/fng/?limit=1",
            headers={"User-Agent": "Morgan-CFO/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        entry = data["data"][0]
        valor = int(entry["value"])
        classificacao = entry["value_classification"]

        if valor <= 20:
            sinal = "bear"
            descricao = "Medo extremo — oportunidade histórica de compra (DCA)"
        elif valor <= 40:
            sinal = "bear"
            descricao = "Medo — mercado pessimista, DCA favorecido"
        elif valor <= 60:
            sinal = "flat"
            descricao = "Neutro — sem sinal claro"
        elif valor <= 80:
            sinal = "bull"
            descricao = "Ganância — mercado optimista, Trailing Stop a monitorizar"
        else:
            sinal = "bull"
            descricao = "Ganância extrema — risco de reversão iminente"

        return {
            "valor": valor,
            "classificacao": classificacao,
            "sinal": sinal,
            "descricao": descricao,
        }
    except Exception as e:
        return {"valor": None, "classificacao": "indisponível", "sinal": "unknown", "erro": str(e)}


# ── Calendário económico ──────────────────────────────────────────────────────

def _eventos_macro_proximos() -> list[dict]:
    """
    Eventos macro de alto impacto nos próximos 14 dias.
    Fonte primária: ForexFactory API (gratuita).
    Fallback: calendário fixo actualizado manualmente.
    """
    hoje = date.today()
    limite = hoje + timedelta(days=14)
    eventos = []

    # Fonte primária: ForexFactory
    try:
        import urllib.request
        proximos = []
        for semana in ["thisweek", "nextweek"]:
            url = f"https://nfs.faireconomy.media/ff_calendar_{semana}.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Morgan-CFO/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            proximos.extend(data)

        moedas_relevantes = {"USD", "BTC", "ETH"}
        for ev in proximos:
            try:
                ev_date = date.fromisoformat(ev.get("date", "")[:10])
                impacto = ev.get("impact", "").lower()
                moeda = ev.get("currency", "")
                if hoje <= ev_date <= limite and impacto == "high" and moeda in moedas_relevantes:
                    dias_para = (ev_date - hoje).days
                    eventos.append({
                        "data": ev.get("date", "")[:10],
                        "evento": ev.get("title", ""),
                        "impacto": "alto",
                        "moeda": moeda,
                        "dias_para": dias_para,
                    })
            except Exception:
                pass
    except Exception:
        pass

    # Fallback: calendário fixo se ForexFactory falhar
    if not eventos:
        calendario_fixo = [
            {"data": "2026-08-13", "evento": "US CPI Julho 2026", "impacto": "alto"},
            {"data": "2026-09-11", "evento": "US CPI Agosto 2026", "impacto": "alto"},
            {"data": "2026-09-17", "evento": "Fed FOMC — decisão taxa de juro", "impacto": "alto"},
            {"data": "2026-10-09", "evento": "US CPI Setembro 2026", "impacto": "alto"},
            {"data": "2026-11-05", "evento": "Fed FOMC — decisão taxa de juro", "impacto": "alto"},
            {"data": "2026-12-16", "evento": "Fed FOMC — decisão taxa de juro", "impacto": "alto"},
        ]
        for ev in calendario_fixo:
            try:
                ev_date = date.fromisoformat(ev["data"])
                if hoje <= ev_date <= limite:
                    eventos.append({**ev, "dias_para": (ev_date - hoje).days})
            except Exception:
                pass

    return sorted(eventos, key=lambda x: x["dias_para"])


# ── Snapshot completo ─────────────────────────────────────────────────────────

def snapshot_fase(symbol: str = "BTC/USDT", use_cache: bool = True) -> dict:
    """
    Snapshot completo de fase de mercado para o CFO.
    Combina 6 fontes independentes. Estratégia só muda quando ≥4 sinais concordam.
    Estratégias: trailing_stop (bull) | grid (flat) | dca (bear)
    """
    if use_cache:
        cached = _load_cache()
        if cached:
            return cached

    estrutural = _fase_estrutural(symbol)
    curto_prazo = _fase_curto_prazo(symbol)
    volume = _volume_spike(symbol)
    funding = _funding_rate(symbol)
    dominancia = _dominancia_btc()
    fg = _fear_greed()
    macro = _eventos_macro_proximos()

    # ── Sistema de votação multi-sinal ────────────────────────────────────────
    # Cada fonte vota: "bull", "flat", "bear", ou "abstain"
    votos = []

    # Voto 1: fase estrutural (SMA200 + RSI)
    fase_est = estrutural.get("fase", "unknown")
    if fase_est in ("bull", "flat", "bear"):
        votos.append(fase_est)

    # Voto 2: momentum curto prazo
    tendencia = curto_prazo.get("tendencia", "unknown")
    if tendencia == "alta":
        votos.append("bull")
    elif tendencia == "baixa":
        votos.append("bear")
    else:
        votos.append("flat")

    # Voto 3: Fear & Greed
    fg_sinal = fg.get("sinal", "unknown")
    if fg_sinal in ("bull", "flat", "bear"):
        votos.append(fg_sinal)

    # Voto 4: Funding rate
    fr = funding.get("rate_pct")
    if fr is not None:
        if fr > 0.05:
            votos.append("bull")
        elif fr < -0.01:
            votos.append("bear")
        else:
            votos.append("flat")

    # Voto 5: Dominância BTC
    dom = dominancia.get("dominancia_pct")
    if dom is not None:
        if dom > 60:
            votos.append("bear")  # capital fugiu para BTC = altcoins em bear
        elif dom < 45:
            votos.append("bull")  # altseason = bull geral
        else:
            votos.append("flat")

    # Contagem
    contagem = {"bull": votos.count("bull"), "flat": votos.count("flat"), "bear": votos.count("bear")}
    total_votos = len(votos)
    fase_maioria = max(contagem, key=contagem.get)
    votos_maioria = contagem[fase_maioria]
    confianca = round(votos_maioria / total_votos * 100) if total_votos > 0 else 0

    # Estratégia (só actua com ≥4 sinais concordantes de 5)
    if votos_maioria >= 4:
        if fase_maioria == "bull":
            estrategia = "trailing_stop"
            estrategia_razao = f"Bull confirmado ({votos_maioria}/5 sinais) — Trailing Stop activo"
        elif fase_maioria == "bear":
            estrategia = "dca"
            estrategia_razao = f"Bear confirmado ({votos_maioria}/5 sinais) — DCA activo, Grid parado"
        else:
            estrategia = "grid"
            estrategia_razao = f"Lateral confirmado ({votos_maioria}/5 sinais) — Grid óptimo"
    else:
        estrategia = "grid"  # default conservador
        estrategia_razao = f"Sinal inconclusivo ({votos_maioria}/5 para {fase_maioria}) — manter Grid por precaução"

    # ── Alertas ───────────────────────────────────────────────────────────────
    alertas = []

    # Volume spike
    vol_alerta = volume.get("alerta", "NORMAL")
    if vol_alerta in ("ALTO", "CRÍTICO"):
        alertas.append(f"VOLUME {vol_alerta}: {volume.get('descricao', '')}")

    # Funding rate extremo
    if fr is not None:
        if fr > 0.1:
            alertas.append(f"FUNDING EXTREMO: {fr:.3f}% — risco de long squeeze")
        elif fr < -0.05:
            alertas.append(f"FUNDING NEGATIVO: {fr:.3f}% — risco de short squeeze")

    # Fear & Greed extremo
    fg_val = fg.get("valor")
    if fg_val is not None:
        if fg_val <= 20:
            alertas.append(f"MEDO EXTREMO (F&G={fg_val}) — oportunidade histórica, aumentar DCA")
        elif fg_val >= 80:
            alertas.append(f"GANÂNCIA EXTREMA (F&G={fg_val}) — risco de reversão, reduzir exposição")

    # Eventos macro próximos
    if macro:
        ev = macro[0]
        if ev["dias_para"] <= 3:
            alertas.append(f"EVENTO MACRO EM {ev['dias_para']}d: {ev['evento']} — reduzir exposição")
        elif ev["dias_para"] <= 7:
            alertas.append(f"Evento macro em {ev['dias_para']}d: {ev['evento']}")

    resultado = {
        "ts": datetime.now().isoformat(),
        "symbol": symbol,
        "fase_estrutural": estrutural,
        "fase_curto_prazo": curto_prazo,
        "volume_spike": volume,
        "funding_rate": funding,
        "dominancia_btc": dominancia,
        "fear_greed": fg,
        "eventos_macro_proximos": macro,
        "votos": contagem,
        "confianca_pct": confianca,
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
    fg = s.get("fear_greed", {})
    fr = s["funding_rate"]
    votos = s.get("votos", {})

    linhas = [
        f"FASE: {est.get('fase','?').upper()} | Confiança: {s.get('confianca_pct',0)}% ({votos.get('bull',0)}B/{votos.get('flat',0)}F/{votos.get('bear',0)}Be)",
        f"BTC ${est.get('preco','?')} | SMA200 ${est.get('sma200','?')} ({est.get('distancia_sma200_pct',0):+.1f}%) | RSI={est.get('rsi14','?')}",
        f"F&G: {fg.get('valor','?')} ({fg.get('classificacao','?')}) | Funding: {fr.get('rate_pct','?')}%",
        f"Estratégia: {s['estrategia_recomendada'].upper()} — {s['estrategia_razao']}",
    ]

    for a in s.get("alertas", []):
        linhas.append(f"⚠ {a}")

    return "\n".join(linhas)
