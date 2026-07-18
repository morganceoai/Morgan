"""
Morgan Creator Agent
Constrói sub-Morgans para oportunidades de negócio aprovadas pelo Scout.
Cada sub-Morgan é um agente especializado com ferramentas, memória, ciclo de vida e reporting.

Reports automáticos desativados por defeito (REPORTS_ENABLED = False).
Ativar quando houver pelo menos um negócio com receita > 0.
"""
import os
import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path(__file__).parent / "memory"
CREATOR_STATE_FILE = MEMORY_DIR / "creator_state.json"

# ── Controlo de reports ──────────────────────────────────────────────────────
# Mantido em False até haver receita ativa. Mudar para True manualmente ou via CEO.
REPORTS_ENABLED = False

# ── Thresholds de autonomia hierárquica ──────────────────────────────────────
# Quando um negócio atinge estes valores, ganha gestão própria automaticamente.
# Abaixo de €500: Morgan CEO gere directamente.
# €500–€2k: 2-3 agentes operacionais, CEO ainda supervisiona.
# €2k–€5k: negócio ganha CEO próprio, Morgan CEO recebe relatórios.
# €5k+: CEO + CFO próprios — empresa autónoma dentro do império.
AUTONOMY_THRESHOLDS = [
    {
        "receita_min": 500,
        "receita_max": 2000,
        "estrutura": "multi_agente",
        "agentes": ["ops", "crescimento"],
        "descricao": "Equipa básica — Ops + Crescimento",
        "ceo_proprio": False,
        "cfo_proprio": False,
    },
    {
        "receita_min": 2000,
        "receita_max": 5000,
        "estrutura": "ceo_proprio",
        "agentes": ["ceo", "ops", "marketing"],
        "descricao": "CEO próprio — Morgan CEO recebe relatórios",
        "ceo_proprio": True,
        "cfo_proprio": False,
    },
    {
        "receita_min": 5000,
        "receita_max": None,  # sem tecto
        "estrutura": "empresa_autonoma",
        "agentes": ["ceo", "cfo", "ops", "marketing", "suporte"],
        "descricao": "Empresa autónoma — CEO + CFO próprios",
        "ceo_proprio": True,
        "cfo_proprio": True,
    },
]


# ── Knowledge Registry — o Creator sabe onde ir buscar o que precisa por domínio ──

