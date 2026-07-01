import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory", "factos.md")


def load_memory() -> str:
    if not os.path.exists(MEMORY_FILE):
        return ""
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_fact(facto: str) -> str:
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"- {facto}\n")
    return f"Guardei: {facto}"


def remove_fact(facto: str) -> str:
    if not os.path.exists(MEMORY_FILE):
        return "Não há memória guardada."
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = [l for l in lines if facto.lower() not in l.lower()]
    if len(new_lines) == len(lines):
        return f"Não encontrei nenhum facto com '{facto}'."
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return f"Removi o facto sobre '{facto}'."


def list_memory() -> str:
    content = load_memory()
    if not content:
        return "Não tenho nada guardado ainda."
    return content
