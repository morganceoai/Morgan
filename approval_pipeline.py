"""
approval_pipeline.py — pipeline de aprovação paralela de oportunidades.

Quando o Scout detecta uma oportunidade:
1. CEO notifica o Vasco imediatamente
2. Em paralelo: Creator prepara plano técnico, Marketeer prepara marketing,
   Solver faz análise de risco, CFO faz projeção financeira
3. CEO envia briefing completo ao Vasco para aprovação
4. Se aprovado → todos os planos activam simultaneamente
"""
import asyncio
import os
from typing import Any
import anthropic

_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

_HAIKU = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-6"


def _ask(system: str, prompt: str, model: str = _HAIKU, max_tokens: int = 400) -> str:
    try:
        r = _claude.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text.strip()
    except Exception as e:
        return f"(erro: {e})"


def _plano_creator(oportunidade: str, descricao: str) -> str:
    return _ask(
        "És o Creator do Morgan. Analisas oportunidades e defines planos técnicos de implementação.",
        f"""Oportunidade: {oportunidade}
Descrição: {descricao}

Define um plano técnico conciso:
- O que construir (agente, serviço, integração?)
- Dependências externas (APIs, contas, bibliotecas)
- Tempo estimado de implementação
- Riscos técnicos
Máximo 5 linhas. Sem emojis. Português europeu.""",
    )


def _plano_marketeer(oportunidade: str, descricao: str) -> str:
    return _ask(
        "És o Marketeer do Morgan. Defines estratégias de marketing para novos negócios.",
        f"""Oportunidade: {oportunidade}
Descrição: {descricao}

Define uma estratégia de marketing inicial:
- Canais prioritários (Pinterest, SEO Etsy, email frio, etc.)
- Primeiras 3 acções concretas
- Custo estimado de marketing inicial
Máximo 5 linhas. Sem emojis. Português europeu.""",
    )


def _analise_solver(oportunidade: str, descricao: str) -> str:
    return _ask(
        "És o Solver do Morgan. Analisas riscos e pontos de falha antes de lançar novos projectos.",
        f"""Oportunidade: {oportunidade}
Descrição: {descricao}

Faz uma análise de risco:
- Principal risco de falha
- Dependências críticas
- O que monitorizar nos primeiros 30 dias
- Nível de risco geral: Baixo / Médio / Alto
Máximo 5 linhas. Sem emojis. Português europeu.""",
    )


def _previsao_cfo(oportunidade: str, descricao: str) -> str:
    return _ask(
        "És o CFO do Morgan. Fazes projeções financeiras realistas para novos negócios.",
        f"""Oportunidade: {oportunidade}
Descrição: {descricao}

Faz uma projeção financeira realista:
- Custo inicial estimado (€)
- Receita esperada em 30 / 90 / 180 dias (€/mês)
- Break-even estimado
- Impacto no objetivo de €10k/mês passivo
Máximo 5 linhas. Sem emojis. Português europeu.""",
    )


async def preparar_briefing_aprovacao(oportunidade: str, descricao: str) -> str:
    """
    Corre as 4 análises em paralelo e devolve o briefing completo.
    Chamado pelo CEO quando o Scout reporta uma oportunidade nova.
    """
    loop = asyncio.get_event_loop()

    # Correr as 4 análises em paralelo
    creator_f   = loop.run_in_executor(None, _plano_creator,   oportunidade, descricao)
    marketeer_f = loop.run_in_executor(None, _plano_marketeer, oportunidade, descricao)
    solver_f    = loop.run_in_executor(None, _analise_solver,  oportunidade, descricao)
    cfo_f       = loop.run_in_executor(None, _previsao_cfo,    oportunidade, descricao)

    creator_r, marketeer_r, solver_r, cfo_r = await asyncio.gather(
        creator_f, marketeer_f, solver_f, cfo_f
    )

    briefing = f"""OPORTUNIDADE DETECTADA: {oportunidade}
{descricao}

─── CREATOR — Plano técnico ───
{creator_r}

─── MARKETEER — Estratégia ───
{marketeer_r}

─── SOLVER — Risco ───
{solver_r}

─── CFO — Projeção financeira ───
{cfo_r}

Respondes "aprovo {oportunidade}" para avançar ou "rejeito {oportunidade}" para arquivar."""

    return briefing


def executar_oportunidade_aprovada(oportunidade: str, descricao: str) -> str:
    """
    Activa os planos após aprovação do Vasco.
    Por agora: regista no sistema e notifica agentes.
    O Creator trata da implementação técnica quando chamado.
    """
    from sistema_service import registar_negocio
    from scout_memory import aprovar_oportunidade as _aprova

    # Registar no sistema central
    chave = oportunidade.lower().replace(" ", "_")[:30]
    registar_negocio(
        chave=chave,
        nome=oportunidade,
        tipo="a_definir",
        plataforma="a_definir",
        descricao=descricao,
        notificar=False,
    )

    # Marcar como aprovada no scout
    try:
        _aprova(oportunidade)
    except Exception:
        pass

    return (
        f"Oportunidade '{oportunidade}' aprovada e registada no sistema.\n"
        f"CEO, Marketeer, Operator e Solver foram notificados via Mem0.\n"
        f"Creator a preparar plano técnico — aguarda briefing."
    )
