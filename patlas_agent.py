"""
PAtlas — Agente autónomo da loja PlannerAtlas (Etsy)
Monitoriza, actua e cresce sem ser chamado. Reporta ao CEO quando relevante.
Inclui operações Etsy, marketing Pinterest/SEO e gestão de fase.
"""
import json
import os
import smtplib
import ssl
import threading
import time
from datetime import datetime, timedelta, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MEMORY_DIR = Path(__file__).parent / "memory"
PATLAS_STATE_FILE = MEMORY_DIR / "patlas_state.json"

from claude_guard import GuardedClient
client = GuardedClient("patlas")

from episodic_memory import registar_evento

# ── Thresholds ────────────────────────────────────────────────────────────────
ALERTA_SEM_VENDAS_DIAS = 14
ALERTA_CTR_MIN = 0.005
ALERTA_QUEDA_BASELINE = 0.40
ALERTA_REVIEW_MIN = 2.0
ALERTA_ROAS_MIN = 2.0

CONTENT_PILLARS = [
    "use_case",
    "before_after",
    "seasonal",
    "behind_scenes",
    "review_visual",
    "comparison",
]

SYSTEM_PROMPT = """És o PAtlas, o agente autónomo da loja PlannerAtlas no Etsy.

NEGÓCIO:
- Loja Etsy: planners digitais PDF/GoodNotes em PT/ES/DE/EN
- Objectivo: €10.000/mês de rendimento passivo para o Vasco Botelho da Costa
- Mercados prioritários: DE (maior), ES, PT/BR, EN

REGRA ANTI-PRÓLOGO: A primeira linha da tua resposta é sempre conteúdo útil.

GESTÃO DE FASES — critérios numéricos:
Validação (0-30d): KPI único = vendas orgânicas. Transição→MVP: ≥5 vendas + CTR>2% + ≥1 review.
MVP (30-90d): CR>2%, reviews. Transição→Lançamento: >30 vendas/mês + CR>2% + ≥10 reviews (4.5★+).
Lançamento: ROAS Etsy Ads, traffic. Transição→Crescimento: >100 vendas/mês + ROAS>2.0 + orgânico>60%.
Regressão: vendas caem >50% em 2 semanas → regredir uma fase.

SEO ETSY 2026:
- Keyword principal nos primeiros 40 chars do título (corte mobile — crítico)
- Título: 70-120 chars, linguagem natural (semantic search activo)
- 13 tags obrigatórias: frases longas ("birthday gift for sister"), nunca genéricas
- ChatGPT Shopping gera +20% tráfego referral → optimizar títulos para LLMs

PINTEREST 2026:
- Fresh pin = nova IMAGEM (não só novo título) para o mesmo URL
- Frequência: 3-5 fresh pins/dia consistente; qualidade > quantidade
- Timing: Sáb/Dom 20h-23h; Sex à noite; Seg-Sex 8h-11h
- Nunca repostar a mesma imagem — o algoritmo trata como spam
- Cada pin destaca um use case diferente do mesmo produto

AUTONOMIA:
- Podes pausar/activar listings — regista sempre
- NUNCA alteras preços sem aprovação do Vasco
- NUNCA apagas listings
- Circuit breaker Ads: ROAS<2.0 por 3 dias → propor pausa imediata

PT-PT sempre. Números concretos. A última decisão é sempre do Vasco."""


# ── Estado ────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if PATLAS_STATE_FILE.exists():
        return json.loads(PATLAS_STATE_FILE.read_text())
    estado = {
        "nome": "PlannerAtlas",
        "plataforma": "Etsy",
        "fase": "lançamento",
        "listings_activos": 0,
        "vendas_total": 0,
        "vendas_28d": [],
        "ctr_medio": 0.0,
        "conversion_rate": 0.0,
        "review_medio": 0.0,
        "receita_total": 0.0,
        "ultima_venda": "",
        "ultima_verificacao": "",
        "alertas_activos": [],
        "etsy_configurado": False,
        "metrics_history": [],
        "campanhas": [],
        "pins_history": [],
        "criado_em": datetime.now().isoformat(),
    }
    PATLAS_STATE_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False))
    return estado


def _save_state(state: dict):
    PATLAS_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ── Notificações ──────────────────────────────────────────────────────────────

def _notificar_ceo(titulo: str, corpo: str, urgente: bool = False):
    try:
        from episodic_memory import registar_evento
        prefixo = "🚨 URGENTE" if urgente else "🛍️ PAtlas"
        registar_evento("ceo", "patlas_alerta" if urgente else "patlas_update",
                        f"{prefixo} — {titulo}: {corpo}")
        registar_evento("operator", "patlas_update", f"{titulo}: {corpo}")
    except Exception:
        pass
    try:
        from ceo_events import publicar
        nivel = "critico" if urgente else "aviso"
        publicar("patlas", "alerta" if urgente else "update", f"{titulo}: {corpo}", nivel=nivel)
    except Exception:
        pass
    if urgente:
        try:
            from push_service import send_push
            send_push(title=f"Morgan — {titulo}", body=corpo[:160], url="/pwa/")
        except Exception:
            pass


# ── Métricas e anomalias ──────────────────────────────────────────────────────

