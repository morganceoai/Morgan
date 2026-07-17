"""
Morgan Solver v2 — LangGraph
Fluxo: Diagnose → Plan → Execute → Verify → Report
Cada nó reporta confiança individual (0-100%).
Confiança < 90% → escala ao Claude Code automaticamente.
"""
import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import anthropic
from dotenv import load_dotenv
load_dotenv()

FIXES_FILE = Path(__file__).parent / "memory" / "solver_fixes.json"


def _load_fixes() -> list:
    """Carrega histórico de fixes anteriores."""
    if FIXES_FILE.exists():
        try:
            return json.loads(FIXES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_fix(problema: str, diagnostico: str, fix: str, confianca: int):
    """Guarda fix bem-sucedido no histórico."""
    fixes = _load_fixes()
    fixes.append({
        "data": datetime.now().isoformat(),
        "problema": problema[:300],
        "diagnostico": diagnostico[:300],
        "fix": fix[:500],
        "confianca": confianca,
    })
    fixes = fixes[-100:]  # máximo 100 fixes
    FIXES_FILE.parent.mkdir(exist_ok=True)
    FIXES_FILE.write_text(json.dumps(fixes, indent=2, ensure_ascii=False), encoding="utf-8")

def _fixes_relevantes(problema: str) -> str:
    """Retorna fixes anteriores relevantes para o problema actual."""
    fixes = _load_fixes()
    if not fixes:
        return ""
    # Procura fixes com palavras-chave em comum
    palavras = set(problema.lower().split())
    relevantes = []
    for f in reversed(fixes):
        palavras_fix = set(f["problema"].lower().split())
        if len(palavras & palavras_fix) >= 2:
            relevantes.append(f"Problema similar: {f['problema'][:100]}\nFix aplicado: {f['fix'][:200]}\nConfiança: {f['confianca']}%")
    return "\n\n".join(relevantes[:3]) if relevantes else ""

def _escalar_claude_code(problema: str, diagnostico: str, plano: str) -> str:
    """Escala para o Claude Code quando confiança < 90%. Invoca claude CLI com contexto completo."""
    try:
        morgan_dir = Path(__file__).parent
        prompt = f"""Morgan Solver escalou este problema por confiança insuficiente.

PROBLEMA: {problema}

DIAGNÓSTICO DO SOLVER: {diagnostico[:500]}

PLANO DO SOLVER: {plano[:500]}

Analisa o código, aplica o fix necessário, faz commit e push. O deploy é automático via GitHub Actions."""

        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True,
            cwd=str(morgan_dir), timeout=300
        )
        if result.returncode == 0 and result.stdout:
            return f"Claude Code resolveu:\n{result.stdout[:1000]}"
        else:
            return f"Claude Code indisponível: {result.stderr[:200]}"
    except FileNotFoundError:
        return "Claude Code CLI não disponível neste ambiente."
    except Exception as e:
        return f"Erro ao escalar para Claude Code: {e}"

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
        "model": "claude-sonnet-4-6",
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
    fixes_hist = _fixes_relevantes(state["problema"])
    historico_bloco = ""
    if fixes_hist:
        historico_bloco = f"\n\nFIXES ANTERIORES RELEVANTES (usa como ponto de partida):\n{fixes_hist}\n"

    system = f"""És o Morgan Solver. Diagnostica o problema com as ferramentas disponíveis.{historico_bloco}

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


def _pre_execution_tests() -> tuple[bool, str]:
    """Corre testes básicos antes de executar qualquer correcção.
    Devolve (passou, relatorio). Se falhar, a execução não deve prosseguir."""
    import subprocess, sys
    resultados = []

    # 1. Sintaxe dos ficheiros Python críticos
    for modulo in ["desktop_server.py", "tools.py", "solver_graph.py"]:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "py_compile", modulo],
                capture_output=True, text=True, timeout=15,
                cwd=str(_MORGAN_DIR())
            )
            if r.returncode == 0:
                resultados.append(f"OK: {modulo} — sintaxe válida")
            else:
                resultados.append(f"ERRO: {modulo} — {r.stderr.strip()[:200]}")
                return False, "\n".join(resultados)
        except Exception as e:
            resultados.append(f"AVISO: não foi possível verificar {modulo}: {e}")

    # 2. Import dos módulos críticos
    criticos = ["anthropic", "fastapi", "langgraph"]
    for mod in criticos:
        try:
            r = subprocess.run(
                [sys.executable, "-c", f"import {mod}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(_MORGAN_DIR())
            )
            if r.returncode == 0:
                resultados.append(f"OK: {mod} importável")
            else:
                resultados.append(f"ERRO: {mod} — {r.stderr.strip()[:100]}")
                return False, "\n".join(resultados)
        except Exception as e:
            resultados.append(f"AVISO: {mod}: {e}")

    return True, "\n".join(resultados)


def _MORGAN_DIR():
    from pathlib import Path
    return Path(__file__).parent


def node_execucao(state: SolverState) -> SolverState:
    # Testes pré-execução — valida sintaxe e imports antes de qualquer correcção
    passou, relatorio_testes = _pre_execution_tests()
    if not passou:
        return {**state,
                "execucao": f"ABORTADO — testes pré-execução falharam:\n{relatorio_testes}",
                "confianca_execucao": 0}

    system = f"""És o Morgan Solver. Executa o plano aprovado com as ferramentas disponíveis.
