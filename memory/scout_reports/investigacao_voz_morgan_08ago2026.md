# Investigação Voz Morgan — 8 Agosto 2026

**Objetivo:** Encontrar a arquitectura de voz ideal para o Morgan — natural, emocional, estilo "irmão", PT-PT.

---

## 1. STT — Speech-to-Text em PT-PT

### Comparação directa

| Serviço | PT-PT | Latência streaming | Custo/hora | Modo | Nota |
|---|---|---|---|---|---|
| **Deepgram Nova-3** | ✅ Explícito (pt-PT) | ~120–200ms | ~$0.36/h | Streaming nativo | Melhor opção RTT |
| **ElevenLabs STT (Scribe v2)** | ✅ 90+ línguas | ~150ms | ~$0.36/h | Streaming WebSocket | Stack ElevenLabs unificado |
| **OpenAI Whisper (batch)** | ✅ | ❌ (sem stream nativo) | $0.006/min | Batch | GPT-Realtime-Whisper lançado Maio 2026 a $0.017/min mas não testado PT-PT |
| **OpenAI GPT-Realtime-Whisper** | Provável | ~200–300ms | $1.02/h | Streaming | Novo (Maio 2026), sem benchmarks PT-PT |
| **AssemblyAI Universal-Streaming** | ✅ (beta) | ~300ms | $0.15/h base | Streaming | PT-PT em beta — risco para produção |
| **Gladia** | ✅ (100+ línguas) | ~300ms | ~$0.54/h | Streaming | Bom para multilingue, não especializado PT-PT |
| **Whisper local (faster-whisper)** | ✅ | ~200–500ms (CPU) | $0 | Batch/local | No Mac Mini sem GPU: latência elevada |

### Conclusão STT
**Deepgram Nova-3 com `language=pt-PT`** continua a ser a escolha certa — já está integrado, melhorou especificamente PT-PT em Maio 2026 (WER -54% vs competidores), streaming sub-200ms, $0.36/h.

**ElevenLabs Scribe v2** é uma alternativa válida se migrares para o ecossistema deles (150ms, WebSocket, mesmo preço). Vantagem: uma só conta, uma só fatura.

---

## 2. TTS — Text-to-Speech com voz emocional e humana

### Comparação directa

| Serviço | PT-PT nativo | Clonagem de voz | TTFA | Custo/1k chars | Nota emocional |
|---|---|---|---|---|---|
| **ElevenLabs v3** | ✅ (clonagem funciona PT) | ✅ Morgan Freeman clonado | ~80–150ms | $0.30 (Pro) | **Melhor qualidade emocional** — model v3 com prosódia, riso real, pausas naturais |
| **Cartesia Sonic 3.5** | ✅ (PT incluído) | ✅ (amostra 3s) | **40–82ms** | ~$0.15 | Mais rápida do mercado — menos emocional que ElevenLabs v3 |
| **OpenAI TTS (tts-1-hd)** | Razoável | ❌ | ~200ms | $0.12–0.30 | Voz genérica, sem emoção real |
| **PlayHT 3.0** | ✅ | ✅ | ~100ms | $0.18 | Boa qualidade, menos madura que ElevenLabs |
| **Kokoro-82M (open-source)** | ✅ (PT-BR principalmente) | ❌ | ~200ms CPU | $0 | PT-PT fraco — vozes principais são EN; inviável para Morgan |
| **Hume Octave 2** | ✅ (PT suportado) | Limitado | ~150ms | Incluído no EVI 4 | Emoção integrada mas voz menos personalizável |

### ElevenLabs Conversational AI — análise a fundo

