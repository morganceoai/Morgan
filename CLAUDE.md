# Morgan — Contexto para Claude Code

Este ficheiro é carregado automaticamente em cada sessão. Lê-o na íntegra antes de qualquer trabalho.

---

## O que é o Morgan

Morgan é o assistente pessoal de IA do Vasco Botelho da Costa. **NÃO é apenas um bot de Telegram** — o Telegram é um canal de acesso, não a interface principal. A interface principal é um avatar a pulsar (ainda por construir). No futuro: PWA, widget iOS, Dynamic Island.

Morgan é o "braço direito" do Vasco. A última decisão é sempre do Vasco. Morgan sugere, analisa, e executa o que for autorizado.

---

## Quem é o Vasco

- Treinador de futebol no Moreirense FC (Portugal)
- Objetivo: €10.000/mês de rendimento passivo
- Email pessoal: vascobotelhodacosta@gmail.com
- Email de infraestrutura do Morgan: morganceoai@gmail.com
- Prefere respostas diretas, sem rodeios
- Fala português europeu (PT-PT)

---

## Arquitetura técnica

| Componente | Detalhe |
|---|---|
| Linguagem | Python 3.12, venv em `~/Morgan/venv` |
| Deploy | Railway.app (Hobby $5/mês) — auto-deploy no push para GitHub |
| GitHub | github.com/morganceoai/Morgan |
| LLM | Anthropic Claude `claude-sonnet-4-6` |
| Telegram | python-telegram-bot |
| Voz (STT) | Deepgram — transcreve áudios enviados pelo Vasco |
| Voz (TTS) | ElevenLabs `eleven_multilingual_v2` — responde em áudio PT-PT |
| Pesquisa web | Tavily (conta morganceoai@gmail.com) |
| Futebol | API Football |
| Scout | Product Hunt API (Bearer token), HN Firebase API, pytrends |

