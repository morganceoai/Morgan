"""
Morgan Marketeer — Agente de outreach e crescimento do império BCVertex.
Identifica leads, redige mensagens personalizadas, monitoriza canais de aquisição.
Reporta ao Morgan CEO. A última decisão é sempre do Vasco.
"""
import os
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv
load_dotenv()

MEMORY_DIR = Path(__file__).parent / "memory"
MARKETEER_FILE = MEMORY_DIR / "marketeer_state.json"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """És o Morgan Marketeer, o agente de marketing e crescimento do império BCVertex.

PERFIL DO VASCO:
Treinador de futebol no Moreirense FC. Objectivo: €10.000/mês de rendimento passivo via BCVertex.
Tempo limitado — quer acções concretas, não teorias. Mercados prioritários: DE, ES, PT/BR.

REGRA ANTI-PRÓLOGO: A primeira linha da tua resposta é sempre conteúdo útil.
Nunca começar com "Claro!", "Com certeza", "Olá", "Bom dia" ou qualquer saudação/confirmação.

MODOS DE RESPOSTA:
- Briefing (default): 3-5 bullets, acções concretas, máximo 10 linhas.
- Análise profunda: só quando o Vasco pede explicitamente ("analisa", "explica", "detalha").

NEGÓCIOS A MARKETEERS (apenas estes):
- PlannerAtlas (Etsy): planners digitais PT/ES/DE — produtividade, bullet journal, organização
  → Canais: Pinterest, Etsy SEO, Instagram, TikTok
- Novos negócios aprovados pelo Scout quando introduzidos pelo CEO

NÃO é da tua responsabilidade: trading bot, futebol, infra técnica.

SEO ETSY 2026 — REGRAS OBRIGATÓRIAS:
- Keyword principal nos primeiros 40 chars do título (corte mobile — crítico)
- Título: 70-120 chars total com keywords naturais (não stuffing)
- 13 tags obrigatórias: frases longas que as pessoas escrevem ("birthday gift for sister"), nunca genéricas ("gift")
- Semantic search activo desde 2025: optimizar para linguagem natural, não só match exacto
- ChatGPT Shopping gera +20% de tráfego referral para Etsy — optimizar títulos para LLMs
- Métricas que o algoritmo Etsy penaliza/premia: CTR, add-to-cart rate, dwell time, favorites

PINTEREST 2026 — REGRAS OBRIGATÓRIAS:
- Fresh pin = nova IMAGEM (não só novo título) para o mesmo URL — criar 5 variantes por listing
- Frequência: 3-5 fresh pins/dia de forma consistente; qualidade > quantidade
- Engagement window: primeiras 48h após publicação determinam distribuição — publicar no melhor timing
- Timing óptimo: Sáb/Dom 20h-23h; Sex à noite; Seg-Sex 8h-11h (segunda melhor janela)
- Nunca repostar a mesma imagem — o algoritmo trata como spam
- Cada pin deve destacar um use case diferente do mesmo produto

CONTENT PILLARS (usar rotação semanal — evita drift de IA):
1. Use case demonstração (como se usa o planner)
2. Before/After (antes/depois de usar o template)
3. Seasonal/trending (ex: "Schulplaner September", "Agenda Septiembre")
4. Behind the scenes / processo de criação
5. Review visual (screenshot de avaliação + produto)
6. Comparação (porque é melhor que alternativas)

LOOP FECHADO DE APRENDIZAGEM:
- Analisar os 20% de pins/listings que geram 80% dos cliques
- Gerar variações dos formatos vencedores
- Medir engagement window (48h) antes de decidir amplificar ou descartar

OUTREACH:
- Máximo 50 emails/dia — proteger reputação do domínio
- Personalização obrigatória: referenciar algo específico do lead (artigo publicado, produto que vende)
- Intent signals: contactar quando lead publicou algo recente sobre o nicho
- NUNCA enviar sem confirmação explícita do Vasco

CONFIANÇA POR TIPO DE DECISÃO:
- Propostas SEO/keywords: sempre, com dados de pesquisa
- Novo nicho: só com evidência de procura (Etsy search volume ou Tavily)
- Outreach: NUNCA sem "sim" explícito do Vasco
- Mudança de estratégia Pinterest: só após 4 semanas de dados

REGRAS:
- PT-PT sempre
- Números concretos — nunca "pode resultar bem"
- Outreach curto, personalizado, com valor real — nunca spam
- A última decisão é sempre do Vasco
"""

