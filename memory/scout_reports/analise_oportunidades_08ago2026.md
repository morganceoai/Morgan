# Análise de Oportunidades BCVertex — 8 Agosto 2026

**Objectivo:** €10.000/mês rendimento passivo
**Contexto:** Etsy PlannerAtlas 0 vendas, trading activo 277 USDT, Mac Mini 24/7, stack Python/Playwright/Anthropic

---

## PARTE 1 — Scout: Novas Oportunidades

### 1. Templates Notion para PMEs portuguesas / brasileiras
**O que é:** Pack de templates Notion para gestão de negócio (CRM simples, gestão de projectos, finanças pessoais) com instruções em PT-BR. Vende em Gumroad + ko-fi.
- **Esforço:** 1 semana (criar 5-8 templates, landing page simples)
- **Potencial mensal:** €300-800 (mercado PT/BR pouco explorado no Notion marketplace)
- **Prazo para 1ª receita:** 2-3 semanas
- **Diferenciador:** tudo em PT-BR, documentação em vídeo curto (Loom), preço €12-25/pack
- **Risco:** Baixo — sem dependência de plataforma externa dominante

### 2. Micro-SaaS: Relatórios automáticos de SEO Etsy para vendedores PT/BR
**O que é:** Ferramenta que analisa uma loja Etsy e gera relatório PDF de SEO + recomendações em português. Subscrição €9/mês ou relatório avulso €15.
- **Esforço:** 2-3 semanas (Playwright scraping, LLM para análise, WeasyPrint para PDF)
- **Potencial mensal:** €500-2.000 (10-200 clientes)
- **Prazo para 1ª receita:** 3-4 semanas
- **Diferenciador:** único serviço em PT, usa stack que já tens (Playwright + Anthropic)
- **Risco:** Médio — Etsy pode mudar DOM; escalabilidade limitada sem API oficial

### 3. Agente IA de outreach para coaches/formadores PT
**O que é:** Serviço mensal onde o Morgan envia outreach semi-automático (email/Instagram DM) em nome de coaches ou formadores para captar clientes. Fee €200-400/mês por cliente.
- **Esforço:** 3-4 semanas (templates, Playwright automação, dashboard simples)
- **Potencial mensal:** €1.000-3.000 (5-10 clientes B2B)
- **Prazo para 1ª receita:** 4-6 semanas (ciclo de venda B2B mais longo)
- **Diferenciador:** personalização real via LLM, resultados mensuráveis
- **Risco:** Médio-Alto — dependência de clientes, risco de spam/bloqueio

### 4. Pack de prompts premium para futebol / análise desportiva
**O que é:** Prompt packs para treinadores, scouts e analistas (Gumroad). Inclui prompts para análise de vídeo, relatórios de adversário, fichas de scouting.
- **Esforço:** 3-5 dias (escrever, formatar, criar landing)
- **Potencial mensal:** €150-500
- **Prazo para 1ª receita:** 1-2 semanas
- **Diferenciador:** Vasco tem credibilidade real (treinador Moreirense) — authority marketing
- **Risco:** Muito baixo — esforço mínimo, sem infra

### 5. Relatórios de mercado IA automatizados (nicho B2B PT/BR)
**O que é:** Relatório semanal/mensal sobre mercado específico (ex: imobiliário Lisboa, startups PT) gerado pelo Scout/Morgan e vendido em subscrição ou avulso.
- **Esforço:** 2 semanas (Exa + Perplexity + template PDF)
- **Potencial mensal:** €400-1.500 (nicho PMEs, investidores)
- **Prazo para 1ª receita:** 3 semanas
- **Diferenciador:** automação real com dados frescos, PT-PT, custo de produção próximo de zero
- **Risco:** Baixo — produto escalável, sem dependência de plataforma

---

## PARTE 2 — Etsy PlannerAtlas: Estado e Melhorias

### Diagnóstico (dados reais)
- **0 vendas, €0 receita** desde criação (~05/08/2026)
- `listings_activos: 0` no patlas_state.json — **crítico: os listings podem não estar activos**
- `etsy_configurado: false` — OAuth Etsy pendente, sem acesso a dados reais de views/CTR
- Análise de ontem (Scout Missão C) confirma: 61 listings genéricos, score 2/10