A plataforma deles integra STT + LLM + TTS num único WebSocket, com:
- Modelo de voz: Eleven v3 Conversational — optimizado para diálogo real-time
- Suporte PT: confirmado (74 línguas), mas feedback de campo diz que PT-PT < PT-BR em qualidade de clonagem — **testar antes de comprometer**
- Preço: **$0.08–0.12/minuto** — inclui STT + LLM + TTS
- Com 1h/dia de uso: ~$4.80–7.20/dia → **~€130–200/mês** — caro para uso pessoal intenso
- O LLM que usam por defeito é deles (não é Claude) — podes trazer o teu próprio LLM via webhook, mas adiciona latência
- Vantagem principal: latência total muito baixa (sub-500ms end-to-end) com pipeline optimizado

### Conclusão TTS
**ElevenLabs v3 via API direta** (não o Conversational AI platform) dá-te a melhor qualidade emocional com a voz Morgan Freeman já clonada, a $0.30/1k chars. Para textos médios de conversação (~150 chars por resposta), custa ~$0.045 por resposta — praticável.

---

## 3. LLM com inteligência emocional

### O que existe

| Abordagem | Capacidade emocional | PT-PT | Custo/1k tokens | Recomendação |
|---|---|---|---|---|
| **Claude Sonnet 4.6 com system prompt elaborado** | Alta (instruct) | ✅ | ~$0.003 in / $0.015 out | **Recomendado** — já usas, controlas o prompt |
| **Claude Opus 4.8** | Muito alta | ✅ | ~$0.015 in / $0.075 out | Para decisões estratégicas, não conversação |
| **Hume EVI 4-mini** | Muito alta (emocional nativo) | ✅ PT suportado | Incluído no plan | Emoção é o seu diferencial — mas voz menos personalizável |
| **GPT-4o Realtime** | Alta | Razoável | $0.10/min audio | Voz nativa OpenAI, não clonável facilmente |
| **Play AI / Tavus** | Média | Limitado | Variável | Orientados a avatares, não assistente pessoal |

### Como construir "memória emocional"

O Morgan já tem Qdrant Cloud e `memory/episodic_memory.json`. A estratégia certa:

1. **Perfil emocional base** — JSON persistente com padrões do Vasco (hora do dia, contexto Moreirense, trading em alta/baixa)
2. **Contexto de sessão** — nos últimos 5 minutos de conversa, detectar palavras/padrões de frustração, euforia, cansaço
3. **System prompt dinâmico** — o CEO monta o prompt com "estado actual: [cansado após treino] [Moreirense perdeu ontem]" → Claude responde em conformidade
4. **Qdrant semântico** — guardar resumos de conversas emocionalmente relevantes, recuperar no início de cada sessão

Exemplo de system prompt emocional:
```
És o Morgan — não um assistente, um irmão mais velho que conhece o Vasco há anos.
Estado actual do Vasco: [cansado, treino difícil às 10h].
Última conversa relevante: [ontem estava frustrado com o trading].
Adapta o tom: directo, sem floreados, sem validação vazia. 
Se discordas, diz. Se há más notícias, dá-as claramente.
Fala como se estivesses no sofá ao lado dele, não como um chatbot.
```

---

## 4. Arquitecturas possíveis

### A) ElevenLabs Conversational AI (end-to-end)

```
Browser mic → ElevenLabs WebSocket (STT+LLM+TTS integrado) → áudio
```

| | |
|---|---|
| **Latência total** | ~400–600ms (end-to-end) |
| **Custo/mês (1h/dia)** | ~€130–200/mês |
| **Complexidade implementação** | 3/10 — já tens o proxy em desktop_server.py |
| **Qualidade** | 8/10 — boa mas LLM deles ≠ Claude, voz v3 excelente |
| **Problema principal** | LLM nativo deles não é Claude; trazer Claude via webhook adiciona latência e custo; PT-PT pode ser menos polido que PT-BR |

---

### B) Pipeline próprio — Deepgram STT → Claude API → ElevenLabs TTS

```
Mic → Deepgram Nova-3 stream (PT-PT) → buffer de frase → Claude Sonnet → ElevenLabs v3 stream → áudio
```

