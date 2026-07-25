"""
Script chamado pelo hook Stop do Claude Code.
Regista no Diário Morgan que a sessão terminou.
Lê memory/claude_session_log.jsonl para incluir o que foi feito.
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

# Adicionar raiz do projecto ao path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

try:
    from notion_service import diario_log

    # Ler log da sessão se existir
    log_path = ROOT / "memory" / "claude_session_log.jsonl"
    entradas = []
    if log_path.exists():
        for linha in log_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                entradas.append(json.loads(linha))
            except Exception:
                pass
        # Limpar após leitura
        log_path.write_text("", encoding="utf-8")

    if entradas:
        resumo = "\n".join(f"• [{e.get('tipo','?')}] {e.get('conteudo','')}" for e in entradas)
        titulo = f"Sessão Claude Code — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}"
        diario_log("Claude Code", "Sessão", resumo, titulo=titulo)
    else:
        diario_log("Claude Code", "Sessão",
                   f"Sessão terminada — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
                   titulo=f"Sessão Claude Code — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")

except Exception as e:
    # Falha silenciosa — nunca bloquear o Claude Code
    pass
