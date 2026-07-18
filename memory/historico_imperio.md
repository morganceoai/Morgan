# Histórico do Império — BCVertex
*Arquivo de ações passadas. Consultado pelos agentes apenas quando necessário.*

## 2026-W26 (01–07 Julho 2026)

### Infraestrutura
- 05/07: Scout melhorado — 7 ferramentas, Opus 4.8, queries cirúrgicas, síntese cruzada
- 06/07: Solver v2 LangGraph implementado — 5 nós, confiança por passo, track record
- 06/07: Sistema de autonomia CEO testado (3/3 testes OK)
- 06/07: Optimização de custos — sonnet em vez de opus, threshold 3 erros, prompt caching
- 06/07: Railway auto-deploy corrigido após migração de conta
- 07/07: Interface desktop atualizada com dados reais do Scout
- 07/07: PWA iPhone criada (pwa/ directory)
- 07/07: Creator Agent estruturado com domain knowledge registry e ciclos de vida
- 07/07: Morgan Coach criado — análise tática, routing no Telegram, esfera verde na interface

### Scout — Semana 2026-W26
Primeiro relatório Scout executado. 5 oportunidades identificadas:
1. Directório de nicho PT/BR monetizado — €1-3k/mês, baixo risco
2. Produtos digitais/templates em PT — €500-5k/mês, muito baixo risco
3. Relatórios táticos automáticos PT/ES — €500-3k/clube, pivô futebol
4. Micro-SaaS vertical de nicho — €5-50k/mês, risco médio
5. Compra de blog/site com receita — requer capital 10-20k€

Nenhuma oportunidade aprovada pelo Vasco ainda.

### Decisões de arquitectura (permanentes)
- Polling em vez de webhooks — estável, sem custo extra, decisão de 05/07
- Réplica única no Railway — evita conflitos Telegram, decisão de 05/07
- Mem0 não-crítico — erros ignorados pelo Solver, decisão de 06/07
- Briefings cancelados pelo Vasco — Morgan só envia informação quando pedido, decisão de 07/07
- Scout pesquisa em inglês primeiro, PT/BR como vantagem de execução — decisão de 07/07

