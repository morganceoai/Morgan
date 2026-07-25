"""
Usado pelo Claude Code durante sessões para registar acções importantes.
Escreve em memory/claude_session_log.jsonl (flush para Notion no Stop hook).
Também pode enviar directamente para o Notion se chamado com --directo.
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()


def log(tipo: str, conteudo: str, directo: bool = False):
    """
    tipo: "Decisão" | "Fix" | "Deploy" | "Acção" | "Conversa"
    conteudo: descrição do que aconteceu
    directo: True → envia para Notion imediatamente
    """
    entrada = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tipo": tipo,
        "conteudo": conteudo,
    }

    # Guardar no log da sessão
    log_path = ROOT / "memory" / "claude_session_log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")

    # Enviar directamente ao Notion se pedido
    if directo:
        try:
            from notion_service import diario_log
            diario_log("Claude Code", tipo, conteudo)
        except Exception:
            pass


if __name__ == "__main__":
    # Uso: python scripts/claude_log.py "Fix" "Corrigido bug X em tools.py" [--directo]
    if len(sys.argv) >= 3:
        _tipo = sys.argv[1]
        _conteudo = sys.argv[2]
        _directo = "--directo" in sys.argv
        log(_tipo, _conteudo, directo=_directo)
        print(f"[claude_log] {_tipo}: {_conteudo[:80]}")
    else:
        print("Uso: python scripts/claude_log.py <tipo> <conteudo> [--directo]")