def obter_metricas() -> dict:
    """Vai buscar métricas reais ao Etsy via etsy_service."""
    state = _load_state()
    try:
        from etsy_service import is_configured, resumo_loja, obter_vendas
        if not is_configured():
            state["etsy_configurado"] = False
            _save_state(state)
            return {"ok": False, "erro": "Etsy OAuth não configurado — ETSY_KEYSTRING em falta"}

        state["etsy_configurado"] = True
        resumo = resumo_loja()
        vendas_30d = obter_vendas(dias=30)

        state["listings_activos"] = resumo.get("listings_activos", state["listings_activos"])
        state["vendas_total"] = resumo.get("vendas_total", state["vendas_total"])
        state["receita_total"] = resumo.get("receita_total", state["receita_total"])
        state["ultima_verificacao"] = datetime.now().isoformat()

        if vendas_30d:
            state["ultima_venda"] = vendas_30d[0].get("data", "") if vendas_30d else state["ultima_venda"]
            state["vendas_28d"] = vendas_30d[:28]

        _save_state(state)
        return {"ok": True, "resumo": resumo, "vendas_30d": len(vendas_30d)}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def _calcular_baseline(historico: list[dict], metrica: str, janela_dias: int = 28) -> float | None:
    limite = datetime.now() - timedelta(days=janela_dias)
    valores = []
    for snapshot in historico:
        try:
            ts = datetime.fromisoformat(snapshot.get("timestamp", ""))
            if ts >= limite:
                v = snapshot.get(metrica)
                if v is not None and isinstance(v, (int, float)):
                    valores.append(float(v))
        except Exception:
            continue
    return sum(valores) / len(valores) if valores else None


def _snapshot_metricas(state: dict):
    historico = state.setdefault("metrics_history", [])
    snap = {"timestamp": datetime.now().isoformat()}
    snap.update({k: state.get(k) for k in ["vendas_total", "receita_total", "ctr_medio", "conversion_rate"]})
    historico.append(snap)
    state["metrics_history"] = historico[-365:]


def _avaliar_transicao_fase(state: dict) -> str | None:
    fase = state.get("fase", "lançamento")
    vendas_total = state.get("vendas_total", 0)
    ctr = state.get("ctr_medio", 0.0)
    cr = state.get("conversion_rate", 0.0)
    review = state.get("review_medio", 0.0)

    if fase == "validação":
        if vendas_total >= 5 and ctr > 0.02 and review >= 1:
            return "mvp"
    elif fase == "mvp":
        if vendas_total >= 30 and cr > 0.02 and review >= 4.5:
            return "lançamento"
    elif fase == "lançamento":
        if vendas_total >= 100:
            return "crescimento"
    return None


def verificar_anomalias() -> list[str]:
    state = _load_state()
    alertas = []
    agora = datetime.now()

    if not state.get("etsy_configurado"):
        alertas.append("Etsy OAuth não configurado — métricas reais indisponíveis")
        state["alertas_activos"] = alertas
        _save_state(state)
        return alertas

    # Sem vendas
    if state.get("ultima_venda"):
        ultima = datetime.fromisoformat(state["ultima_venda"])
        dias_sem_venda = (agora - ultima).days
        if dias_sem_venda >= ALERTA_SEM_VENDAS_DIAS:
            alertas.append(f"Sem vendas há {dias_sem_venda} dias — rever produto ou SEO")

    # CTR baixo
    ctr = state.get("ctr_medio", 0.0)
    if ctr > 0 and ctr < ALERTA_CTR_MIN:
        alertas.append(f"CTR médio {ctr:.1%} — abaixo de 0.5% (thumbnails ou títulos a falhar)")

    # Review baixo
    review = state.get("review_medio", 0.0)
    if review > 0 and review <= ALERTA_REVIEW_MIN:
        alertas.append(f"Review médio {review:.1f}★ — verificar qualidade do produto")

    # Queda vs. baseline rolling 28d
    historico = state.get("metrics_history", [])
    baseline_receita = _calcular_baseline(historico, "receita_total")
    receita_atual = state.get("receita_total", 0.0)
    if baseline_receita and baseline_receita > 0 and receita_atual is not None:
        variacao = (receita_atual - baseline_receita) / baseline_receita
        if variacao < -ALERTA_QUEDA_BASELINE:
            alertas.append(f"Receita caiu {abs(variacao):.0%} vs. baseline 28d — investigar")

    # Transição de fase
    nova_fase = _avaliar_transicao_fase(state)
    if nova_fase:
        alertas.append(f"Critérios para transição para fase '{nova_fase}' cumpridos — confirmar com Vasco")

    # Notificar CEO para alertas novos
    alertas_anteriores = set(state.get("alertas_activos", []))
    for alerta in alertas:
        if alerta not in alertas_anteriores:
            critico = any(k in alerta for k in ["Sem vendas", "Review", "Queda"])
            _notificar_ceo("PAtlas — anomalia", alerta, urgente=critico)

    state["alertas_activos"] = alertas
    _save_state(state)
    return alertas


# ── Operações Etsy ────────────────────────────────────────────────────────────

def etsy_pausar(listing_id: int) -> str:
    """Pausa um listing Etsy. Requer confirmação do Vasco antes de chamar."""
    try:
        from etsy_service import pausar_listing
        ok = pausar_listing(listing_id)
        return f"Listing {listing_id} pausado." if ok else f"Erro ao pausar listing {listing_id}."
    except Exception as e:
        return f"Erro: {e}"


