"""
Morgan Solver v2 — LangGraph
Fluxo: Diagnose → Plan → Execute → Verify → Report
Cada nó reporta confiança individual (0-100%).
"""
import os
import re
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
    # Outputs por nó
    diagnostico: str
    plano: str
    execucao: str
    verificacao: str
    relatorio: str
    # Confiança por passo (0-100)
    confianca_diagnostico: int
    confianca_solucao: int
    confianca_execucao: int
    confianca_verificacao: int
    # Meta
    reversivel: bool
    impacto: str          # "isolado" | "sistémico" | "crítico"
    requer_aprovacao: bool
    aprovado: bool
    iteracoes: int


# ── Utilitários ───────────────────────────────────────────────────────────────

def _get_tools():
    from tools import TOOLS
    return [t for t in TOOLS if t["name"].startswith("solver_") or t["name"] in ["pesquisar_web"]]

def _run_tool(name: str, inp: dict) -> str:
    from tools import TOOL_FUNCTIONS
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Ferramenta {name} não encontrada."
    try:
        return func(**inp) if inp else func()
    except Exception as e:
        return f"Erro: {e}"

def _extrair_confianca(texto: str, campo: str) -> int:
    """Extrai CAMPO: XX% do texto do Claude."""
    pattern = rf"{campo}[:\s]+(\d{{1,3}})%"
    m = re.search(pattern, texto, re.IGNORECASE)
    if m:
        return min(100, max(0, int(m.group(1))))
    return 50  # default conservador

def _chamar_claude(system: str, messages: list, tools: list = None) -> str:
    kwargs = {
        "model": "claude-opus-4-8",
        "max_tokens": 2048,
        "system": system,
        "messages": messages,
    }
    client = get_client()
    msgs = list(messages)

    while True:
        response = client.messages.create(**{**kwargs, "messages": msgs})
        if response.stop_reason == "tool_use" and tools:
            kwargs["tools"] = tools
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
    system = """És o Morgan Solver. Diagnostica o problema com as ferramentas disponíveis.

Obrigatório no final da resposta, neste formato exacto:
DIAGNÓSTICO: [o que está errado e porquê]
CONFIANÇA_DIAGNÓSTICO: XX%
REVERSÍVEL: sim/não
IMPACTO: isolado/sistémico/crítico"""

    texto = _chamar_claude(
        system=system,
        messages=[{"role": "user", "content": f"Diagnostica: {state['problema']}"}],
        tools=_get_tools(),
    )

    confianca = _extrair_confianca(texto, "CONFIANÇA_DIAGNÓSTICO")
    reversivel = "REVERSÍVEL: sim" in texto.lower()
    impacto = "crítico" if "crítico" in texto.lower() else ("sistémico" if "sistémico" in texto.lower() else "isolado")

    return {**state,
            "diagnostico": texto,
            "confianca_diagnostico": confianca,
            "reversivel": reversivel,
            "impacto": impacto,
            "iteracoes": state.get("iteracoes", 0) + 1}


def node_plano(state: SolverState) -> SolverState:
    system = """És o Morgan Solver. Com base no diagnóstico, cria o plano de correção.

Obrigatório no final da resposta, neste formato exacto:
PLANO: [passos concretos]
CONFIANÇA_SOLUÇÃO: XX%
REQUER_APROVAÇÃO: sim/não
MOTIVO_APROVAÇÃO: [porquê requer ou não aprovação do CEO/Vasco]"""

    texto = _chamar_claude(
        system=system,
        messages=[
            {"role": "user", "content": f"Problema: {state['problema']}"},
            {"role": "assistant", "content": state["diagnostico"]},
            {"role": "user", "content": "Cria o plano de correção."},
        ],
    )

    confianca = _extrair_confianca(texto, "CONFIANÇA_SOLUÇÃO")
    requer = "REQUER_APROVAÇÃO: SIM" in texto.upper() or "REQUER_APROVACAO: SIM" in texto.upper()

    return {**state,
            "plano": texto,
            "confianca_solucao": confianca,
            "requer_aprovacao": requer}


def node_aguardar_aprovacao(state: SolverState) -> SolverState:
    return {**state, "aprovado": False, "confianca_execucao": 0}