DOMAIN_KNOWLEDGE = {
    "directorio": {
        "fontes_pesquisa": [
            "profitable directory website niche 2026 indiehackers revenue",
            "directory business model monetization case study AppSumo",
            "niche directory Italy Spain therapist tutor gap opportunity 2026",
        ],
        "comunidades": ["IndieHackers", "r/indiehackers", "r/entrepreneur", "MicroAcquire"],
        "ferramentas_data": ["Ahrefs (SEO)", "SimilarWeb (tráfego)", "Google Trends"],
        "metricas_sucesso": ["visitantes/mês", "listagens pagas", "receita afiliados"],
        "plataformas_venda": ["listagens diretas", "afiliados", "leads pagos"],
    },
    "directorio_terapeutas": {
        "fontes_pesquisa": [
            "therapist directory Italy Spain France niche site revenue 2026",
            "psychology directory listing fee model Psychology Today alternative",
            "mental health professional directory monetization €50-150/month listing 2026",
        ],
        "comunidades": ["IndieHackers", "r/indiehackers", "r/entrepreneur"],
        "ferramentas_data": ["WordPress + Directorist plugin", "Google Maps API", "Stripe"],
        "metricas_sucesso": ["terapeutas listados", "% premium pagos", "MRR"],
        "plataformas_venda": ["listagem premium €40-150/mês", "leads pagos", "booking integrado"],
        "primeiro_mercado": "Itália",
        "modelo_receita": "Listagem básica gratuita (cria massa crítica) + premium €40-150/mês",
        "caso_real": "£8k MRR em 18 meses · 200 terapeutas · £150/mês (UK)",
        "contas_necessarias": ["Domínio (Cloudflare €10/ano)", "Hosting WordPress (Hetzner €10/mês)",
                               "Directorist Plugin ($99/ano)", "Stripe (2.9%+€0.30)", "SendGrid (email onboarding)"],
    },
    "directorio_tutores": {
        "fontes_pesquisa": [
            "tutor directory Italy Indonesia niche site 2026 revenue Superprof alternative",
            "tutoring directory listing model subscription per tutor 2026",
            "private tutoring marketplace gap local directory verified tutors 2026",
        ],
        "comunidades": ["IndieHackers", "r/entrepreneur", "r/SaaS"],
        "ferramentas_data": ["WordPress + Directorist plugin", "Google Maps API", "Stripe"],
        "metricas_sucesso": ["tutores listados", "% premium pagos", "MRR", "sessões marcadas"],
        "plataformas_venda": ["subscription tutor €20-50/mês", "comissão por aula 10-20%"],
        "primeiro_mercado": "Itália",
        "modelo_receita": "Opção A — subscription tutor €20-50/mês para arrancar",
        "contas_necessarias": ["Domínio (Cloudflare €10/ano)", "Hosting WordPress (Hetzner €10/mês)",
                               "Directorist Plugin ($99/ano)", "Stripe (2.9%+€0.30)"],
    },
    "templates_digitais": {
        "fontes_pesquisa": [
            "digital planner Etsy German Spanish non-English market gap 2026",
            "GoodNotes Notability planner template bestseller non-English 2026",
            "Etsy digital downloads passive income 2026 German Spanish French Italian",
        ],
        "comunidades": ["r/passive_income", "Gumroad creators", "Etsy sellers"],
        "ferramentas_data": ["Gumroad analytics", "Etsy stats", "Canva Pro API"],
        "metricas_sucesso": ["unidades vendidas/mês", "preço médio €10-30", "reviews"],
        "plataformas_venda": ["Etsy (tráfego orgânico)", "Gumroad (audiência própria)"],
        "5_categorias": ["Planner anual/semanal/diário", "Planner objectivos e hábitos",
                         "Planner académico/estudante", "Planner negócios/freelancer", "Planner saúde/fitness"],
        "primeiros_mercados": ["Alemão (DE/AT/CH)", "Espanhol (ES/LATAM)"],
        "contas_necessarias": ["Etsy seller (requer ID do Vasco)", "Canva Pro ($15/mês)",
                               "Gumroad (10% comissão)", "Pinterest Business (gratuito)"],
    },
    "templates_notion": {
        "fontes_pesquisa": [
            "Notion template non-English market Spanish French German 2026 revenue",
            "Notion template Gumroad Etsy bestseller productivity finance 2026",
            "Notion marketplace template creator revenue passive income 2026",
        ],
        "comunidades": ["Notion template creators", "r/Notion", "Gumroad creators"],
        "ferramentas_data": ["Gumroad analytics", "Etsy stats", "Notion Marketplace"],
        "metricas_sucesso": ["unidades vendidas/mês", "preço médio €5-49", "avaliações"],
        "plataformas_venda": ["Gumroad (10%)", "Etsy (6.5%+$0.20/listing)", "Notion Marketplace (0%)"],
        "4_categorias": ["Produtividade e gestão pessoal (2ª Brain)", "Finanças pessoais (budget tracker)",
                         "Calendário editorial/criadores", "CRM e negócios (freelancer hub)"],
        "primeiros_mercados": ["Espanhol", "Francês"],
        "contas_necessarias": ["Gumroad (gratuito)", "Etsy seller (requer ID do Vasco)",
                               "Notion Marketplace (gratuito)", "Mailchimp (lista de email)"],
    },
    "relatorios_taticos": {
        "fontes_pesquisa": [
            "football tactical analysis SaaS coaches 2026 revenue pricing",
            "Wyscout alternative smaller clubs affordable AI reports",
            "AI football scouting platform MLS Liga Portugal subscription 2026",
            "StatsBomb open data API football analytics startups",
        ],
        "comunidades": ["r/soccer", "r/footballtactics", "LinkedIn coaches groups"],
        "ferramentas_data": ["Wyscout API", "FBref", "StatsBomb", "Transfermarkt", "API Football"],
        "metricas_sucesso": ["clubes subscritores", "preço/relatório", "churn de clubes"],
        "plataformas_venda": ["subscrição direta", "contacto a clubes", "parceria com ligas"],
        "vantagem_vasco": "Treinador profissional — credibilidade e rede de contactos no futebol PT/ES",
    },
    "gdpr_compliance": {
        "fontes_pesquisa": [
            "RGPD PME Portugal conformidade 2026 multas CNPD",
            "GDPR compliance small business Spain AEPD fines 2026",
            "GDPR SaaS tool SME Europe pricing competitor analysis",
        ],
        "comunidades": ["r/gdpr", "r/portugal", "LinkedIn PMEs PT/ES", "IndieHackers"],
        "ferramentas_data": ["Stripe", "Apollo.io cold email", "Supabase"],
        "metricas_sucesso": ["MRR", "churn <2%/mês", "leads por semana", "custo por cliente"],
        "plataformas_venda": ["subscrição mensal", "plano anual -30%"],
    },
    "review_management": {
        "fontes_pesquisa": [
            "review management software SMB Portugal Spain 2026 pricing",
            "Google Business Profile API review automation",
            "online reputation management tool small business cheap alternative Birdeye",
        ],
        "comunidades": ["r/smallbusiness", "LinkedIn clínicas PT/ES", "Grupos Facebook PMEs"],
        "ferramentas_data": ["Google Business Profile API", "Twilio SMS", "Stripe"],
        "metricas_sucesso": ["MRR", "churn <8%/mês", "reviews geradas/cliente/mês", "NPS"],
        "plataformas_venda": ["subscrição mensal", "plano anual"],
    },
    "freelancer_crm": {
        "fontes_pesquisa": [
            "HoneyBook alternative cheap simple freelancer CRM 2026",
            "freelancer client management tool Reddit 2026 Dubsado alternative",
            "simple invoicing proposals freelancers under $20/month",
        ],
        "comunidades": ["r/freelance", "r/webdev", "r/graphic_design", "IndieHackers", "Product Hunt"],
        "ferramentas_data": ["Stripe", "Supabase", "Product Hunt launch"],
        "metricas_sucesso": ["MRR", "churn <10%/mês", "tempo de onboarding <5min", "NPS"],
        "plataformas_venda": ["subscrição mensal", "plano anual -30%"],
    },
    "micro_saas": {
        "fontes_pesquisa": [
            "micro SaaS vertical niche 2026 10k month founder story indiehackers",
            "SaaS one person company profitable 2026 low competition",
            "vertical SaaS niche monopoly 2026 case study revenue",
        ],
        "comunidades": ["IndieHackers", "r/SaaS", "r/entrepreneur", "MicroAcquire"],
        "ferramentas_data": ["Stripe dashboard", "ChartMogul", "ProfitWell"],
        "metricas_sucesso": ["MRR", "churn rate", "LTV/CAC"],
        "plataformas_venda": ["subscrição SaaS", "freemium", "usage-based pricing"],
    },
    "investimento": {
        "fontes_pesquisa": [
            "passive portfolio management AI 2026 automation dividends",
            "automated investment strategy ETF rebalancing AI tools",
            "passive income investing Portugal 2026 tax efficient",
        ],
        "comunidades": ["r/investing", "r/financialindependence", "r/eupersonalfinance"],
        "ferramentas_data": ["Interactive Brokers API", "Yahoo Finance", "Alpha Vantage"],
        "metricas_sucesso": ["rendimento anual %", "volatilidade", "drawdown máximo"],
        "plataformas_venda": ["autogestão", "advisory fee se escalado a outros"],
    },
}


# ── Estado ──────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        return json.loads(CREATOR_STATE_FILE.read_text())
    except Exception:
        return {"sub_morgans": {}, "criados_em": []}

def _save_state(state: dict):
    CREATOR_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── Templates de sub-Morgan ──────────────────────────────────────────────────