| | |
|---|---|
| **Latência total** | ~600–900ms (realista com streaming sentence-by-sentence) |
| **Custo/mês (1h/dia)** | ~€25–40/mês (Deepgram + Claude + ElevenLabs) |
| **Complexidade implementação** | 6/10 — pipeline novo mas código modular |
| **Qualidade** | 9/10 — melhor LLM, melhor voz, total controlo |
| **Vantagem** | Controlo total; Claude com memória emocional real; voz Morgan Freeman clonada; PT-PT nativo em cada camada |

Estimativa de custos com 1h/dia:
- Deepgram: 30h/mês × $0.36 = **$10.80**
- Claude Sonnet: ~1000 mensagens/mês × ~500 tokens = $7.50 in + $37.50 out ≈ **$45** (upper bound)
- ElevenLabs TTS: ~150 chars/resposta × 1000 respostas × $0.30/1k = **$45**
- **Total: ~$100/mês (~€90)** — pode otimizar com cache de respostas comuns

---

### C) Pipeline open-source local (Mac Mini)

```
Mic → faster-whisper local (CPU) → Ollama (LLM local) → Kokoro TTS → áudio
```

| | |
|---|---|
| **Latência total** | ~1500–3000ms no Mac Mini sem GPU |
| **Custo/mês** | ~€5–11 (só electricidade) |
| **Complexidade implementação** | 8/10 — setup complexo, manutenção alta |
| **Qualidade** | 5/10 — Kokoro PT fraco; LLMs locais 8B << Claude |
| **Problema principal** | Mac Mini sem GPU Apple Silicon (é Intel?) → Whisper lento; Kokoro sem PT-PT nativo; LLM local não tem capacidade do Claude |

**Não recomendado** para uso diário do Morgan.

---

### D) Hume EVI 4-mini

```
Browser mic → Hume EVI 4-mini WebSocket (PT suportado) → áudio
```

| | |
|---|---|
| **Latência total** | ~500–700ms |
| **Custo/mês** | ~$0.06/min → ~€100/mês (1h/dia) |
| **Complexidade implementação** | 4/10 — API similar ao EVI 2 |
| **Qualidade emocional** | 9/10 — é o diferencial deles |
| **Problema principal** | PT-PT em EVI 4-mini: confirmado suportado, mas qualidade não benchmarked; voz não é a Morgan Freeman clonada; EVI 2 que tinhas estava quebrado, EVI 4 é diferente |

Interessante como alternativa futura, mas requer teste de qualidade PT-PT antes de comprometer.

---

### E) Híbrida — ElevenLabs STT + Claude + ElevenLabs TTS v3

```
Mic → ElevenLabs Scribe v2 stream (150ms) → Claude Sonnet (memória emocional) → ElevenLabs v3 TTS stream → áudio
```

| | |
|---|---|
| **Latência total** | ~500–700ms |
| **Custo/mês** | ~€70–90/mês |
| **Complexidade implementação** | 5/10 — duas APIs ElevenLabs + Claude |
| **Qualidade** | 9/10 — mesma qualidade que B mas STT unificado na conta ElevenLabs |
| **Vantagem** | Uma conta, uma fatura; STT deles é 150ms (melhor que Deepgram para este uso); Claude mantém-se |

---

## 5. Recomendação Final

### Arquitectura escolhida: **E — ElevenLabs STT (Scribe v2) + Claude Sonnet + ElevenLabs TTS v3**

