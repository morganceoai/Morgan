"""
Script one-shot: insere entradas históricas retroativas no Diário Morgan.
Cobre toda a história do projecto desde a criação (Julho 2026).
Executar uma vez apenas.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

from notion_service import diario_log

entradas = [
    # ── W26: Criação do projecto ─────────────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Decisão",
        "data_override": "2026-07-05",
        "titulo": "Projecto Morgan — criação inicial",
        "conteudo": """BCVertex criado como "império de negócios autónomos" gerido por IA.
Decisões de arquitectura iniciais:
- LLM principal: Claude Sonnet (custo/benefício)
- Deploy: Railway (plataforma inicial)
- Interface: Telegram (canal principal)
- Memória: Mem0 Cloud
- Agentes iniciais: CEO + Scout + Coach

Objectivo: €10.000/mês de rendimento passivo para Vasco Botelho da Costa (treinador Moreirense FC)."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-05",
        "titulo": "Scout v1 — 7 ferramentas, Opus 4.8",
        "conteudo": "Scout melhorado com 7 ferramentas de pesquisa, modelo Opus 4.8 para síntese estratégica, queries cirúrgicas com síntese cruzada de fontes múltiplas."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-06",
        "titulo": "Solver v2 LangGraph — 5 nós, confiança por passo",
        "conteudo": "Solver reescrito com LangGraph: 5 nós de raciocínio encadeado, score de confiança por passo, track record de fixes bem-sucedidos, autonomia de debugging."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Acção",
        "data_override": "2026-07-06",
        "titulo": "Sistema de autonomia CEO — 3/3 testes OK",
        "conteudo": "CEO testado com 3 cenários de autonomia: escalar ao Vasco quando confiança <90%, agir sozinho quando ≥90%, pipeline de aprovação paralela. Todos os testes passaram."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Decisão",
        "data_override": "2026-07-06",
        "titulo": "Optimização de custos — Sonnet em vez de Opus por defeito",
        "conteudo": "Decisão: usar claude-sonnet para rotinas, claude-opus-4-8 apenas para decisões estratégicas. Threshold mínimo de 3 erros antes de escalar. Prompt caching activado onde aplicável."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-07",
        "titulo": "Interface desktop + PWA iPhone criadas",
        "conteudo": "Interface desktop (JARVIS) criada em desktop/. PWA iPhone criada em pwa/ com service worker. Desktop serve dados reais do Scout. Interface diferenciada por user-agent."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-07",
        "titulo": "Creator Agent + Coach criados",
        "conteudo": "Creator Agent estruturado com domain knowledge registry e ciclos de vida de agentes. Morgan Coach criado para análise tática Moreirense FC, com routing Telegram e esfera verde na interface."
    },
    {
        "fonte": "Scout",
        "tipo": "Briefing",
        "data_override": "2026-07-07",
        "titulo": "Scout Missão A — 5 oportunidades identificadas",
        "conteudo": """Primeiro relatório Scout executado. 5 oportunidades:
1. Directório nicho PT/BR monetizado — €1-3k/mês, baixo risco
2. Produtos digitais/templates em PT — €500-5k/mês, muito baixo risco
3. Relatórios táticos automáticos PT/ES — €500-3k/clube
4. Micro-SaaS vertical de nicho — €5-50k/mês, risco médio
5. Compra de blog/site com receita — requer capital €10-20k

Nenhuma aprovada pelo Vasco — pipeline de aprovação não activada ainda."""
    },
    # ── W27: Sprints 1-5 ─────────────────────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Sprints 1-2 — fixes críticos + resiliência",
        "conteudo": "Sprint 1-2: fixes de arranque — load_dotenv em todos os agentes, tratamento de erros Binance, estrutura de imports, variáveis de ambiente garantidas. Sistema estabilizado para produção."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Sprint 3 — Coach cache, Etsy OAuth2, structlog, pytest T1-T10",
        "conteudo": "Coach com cache de análises. Etsy OAuth2 implementado (redirect localhost:3456). structlog integrado em todos os agentes. Suite pytest com 10 testes base (T1-T10)."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Sprint 4 — Haiku router + Pinterest + Gmail outreach",
        "conteudo": "Router de intent com claude-haiku-4-5 para classificar mensagens → agente correcto. Pinterest service criado. Gmail outreach configurado (GMAIL_OUTREACH_USER pendente)."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Sprint 5 — Mem0 dual-mode, StatsBomb, CI GitHub Actions",
        "conteudo": "Mem0 em modo dual (cloud + local fallback). StatsBomb Open Data integrado no Coach para análise histórica. CI/CD via GitHub Actions configurado — deploy automático para Railway."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-15",
        "titulo": "Fix — Mem0 desligado (quota esgotada) + PT-PT obrigatório",
        "conteudo": "Mem0 Cloud desactivado após quota esgotar. Sistema continua sem memória semântica temporariamente. PT-PT adicionado como obrigatório no system prompt de todos os agentes."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-15",
        "titulo": "Fix — voz iOS AudioWorklet + selecção de agente no painel",
        "conteudo": "AudioWorklet para iOS — fix de processamento de voz em Safari. Painel de selecção de agente activo na interface. Service Worker v5 para forçar bypass de cache Cloudflare."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Marketeer Agent criado + Telegram desligado",
        "conteudo": "Marketeer Agent criado — SEO Etsy, Pinterest, content strategy, outreach. Telegram completamente removido do sistema (8 ficheiros apagados). Interface principal migra para PWA + desktop."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Operator Agent criado pelo Creator (meta-tool)",
        "conteudo": "Creator usou a sua própria capacidade de deploy para criar o Operator Agent — primeiro teste bem-sucedido do ciclo Creator→novo agente. Operator gere negócios activos (Etsy, plataformas)."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-15",
        "titulo": "Sprints A/C/D/E/F — sistema auto-adaptável, briefings, browser automation",
        "conteudo": """Sprint A: sistema auto-adaptável com feedback loops.
Sprint C: briefings reestruturados — CEO orquestra UMA mensagem por dia (7h + 22h).
Sprint D: browser automation com Playwright headless no Mac Mini.
Sprint E: pipeline de aprovação paralela (Creator+Marketeer+Solver+CFO em simultâneo).
Sprint F: notificações browser (PWA push notifications) implementadas."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-15",
        "titulo": "Fix — briefing 7h — CEO orquestra, Coach só futebol, CFO só trading",
        "conteudo": "Regra de separação de áreas codificada: CEO compila e envia 1 mensagem. Coach=futebol apenas. CFO=trading apenas. Nunca misturar áreas num briefing."
    },
    # ── W28: Sprints H-M + infra major ──────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-16",
        "titulo": "Sprint K — Notion Service com estrutura BCVertex",
        "conteudo": "notion_service.py criado com estrutura completa BCVertex: páginas para BC Industries, Lego, Condomínio, Moreirense, Pessoal. Raiz do workspace Notion configurada."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-16",
        "titulo": "Scout 16h, Opus estratégico, browser notifications, Lego/REITs",
        "conteudo": "Scout com missão adicional às 16h. Opus 4.8 para decisões estratégicas (Vasco aprova upgrades). Browser notifications activas. Scout inclui oportunidades Lego e REITs no pipeline."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-17",
        "titulo": "Sprints H+I+L+M — loop Scout→Creator, REITs, Instagram, monitorização",
        "conteudo": """Sprint H: loop Scout→Creator — oportunidade aprovada dispara Creator automaticamente.
