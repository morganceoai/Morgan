"""
Morgan Newsletter Agent — Negócio faceless automatizado
Niche: AI tools & productivity for founders (EN, US market)
Plataforma: Beehiiv
Automatização: curadoria de conteúdo + rascunho semanal + gestão de subs

NOTA DE SETUP (manual — requer acção do Vasco):
1. Criar conta Beehiiv em beehiiv.com (email morgan@bcvertex.com)
2. Criar publicação "The AI Pulse" (slug: ai-pulse)
3. Gerar API key em Settings → Integrations → API
4. Adicionar ao .env: BEEHIIV_API_KEY=... e BEEHIIV_PUB_ID=pub_...
"""
import os
import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

MEMORY_DIR = Path(__file__).parent / "memory"
NEWSLETTER_STATE_FILE = MEMORY_DIR / "newsletter_state.json"

BEEHIIV_BASE = "https://api.beehiiv.com/v2"
BEEHIIV_API_KEY = os.getenv("BEEHIIV_API_KEY", "")
BEEHIIV_PUB_ID = os.getenv("BEEHIIV_PUB_ID", "")

NEWSLETTER_NAME = "The AI Pulse BC"
NEWSLETTER_NICHE = "AI tools & productivity for founders"
NEWSLETTER_LINGUA = "EN"
NEWSLETTER_MERCADO = "US/UK/CA"

CONTENT_SOURCES = [
    "Product Hunt AI launches",
    "Hacker News Show HN",
    "r/SideProject top posts",
    "IndieHackers milestones",
    "AI tools releases last 7 days",
]


def _headers() -> dict:
    return {"Authorization": f"Bearer {BEEHIIV_API_KEY}", "Content-Type": "application/json"}


def _load_state() -> dict:
    if NEWSLETTER_STATE_FILE.exists():
        return json.loads(NEWSLETTER_STATE_FILE.read_text())
    return {
        "setup_completo": False,
        "pub_id": "",
        "subscribers": 0,
        "emails_enviados": 0,
        "ultimo_envio": "",
        "rascunhos": [],
        "receita_total": 0.0,
        "fase": "setup",
        "criado_em": datetime.now().isoformat(),
    }


def _save_state(state: dict):
    NEWSLETTER_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def verificar_setup() -> str:
    """Verifica se o Beehiiv está configurado e retorna estado."""
    state = _load_state()
    if not BEEHIIV_API_KEY:
        return (
            "⚠️ SETUP PENDENTE — Falta BEEHIIV_API_KEY no .env\n"
            "Passos manuais necessários:\n"
            "1. Criar conta em beehiiv.com (morgan@bcvertex.com)\n"
            "2. Criar publicação 'The AI Pulse'\n"
            "3. Settings → Integrations → API → gerar chave\n"
            "4. Adicionar BEEHIIV_API_KEY e BEEHIIV_PUB_ID ao .env"
        )
    if not BEEHIIV_PUB_ID:
        return "⚠️ SETUP PENDENTE — Falta BEEHIIV_PUB_ID no .env"
    return f"✅ Setup completo — {NEWSLETTER_NAME} configurada"


