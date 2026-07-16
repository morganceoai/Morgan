# Graph Report - /Users/vascobotelhodacosta/Morgan  (2026-07-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 625 nodes · 1095 edges · 58 communities (35 shown, 23 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bccc3989`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- chat_with_morgan
- _heartbeat_loop
- creator_agent.py
- solver_graph.py
- desktop_server.py
- coach_agent.py
- operator_agent.py
- marketeer_agent.py
- mem0_service.py
- config_service.py
- automation_service.py
- cfo_agent.py
- _load
- generate_all_products.py
- Request
- voice_id.py
- tools.py
- run_desktop.py
- generate_all_mockups.py
- conversation_store.py
- dca_bot.py
- trading_bot.py
- approval_pipeline.py
- generate_planners.py
- generate_planners_ES.py
- generate_weekly_all_langs.py
- morgan_logging.py
- manifest.json
- conftest.py
- escalada_push
- chat_speak
- _chat_ceo
- listar_google_drive
- bot_multi_status
- get_agent
- transcribe_audio
- sw.js
- atualizar_estado_imperio
- classificacao_primeira_liga
- consultar_historico_imperio
- hacker_news_trending
- monitorizar_nome
- product_hunt_trending
- proximos_jogos
- reddit_trending
- scout_oportunidades
- solver_railway_logs
- solver_ler_ficheiro
- solver_verificar_saude
- solver_analisar_logs
- solver_git_diff
- solver_git_commit_push
- solver_railway_deploy
- solver_criar_ficheiro
- solver_executar_correcao
- resultados_recentes