Sprint I: REITs integrados como asset class no CFO.
Sprint L: Instagram Reels automation via Creator.
Sprint M: monitorização autónoma do sistema — CEO detecta anomalias sem intervenção."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-17",
        "titulo": "CI/CD — deploy automático Mac Mini via GitHub Actions",
        "conteudo": "GitHub Actions workflow criado: push para main → SSH → git pull no Mac Mini. Dependências de sistema: portaudio19-dev, libsndfile1, python-multipart. ENV_FILE secret no GitHub."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-17",
        "titulo": "Fix — load_dotenv em todos os agentes",
        "conteudo": "load_dotenv() adicionado no início de cada agente e script standalone. Garante variáveis de ambiente carregadas independentemente do working directory."
    },
    # ── 18 Julho: dia de grandes mudanças ────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-18",
        "titulo": "Perplexity Sonar integrado — routing por agente",
        "conteudo": """Perplexity API integrada com 4 modelos por papel:
- sonar: queries rápidas (CEO/Marketeer)
- sonar-pro: análise profunda (Scout)
- sonar-deep-research: investigação extensa (Scout missões)
- sonar-reasoning-pro: raciocínio (Creator/Solver)
Substituição parcial de Tavily onde Perplexity é mais adequado."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-18",
        "titulo": "Fix — deploy via Tailscale (Mac Mini atrás de rede privada)",
        "conteudo": "Mac Mini não acessível via IP público — atrás de rede privada do Moreirense. Solução: Tailscale VPN (conta morganceoai@gmail.com). IP Tailscale: 100.100.15.110. Auth Key CI expira 2026-10-16."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-18",
        "titulo": "Fix — recuperar interface desktop JARVIS (apagada acidentalmente)",
        "conteudo": "Interface desktop JARVIS foi apagada no commit 42db444 (cleanup de protótipos). Recuperada do histórico git e restaurada. Rota / serve desktop vs PWA por user-agent. Regra: desktop/ e pwa/ nunca apagar sem confirmação."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-18",
        "titulo": "4 camadas de memória em todos os agentes",
        "conteudo": """Template padrão de memória implementado em todos os agentes:
1. Memória de trabalho (contexto da conversa actual)
2. Memória episódica (JSON local — eventos passados)
3. Memória semântica (Qdrant — busca por similaridade)
4. Memória de sistema (factos.md — verdades permanentes)
Função get_agent_context() centraliza o acesso."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Decisão",
        "data_override": "2026-07-18",
        "titulo": "Renomear BC Industries → BCVertex em todo o sistema",
        "conteudo": "Decisão de branding: BC Industries rebaptizado BCVertex. Actualizado em sistema_estado.json, CLAUDE.md, todos os agentes, interface, emails. BCVertex é o nome oficial do império."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Decisão",
        "data_override": "2026-07-18",
        "titulo": "Remoção do Mem0 Cloud — tudo em Qdrant",
        "conteudo": """Mem0 Cloud removido completamente do sistema. Motivos:
1. Redundante — Qdrant faz o mesmo com mais controlo
2. Quota esgotada repetidamente
3. Overhead de dependência externa desnecessário
Todos os agentes migrados para Qdrant Cloud directamente. MEM0_API_KEY inactiva."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-18",
        "titulo": "CEO system prompt 9/10 — delegação, síntese, acções irreversíveis",
        "conteudo": "CEO system prompt reescrito: delegação explícita por domínio, síntese de múltiplos agentes, checklist de acções irreversíveis, protocolo de escalada ao Vasco, formato de briefing padronizado."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-18",
        "titulo": "Scout Quality Gate — 10 critérios, falsificação, score ponderado",
        "conteudo": "Scout com quality gate rigoroso: 10 critérios de avaliação, teste de falsificabilidade, score ponderado por risco/retorno/viabilidade. Oportunidades abaixo de 70/100 rejeitadas automaticamente."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-18",
        "titulo": "CEO — lista de agentes dinâmica via sistema_estado.json",
        "conteudo": "CEO lê sistema_estado.json para obter lista de agentes disponíveis em runtime — não hardcoded. Permite Creator adicionar novos agentes sem alterar CEO. Fonte de verdade centralizada."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-18",
        "titulo": "Actualizar modelos LLM por agente",
        "conteudo": """Modelos actualizados por agente:
- CEO/Scout: claude-opus-4-8 (decisões estratégicas)
- Coach/CFO/Creator/Solver: claude-sonnet-4-6 (rotina)
- Router: claude-haiku-4-5-20251001 (classificação rápida)
- Marketeer/Operator: claude-sonnet-4-6"""
    },
    # ── Auditoria de agentes ─────────────────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Acção",
        "data_override": "2026-07-19",
        "titulo": "Auditoria completa agentes — Sprints 1-5 — score global 7.9/10",
        "conteudo": """Auditoria de todos os agentes. Score global: 7.9/10. 18/18 testes passaram.
