"""
Morgan — Memory Store
Acesso unificado à memória do sistema: factos permanentes + base de conhecimento episódica.
"""
import os
from pathlib import Path

MEMORY_DIR = Path(__file__).parent / "memory"
MEMORY_FILE = MEMORY_DIR / "factos.md"


# ── Factos permanentes (factos.md) ────────────────────────────────────────────

def load_memory() -> str:
    if not MEMORY_FILE.exists():
        return ""
    return MEMORY_FILE.read_text(encoding="utf-8").strip()


def save_fact(facto: str) -> str:
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"- {facto}\n")
    return f"Guardei: {facto}"


def remove_fact(facto: str) -> str:
    if not MEMORY_FILE.exists():
        return "Não há memória guardada."
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = [l for l in lines if facto.lower() not in l.lower()]
    if len(new_lines) == len(lines):
        return f"Não encontrei nenhum facto com '{facto}'."
    MEMORY_FILE.write_text("".join(new_lines), encoding="utf-8")
    return f"Removi o facto sobre '{facto}'."


def list_memory() -> str:
    content = load_memory()
    return content if content else "Não tenho nada guardado ainda."


# ── Base de conhecimento episódica ────────────────────────────────────────────
# Re-exporta as funções principais da camada episódica para uso directo

def consultar_base(query: str, agente: str | None = None, limite: int = 20) -> str:
    """Consulta a base de conhecimento em linguagem natural. Ferramenta do CEO."""
    from episodic_memory import consultar_base as _cb
    return _cb(query, agente=agente, limite=limite)


def registar_evento(agente: str, tema: str, conteudo: str, dados: dict | None = None) -> bool:
    """Atalho para registar_evento da camada episódica."""
    from episodic_memory import registar_evento as _re
    return _re(agente, tema, conteudo, dados)
