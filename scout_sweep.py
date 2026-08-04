"""
Scout Sweep — recolha contínua de sinais de mercado sem LLM.
Corre a cada 6 horas via scheduler próprio do Scout.

Fontes (gratuitas, €0/mês):
  HN Firebase, Product Hunt, Reddit, arxiv, GitHub Trending,
  Remotive, Dev.to, Lobsters, Etsy autocomplete, pytrends,
  BetaList, Gumroad, Product Hunt Ship, App Store RSS

Saída: memory/signal_queue.json com sinais + trajectory score.
O Scout só é acordado com Claude quando velocity > 2x baseline.
"""
import json
import os
import re
import time
import threading
import feedparser
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).parent
_QUEUE_FILE = _BASE / "memory" / "signal_queue.json"
_BASELINE_FILE = _BASE / "memory" / "sweep_baseline.json"
_TRIGGERED_FILE = _BASE / "memory" / "sweep_triggered.json"
_SOURCE_HEALTH_FILE = _BASE / "memory" / "sweep_source_health.json"

# Quantas falhas consecutivas até pausar a fonte
_MAX_CONSECUTIVE_FAILS = 3

# Keywords BCVertex para pytrends e filtragem de relevância
BCVERTEX_KEYWORDS = [
    "digital planner", "notion template", "ai automation tool",
    "passive income digital", "solopreneur saas", "printable planner",
    "ai productivity", "budget planner pdf",
]

# Subreddits com sinal de oportunidade de negócio
REDDIT_SUBS = [
    "SaaS", "entrepreneur", "nocode", "sidehustle",
    "AItools", "SideProject", "passive_income", "indiehackers",
]

# Categorias BCVertex para filtro de relevância
BCVERTEX_CATEGORIES = {
    "digital", "saas", "automation", "ai", "template", "planner",
    "productivity", "passive", "income", "nocode", "notion", "pdf",
    "ebook", "course", "newsletter", "tool", "plugin", "extension",
}

# Palavras-chave de exclusão (negócios físicos, muito fora do perfil)
EXCLUDE_KEYWORDS = {
    "hardware", "manufacturing", "restaurant", "retail", "physical",
    "inventory", "warehouse", "shipping", "franchise",
}


# ── Utilitários ───────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10, headers: dict = None) -> Optional[dict]:
    try:
        h = {"User-Agent": "Mozilla/5.0 BCVertex Scout"}
        if headers:
            h.update(headers)
        r = requests.get(url, timeout=timeout, headers=h)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _http_text(url: str, timeout: int = 10) -> str:
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0 BCVertex Scout"})
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


def _is_relevant(text: str) -> bool:
    """Filtra conteúdo claramente fora do perfil BCVertex."""
    text_lower = text.lower()
    if any(ex in text_lower for ex in EXCLUDE_KEYWORDS):
        return False
    return True