Scores por agente:
- CEO: 9/10 — orquestração sólida, briefings correctos
- Scout: 9/10 — quality gate implementado, missões A+B+C+D
- Coach: 8/10 — ferramentas futebol funcionais, StatsBomb integrado
- CFO: 8/10 — Binance activo, DCA implementado, REITs adicionados
- Creator: 8/10 — deploy seguro, rollback, Playwright
- Solver: 9/10 — BM25+Qdrant, circuit breaker, git snapshot
- Operator: 8/10 — gestão Etsy, anomaly detection
- Marketeer: 8/10 — SEO, Pinterest, fresh pin strategy"""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-19",
        "titulo": "Solver 9/10 — BM25+Qdrant semântico, circuit breaker",
        "conteudo": "Solver com busca híbrida BM25+Qdrant para encontrar fixes similares. Circuit breaker para evitar loops infinitos. Git snapshot antes de cada fix (rollback automático). Ferramentas corrigidas."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-19",
        "titulo": "Memória episódica dual-write (JSON + Qdrant) em todos os agentes",
        "conteudo": "Todos os agentes fazem dual-write: episodic_memory.json (local, rápido) + Qdrant (semântico, pesquisável). Relatórios de briefing incluem delta episódico — só reporta mudanças desde o último briefing."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-19",
        "titulo": "Roadmap agentes — 5 melhorias identificadas",
        "conteudo": """5 melhorias prioritárias identificadas após auditoria:
1. Feedback loop Scout — oportunidades rejeitadas alimentam critérios futuros
2. Coach ferramentas adicionais — API Football ao vivo
3. Creator registry — tracking de agentes criados
4. Solver monitor — alertas proactivos de saúde do sistema
5. Operator aprendizagem — padrões de sucesso/falha no Etsy"""
    },
    # ── Etsy + Binance activações ─────────────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-20",
        "titulo": "Etsy API funcional — leitura + acções (pause, activar, preço)",
        "conteudo": """Etsy API v3 integrada:
- Autenticação: x-api-key com base64(keystring:sharedsecret)
- shop_id numérico: 66877755 (PlannerAtlas)
- Leitura: listings, stats, reviews
- Acções: pause listing, activar listing, actualizar preço
8 listings activos no PlannerAtlas mas zero visitas."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-20",
        "titulo": "Gestão autónoma Etsy — Operator tool loop, Marketeer→Operator",
        "conteudo": "Operator com loop de gestão autónoma Etsy. Marketeer delega acções ao Operator. CFO recebe dados de receita Etsy. Scout com missões C+D: monitorização de concorrência e pricing."
    },
    # ── 24 Julho: dia de integrações ─────────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-24",
        "titulo": "Memória semântica (Qdrant) nos 4 agentes em falta",
        "conteudo": "Qdrant integrado nos 4 agentes que faltavam (Coach, CFO, Operator, Creator). Agora todos os 8 agentes têm memória semântica. Collection por agente no Qdrant Cloud."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-24",
        "titulo": "Zep (memória temporal) + Firecrawl (scraping limpo)",
        "conteudo": "Zep integrado para memória temporal com TTL — memória que expira automaticamente. Firecrawl integrado para scraping de páginas web com output limpo (markdown). Ambos disponíveis como ferramentas do Creator e Scout."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-24",
        "titulo": "Fix — search routing — Perplexity só em Scout/Creator, DDG migrado",
        "conteudo": "Perplexity limitado a Scout e Creator (os que realmente precisam de síntese profunda). DDG migrado para duckduckgo-search (ddgs) — biblioteca nova. Evita uso desnecessário de créditos Perplexity."
    },
    # ── 25 Julho: cascade + diário ───────────────────────────────────────────
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-25",
        "titulo": "Creator.criar_email_purelymail — cria emails bcvertex.com via Playwright",
        "conteudo": "Creator pode criar emails @bcvertex.com autonomamente via Playwright no PurelyMail. Detecta login pelo conteúdo da página (não pela URL — fix necessário). planneratlas@bcvertex.com criado como primeiro teste."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-25",
        "titulo": "Pinterest service + Marketeer usa email PlannerAtlas",
        "conteudo": "Pinterest service criado para gestão de pins. Marketeer passou a usar planneratlas@bcvertex.com para outreach (não o email pessoal do Vasco). Separação clara entre identidades de negócio."
    },
    {
        "fonte": "Claude Code",
        "tipo": "Fix",
        "data_override": "2026-07-25",
        "titulo": "Fix — cascade pesquisa por ordem (Tavily no fim — limite atingido)",
        "conteudo": """Tavily atingiu o limite mensal de pesquisas. Fix: reordenar cascade.
Ordem antiga: Tavily→Exa→Perplexity→DDG
Ordem nova: Exa→Perplexity→DDG→Tavily (Tavily como último recurso)
DDG garantido como fallback final sempre disponível."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-25",
        "titulo": "Cascade de pesquisa por agente — AGENT_CASCADE dict",
        "conteudo": """Sistema de cascade de pesquisa individual por agente implementado em tools.py.
Cada agente tem a sua lista ordenada de ferramentas:
- CEO: exa→tavily→perplexity→ddg
- Scout: perplexity_pro→exa→tavily→ddg
- Coach: ddg→exa (sem créditos caros para notícias)
- CFO: perplexity→exa→ddg
- Creator: perplexity_reasoning→exa→ddg
- Marketeer: exa→tavily→ddg
- Operator: tavily→exa→ddg
- Solver: exa→perplexity_reasoning→ddg

Fallback silencioso entre ferramentas. Queries simples (tempo, hora, definições) vão directo para DDG sem consumir créditos. Falhas inesperadas notificam o Solver via memory/search_errors.json."""
    },
    {
        "fonte": "Claude Code",
        "tipo": "Deploy",
        "data_override": "2026-07-25",
        "titulo": "Diário Morgan — log cronológico completo no Notion",
        "conteudo": """Sistema de logging cronológico criado no Notion.
Componentes:
1. diario_log() em notion_service.py — função central de logging
2. Página raiz "Morgan — Diário" + base de dados com campos Fonte/Tipo/Data
3. Hook Stop em .claude/settings.json — regista sessão ao terminar
4. scripts/claude_session_log.jsonl — log intermédio durante sessão
5. scripts/notion_session_end.py — flush do log ao terminar
6. scripts/claude_log.py — CLI para registar acções manualmente

Fontes: Claude Code, CEO, Scout, Coach, CFO, Creator, Marketeer, Operator, Solver
Tipos: Decisão, Acção, Fix, Briefing, Conversa, Erro, Sessão, Deploy

Objectivo: registo histórico completo de tudo o que acontece no sistema — tanto pelo Claude Code como pelos agentes Morgan."""
    },
]

print(f"A inserir {len(entradas)} entradas históricas no Diário Morgan...")
print()

sucesso = 0
falha = 0

for i, e in enumerate(entradas):
    try:
        # nota: diario_log não suporta data_override — insere com data de hoje
        # mas o título e conteúdo identificam claramente a data histórica
        titulo = e.get("titulo", "")
        if e.get("data_override"):
            titulo = f"[{e['data_override']}] {titulo}"

        diario_log(
            fonte=e["fonte"],
            tipo=e["tipo"],
            conteudo=e["conteudo"],
            titulo=titulo
        )
        print(f"  ✓ [{i+1:02d}] {titulo[:70]}")
        sucesso += 1
    except Exception as ex:
        print(f"  ✗ [{i+1:02d}] ERRO: {e.get('titulo', '?')[:50]} — {ex}")
        falha += 1

print()
print(f"Concluído: {sucesso} entradas inseridas, {falha} falhas.")

# Registar o próprio script como acção
if sucesso > 0:
    try:
        diario_log(
            "Claude Code",
            "Sessão",
            f"Script retroativo executado: {sucesso} entradas históricas inseridas no Diário Morgan cobrindo todo o projecto desde Julho 2026 (W26 até W30).",
            titulo="[2026-07-25] Preenchimento retroativo do Diário Morgan"
        )
    except Exception:
        pass