def node_execucao(state: SolverState) -> SolverState:
    system = """És o Morgan Solver. Executa o plano aprovado com as ferramentas disponíveis.
Documenta cada passo e o resultado. Se algo correr mal, para imediatamente.

Obrigatório no final da resposta, neste formato exacto:
EXECUÇÃO: [o que foi feito]
CONFIANÇA_EXECUÇÃO: XX%"""

    texto = _chamar_claude(
        system=system,
        messages=[
            {"role": "user", "content": f"Problema: {state['problema']}"},
            {"role": "assistant", "content": state["diagnostico"]},
            {"role": "user", "content": f"Plano aprovado: {state['plano']}"},
            {"role": "user", "content": "Executa agora."},
        ],
        tools=_get_tools(),
    )

    confianca = _extrair_confianca(texto, "CONFIANÇA_EXECUÇÃO")
    return {**state, "execucao": texto, "confianca_execucao": confianca}


def node_verificacao(state: SolverState) -> SolverState:
    system = """És o Morgan Solver. Verifica se o problema foi resolvido com as ferramentas disponíveis.

Obrigatório no final da resposta, neste formato exacto:
RESULTADO: RESOLVIDO / PARCIALMENTE_RESOLVIDO / NÃO_RESOLVIDO
CONFIANÇA_VERIFICAÇÃO: XX%
DETALHES: [o que verificaste e como]"""

    texto = _chamar_claude(
        system=system,
        messages=[
            {"role": "user", "content": f"Problema original: {state['problema']}"},
            {"role": "assistant", "content": f"Correção executada: {state['execucao']}"},
            {"role": "user", "content": "Verifica se está resolvido."},
        ],
        tools=_get_tools(),
    )

    confianca = _extrair_confianca(texto, "CONFIANÇA_VERIFICAÇÃO")
    return {**state, "verificacao": texto, "confianca_verificacao": confianca}


def node_relatorio(state: SolverState) -> SolverState:
    """Gera relatório estruturado para o CEO — inclui confiança por passo."""

    if state.get("requer_aprovacao") and not state.get("aprovado"):
        relatorio = (
            f"PROBLEMA: {state['problema']}\n\n"
            f"DIAGNÓSTICO (confiança {state.get('confianca_diagnostico', '?')}%):\n{state['diagnostico']}\n\n"
            f"PLANO PROPOSTO (confiança solução {state.get('confianca_solucao', '?')}%):\n{state['plano']}\n\n"
            f"REVERSÍVEL: {'Sim' if state.get('reversivel') else 'Não'}\n"
            f"IMPACTO: {state.get('impacto', 'desconhecido')}\n\n"
            f"AGUARDA APROVAÇÃO DO CEO/VASCO"
        )
    else:
        confianca_media = int((
            state.get('confianca_diagnostico', 0) +
            state.get('confianca_solucao', 0) +
            state.get('confianca_execucao', 0) +
            state.get('confianca_verificacao', 0)
        ) / 4)

        relatorio = (
            f"PROBLEMA: {state['problema']}\n\n"
            f"DIAGNÓSTICO (confiança {state.get('confianca_diagnostico', '?')}%):\n{state['diagnostico']}\n\n"
            f"PLANO (confiança solução {state.get('confianca_solucao', '?')}%):\n{state['plano']}\n\n"
            f"EXECUÇÃO (confiança execução {state.get('confianca_execucao', '?')}%):\n{state['execucao']}\n\n"
            f"VERIFICAÇÃO (confiança verificação {state.get('confianca_verificacao', '?')}%):\n{state['verificacao']}\n\n"
            f"REVERSÍVEL: {'Sim' if state.get('reversivel') else 'Não'} | IMPACTO: {state.get('impacto', 'desconhecido')}\n"
            f"CONFIANÇA GLOBAL: {confianca_media}%"
        )

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
    global _graph
    if _graph is None:
        _graph = build_solver_graph()

    estado_inicial: SolverState = {
        "messages": [],
        "problema": problema,
        "diagnostico": "",
        "plano": "",
        "execucao": "",
        "verificacao": "",
        "relatorio": "",
        "confianca_diagnostico": 0,
        "confianca_solucao": 0,
        "confianca_execucao": 0,
        "confianca_verificacao": 0,
        "reversivel": True,
        "impacto": "isolado",
        "requer_aprovacao": False,
        "aprovado": aprovado,
        "iteracoes": 0,
    }

    return _graph.invoke(estado_inicial)