### Variáveis de ambiente (.env e Railway)
`ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TAVILY_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `DEEPGRAM_API_KEY`, `API_FOOTBALL_KEY`, `PRODUCT_HUNT_TOKEN`

---

## Ficheiros principais

| Ficheiro | Função |
|---|---|
| `telegram_bot.py` | Ficheiro principal — bot, heartbeat, Scout, comandos |
| `tools.py` | Todas as ferramentas disponíveis ao Morgan |
| `scout_memory.py` | Memória persistente do Scout (JSON) |
| `memory_store.py` | Memória de factos do Morgan (factos.md) |
| `conversation_store.py` | Histórico de conversa por utilizador |
| `voice.py` | Utilitários de voz |
| `heartbeat.py` | Lógica de heartbeat |
| `morgan.py` | Entry point alternativo |

### Ficheiros de estado (em `~/Morgan/memory/`)
- `scout_memoria.json` — histórico de oportunidades do Scout
- `factos.md` — memória de factos do Morgan
- `heartbeat_state.json` — estado do heartbeat e briefings
- `noticias_enviadas.json` — deduplicação de notícias
- `audit.log` — log de ações

---

## O que está implementado (100% ativo)

### Conversação
- Responde a mensagens de texto no Telegram
- Responde a mensagens de voz (Deepgram transcreve → Claude processa → ElevenLabs responde em áudio)
- Histórico de conversa por utilizador
- Sistema de confirmação antes de ações sensíveis (`pedir_confirmacao`)

### Briefings automáticos
- **7h e 20h** todos os dias (exceto horas de silêncio: 23h–7h)
- Conteúdo: meteo, notícias Moreirense FC, resultados recentes, próximos jogos, menções ao nome do Vasco
- Sem repetições (deduplicação por hash)

### Monitorização de nome
- `monitorizar_nome()` pesquisa "Vasco Botelho da Costa" em 10 plataformas via Tavily: Reddit, YouTube, X/Twitter, Facebook, Instagram, TikTok, LinkedIn, Transfermarkt, ZeroZero, web geral
- Corre nos briefings das 7h e 20h — **NÃO tem loop separado de 2 em 2 horas**

### Morgan AI Scout
- Corre **todos os domingos às 20h** (integrado no heartbeat)
- Usa **7 ferramentas** em cada relatório:
  1. `product_hunt_trending` — produtos IA mais votados (API GraphQL com Bearer token)
  2. `hacker_news_trending` — HN Firebase API, filtra posts com score > 50 e keywords IA/negócio
  3. `reddit_trending` — via Tavily com site:reddit.com (API direta bloqueada com 403)
  4. `scout_oportunidades` — 10 queries Tavily sobre mercados PT/BR/ES, SaaS, IA, rendimento passivo
  5. `indiehackers_trending` — via Tavily, dados reais de receita de fundadores
  6. `google_trends` — pytrends, valida crescimento das top 3 oportunidades
  7. `monitorizar_oportunidades_aprovadas` — pesquisa aprofundada de oportunidades aprovadas pelo Vasco (só corre se existirem aprovadas)
- Memória persistente: `scout_memoria.json` guarda histórico semanal, oportunidades recorrentes, aprovações
- Extrai bloco JSON do relatório, chama `registar_oportunidades()`, remove JSON antes de enviar ao Vasco
- Vasco pode aprovar oportunidades dizendo "aprova [nome]" → Morgan chama `aprovar_oportunidade_scout()`

### Comandos Telegram
- `/status` — estado atual (ativo/pausado, horas silêncio, modelo, hora)

### Controlos de comportamento
- Horas de silêncio configuráveis (padrão 23h–7h)
- Pode ser pausado/despausado
- Modelo configurável

---

## O que NÃO está implementado ainda

| Item | Notas |
|---|---|
| Interface avatar (PWA) | Eixo B Fase 3 — a interface principal visual |
| Widget iOS / Dynamic Island | Futuro — "virar o ecrã e ele estar logo ali" |
| Multi-agente (CrewAI/AutoGen) | Fase 4 — Morgan CEO + sub-Morgans |
| X API | $100/mês — ativar quando houver receita |
| Perplexity API | Pesquisa mais profunda — ativar quando houver receita |
| Google Search API | Cobertura máxima — ativar quando houver receita |

---

## Hierarquia de negócios (Eixo C)

```
Vasco (decisão final)
  └── Morgan CEO (braço direito)
        ├── Morgan AI Scout  ← primeiro e único agente definido
        └── Morgan [Negócio X], [Y]...  ← definidos pelo Scout com dados
```

Os negócios **não estão definidos à partida**. O Scout descobre quais os melhores com base em dados reais. O futebol foi um exemplo em conversa — pode ou não entrar no top.

Marcos de rendimento passivo: €1k → €3k → €10k → €25k → €50k → sem teto.

---

## Contas de infraestrutura

| Serviço | Email | Estado |
|---|---|---|
| GitHub | morganceoai@gmail.com | ✅ migrado |
| Railway | morganceoai@gmail.com | ✅ migrado |
| ElevenLabs | morganceoai@gmail.com | ✅ migrado |
| Tavily | morganceoai@gmail.com | ✅ migrado |
| Product Hunt | morganceoai@gmail.com | ✅ criado diretamente |
| Deepgram | vascobotelhodacosta@gmail.com | ⏳ migrar quando $200 crédito acabar |
| API Football | (bloqueado) | ⏳ migrar quando subscrição acabar |
| Twilio | — | ❌ cancelado |
| ngrok | — | ❌ cancelado |

---

## Preferências de trabalho do Vasco

- Respostas diretas e curtas — sem rodeios
- Nunca implementar monitorização com loops frequentes sem confirmação (ex: foi pedido para remover loop de 2 em 2 horas para menções de nome)
- A última decisão é sempre do Vasco — Morgan sugere, Vasco decide
- Guardar em memória tudo o que for relevante ao longo da conversa, sem esperar que Vasco peça
- Quando há dúvida sobre o estado do código, **ler o ficheiro antes de assumir**