## God Nodes (most connected - your core abstractions)
1. `chat_with_morgan()` - 22 edges
2. `_heartbeat_loop()` - 18 edges
3. `send_push()` - 17 edges
4. `_load()` - 15 edges
5. `_run_daily_report()` - 13 edges
6. `get_coach_reply()` - 12 edges
7. `_agora_lisboa()` - 11 edges
8. `_run_briefing()` - 11 edges
9. `SolverState` - 11 edges
10. `build_solver_graph()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `_heartbeat_loop()` --indirect_call--> `gerar_plano_semana_planneratlas()`  [INFERRED]
  desktop_server.py → creator_agent.py
- `_heartbeat_loop()` --indirect_call--> `reset_dca_daily_pnl()`  [INFERRED]
  desktop_server.py → dca_bot.py
- `_chat_ceo()` --indirect_call--> `mem0_add()`  [INFERRED]
  desktop_server.py → mem0_service.py
- `solver_run()` --indirect_call--> `run_solver()`  [INFERRED]
  desktop_server.py → solver_graph.py
- `_run_daily_report()` --indirect_call--> `_etsy_dados_reais()`  [INFERRED]
  desktop_server.py → operator_agent.py

## Import Cycles
- None detected.

## Communities (58 total, 23 thin omitted)

### Community 0 - "chat_with_morgan"
Cohesion: 0.05
Nodes (29): listar_agentes(), Lista todos os ficheiros de agente Python no projecto., chat_with_morgan(), _classificar_agente(), Usa Claude Haiku para classificar para qual agente encaminhar a mensagem., Alias público para o endpoint /api/solver/run., run_solver(), T1-T6 — Testes de agentes: resposta válida, sem exposição de erros, sem truncage (+21 more)

### Community 1 - "_heartbeat_loop"
Cohesion: 0.09
Nodes (44): _agora_lisboa(), _dedup_check(), _dedup_mark(), get_system_prompt(), _heartbeat_loop(), push_report_now(), push_test(), Força o relatório diário agora — para teste sem esperar as 22h. (+36 more)

### Community 2 - "creator_agent.py"
Cohesion: 0.07
Nodes (43): activar_sub_morgan(), avancar_fase(), construir_agente(), criar_sub_morgan(), deploy_agente(), escrever_agente(), gerar_codigo_agente(), gerar_conteudo_social_planneratlas() (+35 more)

### Community 3 - "solver_graph.py"
Cohesion: 0.13
Nodes (32): build_solver_graph(), _chamar_claude(), decide_apos_plano(), _escalar_claude_code(), _extrair_confianca(), _fixes_relevantes(), get_client(), _get_tools() (+24 more)

### Community 4 - "desktop_server.py"
Cohesion: 0.07
Nodes (21): bot_status(), elevenlabs_sentence(), get_activity(), get_agents(), get_history(), get_notifications(), get_reports(), _load_notifs() (+13 more)

### Community 5 - "coach_agent.py"
Cohesion: 0.11
Nodes (28): analisar_adversario(), _api_football_cached(), briefing_pre_jogo(), build_coach_system(), _chamar_claude_coach(), _fetch_moreirense_fixtures(), get_coach_reply(), _get_coach_tools() (+20 more)

### Community 6 - "operator_agent.py"
Cohesion: 0.12
Nodes (27): estado_para_operador(), get_api(), is_configured(), obter_listings(), obter_vendas(), Etsy API v3 — serviço OAuth2 para o Morgan Operator. Usa a biblioteca etsyv3 com, Texto formatado para o Operator usar no seu system prompt., Fluxo PKCE interactivo para obter tokens de acesso Etsy. (+19 more)

### Community 7 - "marketeer_agent.py"
Cohesion: 0.11
Nodes (24): analisar_etsy_nicho(), enviar_outreach_email(), get_marketeer_reply(), _load_state(), otimizar_listings_etsy(), _outreach_hoje(), pesquisar_leads(), pesquisar_pinterest() (+16 more)

### Community 8 - "mem0_service.py"
Cohesion: 0.15
Nodes (17): _contexto_para_hume(), Proxy WebSocket: browser → Deepgram Live API → browser com verificação de voz., Proxy WebSocket: browser → ElevenLabs Conversational AI → browser.     Áudio de, Constrói contexto completo para o Hume:     - Mem0: memórias de longo prazo (fac, Hume EVI + Claude — voz com emoção em tempo real., ws_convai(), ws_hume(), ws_transcribe() (+9 more)

### Community 9 - "config_service.py"
Cohesion: 0.21
Nodes (16): confianca_limiar(), get(), hora_silencio(), is_pausado(), load_config(), modelo(), pausar(), Serviço de configuração centralizado — lê/escreve config.yaml. Partilhado por de (+8 more)

### Community 10 - "automation_service.py"
Cohesion: 0.17
Nodes (15): criar_conta_plataforma(), _get_email_body(), _imap_connect(), instalar_playwright(), listar_emails_recentes(), _playwright_disponivel(), automation_service.py — browser automation e acesso a email Zoho.  Usa Playwrigh, Lista os N emails mais recentes — usado pelo CEO para dar contexto ao Vasco. (+7 more)

### Community 11 - "cfo_agent.py"
Cohesion: 0.19
Nodes (15): avaliar_risco_trading(), _build_cfo_system(), get_cfo_reply(), _load_reports(), _load_trading_state(), Morgan CFO — Agente financeiro do império BC Industries. Supervisiona: trading b, Relatório diário do CFO para o CEO., Resumo mensal de performance. (+7 more)

### Community 12 - "_load"
Cohesion: 0.21
Nodes (14): aprovar_oportunidade(), get_contexto_scout(), get_resumo_para_vasco(), _load(), Resumo do histórico do Scout para o Vasco consultar., Regista as oportunidades desta semana e actualiza o histórico.     Cada oportuni, Marca uma oportunidade como aprovada pelo Vasco para acompanhamento contínuo., Devolve o contexto acumulado para o Scout usar no relatório desta semana. (+6 more)

### Community 13 - "generate_all_products.py"
Cohesion: 0.38
Nodes (13): bg(), budget_overview(), budget_savings(), cover_page(), daily_page(), ftr(), habit_page(), hdr() (+5 more)

### Community 14 - "Request"
Cohesion: 0.14
Nodes (14): chat_endpoint(), chat_stream(), enroll_voice_endpoint(), push_subscribe(), Recebe chunks PCM acumulados e cria o perfil de voz do Vasco., Define o agente ativo via canvas click., Corre o Solver v2 (LangGraph) com um problema — endpoint de teste., Claude com streaming — tokens aparecem à medida que chegam. (+6 more)

### Community 15 - "voice_id.py"
Cohesion: 0.20
Nodes (13): voice_id_status(), ndarray, enroll_voice(), _get_encoder(), has_profile(), is_vasco(), load_profile(), _pcm_to_float() (+5 more)

### Community 16 - "tools.py"
Cohesion: 0.19
Nodes (12): list_memory(), load_memory(), remove_fact(), save_fact(), indiehackers_trending(), Pesquisa no IndieHackers negócios reais com receita declarada pelos fundadores., Executa um comando de diagnóstico (read-only). Requer aprovação para comandos qu, Mostra os últimos commits do repositório para o Solver verificar o que foi deplo (+4 more)

### Community 17 - "run_desktop.py"
Cohesion: 0.16
Nodes (4): Api, get_screen_size(), Morgan Desktop — lançador da interface JARVIS no Mac. Corre: python3 run_desktop, Bridge JS → Python para controlo da janela.

### Community 18 - "generate_all_mockups.py"
Cohesion: 0.29
Nodes (11): add_vignette(), cast_shadow(), fit(), fit_text_font(), get_page(), load_background(), load_fonts(), make_linen() (+3 more)

### Community 19 - "conversation_store.py"
Cohesion: 0.30
Nodes (11): _file_load(), _file_save(), get_context_messages(), _headers(), load_history(), Histórico de conversa centralizado — Supabase. Telegram e Desktop partilham o me, Devolve as últimas `limit` mensagens em formato Claude (role/content).     Supab, save_message() (+3 more)

### Community 20 - "dca_bot.py"
Cohesion: 0.33
Nodes (11): get_dca_status(), get_exchange(), load_state(), pause_dca(), BC Industries — DCA Bot (SOL/USDT) Estratégia: Compra metade do capital disponív, reset_dca_daily_pnl(), resume_dca(), run_dca_cycle() (+3 more)

### Community 21 - "trading_bot.py"
Cohesion: 0.33
Nodes (11): _atr(), get_exchange(), get_supertrend_signal(), load_state(), pause_bot(), BC Industries — Trading Bot (Supertrend ATR10×3) Estratégia: Supertrend 4h, BTC/, Calcula sinal Supertrend. Devolve (signal, new_trend)., reset_daily_pnl() (+3 more)

### Community 22 - "approval_pipeline.py"
Cohesion: 0.35
Nodes (10): _analise_solver(), _ask(), executar_oportunidade_aprovada(), _plano_creator(), _plano_marketeer(), preparar_briefing_aprovacao(), _previsao_cfo(), approval_pipeline.py — pipeline de aprovação paralela de oportunidades.  Quando (+2 more)

### Community 23 - "generate_planners.py"
Cohesion: 0.56
Nodes (9): bg(), cover(), ftr(), habit(), hdr(), jahres(), monats(), notizen() (+1 more)

### Community 24 - "generate_planners_ES.py"
Cohesion: 0.56
Nodes (9): bg(), cover(), ftr(), habit(), hdr(), jahres(), monats(), notizen() (+1 more)

### Community 25 - "generate_weekly_all_langs.py"
Cohesion: 0.56
Nodes (9): bg(), cover(), ftr(), habit(), hdr(), jahres(), monats(), notizen() (+1 more)

### Community 26 - "morgan_logging.py"
Cohesion: 0.22
Nodes (9): bind_agent(), configure(), get_logger(), log_llm_call(), Morgan — logging estruturado + Sentry. Importar no início de qualquer módulo que, Configura structlog + Sentry. Chamado uma vez no startup do servidor., Retorna logger structlog (ou stdlib como fallback)., Bind do nome do agente ao contexto de logging para todas as chamadas seguintes. (+1 more)

### Community 27 - "manifest.json"
Cohesion: 0.20
Nodes (9): background_color, description, display, icons, name, orientation, short_name, start_url (+1 more)

### Community 28 - "conftest.py"
Cohesion: 0.20
Nodes (9): make_claude_response(), mock_api_football(), mock_claude(), mock_tavily(), Configuração global de testes do Morgan. Mocks determinísticos para Claude, Tavi, Cria um objecto de resposta Claude falso mas estruturalmente correcto., Mock do anthropic.Anthropic — evita chamadas reais e custos., Mock do TavilyClient — devolve resultados vazios por defeito. (+1 more)

### Community 29 - "escalada_push"
Cohesion: 0.33
Nodes (6): api_escalada(), escalada_push(), _handle_trading_result(), Envia push ao Vasco quando um agente tem confiança < 90% e precisa de decisão., Endpoint interno para agentes enviarem escaladas ao Vasco via push., Processa resultado de um ciclo de trading e envia push se necessário.

### Community 30 - "chat_speak"
Cohesion: 0.40
Nodes (5): barge_in(), chat_speak(), kill_player(), Claude → ElevenLabs frase-a-frase → SSE para estado em tempo real., Para o áudio imediatamente — chamado quando o utilizador começa a falar.

### Community 31 - "_chat_ceo"
Cohesion: 0.40
Nodes (5): _chat_ceo(), _chat_ceo_with_system(), CEO — chamada direta ao Claude com ferramentas., CEO com system prompt customizado (ex: Scout mode)., run_tool()

### Community 32 - "listar_google_drive"
Cohesion: 0.50
Nodes (4): listar_google_drive(), organizar_google_drive_sugestoes(), Lista ficheiros e pastas do Google Drive do Vasco.     Requer GOOGLE_SERVICE_ACC, Analisa o Google Drive e sugere organização em pastas por categoria.     Não mov

## Knowledge Gaps
- **10 isolated node(s):** `name`, `short_name`, `description`, `start_url`, `display` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_solver()` connect `chat_with_morgan` to `solver_graph.py`, `desktop_server.py`, `Request`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `send_push()` connect `_heartbeat_loop` to `desktop_server.py`, `escalada_push`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `pesquisar_web()` connect `chat_with_morgan` to `tools.py`, `_heartbeat_loop`, `creator_agent.py`, `desktop_server.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `_heartbeat_loop()` (e.g. with `gerar_plano_semana_planneratlas()` and `reset_dca_daily_pnl()`) actually correct?**
  _`_heartbeat_loop()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `short_name`, `description` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `chat_with_morgan` be split into smaller, more focused modules?**
  _Cohesion score 0.05187074829931973 - nodes in this community are weakly interconnected._
- **Should `_heartbeat_loop` be split into smaller, more focused modules?**
  _Cohesion score 0.08695652173913043 - nodes in this community are weakly interconnected._