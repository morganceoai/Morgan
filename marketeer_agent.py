"""
Morgan Marketeer — Agente de outreach e crescimento do império BC Industries.
Identifica leads, redige mensagens personalizadas, monitoriza canais de aquisição.
Reporta ao Morgan CEO. A última decisão é sempre do Vasco.
"""
import os
import json
from pathlib import Path
from datetime import datetime
import anthropic

MEMORY_DIR = Path(__file__).parent / "memory"
MARKETEER_FILE = MEMORY_DIR / "marketeer_state.json"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """És o Morgan Marketeer, o agente de marketing e crescimento do império BC Industries.

O teu papel:
- Identificar oportunidades de outreach (leads que procuram um serviço que oferecemos)
- Redigir mensagens de contacto personalizadas e humanas (nunca spam genérico)
- Propor estratégias de aquisição de clientes para os negócios do Vasco
- Analisar canais: Etsy, LinkedIn, Reddit, fóruns PT/BR/ES
- Monitorizar desempenho de anúncios e sugerir melhorias
- Criar conteúdo de marketing (descrições de produtos Etsy, posts, emails)

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
                "canal": {"type": "string", "description": "Canal: etsy, linkedin, reddit, email, etc."},
                "objetivo": {"type": "string"}
            },
            "required": ["nome", "canal", "objetivo"]
        }
    },
]

TOOL_MAP = {
    "pesquisar_leads": lambda a: pesquisar_leads(**a),
    "analisar_etsy_nicho": lambda a: analisar_etsy_nicho(**a),
    "redigir_mensagem_outreach": lambda a: redigir_mensagem_outreach(**a),
    "registar_campanha": lambda a: registar_campanha(**a),
}


# ── Reply principal ───────────────────────────────────────────────────────────

def get_marketeer_reply(user_text: str) -> str:
    """Processa uma mensagem e devolve resposta do Marketeer com ferramentas."""
    state = _load_state()
    context = f"\nCampanhas activas: {len([c for c in state['campanhas'] if c.get('status')=='ativa'])}"

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

    return next((b.text for b in r.content if hasattr(b, "text")), "Sem resposta.")
