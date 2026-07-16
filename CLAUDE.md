# Morgan — Contexto para Claude Code

Este ficheiro é carregado automaticamente em cada sessão. Lê-o na íntegra antes de qualquer trabalho.
Lê também `memory/MEMORY.md` e os ficheiros de memória relevantes antes de começar.

---

## O que é o Morgan

Morgan é o assistente pessoal de IA do Vasco Botelho da Costa e o CEO do império BC Industries.
**O Telegram foi removido.** A interface principal é a PWA em morgan.bcvertex.com (ainda a ser construída).
Morgan é o "braço direito" do Vasco. A última decisão é sempre do Vasco.

---

## Quem é o Vasco

- Treinador de futebol no Moreirense FC (Portugal)
- Objetivo: €10.000/mês de rendimento passivo via BC Industries
- Email pessoal: vascobotelhodacosta@gmail.com
- Email sistema: morgan@bcvertex.com | vasco@bcvertex.com (PurelyMail, bcvertex.com)
- **Fala e prefere respostas em PT-PT**
- Prefere respostas directas e curtas — sem rodeios, sem sumários no final
- Quando apresentas opções, **máximo 3**, com recomendação clara
- Confirmar abordagem antes de implementar código novo — não implementar sem alinhamento
- A última decisão é sempre do Vasco

---

## Arquitectura actual (Julho 2026)

| Componente | Detalhe |
|---|---|
| Linguagem | Python 3.12, venv em `~/Morgan/venv` |
| Deploy | **Mac Mini** (ssh vasco@mac-mini) — git pull via SSH; Railway CANCELADO |
| GitHub | github.com/morganceoai/Morgan |
| CI/CD | GitHub Actions (secrets pendentes: MAC_MINI_HOST, MAC_MINI_USER, MAC_MINI_SSH_KEY) |
| LLM principal | `claude-sonnet-4-6` (rotina); `claude-opus-4-8` para decisões estratégicas |
| LLM router | `claude-haiku-4-5-20251001` — classifica intent (cfo/coach/marketeer/etc.) |
| Interface | PWA morgan.bcvertex.com (em construção); voz via ElevenLabs Conv. AI (migração pendente) |
| Voz STT | Deepgram (PT-PT) |
| Voz TTS | ElevenLabs (voz Morgan Freeman clonada) |
| Browser automation | Playwright headless (Mac Mini) — agentes usam, independente do browser do Vasco |
| Email IMAP | PurelyMail — imap.purelymail.com:993 |
| Pesquisa web | Tavily + Exa (a integrar) |
| Memória | Mem0 Cloud (MEM0_API_KEY activo) + Qdrant Cloud (activo) |
| Observabilidade | LangSmith (LANGCHAIN_API_KEY activo — activar SENTRY_DSN) |
| Futebol | API Football + StatsBomb Open Data |
| Scout | Product Hunt API, HN Firebase API, pytrends |
| Trading | CCXT + Binance (100 USDT BTC/USDT activo, BINANCE_TESTNET=false) |
| Etsy | PlannerAtlas (8 listings activos, etsy OAuth pendente) |

---

## Os 8 Agentes

| Agente | Ficheiro | Responsabilidade |
|---|---|---|
| CEO | `desktop_server.py` | Orquestra, briefings, decisões, push ao Vasco |
| Scout | `scout_agent.py` | Dom 20h: oportunidades de negócio; Qua 20h: melhorias ao sistema |
| Coach | `coach_agent.py` | Exclusivamente futebol — Moreirense, análise, scouting |
| CFO | `cfo_agent.py` | Exclusivamente trading e finanças — nunca misturar com Coach |
| Creator | `creator_agent.py` | Cria e faz deploy de novos agentes/ferramentas |
| Solver | `solver_agent.py` | Debugging, erros, LangGraph, manutenção |
| Operator | `operator_agent.py` | Gestão de negócios activos (Etsy, plataformas) |
| Marketeer | `marketeer_agent.py` | SEO Etsy, Pinterest, conteúdo, outreach |

**Regra de ouro dos briefings:** CEO orquestra UMA mensagem. Coach = futebol apenas. CFO = trading apenas. Nunca misturar áreas.

---

## Ficheiros principais

