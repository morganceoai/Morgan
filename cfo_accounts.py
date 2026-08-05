"""
CFO Accounts — Registo unificado de todas as contas do império BCVertex.
O CFO não conhece ficheiros individuais — conhece contas registadas aqui.
Adicionar um negócio novo = registar uma conta. O CFO fica intacto.
"""
import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).parent
_ACCOUNTS_FILE = _BASE / "memory" / "cfo_accounts.json"

# Tipos de conta
TIPO_TRADING   = "trading"
TIPO_LOJA      = "loja"
TIPO_CONTEUDO  = "conteudo"
TIPO_SERVICO   = "servico"
TIPO_BANCO     = "banco"

# Estado
ESTADO_ACTIVO   = "activo"
ESTADO_PAUSADO  = "pausado"
ESTADO_PENDENTE = "pendente"
ESTADO_INACTIVO = "inactivo"


def _load() -> list:
    try:
        return json.loads(_ACCOUNTS_FILE.read_text())
    except Exception:
        return []

def _save(accounts: list):
    _ACCOUNTS_FILE.parent.mkdir(exist_ok=True)
    _ACCOUNTS_FILE.write_text(json.dumps(accounts, ensure_ascii=False, indent=2))


def registar_conta(
    id: str,
    nome: str,
    tipo: str,
    plataforma: str,
    capital_alocado: float,
    moeda: str = "USDT",
    collector: str = "",
    estado: str = ESTADO_ACTIVO,
    meta_mensal: float = 0.0,
    notas: str = "",
) -> dict:
    """Regista uma nova conta no império. Idempotente — não duplica se id já existe."""
    accounts = _load()
    for a in accounts:
        if a["id"] == id:
            return a  # já existe

    conta = {
        "id": id,
        "nome": nome,
        "tipo": tipo,
        "plataforma": plataforma,
        "capital_alocado": capital_alocado,
        "moeda": moeda,
        "collector": collector,
        "estado": estado,
        "meta_mensal": meta_mensal,
        "notas": notas,
        "criado_em": datetime.now().isoformat(),
        "pnl_total": 0.0,
        "pnl_mes": 0.0,
        "ultimo_snapshot": None,
    }
    accounts.append(conta)
    _save(accounts)
    return conta


def listar_contas(tipo: str = None, estado: str = None) -> list:
    accounts = _load()
    if tipo:
        accounts = [a for a in accounts if a["tipo"] == tipo]
    if estado:
        accounts = [a for a in accounts if a["estado"] == estado]
    return accounts


def get_conta(id: str) -> dict | None:
    for a in _load():
        if a["id"] == id:
            return a
    return None


def actualizar_snapshot(id: str, snapshot: dict):
    """O collector de cada conta chama isto para actualizar o estado financeiro."""
    accounts = _load()
    for a in accounts:
        if a["id"] == id:
            a["ultimo_snapshot"] = {
                **snapshot,
                "ts": datetime.now().isoformat(),
            }
            if "pnl_total" in snapshot:
                a["pnl_total"] = snapshot["pnl_total"]
            if "pnl_mes" in snapshot:
                a["pnl_mes"] = snapshot["pnl_mes"]
            break
    _save(accounts)


def actualizar_estado(id: str, estado: str):
    accounts = _load()
    for a in accounts:
        if a["id"] == id:
            a["estado"] = estado
            break
    _save(accounts)


def resumo_imperio() -> dict:
    """Snapshot financeiro completo do império para o CFO."""
    accounts = _load()
    total_alocado = sum(a["capital_alocado"] for a in accounts)
    total_pnl = sum(a.get("pnl_total", 0) for a in accounts)
    total_pnl_mes = sum(a.get("pnl_mes", 0) for a in accounts)
    activas = [a for a in accounts if a["estado"] == ESTADO_ACTIVO]

    return {
        "total_contas": len(accounts),
        "contas_activas": len(activas),
        "capital_total_alocado": round(total_alocado, 2),
        "pnl_total_imperio": round(total_pnl, 4),
        "pnl_mes_imperio": round(total_pnl_mes, 4),
        "contas": accounts,
    }


def _seed_contas_iniciais():
    """Regista as contas actuais do império se ainda não existirem."""
    registar_conta(
        id="binance_supertrend_btc",
        nome="Supertrend BTC/USDT",
        tipo=TIPO_TRADING,
        plataforma="Binance",
        capital_alocado=0.0,  # inactivo — sem trades
        moeda="USDT",
        collector="collector_supertrend",
        estado=ESTADO_PAUSADO,
        notas="Estratégia lenta 4h — em observação. CFO decide quando activar.",
    )
    registar_conta(
        id="binance_grid_btc",
        nome="Grid Bot BTC/USDT",
        tipo=TIPO_TRADING,
        plataforma="Binance",
        capital_alocado=100.0,
        moeda="USDT",
        collector="collector_grid",
        estado=ESTADO_ACTIVO,
        meta_mensal=4.0,  # 4% ao mês baseado no backtest
        notas="Grid 10 níveis, range 8%. Activo desde 04/08/2026.",
    )
    registar_conta(
        id="binance_grid_eth",
        nome="Grid Bot ETH/USDT",
        tipo=TIPO_TRADING,
        plataforma="Binance",
        capital_alocado=100.0,
        moeda="USDT",
        collector="collector_eth_grid",
        estado=ESTADO_ACTIVO,
        meta_mensal=5.0,  # ETH mais volátil → mais trades → meta ligeiramente superior
        notas="Grid 10 níveis, range 10%. Activo desde 05/08/2026.",
    )
    registar_conta(
        id="etsy_planneratlas",
        nome="PlannerAtlas",
        tipo=TIPO_LOJA,
        plataforma="Etsy",
        capital_alocado=0.0,
        moeda="EUR",
        collector="collector_etsy",
        estado=ESTADO_ACTIVO,
        meta_mensal=200.0,
        notas="24 listings activos. Ads a partir 01/08/2026.",
    )


# Seed automático quando importado pela primeira vez
if not _ACCOUNTS_FILE.exists():
    _seed_contas_iniciais()
