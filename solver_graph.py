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
QDRANT_COLLECTION = "solver_fixes"


def _load_fixes() -> list:
    """Carrega histórico de fixes anteriores."""
    if FIXES_FILE.exists():
        try:
            return json.loads(FIXES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_fix(problema: str, diagnostico: str, fix: str, confianca: int, fonte: str = "solver"):
    """Guarda fix no histórico."""
    fixes = _load_fixes()
    fixes.append({
        "data": datetime.now().isoformat(),
        "problema": problema[:300],
        "diagnostico": diagnostico[:300],
        "fix": fix[:500],
        "confianca": confianca,
        "fonte": fonte,
    })
    fixes = fixes[-200:]
    FIXES_FILE.parent.mkdir(exist_ok=True)
    FIXES_FILE.write_text(json.dumps(fixes, indent=2, ensure_ascii=False), encoding="utf-8")
    # Indexar automaticamente no Qdrant para pesquisa semântica
    _qdrant_upsert_fix(fixes[-1])


def registar_fix_manual(problema: str, diagnostico: str, fix: str, confianca: int = 95) -> str:
    """
    Regista um fix feito manualmente (por Claude Code ou pelo Vasco) no histórico do Solver.
    Chamar sempre que um erro for corrigido fora do pipeline do Solver.
    confianca: 95 para fixes confirmados em produção, menos se incerto.
    """
    _save_fix(problema, diagnostico, fix, confianca, fonte="manual")
    return f"Fix registado: {problema[:80]}"

def _fixes_relevantes(problema: str) -> str:
    """Retorna fixes anteriores relevantes para o problema actual."""
    fixes = _load_fixes()
    if not fixes:
        return ""
    palavras = set(problema.lower().split())
    relevantes = []
    for f in reversed(fixes):
        palavras_fix = set(f["problema"].lower().split())
        if len(palavras & palavras_fix) >= 2:
            relevantes.append(f"Problema similar: {f['problema'][:100]}\nFix aplicado: {f['fix'][:200]}\nConfiança: {f['confianca']}%")
    return "\n\n".join(relevantes[:3]) if relevantes else ""


def _get_embedding(texto: str) -> list[float] | None:
    """Gera embedding via OpenAI text-embedding-3-small."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        resp = client.embeddings.create(model="text-embedding-3-small", input=texto[:2000])
        return resp.data[0].embedding
    except Exception:
        return None


def _qdrant_client():
    try:
        from qdrant_client import QdrantClient
        url = os.getenv("QDRANT_URL", "")
        api_key = os.getenv("QDRANT_API_KEY", "")
        if not url:
            return None
        return QdrantClient(url=url, api_key=api_key or None)
    except Exception:
        return None


def _qdrant_ensure_collection(client) -> bool:
    """Cria colecção solver_fixes no Qdrant se não existir."""
    try:
        from qdrant_client.models import VectorParams, Distance
        cols = [c.name for c in client.get_collections().collections]
        if QDRANT_COLLECTION not in cols:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
        return True
    except Exception:
        return False


def _qdrant_upsert_fix(fix: dict) -> None:
    """Indexa um fix no Qdrant para pesquisa semântica futura."""
    try:
        import uuid
        from qdrant_client.models import PointStruct
        client = _qdrant_client()
        if not client:
            return
        if not _qdrant_ensure_collection(client):
            return
        texto = f"{fix['problema']} {fix.get('diagnostico', '')} {fix.get('fix', '')}"
        vec = _get_embedding(texto)
        if not vec:
            return
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fix['problema'][:200]))
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[PointStruct(id=point_id, vector=vec, payload=fix)],
        )
    except Exception:
        pass


def _qdrant_search(problema: str, top_k: int = 3) -> list[dict]:
    """Pesquisa semântica de fixes similares no Qdrant."""
    try:
        client = _qdrant_client()
        if not client:
            return []
        vec = _get_embedding(problema)
        if not vec:
            return []
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vec,
            limit=top_k,
            score_threshold=0.70,
        )
        return [r.payload for r in results if r.payload]
    except Exception:
        return []


def _seed_qdrant_from_json() -> int:
    """Indexa todos os fixes do solver_fixes.json no Qdrant (idempotente)."""
    fixes = _load_fixes()
    count = 0
    for f in fixes:
        _qdrant_upsert_fix(f)
        count += 1
    return count


def _bm25_score(query_tokens: list[str], doc_tokens: list[str], k1: float = 1.5, b: float = 0.75, avg_len: float = 20) -> float:
    """BM25 score simplificado sem dependências externas."""
    if not doc_tokens:
        return 0.0
    score = 0.0
    doc_len = len(doc_tokens)
    freq_map: dict[str, int] = {}
    for t in doc_tokens:
        freq_map[t] = freq_map.get(t, 0) + 1
    for token in query_tokens:
        tf = freq_map.get(token, 0)
        if tf == 0:
            continue
        idf = 1.0  # IDF simplificado — corpus pequeno
        num = tf * (k1 + 1)
        den = tf + k1 * (1 - b + b * doc_len / avg_len)
        score += idf * num / den
    return score


def _fixes_relevantes(problema: str) -> str:
    """Pesquisa híbrida: BM25 (keywords exactas) + Qdrant (semântico). Union dos top-3 de cada."""
    fixes = _load_fixes()
    vistos: set[str] = set()
    resultado: list[str] = []

    # 1. Qdrant semântico — melhor para variações de linguagem
    semanticos = _qdrant_search(problema, top_k=3)
    for f in semanticos:
        chave = f.get("problema", "")[:80]
        if chave not in vistos:
            vistos.add(chave)
            resultado.append(
                f"[semântico|{f.get('fonte', '?')}] {f['problema'][:120]}\n"
                f"Fix: {f.get('fix', '')[:200]}\n"
                f"Confiança: {f.get('confianca', '?')}%"
            )

    # 2. BM25 — melhor para keywords técnicas exactas (nomes de variáveis, módulos)
    if fixes:
        query_tokens = [t for t in problema.lower().split() if len(t) > 2]
        scored = []
        for f in fixes:
            doc = f"{f['problema']} {f.get('diagnostico', '')} {f.get('fix', '')}".lower()
            score = _bm25_score(query_tokens, doc.split())
            if score > 0:
                scored.append((score, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, f in scored[:3]:
            chave = f.get("problema", "")[:80]
            if chave not in vistos:
                vistos.add(chave)
                resultado.append(
                    f"[bm25|{f.get('fonte', '?')}] {f['problema'][:120]}\n"
                    f"Fix: {f.get('fix', '')[:200]}\n"
                    f"Confiança: {f.get('confianca', '?')}%"
                )

    return "\n\n".join(resultado[:5])


def _erro_recorrente(problema: str) -> bool:
    """Verifica se o mesmo erro apareceu >2x nas últimas 24h."""
    fixes = _load_fixes()
    if not fixes:
        return False
    from datetime import timedelta
    limite = datetime.now() - timedelta(hours=24)
    palavras = set(problema.lower().split())
    count = 0
    for f in fixes:
        try:
            data_fix = datetime.fromisoformat(f["data"])
        except Exception:
            continue
        if data_fix < limite:
            continue
        palavras_fix = set(f["problema"].lower().split())
        if len(palavras & palavras_fix) >= 3:
            count += 1
    return count >= 2


def _circuit_breaker(problema: str) -> bool:
    """Circuit breaker: mesmo erro ≥3x em 2h sem fix → escalar directamente."""
    fixes = _load_fixes()
    if not fixes:
        return False
    from datetime import timedelta
    limite = datetime.now() - timedelta(hours=2)
    palavras = [t for t in problema.lower().split() if len(t) > 3]
    count = 0
    for f in fixes:
        try:
            data_fix = datetime.fromisoformat(f["data"])
        except Exception:
            continue
        if data_fix < limite:
            continue
        palavras_fix = set(f["problema"].lower().split())
        matches = sum(1 for p in palavras if p in palavras_fix)
        if matches >= min(3, len(palavras)):
            count += 1
    return count >= 3


def _gather_context() -> str:
    """Sprint 1: recolhe contexto git + logs antes do diagnóstico."""
    morgan_dir = Path(__file__).parent
    partes = []

    # git log últimas 10 commits
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True, text=True, timeout=10, cwd=str(morgan_dir)
        )
        if r.stdout.strip():
            partes.append(f"GIT LOG (últimas 10):\n{r.stdout.strip()}")
    except Exception:
        pass

    # git diff HEAD -- ficheiros Python
    try:
        r = subprocess.run(
            ["git", "diff", "HEAD", "--stat", "--", "*.py"],
            capture_output=True, text=True, timeout=10, cwd=str(morgan_dir)
        )
        if r.stdout.strip():
            partes.append(f"GIT DIFF STAT:\n{r.stdout.strip()[:800]}")
    except Exception:
        pass

    # últimas linhas do log de servidor
    log_path = morgan_dir / "morgan_server.log"
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = "\n".join(lines[-30:])
            partes.append(f"LOG SERVIDOR (últimas 30 linhas):\n{tail}")
        except Exception:
            pass

    return "\n\n".join(partes) if partes else "(contexto não disponível)"


def _atomic_git_snapshot(problema: str) -> str:
    """Sprint 1: cria git tag pre-fix antes de executar. Permite rollback trivial."""
    morgan_dir = Path(__file__).parent
    tag = f"pre-fix-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    try:
        r = subprocess.run(
            ["git", "tag", tag],
            capture_output=True, text=True, timeout=10, cwd=str(morgan_dir)
        )
        if r.returncode == 0:
            return f"Snapshot criado: git tag {tag} (rollback: git checkout {tag})"
        return f"Snapshot falhou: {r.stderr.strip()[:100]}"
    except Exception as e:
        return f"Snapshot indisponível: {e}"


def _dependency_health_check() -> str:
    """Sprint 2: verifica saúde das dependências críticas antes de executar."""
    import sys
    deps = {
        "anthropic": "claude-sonnet-4-6",
        "fastapi": "servidor HTTP",
        "langgraph": "grafo Solver",
        "ccxt": "trading Binance",
        "playwright": "browser automation",
        "qdrant_client": "memória vectorial",
        "dotenv": "variáveis de ambiente",
    }
    resultados = []
    falhas = []
    for dep, descricao in deps.items():
        try:
            r = subprocess.run(
                [sys.executable, "-c", f"import {dep}"],
                capture_output=True, text=True, timeout=8,
                cwd=str(Path(__file__).parent)
            )
            if r.returncode == 0:
                resultados.append(f"OK: {dep}")
            else:
                falhas.append(f"ERRO: {dep} ({descricao}) — {r.stderr.strip()[:80]}")
        except Exception as e:
            falhas.append(f"TIMEOUT/ERRO: {dep} — {e}")

    resumo = "\n".join(resultados + falhas)
    if falhas:
        resumo = f"⚠ {len(falhas)} dependência(s) em falta:\n" + resumo
    return resumo

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
    modo: str             # "fix" | "explain"
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
    attempt_count: int    # tentativas de execução — máximo 2


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
    # Sprint 1: contexto git + logs
    contexto = _gather_context()
    contexto_bloco = f"\n\nCONTEXTO DO SISTEMA:\n{contexto}\n"

    # Sprint 2: saúde das dependências
    dep_health = _dependency_health_check()
    dep_bloco = f"\n\nSAÚDE DAS DEPENDÊNCIAS:\n{dep_health}\n" if dep_health else ""

    fixes_hist = _fixes_relevantes(state["problema"])
    historico_bloco = f"\n\nFIXES ANTERIORES RELEVANTES (BM25):\n{fixes_hist}\n" if fixes_hist else ""
    recorrente = _erro_recorrente(state["problema"])
    recorrente_bloco = "\n⚠ ATENÇÃO: Este erro é recorrente (>2x em 24h) — indica causa sistémica, não pontual.\n" if recorrente else ""
    circuit = _circuit_breaker(state["problema"])
    circuit_bloco = "\n🔴 CIRCUIT BREAKER: erro apareceu ≥3x em 2h — diagnóstico urgente, escalar ao Vasco após.\n" if circuit else ""

    system = f"""És o Morgan Solver — agente de diagnóstico e correcção do sistema Morgan.{contexto_bloco}{dep_bloco}{historico_bloco}{recorrente_bloco}{circuit_bloco}

REGRA DE DIAGNÓSTICO OBRIGATÓRIA:
- Nunca afirmes uma causa que não consegues apontar no código com linha específica
- Preenche obrigatoriamente: causa_raiz, evidência (ficheiro:linha), hipóteses_alternativas
- Se não encontras evidência concreta: confiança deve ser <70%
- "Never state a cause you cannot point to in the code."

Obrigatório no final da resposta, neste formato exacto:
DIAGNÓSTICO: [causa raiz + evidência ficheiro:linha]
HIPÓTESES_ALTERNATIVAS: [outras causas possíveis se existirem]
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
    # Limite de tentativas — evita loops infinitos
    attempt = state.get("attempt_count", 0)
    if attempt >= 2:
        return {**state,
                "execucao": "ABORTADO — limite de 2 tentativas atingido. Escalar ao Vasco.",
                "confianca_execucao": 0,
                "attempt_count": attempt}

    # Sprint 1: snapshot atómico antes de qualquer mudança
    snapshot_info = _atomic_git_snapshot(state["problema"])

    # Testes pré-execução — valida sintaxe e imports antes de qualquer correcção
    passou, relatorio_testes = _pre_execution_tests()
    if not passou:
        return {**state,
                "execucao": f"ABORTADO — testes pré-execução falharam:\n{relatorio_testes}",
                "confianca_execucao": 0,
                "attempt_count": attempt + 1}

    system = f"""És o Morgan Solver. Executa o plano aprovado com as ferramentas disponíveis.
{snapshot_info} — em caso de falha: git checkout <tag>
Documenta cada passo e o resultado. Para imediatamente se algo correr mal.

Testes pré-execução passaram:
{relatorio_testes}

FLUXO DE CORRECÇÃO OBRIGATÓRIO:
1. solver_ler_ficheiro — ler antes de qualquer edição
2. solver_editar_ficheiro para edições cirúrgicas (preferível) ou solver_criar_ficheiro para reescritas
3. solver_git_commit_push — deploy automático via GitHub Actions

FICHEIROS E ACÇÕES PROIBIDAS SEM APROVAÇÃO EXPLÍCITA DO VASCO:
- memory/*.json, memory/*.md (estado do sistema)
- .env ou qualquer ficheiro com credenciais
- trading_bot.py ou qualquer lógica de trading
- Funções que enviam emails, fazem chamadas a APIs externas de pagamento
- Qualquer alteração em scheduling ou lógica de briefings (desktop_server.py heartbeat)
- Apagar ficheiros — nunca, sem aprovação
- Regra geral: se o fix toca mais do que um boundary de módulo → escalar

Obrigatório no final da resposta, neste formato exacto:
EXECUÇÃO: [o que foi feito, ficheiro:linha]
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
    return {**state, "execucao": texto, "confianca_execucao": confianca, "attempt_count": attempt + 1}


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

    problema = state['problema']
    cd = state.get('confianca_diagnostico', '?')
    cs = state.get('confianca_solucao', '?')
    ce = state.get('confianca_execucao', '?')
    cv = state.get('confianca_verificacao', '?')
    impacto = state.get('impacto', 'desconhecido')
    reversivel = 'Sim' if state.get('reversivel') else 'Não'

    # Modo explain — só diagnóstico, sem execução
    if state.get("modo") == "explain":
        relatorio = (
            f"SOLVER — Diagnóstico\n"
            f"Problema: {problema}\n"
            f"Confiança: {cd}% | Reversível: {reversivel} | Impacto: {impacto}\n\n"
            f"{state['diagnostico']}"
        )
    elif state.get("requer_aprovacao") and not state.get("aprovado"):
        relatorio = (
            f"SOLVER — Aguarda aprovação\n"
            f"Problema: {problema}\n"
            f"Confiança diagnóstico: {cd}% | Confiança solução: {cs}%\n"
            f"Reversível: {reversivel} | Impacto: {impacto}\n\n"
            f"DIAGNÓSTICO:\n{state['diagnostico']}\n\n"
            f"PLANO PROPOSTO:\n{state['plano']}\n\n"
            f"→ Responde com solver_diagnosticar(problema, aprovado=True) para executar."
        )
    else:
        via_claude = state.get("confianca_solucao", 100) < 90 or _erro_recorrente(problema)
        executor = "Claude Code (escalado)" if via_claude else "Solver autónomo"
        verificacao_txt = state.get('verificacao', '')
        resolvido = "RESOLVIDO" in verificacao_txt.upper() and "NÃO_RESOLVIDO" not in verificacao_txt.upper()
        estado_final = "RESOLVIDO" if resolvido else "NÃO RESOLVIDO — verificar manualmente"

        relatorio = (
            f"SOLVER — {estado_final}\n"
            f"Problema: {problema}\n"
            f"Executor: {executor} | Tentativas: {state.get('attempt_count', 1)}\n"
            f"Confiança: diag {cd}% / solução {cs}% / execução {ce}% / verificação {cv}%\n"
            f"Reversível: {reversivel} | Impacto: {impacto}\n\n"
            f"DIAGNÓSTICO:\n{state['diagnostico']}\n\n"
            f"EXECUÇÃO:\n{state['execucao']}\n\n"
            f"VERIFICAÇÃO:\n{verificacao_txt}"
        )

    return {**state, "relatorio": relatorio}


# ── Edges condicionais ────────────────────────────────────────────────────────

def decide_apos_diagnostico(state: SolverState) -> str:
    """Se modo=explain, salta directamente para relatório sem executar nada."""
    if state.get("modo") == "explain":
        return "relatorio"
    return "plano"


def decide_apos_plano(state: SolverState) -> str:
    if state.get("requer_aprovacao"):
        return "aguardar_aprovacao"
    problema = state.get("problema", "")
    confianca = state.get("confianca_solucao", 50)
    # Circuit breaker: ≥3x em 2h → escalar directamente, não tentar mais
    if _circuit_breaker(problema):
        return "escalar_claude_code"
    # Escalar se confiança baixa OU se o erro é recorrente (causa sistémica)
    if confianca < 90 or _erro_recorrente(problema):
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
    grafo.add_conditional_edges("diagnostico", decide_apos_diagnostico, {
        "relatorio": "relatorio",
        "plano": "plano",
    })
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


def solver_diagnosticar(problema: str, aprovado: bool = False, modo: str = "fix") -> dict:
    """
    modo='fix': pipeline completo Diagnose→Plan→Execute→Verify→Report
    modo='explain': só diagnóstico, sem execução (para o Vasco perceber o que se passa)
    """
    global _graph
    if _graph is None:
        _graph = build_solver_graph()

    estado_inicial: SolverState = {
        "messages": [],
        "problema": problema,
        "modo": modo,
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
        "attempt_count": 0,
    }

    return _graph.invoke(estado_inicial)


def solver_explicar(problema: str) -> str:
    """Modo explain — só diagnóstico, sem executar nenhum fix."""
    resultado = solver_diagnosticar(problema, modo="explain")
    return resultado.get("relatorio", "Solver sem diagnóstico.")
