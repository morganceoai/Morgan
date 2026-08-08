"""
Hook do Claude Code — regista acções da sessão no knowledge_base.jsonl do Morgan.

Chamado por PostToolUse (Write/Edit/Bash) e Stop hooks.
Recebe JSON no stdin com: session_id, tool_name, tool_input, tool_response
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

MORGAN_DIR = Path(__file__).parent.parent
KB_FILE = MORGAN_DIR / "memory" / "knowledge_base.jsonl"

# Comandos bash que não vale a pena registar
BASH_IGNORAR = {
    "cat ", "ls ", "head ", "tail ", "wc ", "grep ", "find ",
    "echo ", "pwd", "which ", "git log", "git status", "git diff",
    "curl -sf http://localhost:8765/health",
    "source venv", "python3 -c \"import",
}


def _ignorar_bash(cmd: str) -> bool:
    cmd_strip = cmd.strip()
    for prefixo in BASH_IGNORAR:
        if cmd_strip.startswith(prefixo):
            return True
    return False


def _append(evento: dict):
    KB_FILE.parent.mkdir(exist_ok=True)
    with open(KB_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
    ts = datetime.now(timezone.utc).isoformat()

    if tool in ("Write", "Edit"):
        caminho = inp.get("file_path", inp.get("path", ""))
        # Só ficheiros do projecto Morgan
        if "Morgan" not in caminho and not caminho.startswith("/"):
            return
        # Ignorar ficheiros de memória e temporários
        nome = Path(caminho).name
        if nome in ("knowledge_base.jsonl", "cfo_phase_cache.json", "runtime_state.json",
                    "trading_state.json", "health_baseline.json"):
            return

        acao = "criado" if tool == "Write" else "editado"
        rel = caminho.replace(str(MORGAN_DIR) + "/", "")
        _append({
            "ts": ts,
            "agente": "claude_code",
            "tema": f"ficheiro_{acao}",
            "conteudo": f"{rel}",
            "dados": {"ferramenta": tool},
        })

    elif tool == "Bash":
        cmd = inp.get("command", "")
        if not cmd or _ignorar_bash(cmd):
            return
        # Registar comandos que mudam estado
        _append({
            "ts": ts,
            "agente": "claude_code",
            "tema": "bash_executado",
            "conteudo": cmd[:300],
        })

    elif tool == "" or data == {}:
        # Stop hook — fim de sessão
        _append({
            "ts": ts,
            "agente": "claude_code",
            "tema": "sessao_terminada",
            "conteudo": f"Sessão Claude Code terminada — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC",
        })


if __name__ == "__main__":
    main()
