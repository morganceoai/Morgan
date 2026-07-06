"""
Morgan Solver v2 — LangGraph
Fluxo estruturado: Diagnose → Plan → Execute → Verify → Report
"""
import os
import json
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_client = None

def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ── Estado do grafo ───────────────────────────────────────────────────────────

class SolverState(TypedDict):
    messages: Annotated[list, add_messages]
    problema: str
    diagnostico: str
    plano: str
    execucao: str
    verificacao: str
    relatorio: str
    requer_aprovacao: bool
    aprovado: bool
    iteracoes: int


# ── Ferramentas disponíveis ao Solver ─────────────────────────────────────────

def _get_tools():
    from tools import TOOLS
    # Só as ferramentas do Solver
    solver_tools = [
        t for t in TOOLS
        if t["name"].startswith("solver_") or t["name"] in ["pesquisar_web"]
    ]
    return solver_tools

def _run_tool(name: str, inp: dict) -> str:
    from tools import TOOL_FUNCTIONS
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Ferramenta {name} não encontrada."
    try:
        return func(**inp) if inp else func()
    except Exception as e:
        return f"Erro: {e}"

def _chamar_claude(system: str, messages: list, tools: list = None) -> str:
    kwargs = {
        "model": "claude-opus-4-8",
        "max_tokens": 2048,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    client = get_client()
    msgs = list(messages)

    while True:
        response = client.messages.create(**{**kwargs, "messages": msgs})
        if response.stop_reason == "tool_use" and tools:
            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            msgs.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""


# ── Nós do grafo ──────────────────────────────────────────────────────────────

def node_diagnostico(state: SolverState) -> SolverState:
    """Nó 1 — Diagnostica o problema com ferramentas reais."""
    system = """És o Morgan Solver — agente de diagnóstico técnico da BC Industries.
Usa as ferramentas para diagnosticar o problema. Sê preciso e técnico.
Responde APENAS com o diagnóstico — o que está errado, onde, e qual a causa provável."""

    texto = _chamar_claude(
        system=system,
        messages=[{"role": "user", "content": f"Diagnostica este problema: {state['problema']}"}],
        tools=_get_tools(),
    )
    return {**state, "diagnostico": texto, "iteracoes": state.get("iteracoes", 0) + 1}


def node_plano(state: SolverState) -> SolverState:
    """Nó 2 — Cria plano de correção e decide se requer aprovação."""
    system = """És o Morgan Solver. Com base no diagnóstico, cria um plano de correção concreto.
Indica claramente:
1. O que vais fazer (passos específicos)
2. Se é reversível ou irreversível
3. Se requer aprovação do Vasco (sim/não)

Formato da resposta:
PLANO: [descrição dos passos]
REVERSÍVEL: [sim/não]
REQUER_APROVAÇÃO: [sim/não]
MOTIVO: [porquê requer ou não aprovação]"""

    texto = _chamar_claude(
        system=system,
        messages=[
            {"role": "user", "content": f"Problema: {state['problema']}"},
            {"role": "assistant", "content": f"Diagnóstico: {state['diagnostico']}"},
            {"role": "user", "content": "Cria o plano de correção."},
        ],
    )

    requer = "REQUER_APROVACAO: SIM" in texto.upper() or "REQUER_APROVAÇÃO: SIM" in texto.upper()
    return {**state, "plano": texto, "requer_aprovacao": requer}


def node_aguardar_aprovacao(state: SolverState) -> SolverState:
    """Nó 3a — Marca que aguarda aprovação (o CEO informa o Vasco)."""
    return {**state, "aprovado": False}


def node_execucao(state: SolverState) -> SolverState:
    """Nó 3b — Executa a correção com ferramentas reais."""
    system = """És o Morgan Solver. Executa o plano de correção usando as ferramentas disponíveis.
Documenta cada passo que executas e o resultado.
Se algo correr mal, para e reporta."""

    texto = _chamar_claude(
        system=system,
        messages=[
            {"role": "user", "content": f"Problema: {state['problema']}"},
            {"role": "assistant", "content": f"Diagnóstico: {state['diagnostico']}"},
            {"role": "user", "content": f"Plano aprovado: {state['plano']}"},
            {"role": "user", "content": "Executa o plano agora."},
        ],
        tools=_get_tools(),
    )
    return {**state, "execucao": texto}


def node_verificacao(state: SolverState) -> SolverState:
    """Nó 4 — Verifica se a correção funcionou."""
    system = """És o Morgan Solver. Verifica se o problema foi resolvido.
Usa as ferramentas para confirmar. Responde com:
RESULTADO: [RESOLVIDO / PARCIALMENTE_RESOLVIDO / NÃO_RESOLVIDO]
DETALHES: [o que verificaste]"""

    texto = _chamar_claude(
        system=system,
        messages=[
            {"role": "user", "content": f"Problema original: {state['problema']}"},
            {"role": "assistant", "content": f"Correção executada: {state['execucao']}"},
            {"role": "user", "content": "Verifica se o problema foi resolvido."},
        ],
        tools=_get_tools(),
    )
    return {**state, "verificacao": texto}


def node_relatorio(state: SolverState) -> SolverState:
    """Nó 5 — Gera relatório final para o CEO traduzir ao Vasco."""
    partes = [
        f"PROBLEMA: {state['problema']}",
        f"DIAGNÓSTICO: {state['diagnostico']}",
    ]
    if state.get("requer_aprovacao") and not state.get("aprovado"):
        partes.append(f"PLANO (aguarda aprovação): {state['plano']}")
        relatorio = "\n\n".join(partes)
    else:
        partes += [
            f"PLANO: {state['plano']}",
            f"EXECUÇÃO: {state['execucao']}",
            f"VERIFICAÇÃO: {state['verificacao']}",
        ]
        relatorio = "\n\n".join(partes)

    return {**state, "relatorio": relatorio}


# ── Edges condicionais ────────────────────────────────────────────────────────

def decide_apos_plano(state: SolverState) -> str:
    if state.get("requer_aprovacao"):
        return "aguardar_aprovacao"
    return "execucao"


# ── Construção do grafo ───────────────────────────────────────────────────────

def build_solver_graph():
    grafo = StateGraph(SolverState)

    grafo.add_node("diagnostico", node_diagnostico)
    grafo.add_node("plano", node_plano)
    grafo.add_node("aguardar_aprovacao", node_aguardar_aprovacao)
    grafo.add_node("execucao", node_execucao)
    grafo.add_node("verificacao", node_verificacao)
    grafo.add_node("relatorio", node_relatorio)

    grafo.set_entry_point("diagnostico")
    grafo.add_edge("diagnostico", "plano")
    grafo.add_conditional_edges("plano", decide_apos_plano, {
        "aguardar_aprovacao": "aguardar_aprovacao",
        "execucao": "execucao",
    })
    grafo.add_edge("aguardar_aprovacao", "relatorio")
    grafo.add_edge("execucao", "verificacao")
    grafo.add_edge("verificacao", "relatorio")
    grafo.add_edge("relatorio", END)

    return grafo.compile()


# ── Interface pública ─────────────────────────────────────────────────────────

_graph = None

def solver_diagnosticar(problema: str, aprovado: bool = False) -> dict:
    """Corre o grafo do Solver para um problema dado. Devolve o estado final."""
    global _graph
    if _graph is None:
        _graph = build_solver_graph()

    estado_inicial = {
        "messages": [],
        "problema": problema,
        "diagnostico": "",
        "plano": "",
        "execucao": "",
        "verificacao": "",
        "relatorio": "",
        "requer_aprovacao": False,
        "aprovado": aprovado,
        "iteracoes": 0,
    }

    resultado = _graph.invoke(estado_inicial)
    return resultado
