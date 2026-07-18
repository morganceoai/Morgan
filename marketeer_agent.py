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

O teu papel:
- Identificar oportunidades de outreach (leads que procuram um serviço que oferecemos)
- Redigir mensagens de contacto personalizadas e humanas (nunca spam genérico)
- Propor estratégias de aquisição de clientes para os negócios do Vasco
- Analisar canais: Etsy, LinkedIn, Reddit, fóruns PT/BR/ES
- Monitorizar desempenho de anúncios e sugerir melhorias
- Criar conteúdo de marketing (descrições de produtos Etsy, posts, emails)
- Analisar tendências no Pinterest e sugerir pins/nichos com tráfego
- Enviar emails de outreach personalizados (máx 50/dia) — SEMPRE pedir confirmação ao Vasco antes de enviar

Negócios actuais do Vasco:
- PlannerAtlas (Etsy): planners digitais em PT/ES/DE — foco em nichos de produtividade, organização, bullet journal
- Trading bot BTC/USDT (crescimento de capital)
- Directórios e templates PT/BR em desenvolvimento

Princípios:
- Mensagens de outreach: curtas, directas, personalizadas, com valor real
- Nunca propores comprar listas de emails ou práticas spam
- Foco em mercados lusófonos e ibéricos primeiro
- Métricas que importam: conversões, receita, CAC, LTV

LÍNGUA: Responde SEMPRE em português europeu (PT-PT). Nunca uses inglês.
"""


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
    """Pesquisa leads potenciais via Tavily para um nicho e mercado."""
    try:
        from tavily import TavilyClient
        c = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        query = f"{nicho} procura comprar {mercado} 2025 2026 fórum reddit"
        r = c.search(query, max_results=5, search_depth="basic")
        snippets = []
        for res in (r.get("results") or [])[:5]:
            url = res.get("url", "")
            content = res.get("content", "")[:200]
            if content:
                snippets.append(f"- {url}\n  {content}")
        return "Leads encontrados:\n" + "\n".join(snippets) if snippets else "Sem resultados."
    except Exception as e:
        return f"Erro na pesquisa: {e}"


def analisar_etsy_nicho(nicho: str) -> str:
    """Analisa concorrência e oportunidades Etsy via Tavily."""
    try:
        from tavily import TavilyClient
        c = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        r = c.search(f"etsy {nicho} bestseller digital download 2025 2026", max_results=4, search_depth="basic")
        snippets = [res.get("content","")[:250] for res in (r.get("results") or [])[:4] if res.get("content")]
        return "Análise Etsy:\n" + "\n---\n".join(snippets) if snippets else "Sem dados."
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
    """Analisa presença e tendências de um nicho no Pinterest via Tavily."""
    try:
        from tavily import TavilyClient
        c = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        queries = [
            f"site:pinterest.com {nicho} planner digital download most saved 2026",
            f"pinterest {nicho} trending pins viral digital product",
        ]
        snippets = []
        for q in queries:
            r = c.search(q, max_results=3, search_depth="basic")
            for res in (r.get("results") or []):
                c_text = res.get("content", "")[:250]
                if c_text:
                    snippets.append(f"• {res.get('url','')}\n  {c_text}")
        if snippets:
            return f"**Pinterest — {nicho}:**\n" + "\n".join(snippets[:5])
        return f"Sem dados Pinterest para '{nicho}'."
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

    smtp_user = os.getenv("MORGAN_EMAIL", "")
    smtp_pass = os.getenv("MORGAN_EMAIL_PASS", "")
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
        from tavily import TavilyClient
        c = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
        r1 = c.search(f"etsy SEO keywords {nicho} 2026 high traffic tags titles best sellers", max_results=3, search_depth="basic")
        r2 = c.search(f"etsy {nicho} top listings titles tags Portuguese Spanish", max_results=3, search_depth="basic")
        snippets = []
        for r in [r1, r2]:
            snippets += [res.get("content", "")[:300] for res in (r.get("results") or [])[:3] if res.get("content")]
        dados_seo = "\n---\n".join(snippets[:5])
    except Exception as e:
        dados_seo = f"(pesquisa indisponível: {e})"

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system="És o Marketeer do Morgan. Especializas-te em SEO para Etsy. Geras títulos e tags de alta conversão.",
            messages=[{"role": "user", "content": f"""Nicho: {nicho}
Dados de pesquisa SEO:
{dados_seo}

Gera 3 propostas de optimização para listings Etsy:
1. Título optimizado (max 140 chars, keywords à frente)
2. 13 tags (separadas por vírgula)
3. Primeira frase da descrição (gancho de 1 linha)

Formato para cada proposta:
TÍTULO: ...
TAGS: ...
DESCRIÇÃO: ...

PT-PT. Sem emojis."""}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"Erro ao gerar optimizações: {e}"


def plano_pinterest_semanal(negocio: str = "PlannerAtlas", nicho: str = "planners digitais") -> str:
    """Gera um plano de pins Pinterest para a semana — 5 pins com descrições e hashtags."""
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system="Crias planos de conteúdo Pinterest para lojas Etsy. Foco em pins que convertem em visitas.",
            messages=[{"role": "user", "content": f"""Negócio: {negocio} — loja Etsy de {nicho}
Mercados: PT, ES, BR

Cria um plano de 5 pins para esta semana:
- Título do pin (max 100 chars)
- Descrição (max 200 chars, inclui hashtags relevantes)
- Tipo de imagem sugerida

Formato: PIN 1: | Título: | Descrição: | Imagem:
PT-PT. Foco em descoberta orgânica."""}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"Erro: {e}"


def analisar_instagram_referencia(conta_referencia: str = "pepteam", conta_vasco: str = "vascobotelhodacosta") -> str:
    """
    Analisa uma conta Instagram de referência (ex: @pepteam de Pep Guardiola)
    e produz um plano de crescimento para a conta do Vasco como treinador.
    Usa pesquisa web como proxy (Instagram não tem API pública sem aprovação).
    """
    from tools import pesquisar_web

    resultados = []
    for q in [
        f"instagram @{conta_referencia} estratégia conteúdo futebol treinador",
        f"instagram coach football content strategy growth 2026",
        f"treinador futebol instagram crescimento conta pessoal dicas 2026",
    ]:
        try:
            resultados.append(pesquisar_web(q)[:500])
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
}


# ── Reply principal ───────────────────────────────────────────────────────────

def get_marketeer_reply(user_text: str) -> str:
    """Processa uma mensagem e devolve resposta do Marketeer com ferramentas."""
    state = _load_state()
    context = f"\nCampanhas activas: {len([c for c in state['campanhas'] if c.get('status')=='ativa'])}"
    try:
        from mem0_service import get_agent_context
        mem_sistema = get_agent_context("marketeer", user_text or "marketing Etsy Pinterest outreach campanhas SEO")
        if mem_sistema:
            context = f"\n## Memória relevante:\n{mem_sistema}\n{context}"
    except Exception:
        pass

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
            return next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")
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

    reply = next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")

    # Camada episódica — registar evento
    try:
        from episodic_memory import registar_evento
        registar_evento("marketeer", "conversa", f"Q: {user_text[:100]} | R: {reply[:200]}")
    except Exception:
        pass

    return reply