TEMPLATES = {
    "directorio": {
        "nome": "Morgan Directório",
        "descricao": "Gere directório de nicho — conteúdo, SEO, monetização",
        "ferramentas": ["pesquisar_web", "tavily_search"],
        "prompt_base": """És o Morgan Directório, um sub-agente especializado em construir e gerir
directórios de nicho por país. O teu trabalho é:
1. Identificar categorias e subcategorias relevantes para o nicho e país
2. Pesquisar e catalogar entidades relevantes (terapeutas, tutores, etc.)
3. Sugerir estratégias de monetização (listagens pagas €40-150/mês, leads, afiliados)
4. Gerar conteúdo SEO optimizado no idioma do mercado-alvo
5. Planear campanha de cold outreach automático via email para atrair primeiros listados
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "directorio_terapeutas": {
        "nome": "Morgan Terapisti IT",
        "descricao": "Directório de terapeutas — primeiro mercado: Itália",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan Terapisti, sub-agente especializado no directório de terapeutas/psicólogos.
Primeiro mercado: Itália. Depois: Espanha, França, América Latina.
O teu trabalho:
1. Encontrar terapeutas italianos via Google Maps + Ordine degli Psicologi
2. Gerar emails de outreach personalizados em italiano (oferecer listagem gratuita 3 meses)
3. Criar perfis no directório com conteúdo SEO em italiano
4. Gerir conversão de gratuito para premium (€60-80/mês)
5. Relatório mensal ao CEO: terapeutas listados, % premium, MRR
Referência: Psychology Today ($29.95/mês US) · caso real UK: £8k MRR/18 meses com £150/mês
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "directorio_tutores": {
        "nome": "Morgan Tutori IT",
        "descricao": "Directório de tutores — primeiro mercado: Itália",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan Tutori, sub-agente especializado no directório de tutores/explicadores.
Primeiro mercado: Itália. Depois: Indonésia, Alemanha, Espanha.
O teu trabalho:
1. Encontrar tutores italianos via Google Maps + plataformas existentes
2. Gerar emails de outreach em italiano (listagem gratuita para os primeiros 50)
3. Criar perfis verificados com conteúdo SEO em italiano
4. Modelo: subscription €20-35/mês por tutor (começar simples, depois comissão por aula)
5. Relatório mensal ao CEO: tutores listados, % premium, MRR, sessões marcadas
Referência: Superprof (27M tutores em 50 países) — mas sem versão local curada em IT
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "templates_digitais": {
        "nome": "Morgan Planners",
        "descricao": "Cria e vende planners digitais em idiomas sub-representados no Etsy",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan Planners, especializado em criar e vender planners digitais
(GoodNotes/Notability) em idiomas com gap confirmado no Etsy.
Primeiros mercados: Alemão (DE/AT/CH) e Espanhol (ES/LATAM).
O teu trabalho:
1. Criar 50+ planners nos primeiros 30 dias nas 5 categorias aprovadas:
   — Planner anual/semanal/diário
   — Planner objectivos e hábitos
   — Planner académico/estudante
   — Planner negócios/freelancer
   — Planner saúde/fitness
2. Optimizar títulos e tags SEO em alemão e espanhol para o Etsy
3. Publicar também no Gumroad como backup
4. Monitorizar vendas e ajustar keywords
5. Relatório mensal: unidades vendidas, receita, reviews
Referência: Rachel Jimenez $9.5k/mês · PlannerKate milhões em receita total
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "templates_notion": {
        "nome": "Morgan Notion",
        "descricao": "Cria e vende Notion templates em idiomas sub-representados",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan Notion, especializado em criar e vender Notion templates
em idiomas com pouca concorrência.
Primeiros mercados: Espanhol e Francês. Depois: Alemão.
O teu trabalho:
1. Criar templates nas 4 categorias top (por ordem de prioridade):
   — Produtividade e gestão pessoal (Segunda Brain, dashboards)
   — Finanças pessoais (budget tracker, controlo de despesas)
   — Calendário editorial / criadores de conteúdo
   — CRM e negócios (freelancer hub, pipeline de clientes)
2. Publicar em 3 plataformas: Gumroad + Etsy + Notion Marketplace
3. Optimizar descrições em espanhol e francês
4. Construir lista de email com os primeiros compradores
5. Relatório mensal: vendas, receita, plataforma mais eficaz
Referência: $500k com um único template de finance tracker
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "relatorios_taticos": {
        "nome": "Morgan Tático",
        "descricao": "Gera relatórios táticos automáticos para clubes PT/ES",
        "ferramentas": ["pesquisar_web", "api_football"],
        "prompt_base": """És o Morgan Tático, especializado em análise e relatórios táticos de futebol.
Constróis relatórios pré-jogo e pós-jogo em português para clubes. O teu trabalho é:
1. Analisar dados de jogos e adversários via API Football
2. Identificar padrões táticos e vulnerabilidades
3. Gerar relatórios em linguagem natural para treinadores
4. Traduzir dados XML de Metrica/SportsCode em briefings legíveis
A vantagem competitiva é o conhecimento insider do Vasco como treinador profissional.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "micro_saas": {
        "nome": "Morgan SaaS",
        "descricao": "Desenvolve e lança micro-SaaS vertical de nicho",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan SaaS, especializado em identificar e construir micro-SaaS
para nichos verticais específicos. O teu trabalho é:
1. Validar o problema com utilizadores reais antes de construir
2. Definir MVP mínimo e stack tecnológico
3. Construir landing page e sistema de pagamento
4. Iterar com base em feedback real
Foco: resolver UM problema completamente para um grupo muito específico.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "gdpr_compliance": {
        "nome": "Morgan GDPR",
        "descricao": "SaaS de conformidade RGPD para PMEs em PT/ES — validação e lançamento",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan GDPR, sub-agente especializado em lançar e gerir um SaaS
de conformidade RGPD para PMEs em Portugal e Espanha.

PRODUTO: Dashboard RGPD em PT/ES — gerador de política de privacidade, banner cookies conforme,
ROPA automático, gestão de pedidos de titulares, alertas de prazo, relatório CNPD/AEPD.
PREÇO: €29/mês básico · €69/mês avançado · €149/mês multi-empresa.

FASE ACTUAL: validação — antes de construir qualquer coisa.

O teu trabalho em cada ciclo:
1. VALIDAÇÃO (primeiros 30 dias): criar landing page simples com formulário de interesse.
   Fazer cold email a 200 PMEs PT + 200 PMEs ES por semana.
   Métrica de avanço: 20+ emails de interesse em 30 dias → prosseguir para MVP.
2. MVP (meses 2–3): gerador de política de privacidade + banner cookies (sem ROPA ainda).
   Apenas depois de validação confirmada. Stack: Next.js + Supabase + Stripe.
   OBRIGATÓRIO: templates validados por advogado PT+ES antes de aceitar pagamentos.
3. LANÇAMENTO: cold email a lista de interessados, SEO "RGPD PME Portugal".
4. CRESCIMENTO: adicionar ROPA, gestão de titulares, expansão ES→IT→FR.
5. Relatório mensal ao CEO: leads, clientes pagantes, MRR, churn.

REGRAS:
- Nunca aceitar pagamentos sem validação jurídica dos templates.
- Usar multas reais da CNPD/AEPD como argumento de marketing.
- Churn esperado 1–2%/mês (moat regulatório) — focar em retenção desde onboarding.
- Escalar ao Vasco quando: primeiro pagante confirmado, ou problema legal identificado.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "review_management": {
        "nome": "Morgan Reviews",
        "descricao": "SaaS de gestão de reviews para PMEs locais PT/ES/IT — €29–49/mês",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan Reviews, sub-agente especializado em lançar e gerir um SaaS
de gestão de reviews online para PMEs locais em PT/ES/IT.

PRODUTO: Plataforma que centraliza e automatiza reviews — pedidos automáticos pós-compra
(email/SMS), monitorização Google/TripAdvisor/Facebook, resposta assistida por IA,
relatórios de reputação. PREÇO: €29/mês básico · €49/mês avançado.
GAP: Birdeye cobra €349/mês, Podium €289+/mês. Segmento sub-€50 está vazio.

NICHO DE ARRANQUE: clínicas dentárias e de estética PT — dor real, disposição a pagar confirmada.

O teu trabalho em cada ciclo:
1. VALIDAÇÃO (primeiros 30 dias): landing page + cold email a 200 clínicas PT/semana.
   Métrica de avanço: 15+ emails de interesse em 30 dias → prosseguir.
2. MVP (meses 2–3): integração Google Business Profile API + envio automático email pós-visita.
   Stack: Next.js + Supabase + Twilio (SMS) + Stripe.
3. LANÇAMENTO: Google Ads "gestão reviews Google Portugal" (budget €50–100/mês).
   Expandir para ES (clínicas) e IT (restauração).
4. CRESCIMENTO: adicionar TripAdvisor, Facebook, resposta IA, relatórios.
5. Relatório mensal ao CEO: leads, clientes, MRR, churn, NPS.

REGRAS:
- Primeiras reviews têm de aparecer em 2 semanas após onboarding — senão cliente cancela.
- Onboarding automático crítico: cliente instala em <10 minutos ou abandona.
- Escalar ao Vasco quando: primeiro pagante confirmado, ou integração de API falhar.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
    "freelancer_crm": {
        "nome": "Morgan FreelancerCRM",
        "descricao": "CRM minimalista para freelancers — mercado global EN, €19–39/mês",
        "ferramentas": ["pesquisar_web"],
        "prompt_base": """És o Morgan FreelancerCRM, sub-agente especializado em lançar e gerir
um CRM minimalista para freelancers em mercado global inglês.

PRODUTO: Dashboard simples para freelancers — gestão de clientes, propostas, contratos,
faturas, follow-ups automáticos, pipeline visual. Tudo em <5 cliques.
PREÇO: €19/mês solo · €39/mês profissional. EM INGLÊS — mercado global desde dia 1.
GAP: HoneyBook subiu para $19–79/mês (2024), Dubsado para $20–40/mês com curva enorme.
Freelancers querem 20% das features a 1/3 do preço.

O teu trabalho em cada ciclo:
1. VALIDAÇÃO (primeiros 30 dias): postar em Reddit r/freelance e r/webdev perguntando
   "pagariam €19/mês por X?" Criar landing page. Métrica: 25+ upvotes/comentários positivos.
2. MVP (meses 2–3): clientes + propostas + faturas simples + pipeline. SÓ ISSO na v1.
   Stack: Next.js + Supabase + Stripe. Sem features extra até 10 pagantes.
3. LANÇAMENTO: Product Hunt launch day + comparações SEO "HoneyBook alternative",
   "simple freelancer CRM", "cheap Dubsado alternative".
4. CRESCIMENTO: contratos com assinatura digital, integrações Calendly/Notion, plano anual.
5. Relatório mensal ao CEO: leads, pagantes, MRR, churn, feature requests top 3.

REGRAS:
- NUNCA adicionar features antes de ter 10 pagantes — simplicidade é o produto.
- Plano anual com 30% desconto desde o início — reduz churn estruturalmente.
- Escalar ao Vasco quando: primeiro pagante, ou Reddit/PH indicar pivot necessário.
Reportas ao Morgan CEO. A última decisão é sempre do Vasco.""",
    },
}

OPORTUNIDADE_TO_TEMPLATE = {
    "Directório de nicho PT/BR monetizado": "directorio",
    "Directório de terapeutas global": "directorio_terapeutas",
    "Directório de tutores global": "directorio_tutores",
    "Produtos digitais/templates em PT": "templates_digitais",
    "Templates planners digitais — mercados não-ingleses": "templates_digitais",
    "Templates Notion — mercados não-ingleses": "templates_notion",
    "Relatórios táticos automáticos em PT/ES (pivô futebol)": "relatorios_taticos",
    "Micro-SaaS vertical de nicho": "micro_saas",
    "GDPR Compliance SaaS PT/ES": "gdpr_compliance",
    "Review Management SaaS PT/ES/IT": "review_management",
    "Freelancer CRM global EN": "freelancer_crm",
}


# ── Interface pública ────────────────────────────────────────────────────────

def criar_sub_morgan(oportunidade: str) -> dict:
    """Cria um sub-Morgan para uma oportunidade aprovada pelo Scout."""
    # Camada 3 — memória semântica antes de criar
    try:
        from mem0_service import get_agent_context
        _mem_ctx = get_agent_context("creator", f"sub-morgan oportunidade {oportunidade[:80]}")
    except Exception:
        pass

    state = _load_state()

    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade)
    if not template_key:
        # Template genérico para oportunidades não mapeadas
        template_key = "micro_saas"

    template = TEMPLATES[template_key].copy()
    sub_id = template_key + "_" + datetime.now().strftime("%Y%m%d")

    if sub_id in state["sub_morgans"]:
        return {"status": "ja_existe", "id": sub_id, "nome": template["nome"]}

    knowledge = DOMAIN_KNOWLEDGE.get(template_key, {})
    sub_morgan = {
        "id": sub_id,
        "oportunidade": oportunidade,
        "nome": template["nome"],
        "descricao": template["descricao"],
        "ferramentas": template["ferramentas"],
        "prompt_base": template["prompt_base"],
        "criado_em": datetime.now().isoformat(),
        # Ciclo de vida: validacao → mvp → lancamento → crescimento → consolidacao → analise
        "fase": "validacao",
        "receita_atual": 0.0,
        "reports_enabled": False,  # ativar só quando houver receita
        # Knowledge do domínio herdado do registry
        "fontes_pesquisa": knowledge.get("fontes_pesquisa", []),
        "comunidades": knowledge.get("comunidades", []),
        "metricas_sucesso": knowledge.get("metricas_sucesso", []),
        "vantagem_vasco": knowledge.get("vantagem_vasco", ""),
        "mem0_user_id": f"sub_{template_key}",
        "metricas": {"interacoes": 0, "tarefas_concluidas": 0},
    }

    state["sub_morgans"][sub_id] = sub_morgan
    state["criados_em"].append({
        "id": sub_id,
        "oportunidade": oportunidade,
        "data": datetime.now().isoformat(),
    })
    _save_state(state)

    return {"status": "criado", "id": sub_id, "nome": template["nome"]}


def listar_sub_morgans() -> list:
    """Lista todos os sub-Morgans existentes."""
    state = _load_state()
    return list(state["sub_morgans"].values())


def get_sub_morgan(sub_id: str) -> dict:
    """Retorna um sub-Morgan pelo ID."""
    state = _load_state()
    return state["sub_morgans"].get(sub_id, {})


def get_prompt_sub_morgan(oportunidade: str) -> str:
    """Retorna o system prompt para o sub-Morgan de uma oportunidade."""
    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade, "micro_saas")
    return TEMPLATES[template_key]["prompt_base"]


def activar_sub_morgan(oportunidade: str, mensagem: str) -> str:
    """Invoca o sub-Morgan de uma oportunidade com uma mensagem."""
    import anthropic
    from tools import TOOLS, TOOL_FUNCTIONS
    from scout_memory import _load as load_scout

    scout_data = load_scout()
    aprovadas = scout_data.get("aprovadas", [])
    nomes_aprovados = [a["nome"] if isinstance(a, dict) else a for a in aprovadas]
    if oportunidade not in nomes_aprovados:
        return f"Oportunidade '{oportunidade}' não está aprovada pelo Vasco."

    state = _load_state()
    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade, "micro_saas")
    template = TEMPLATES[template_key]

    ferramentas_disponiveis = [t for t in TOOLS if t["name"] in template["ferramentas"]]

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    msgs = [{"role": "user", "content": mensagem}]

    while True:
        response = client.messages.create(
            model="claude-fable-5",
            max_tokens=2048,
            system=[{"type": "text", "text": template["prompt_base"],
                      "cache_control": {"type": "ephemeral"}}],
            messages=msgs,
            tools=ferramentas_disponiveis if ferramentas_disponiveis else [],
        )

        if response.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    func = TOOL_FUNCTIONS.get(block.name)
                    result = func(**block.input) if func else f"Ferramenta {block.name} não encontrada."
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            msgs.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if hasattr(block, "text"):
                    # Actualiza métricas
                    for sub in state["sub_morgans"].values():
                        if sub.get("oportunidade") == oportunidade:
                            sub["metricas"]["interacoes"] += 1
                    _save_state(state)
                    return block.text
            return ""


def verificar_autonomia(sub_id: str) -> dict:
    """
    Verifica se um negócio atingiu receita suficiente para ganhar gestão própria.
    Retorna a estrutura recomendada e se é uma mudança face ao estado actual.
    """
    state = _load_state()
    sub = state["sub_morgans"].get(sub_id)
    if not sub:
        return {"status": "nao_encontrado"}

    receita = sub.get("receita_atual", 0)
    estrutura_atual = sub.get("estrutura_autonomia", "ceo_central")

    # Determinar threshold aplicável
    threshold_aplicavel = None
    for t in AUTONOMY_THRESHOLDS:
        r_max = t["receita_max"] if t["receita_max"] else float("inf")
        if t["receita_min"] <= receita < r_max:
            threshold_aplicavel = t
            break

    if not threshold_aplicavel:
        # Abaixo de €500 — CEO central gere directamente
        nova_estrutura = "ceo_central"
        descricao = "CEO central gere directamente"
        agentes = []
        ceo_proprio = False
        cfo_proprio = False
    else:
        nova_estrutura = threshold_aplicavel["estrutura"]
        descricao = threshold_aplicavel["descricao"]
        agentes = threshold_aplicavel["agentes"]
        ceo_proprio = threshold_aplicavel["ceo_proprio"]
        cfo_proprio = threshold_aplicavel["cfo_proprio"]

    mudou = nova_estrutura != estrutura_atual

    if mudou:
        sub["estrutura_autonomia"] = nova_estrutura
        sub["agentes_autonomia"] = agentes
        sub["ceo_proprio"] = ceo_proprio
        sub["cfo_proprio"] = cfo_proprio
        _save_state(state)

    return {
        "status": "ok",
        "sub_id": sub_id,
        "nome": sub["nome"],
        "receita": receita,
        "estrutura": nova_estrutura,
        "descricao": descricao,
        "agentes_necessarios": agentes,
        "ceo_proprio": ceo_proprio,
        "cfo_proprio": cfo_proprio,
        "mudanca": mudou,
        "alerta_vasco": mudou and ceo_proprio,  # avisa o Vasco quando ganha CEO próprio
    }


def avancar_fase(sub_id: str) -> dict:
    """Avança o sub-Morgan para a próxima fase do ciclo de vida."""
    FASES = ["validacao", "mvp", "lancamento", "crescimento", "consolidacao", "analise", "autonomia"]
    state = _load_state()
    sub = state["sub_morgans"].get(sub_id)
    if not sub:
        return {"status": "nao_encontrado"}
    fase_atual = sub.get("fase", "validacao")
    idx = FASES.index(fase_atual) if fase_atual in FASES else 0
    if idx < len(FASES) - 1:
        sub["fase"] = FASES[idx + 1]
        # Ativar reports automaticamente a partir do lançamento
        if sub["fase"] in ("lancamento", "crescimento", "consolidacao", "analise"):
            sub["reports_enabled"] = True
        _save_state(state)
        return {"status": "ok", "fase_anterior": fase_atual, "fase_nova": sub["fase"]}
    return {"status": "ja_na_ultima_fase", "fase": fase_atual}


def registar_receita(sub_id: str, receita_mensal: float) -> dict:
    """Atualiza a receita de um sub-Morgan. Ativa reports e verifica autonomia."""
    state = _load_state()
    sub = state["sub_morgans"].get(sub_id)
    if not sub:
        return {"status": "nao_encontrado"}
    receita_anterior = sub.get("receita_atual", 0)
    sub["receita_atual"] = receita_mensal
    if receita_mensal > 0:
        sub["reports_enabled"] = True
    _save_state(state)

    # Verificar se muda de patamar de autonomia
    autonomia = verificar_autonomia(sub_id)

    resultado = {
        "status": "ok",
        "receita_anterior": receita_anterior,
        "receita_atual": receita_mensal,
        "reports_enabled": sub["reports_enabled"],
        "estrutura": autonomia["estrutura"],
        "descricao_estrutura": autonomia["descricao"],
    }

    if autonomia["alerta_vasco"]:
        resultado["alerta"] = (
            f"🏢 {sub['nome']} atingiu €{receita_mensal:.0f}/mês — "
            f"recomendo criar {autonomia['descricao']}. "
            f"Agentes necessários: {', '.join(autonomia['agentes_necessarios'])}."
        )

    return resultado


def report_global_creator() -> str:
    """Relatório global do Creator para o CEO — só corre se REPORTS_ENABLED ou houver receita ativa."""
    state = _load_state()
    subs = list(state["sub_morgans"].values())

    if not subs:
        return "Creator: nenhum sub-Morgan ativo."

    receita_total = sum(s.get("receita_atual", 0) for s in subs)
    com_receita = [s for s in subs if s.get("receita_atual", 0) > 0]

    if not REPORTS_ENABLED and receita_total == 0:
        return "Creator: reports em standby — sem receita ativa ainda."

    linhas = [f"MORGAN CREATOR — Relatório Global\nData: {datetime.now().strftime('%d/%m/%Y')}\n"]
    for sub in subs:
        linhas.append(
            f"• {sub['nome']} [{sub.get('fase','?')}]"
            f" — Receita: €{sub.get('receita_atual',0):.0f}/mês"
            f" — Reports: {'ON' if sub.get('reports_enabled') else 'standby'}"
        )
    linhas.append(f"\nReceita total: €{receita_total:.0f}/mês | Com receita: {len(com_receita)}/{len(subs)}")
    return "\n".join(linhas)


def get_domain_knowledge(oportunidade: str) -> str:
    """Devolve o knowledge do domínio formatado para uso em prompts."""
    template_key = OPORTUNIDADE_TO_TEMPLATE.get(oportunidade, "micro_saas")
    k = DOMAIN_KNOWLEDGE.get(template_key, {})
    if not k:
        return ""
    lines = ["## Knowledge do domínio:"]
    if k.get("fontes_pesquisa"):
        lines.append("Queries de pesquisa recomendadas (em inglês):\n- " + "\n- ".join(k["fontes_pesquisa"]))
    if k.get("comunidades"):
        lines.append("Comunidades a monitorizar: " + ", ".join(k["comunidades"]))
    if k.get("metricas_sucesso"):
        lines.append("Métricas de sucesso: " + ", ".join(k["metricas_sucesso"]))
    if k.get("vantagem_vasco"):
        lines.append(f"Vantagem do Vasco: {k['vantagem_vasco']}")
    return "\n".join(lines)


def gerar_plano_semana_planneratlas() -> str:
    """
    Gera automaticamente o plano de produtos para a semana no PlannerAtlas (Etsy).
    Corre toda a segunda-feira de manhã (integrado no heartbeat).
    Retorna texto com ideias de produtos + keywords Etsy.
    """
    import anthropic as _a
    from tools import pesquisar_web

    # Pesquisar tendências actuais Etsy para planners
    tendencias = ""
    try:
        tendencias = pesquisar_web("Etsy digital planner bestseller trending German Spanish 2026 GoodNotes")
    except Exception:
        pass

    prompt = f"""Hoje é {datetime.now().strftime('%A, %d de %B de %Y')}.

Você é o Morgan Planners — gestor autónomo da loja PlannerAtlas no Etsy.
A loja tem 8 anúncios activos em PT/ES/DE e tem de crescer para 50+ produtos.

TENDÊNCIAS DETECTADAS:
{tendencias[:500] if tendencias else 'indisponível'}

CONTEXTO:
- 5 categorias activas: planner anual/semanal/diário, objectivos/hábitos, académico, negócios/freelancer, saúde/fitness
- Mercados prioritários: Alemão (DE/AT/CH), Espanhol (ES/LATAM)
- Preço alvo: €3-15 por template
- Plataforma: Etsy (SEO por keywords) + Pinterest (visual)

Gera o plano para esta semana:
1. 3 novos produtos a criar (idioma, categoria, título Etsy em alemão ou espanhol)
2. Keywords SEO para cada produto (5 keywords por produto, no idioma do mercado)
3. Sugestão de imagem de capa (descreve o estilo visual)
4. Estratégia de Pinterest: 1 pin por produto (descrição curta, 5 hashtags)

Formato directo, sem rodeios. Português europeu."""

    client = _a.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    r = client.messages.create(
        model="claude-fable-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    plano = r.content[0].text if r.content else "Plano indisponível."

    # Guardar plano no ficheiro de memória do Creator
    plano_file = Path(__file__).parent / "memory" / "planneratlas_plano_semana.md"
    plano_file.parent.mkdir(exist_ok=True)
    plano_file.write_text(
        f"# Plano PlannerAtlas — {datetime.now().strftime('%d/%m/%Y')}\n\n{plano}",
        encoding="utf-8"
    )
    return plano


def gerar_conteudo_social_planneratlas(produto: str, idioma: str = "de") -> str:
    """
    Gera conteúdo para Pinterest/Instagram para um produto PlannerAtlas.
    idioma: 'de' (Alemão), 'es' (Espanhol), 'pt' (Português)
    """
    import anthropic as _a
    idiomas_map = {"de": "alemão", "es": "espanhol", "pt": "português europeu"}
    lang_name = idiomas_map.get(idioma, idioma)

    prompt = f"""Gera conteúdo de marketing para redes sociais para o seguinte produto Etsy:

Produto: {produto}
Idioma de saída: {lang_name}
Loja: PlannerAtlas (planners digitais GoodNotes/Notability no Etsy)

Cria:
1. **Pinterest** (2 descrições de pin — uma curta ~50 palavras, uma longa ~150 palavras)
2. **Instagram** (caption com emoji, máximo 150 palavras + 20 hashtags relevantes em {lang_name})
3. **TikTok** (hook inicial de 3 segundos + texto do vídeo ~100 palavras)

Tom: inspiracional, produtivo, minimalista. Público-alvo: estudantes e profissionais 18-35 anos."""

    client = _a.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    r = client.messages.create(
        model="claude-fable-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return r.content[0].text if r.content else "Conteúdo indisponível."


# ═══════════════════════════════════════════════════════════════════════════════
# CREATOR META-TOOL — Constrói e faz deploy de novos agentes de forma autónoma
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
import textwrap

MORGAN_DIR = Path(__file__).parent
MAC_MINI_HOST = "bcvertex@100.100.15.110"
MAC_MINI_MORGAN_DIR = "/Users/bcvertex/Morgan"

SYSTEM_PROMPT_META_CREATOR = """És o Morgan Creator, um meta-agente especializado em construir outros agentes Python.
Tens acesso ao código-fonte de todos os agentes existentes como referência.
Segues sempre os padrões do projecto:
- Ficheiro standalone com funções públicas: get_X_reply(msg) ou run_X()
- Usa anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
- System prompt em português europeu com regras claras
- Retorna sempre uma string
- Ferramentas via TOOLS/TOOL_FUNCTIONS de tools.py se necessário
- Logging com logger = logging.getLogger(__name__)
- Estado persistido em memory/X_state.json se necessário
- Nunca uses emojis no código. Código limpo, sem comentários desnecessários.
A última decisão é sempre do Vasco."""


def listar_agentes() -> list[str]:
    """Lista todos os ficheiros de agente Python no projecto."""
    agentes = []
    for f in sorted(MORGAN_DIR.glob("*_agent.py")):
        agentes.append(f.name)
    return agentes


def ler_agente(nome_ficheiro: str) -> str:
    """Lê o código de um agente existente (para usar como referência/template)."""
    f = MORGAN_DIR / nome_ficheiro
    if not f.exists():
        return f"Ficheiro {nome_ficheiro} não encontrado."
    return f.read_text(encoding="utf-8")


def gerar_codigo_agente(nome: str, descricao: str, capacidades: list[str]) -> str:
    """
    Usa Claude para gerar o código Python completo de um novo agente.
    nome: nome do agente (ex: 'operator')
    descricao: o que o agente faz (ex: 'Gere todas as lojas Etsy e directórios')
    capacidades: lista de capacidades (ex: ['gerir listagens Etsy', 'monitorizar receita'])
    """
    import anthropic as _a

    # Ler agentes existentes como referência
    refs = []
    for ag_file in ["cfo_agent.py", "coach_agent.py", "marketeer_agent.py"]:
        codigo = ler_agente(ag_file)
        if not codigo.startswith("Ficheiro"):
            refs.append(f"=== {ag_file} ===\n{codigo[:1500]}")

    referencias = "\n\n".join(refs)
    caps_str = "\n".join(f"- {c}" for c in capacidades)

    # Template base com todas as camadas de memória
    from agent_template import gerar_codigo_agente_base
    template_base = gerar_codigo_agente_base(nome, descricao)

    prompt = f"""Cria o ficheiro Python completo para um novo agente Morgan chamado '{nome}_agent.py'.

DESCRIÇÃO DO AGENTE:
{descricao}

CAPACIDADES OBRIGATÓRIAS:
{caps_str}

TEMPLATE BASE OBRIGATÓRIO (adapta e expande, nunca removes as camadas de memória):
{template_base}

AGENTES EXISTENTES COMO REFERÊNCIA DE PADRÕES:
{referencias}

REQUISITOS TÉCNICOS OBRIGATÓRIOS:
1. Função principal: get_{nome}_reply(msg: str) -> str
2. System prompt em português europeu detalhado, com regras claras
3. Integração com Claude claude-sonnet-4-6 via anthropic SDK
4. OBRIGATÓRIO: agent_bootstrap('{nome}') chamado na importação (primeira tarefa do agente)
5. OBRIGATÓRIO: get_agent_context('{nome}', ...) antes de cada resposta (camada semântica)
6. OBRIGATÓRIO: registar_evento('{nome}', ...) após cada resposta (camada episódica)
7. Se precisar de ferramentas externas, usar TOOLS/TOOL_FUNCTIONS de tools.py
8. Se precisar de estado persistente, usar memory/{nome}_state.json
9. Logging com logger = logging.getLogger(__name__)
10. Código limpo, sem comentários desnecessários, sem emojis

Devolve APENAS o código Python completo, sem explicações antes ou depois.
Começa com a docstring do módulo (\"\"\"...\"\"\") e termina com if __name__ == \"__main__\":"""

    client = _a.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model="claude-fable-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT_META_CREATOR,
        messages=[{"role": "user", "content": prompt}]
    )
    codigo = response.content[0].text if response.content else ""

    # Limpar markdown code blocks se o Claude os incluiu
    if codigo.startswith("```python"):
        codigo = codigo[9:]
    if codigo.startswith("```"):
        codigo = codigo[3:]
    if codigo.endswith("```"):
        codigo = codigo[:-3]

    codigo = codigo.strip()

    # Camada 2 — registar evento episódico
    try:
        from episodic_memory import registar_evento
        registar_evento("creator", "agente_gerado", f"Agente '{nome}' gerado: {descricao[:150]}")
    except Exception:
        pass

    return codigo


def escrever_agente(nome: str, codigo: str) -> dict:
    """Escreve o código do agente para o disco."""
    ficheiro = MORGAN_DIR / f"{nome}_agent.py"
    try:
        ficheiro.write_text(codigo, encoding="utf-8")
        return {"status": "ok", "ficheiro": str(ficheiro), "linhas": len(codigo.splitlines())}
    except Exception as e:
        return {"status": "erro", "message": str(e)}


def integrar_no_desktop(nome: str, keywords_trigger: list[str]) -> dict:
    """
    Integra o novo agente no desktop_server.py:
    - Adiciona import
    - Adiciona função de routing _quer_X()
    - Adiciona handling no chat_with_morgan()
    Retorna status da integração.
    """
    desktop = MORGAN_DIR / "desktop_server.py"
    codigo = desktop.read_text(encoding="utf-8")

    fn_import = f"get_{nome}_reply"
    modulo = f"{nome}_agent"

    # Verificar se já está integrado
    if fn_import in codigo:
        return {"status": "ja_integrado", "agente": nome}

    # 1. Adicionar import após os imports existentes de agentes
    import_line = f"from {modulo} import {fn_import}\n"
    # Inserir após a última linha "from X_agent import"
    import_anchor = "from marketeer_agent import get_marketeer_reply\n"
    if import_anchor in codigo:
        codigo = codigo.replace(import_anchor, import_anchor + import_line)
    else:
        # Fallback: adicionar antes da linha "from trading_bot"
        codigo = codigo.replace("from trading_bot import", import_line + "from trading_bot import", 1)

    # 2. Adicionar função _quer_X() após _quer_marketeer()
    kw_list = str(keywords_trigger).replace("'", '"')
    nova_func = f"""
def _quer_{nome}(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in {kw_list})

"""
    quer_marketeer_end = "def _chat_ceo(user_text: str) -> str:"
    if quer_marketeer_end in codigo:
        codigo = codigo.replace(quer_marketeer_end, nova_func + quer_marketeer_end)

    # 3. Adicionar handling no chat_with_morgan(), antes do "# Scout"
    handling = f"""
    if _quer_{nome}(user_text):
        _desktop_agent["current"] = "{nome}"
        try:
            reply = "[{nome.upper()}] " + {fn_import}(user_text)
        except Exception as e:
            reply = f"[{nome.upper()}] Erro: {{e}}"
        store_save(DESKTOP_USER_ID, "assistant", reply)
        return reply

"""
    scout_anchor = "    # Scout — CEO com contexto Scout"
    if scout_anchor in codigo:
        codigo = codigo.replace(scout_anchor, handling + scout_anchor)

    # 4. Adicionar ao valid set em /api/agent
    valid_anchor = 'valid = {"ceo", "coach", "cfo", "scout", "solver", "creator"}'
    if valid_anchor in codigo and f'"{nome}"' not in valid_anchor:
        novo_valid = valid_anchor.replace("}", f', "{nome}"}}')
        codigo = codigo.replace(valid_anchor, novo_valid)

    try:
        desktop.write_text(codigo, encoding="utf-8")
        return {"status": "ok", "agente": nome, "import": import_line.strip()}
    except Exception as e:
        return {"status": "erro", "message": str(e)}


def deploy_agente(nome: str, mensagem_commit: str = "") -> dict:
    """
    Deploy seguro com rollback automático:
    1. Validação de sintaxe antes do commit
    2. git add + commit + push
    3. SSH no Mac Mini: git pull + kill + restart
    4. Health check — reverte se o servidor não responder em 30s
    """
    import sys
    import time
    import urllib.request

    ficheiro = f"{nome}_agent.py"
    if not mensagem_commit:
        mensagem_commit = f"feat: {nome}_agent — criado pelo Creator"

    resultados = {}

    # 0. Validação de sintaxe antes de qualquer commit
    ficheiro_path = MORGAN_DIR / ficheiro
    if ficheiro_path.exists():
        check = subprocess.run(
            [sys.executable, "-m", "py_compile", str(ficheiro_path)],
            capture_output=True, text=True
        )
        if check.returncode != 0:
            return {"status": "erro", "fase": "sintaxe", "detalhes": check.stderr[:500]}
    desktop_path = MORGAN_DIR / "desktop_server.py"
    check_desktop = subprocess.run(
        [sys.executable, "-m", "py_compile", str(desktop_path)],
        capture_output=True, text=True
    )
    if check_desktop.returncode != 0:
        return {"status": "erro", "fase": "sintaxe_desktop", "detalhes": check_desktop.stderr[:500]}

    # Guardar commit anterior para rollback
    prev_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=MORGAN_DIR, capture_output=True, text=True
    ).stdout.strip()

    # 1. git add + commit + push
    try:
        subprocess.run(["git", "add", ficheiro, "desktop_server.py", "creator_agent.py"],
                       cwd=MORGAN_DIR, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", mensagem_commit],
                       cwd=MORGAN_DIR, check=True, capture_output=True)
        push = subprocess.run(["git", "push"], cwd=MORGAN_DIR, capture_output=True, text=True)
        resultados["git"] = "ok" if push.returncode == 0 else f"erro: {push.stderr[:200]}"
    except subprocess.CalledProcessError as e:
        resultados["git"] = f"erro: {e.stderr.decode()[:200] if e.stderr else str(e)}"

    # 2. SSH: pull + kill porta 8765 + restart com venv
    restart_cmd = (
        f"cd {MAC_MINI_MORGAN_DIR} && "
        "git pull && "
        "lsof -ti:8765 | xargs kill -9 2>/dev/null; "
        "sleep 3; "
        f"nohup {MAC_MINI_MORGAN_DIR}/venv/bin/python3 {MAC_MINI_MORGAN_DIR}/desktop_server.py "
        f"> {MAC_MINI_MORGAN_DIR}/morgan_server.log 2>&1 &"
    )
    try:
        ssh = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=no",
             MAC_MINI_HOST, restart_cmd],
            capture_output=True, text=True, timeout=30
        )
        resultados["deploy"] = "ok" if ssh.returncode == 0 else f"erro: {ssh.stderr[:200]}"
    except Exception as e:
        resultados["deploy"] = f"erro: {e}"
        return resultados

    # 3. Health check — polling por 30s
    health_ok = False
    for _ in range(6):
        time.sleep(5)
        try:
            resp = urllib.request.urlopen(
                f"http://{MAC_MINI_HOST.split('@')[1]}:8765/health", timeout=3
            )
            if resp.status == 200:
                health_ok = True
                break
        except Exception:
            pass

    if health_ok:
        resultados["health"] = "ok"
        return resultados

    # 4. Rollback automático — servidor não respondeu
    resultados["health"] = "timeout — a reverter"
    rollback_cmd = (
        f"cd {MAC_MINI_MORGAN_DIR} && "
        f"git checkout {prev_commit} && "
        "lsof -ti:8765 | xargs kill -9 2>/dev/null; "
        "sleep 2; "
        f"nohup {MAC_MINI_MORGAN_DIR}/venv/bin/python3 {MAC_MINI_MORGAN_DIR}/desktop_server.py "
        f"> {MAC_MINI_MORGAN_DIR}/morgan_server.log 2>&1 &"
    )
    try:
        subprocess.run(
            ["ssh", "-o", "ConnectTimeout=15", MAC_MINI_HOST, rollback_cmd],
            capture_output=True, text=True, timeout=30
        )
        # Reverter também o commit local
        subprocess.run(["git", "revert", "HEAD", "--no-edit"], cwd=MORGAN_DIR, capture_output=True)
        subprocess.run(["git", "push"], cwd=MORGAN_DIR, capture_output=True)
        resultados["rollback"] = f"revertido para {prev_commit[:8]}"
    except Exception as e:
        resultados["rollback_erro"] = str(e)

    return resultados