# Content pillars rotação
CONTENT_PILLARS = [
    "use_case",       # demonstração de uso
    "before_after",   # transformação
    "seasonal",       # sazonal/trending
    "behind_scenes",  # processo
    "review_visual",  # prova social
    "comparison",     # diferenciação
]


# ── Estado persistente ────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        return json.loads(MARKETEER_FILE.read_text())
    except Exception:
        return {
            "campanhas": [],
            "leads": [],
            "metricas": {},
            "ultimo_relatorio": "",
        }

def _save_state(state: dict):
    MARKETEER_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARKETEER_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── Ferramentas do Marketeer ──────────────────────────────────────────────────

def pesquisar_leads(nicho: str, mercado: str = "PT") -> str:
    """Pesquisa leads via cascade (Exa→Tavily→Perplexity→DDG)."""
    try:
        from tools import pesquisar
        query = f"{nicho} procura comprar {mercado} 2026 fórum reddit"
        return pesquisar(query, agente="marketeer")
    except Exception as e:
        return f"Erro na pesquisa: {e}"


def analisar_etsy_nicho(nicho: str) -> str:
    """Analisa concorrência e oportunidades Etsy via cascade de pesquisa."""
    try:
        from tools import pesquisar
        return pesquisar(f"etsy {nicho} bestseller digital download 2026", agente="marketeer")
    except Exception as e:
        return f"Erro: {e}"


def redigir_mensagem_outreach(contexto: str, destinatario: str, produto: str) -> str:
    """Redige uma mensagem de outreach personalizada com Claude."""
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system="Redige mensagens de outreach curtas (max 80 palavras), personalizadas, em PT-PT. Tom: profissional mas humano. Nunca uses saudações genéricas.",
            messages=[{"role": "user", "content": f"Contexto do lead: {contexto}\nDestinatário: {destinatario}\nProduto/serviço a oferecer: {produto}\n\nRedige a mensagem:"}]
        )
        return r.content[0].text
    except Exception as e:
        return f"Erro ao redigir: {e}"


def pesquisar_pinterest(nicho: str) -> str:
    """Analisa tendências de um nicho no Pinterest via cascade de pesquisa."""
    try:
        from tools import pesquisar
        r1 = pesquisar(f"site:pinterest.com {nicho} planner digital download most saved 2026", agente="marketeer")
        r2 = pesquisar(f"pinterest {nicho} trending pins viral digital product 2026", agente="marketeer")
        return f"**Pinterest — {nicho}:**\n{r1}\n---\n{r2}"
    except Exception as e:
        return f"Erro Pinterest: {e}"


# Limite diário de emails de outreach (GDPR / anti-spam)
_OUTREACH_CAP = 50

def _outreach_hoje() -> int:
    """Retorna quantos emails de outreach já foram enviados hoje."""
    state = _load_state()
    hoje = str(date.today())
    return state.get("outreach_diario", {}).get(hoje, 0)

def _registar_outreach_enviado():
    state = _load_state()
    hoje = str(date.today())
    d = state.setdefault("outreach_diario", {})
    d[hoje] = d.get(hoje, 0) + 1
    _save_state(state)


