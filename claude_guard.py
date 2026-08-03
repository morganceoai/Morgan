"""
Claude Guard — 5 camadas de protecção contra consumo descontrolado de tokens.

Camada 1: Tecto por chamada (max tokens por request)
Camada 2: Budget diário por agente (USD estimado)
Camada 3: Circuit breaker (pybreaker — fecha circuito após falhas consecutivas)
Camada 4: Token velocity guard (detecta loops por janela de 60s)
Camada 5: Detector de prompt repetido (hash, bloqueia se mesmo prompt 3x seguidas)

Uso:
    from claude_guard import claude_call
    resposta = claude_call(
        agente="ceo",
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )
"""

import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_log = logging.getLogger(__name__)

# ── Configuração ───────────────────────────────────────────────────────────────

BUDGET_FILE = Path(__file__).parent / "memory" / "claude_usage.json"

# Custo estimado por 1M tokens (input + output médio ponderado)
CUSTO_POR_1M = {
    "claude-sonnet-4-6": 9.0,   # $3 input + $15 output, média ponderada
    "claude-opus-4-8":   15.0,  # $5 input + $25 output, média ponderada
    "claude-haiku-4-5-20251001": 3.0,  # $1 input + $5 output
    "claude-haiku-4-5":  3.0,
    "default":           9.0,
}

# Budget diário por agente (USD) — soma total máx ~$5/dia
BUDGET_DIARIO = {
    "ceo":       2.0,
    "scout":     1.0,
    "cfo":       0.5,
    "coach":     0.5,
    "creator":   0.5,
    "solver":    0.5,
    "operator":  0.5,
    "marketeer": 0.5,
    "patlas":    0.3,
    "pulser":    0.3,
    "sistema":   0.5,  # desktop_server chamadas directas
    "router":    0.3,  # classificador Haiku (chamadas rápidas e baratas)
    "_total":    5.0,  # tecto absoluto diário
}

# Camada 1: tecto de tokens por chamada
MAX_INPUT_TOKENS = 60_000   # ~45k words — mais do que qualquer briefing normal
MAX_OUTPUT_TOKENS = 8_000

# Camada 4: token velocity (janela de 60s)
VELOCITY_JANELA_SEC = 60
VELOCITY_MAX_TOKENS = 80_000   # mais de 80k tokens em 60s = loop

# Camada 5: detector de prompt repetido
MAX_REPETICOES_PROMPT = 3

# ── Estado em memória ──────────────────────────────────────────────────────────

_lock = Lock()
_velocity: dict[str, deque] = defaultdict(deque)  # agente → deque de (ts, tokens)
_prompt_hashes: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))  # agente → últimos hashes
_circuit_open: dict[str, float] = {}  # agente → timestamp quando circuito abriu
_falhas_consecutivas: dict[str, int] = defaultdict(int)
CIRCUIT_FALHAS_MAX = 5
CIRCUIT_RESET_SEC = 300  # 5 min


# ── Persistência de budget ─────────────────────────────────────────────────────

