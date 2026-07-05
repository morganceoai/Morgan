import json
import os
from datetime import date

SCOUT_FILE = os.path.join(os.path.dirname(__file__), "memory", "scout_memoria.json")


def _load() -> dict:
    if not os.path.exists(SCOUT_FILE):
        return {"oportunidades": {}, "historico_semanal": [], "aprovadas": []}
    with open(SCOUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    os.makedirs(os.path.dirname(SCOUT_FILE), exist_ok=True)
    tmp = SCOUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SCOUT_FILE)  # atómico — evita corrupção por write concorrente


def registar_oportunidades(oportunidades: list[dict]):
    """
    Regista as oportunidades desta semana e actualiza o histórico.
    Cada oportunidade: {"nome": str, "descricao": str, "receita_estimada": str, "notas": str}
    """
    data = _load()
    semana = date.today().strftime("%Y-W%W")

    for op in oportunidades:
        nome = op.get("nome", "").strip()
        if not nome:
            continue
        if nome not in data["oportunidades"]:
            data["oportunidades"][nome] = {
                "primeira_vez": semana,
                "vezes_visto": 0,
                "semanas": [],
                "descricao": op.get("descricao", ""),
                "receita_estimada": op.get("receita_estimada", ""),
                "notas": [],
            }
        entry = data["oportunidades"][nome]
        if semana not in entry["semanas"]:
            entry["vezes_visto"] += 1
            entry["semanas"].append(semana)
        if op.get("notas"):
            entry["notas"].append(f"{semana}: {op['notas']}")
        entry["notas"] = entry["notas"][-10:]

    data["historico_semanal"].append({
        "semana": semana,
        "oportunidades": [op.get("nome") for op in oportunidades],
    })
    data["historico_semanal"] = data["historico_semanal"][-52:]
    _save(data)


def aprovar_oportunidade(nome: str):
    """Marca uma oportunidade como aprovada pelo Vasco para acompanhamento contínuo."""
    data = _load()
    semana = date.today().strftime("%Y-W%W")
    if nome not in data["aprovadas"]:
        data["aprovadas"].append({"nome": nome, "aprovada_em": semana, "updates": []})
    _save(data)


def get_contexto_scout() -> str:
    """Devolve o contexto acumulado para o Scout usar no relatório desta semana."""
    data = _load()
    semana_atual = date.today().strftime("%Y-W%W")
    linhas = []

    # Oportunidades recorrentes (vistas 2+ semanas)
    recorrentes = [
        (nome, info) for nome, info in data["oportunidades"].items()
        if info["vezes_visto"] >= 2
    ]
    recorrentes.sort(key=lambda x: x[1]["vezes_visto"], reverse=True)

    if recorrentes:
        linhas.append("## Oportunidades recorrentes (sinal forte):")
        for nome, info in recorrentes[:5]:
            linhas.append(
                f"- **{nome}** — vista {info['vezes_visto']}x "
                f"(desde {info['primeira_vez']}). {info['descricao']}"
            )

    # Oportunidades aprovadas pelo Vasco
    if data["aprovadas"]:
        linhas.append("\n## Oportunidades aprovadas pelo Vasco (monitorizar de perto):")
        for ap in data["aprovadas"]:
            nome = ap["nome"]
            info = data["oportunidades"].get(nome, {})
            linhas.append(
                f"- **{nome}** (aprovada em {ap['aprovada_em']}) "
                f"— vista {info.get('vezes_visto', 1)}x no total"
            )

    # Semanas anteriores para evitar repetição desnecessária
    semanas_anteriores = [
        h for h in data["historico_semanal"]
        if h["semana"] != semana_atual
    ]
    if semanas_anteriores:
        ultima = semanas_anteriores[-1]
        linhas.append(f"\n## Semana anterior ({ultima['semana']}):")
        linhas.append("Oportunidades identificadas: " + ", ".join(ultima["oportunidades"]))

    if not linhas:
        return "Primeira semana de análise — sem histórico anterior."

    return "\n".join(linhas)


def get_resumo_para_vasco() -> str:
    """Resumo do histórico do Scout para o Vasco consultar."""
    data = _load()
    if not data["oportunidades"]:
        return "O Scout ainda não tem histórico acumulado. Primeiro relatório no próximo domingo."

    linhas = ["**Histórico do Morgan AI Scout**\n"]
    linhas.append(f"Total de oportunidades identificadas: {len(data['oportunidades'])}")
    linhas.append(f"Semanas analisadas: {len(data['historico_semanal'])}\n")

    recorrentes = sorted(
        data["oportunidades"].items(),
        key=lambda x: x[1]["vezes_visto"],
        reverse=True
    )
    linhas.append("**Por força do sinal (mais vistas):**")
    for nome, info in recorrentes[:8]:
        linhas.append(f"• {nome} — {info['vezes_visto']}x | {info['receita_estimada']}")

    if data["aprovadas"]:
        linhas.append("\n**Aprovadas pelo Vasco:**")
        for ap in data["aprovadas"]:
            linhas.append(f"• {ap['nome']} (desde {ap['aprovada_em']})")

    return "\n".join(linhas)