def enviar_outreach_email(destinatario_email: str, assunto: str, corpo: str, nome_destinatario: str = "") -> str:
    """
    Envia email de outreach via PurelyMail SMTP.
    Usa MORGAN_EMAIL e MORGAN_EMAIL_PASS do .env.
    Limite diário: 50 emails.
    """
    enviados = _outreach_hoje()
    if enviados >= _OUTREACH_CAP:
        return f"Limite diário de {_OUTREACH_CAP} emails atingido. Retoma amanhã."

    smtp_user = os.getenv("PLANNERATLAS_EMAIL", os.getenv("MORGAN_EMAIL", ""))
    smtp_pass = os.getenv("PLANNERATLAS_EMAIL_PASS", os.getenv("MORGAN_EMAIL_PASS", ""))
    if not smtp_user or not smtp_pass:
        return "Variáveis MORGAN_EMAIL / MORGAN_EMAIL_PASS não configuradas no .env."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = smtp_user
        msg["To"] = f"{nome_destinatario} <{destinatario_email}>" if nome_destinatario else destinatario_email
        msg.attach(MIMEText(corpo, "plain", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP("smtp.purelymail.com", 587) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, destinatario_email, msg.as_string())

        _registar_outreach_enviado()
        enviados_agora = _outreach_hoje()
        return f"Email enviado para {destinatario_email}. Total hoje: {enviados_agora}/{_OUTREACH_CAP}."
    except smtplib.SMTPAuthenticationError:
        return "Erro de autenticação PurelyMail. Verifica MORGAN_EMAIL_PASS no .env."
    except Exception as e:
        return f"Erro ao enviar email: {e}"


def otimizar_listings_etsy(nicho: str = "planners digitais") -> str:
    """
    Pesquisa keywords de alto tráfego Etsy e gera títulos + tags optimizados.
    Proposta para aprovação — não publica directamente.
    """
    try:
        from tools import pesquisar
        r1 = pesquisar(f"etsy SEO keywords {nicho} 2026 high traffic tags titles best sellers", agente="marketeer")
        r2 = pesquisar(f"etsy {nicho} top listings titles tags Portuguese Spanish German", agente="marketeer")
        dados_seo = f"{r1[:600]}\n---\n{r2[:600]}"
    except Exception as e:
        dados_seo = f"(pesquisa indisponível: {e})"

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system="És o Marketeer do Morgan. Especializas-te em SEO para Etsy 2026. Geras títulos e tags de alta conversão.",
            messages=[{"role": "user", "content": f"""Nicho: {nicho}
Dados de pesquisa SEO:
{dados_seo}

REGRAS SEO ETSY 2026 OBRIGATÓRIAS:
- Keyword principal nos PRIMEIROS 40 CHARS do título (corte mobile)
- Título: 70-120 chars, linguagem natural (semantic search activo)
- 13 tags obrigatórias: frases longas e específicas ("weekly planner for students"), nunca termos genéricos
- Optimizar para ser encontrado via ChatGPT Shopping (linguagem conversacional)
- CTR e add-to-cart são sinais directos no algoritmo — título e foto determinam CTR

Gera 3 propostas por mercado (DE, EN, ES, PT) — OBRIGATÓRIO cobrir os 4:
MERCADO: [DE/EN/ES/PT]
TÍTULO: ... (keyword principal nos primeiros 40 chars assinalada com [*])
TAGS: tag1, tag2, ... (13 tags obrigatórias)
GANCHO: ... (primeira frase da descrição — 1 linha)
CTR_ESPERADO: alto/médio/baixo (justifica em 5 palavras)

Sem emojis. Linguagem nativa de cada mercado. DE em alemão, EN em inglês, ES em espanhol, PT em português."""}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"Erro ao gerar optimizações: {e}"


def _detectar_mercados_etsy() -> list[dict]:
    """Lê os listings activos da Etsy e detecta os mercados/línguas presentes."""
    LINGUA_MAP = {
        "DE": {"codigo": "DE", "lingua": "Alemão", "keyword": "Planer PDF zum Ausdrucken", "timing": "Sa/So 20h-22h CET",
               "signals": ["druckbar", "planer", "vorlage", "ausdrucken", "monatsplaner", "wochenplaner", "tagesplaner", "mahlzeiten", "haushalts"]},
        "EN": {"codigo": "EN", "lingua": "Inglês", "keyword": "Printable Planner PDF", "timing": "Fri/Sat 8-11pm EST",
               "signals": ["printable", "planner", "tracker", "monthly", "weekly", "budget", "meal", "habit", "daily"]},
        "ES": {"codigo": "ES", "lingua": "Espanhol", "keyword": "Planificador Imprimible PDF", "timing": "Sáb/Dom 20h-22h CET",
               "signals": ["imprimible", "planificador", "planeacion", "mensual", "semanal", "rastreador", "comidas", "control de gastos"]},
        "PT": {"codigo": "PT", "lingua": "Português", "keyword": "Planeador Imprimível PDF", "timing": "Sáb/Dom 20h-22h WET",
               "signals": ["imprimível", "planeador", "rastreador", "mensal", "semanal", "refeições", "despesas", "hábitos"]},
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
        # fallback: assumir EN se Etsy não disponível
        return [LINGUA_MAP["EN"]]


def plano_pinterest_semanal(negocio: str = "PlannerAtlas", nicho: str = "planners digitais") -> str:
    """Gera plano de pins Pinterest para a semana — detecta mercados a partir dos listings Etsy activos."""
    MERCADOS = _detectar_mercados_etsy()
    resultados = []
    for m in MERCADOS:
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                system=f"Crias pins Pinterest de alta conversão para lojas Etsy. Escreve SEMPRE em {m['lingua']}. Foco em descoberta orgânica.",
                messages=[{"role": "user", "content": f"""Negócio: {negocio} — loja Etsy de {nicho}
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


def analisar_instagram_referencia(conta_referencia: str = "pepteam", conta_vasco: str = "vascobotelhodacosta") -> str:
    """
    Analisa uma conta Instagram de referência (ex: @pepteam de Pep Guardiola)
    e produz um plano de crescimento para a conta do Vasco como treinador.
    Usa pesquisa web como proxy (Instagram não tem API pública sem aprovação).
    """
    from tools import pesquisar

    resultados = []
    for q in [
        f"instagram @{conta_referencia} estratégia conteúdo futebol treinador",
        f"instagram coach football content strategy growth 2026",
        f"treinador futebol instagram crescimento conta pessoal dicas 2026",
    ]:
        try:
            resultados.append(pesquisar(q, agente="marketeer")[:500])
        except Exception:
            pass

    pesquisa = "\n---\n".join(resultados) if resultados else "Pesquisa indisponível."

    hoje = date.today().strftime("%d/%m/%Y")

    prompt = f"""Analisa a estratégia de Instagram do @{conta_referencia} (conta de Pep Guardiola) como referência.
Com base nos dados de pesquisa, define um plano de crescimento para @{conta_vasco} (treinador de futebol profissional no Moreirense FC, Portugal).

Contexto do Vasco:
- Treinador no Moreirense FC (Liga Portugal 2)
- Especialidade: análise táctica, coaching, desenvolvimento de jogadores
- Objectivo: construir autoridade como treinador PT e eventualmente monetizar (cursos, consultoria)
- Tem o Morgan (IA) para criar e agendar conteúdo automaticamente

Dados de pesquisa:
{pesquisa[:1500]}

Plano de crescimento — estrutura:
1. O que @{conta_referencia} faz bem (3 pontos max)
2. Tipos de conteúdo para @{conta_vasco} (com exemplos concretos)
3. Frequência e timing ideal (dias/horas)
4. Hashtag strategy
5. Primeiras 4 semanas — calendário concreto semana a semana
6. KPIs a monitorizar (seguidores, reach, engagement rate)
7. O que o Morgan executa automaticamente

Máximo 400 palavras. Português europeu. Directo e accionável."""

    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system="És o Morgan Marketeer. Analisas estratégias de crescimento em redes sociais com foco em conversão e autoridade.",
            messages=[{"role": "user", "content": prompt}],
        )
        plano = r.content[0].text.strip()
    except Exception as e:
        plano = f"(erro ao gerar plano: {e})"

    # Guardar plano em memória
    output_file = MEMORY_DIR / f"instagram_plano_{date.today().strftime('%Y%m%d')}.txt"
    output_file.write_text(
        f"Análise Instagram — @{conta_referencia} → @{conta_vasco} ({hoje})\n{'='*60}\n{plano}",
        encoding="utf-8"
    )

    return plano


def gerar_conteudo_social_planneratlas(produto: str, idioma: str = "de") -> str:
    """Gera conteúdo Pinterest/Instagram/TikTok para um produto PlannerAtlas."""
    idiomas_map = {"de": "alemão", "es": "espanhol", "pt": "português europeu"}
    lang_name = idiomas_map.get(idioma, idioma)

    prompt = f"""Gera conteúdo de marketing para redes sociais para o seguinte produto Etsy:

Produto: {produto}
Idioma de saída: {lang_name}
Loja: PlannerAtlas (planners digitais GoodNotes/Notability no Etsy)

Cria:
1. Pinterest (2 descrições de pin — curta ~50 palavras, longa ~150 palavras)
2. Instagram (caption, máximo 150 palavras + 20 hashtags em {lang_name})
3. TikTok (hook inicial 3 segundos + texto do vídeo ~100 palavras)

Tom: inspiracional, produtivo, minimalista. Público: estudantes e profissionais 18-35 anos."""

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
    """
    Gera variantes de pin para o mesmo listing — por defeito cobre TODOS os 4 mercados (DE, EN, ES, PT).
    idioma='todos' gera para os 4 mercados; ou passa 'de'/'en'/'es'/'pt' para um mercado específico.
    """
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
URL do listing: {listing_url or 'https://www.etsy.com/shop/PlannerAtlas'}
Mercado: {m['codigo']} | Idioma: {m['lingua']}

Cria {n} variantes de pin Pinterest, cada uma com um ângulo diferente:
{chr(10).join(f"{i+1}. Ângulo '{p}'" for i, p in enumerate(pillars_usados))}

Para cada variante:
- TÍTULO: máx 100 chars (keyword principal à frente, em {m['lingua']})
- DESCRIÇÃO: máx 150 chars + 5-8 hashtags em {m['lingua']}
- TIMING: melhor dia/hora para publicar
- IMAGEM: sugestão do visual

Escreve TUDO em {m['lingua']}. Fresh pins = imagens diferentes para o mesmo URL."""

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

    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        resultado = r.content[0].text if r.content else "Variantes indisponíveis."
    except Exception as e:
        return f"Erro ao gerar variantes: {e}"

    # Guardar no histórico de pins para loop de aprendizagem
    state = _load_state()
    pins_hist = state.setdefault("pins_history", [])
    pins_hist.append({
        "data": datetime.now().isoformat()[:16],
        "produto": produto,
        "mercados": [m["codigo"] for m in mercados],
        "variantes_geradas": n * len(mercados),
        "status": "gerado",  # → publicado → medido
        "engagement": None,  # preenchido após engagement window 48h
    })
    state["pins_history"] = pins_hist[-500:]
    _save_state(state)
    return "\n---".join(resultados)

    return resultado


def analisar_top_performers(semanas: int = 4) -> str:
    """
    Loop fechado de aprendizagem: analisa histórico de pins/listings,
    identifica os 20% que geram mais engagement, e sugere variações dos vencedores.
    """
    state = _load_state()
    pins_hist = state.get("pins_history", [])
    campanhas = state.get("campanhas", [])

    if not pins_hist and not campanhas:
        return "Sem histórico suficiente para análise. Publica pins durante 4 semanas para activar o loop de aprendizagem."

    from datetime import timedelta
    limite = datetime.now() - timedelta(weeks=semanas)

    pins_recentes = [
        p for p in pins_hist
        if p.get("engagement") is not None
        and datetime.fromisoformat(p["data"]) >= limite
    ]

    if not pins_recentes:
        return (
            f"Sem dados de engagement nos últimos {semanas} semanas. "
            "Quando tiveres pins publicados, actualiza o engagement em marketeer_state.json "
            "para activar o loop de aprendizagem."
        )

    pins_ordenados = sorted(pins_recentes, key=lambda p: p.get("engagement", 0), reverse=True)
    top_20pct = pins_ordenados[:max(1, len(pins_ordenados) // 5)]
    bottom_80pct = pins_ordenados[max(1, len(pins_ordenados) // 5):]

    top_resumo = "\n".join(
        f"- {p['produto']} ({p['idioma']}) — engagement: {p['engagement']} — data: {p['data']}"
        for p in top_20pct
    )
    bottom_resumo = f"{len(bottom_80pct)} pins com baixo engagement"

    prompt = f"""Análise de performance de pins Pinterest — últimas {semanas} semanas.

TOP PERFORMERS (20%):
{top_resumo}

BAIXO ENGAGEMENT: {bottom_resumo}

Com base nestes dados:
1. Que padrões distinguem os top performers? (produto, idioma, timing, tipo de conteúdo)
2. Que variações dos top performers devo criar esta semana?
3. Que produtos/idiomas devo priorizar ou abandonar?
4. 3 acções concretas para a próxima semana.

Máximo 15 linhas. PT-PT. Números concretos."""

    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text if r.content else "Análise indisponível."
    except Exception as e:
        return f"Erro na análise: {e}"


_MARKETEER_OPS = Path(__file__).parent / "memory" / "marketeer_ops.json"

def escrever_recomendacoes_operator() -> str:
    """Analisa a loja Etsy e escreve recomendações para o Operator agir."""
    try:
        from etsy_service import resumo_loja
        resumo = resumo_loja()
    except Exception as e:
        return f"Erro ao obter dados Etsy: {e}"

    listings = resumo.get("listings", [])
    vendas = resumo.get("vendas_periodo", 0)
    receita = resumo.get("receita_estimada", 0.0)

    # Listings sem vendas recentes são candidatos a pausa
    sem_vendas = [l for l in listings if l.get("quantity", 0) > 0]
    recomendacoes = []

    prompt = f"""És o Morgan Marketeer. Analisa estes dados da loja Etsy PlannerAtlas e gera recomendações de gestão para o Operator:

Listings activos: {len(listings)}
Vendas últimos 30 dias: {vendas}
Receita estimada: €{receita:.2f}

Listings: {json.dumps([{"id": l.get("listing_id"), "titulo": l.get("title","")[:50], "views": l.get("views",0), "quantity": l.get("quantity",0)} for l in listings[:20]], ensure_ascii=False)}

Gera recomendações no formato JSON:
{{
  "pausar": [lista de listing_ids a pausar por baixo desempenho],
  "activar": [lista de listing_ids a reactivar],
  "investigar": [listing_ids com dados anómalos],
  "resumo": "1-2 linhas com a situação geral da loja",
  "prioridade": "alta/media/baixa"
}}

Apenas responde com o JSON, sem mais texto."""

    try:
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        texto = r.content[0].text.strip() if r.content else "{}"
        # Extrair JSON se vier com markdown
        if "```" in texto:
            texto = texto.split("```")[1].lstrip("json").strip()
        recs = json.loads(texto)
    except Exception:
        recs = {"resumo": "Erro ao gerar recomendações", "prioridade": "baixa"}

    # Guardar para o Operator ler
    dados = {
        "gerado_em": datetime.now().isoformat()[:16],
        "resumo_loja": {"vendas": vendas, "receita": receita, "listings_activos": len(listings)},
        "recomendacoes": recs,
    }
    try:
        _MARKETEER_OPS.parent.mkdir(exist_ok=True)
        _MARKETEER_OPS.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    except Exception:
        pass

    return f"Recomendações escritas para Operator: {recs.get('resumo','OK')} (prioridade: {recs.get('prioridade','?')})"


def registar_campanha(nome: str, canal: str, objetivo: str) -> str:
    """Regista uma nova campanha de marketing."""
    state = _load_state()
    campanha = {
        "id": f"camp_{len(state['campanhas'])+1:03d}",
        "nome": nome,
        "canal": canal,
        "objetivo": objetivo,
        "criada": datetime.now().isoformat()[:16],
        "status": "ativa",
        "conversoes": 0,
    }
    state["campanhas"].append(campanha)
    _save_state(state)
    return f"Campanha '{nome}' registada (ID: {campanha['id']})."


TOOLS = [
    {
        "name": "pesquisar_leads",
        "description": "Pesquisa leads potenciais para um nicho e mercado específico via web search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nicho": {"type": "string", "description": "Nicho de mercado (ex: 'planners digitais', 'templates Excel')"},
                "mercado": {"type": "string", "description": "Mercado alvo (ex: 'PT', 'BR', 'ES')", "default": "PT"}
            },
            "required": ["nicho"]
        }
    },
    {
        "name": "analisar_etsy_nicho",
        "description": "Analisa concorrência e oportunidades de um nicho no Etsy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nicho": {"type": "string", "description": "Nicho a analisar no Etsy"}
            },
            "required": ["nicho"]
        }
    },
    {
        "name": "redigir_mensagem_outreach",
        "description": "Redige uma mensagem de outreach personalizada para um lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contexto": {"type": "string", "description": "Contexto sobre o lead (o que procura, onde foi encontrado)"},
                "destinatario": {"type": "string", "description": "Quem é o destinatário (perfil geral)"},
                "produto": {"type": "string", "description": "Produto ou serviço a oferecer"}
            },
            "required": ["contexto", "destinatario", "produto"]
        }
    },
    {
        "name": "registar_campanha",
        "description": "Regista uma nova campanha de marketing no sistema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string"},
                "canal": {"type": "string", "description": "Canal: etsy, linkedin, reddit, email, pinterest, etc."},
                "objetivo": {"type": "string"}
            },
            "required": ["nome", "canal", "objetivo"]
        }
    },
    {
        "name": "pesquisar_pinterest",
        "description": "Analisa tendências e presença de um nicho no Pinterest via web search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nicho": {"type": "string", "description": "Nicho a analisar no Pinterest (ex: 'planners digitais', 'bullet journal')"}
            },
            "required": ["nicho"]
        }
    },
    {
        "name": "otimizar_listings_etsy",
        "description": "Pesquisa keywords de alto tráfego Etsy e gera propostas de títulos + tags optimizados para o nicho.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nicho": {"type": "string", "description": "Nicho da loja (ex: 'planners digitais', 'templates organização')"}
            },
            "required": []
        }
    },
    {
        "name": "plano_pinterest_semanal",
        "description": "Gera plano de 5 pins Pinterest para a semana com títulos, descrições e hashtags.",
        "input_schema": {
            "type": "object",
            "properties": {
                "negocio": {"type": "string", "description": "Nome do negócio (ex: 'PlannerAtlas')"},
                "nicho": {"type": "string", "description": "Nicho de produto (ex: 'planners digitais')"}
            },
            "required": []
        }
    },
    {
        "name": "gerar_conteudo_social_planneratlas",
        "description": "Gera conteúdo de marketing (Pinterest, Instagram, TikTok) para um produto PlannerAtlas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "produto": {"type": "string", "description": "Nome/descrição do produto Etsy"},
                "idioma": {"type": "string", "description": "Idioma do conteúdo: 'de' (alemão), 'es' (espanhol), 'pt' (português)", "default": "de"}
            },
            "required": ["produto"]
        }
    },
    {
        "name": "analisar_instagram_referencia",
        "description": "Analisa o Instagram de uma conta de referência e compara com a conta do Vasco para identificar estratégias de crescimento.",
        "input_schema": {
            "type": "object",
            "properties": {
                "conta_referencia": {"type": "string", "description": "Handle Instagram da conta de referência (sem @)", "default": "pepteam"},
                "conta_vasco": {"type": "string", "description": "Handle Instagram do Vasco (sem @)", "default": "vascobotelhodacosta"}
            },
            "required": []
        }
    },
    {
        "name": "gerar_variantes_pin",
        "description": "Gera N variantes de pin Pinterest para o mesmo listing (fresh pin strategy — cada variante é uma imagem diferente com um ângulo diferente: use case, before/after, seasonal, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "produto": {"type": "string", "description": "Nome/descrição do produto Etsy"},
                "listing_url": {"type": "string", "description": "URL do listing Etsy (opcional)"},
                "idioma": {"type": "string", "description": "Idioma: 'de' (alemão), 'es' (espanhol), 'pt' (português)", "default": "de"},
                "n": {"type": "integer", "description": "Número de variantes a gerar (default: 5)", "default": 5}
            },
            "required": ["produto"]
        }
    },
    {
        "name": "analisar_top_performers",
        "description": "Loop fechado de aprendizagem: analisa os 20% de pins/listings com mais engagement e sugere variações dos vencedores para a próxima semana.",
        "input_schema": {
            "type": "object",
            "properties": {
                "semanas": {"type": "integer", "description": "Janela de análise em semanas (default: 4)", "default": 4}
            },
            "required": []
        }
    },
    {
        "name": "enviar_outreach_email",
        "description": "Envia um email de outreach personalizado via PurelyMail. Limite: 50 emails/dia. Requer confirmação do Vasco antes de enviar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destinatario_email": {"type": "string", "description": "Email do destinatário"},
                "assunto": {"type": "string", "description": "Assunto do email"},
                "corpo": {"type": "string", "description": "Corpo do email em texto simples"},
                "nome_destinatario": {"type": "string", "description": "Nome do destinatário (opcional)"}
            },
            "required": ["destinatario_email", "assunto", "corpo"]
        }
    },
]