def _load_budget() -> dict:
    try:
        if BUDGET_FILE.exists():
            return json.loads(BUDGET_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_budget(data: dict):
    try:
        BUDGET_FILE.parent.mkdir(exist_ok=True)
        BUDGET_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        pass


def _hoje() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _registar_uso(agente: str, model: str, tokens_total: int):
    """Regista uso em memory/claude_usage.json."""
    hoje = _hoje()
    custo_1m = CUSTO_POR_1M.get(model, CUSTO_POR_1M["default"])
    custo = (tokens_total / 1_000_000) * custo_1m

    with _lock:
        data = _load_budget()
        if "dias" not in data:
            data["dias"] = {}
        if hoje not in data["dias"]:
            data["dias"][hoje] = {"total_tokens": 0, "total_usd": 0.0, "agentes": {}}

        dia = data["dias"][hoje]
        dia["total_tokens"] = dia.get("total_tokens", 0) + tokens_total
        dia["total_usd"] = round(dia.get("total_usd", 0.0) + custo, 6)

        if agente not in dia["agentes"]:
            dia["agentes"][agente] = {"tokens": 0, "usd": 0.0, "chamadas": 0}
        ag = dia["agentes"][agente]
        ag["tokens"] = ag.get("tokens", 0) + tokens_total
        ag["usd"] = round(ag.get("usd", 0.0) + custo, 6)
        ag["chamadas"] = ag.get("chamadas", 0) + 1

        # manter só últimos 30 dias
        dias_sorted = sorted(data["dias"].keys())
        for d in dias_sorted[:-30]:
            del data["dias"][d]

        _save_budget(data)
    return custo


def _gasto_hoje(agente: str) -> float:
    """Retorna USD gasto hoje por este agente."""
    hoje = _hoje()
    data = _load_budget()
    return data.get("dias", {}).get(hoje, {}).get("agentes", {}).get(agente, {}).get("usd", 0.0)


def _gasto_total_hoje() -> float:
    hoje = _hoje()
    data = _load_budget()
    return data.get("dias", {}).get(hoje, {}).get("total_usd", 0.0)


# ── As 5 camadas ───────────────────────────────────────────────────────────────

class BudgetExceeded(Exception):
    pass

class VelocityExceeded(Exception):
    pass

class PromptLoop(Exception):
    pass

class CircuitOpen(Exception):
    pass


def _check_circuit(agente: str):
    """Camada 3 — circuit breaker."""
    if agente in _circuit_open:
        elapsed = time.time() - _circuit_open[agente]
        if elapsed < CIRCUIT_RESET_SEC:
            raise CircuitOpen(
                f"[{agente}] circuito aberto há {elapsed:.0f}s — "
                f"aguardar {CIRCUIT_RESET_SEC - elapsed:.0f}s"
            )
        else:
            # half-open: deixar passar 1 chamada de teste
            del _circuit_open[agente]
            _falhas_consecutivas[agente] = 0
            _log.info("[claude_guard] circuito %s → half-open", agente)


def _registar_falha(agente: str):
    _falhas_consecutivas[agente] += 1
    if _falhas_consecutivas[agente] >= CIRCUIT_FALHAS_MAX:
        _circuit_open[agente] = time.time()
        _log.error(
            "[claude_guard] circuito ABERTO para %s após %d falhas",
            agente, _falhas_consecutivas[agente]
        )
        _alertar(agente, f"Circuit breaker aberto após {_falhas_consecutivas[agente]} falhas consecutivas")


def _registar_sucesso(agente: str):
    _falhas_consecutivas[agente] = 0
    if agente in _circuit_open:
        del _circuit_open[agente]


def _check_velocity(agente: str, tokens_estimados: int):
    """Camada 4 — token velocity (janela 60s)."""
    agora = time.time()
    fila = _velocity[agente]
    while fila and fila[0][0] < agora - VELOCITY_JANELA_SEC:
        fila.popleft()
    total_janela = sum(t for _, t in fila) + tokens_estimados
    if total_janela > VELOCITY_MAX_TOKENS:
        raise VelocityExceeded(
            f"[{agente}] {total_janela} tokens em {VELOCITY_JANELA_SEC}s — "
            f"possível loop (limite: {VELOCITY_MAX_TOKENS})"
        )
    fila.append((agora, tokens_estimados))


def _check_prompt_repetido(agente: str, prompt_hash: str):
    """Camada 5 — detector de prompt repetido."""
    fila = _prompt_hashes[agente]
    repeticoes = sum(1 for h in fila if h == prompt_hash)
    if repeticoes >= MAX_REPETICOES_PROMPT:
        raise PromptLoop(
            f"[{agente}] mesmo prompt enviado {repeticoes + 1}x seguidas — loop detectado"
        )
    fila.append(prompt_hash)


def _estimar_tokens(messages: list, max_tokens: int) -> int:
    """Estimativa rápida: 1 token ≈ 4 chars."""
    chars = sum(len(str(m.get("content", ""))) for m in messages)
    return (chars // 4) + max_tokens


def _alertar(agente: str, motivo: str):
    """Push de emergência ao Vasco."""
    try:
        from push_service import send_push
        send_push(
            title=f"⛔ Claude Guard — {agente.upper()}",
            body=motivo[:200],
            url="/pwa/"
        )
    except Exception:
        pass
    try:
        from episodic_memory import registar_evento
        registar_evento("ceo", "claude_guard_alerta", f"[{agente}] {motivo}")
    except Exception:
        pass
    _log.critical("[claude_guard] ALERTA %s: %s", agente, motivo)


# ── Ponto de entrada principal ─────────────────────────────────────────────────

def claude_call(
    agente: str,
    model: str,
    messages: list,
    max_tokens: int = 1000,
    system: str | None = None,
    **kwargs
) -> object:
    """
    Wrapper seguro para anthropic.messages.create().
    Aplica as 5 camadas de protecção antes e regista uso depois.

    Raises BudgetExceeded, VelocityExceeded, PromptLoop, CircuitOpen em caso de violação.
    """
    import anthropic

    # ── Camada 1: tecto por chamada ──
    if max_tokens > MAX_OUTPUT_TOKENS:
        _log.warning("[claude_guard] %s: max_tokens=%d reduzido para %d", agente, max_tokens, MAX_OUTPUT_TOKENS)
        max_tokens = MAX_OUTPUT_TOKENS

    tokens_estimados = _estimar_tokens(messages, max_tokens)
    if tokens_estimados > MAX_INPUT_TOKENS + MAX_OUTPUT_TOKENS:
        raise BudgetExceeded(
            f"[{agente}] prompt estimado em {tokens_estimados} tokens — excede tecto por chamada"
        )

    # ── Camada 2: budget diário ──
    budget_agente = BUDGET_DIARIO.get(agente, 0.5)
    gasto_agente = _gasto_hoje(agente)
    gasto_total = _gasto_total_hoje()

    if gasto_agente >= budget_agente:
        msg = f"Budget diário do agente {agente} esgotado: ${gasto_agente:.4f} / ${budget_agente}"
        _alertar(agente, msg)
        raise BudgetExceeded(msg)

    budget_total = BUDGET_DIARIO.get("_total", 5.0)
    if gasto_total >= budget_total:
        msg = f"Budget diário TOTAL esgotado: ${gasto_total:.4f} / ${budget_total}"
        _alertar(agente, msg)
        raise BudgetExceeded(msg)

    # ── Camada 3: circuit breaker ──
    with _lock:
        _check_circuit(agente)

    # ── Camada 4: token velocity ──
    with _lock:
        _check_velocity(agente, tokens_estimados)

    # ── Camada 5: prompt repetido ──
    prompt_texto = " ".join(str(m.get("content", "")) for m in messages)
    prompt_hash = hashlib.sha256(prompt_texto[:2000].encode()).hexdigest()[:16]
    with _lock:
        _check_prompt_repetido(agente, prompt_hash)

    # ── Chamada real ──
    try:
        client = anthropic.Anthropic()
        params = dict(model=model, messages=messages, max_tokens=max_tokens, **kwargs)
        if system:
            params["system"] = system

        resposta = client.messages.create(**params)

        # Regista uso real
        tokens_usados = resposta.usage.input_tokens + resposta.usage.output_tokens
        custo = _registar_uso(agente, model, tokens_usados)

        with _lock:
            _registar_sucesso(agente)
            # actualiza velocity com tokens reais (substitui estimativa)
            fila = _velocity[agente]
            if fila:
                ts_est, _ = fila[-1]
                fila[-1] = (ts_est, tokens_usados)

        _log.info(
            "[claude_guard] %s | %s | %d tokens | $%.4f (acum hoje: $%.4f)",
            agente, model, tokens_usados, custo, _gasto_hoje(agente)
        )

        # Alerta preventivo a 80% do budget
        if _gasto_hoje(agente) >= budget_agente * 0.8:
            _alertar(agente, f"A 80% do budget diário: ${_gasto_hoje(agente):.4f} / ${budget_agente}")

        return resposta

    except (BudgetExceeded, VelocityExceeded, PromptLoop, CircuitOpen):
        raise
    except Exception as e:
        with _lock:
            _registar_falha(agente)
        raise


# ── Utilitários de consulta ────────────────────────────────────────────────────

def resumo_uso_hoje() -> str:
    """Resumo legível do uso de hoje — para o CEO/dashboard."""
    hoje = _hoje()
    data = _load_budget()
    dia = data.get("dias", {}).get(hoje, {})
    if not dia:
        return "Sem chamadas Claude registadas hoje."

    total_tokens = dia.get("total_tokens", 0)
    total_usd = dia.get("total_usd", 0.0)
    budget_total = BUDGET_DIARIO.get("_total", 5.0)
    pct = (total_usd / budget_total * 100) if budget_total else 0

    linhas = [
        f"💰 Claude hoje: {total_tokens:,} tokens | ${total_usd:.4f} / ${budget_total:.2f} ({pct:.0f}%)"
    ]
    for ag, info in sorted(dia.get("agentes", {}).items()):
        linhas.append(
            f"  • {ag}: {info['chamadas']}x | {info['tokens']:,} tok | ${info['usd']:.4f}"
        )

    circuitos = [ag for ag in _circuit_open]
    if circuitos:
        linhas.append(f"⛔ Circuitos abertos: {', '.join(circuitos)}")

    return "\n".join(linhas)


def estado_circuitos() -> dict:
    return {ag: "ABERTO" for ag in _circuit_open}


# ── Cliente guardado ──────────────────────────────────────────────────────────

class _GuardedMessages:
    """Substitui client.messages com intercepção transparente."""

    def __init__(self, agente: str, real_messages):
        self._agente = agente
        self._real = real_messages

    def create(self, *, model: str, messages: list, max_tokens: int = 1000,
               system: str | None = None, **kwargs):
        # Extrair agente do model se não definido explicitamente
        agente = self._agente

        # Camada 1
        if max_tokens > MAX_OUTPUT_TOKENS:
            _log.warning("[claude_guard] %s: max_tokens=%d → %d", agente, max_tokens, MAX_OUTPUT_TOKENS)
            max_tokens = MAX_OUTPUT_TOKENS

        tokens_est = _estimar_tokens(messages, max_tokens)
        if tokens_est > MAX_INPUT_TOKENS + MAX_OUTPUT_TOKENS:
            raise BudgetExceeded(f"[{agente}] prompt ~{tokens_est} tokens excede tecto")

        # Camada 2
        budget_ag = BUDGET_DIARIO.get(agente, 0.5)
        gasto_ag = _gasto_hoje(agente)
        gasto_tot = _gasto_total_hoje()
        if gasto_ag >= budget_ag:
            msg = f"Budget {agente} esgotado: ${gasto_ag:.4f}/${budget_ag}"
            _alertar(agente, msg); raise BudgetExceeded(msg)
        budget_tot = BUDGET_DIARIO.get("_total", 5.0)
        if gasto_tot >= budget_tot:
            msg = f"Budget TOTAL esgotado: ${gasto_tot:.4f}/${budget_tot}"
            _alertar(agente, msg); raise BudgetExceeded(msg)

        # Camada 3
        with _lock:
            _check_circuit(agente)

        # Camada 4
        with _lock:
            _check_velocity(agente, tokens_est)

        # Camada 5
        texto = " ".join(str(m.get("content", "")) for m in messages)
        ph = hashlib.sha256(texto[:2000].encode()).hexdigest()[:16]
        with _lock:
            _check_prompt_repetido(agente, ph)

        # Chamada real
        try:
            params = dict(model=model, messages=messages, max_tokens=max_tokens, **kwargs)
            if system is not None:
                params["system"] = system
            resp = self._real.create(**params)

            tokens_reais = resp.usage.input_tokens + resp.usage.output_tokens
            custo = _registar_uso(agente, model, tokens_reais)
            with _lock:
                _registar_sucesso(agente)
                fila = _velocity[agente]
                if fila:
                    ts, _ = fila[-1]
                    fila[-1] = (ts, tokens_reais)

            _log.info("[claude_guard] %s | %s | %dt | $%.4f", agente, model, tokens_reais, custo)
            if _gasto_hoje(agente) >= budget_ag * 0.8:
                _alertar(agente, f"80% do budget: ${_gasto_hoje(agente):.4f}/${budget_ag}")
            return resp

        except (BudgetExceeded, VelocityExceeded, PromptLoop, CircuitOpen):
            raise
        except Exception:
            with _lock:
                _registar_falha(agente)
            raise


class GuardedClient:
    """
    Substituto drop-in para anthropic.Anthropic() com protecção de custos.

    Uso:
        from claude_guard import GuardedClient
        claude = GuardedClient("ceo")
        # claude.messages.create(...) já está protegido
    """
    def __init__(self, agente: str):
        import anthropic
        self._client = anthropic.Anthropic()
        self.messages = _GuardedMessages(agente, self._client.messages)
        self._agente = agente

    def __getattr__(self, name):
        return getattr(self._client, name)


def get_guarded_client(agente: str) -> GuardedClient:
    """Factory: devolve um cliente Anthropic com todas as camadas de protecção."""
    return GuardedClient(agente)


if __name__ == "__main__":
    print(resumo_uso_hoje())