def _load_queue() -> list:
    if _QUEUE_FILE.exists():
        try:
            return json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_queue(queue: list) -> None:
    _QUEUE_FILE.parent.mkdir(exist_ok=True)
    _QUEUE_FILE.write_text(
        json.dumps(queue[-500:], indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def _load_baseline() -> dict:
    if _BASELINE_FILE.exists():
        try:
            return json.loads(_BASELINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_baseline(b: dict) -> None:
    _BASELINE_FILE.parent.mkdir(exist_ok=True)
    _BASELINE_FILE.write_text(json.dumps(b, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Source health tracking ────────────────────────────────────────────────────

def _load_source_health() -> dict:
    if _SOURCE_HEALTH_FILE.exists():
        try:
            return json.loads(_SOURCE_HEALTH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_source_health(h: dict) -> None:
    _SOURCE_HEALTH_FILE.parent.mkdir(exist_ok=True)
    _SOURCE_HEALTH_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")


def _record_source_success(source_name: str) -> None:
    h = _load_source_health()
    h[source_name] = {"consecutive_fails": 0, "last_success": datetime.now().isoformat()}
    _save_source_health(h)


def _record_source_fail(source_name: str, error: str = "") -> None:
    h = _load_source_health()
    entry = h.get(source_name, {"consecutive_fails": 0})
    entry["consecutive_fails"] = entry.get("consecutive_fails", 0) + 1
    entry["last_fail"] = datetime.now().isoformat()
    entry["last_error"] = error[:200]
    h[source_name] = entry
    _save_source_health(h)


def _should_skip_source(source_name: str) -> bool:
    """Pausa fonte com ≥3 falhas consecutivas. Tenta de novo após 24h."""
    h = _load_source_health()
    entry = h.get(source_name, {})
    if entry.get("consecutive_fails", 0) < _MAX_CONSECUTIVE_FAILS:
        return False
    last_fail = entry.get("last_fail", "")
    if last_fail:
        try:
            delta_h = (datetime.now() - datetime.fromisoformat(last_fail)).total_seconds() / 3600
            if delta_h > 24:
                return False  # tentar de novo após 24h
        except Exception:
            pass
    return True


def _get_source_health_summary() -> dict:
    """Retorna fontes pausadas para incluir no resumo do sweep."""
    h = _load_source_health()
    return {
        nome: entry for nome, entry in h.items()
        if entry.get("consecutive_fails", 0) >= _MAX_CONSECUTIVE_FAILS
    }


# ── Trajectory scoring ────────────────────────────────────────────────────────

_COLD_START_VELOCITY = -1.0  # sentinel: sinal novo sem histórico suficiente


def _record_signal(topic: str, source: str) -> float:
    """
    Regista uma menção e calcula o velocity score.
    Velocity = menções esta semana / média das últimas 4 semanas.
    Retorna -1.0 se não há histórico suficiente (cold start — sinal novo).
    """
    baseline = _load_baseline()
    semana = datetime.now().strftime("%Y-W%W")

    if topic not in baseline:
        baseline[topic] = {}
    if semana not in baseline[topic]:
        baseline[topic][semana] = 0
    baseline[topic][semana] += 1

    semanas = sorted(baseline[topic].keys())
    hist = [baseline[topic][s] for s in semanas[-5:-1]]  # 4 semanas anteriores

    # Cold start: < 2 semanas de histórico → marcar como sinal novo sem comparação
    if len(hist) < 2:
        _save_baseline(baseline)
        return _COLD_START_VELOCITY

    media = sum(hist) / len(hist)
    atual = baseline[topic][semana]
    velocity = atual / media if media > 0 else 1.0

    _save_baseline(baseline)
    return round(velocity, 2)


def _quality_prefilter(titulo: str, descricao: str = "") -> bool:
    """
    Pré-filtro sem Claude. Verifica fit básico com BCVertex antes de gastar tokens.
    Requer: pelo menos 1 categoria BCVertex presente E nenhuma palavra de exclusão.
    """
    texto = f"{titulo} {descricao}".lower()
    # Rejeitar se contém palavras de negócio físico
    if not _is_relevant(texto):
        return False
    # Exigir pelo menos 1 categoria BCVertex — evita passar ruído genérico
    if not any(cat in texto for cat in BCVERTEX_CATEGORIES):
        return False
    # Verificar se já foi rejeitado antes
    try:
        from scout_agent import _load_state
        state = _load_state()
        rejeitados = [r.get("nome", "").lower() if isinstance(r, dict) else str(r).lower()
                      for r in state.get("oportunidades_rejeitadas", [])]
        if any(rej[:20] in texto for rej in rejeitados if len(rej) > 5):
            return False
    except Exception:
        pass
    return True


# ── Colectores ────────────────────────────────────────────────────────────────

def _sweep_hacker_news() -> list:
    """HN Firebase — top stories + Ask HN. Gratuito, sem auth."""
    sinais = []
    try:
        # Top stories
        ids = _http_get("https://hacker-news.firebaseio.com/v0/topstories.json") or []
        for item_id in ids[:30]:
            item = _http_get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
            if not item:
                continue
            titulo = item.get("title", "")
            score = item.get("score", 0)
            if score < 50:
                continue
            if not _quality_prefilter(titulo):
                continue
            vel = _record_signal(titulo[:40], "hn_top")
            sinais.append({
                "fonte": "hn_top", "titulo": titulo, "score_hn": score,
                "velocity": vel, "url": f"https://news.ycombinator.com/item?id={item_id}",
                "ts": datetime.now().isoformat(),
            })

        # Ask HN — pedidos directos de produto
        ask_ids = _http_get("https://hacker-news.firebaseio.com/v0/askstories.json") or []
        for item_id in ask_ids[:15]:
            item = _http_get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
            if not item:
                continue
            titulo = item.get("title", "")
            if item.get("score", 0) < 30:
                continue
            if not _quality_prefilter(titulo):
                continue
            vel = _record_signal(titulo[:40], "hn_ask")
            sinais.append({
                "fonte": "hn_ask", "titulo": titulo, "score_hn": item.get("score", 0),
                "velocity": vel, "url": f"https://news.ycombinator.com/item?id={item_id}",
                "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_product_hunt() -> list:
    """Product Hunt — RSS público, sem auth."""
    sinais = []
    try:
        feed = feedparser.parse("https://www.producthunt.com/feed")
        for entry in feed.entries[:20]:
            titulo = entry.get("title", "")
            desc = entry.get("summary", "")
            if not _quality_prefilter(titulo, desc):
                continue
            vel = _record_signal(titulo[:40], "product_hunt")
            sinais.append({
                "fonte": "product_hunt", "titulo": titulo, "descricao": desc[:300],
                "velocity": vel, "url": entry.get("link", ""),
                "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_reddit() -> list:
    """Reddit — JSON público sem autenticação (hot posts por subreddit)."""
    sinais = []
    try:
        for sub in REDDIT_SUBS:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
            data = _http_get(url, headers={"User-Agent": "BCVertex Scout v1.0"})
            if not data:
                time.sleep(2)
                continue
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                p = post.get("data", {})
                titulo = p.get("title", "")
                score = p.get("score", 0)
                if score < 100:
                    continue
                if not _quality_prefilter(titulo, p.get("selftext", "")[:200]):
                    continue
                vel = _record_signal(titulo[:40], f"reddit_{sub}")
                sinais.append({
                    "fonte": f"reddit_{sub}", "titulo": titulo, "score_reddit": score,
                    "velocity": vel, "url": f"https://reddit.com{p.get('permalink', '')}",
                    "ts": datetime.now().isoformat(),
                })
            time.sleep(1)  # rate limit cortesia
    except Exception:
        pass
    return sinais


def _sweep_arxiv() -> list:
    """arxiv cs.AI + cs.LG — RSS gratuito, sem auth."""
    sinais = []
    try:
        for cat in ["cs.AI", "cs.LG"]:
            feed = feedparser.parse(
                f"http://export.arxiv.org/rss/{cat}"
            )
            for entry in feed.entries[:10]:
                titulo = entry.get("title", "")
                summary = entry.get("summary", "")[:300]
                # Só papers com palavras-chave de produto/ferramenta
                keywords = ["tool", "framework", "system", "agent", "automation",
                            "application", "platform", "assistant", "workflow"]
                if not any(k in titulo.lower() or k in summary.lower() for k in keywords):
                    continue
                vel = _record_signal(titulo[:40], "arxiv")
                sinais.append({
                    "fonte": "arxiv", "titulo": titulo, "resumo": summary,
                    "velocity": vel, "url": entry.get("link", ""),
                    "ts": datetime.now().isoformat(),
                })
    except Exception:
        pass
    return sinais


def _sweep_github_trending() -> list:
    """GitHub Trending — scraping simples da página pública."""
    sinais = []
    try:
        html = _http_text("https://github.com/trending?since=daily&spoken_language_code=")
        # Extrair nomes de repositórios via regex
        repos = re.findall(r'href="/([^/]+/[^/"]+)"[^>]*>\s*(?:<[^>]+>)*\s*([^<\n]+)', html)
        seen = set()
        for href, desc in repos[:30]:
            if href in seen or "/" not in href:
                continue
            seen.add(href)
            if not _quality_prefilter(href, desc):
                continue
            vel = _record_signal(href, "github_trending")
            sinais.append({
                "fonte": "github_trending", "titulo": href, "descricao": desc.strip()[:200],
                "velocity": vel, "url": f"https://github.com/{href}",
                "ts": datetime.now().isoformat(),
            })
            if len(sinais) >= 10:
                break
    except Exception:
        pass
    return sinais


def _sweep_remotive() -> list:
    """Remotive — JSON público gratuito, sem auth. Jobs remotos por categoria."""
    sinais = []
    try:
        data = _http_get("https://remotive.com/api/remote-jobs?limit=50")
        if not data:
            return sinais
        jobs = data.get("jobs", [])
        # Agrupar por categoria para detectar mercados em crescimento
        from collections import Counter
        cats = Counter(j.get("category", "") for j in jobs if j.get("category"))
        for cat, count in cats.most_common(10):
            if not _quality_prefilter(cat):
                continue
            vel = _record_signal(cat, "remotive")
            sinais.append({
                "fonte": "remotive", "titulo": f"[jobs] {cat}", "count": count,
                "velocity": vel, "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_devto() -> list:
    """Dev.to API — gratuita, sem auth."""
    sinais = []
    try:
        data = _http_get("https://dev.to/api/articles?top=7&per_page=20")
        if not data:
            return sinais
        for article in data:
            titulo = article.get("title", "")
            tags = article.get("tag_list", [])
            if not any(t in ["productivity", "tools", "ai", "startup", "career", "showdev"]
                       for t in tags):
                continue
            if not _quality_prefilter(titulo):
                continue
            vel = _record_signal(titulo[:40], "devto")
            sinais.append({
                "fonte": "devto", "titulo": titulo, "tags": tags,
                "velocity": vel, "url": article.get("url", ""),
                "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_lobsters() -> list:
    """Lobsters — JSON gratuito, sem auth. Comunidade técnica de alta qualidade."""
    sinais = []
    try:
        data = _http_get("https://lobste.rs/hottest.json")
        if not data:
            return sinais
        for item in data[:15]:
            titulo = item.get("title", "")
            tags = item.get("tags", [])
            if not _quality_prefilter(titulo):
                continue
            vel = _record_signal(titulo[:40], "lobsters")
            sinais.append({
                "fonte": "lobsters", "titulo": titulo, "tags": tags,
                "velocity": vel, "url": item.get("url", ""),
                "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_etsy_autocomplete() -> list:
    """Etsy search autocomplete — endpoint público, sem auth."""
    sinais = []
    seed_terms = ["planner", "digital template", "printable", "notion", "budget tracker",
                  "habit tracker", "meal planner", "weekly planner", "ai tool"]
    try:
        for term in seed_terms:
            url = f"https://www.etsy.com/api/v3/ajax/bespoke/public/canopy/top_searches?keywords={requests.utils.quote(term)}&language=en&location_id=1&limit=8"
            data = _http_get(url)
            if not data:
                time.sleep(1)
                continue
            suggestions = data.get("results", []) or data.get("data", [])
            for s in suggestions[:5]:
                query = s.get("keywords", s.get("query", "")) if isinstance(s, dict) else str(s)
                if not query or len(query) < 5:
                    continue
                vel = _record_signal(query, "etsy_suggest")
                sinais.append({
                    "fonte": "etsy_suggest", "titulo": query,
                    "velocity": vel, "ts": datetime.now().isoformat(),
                })
            time.sleep(0.5)
    except Exception:
        pass
    return sinais


def _sweep_pytrends() -> list:
    """Google Trends via pytrends — keywords BCVertex."""
    sinais = []
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
        # Dividir em grupos de 5 (limite pytrends)
        groups = [BCVERTEX_KEYWORDS[i:i+5] for i in range(0, len(BCVERTEX_KEYWORDS), 5)]
        for group in groups:
            try:
                pt.build_payload(group, timeframe="now 7-d", geo="")
                df = pt.interest_over_time()
                if df.empty:
                    continue
                for kw in group:
                    if kw not in df.columns:
                        continue
                    recent_avg = df[kw].tail(7).mean()
                    prev_avg = df[kw].head(7).mean() if len(df) > 7 else recent_avg
                    velocity = recent_avg / prev_avg if prev_avg > 0 else 1.0
                    if velocity < 1.3:
                        continue
                    _record_signal(kw, "pytrends")
                    sinais.append({
                        "fonte": "pytrends", "titulo": kw,
                        "velocity": round(velocity, 2),
                        "ts": datetime.now().isoformat(),
                    })
                time.sleep(3)
            except Exception:
                time.sleep(5)
    except ImportError:
        pass
    except Exception:
        pass
    return sinais


def _sweep_betalist() -> list:
    """BetaList — RSS público, sem auth. Pre-launches 3-6 meses antes do Product Hunt."""
    sinais = []
    try:
        feed = feedparser.parse("https://betalist.com/feed")
        for entry in feed.entries[:15]:
            titulo = entry.get("title", "")
            desc = entry.get("summary", "")[:300]
            if not _quality_prefilter(titulo, desc):
                continue
            vel = _record_signal(titulo[:40], "betalist")
            sinais.append({
                "fonte": "betalist", "titulo": titulo, "descricao": desc,
                "velocity": vel, "url": entry.get("link", ""),
                "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_gumroad() -> list:
    """Gumroad discover — scraping da página pública."""
    sinais = []
    try:
        html = _http_text("https://app.gumroad.com/discover?sort=featured")
        # Extrair títulos de produtos
        titles = re.findall(r'<h3[^>]*>([^<]{5,80})</h3>', html)
        for t in titles[:20]:
            t = t.strip()
            if not t or not _quality_prefilter(t):
                continue
            vel = _record_signal(t[:40], "gumroad")
            sinais.append({
                "fonte": "gumroad", "titulo": t,
                "velocity": vel, "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


def _sweep_appstore_rss() -> list:
    """App Store RSS — top apps por categoria. Apple API pública."""
    sinais = []
    categories = {
        "productivity": "6007",
        "business": "6000",
        "education": "6017",
    }
    try:
        for cat_name, cat_id in categories.items():
            feed = feedparser.parse(
                f"https://itunes.apple.com/us/rss/topfreeapplications/limit=20/genre={cat_id}/json"
            )
            for entry in (feed.entries or [])[:10]:
                titulo = entry.get("title", "")
                if not _quality_prefilter(titulo):
                    continue
                vel = _record_signal(titulo[:40], f"appstore_{cat_name}")
                sinais.append({
                    "fonte": f"appstore_{cat_name}", "titulo": titulo,
                    "velocity": vel, "ts": datetime.now().isoformat(),
                })
    except Exception:
        pass
    return sinais


def _sweep_indiehackers() -> list:
    """IndieHackers — RSS de posts recentes. Fundadores com receita real."""
    sinais = []
    try:
        feed = feedparser.parse("https://www.indiehackers.com/feed.rss")
        for entry in feed.entries[:20]:
            titulo = entry.get("title", "")
            desc = entry.get("summary", "")[:300]
            if not _quality_prefilter(titulo, desc):
                continue
            # IH é sempre relevante — fundadores reais com dados reais
            vel = _record_signal(titulo[:40], "indiehackers")
            sinais.append({
                "fonte": "indiehackers", "titulo": titulo, "descricao": desc,
                "velocity": vel, "url": entry.get("link", ""),
                "ts": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return sinais


# ── Ponto de entrada principal ────────────────────────────────────────────────

# Nome interno da fonte → nome legível
SWEEPERS = [
    ("hn", "HN Firebase", _sweep_hacker_news),
    ("product_hunt", "Product Hunt", _sweep_product_hunt),
    ("reddit", "Reddit", _sweep_reddit),
    ("arxiv", "arxiv", _sweep_arxiv),
    ("github_trending", "GitHub Trending", _sweep_github_trending),
    ("remotive", "Remotive", _sweep_remotive),
    ("devto", "Dev.to", _sweep_devto),
    ("lobsters", "Lobsters", _sweep_lobsters),
    ("etsy_suggest", "Etsy Autocomplete", _sweep_etsy_autocomplete),
    ("pytrends", "Google Trends", _sweep_pytrends),
    ("betalist", "BetaList", _sweep_betalist),
    ("gumroad", "Gumroad", _sweep_gumroad),
    ("appstore", "App Store RSS", _sweep_appstore_rss),
    ("indiehackers", "IndieHackers", _sweep_indiehackers),
]


def _get_top_signals_week(top_n: int = 15) -> list:
    """
    Retorna os sinais mais fortes da última semana para a Missão A do Scout.
    Inclui sinais com velocity ≥ 1.5 e sinais novos (cold start).
    Ordenados por velocity descendente (novos ficam no fim).
    """
    queue = _load_queue()
    semana_inicio = datetime.now() - timedelta(days=7)
    recentes = []
    for s in queue:
        try:
            ts = datetime.fromisoformat(s.get("ts", ""))
            if ts >= semana_inicio:
                recentes.append(s)
        except Exception:
            pass

    # Separar: com velocity real vs novos (cold start)
    com_velocity = [s for s in recentes if s.get("velocity", 0) > 0 and s.get("velocity", 0) >= 1.5]
    novos = [s for s in recentes if s.get("velocity", 0) == _COLD_START_VELOCITY]

    # Deduplicar por título
    vistos = set()
    resultado = []
    for s in sorted(com_velocity, key=lambda x: x.get("velocity", 0), reverse=True):
        chave = s.get("titulo", "")[:40]
        if chave not in vistos:
            vistos.add(chave)
            resultado.append(s)
        if len(resultado) >= top_n - 3:
            break

    # Adicionar até 3 sinais novos
    for s in novos[:3]:
        chave = s.get("titulo", "")[:40]
        if chave not in vistos:
            vistos.add(chave)
            s = dict(s, velocity="NOVO")
            resultado.append(s)

    return resultado[:top_n]


def run_sweep() -> dict:
    """
    Corre todos os sweepers. Devolve resumo com sinais fortes detectados.
    - Sinais fortes: velocity >= 2.0
    - Sinais novos (cold start): sem histórico — listados separadamente
    - Fontes com ≥3 falhas consecutivas: pausadas automaticamente por 24h
    """
    todos_sinais = []
    erros = []
    fontes_pausadas = []

    for key, nome, fn in SWEEPERS:
        if _should_skip_source(key):
            fontes_pausadas.append(nome)
            continue
        try:
            sinais = fn()
            if sinais is not None:
                todos_sinais.extend(sinais)
                _record_source_success(key)
        except Exception as e:
            erros.append(f"{nome}: {e}")
            _record_source_fail(key, str(e))

    # Guardar todos na queue
    queue = _load_queue()
    queue.extend(todos_sinais)
    _save_queue(queue)

    # Sinais com velocity real forte (≥ 2x)
    fortes = [s for s in todos_sinais if isinstance(s.get("velocity"), float) and s["velocity"] >= 2.0]
    fortes.sort(key=lambda x: x.get("velocity", 0), reverse=True)

    # Sinais novos (cold start — sem histórico)
    novos = [s for s in todos_sinais if s.get("velocity") == _COLD_START_VELOCITY]

    pausadas_detalhes = _get_source_health_summary()
    resumo = {
        "ts": datetime.now().isoformat(),
        "total_sinais": len(todos_sinais),
        "sinais_fortes": len(fortes),
        "sinais_novos": len(novos),
        "fontes_pausadas": fontes_pausadas,
        "fontes_pausadas_detalhes": {
            k: {"fails": v.get("consecutive_fails"), "ultimo_erro": v.get("last_error", "")}
            for k, v in pausadas_detalhes.items()
        },
        "top_sinais": fortes[:10],
        "top_novos": novos[:5],
        "erros": erros,
    }

    # Notificar CEO se há sinais muito fortes (velocity >= 3x)
    muito_fortes = [s for s in fortes if s.get("velocity", 0) >= 3.0]
    if muito_fortes:
        _notificar_scout(muito_fortes)

    return resumo


def _notificar_scout(sinais_criticos: list) -> None:
    """
    Acorda o Scout com Claude quando há sinais muito fortes (velocity ≥ 3x).
    Throttle: máximo 1x por 12 horas para evitar análises desnecessárias.
    """
    triggered_file = _TRIGGERED_FILE
    agora = datetime.now()
    triggered = {}
    if triggered_file.exists():
        try:
            triggered = json.loads(triggered_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    ultimo = triggered.get("ultimo_trigger")
    if ultimo:
        try:
            delta_h = (agora - datetime.fromisoformat(ultimo)).total_seconds() / 3600
            if delta_h < 12:
                return  # Já foi acionado há menos de 12h
        except Exception:
            pass

    # Registar trigger
    triggered["ultimo_trigger"] = agora.isoformat()
    triggered["sinais"] = [s["titulo"] for s in sinais_criticos[:5]]
    triggered_file.parent.mkdir(exist_ok=True)
    triggered_file.write_text(json.dumps(triggered, indent=2, ensure_ascii=False), encoding="utf-8")

    # Chamar Scout com contexto dos sinais fortes
    try:
        from scout_agent import missao_a_oportunidades_triggered
        tops = "\n".join(f"- [{s['fonte']}] {s['titulo']} (velocity {s['velocity']}x)"
                         for s in sinais_criticos[:5])
        threading.Thread(
            target=missao_a_oportunidades_triggered,
            args=(tops,),
            daemon=True,
        ).start()
    except Exception:
        pass


# ── Scheduler próprio do Scout ─────────────────────────────────────────────────

def iniciar_scheduler_scout() -> None:
    """
    Loop independente do Scout — não depende do CEO heartbeat.
    Corre sweep a cada 6 horas.
    """
    import time as _time

    def _loop():
        _time.sleep(60)  # esperar 1 min para o servidor arrancar
        while True:
            try:
                resumo = run_sweep()
                from pathlib import Path
                import logging
                _log = logging.getLogger("morgan")
                _log.info(
                    "Scout sweep: %d sinais, %d fortes, %d muito fortes",
                    resumo["total_sinais"],
                    resumo["sinais_fortes"],
                    len([s for s in resumo["top_sinais"] if s.get("velocity", 0) >= 3.0]),
                )
            except Exception as e:
                pass
            _time.sleep(6 * 3600)  # 6 horas

    t = threading.Thread(target=_loop, daemon=True, name="scout_sweep")
    t.start()


if __name__ == "__main__":
    print("A correr sweep manual...")
    resumo = run_sweep()
    print(f"Total sinais: {resumo['total_sinais']}")
    print(f"Sinais fortes (≥2x): {resumo['sinais_fortes']}")
    if resumo["top_sinais"]:
        print("\nTop sinais:")
        for s in resumo["top_sinais"][:5]:
            print(f"  [{s['fonte']}] {s['titulo']} — velocity {s.get('velocity', '?')}x")
    if resumo["erros"]:
        print(f"\nErros: {', '.join(resumo['erros'])}")