def etsy_activar(listing_id: int) -> str:
    """Reactiva um listing Etsy pausado."""
    try:
        from etsy_service import activar_listing
        ok = activar_listing(listing_id)
        return f"Listing {listing_id} activado." if ok else f"Erro ao activar listing {listing_id}."
    except Exception as e:
        return f"Erro: {e}"


def etsy_actualizar_preco(listing_id: int, preco: float) -> str:
    """Actualiza preço de um listing. Requer confirmação do Vasco antes de chamar."""
    try:
        from etsy_service import actualizar_preco
        ok = actualizar_preco(listing_id, preco)
        return f"Preço do listing {listing_id} actualizado para €{preco:.2f}." if ok else "Erro ao actualizar preço."
    except Exception as e:
        return f"Erro: {e}"


def _ler_listings_etsy() -> str:
    try:
        from etsy_service import obter_listings
        listings = obter_listings()
        if not listings:
            return ""
        linhas = ["[Listings Etsy activos]"]
        for l in listings[:10]:
            lid = l.get("listing_id", "?")
            title = l.get("title", "?")[:45]
            preco = l.get("price", {}).get("amount", 0) / 100
            linhas.append(f"  [{lid}] {title}… €{preco:.2f}")
        if len(listings) > 10:
            linhas.append(f"  … +{len(listings)-10} mais")
        return "\n".join(linhas)
    except Exception:
        return ""


def enviar_mensagens_compradores() -> str:
    """Detecta novas ordens Etsy e envia mensagem personalizada na língua do produto."""
    try:
        from scripts.etsy_order_messages import run as run_messages
        sent = run_messages()
        if sent > 0:
            return f"✅ {sent} mensagem(ns) enviada(s) a compradores."
        return "Sem novas ordens para mensagear."
    except Exception as e:
        return f"Erro em enviar_mensagens_compradores: {e}"


def gerar_plano_semana() -> str:
    """Gera o plano de produtos PlannerAtlas para a semana — corre às segundas de manhã."""
    try:
        from tools import pesquisar
        tendencias = pesquisar("Etsy digital planner bestseller trending German Spanish 2026 GoodNotes", agente="patlas")
    except Exception:
        tendencias = "indisponível"

    prompt = f"""Hoje é {datetime.now().strftime('%A, %d de %B de %Y')}.
Loja PlannerAtlas no Etsy — planners digitais em PT/ES/DE/EN, objectivo 50+ produtos.

TENDÊNCIAS DETECTADAS:
{tendencias[:500] if tendencias else 'indisponível'}

Gera o plano para esta semana:
1. 3 novos produtos a criar (idioma, categoria, título Etsy)
2. Keywords SEO para cada produto (5 keywords no idioma do mercado)
3. Sugestão de imagem de capa
4. Pinterest: 1 pin por produto (descrição curta, 5 hashtags)

Formato directo. Português europeu."""

    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        plano = r.content[0].text if r.content else "Plano indisponível."
    except Exception as e:
        return f"Erro ao gerar plano: {e}"

    plano_file = MEMORY_DIR / "planneratlas_plano_semana.md"
    plano_file.write_text(
        f"# Plano PlannerAtlas — {datetime.now().strftime('%d/%m/%Y')}\n\n{plano}",
        encoding="utf-8"
    )
    return plano


# ── Marketing — Pinterest & SEO ───────────────────────────────────────────────

def _detectar_mercados_etsy() -> list[dict]:
    LINGUA_MAP = {
        "DE": {"codigo": "DE", "lingua": "Alemão", "keyword": "Planer PDF zum Ausdrucken", "timing": "Sa/So 20h-22h CET",
               "signals": ["druckbar", "planer", "vorlage", "ausdrucken", "monatsplaner", "wochenplaner", "tagesplaner"]},
        "EN": {"codigo": "EN", "lingua": "Inglês", "keyword": "Printable Planner PDF", "timing": "Fri/Sat 8-11pm EST",
               "signals": ["printable", "planner", "tracker", "monthly", "weekly", "budget", "meal", "habit", "daily"]},
        "ES": {"codigo": "ES", "lingua": "Espanhol", "keyword": "Planificador Imprimible PDF", "timing": "Sáb/Dom 20h-22h CET",
               "signals": ["imprimible", "planificador", "planeacion", "mensual", "semanal", "rastreador"]},
        "PT": {"codigo": "PT", "lingua": "Português", "keyword": "Planeador Imprimível PDF", "timing": "Sáb/Dom 20h-22h WET",
               "signals": ["imprimível", "planeador", "rastreador", "mensal", "semanal"]},
    }
    try:
        from etsy_service import obter_listings
        listings = obter_listings()
        titulos = " ".join(l.get("title", "").lower() for l in listings)
        mercados_detectados = []
        for cod, m in LINGUA_MAP.items():
            if any(s in titulos for s in m["signals"]):
                mercados_detectados.append(m)
        return mercados_detectados if mercados_detectados else list(LINGUA_MAP.values())
    except Exception:
        return list(LINGUA_MAP.values())


def pesquisar_pinterest(nicho: str) -> str:
    """Analisa tendências de um nicho no Pinterest."""
    try:
        from tools import pesquisar
        r1 = pesquisar(f"site:pinterest.com {nicho} planner digital download most saved 2026", agente="patlas")
        r2 = pesquisar(f"pinterest {nicho} trending pins viral digital product 2026", agente="patlas")
        return f"**Pinterest — {nicho}:**\n{r1}\n---\n{r2}"
    except Exception as e:
        return f"Erro Pinterest: {e}"


