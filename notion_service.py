"""
notion_service.py — integração com o Notion para o Morgan.

Cria e gere páginas nas 5 áreas do Espaço de Vasco:
  BCVertex | Moreirense FC | Lego | Condomínio | Vida Pessoal

Variáveis de ambiente:
  NOTION_TOKEN  — token de acesso pessoal (ntn_...)
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

import requests

logger = logging.getLogger("notion_service")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# IDs das páginas raiz (preenchidos após setup)
_IDS_FILE = __import__("pathlib").Path(__file__).parent / "memory" / "notion_ids.json"


def _load_ids() -> dict:
    if _IDS_FILE.exists():
        return json.loads(_IDS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_ids(ids: dict):
    _IDS_FILE.parent.mkdir(exist_ok=True)
    _IDS_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")


def _get(path: str) -> dict:
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(path: str, data: dict) -> dict:
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=10)
    r.raise_for_status()
    return r.json()


def _patch(path: str, data: dict) -> dict:
    r = requests.patch(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=10)
    r.raise_for_status()
    return r.json()


def is_configured() -> bool:
    return bool(NOTION_TOKEN)


# ── Criação de páginas ────────────────────────────────────────────────────────

def _criar_pagina(parent_id: str, titulo: str, emoji: str = "📄", conteudo: list = None) -> str:
    """Cria uma página filha e devolve o seu ID."""
    data = {
        "parent": {"page_id": parent_id},
        "icon": {"type": "emoji", "emoji": emoji},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": titulo}}]}
        },
    }
    if conteudo:
        data["children"] = conteudo
    result = _post("/pages", data)
    return result["id"]


def _criar_pagina_raiz(titulo: str, emoji: str = "📄") -> str:
    """Cria uma página no nível raiz do workspace."""
    data = {
        "parent": {"type": "workspace", "workspace": True},
        "icon": {"type": "emoji", "emoji": emoji},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": titulo}}]}
        },
    }
    result = _post("/pages", data)
    return result["id"]


def _bloco_titulo(texto: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": texto}}]},
    }


def _bloco_paragrafo(texto: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": texto}}]},
    }


def _bloco_divisor() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


# ── Setup inicial — cria estrutura completa ───────────────────────────────────

def setup_estrutura() -> str:
    """Cria as 5 áreas principais no Notion. Corre uma vez."""
    if not is_configured():
        return "NOTION_TOKEN não definido."

    ids = _load_ids()
    criados = []

    # 1. BCVertex
    if "bc_industries" not in ids:
        pid = _criar_pagina_raiz("BCVertex", "🏢")
        ids["bc_industries"] = pid
        # Sub-páginas
        ids["bc_oportunidades"] = _criar_pagina(pid, "Pipeline de Oportunidades", "🔍", [
            _bloco_titulo("Oportunidades em avaliação"),
            _bloco_paragrafo("O Scout adiciona aqui as oportunidades identificadas."),
            _bloco_divisor(),
            _bloco_titulo("Aprovadas"),
            _bloco_titulo("Rejeitadas"),
        ])
        ids["bc_negocios"] = _criar_pagina(pid, "Negócios Activos", "💼", [
            _bloco_titulo("PlannerAtlas — Etsy"),
            _bloco_paragrafo("24 listings activos | planneratlas.etsy.com"),
            _bloco_divisor(),
            _bloco_titulo("Lego Arbitrage"),
            _bloco_titulo("Prompt Packs"),
        ])
        ids["bc_financas"] = _criar_pagina(pid, "Finanças BCVertex", "💰", [
            _bloco_titulo("Receitas mensais"),
            _bloco_titulo("Despesas (APIs, serviços)"),
            _bloco_titulo("Binance Trading"),
            _bloco_paragrafo("Bots activos: Grid BTC/USDT | Grid ETH/USDT | SOL DCA — $100 cada, Binance spot"),
        ])
        ids["bc_sprints"] = _criar_pagina(pid, "Sprints de Desenvolvimento", "⚡", [
            _bloco_titulo("Em curso"),
            _bloco_titulo("Concluídos"),
            _bloco_titulo("Pendentes"),
        ])
        criados.append("BCVertex")

    # 2. Lego
    if "lego" not in ids:
        pid = _criar_pagina_raiz("Lego", "🧱")
        ids["lego"] = pid
        ids["lego_inventario"] = _criar_pagina(pid, "Inventário", "📦", [
            _bloco_titulo("Sets completos"),
            _bloco_paragrafo("Adicionar: nome, número, estado, preço pago, valor BrickLink actual"),
            _bloco_divisor(),
            _bloco_titulo("Sets incompletos / para peças"),
        ])
        ids["lego_bricklink"] = _criar_pagina(pid, "BrickLink — Loja", "🛒", [
            _bloco_titulo("À venda"),
            _bloco_titulo("Vendidos"),
            _bloco_titulo("Watchlist — sets a comprar"),
        ])
        ids["lego_precos"] = _criar_pagina(pid, "Análise de Preços", "📈", [
            _bloco_titulo("Sets com maior valorização histórica"),
            _bloco_paragrafo("O Morgan monitoriza OLX, Vinted, CustoJusto para oportunidades."),
        ])
        criados.append("Lego")

    # 3. Condomínio
    if "condominio" not in ids:
        pid = _criar_pagina_raiz("Condomínio", "🏘️")
        ids["condominio"] = pid
        ids["condominio_actas"] = _criar_pagina(pid, "Actas de Reunião", "📋")
        ids["condominio_financas"] = _criar_pagina(pid, "Finanças do Condomínio", "💳", [
            _bloco_titulo("Quotas mensais"),
            _bloco_titulo("Despesas comuns"),
            _bloco_titulo("Fundo de reserva"),
        ])
        ids["condominio_ocorrencias"] = _criar_pagina(pid, "Ocorrências e Manutenção", "🔧", [
            _bloco_titulo("Abertas"),
            _bloco_titulo("Resolvidas"),
        ])
        ids["condominio_prazos"] = _criar_pagina(pid, "Prazos e Calendário", "📅")
        criados.append("Condomínio")

    # 4. Moreirense FC
    if "moreirense" not in ids:
        pid = _criar_pagina_raiz("Moreirense FC", "⚽")
        ids["moreirense"] = pid
        ids["moreirense_plantel"] = _criar_pagina(pid, "Plantel", "👥")
        ids["moreirense_analises"] = _criar_pagina(pid, "Análises de Jogo", "🎯")
        ids["moreirense_scouting"] = _criar_pagina(pid, "Scouting", "🔭")
        criados.append("Moreirense FC")

    # 5. Vida Pessoal
    if "pessoal" not in ids:
        pid = _criar_pagina_raiz("Vida Pessoal", "🌟")
        ids["pessoal"] = pid
        ids["pessoal_objetivos"] = _criar_pagina(pid, "Objectivos", "🎯", [
            _bloco_titulo("2026"),
            _bloco_paragrafo("€10.000/mês de rendimento passivo via BCVertex"),
        ])
        ids["pessoal_notas"] = _criar_pagina(pid, "Notas Rápidas", "📝")
        criados.append("Vida Pessoal")

    _save_ids(ids)

    if criados:
        return f"Estrutura criada: {', '.join(criados)}\nIDs guardados em memory/notion_ids.json"
    return "Estrutura já existia — sem alterações."


# ── Funções de escrita (usadas pelos agentes) ─────────────────────────────────

def registar_oportunidade(nome: str, descricao: str, estado: str = "Em avaliação") -> str:
    """Scout chama isto quando identifica uma nova oportunidade."""
    ids = _load_ids()
    if "bc_oportunidades" not in ids:
        return "Página de oportunidades não encontrada — corre setup_estrutura() primeiro."
    try:
        data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _post("/pages", {
            "parent": {"page_id": ids["bc_oportunidades"]},
            "icon": {"type": "emoji", "emoji": "🔍"},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": f"[{data}] {nome}"}}]}
            },
            "children": [
                _bloco_paragrafo(f"Estado: {estado}"),
                _bloco_divisor(),
                _bloco_paragrafo(descricao),
            ],
        })
        return f"Oportunidade '{nome}' registada no Notion."
    except Exception as e:
        return f"Erro ao registar oportunidade: {e}"


def registar_acta_condominio(data: str, assuntos: str, decisoes: str) -> str:
    """Operator chama isto após reunião de condomínio."""
    ids = _load_ids()
    if "condominio_actas" not in ids:
        return "Página de actas não encontrada — corre setup_estrutura() primeiro."
    try:
        _post("/pages", {
            "parent": {"page_id": ids["condominio_actas"]},
            "icon": {"type": "emoji", "emoji": "📋"},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": f"Acta {data}"}}]}
            },
            "children": [
                _bloco_titulo("Assuntos tratados"),
                _bloco_paragrafo(assuntos),
                _bloco_divisor(),
                _bloco_titulo("Decisões"),
                _bloco_paragrafo(decisoes),
            ],
        })
        return f"Acta de {data} registada no Notion."
    except Exception as e:
        return f"Erro ao registar acta: {e}"


def adicionar_lego_set(nome: str, numero: str, estado: str, preco_pago: float, valor_bricklink: float) -> str:
    """Adiciona um set Lego ao inventário."""
    ids = _load_ids()
    if "lego_inventario" not in ids:
        return "Inventário Lego não encontrado — corre setup_estrutura() primeiro."
    try:
        margem = round((valor_bricklink - preco_pago) / preco_pago * 100, 1) if preco_pago > 0 else 0
        _post("/pages", {
            "parent": {"page_id": ids["lego_inventario"]},
            "icon": {"type": "emoji", "emoji": "🧱"},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": f"{numero} — {nome}"}}]}
            },
            "children": [
                _bloco_paragrafo(f"Estado: {estado}"),
                _bloco_paragrafo(f"Preço pago: €{preco_pago:.2f}"),
                _bloco_paragrafo(f"Valor BrickLink: €{valor_bricklink:.2f}"),
                _bloco_paragrafo(f"Margem potencial: {margem}%"),
            ],
        })
        return f"Set {numero} '{nome}' adicionado ao inventário Lego."
    except Exception as e:
        return f"Erro ao adicionar set: {e}"


# ── Diário Morgan — log cronológico de tudo ───────────────────────────────────

# Fontes possíveis: "Claude Code", "CEO", "Scout", "Coach", "CFO",
#                   "Creator", "Marketeer", "Operator", "Solver"
# Tipos possíveis:  "Decisão", "Acção", "Fix", "Briefing", "Conversa",
#                   "Erro", "Sessão", "Deploy"

def _setup_diario() -> str:
    """Cria a base de dados 'Diário Morgan' no Notion (corre automaticamente na 1ª chamada)."""
    ids = _load_ids()
    if "diario_db" in ids:
        return ids["diario_db"]

    # Cria página raiz "Morgan — Diário"
    raiz = _criar_pagina_raiz("Morgan — Diário", "📓")
    ids["diario_raiz"] = raiz

    # Cria database dentro da página raiz
    r = requests.post(f"{BASE_URL}/databases", headers=HEADERS, json={
        "parent": {"type": "page_id", "page_id": raiz},
        "icon": {"type": "emoji", "emoji": "📓"},
        "title": [{"type": "text", "text": {"content": "Diário Morgan"}}],
        "properties": {
            "Nome": {"title": {}},
            "Data": {"date": {}},
            "Fonte": {
                "select": {
                    "options": [
                        {"name": "Claude Code", "color": "blue"},
                        {"name": "CEO",         "color": "purple"},
                        {"name": "Scout",       "color": "green"},
                        {"name": "Coach",       "color": "yellow"},
                        {"name": "CFO",         "color": "orange"},
                        {"name": "Creator",     "color": "pink"},
                        {"name": "Marketeer",   "color": "red"},
                        {"name": "Operator",    "color": "brown"},
                        {"name": "Solver",      "color": "gray"},
                    ]
                }
            },
            "Tipo": {
                "select": {
                    "options": [
                        {"name": "Decisão",   "color": "blue"},
                        {"name": "Acção",     "color": "green"},
                        {"name": "Fix",       "color": "red"},
                        {"name": "Briefing",  "color": "purple"},
                        {"name": "Conversa",  "color": "yellow"},
                        {"name": "Erro",      "color": "orange"},
                        {"name": "Sessão",    "color": "gray"},
                        {"name": "Deploy",    "color": "pink"},
                    ]
                }
            },
        },
    }, timeout=15)
    r.raise_for_status()
    db_id = r.json()["id"]
    ids["diario_db"] = db_id
    _save_ids(ids)
    return db_id


def diario_log(fonte: str, tipo: str, conteudo: str, titulo: str = "") -> None:
    """
    Regista uma entrada no Diário Morgan.
    Criação automática da base de dados na primeira chamada.
    Falha silenciosa — nunca bloqueia o fluxo principal.

    Args:
        fonte:    quem gerou a entrada ("Claude Code", "CEO", "Scout", etc.)
        tipo:     categoria ("Decisão", "Acção", "Fix", "Briefing", "Sessão", etc.)
        conteudo: descrição completa do que aconteceu
        titulo:   título curto opcional (gerado automaticamente se vazio)
    """
    if not NOTION_TOKEN:
        return
    try:
        db_id = _setup_diario()
        agora = datetime.now(timezone.utc)
        titulo_final = titulo or f"[{fonte}] {conteudo[:60]}{'...' if len(conteudo) > 60 else ''}"

        requests.post(f"{BASE_URL}/pages", headers=HEADERS, json={
            "parent": {"database_id": db_id},
            "icon": {"type": "emoji", "emoji": _emoji_para_tipo(tipo)},
            "properties": {
                "Nome": {"title": [{"type": "text", "text": {"content": titulo_final}}]},
                "Data": {"date": {"start": agora.isoformat()}},
                "Fonte": {"select": {"name": fonte}},
                "Tipo":  {"select": {"name": tipo}},
            },
            "children": [
                _bloco_paragrafo(conteudo),
            ],
        }, timeout=10)
    except Exception:
        pass  # falha silenciosa


def _emoji_para_tipo(tipo: str) -> str:
    return {
        "Decisão":  "🧭",
        "Acção":    "⚡",
        "Fix":      "🔧",
        "Briefing": "📋",
        "Conversa": "💬",
        "Erro":     "🚨",
        "Sessão":   "🔵",
        "Deploy":   "🚀",
    }.get(tipo, "📝")


def estado_notion() -> str:
    """Resumo do estado da integração Notion."""
    if not is_configured():
        return "Notion: não configurado (NOTION_TOKEN em falta)."
    ids = _load_ids()
    areas = ["bc_industries", "lego", "condominio", "moreirense", "pessoal"]
    configuradas = [a for a in areas if a in ids]
    return (
        f"Notion: configurado ✓\n"
        f"Áreas criadas: {len(configuradas)}/5 — {', '.join(configuradas)}"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        print(setup_estrutura())
    else:
        print(estado_notion())