Documenta cada passo e o resultado. Se algo correr mal, para imediatamente.

Testes pré-execução passaram:
{relatorio_testes}

FLUXO DE CORRECÇÃO OBRIGATÓRIO:
1. Usa solver_ler_ficheiro para ler o ficheiro antes de editar
2. Usa solver_editar_ficheiro para edições cirúrgicas (preferível) ou solver_criar_ficheiro para reescritas completas
3. Usa solver_git_commit_push para fazer commit e push — o deploy é automático via GitHub Actions, NÃO precisas de chamar solver_railway_deploy
4. Verifica o resultado com solver_executar_diagnostico

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


def node_escalar_claude_code(state: SolverState) -> SolverState:
    """Invocado quando confiança < 90%. Chama Claude Code CLI em vez de perguntar ao Vasco."""
    resultado = _escalar_claude_code(
        state["problema"],
        state.get("diagnostico", ""),
        state.get("plano", ""),
    )
    return {**state,
            "execucao": resultado,
            "confianca_execucao": 85}  # Claude Code é mais capaz — confiança base 85%


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

    # Guarda fix no histórico se resolvido com sucesso
    if "RESOLVIDO" in texto.upper() and "NÃO_RESOLVIDO" not in texto.upper():
        _save_fix(
            problema=state["problema"],
            diagnostico=state.get("diagnostico", "")[:300],
            fix=state.get("execucao", "")[:500],
            confianca=confianca,
        )

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

        via_claude = state.get("confianca_solucao", 100) < 90 and not state.get("requer_aprovacao")
        executor = "Claude Code (escalado — confiança solução <90%)" if via_claude else "Solver autónomo"
        relatorio = (
            f"PROBLEMA: {state['problema']}\n\n"
            f"DIAGNÓSTICO (confiança {state.get('confianca_diagnostico', '?')}%):\n{state['diagnostico']}\n\n"
            f"PLANO (confiança solução {state.get('confianca_solucao', '?')}%):\n{state['plano']}\n\n"
            f"EXECUTOR: {executor}\n"
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
    confianca = state.get("confianca_solucao", 50)
    if confianca < 90:
        return "escalar_claude_code"
    return "execucao"


# ── Construção do grafo ───────────────────────────────────────────────────────

def build_solver_graph():
    grafo = StateGraph(SolverState)

    grafo.add_node("diagnostico", node_diagnostico)
    grafo.add_node("plano", node_plano)
    grafo.add_node("aguardar_aprovacao", node_aguardar_aprovacao)
    grafo.add_node("escalar_claude_code", node_escalar_claude_code)
    grafo.add_node("execucao", node_execucao)
    grafo.add_node("verificacao", node_verificacao)
    grafo.add_node("relatorio", node_relatorio)

    grafo.set_entry_point("diagnostico")
    grafo.add_edge("diagnostico", "plano")
    grafo.add_conditional_edges("plano", decide_apos_plano, {
        "aguardar_aprovacao": "aguardar_aprovacao",
        "escalar_claude_code": "escalar_claude_code",
        "execucao": "execucao",
    })
    grafo.add_edge("aguardar_aprovacao", "relatorio")
    grafo.add_edge("escalar_claude_code", "verificacao")
    grafo.add_edge("execucao", "verificacao")
    grafo.add_edge("verificacao", "relatorio")
    grafo.add_edge("relatorio", END)

    return grafo.compile()


# ── Interface pública ─────────────────────────────────────────────────────────

_graph = None

def run_solver(problema: str, aprovado: bool = False) -> str:
    """Alias público para o endpoint /api/solver/run."""
    resultado = solver_diagnosticar(problema, aprovado)
    return resultado.get("relatorio", "Solver sem relatório.")


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