def analisar_etsy_nicho(nicho: str) -> str:
    """Analisa concorrência e oportunidades Etsy."""
    try:
        from tools import pesquisar
        return pesquisar(f"etsy {nicho} bestseller digital download 2026", agente="patlas")
    except Exception as e:
        return f"Erro: {e}"


def otimizar_listings_etsy(nicho: str = "planners digitais") -> str:
    """Pesquisa keywords de alto tráfego e gera títulos + tags optimizados."""
    try:
        from tools import pesquisar
        r1 = pesquisar(f"etsy SEO keywords {nicho} 2026 high traffic tags titles best sellers", agente="patlas")
        r2 = pesquisar(f"etsy {nicho} top listings titles tags Portuguese Spanish German", agente="patlas")
        dados_seo = f"{r1[:600]}\n---\n{r2[:600]}"
    except Exception as e:
        dados_seo = f"(pesquisa indisponível: {e})"

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=[{"type": "text", "text": "Especialistas em SEO para Etsy 2026. Geras títulos e tags de alta conversão.", "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"""Nicho: {nicho}
Dados SEO:
{dados_seo}

REGRAS SEO ETSY 2026:
- Keyword principal nos PRIMEIROS 40 CHARS do título
- Título: 70-120 chars, linguagem natural
- 13 tags obrigatórias: frases longas e específicas
- Optimizar para ChatGPT Shopping (linguagem conversacional)

Gera 3 propostas por mercado (DE, EN, ES, PT):
MERCADO: [DE/EN/ES/PT]
TÍTULO: ... (keyword [*] nos primeiros 40 chars)
TAGS: tag1, tag2, ... (13 tags)
GANCHO: ... (primeira frase da descrição)
CTR_ESPERADO: alto/médio/baixo

Sem emojis. DE em alemão, EN em inglês, ES em espanhol, PT em português."""}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"Erro ao gerar optimizações: {e}"


def plano_pinterest_semanal(nicho: str = "planners digitais") -> str:
    """Gera plano de pins Pinterest para a semana."""
    mercados = _detectar_mercados_etsy()
    resultados = []
    for m in mercados:
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                system=[{"type": "text", "text": f"Crias pins Pinterest de alta conversão para Etsy. Escreve SEMPRE em {m['lingua']}.", "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": f"""Negócio: PlannerAtlas — loja Etsy de {nicho}
Mercado: {m['codigo']} | Língua: {m['lingua']} | Keyword base: {m['keyword']}
Timing óptimo: {m['timing']}

Cria 3 pins para esta semana (use_case / before_after / seasonal):
- Título (max 100 chars, keyword nos primeiros 40)
- Descrição (max 200 chars + hashtags)
- Sugestão de imagem

Escreve TUDO em {m['lingua']}."""}]
            )
            resultados.append(f"\n## MERCADO {m['codigo']} ({m['lingua']})\n{resp.content[0].text}")
        except Exception as e:
            resultados.append(f"\n## MERCADO {m['codigo']}: Erro — {e}")
    return "\n---".join(resultados)


def gerar_conteudo_social(produto: str, idioma: str = "de") -> str:
    """Gera conteúdo Pinterest/Instagram/TikTok para um produto PlannerAtlas."""
    idiomas_map = {"de": "alemão", "es": "espanhol", "pt": "português europeu", "en": "inglês"}
    lang_name = idiomas_map.get(idioma, idioma)

    prompt = f"""Gera conteúdo de marketing para redes sociais:

Produto: {produto}
Idioma: {lang_name}
Loja: PlannerAtlas (planners digitais Etsy)

Cria:
1. Pinterest (2 descrições — curta ~50 palavras, longa ~150 palavras)
2. Instagram (caption, máximo 150 palavras + 20 hashtags em {lang_name})
3. TikTok (hook 3 segundos + texto ~100 palavras)

Tom: inspiracional, produtivo, minimalista. Público: 18-35 anos."""

    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text if r.content else "Conteúdo indisponível."
    except Exception as e:
        return f"Erro ao gerar conteúdo: {e}"


def gerar_variantes_pin(produto: str, listing_url: str = "", idioma: str = "todos", n: int = 3) -> str:
    """Gera N variantes de pin para o mesmo listing (fresh pin strategy)."""
    TODOS_MERCADOS = [
        {"codigo": "DE", "lingua": "alemão"},
        {"codigo": "EN", "lingua": "inglês"},
        {"codigo": "ES", "lingua": "espanhol"},
        {"codigo": "PT", "lingua": "português europeu"},
    ]
    idiomas_map = {"de": "alemão", "es": "espanhol", "pt": "português europeu", "en": "inglês"}

    if idioma == "todos":
        mercados = _detectar_mercados_etsy()
    else:
        lang_name = idiomas_map.get(idioma, idioma)
        mercados = [{"codigo": idioma.upper(), "lingua": lang_name}]

    resultados = []
    pillars_usados = CONTENT_PILLARS[:n]

    for m in mercados:
        prompt = f"""Produto Etsy: {produto}
URL: {listing_url or 'https://www.etsy.com/shop/PlannerAtlas'}
Mercado: {m['codigo']} | Idioma: {m['lingua']}

Cria {n} variantes de pin, cada uma com ângulo diferente:
{chr(10).join(f"{i+1}. Ângulo '{p}'" for i, p in enumerate(pillars_usados))}

Para cada variante:
- TÍTULO: máx 100 chars (keyword à frente, em {m['lingua']})
- DESCRIÇÃO: máx 150 chars + 5-8 hashtags em {m['lingua']}
- TIMING: melhor dia/hora
- IMAGEM: sugestão do visual

Escreve TUDO em {m['lingua']}."""

        try:
            r = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}]
            )
            resultado = r.content[0].text if r.content else "Variantes indisponíveis."
            resultados.append(f"\n## MERCADO {m['codigo']} ({m['lingua']})\n{resultado}")
        except Exception as e:
            resultados.append(f"\n## MERCADO {m['codigo']}: Erro — {e}")

    state = _load_state()
    pins_hist = state.setdefault("pins_history", [])
    pins_hist.append({
        "data": datetime.now().isoformat()[:16],
        "produto": produto,
        "mercados": [m["codigo"] for m in mercados],
        "variantes_geradas": n * len(mercados),
        "status": "gerado",
        "engagement": None,
    })
    state["pins_history"] = pins_hist[-500:]
    _save_state(state)
    return "\n---".join(resultados)


MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/mml5ugu7c1dygppxx1o4ydzwqibshufg"

# Mapeamento produto → board_id Pinterest (board IDs da conta @PlannerAtlas)
PINTEREST_BOARDS = {
    "weekly_planner":  {"en": "1112952195355456475", "de": "1112952195355460499", "es": "1112952195355460414", "pt": "1112952195355460545"},
    "monthly_planner": {"en": "1112952195355456816", "de": "1112952195355460520", "es": "1112952195355460419", "pt": "1112952195355460546"},
    "daily_planner":   {"en": "1112952195355456827", "de": "1112952195355460500", "es": "1112952195355460422", "pt": "1112952195355460547"},
    "meal_planner":    {"en": "1112952195355456853", "de": "1112952195355460505", "es": "1112952195355460428", "pt": "1112952195355460553"},
    "habit_tracker":   {"en": "1112952195355456833", "de": "1112952195355460503", "es": "1112952195355460424", "pt": "1112952195355460550"},
    "budget_tracker":  {"en": "1112952195355456843", "de": "1112952195355460504", "es": "1112952195355460427", "pt": "1112952195355460552"},
}

ETSY_LISTING_URLS = {
    "weekly_planner":  "https://www.etsy.com/shop/PlannerAtlas?ref=seller-platform-mcnav&search_query=weekly",
    "monthly_planner": "https://www.etsy.com/shop/PlannerAtlas?ref=seller-platform-mcnav&search_query=monthly",
    "daily_planner":   "https://www.etsy.com/shop/PlannerAtlas?ref=seller-platform-mcnav&search_query=daily",
    "meal_planner":    "https://www.etsy.com/shop/PlannerAtlas?ref=seller-platform-mcnav&search_query=meal",
    "habit_tracker":   "https://www.etsy.com/shop/PlannerAtlas?ref=seller-platform-mcnav&search_query=habit",
    "budget_tracker":  "https://www.etsy.com/shop/PlannerAtlas?ref=seller-platform-mcnav&search_query=budget",
}

PREVIEW_IMAGES = {
    "weekly_planner":  "https://d8j0ntlcm91z4.cloudfront.net/user_3Gth9k6jhmzNUof4cZtSy4XAW7p/hf_20260808_215232_3edb628a-b412-494a-b1df-7c8217e5da3b.png",
    "monthly_planner": "https://d8j0ntlcm91z4.cloudfront.net/user_3Gth9k6jhmzNUof4cZtSy4XAW7p/hf_20260808_215232_d77c3b5a-50fa-4766-8217-adbafba15c1a.png",
    "daily_planner":   "https://d8j0ntlcm91z4.cloudfront.net/user_3Gth9k6jhmzNUof4cZtSy4XAW7p/hf_20260808_215232_067de21e-5bbf-4212-be30-ce48e1a4acf1.png",
    "meal_planner":    "https://d8j0ntlcm91z4.cloudfront.net/user_3Gth9k6jhmzNUof4cZtSy4XAW7p/hf_20260808_215232_c643d363-40e5-47ee-a059-d1a418bfd14d.png",
    "habit_tracker":   "https://d8j0ntlcm91z4.cloudfront.net/user_3Gth9k6jhmzNUof4cZtSy4XAW7p/hf_20260808_215232_6dd8f68e-2930-4d31-9521-101c4df4d2b4.png",
    "budget_tracker":  "https://d8j0ntlcm91z4.cloudfront.net/user_3Gth9k6jhmzNUof4cZtSy4XAW7p/hf_20260808_215232_576e3128-3443-4d36-aa52-ac252b20c71a.png",
}


def publicar_pin_pinterest(produto: str, idioma: str = "en") -> dict:
    """Publica um pin no Pinterest via Make webhook. Retorna resultado."""
    import requests

    board = PINTEREST_BOARDS.get(produto, {}).get(idioma, "1112952195355456475")
    link = ETSY_LISTING_URLS.get(produto, "https://www.etsy.com/shop/PlannerAtlas")
    image_url = PREVIEW_IMAGES.get(produto, PREVIEW_IMAGES["weekly_planner"])

    # Gera título e descrição com Claude
    idiomas_map = {"en": "English", "de": "German", "es": "Spanish", "pt": "Portuguese (European)"}
    lingua = idiomas_map.get(idioma, "English")
    produto_nome = produto.replace("_", " ").title()

    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Write a Pinterest pin title (max 80 chars) and description (max 150 chars + 5 hashtags) for a digital {produto_nome} PDF download on Etsy. Language: {lingua}. Reply with exactly two lines:\nTITLE: your title here\nDESCRIPTION: your description here"}]
        )
        texto = r.content[0].text if r.content else ""
        titulo = produto_nome
        descricao = ""
        for linha in texto.strip().split("\n"):
            linha = linha.strip().lstrip("*#- ")
            if linha.upper().startswith("TITLE:"):
                titulo = linha.split(":", 1)[1].strip().strip("*").strip()
            elif linha.upper().startswith("DESCRIPTION:"):
                descricao = linha.split(":", 1)[1].strip().strip("*").strip()
        if not titulo:
            titulo = f"Digital {produto_nome} | Instant Download"
    except Exception:
        titulo = f"Digital {produto_nome} | Instant Download"
        descricao = f"Printable {produto_nome} PDF. Instant download on Etsy. #planner #digital #printable"

    payload = {
        "board_id": board,
        "title": titulo[:100],
        "description": descricao[:800],
        "link": link,
        "image_url": image_url,
    }

    try:
        resp = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=15)
        sucesso = resp.status_code == 200
    except Exception as e:
        return {"ok": False, "erro": str(e)}

    registar_evento("patlas", "pin_publicado",
                    f"Pin publicado: {produto} ({idioma}) — {'✅' if sucesso else '❌'}",
                    dados={"produto": produto, "idioma": idioma, "titulo": titulo})

    return {"ok": sucesso, "produto": produto, "idioma": idioma, "titulo": titulo}


def publicar_pins_idioma(idioma: str, n: int = 2) -> str:
    """Publica N pins para um idioma específico em rotação pelos produtos."""
    import random
    produtos = list(PINTEREST_BOARDS.keys())

    state = _load_state()
    historico = state.get("pins_publicados_hoje", [])
    hoje = date.today().isoformat()

    if state.get("pins_data") != hoje:
        state["pins_publicados_hoje"] = []
        state["pins_data"] = hoje
        historico = []

    combinacoes = [p for p in produtos if f"{p}_{idioma}" not in historico]
    if not combinacoes:
        # Todas publicadas hoje neste idioma — reset só para este idioma
        historico = [h for h in historico if not h.endswith(f"_{idioma}")]
        combinacoes = produtos[:]

    seleccao = random.sample(combinacoes, min(n, len(combinacoes)))
    resultados = []
    for produto in seleccao:
        res = publicar_pin_pinterest(produto, idioma)
        historico.append(f"{produto}_{idioma}")
        resultados.append(f"{'✅' if res['ok'] else '❌'} {produto} ({idioma})")

    state["pins_publicados_hoje"] = historico
    _save_state(state)
    return f"Pins {idioma.upper()}:\n" + "\n".join(resultados)


def publicar_pins_diarios() -> str:
    """Wrapper de compatibilidade — publica pins EN (chamado pelo ciclo legacy)."""
    return publicar_pins_idioma("en", n=2)


def analisar_top_performers(semanas: int = 4) -> str:
    """Loop fechado: analisa 20% de pins com mais engagement e sugere variações."""
    state = _load_state()
    pins_hist = state.get("pins_history", [])

    if not pins_hist:
        return "Sem histórico suficiente. Publica pins durante 4 semanas para activar o loop de aprendizagem."

    limite = datetime.now() - timedelta(weeks=semanas)
    pins_recentes = [
        p for p in pins_hist
        if p.get("engagement") is not None
        and datetime.fromisoformat(p["data"]) >= limite
    ]

    if not pins_recentes:
        return (
            f"Sem dados de engagement nos últimos {semanas} semanas. "
            "Actualiza o engagement em patlas_state.json para activar o loop."
        )

    pins_ordenados = sorted(pins_recentes, key=lambda p: p.get("engagement", 0), reverse=True)
    top_20pct = pins_ordenados[:max(1, len(pins_ordenados) // 5)]
    bottom_80pct = pins_ordenados[max(1, len(pins_ordenados) // 5):]

    top_resumo = "\n".join(
        f"- {p['produto']} ({', '.join(p.get('mercados', ['?']))}) — engagement: {p['engagement']} — data: {p['data']}"
        for p in top_20pct
    )
    bottom_resumo = f"{len(bottom_80pct)} pins com baixo engagement"

    prompt = f"""Análise de performance de pins Pinterest — últimas {semanas} semanas.

TOP PERFORMERS (20%):
{top_resumo}

BAIXO ENGAGEMENT: {bottom_resumo}

1. Padrões que distinguem os top performers?
2. Variações dos top performers a criar esta semana?
3. Produtos/idiomas a priorizar ou abandonar?
4. 3 acções concretas para a próxima semana.

Máximo 15 linhas. PT-PT. Números concretos."""

    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text if r.content else "Análise indisponível."
    except Exception as e:
        return f"Erro na análise: {e}"


def propor_accoes_correctivas() -> str:
    """Usa Claude para propor acções baseadas nos alertas actuais."""
    state = _load_state()
    alertas = state.get("alertas_activos", [])
    if not alertas:
        return "Sem alertas activos — nenhuma acção correctiva necessária."

    prompt = f"""PlannerAtlas — alertas detectados:
{chr(10).join(f'- {a}' for a in alertas)}

Estado: Listings: {state['listings_activos']} | Receita: €{state['receita_total']:.2f} | CTR: {state.get('ctr_medio', 0):.1%}

Propõe 1-3 acções correctivas concretas. Cada acção numa linha, começando com verbo."""

    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text
    except Exception as e:
        return f"Erro ao gerar acções: {e}"


# ── Relatórios ────────────────────────────────────────────────────────────────

def relatorio_para_ceo() -> str:
    state = _load_state()
    alertas = state.get("alertas_activos", [])

    ultima_venda = state.get("ultima_venda", "")
    if ultima_venda:
        dias = (datetime.now() - datetime.fromisoformat(ultima_venda)).days
        ultima_str = f"há {dias} dias" if dias > 0 else "hoje"
    else:
        ultima_str = "desconhecida"

    linhas = [
        "🛍️ PLANNERATLAS — Relatório",
        f"Fase: {state['fase']} | Listings: {state['listings_activos']}",
        f"Vendas total: {state['vendas_total']} | Receita: €{state['receita_total']:.2f}",
        f"CTR: {state.get('ctr_medio', 0):.1%} | CR: {state.get('conversion_rate', 0):.1%}",
        f"Última venda: {ultima_str}",
        f"Etsy OAuth: {'✅' if state.get('etsy_configurado') else '⏳ pendente'}",
    ]
    if alertas:
        linhas.append(f"⚠️ {len(alertas)} alerta(s): {' | '.join(alertas[:2])}")
    else:
        linhas.append("✅ Sem alertas")
    return "\n".join(linhas)


# ── Ciclo autónomo ────────────────────────────────────────────────────────────

def ciclo_diario() -> str:
    state = _load_state()
    obter_metricas()
    alertas = verificar_anomalias()
    _snapshot_metricas(state)
    _save_state(state)

    # Mensagens automáticas a compradores
    try:
        enviar_mensagens_compradores()
    except Exception:
        pass

    estado_str = relatorio_para_ceo()

    if alertas:
        _notificar_ceo(
            "PAtlas — resumo diário com alertas",
            f"{len(alertas)} alerta(s): {alertas[0]}",
            urgente=False
        )

    try:
        from runtime_state import publicar as rs_publicar
        rs_publicar("patlas", {
            "status": f"{'⚠️ alertas' if alertas else '✅ normal'}",
            "resumo": f"Vendas: {state['vendas_total']} | Receita: €{state['receita_total']:.2f} | Alertas: {len(alertas)}",
            "listings": state.get("listings_activos", 0),
            "receita": state.get("receita_total", 0),
            "alertas": alertas,
            "etsy_oauth": state.get("etsy_configurado", False),
        })
    except Exception:
        pass

    # Plano semanal às segundas
    if datetime.now().weekday() == 0:
        try:
            gerar_plano_semana()
        except Exception:
            pass

    # Publicar pins diários no Pinterest via Make
    try:
        pins_resultado = publicar_pins_diarios()
        estado_str += f"\n\n📌 Pinterest: {pins_resultado}"
    except Exception as e:
        pass

    try:
        state = _load_state()
        registar_evento("patlas", "ciclo_diario",
                        f"Fase: {state['fase']} | Listings: {state['listings_activos']} | "
                        f"Vendas: {state['vendas_total']} | Receita: €{state['receita_total']:.2f} | "
                        f"Alertas: {len(alertas)}",
                        dados={"alertas": alertas[:3]} if alertas else None)
    except Exception:
        pass

    return estado_str


def get_resumo_financeiro() -> str:
    """Resumo financeiro compacto para o CFO — receita, vendas, estado."""
    state = _load_state()
    receita = state.get("receita_total", 0.0)
    vendas = state.get("vendas_total", 0)
    listings = state.get("listings_activos", 0)
    alertas = state.get("alertas_activos", [])
    alerta_str = f" | ⚠ {len(alertas)} alerta(s)" if alertas else ""
    return f"Etsy/PlannerAtlas — Receita: €{receita:.2f} | Vendas: {vendas} | Listings: {listings}{alerta_str}"


def iniciar_scheduler_patlas():
    """Arranca o loop autónomo diário do PAtlas em daemon thread."""
    def _loop():
        # Esperar 2min após startup para o servidor estabilizar
        time.sleep(120)
        while True:
            try:
                ciclo_diario()
            except Exception as e:
                print(f"[patlas] ciclo_diario erro: {e}", flush=True)
            time.sleep(24 * 3600)

    t = threading.Thread(target=_loop, daemon=True, name="patlas-scheduler")
    t.start()


# ── Interface conversacional ──────────────────────────────────────────────────

TOOLS = [
    {"name": "obter_metricas", "description": "Vai buscar métricas reais da loja ao Etsy.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "verificar_anomalias", "description": "Detecta anomalias e alertas activos.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "relatorio_para_ceo", "description": "Gera relatório completo do estado da loja.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "propor_accoes_correctivas", "description": "Propõe acções correctivas baseadas nos alertas actuais.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "pesquisar_pinterest", "description": "Analisa tendências de um nicho no Pinterest.", "input_schema": {"type": "object", "properties": {"nicho": {"type": "string"}}, "required": ["nicho"]}},
    {"name": "analisar_etsy_nicho", "description": "Analisa concorrência e oportunidades Etsy.", "input_schema": {"type": "object", "properties": {"nicho": {"type": "string"}}, "required": ["nicho"]}},
    {"name": "otimizar_listings_etsy", "description": "Gera títulos + tags SEO optimizados.", "input_schema": {"type": "object", "properties": {"nicho": {"type": "string"}}}},
    {"name": "plano_pinterest_semanal", "description": "Gera plano de pins Pinterest para a semana.", "input_schema": {"type": "object", "properties": {"nicho": {"type": "string"}}}},
    {"name": "gerar_conteudo_social", "description": "Gera conteúdo Pinterest/Instagram/TikTok para um produto.", "input_schema": {"type": "object", "properties": {"produto": {"type": "string"}, "idioma": {"type": "string", "default": "de"}}, "required": ["produto"]}},
    {"name": "gerar_variantes_pin", "description": "Gera variantes de pin para o mesmo listing (fresh pin strategy).", "input_schema": {"type": "object", "properties": {"produto": {"type": "string"}, "listing_url": {"type": "string"}, "idioma": {"type": "string", "default": "todos"}, "n": {"type": "integer", "default": 3}}, "required": ["produto"]}},
    {"name": "analisar_top_performers", "description": "Analisa os 20% de pins com mais engagement e sugere variações.", "input_schema": {"type": "object", "properties": {"semanas": {"type": "integer", "default": 4}}}},
    {"name": "etsy_pausar", "description": "Pausa um listing Etsy (CTR <0.3% por 7 dias). Requer confirmação do Vasco.", "input_schema": {"type": "object", "properties": {"listing_id": {"type": "integer"}}, "required": ["listing_id"]}},
    {"name": "etsy_activar", "description": "Reactiva um listing pausado.", "input_schema": {"type": "object", "properties": {"listing_id": {"type": "integer"}}, "required": ["listing_id"]}},
    {"name": "gerar_plano_semana", "description": "Gera o plano de produtos PlannerAtlas para a semana.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "enviar_mensagens_compradores", "description": "Envia mensagens personalizadas a novos compradores Etsy.", "input_schema": {"type": "object", "properties": {}}},
]

TOOL_MAP = {
    "obter_metricas": lambda a: str(obter_metricas()),
    "verificar_anomalias": lambda a: str(verificar_anomalias()),
    "relatorio_para_ceo": lambda a: relatorio_para_ceo(),
    "propor_accoes_correctivas": lambda a: propor_accoes_correctivas(),
    "pesquisar_pinterest": lambda a: pesquisar_pinterest(**a),
    "analisar_etsy_nicho": lambda a: analisar_etsy_nicho(**a),
    "otimizar_listings_etsy": lambda a: otimizar_listings_etsy(**a),
    "plano_pinterest_semanal": lambda a: plano_pinterest_semanal(**a),
    "gerar_conteudo_social": lambda a: gerar_conteudo_social(**a),
    "gerar_variantes_pin": lambda a: gerar_variantes_pin(**a),
    "analisar_top_performers": lambda a: analisar_top_performers(**a),
    "etsy_pausar": lambda a: etsy_pausar(**a),
    "etsy_activar": lambda a: etsy_activar(**a),
    "gerar_plano_semana": lambda a: gerar_plano_semana(),
    "enviar_mensagens_compradores": lambda a: enviar_mensagens_compradores(),
}


def get_patlas_reply(user_text: str) -> str:
    state = _load_state()
    context = (
        f"Estado actual: Fase={state['fase']} | Listings={state['listings_activos']} | "
        f"Receita=€{state['receita_total']:.2f} | Alertas={len(state.get('alertas_activos', []))}"
    )

    mem_semantica = ""
    try:
        from episodic_memory import get_contexto_agente
        mem_semantica = get_contexto_agente("patlas", user_text or "Etsy PlannerAtlas marketing Pinterest vendas")
    except Exception:
        pass
    if mem_semantica:
        context += f"\n\n[Memórias relevantes]\n{mem_semantica}"

    msgs = [{"role": "user", "content": user_text}]
    for _ in range(5):
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=[{"type": "text", "text": SYSTEM_PROMPT + "\n\n" + context, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=msgs,
        )
        if r.stop_reason == "end_turn":
            reply = next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")
            try:
                from episodic_memory import registar_evento
                registar_evento("patlas", "conversa", f"Q: {user_text[:100]} | R: {reply[:200]}")
            except Exception:
                pass
            return reply
        if r.stop_reason != "tool_use":
            break
        tool_results = []
        for block in r.content:
            if block.type == "tool_use":
                fn = TOOL_MAP.get(block.name)
                result = fn(block.input) if fn else f"Ferramenta desconhecida: {block.name}"
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        msgs.append({"role": "assistant", "content": r.content})
        msgs.append({"role": "user", "content": tool_results})

    return next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")


if __name__ == "__main__":
    print(relatorio_para_ceo())
    print()
    anomalias = verificar_anomalias()
    if anomalias:
        print("Anomalias:", anomalias)
        print()
        print(propor_accoes_correctivas())