def construir_agente(
    nome: str,
    descricao: str,
    capacidades: list[str],
    keywords_trigger: list[str],
    auto_deploy: bool = True,
) -> dict:
    """
    Pipeline completo do Creator:
    1. Gera código Python com Claude
    2. Escreve o ficheiro
    3. Integra no desktop_server.py
    4. (Opcional) Deploy automático no Mac Mini

    Devolve um dict com o resultado de cada passo e o código gerado.
    O Vasco pode rever o código antes de autorizar o deploy.
    """
    resultado = {"nome": nome, "passos": {}}

    # Passo 1 — Gerar código
    print(f"[Creator] A gerar {nome}_agent.py...", flush=True)
    codigo = gerar_codigo_agente(nome, descricao, capacidades)
    if not codigo or len(codigo) < 100:
        return {"status": "erro", "message": "Código gerado inválido ou muito curto.", "codigo": codigo}
    resultado["passos"]["gerar"] = f"ok ({len(codigo.splitlines())} linhas)"
    resultado["codigo"] = codigo

    # Passo 2 — Escrever ficheiro
    escrita = escrever_agente(nome, codigo)
    resultado["passos"]["escrever"] = escrita["status"]
    if escrita["status"] != "ok":
        return {"status": "erro", "message": escrita.get("message"), **resultado}

    # Passo 3 — Integrar no desktop
    integracao = integrar_no_desktop(nome, keywords_trigger)
    resultado["passos"]["integrar"] = integracao["status"]

    # Passo 4 — Deploy (só se autorizado)
    if auto_deploy:
        deploy = deploy_agente(nome)
        resultado["passos"]["deploy"] = deploy

    resultado["status"] = "ok"
    return resultado


def rever_agente(nome: str) -> str:
    """Lê o agente gerado para revisão antes do deploy."""
    f = MORGAN_DIR / f"{nome}_agent.py"
    if not f.exists():
        return f"Agente {nome}_agent.py não existe ainda."
    return f.read_text(encoding="utf-8")


if __name__ == "__main__":
    # Teste rápido
    resultado = criar_sub_morgan("Directório de nicho PT/BR monetizado")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print("\nSub-Morgans criados:", len(listar_sub_morgans()))
    print("\nKnowledge do domínio:")
    print(get_domain_knowledge("Directório de nicho PT/BR monetizado"))