def obter_stats() -> dict:
    """Obtém estatísticas da newsletter via Beehiiv API."""
    if not BEEHIIV_API_KEY or not BEEHIIV_PUB_ID:
        return {"erro": "Beehiiv não configurado", "setup": verificar_setup()}
    try:
        r = httpx.get(
            f"{BEEHIIV_BASE}/publications/{BEEHIIV_PUB_ID}",
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        stats = {
            "nome": data.get("name", NEWSLETTER_NAME),
            "subscribers": data.get("stats", {}).get("total_active_subscriptions", 0),
            "emails_enviados": data.get("stats", {}).get("total_sent", 0),
        }
        state = _load_state()
        state["subscribers"] = stats["subscribers"]
        state["emails_enviados"] = stats["emails_enviados"]
        _save_state(state)
        return stats
    except Exception as e:
        return {"erro": str(e)}


def curar_conteudo_semanal() -> str:
    """Usa Claude para curar conteúdo da semana e gerar rascunho da newsletter."""
    try:
        from claude_guard import GuardedClient
        client = GuardedClient("pulser")

        hoje = datetime.now().strftime("%d %b %Y")
        semana_anterior = (datetime.now() - timedelta(days=7)).strftime("%d %b")

        prompt = f"""Prepara o rascunho da newsletter "{NEWSLETTER_NAME}" para a semana de {semana_anterior}–{hoje}.

Audiência: fundadores e builders anglofonos (US/UK/CA) — usam AI no trabalho diário.
Formato: 5 secções, cada uma concisa e accionável.

Estrutura obrigatória:
1. 🔥 THIS WEEK'S TOP PICK — 1 ferramenta AI nova que vale a pena testar (com caso de uso real)
2. ⚡ 3 TOOLS WORTH YOUR TIME — lista de 3 ferramentas com 1 linha de valor cada
3. 📈 INDIE FOUNDER WIN — 1 história real de um indie founder com AI (números concretos)
4. 🧠 PROMPT OF THE WEEK — 1 prompt específico que aumenta produtividade
5. 🎯 QUICK TAKE — 1 opinião directa sobre o estado do ecossistema AI

Tom: directo, sem fluff, sem buzzwords. Fala como um colega que encontrou algo útil.
Não usar: "game-changer", "revolutionary", "paradigm shift", "leverage", "synergy".

Gera o rascunho completo em inglês. Inclui subject line (max 50 chars) e preview text (max 90 chars)."""

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"Erro ao curar conteúdo: {e}"


def criar_rascunho_local(assunto: str, conteudo: str) -> dict:
    """
    Guarda rascunho localmente e notifica o Vasco via push.
    API Beehiiv só permite criar posts no plano Enterprise — usamos ficheiro local.
    """
    drafts_dir = MEMORY_DIR / "newsletter_drafts"
    drafts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    ficheiro = drafts_dir / f"draft_{timestamp}.md"
    ficheiro.write_text(f"# {assunto}\n\n{conteudo}", encoding="utf-8")

    state = _load_state()
    state["rascunhos"].append({
        "ficheiro": str(ficheiro),
        "assunto": assunto,
        "criado_em": datetime.now().isoformat(),
        "status": "draft_local",
    })
    _save_state(state)

    try:
        from push_service import send_push
        send_push(
            title="The AI Pulse BC — Rascunho pronto",
            body=f"'{assunto}' — copia para o Beehiiv e envia.",
            url="/pwa/"
        )
    except Exception:
        pass

    return {"ok": True, "ficheiro": str(ficheiro), "assunto": assunto}


def relatorio_semanal() -> str:
    """Relatório semanal do estado da newsletter para o CEO."""
    state = _load_state()
    setup = verificar_setup()

    if not BEEHIIV_API_KEY:
        return f"📰 THE AI PULSE — Estado\n{setup}"

    stats = obter_stats()

    subs = stats.get("subscribers", state.get("subscribers", 0))
    enviados = stats.get("emails_enviados", state.get("emails_enviados", 0))
    fase = state.get("fase", "setup")
    receita = state.get("receita_total", 0.0)

    milestones = {
        "setup": "Criar conta Beehiiv + primeiros 100 subs",
        "crescimento": "100-1.000 subs via SEO + conteúdo orgânico",
        "monetizacao": "1.000+ subs → activar Beehiiv Boosts + sponsors",
        "escala": "5.000+ subs → CPM sponsors $15-40/1k",
    }
    proximo = milestones.get(fase, "—")

    return f"""📰 THE AI PULSE — Relatório semanal
Fase: {fase} | Subs: {subs} | Emails enviados: {enviados}
Receita total: €{receita:.2f}
Próximo milestone: {proximo}
Rascunhos pendentes: {len([r for r in state.get('rascunhos', []) if r.get('status') == 'draft'])}"""


def ciclo_semanal_automatico() -> str:
    """Chamado automaticamente ao domingo pelo CEO. Cura + rascunho + relatório."""
    relatorio = relatorio_semanal()

    if not BEEHIIV_API_KEY:
        return relatorio + "\n\n⚠️ Sem acção — Beehiiv não configurado."

    conteudo_raw = curar_conteudo_semanal()

    conteudo_html = conteudo_raw.replace("\n", "<br>")
    linhas = conteudo_raw.split("\n")
    assunto = next((l for l in linhas if "subject" in l.lower()), "AI Pulse — This Week's Top Picks")
    assunto = assunto.split(":")[-1].strip().strip('"') if ":" in assunto else assunto[:50]

    resultado = criar_rascunho_local(assunto=assunto, conteudo=conteudo_raw)

    if resultado.get("ok"):
        return f"{relatorio}\n\n✅ Rascunho guardado: '{assunto}'\nFicheiro: {resultado['ficheiro']}\nCopia para o Beehiiv e envia quando aprovares."
    else:
        return f"{relatorio}\n\n❌ Erro ao guardar rascunho: {resultado.get('erro')}"


if __name__ == "__main__":
    print(verificar_setup())
    print()
    print(relatorio_semanal())