| Ficheiro | Função |
|---|---|
| `desktop_server.py` | Servidor principal — heartbeat, briefings, Scout, aprovações |
| `tools.py` | Ferramentas do CEO |
| `sistema_service.py` | Fonte de verdade — agentes, negócios, contas Zoho |
| `automation_service.py` | Playwright + IMAP PurelyMail |
| `approval_pipeline.py` | Pipeline paralela de aprovação de oportunidades |
| `scout_memory.py` | Memória persistente do Scout |
| `memory_store.py` | Factos do Morgan (factos.md) |

### Estado em `~/Morgan/memory/`
- `sistema_estado.json` — fonte de verdade: 8 agentes + negócios + contas
- `scout_memoria.json` — histórico Scout
- `heartbeat_state.json` — estado briefings
- `audit.log` — log de acções

---

## Briefings e horários automáticos

- **7h diário** — CEO: Coach (futebol 2 linhas) + CFO (trading 1 linha) + Scout (oportunidade top) → 1 push
- **22h diário** — CEO: relatório completo (todos os agentes, erros, sistema)
- **Domingo 20h** — Scout Mission A: oportunidades de negócio
- **Quarta 20h** — Scout Mission B: melhorias ao ecossistema de agentes
- **Silêncio:** 23h–7h

---

## Pipeline de aprovação de oportunidades

Quando Scout detecta oportunidade:
1. Execução paralela: Creator (plano técnico) + Marketeer (estratégia) + Solver (riscos) + CFO (projecções)
2. CEO compila e envia briefing completo ao Vasco
3. Vasco diz "aprovo X" → `executar_oportunidade_aprovada()` → regista em `sistema_estado.json`
4. Vasco diz "rejeito X" → arquiva

---

## Contas de infraestrutura

| Serviço | Email | Estado |
|---|---|---|
| GitHub | morganceoai@gmail.com | ✅ |
| ElevenLabs | morganceoai@gmail.com | ✅ |
| Tavily | morganceoai@gmail.com | ✅ |
| Product Hunt | morganceoai@gmail.com | ✅ |
| PurelyMail | morgan@bcvertex.com | ✅ activo |
| Mem0 | — | ✅ activo (MEM0_API_KEY) |
| Qdrant | — | ✅ activo (QDRANT_URL) |
| Binance | — | ✅ live (100 USDT) |
| Etsy | — | ⏳ OAuth pendente (ETSY_KEYSTRING em falta) |
| Deepgram | vascobotelhodacosta@gmail.com | ⏳ migrar quando crédito acabar |
| Railway | — | ❌ cancelado |
| Telegram | — | ❌ removido |

---

## O que NÃO está implementado ainda

| Item | Notas |
|---|---|
| PWA morgan.bcvertex.com | Interface visual principal — a construir |
| ElevenLabs Conversational AI | Substituir Hume EVI (PT-PT quebrado) — decisão tomada, não implementado |
| Etsy OAuth | ETSY_KEYSTRING em falta → `python etsy_service.py --setup` |
| GitHub Actions secrets | MAC_MINI_HOST, MAC_MINI_USER, MAC_MINI_SSH_KEY |
| Gmail outreach | GMAIL_OUTREACH_USER + GMAIL_OUTREACH_PASS |
| Sentry | Activar SENTRY_DSN (já no requirements.txt) |
| Widget iOS / Dynamic Island | Futuro |

---

## Preferências de trabalho do Vasco

- **Respostas em PT-PT**, directas e curtas — sem sumários no final, sem rodeios
- Quando há opções: **máximo 3**, com recomendação clara e o principal trade-off
- **Confirmar abordagem antes de implementar** — não avançar sem alinhamento
- **Nunca implementar loops frequentes** sem confirmação (ex: removido loop 2h para menções de nome)
- **Guardar em memória** tudo o que for relevante — não esperar que Vasco peça
- **Ler o ficheiro antes de assumir** — quando há dúvida sobre estado do código
- Para explorar questões abertas ("o que fazemos sobre X?"): resposta em 2-3 frases com recomendação, não plano completo
- Para tarefas simples: executar directamente sem narrar o processo
- Dar contexto rápido quando muda de direcção ou encontra algo importante — uma frase chega