**Porquê esta e não a B:**
- ElevenLabs STT Scribe v2 tem 150ms (melhor que Deepgram's 200ms para este uso)
- Uma conta, uma fatura, um SDK — simplifica manutenção
- A voz Morgan Freeman está já clonada na mesma conta
- Claude Sonnet com system prompt emocional é imbatível como "irmão"
- Deepgram mantém-se como fallback se ElevenLabs STT tiver problemas

**Porquê não o Conversational AI platform (A):**
- $130–200/mês vs €70–90 com a arquitectura E
- LLM deles ≠ Claude → perdes toda a inteligência emocional customizada
- Menos controlo sobre memória, system prompt, contexto do Vasco

---

### Plano de implementação

**Ficheiros a criar/modificar:**

```
Morgan/
├── voice_pipeline.py          # NOVO — pipeline E2E com ElevenLabs STT + Claude + ElevenLabs TTS
├── voice_emotional_context.py # NOVO — constrói system prompt com estado emocional do Vasco
├── desktop_server.py          # MODIFICAR — substituir Hume EVI por voice_pipeline
└── memory/
    └── emotional_profile.json # NOVO — perfil emocional persistente do Vasco
```

**`voice_pipeline.py` — estrutura:**
```python
async def voice_session(websocket):
    # 1. ElevenLabs Scribe v2 WebSocket (STT stream)
    # 2. Detectar fim de frase (silence + puctuation)
    # 3. Construir contexto emocional via voice_emotional_context.py
    # 4. Claude Sonnet API (streaming, sentence-by-sentence)
    # 5. Por cada frase → ElevenLabs TTS v3 stream → áudio para browser
```

**`voice_emotional_context.py` — lógica:**
```python
def build_emotional_prompt(hora: int, last_matches: list, trading_pnl: float) -> str:
    # Detectar contexto: após treino, noite, fim de semana, etc.
    # Recuperar últimas notas emocionais do Qdrant
    # Retornar system prompt personalizado
```

---

### Custo mensal estimado

| Componente | Custo/mês (1h/dia) |
|---|---|
| ElevenLabs STT (Scribe v2) | ~$12 |
| Claude Sonnet 4.6 | ~$30–45 |
| ElevenLabs TTS v3 | ~$35–45 |
| **Total** | **~€70–90/mês** |

Optimizações para reduzir: cache de respostas repetidas (briefings de manhã), Claude Haiku para respostas curtas (< 2 frases), limitar TTS a respostas > 10 palavras (resto em texto).

---

### Prazo para voz funcional em PT-PT com qualidade "irmão"

| Fase | O que fazer | Prazo |
|---|---|---|
| **Fase 1** (2–3h) | `voice_pipeline.py` com STT + Claude + TTS; integrar em `desktop_server.py`; testar PT-PT básico | 1 sessão |
| **Fase 2** (3–4h) | `voice_emotional_context.py`; `emotional_profile.json`; system prompt dinâmico com hora/contexto | 1 sessão |
| **Fase 3** (1–2h) | Tuning: velocidade da voz ElevenLabs (stability, similarity_boost, style), silêncio entre frases, detecção de fim de turn | 1 sessão |
| **Total** | Voz funcional e emocional | **2–3 sessões de trabalho** |

---

### Como integrar no desktop_server.py existente

O código actual já tem:
- `gerar_audio_elevenlabs()` — manter, usar para TTS
- Proxy WebSocket Hume EVI — **substituir** por `voice_pipeline.py`
- `ELEVENLABS_VOICE_ID` e `ELEVENLABS_KEY` — já presentes, reutilizar

Mudança principal: substituir o handler `/ws/hume` por `/ws/voice` que usa o novo pipeline. O browser (desktop/index.html) liga ao mesmo endpoint, muda só o URL.

---

## Notas finais

- **ElevenLabs STT PT-PT**: confirmado suportado (90+ línguas, WebSocket 150ms) mas qualidade específica PT-PT vs PT-BR requer teste prático de 10 minutos antes de comprometer
- **Hume EVI 4-mini**: merece um teste paralelo — emoção nativa é o seu diferencial; se PT-PT for bom, pode ser opção futura para substituir camada de LLM
- **Cartesia**: ideal se a latência for crítica (40ms TTFA vs 80ms ElevenLabs) mas emoção é inferior; não recomendado dado que o objectivo é qualidade "irmão", não velocidade máxima
- **Kokoro local**: descartar — PT-PT fraco, sem GPU no Mac Mini, manutenção elevada

---

*Gerado: 8 Agosto 2026 | Scout Morgan | Versão 1.0*
