---
name: newsletter-brief
description: Brief técnico completo para o Creator montar The AI Pulse (Beehiiv newsletter)
metadata:
  type: project
---

# The AI Pulse — Brief Técnico para o Creator

**Tipo:** Newsletter faceless automatizada  
**Niche:** AI tools & productivity para founders (EN)  
**Mercado:** US/UK/CA (anglofonico — CPM $15-40, open rates B2B 40%+)  
**Plataforma:** Beehiiv  
**Agente responsável:** `newsletter_agent.py`

## Estado actual

- `newsletter_agent.py` criado ✅
- Negócio registado em `sistema_estado.json` ✅
- Operator e Marketeer actualizados ✅
- **Beehiiv account: PENDENTE (acção manual do Vasco)**

## Passos de setup (por ordem)

### 1. Vasco cria conta Beehiiv (manual — 5 min)
- Aceder a beehiiv.com
- Registar com morgan@bcvertex.com
- Criar publicação: nome "The AI Pulse", slug "ai-pulse"
- Settings → Integrations → API → gerar API key
- Adicionar ao `.env`:
  ```
  BEEHIIV_API_KEY=key_...
  BEEHIIV_PUB_ID=pub_...
  ```

### 2. Creator: testar newsletter_agent.py
```bash
cd ~/Morgan && source venv/bin/activate
python3 newsletter_agent.py
# Deve mostrar "✅ Setup completo" e stats reais
```

### 3. Creator: integrar ciclo_semanal_automatico() no desktop_server.py
- Adicionar ao scheduler do CEO (domingo 18h — antes do briefing das 20h)
- Código a adicionar no agendamento:
  ```python
  # Domingo 18h — ciclo newsletter
  if agora.weekday() == 6 and agora.hour == 18 and agora.minute == 0:
      from newsletter_agent import ciclo_semanal_automatico
      resultado = ciclo_semanal_automatico()
      # O rascunho criado no Beehiiv aguarda aprovação do Vasco
  ```

### 4. Marketeer: estratégia de crescimento 0→1k subs

**Fase 1 (0-100 subs) — SEO orgânico puro:**
- Criar 10 artigos "best AI tools for [niche]" no Beehiiv Blog (indexado pelo Google)
  - "Best AI tools for solopreneurs 2026"
  - "Best AI writing tools for founders"
  - "Free AI tools that replaced $500/month subscriptions"
- Cada artigo termina com CTA para subscrever a newsletter

**Fase 2 (100-1k subs) — Beehiiv Recommendations:**
- Activar Beehiiv Recommendations (pagar $0.50-2 por sub recomendado por outras newsletters)
- Budget inicial: $50/mês → estima 25-100 subs qualificados

**Fase 3 (1k+ subs) — Monetização:**
- Activar Beehiiv Ad Network (automatica, sem vendas)
- Receita estimada: $15-40 CPM → $15-40/1k views/edição
- 1k subs × 40% open rate = 400 views → ~$6-16/edição = ~$24-64/mês inicialmente

## Projecções financeiras (para o CFO)

| Milestone | Timeline | Receita estimada |
|---|---|---|
| 0 subs | Agora | €0 |
| 100 subs | 2-3 meses | €0 (sem ads) |
| 1.000 subs | 6-9 meses | ~€30-80/mês (Beehiiv Ads) |
| 5.000 subs | 12-18 meses | ~€150-400/mês (Ads + Boosts) |
| 10.000 subs | 18-24 meses | ~€500-1.500/mês (sponsors directos) |

Caminho para €10k/mês: ~100k subs (realista via SEO+Boosts em 3-4 anos, acelerado com Boosts pagos)

## Custos operacionais

- Beehiiv: €0 (free até 2.500 subs) → €39/mês depois
- Claude API (curadoria semanal): ~$0.10/semana
- **Total setup: ~€0**

## Ficheiros relevantes

- `newsletter_agent.py` — agente principal
- `memory/newsletter_state.json` — estado persistente (auto-criado)
- `sistema_estado.json` → `negocios.newsletter_ai_pulse`