### O que está a falhar
1. **OAuth Etsy não está configurado** — Morgan não consegue monitorizar nem optimizar autonomamente. Primeira prioridade técnica.
2. **Listings podem estar desactivados** (listings_activos: 0) — verificar manualmente no Etsy dashboard.
3. **Posicionamento genérico** — "digital planner" competindo com 700k+ listings sem histórico de vendas = invisível.
4. **Mockups fracos** — CTR depende 80% da imagem principal. Sem Canva/mockup profissional não há cliques.
5. **Sem tráfego externo** — Etsy só premeia lojas que já têm tráfego fora da plataforma.

### Melhorias concretas (por prioridade)

**Imediato (esta semana):**
- Confirmar que os 24 listings estão activos no painel Etsy
- Corrigir OAuth (`python etsy_service.py --setup`) para Morgan monitorizar
- Identificar 2-3 listings com melhor potencial e refazer thumbnail (mockup iPhone/iPad estilo lifestyle)

**Títulos:** Mudar de "Digital Weekly Planner PDF" para padrões tipo:
- "ADHD Daily Planner | Undated Digital Planner | GoodNotes + iPad | Printable PDF"
- "Budget Planner for Couples 2026 | Monthly Expense Tracker | Digital Download"

**Preço:** Subir os nichos profissionais de €7.99 para €12-17. Manter apenas 1-2 listings a €4.99 como "entrada".

**Tags:** 13 tags, todas específicas. Usar ferramentas de autocomplete do Etsy para nichos com <50k resultados.

### Estratégia de Ads
- **Budget inicial:** $1-2/dia por listing testado (máx $20 total para teste)
- **Targeting:** Etsy Ads só funciona quando o listing já tem bom CTR orgânico. Com 0 reviews, ROI negativo.
- **Recomendação:** NÃO activar ads ainda. Primeiro: 1ª venda orgânica (pode ser a preço reduzido ou via amigo/teste). Com 1 review, os ads passam a fazer sentido.
- **Timeline realista para 1ª venda:** 3-6 semanas com Pinterest activo. 8-12 semanas só com SEO orgânico Etsy.

### Upsell/Bundle rápido
- **Bundle "Starter Pack"** (3 planners complementares a €17.99 vs €24 individuais) — cria em 1 dia
- **Versão premium** com personalização nome/cor: cobrar +€5, entregar manual (1-2h trabalho)
- **Add-on digital:** guia de uso (PDF 5 páginas) grátis com qualquer compra — aumenta perceived value

---

## PARTE 3 — Pulser: Activar para Receita

### Estado actual
Pulser está idle. Não há registo de actividade em scout_state.json. Zero acções de marketing/publishing em curso.

### O que o Pulser devia estar a fazer AGORA

**Pinterest (maior ROI para Etsy):**
- 1 pin/dia por nicho principal (3-4 pins/dia total)
- Pins para boards temáticos: "ADHD Planners", "Digital Planning iPad", "Budget Planner Ideas"
- Formato: imagem mockup lifestyle 1000x1500 + título keyword-rich + link directo para listing
- Custo: €0 — Playwright automação já disponível

**SEO content (tráfego orgânico Google):**
- 2 artigos/semana num blog simples (pode ser Notion public page ou substack gratuito)
- Tema: "How to use digital planners for ADHD", "Best GoodNotes templates 2026"
- Cada artigo → link para listing Etsy → sinal backlink + Google discovery

**Outreach automático:**
- Identificar 20 contas Pinterest/Instagram no nicho (produtividade, planning, ADHD)
- DM simples: "Tenho um planner que os teus seguidores podem gostar — posso enviar grátis para review?"
- Meta: 2-3 micro-influencers com reviews = primeiras vendas + social proof

### Plano 30 dias Pulser → Tráfego Etsy