TOOL_MAP = {
    "pesquisar_leads": lambda a: pesquisar_leads(**a),
    "analisar_etsy_nicho": lambda a: analisar_etsy_nicho(**a),
    "redigir_mensagem_outreach": lambda a: redigir_mensagem_outreach(**a),
    "registar_campanha": lambda a: registar_campanha(**a),
    "pesquisar_pinterest": lambda a: pesquisar_pinterest(**a),
    "otimizar_listings_etsy": lambda a: otimizar_listings_etsy(**a),
    "plano_pinterest_semanal": lambda a: plano_pinterest_semanal(**a),
    "enviar_outreach_email": lambda a: enviar_outreach_email(**a),
    "analisar_instagram_referencia": lambda a: analisar_instagram_referencia(**a),
    "gerar_conteudo_social_planneratlas": lambda a: gerar_conteudo_social_planneratlas(**a),
    "gerar_variantes_pin": lambda a: gerar_variantes_pin(**a),
    "analisar_top_performers": lambda a: analisar_top_performers(**a),
}


# ── Reply principal ───────────────────────────────────────────────────────────

def get_marketeer_reply(user_text: str) -> str:
    """Processa uma mensagem e devolve resposta do Marketeer com ferramentas."""
    state = _load_state()
    context = f"\nCampanhas activas: {len([c for c in state['campanhas'] if c.get('status')=='ativa'])}"

    mem_semantica = ""
    try:
        from episodic_memory import get_contexto_agente
        mem_semantica = get_contexto_agente("marketeer", user_text or "Etsy SEO marketing Pinterest campanhas BCVertex")
    except Exception:
        pass
    if mem_semantica:
        context += f"\n\n[Memórias relevantes]\n{mem_semantica}"

    msgs = [{"role": "user", "content": user_text}]
    for _ in range(5):
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT + context,
            tools=TOOLS,
            messages=msgs,
        )
        if r.stop_reason == "end_turn":
            reply = next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")
            try:
                from episodic_memory import registar_evento
                registar_evento("marketeer", "conversa", f"Q: {user_text[:100]} | R: {reply[:200]}")
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