| Semana | Acção Pulser | Meta |
|--------|-------------|------|
| 1 | Setup Pinterest: criar boards, primeiros 10 pins | 100 impressões/dia |
| 2 | Aumentar para 1 pin/dia, iniciar outreach (10 contas) | 300 impressões/dia, 1ª resposta |
| 3 | Publicar 2 artigos SEO, pins com links article→listing | 1ª venda ou review grátis |
| 4 | Analisar o que funcionou, dobrar no melhor canal | 2-3 vendas acumuladas |

### Outras plataformas além do Etsy

| Plataforma | Acção | Esforço |
|-----------|-------|---------|
| **Gumroad** | Upload dos mesmos ficheiros, preço igual | 2h setup |
| **Ko-fi** | Loja + subscrição "Planning Bundle" mensal €5 | 1h setup |
| **Creative Market** | Aplicação + upload (aprovação demora 1-2 semanas) | 3h |
| **Payhip** | Zero taxas fixas, simples | 1h setup |

**Recomendação:** Começar com Gumroad (imediato, zero esforço) e Ko-fi como backup. Creative Market a seguir — tem audiência própria e premeia design quality.

---

## PARTE 4 — Quick Wins: Top 5 nos Próximos 30 Dias

Ordenados por impacto esperado:

### #1 — Corrigir OAuth Etsy + verificar listings activos
**Impacto:** Desbloqueador de tudo. Sem isso Morgan não monitoriza, não optimiza, não sabe o que está a acontecer.
**Esforço:** 1-2h (`python etsy_service.py --setup` + ETSY_KEYSTRING)
**ROI:** Indirecto mas crítico — é o único bloqueio técnico à optimização autónoma.

### #2 — Activar Pulser no Pinterest (3 pins/dia)
**Impacto:** Pinterest é o canal #1 de tráfego externo para Etsy. Pins têm vida útil longa (meses). Investimento de tempo = retorno composto.
**Esforço:** 2-3 dias para setup + automação Playwright
**ROI:** Primeiros cliques em 1-2 semanas, primeiras vendas em 3-4 semanas.

### #3 — Lançar loja Gumroad com os mesmos produtos
**Impacto:** Duplicar presença em 2h. Gumroad tem discovery próprio e zero comissão fixa.
**Esforço:** Upload de ficheiros + descrições copiadas do Etsy
**ROI:** Potencial €50-200/mês adicional sem trabalho extra.

### #4 — Criar pack de prompts de futebol (Gumroad €15-25)
**Impacto:** Produto único com credibilidade real de Vasco. Audiência nicho mas disposta a pagar.
**Esforço:** 3-5 dias de escrita
**ROI:** Primeiras vendas em 2 semanas. Escalável com afiliados/coaches.

### #5 — Refazer mockups dos 3 melhores listings (Canva MCP)
**Impacto:** CTR é o multiplicador de tudo — bom mockup = 3-5x mais cliques para o mesmo SEO.
**Esforço:** 1-2h por listing (Canva MCP já disponível)
**ROI:** Aumento de CTR visível em 1-2 semanas após publicação.

---

## Resumo Executivo

**Situação:** BCVertex está em €0 rendimento passivo. A PlannerAtlas tem produto mas zero distribuição e problemas técnicos (OAuth, listings possivelmente inactivos). O Pulser não está a trabalhar.

**Problema raiz:** Falta de tráfego externo + posicionamento genérico + bloqueios técnicos por resolver.

**Prioridade máxima (hoje/amanhã):**
1. Corrigir OAuth Etsy
2. Activar Pulser com Pinterest
3. Lançar Gumroad

**Horizonte realista:**
- 1ª venda Etsy: 3-4 semanas com Pinterest activo
- €100/mês: 6-8 semanas
- €500/mês: 3-4 meses (requer niching + múltiplas plataformas)
- €10.000/mês: requer escala via SaaS ou serviços B2B (horizonte 12-18 meses)

**Próxima oportunidade a avaliar:** Micro-SaaS de relatórios SEO Etsy em PT/BR — baixo risco, alta diferenciação, usa stack existente.

---
*Gerado por Scout — Morgan/BCVertex — 8 Agosto 2026*
